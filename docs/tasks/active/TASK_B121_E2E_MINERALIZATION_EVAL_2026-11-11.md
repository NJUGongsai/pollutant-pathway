# 任务书：`[biosysmodb121]` 全卷 121 条多步降解路径端到端无束宽（`B=1`）完全矿化评测

- **文档编号**：`TASK_B121_E2E_MINERALIZATION_EVAL_2026-11-11`
- **立项与拍板日期**：2026-11-11（CC 逐项拍板确认）
- **题域标签**：**`[biosysmodb121]`**（B1 环境微生物多步降解路径，与 `[dev-298]` 双向不外推）
- **模型与管线锚点**：
  - 基座模型固定：**`deepseek-v4.1-flash-1017`**
  - 生产管线固定：**`v44-Next v1.2`**（`/Volumes/CC/Enzyme_Agent/v44` @ `d40eec7`：`S1d + S5-env ∪ S5-rr` 12 大类均衡 Top-16 建池 + 去 `v1card` + 双路 `novel` 编译 + 智能门控回填 + C-C/C-O/C1 裂解共产物补全 + 五层级候选排序器校准）

---

## 一、 CC 拍板决议与现状表

### 1.1 CC 已拍板锁定的四大设计准则（2026-11-11）

| 拍板项 | 锁定结论 | 工程与化学兑现契约 |
| :--- | :--- | :--- |
| **评测范围（选项 B）** | 评测 `biosysmodb121` 全卷 **`121` 条正式多步降解路径**（覆盖 `417` 道单步题来源），从每条路径的起始根污染物出发端到端自回归推演 | 公开与内部报告同时拆分三栏独立披露：<br>① **`[biosysmodb121·Tuning]`（`76` 条路径 / `261` 步）**<br>② **`[biosysmodb121·Holdout]`（`43` 条路径 / `156` 步，盲测只读一镜到底，严禁回调任何参数）**<br>③ **`[biosysmodb121·Full-121]`（全卷 `121` 条路径，含 `2` 条非 `417` 正式路径）** |
| **搜索策略（不要束宽 `B`）** | **严格零束宽 `B = 1`**（每步只认校准排序后第 1 名的合规反应事件，不靠平行猜多条备选路线凑召回） | 对每个非终点待降解分子，调用正规 `v44-Next v1.2`（`start_ppv1_run`），从导出的已通过 11 项 `audit_hypothesis` 的合规事件中**严格只取 `Rank 1` 那唯一 1 个反应事件**（若 `0` 个合规事件则该分支判 `DEAD_END_TP`）。 |
| **完全矿化终点标志（A1 + A2）** | **三道硬门槛同时满足才停机**：<br>1) **A0/A 档无机物**：无碳无机物（`H₂O/NH₃/Cl⁻/SO₄²⁻/PO₄³⁻` 等）或直接无机碳（**`CO₂`、碳酸/碳酸氢根**）；**一碳有机物（甲醇/甲醛/甲酸/氰化物/尿素）和乙醛不算终点，必须继续氧化到 `CO₂` 或乙酸才停**；<br>2) **B 档宿主中心碳代谢核心池（~21 个精确分子白名单）**：丙酮酸、乳酸、乙酸、乙酰-CoA、丙酰-CoA、乙酰乙酸、乙酰乙酰-CoA、琥珀酸、琥珀酰-CoA、富马酸、苹果酸、草酰乙酸、柠檬酸、顺乌头酸、异柠檬酸、2-酮戊二酸、乙醛酸、甘油醛-3-磷酸、二羟丙酮磷酸、3-磷酸甘油酸、2-磷酸甘油酸、PEP；<br>3) **儿茶酚/原儿茶酸/龙胆酸/苯甲酸等未开环漏斗中间体不算终点**，必须把芳环劈开落进中心代谢池才停机。 | 新增确定性零 LLM 终点分类器 [`src/pathway_v43/pollutant/mineralization_sink.py`](../../src/pathway_v43/pollutant/mineralization_sink.py)（契约版本 `ppv1-mineralization-sink-v1`）：<br>• 基于 RDKit 去电荷归一精确分子身份匹配白名单 + 外源杂原子（卤素/硝基/偶氮/磺酸/硫代磷酸酯等）与非辅因子未开环芳环一票否决；<br>• 内源货币辅因子副产物（如 `NADH/NAD+`、`ADP/ATP`、`CoA-SH`、`FAD/FADH2`、`SAH` 等作为 `coproduct` 出现时）标记为 `ENDOGENOUS_CURRENCY_COFACTOR` 不误追；<br>• 若数据库参考路径提前停在儿茶酚等半路节点，参考图对齐算分时**绝不惩罚模型继续往下走到矿化的额外步数**。 |
| **裂解分支闭合与防失控护栏（A3）** | **全含碳分支闭合 + 单分支 `15` 步安全上限 + 环路检测** | 同一步 `Rank 1` 反应事件产出的**全部含碳非货币辅因子产物**（含 `principal_product` 与裂解补全 `coproduct`）均必须各自入队追踪：<br>• 全部含碳分支均抵达 `A0/A/B` 终点池 $\Rightarrow$ **`MINERALIZED_CLOSED`**（并细分碳账 100% 闭合 vs 存在未声明碳损失）；<br>• 任一分支出现祖先同构分子 $\Rightarrow$ **`CYCLE_ABORTED`**；<br>• 任一分支达 `depth == 15` 仍未进终点池 $\Rightarrow$ **`MAX_DEPTH_UNFINISHED`**；<br>• 任一分支无合规反应提前中断 $\Rightarrow$ **`DEAD_END_TP`**。 |

### 1.2 底层数据现状核实（已实测确认）

| 数据源路径 | 行数 / 规模 | 核实结论 |
| :--- | :---: | :--- |
| `/Volumes/CC/Enzyme_Agent/v44/reports/ppv1_s5b/b121_full_20261103/biosysmodb121/work/B1/out/formal_121_cases.tsv` | `121` 条路径 | 含 `97` 条 `LINEAR_UNIQUE` 线性链 + `24` 条 `BRANCHED_DAG` 分支图。 |
| `/Volumes/CC/Enzyme_Agent/v44/reports/ppv1_s5b/b121_full_20261103/biosysmodb121/work/B1/out/step_queries.tsv` & `step_participants.tsv` | `533` 步 / `2,473` 参与物行 | 提取每条路径 `predecessor_step_ids == ""` 且 `in_main_view == "TRUE"` 的起始 `SUBSTRATE`，`121/121` 条路径 100% 具备合法 RDKit 根污染物结构（`111` 条单根底物、`10` 条双根底物）。 |
| `/Volumes/CC/Enzyme_Agent/v44/docs/reviews/evidence/strong_model_probe_phase0_1_2026-11-09/seed_and_arm_identity_b121.json` | `417` 步分集锚点 | 按 `case_id` 整路径切分：`76` 条 Tuning 路径（`261` 步）、`43` 条 Holdout 路径（`156` 步）、`2` 条无单步 `417` 题路径（合计 `121` 条）。 |

---

## 二、 铁律与红线约束

1. **留出集单向盲测纪律**：
   - `mineralization_sink.py` 的编写、单元测试与前 5 条路径冒烟测试**只准在 `[biosysmodb121·Tuning]` 子集或教科书通用分子上进行**；
   - 冒烟通过后锁定代码哈希，一次性跑通全卷 `121` 条路径；**严禁根据 Holdout（43 条）结果回头修改终点白名单、排序器或管线参数**。
2. **公开产物零金标 / 零题面 / 零私有 ID**：
   - 公开报告（`docs/reports/B121_E2E_MINERALIZATION_BENCHMARK_2026-11-11.md`）与公开证据 JSON（`docs/reviews/evidence/b121_e2e_mineralization_2026-11-11/e2e_mineralization_summary.json`）**严禁出现任何 `BIOPATH150_xxx`、`BSY-rxxx`、单题 `qid` 或测试集污染物/中间体 SMILES**（仅允许讨论教科书通用中心代谢物如 `pyruvate`、`succinate`、`CO₂`）；
   - 逐路径推演树明细、每步事件记录与私有对账表一律写入 gitignored 目录：`reports/ppv1_s5b/b121_e2e_mineralization_20261111/`。
3. **正规 PPV1 管线与零密钥落盘**：
   - 每个波次（Wave $d = 1 \dots 15$）的新增唯一非终点底物必须走正规 `v44-Next v1.2` 建池与 `start_ppv1_run`（或 `s5b_cli build --preset v44-next --recorded-source` + 并发在线调用），所有采纳事件必须 100% 通过 `prepare_hypothesis` + `execute_atomtool_expansion` + 11 项 `audit_hypothesis`；
   - API 凭证通过 `load_llm_credentials_in_memory()`（内存读取远端 `llm_exp1.env`）注入，绝不将密钥写入任何仓库文件或日志；完整记录每波次 `input_tokens`、`output_tokens`、`reasoning_output_tokens`（价目快照写 `未核实`）。
4. **mimo 化学判据评审同步执行（`AGENTS.md` 触发点 1）**：
   - 对冻结的 `mineralization_sink.py` 规则级化学判据（零金标），通过通道 A（`opencode run -m opencode/mimo-v2.6-flash-free`）执行只读化学抽审，原文落盘 `docs/mimo_mineralization_endpoint_review_response_2026-11-11.md`，按“与程序证据互证”原则核验无化学漏洞。

---

## 三、 核心模块设计与波次去重执行协议

### 3.1 确定性完全矿化终点判定器：`src/pathway_v43/pollutant/mineralization_sink.py`

1. **分类优先级（输入任意合法 SMILES `s` 及参与物角色 `role`）**：
   - **Step 1（无碳无机物 `A0_noncarbon_inorganic`）**：若碳原子数 `C == 0`，返回 `is_terminal_sink=True, sink_tier="A0_noncarbon_inorganic"`（如 `H2O`, `O2`, `NH3/NH4+`, `Cl-`, `Br-`, `F-`, `I-`, `SO4^2-`, `H2S`, `PO4^3-`, `NO2-/NO3-` 等）。
   - **Step 2（内源货币辅因子旁观排除 `ENDOGENOUS_CURRENCY_COFACTOR`）**：仅当 `role == "coproduct"` 时，若去电荷后连通骨架 InChIKey-14 命中冻结货币辅因子集合（`NAD+/NADH`, `NADP+/NADPH`, `FAD/FADH2`, `FMN/FMNH2`, `ATP/ADP/AMP/adenosine`, `GTP/GDP`, `UTP/UDP`, `CTP/CDP`, `free CoA-SH`, `SAM/SAH`, `PAPS/PAP`, `THF`, `glutathione GSH/GSSG`），返回 `is_terminal_sink=True, sink_tier="ENDOGENOUS_CURRENCY_COFACTOR", track_branch=False`（避免把辅酶副产物当污染物碎片往下拆）。
   - **Step 3（直接无机一碳矿化物 `A_inorganic_carbon`）**：去电荷质子化归一后精确匹配二氧化碳 `O=C=O`（InChIKey-14 `CURLTUGMZLYLDI`）或碳酸/碳酸氢根/碳酸根 `O=C(O)O`（InChIKey-14 `BVKZGUZZVIAZIE`），返回 `is_terminal_sink=True, sink_tier="A_inorganic_carbon"`。
     - **显式拦截**：`CO`（一氧化碳）、`CO`（甲醇 `CH3OH`）、`C=O`（甲醛）、`O=CO`（甲酸/甲酸根）、`C#N`（氰化氢/氰根）、`NC(N)=O`（尿素）、`CN`（甲胺）、`C`（甲烷）**一律 `is_terminal_sink=False`，标记 `reason="c1_organic_must_oxidize_to_co2"`**！
   - **Step 4（外源毒害基团一票否决护栏）**：若分子含任何 `F, Cl, Br, I, As, Hg, Pb, Sn, Br`、硝基 `-[N+](=O)[O-]`、亚硝基、偶氮基 `-N=N-`、叠氮基、磺酸基 `-S(=O)(=O)[O,OH]`、膦酸/硫代磷酸酯键，直接返回 `is_terminal_sink=False, reason="xenobiotic_moiety_present"`。
   - **Step 5（宿主中心碳代谢核心池精确白名单 `B_central_carbon_sink`）**：
     - 对输入分子执行 `rdMolStandardize.Uncharger` 中性化（保留双键顺反构型以区分富马酸 `fumarate` 与马来酸 `cis-maleate`：若明确标为顺式马来酸 `C(\C(=O)O)=C\C(=O)O`，令其再异构化 1 步至富马酸/苹果酸；反式富马酸与未指定立体丁烯二酸放行），用中性化后**精确连通性与原子组成签名（`InChIKey-14` + 元素计数表）**匹配以下 **22 个冻结中心碳代谢核心分子**：
       1. `citrate`（柠檬酸）
       2. `cis-aconitate`（顺乌头酸）
       3. `isocitrate`（异柠檬酸）
       4. `2-oxoglutarate`（$\alpha$-酮戊二酸）
       5. `succinyl-CoA`（琥珀酰辅酶 A）
       6. `succinate`（琥珀酸）
       7. `fumarate`（富马酸；排除显式 `Z`-马来酸）
       8. `malate`（苹果酸）
       9. `oxaloacetate`（草酰乙酸）
       10. `glyoxylate`（乙醛酸）
       11. `glyceraldehyde-3-phosphate`（3-磷酸甘油醛）
       12. `dihydroxyacetone-phosphate`（二羟丙酮磷酸）
       13. `1,3-bisphosphoglycerate`（1,3-二磷酸甘油酸）
       14. `3-phosphoglycerate`（3-磷酸甘油酸）
       15. `2-phosphoglycerate`（2-磷酸甘油酸）
       16. `phosphoenolpyruvate`（磷酸烯醇式丙酮酸 PEP）
       17. `pyruvate`（丙酮酸）
       18. `lactate`（乳酸）
       19. `acetate`（乙酸；**注意：乙醛 `CC=O` 显式排除，必须继续氧化为乙酸或乙酰-CoA！**）
       20. `acetyl-CoA`（乙酰辅酶 A）
       21. `propionyl-CoA`（丙酰辅酶 A）
       22. `acetoacetate` & `acetoacetyl-CoA`（乙酰乙酸 / 乙酰乙酰辅酶 A）
     - **未命中白名单的所有其他含碳分子**（包括：儿茶酚、原儿茶酸、龙胆酸、苯甲酸、水杨酸、苯乙酸、苯甲酰-CoA 等芳环分子；粘康酸、2-羟基粘康酸半醛、3-氧代己二酸等开环中段分子；乙醛、乙醇、甲醇、甲醛、甲酸）：一律返回 **`is_terminal_sink=False`**，继续入队推演！

### 3.2 波次去重并发自回归驱动器：`scripts/eval/run_b121_e2e_mineralization_eval.py`

为在保证 **100% 真实正规 `v44-Next v1.2` + `deepseek-v4.1-flash-1017` 单步执行**的前提下兼顾速度与断点续跑能力，采用 **Wave-by-Wave（按深度波次 $d = 1, 2, \dots, 15$）唯一底物去重并发执行**：

1. **初始化（Wave 0）**：
   - 读取 `formal_121_cases.tsv`、`step_queries.tsv`、`step_participants.tsv` 与 `seed_and_arm_identity_b121.json`；
   - 为每条路径 $m \in \{1 \dots 121\}$ 提取 `predecessor_step_ids == ""` 且 `in_main_view == "TRUE"` 的起始 `SUBSTRATE` 分子，作为初始活跃分支节点 `(smiles, strict_id, depth=0, ancestor_strict_ids=frozenset())`；
   - 同时提取每条路径在 `step_participants.tsv`（`in_main_view == "TRUE"`）中的参考中间体/终末产物集合 $V_{m,\text{ref}}$ 与有向反应边集合 $E_{m,\text{ref}}$，仅供最终零 LLM 对齐打分使用（推演期 100% 盲推，严禁把参考图信息喂给模型或终点器）。
2. **波次推进（对 $d = 1, 2, \dots, 15$）**：
   - 扫描全部活跃路径树中处于 `depth == d - 1` 且尚未终止的分支节点：
     - 先运行 `classify_mineralization_sink(smiles, role="principal_product")`：若已命中终点池，直接将该节点状态标为 `SINK_REACHED`；
     - 若 `strict_id in ancestor_strict_ids`，标为 `CYCLE_ABORTED`；
   - 汇总本波次所有待展开且不在本地持久化缓存 `substrate_step_cache/` 中的唯一底物 `strict_id -> canonical_smiles`；
   - 若新增唯一底物集合非空：
     - 构造该波次标准单步输入 `wave_d_questions.jsonl`（虚设占位参考产物，因为在线推演期不判分，只跑 `build` + `run` 拿 `native_export`！）；
     - 调用正规 `v44-Next v1.2` 建池（`build_question_batch(..., preset="v44-next", recorded_source=True)`）与多进程/多线程并发在线执行（`deepseek-v4.1-flash-1017`，固定 **36 路并发 `--workers 36`**，每完成一个底物立即原子落盘至 `substrate_step_cache/<sha16>.json`，含 Top-1 事件主产物、全部共产物、碳账完整性、编译/审计摘要及真实 Token 用量）；
     - **复用加速规则（可选开关 `--reuse-v12-tuning-runs`，默认关闭或仅对完全同代码 `build_identity` 的已录制单步核验）**：为保证全卷 121 条路径在完全统一的 `v44-Next v1.2` 提示与运行环境下公平测试，默认统一走 `v44-Next v1.2` 实跑并持久化到 `substrate_step_cache/`（由于不同路径在儿茶酚/原儿茶酸/粘康酸半醛/乙醛/甲酸等中间体大量汇合，全卷 121 条路径跨越 15 步预计去重后仅约 `280–420` 个唯一底物，**36 路并发**仅需约 **8–12 分钟**即可全部跑完！）。
   - **严格 `B = 1` 展开与全含碳分支入队**：
     - 读取该底物导出的 `native_export` 中排位第 1 的已准入事件 `Event #1`：
       - 若无任何已准入事件：当前分支终止为 `DEAD_END_TP`；
       - 若有 `Event #1`：提取 `Event #1` 产物侧全部参与物（`principal_product` + `coproduct`），逐个调用 `classify_mineralization_sink(prod_smiles, role=prod_role)`：
         - 若 `sink_tier == "ENDOGENOUS_CURRENCY_COFACTOR"` 或 `"A0_noncarbon_inorganic"`：记入已释放辅因子/无碳无机物，不建新碳分支；
         - 若 `sink_tier in ("A_inorganic_carbon", "B_central_carbon_sink")`：建立子叶节点并立即标为 `SINK_REACHED`；
         - 若 `is_terminal_sink == False`（含碳未矿化碎片）：若 `d == 15` 则标为 `MAX_DEPTH_UNFINISHED`，否则若 `prod_strict_id in (ancestor_strict_ids | {strict_id})` 则标为 `CYCLE_ABORTED`，否则作为 `depth = d` 活跃分支入下一波次队列！
       - **未声明碳损失核查（Carbon Bookkeeping Check）**：对比底物碳数与 `Event #1` 产物侧（扣除显式共底物/辅因子碳数后）碳数总和；若存在未由显式 `coproduct` 承载的碳损失，将该步标记 `has_unaccounted_carbon_loss = True`。
3. **路径级四分类结局与双栏参考图对齐统计**：
   - **路径结局四桶（互斥完备，分母分别为 `76` / `43` / `121`）**：
     1. **`MINERALIZED_CLOSED`**（全部含碳分支均抵达 `Tier A` 或 `Tier B`；并在表内细分 **`MINERALIZED_STRICT_CARBON_CLOSED`** 即全程零未声明碳损失 vs **`MINERALIZED_DECLARED_BRANCHES_CLOSED`**）；
     2. **`DEAD_END_TP`**（至少一个分支因无合规下一步反应停在非终点中间体，且无环路/步数超限）；
     3. **`CYCLE_ABORTED`**（至少一个分支发生分子重访环路）；
     4. **`MAX_DEPTH_UNFINISHED`**（至少一个分支走到第 15 步仍未进终点池）。
   - **与 `BIOSYSMOdb121` 已知路径的无惩罚双栏对齐指标**：
     - **`Ref-Prefix-Depth` & `Ref-Prefix-Ratio`**：从根污染物起连续命中参考图已知中间体的步深与比例；
     - **`Ref-Node-Recall`（strict / neutral-constitution）**：参考图已知非根主链中间体被模型 `B=1` 推演轨迹覆盖的比例（模型越过参考图终点继续往下开环矿化的步数不计错、不扣分！）；
     - **`Ref-Terminal-Hit-and-Mineralized`**：模型既命中了参考图记录的终末产物，又成功将其一路推演至 `MINERALIZED_CLOSED` 的路径数与占比。

---

## 四、 分步执行命令（执行子代理照书执行）

### Step 1：实现 `mineralization_sink.py` 与单元测试（零网络、零留出集接触）
1. 编写 `/Volumes/CC/Enzyme_Agent/v44/src/pathway_v43/pollutant/mineralization_sink.py`；
2. 编写 `/Volumes/CC/Enzyme_Agent/v44/tests/pollutant/test_mineralization_sink.py`，覆盖全部正负控：
   - **正控**：`O=C=O` (`A_inorganic_carbon`)、`O=C([O-])O` (`A_inorganic_carbon`)、`Cl-` / `O` / `N` (`A0_noncarbon_inorganic`)、丙酮酸 `CC(=O)C([O-])=O`、琥珀酸、富马酸、草酰乙酸、乙酸 `CC(=O)[O-]`、乙酰-CoA、琥珀酰-CoA、甘油醛-3-磷酸、乙醛酸 (`B_central_carbon_sink`)，以及 `NADH` / `ADP` / `CoA-SH` 作为 `coproduct` 时的 `ENDOGENOUS_CURRENCY_COFACTOR`；
   - **负控（必须全部返回 `is_terminal_sink == False`）**：甲醇 `CO`、甲醛 `C=O`、甲酸 `O=CO` / `O=C[O-]`、氰化氢 `C#N`、尿素 `NC(N)=O`、**乙醛 `CC=O`**、**氟乙酸 `FCC(=O)O`**、2-氯琥珀酸、**儿茶酚 `Oc1ccccc1O`**、**原儿茶酸**、**龙胆酸**、**苯甲酸 `O=C(O)c1ccccc1`**、顺,顺-粘康酸、2-羟基粘康酸半醛、3-氧代己二酸、显式顺式马来酸 `O=C(O)/C=C\C(=O)O`。
3. 运行单测确认 100% 绿灯：
   ```bash
   PYTHONPATH=/Volumes/CC/Enzyme_Agent/v44/src \
     /Users/cc/miniconda3/envs/depending43/bin/pytest \
     /Volumes/CC/Enzyme_Agent/v44/tests/pollutant/test_mineralization_sink.py \
     /Volumes/CC/Enzyme_Agent/v44/tests/pollutant/test_v44_next_pipeline.py -v
   ```

### Step 2：发起通道 A `mimo` 规则级化学判据抽审（零金标）
```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43 && \
  opencode run -m opencode/mimo-v2.6-flash-free "$(cat docs/mimo_mineralization_endpoint_review_request_2026-11-11.md)" \
  > docs/mimo_mineralization_endpoint_review_response_2026-11-11.md
```
核对 `mimo` 对 22 个中心代谢白名单分子与负控拦截边界的化学意见；若有与源码互证成立的真实漏口（如辅因子异构体或常见细菌中心汇入物遗漏，且不违背 CC 拍板的 A1/A2/A3 三条铁律），在开跑全量前修补并重跑单测。

### Step 3：Tuning 子集 5 条路径冒烟验证（验证波次驱动、缓存与碳账闭合）
```bash
PYTHONPATH=/Volumes/CC/Enzyme_Agent/v44/src \
  /Users/cc/miniconda3/envs/depending43/bin/python \
  /Volumes/CC/Enzyme_Agent/v44/scripts/eval/run_b121_e2e_mineralization_eval.py \
  --work-dir /Volumes/CC/Enzyme_Agent/v44/reports/ppv1_s5b/b121_e2e_mineralization_20261111 \
  --subset tuning_smoke5 \
  --max-depth 15 \
  --workers 36
```

### Step 4：全卷 121 条路径（`B=1`，最大深度 `15`）正式端到端完全矿化推演与评测
```bash
PYTHONPATH=/Volumes/CC/Enzyme_Agent/v44/src \
  /Users/cc/miniconda3/envs/depending43/bin/python \
  /Volumes/CC/Enzyme_Agent/v44/scripts/eval/run_b121_e2e_mineralization_eval.py \
  --work-dir /Volumes/CC/Enzyme_Agent/v44/reports/ppv1_s5b/b121_e2e_mineralization_20261111 \
  --subset full121 \
  --max-depth 15 \
  --workers 36 \
  --out-summary /Volumes/CC/Enzyme_Agent/v44/docs/reviews/evidence/b121_e2e_mineralization_2026-11-11/e2e_mineralization_summary.json \
  --out-report /Volumes/CC/Enzyme_Agent/v44/docs/reports/B121_E2E_MINERALIZATION_BENCHMARK_2026-11-11.md
```

### Step 5：三道红线门禁扫描与双仓同步
```bash
# 1. 验证公开报告与公开 JSON 零 BIOPATH150_、零 BSY-r、零 API 密钥痕迹
! grep -E "BIOPATH150_[0-9]+|BSY-r[0-9]+|sk-[A-Za-z0-9]{16,}" \
  /Volumes/CC/Enzyme_Agent/v44/docs/reports/B121_E2E_MINERALIZATION_BENCHMARK_2026-11-11.md \
  /Volumes/CC/Enzyme_Agent/v44/docs/reviews/evidence/b121_e2e_mineralization_2026-11-11/e2e_mineralization_summary.json \
  && echo "PUBLIC REDLINE SCAN PASS"

# 2. 验证分集路径加总闭合：76 (Tuning) + 43 (Holdout) + 2 (Non-417 Formal) == 121
/Users/cc/miniconda3/envs/depending43/bin/python -c '
import json
from pathlib import Path
d = json.loads(Path("/Volumes/CC/Enzyme_Agent/v44/docs/reviews/evidence/b121_e2e_mineralization_2026-11-11/e2e_mineralization_summary.json").read_text())
assert d["counts"]["full_121"] == 121
assert d["counts"]["tuning_76"] == 76
assert d["counts"]["holdout_43"] == 43
print("DENOMINATOR CLOSURE PASS:", d["counts"])
'
```
并将新增报告、证据包与同步文档复制到 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/` 对应目录（主树不自动 `git push`）。

---

## 五、 排障表

| 故障现象 | 根因排查 | 标准处置动作 |
| :--- | :--- | :--- |
| 辅酶 A 硫酯（如 `acetyl-CoA`、`succinyl-CoA`）异构或立体表示差异导致未命中白名单 | 不同规则/模板输出的 CoA 泛酰巯基乙胺或核糖磷酸立体标记可能部分省略（flat vs chiral CoA） | 在 `mineralization_sink.py` 中对 CoA 硫酯白名单同时匹配 **去电荷连通骨架 `InChIKey-14`（第一段 14 字符连通块）+ 精确分子式**，并对非 CoA 分子阻断未知芳环，从而既兼容 CoA 立体省略表示，又绝不误放行苯甲酰-CoA（`benzoyl-CoA` 连通块不同，100% 区分）！ |
| 某波次个别底物 LLM API 超时或网关抖动 | 并发请求偶发 `502/504/Timeout` | 单底物内置指数退避重试 3 次；已完成的底物缓存在 `substrate_step_cache/`，重跑命令天然跳过已完成底物。 |
| `opencode` 免费 `mimo` 网关流式中断 | `OpenAI Chat stream ended without finish_reason` | 按 `AGENTS.md` 通道 A 规程执行 `opencode session list` 找回会话并 `opencode run -s <id> "继续输出完整回应"` 续跑 1 次。 |
| 起始污染物本身含 2 个根底物（`121` 条中有 `10` 条） | 分支/汇聚路径在 `step_participants.tsv` 中有 2 个无前驱主链起始物 | 将含碳非货币辅因子的全部起始主链底物一并放入该 `case_id` 的初始活跃分支集合，全部闭合才算该 `case_id` 完全矿化闭合。 |

---

## 六、 回传义务清单

子代理完成后必须向主会话回传：
1. **核心四结局总表（分三栏：`[biosysmodb121·Tuning 76]`、`[biosysmodb121·Holdout 43]`、`[biosysmodb121·Full 121]`）**：
   - `MINERALIZED_CLOSED`（完全矿化闭合数与占比，含严格碳账闭合细分）、`DEAD_END_TP`（半路卡死数与主要卡死反应类型归因）、`CYCLE_ABORTED`（环路熔断数）、`MAX_DEPTH_UNFINISHED`（15 步未完数），以及矿化路径的平均步深与平均分支数；
2. **与 `BIOSYSMOdb121` 参考图的双栏对齐表**：
   - `Ref-Step1-Hit@1`、`Ref-Prefix-Depth`、`Ref-Node-Recall`（`strict` 与 `neutral-constitution`）、`Ref-Edge-Recall`、以及“参考图停在半路（如儿茶酚）但模型继续劈环走完完全矿化”的路径数；
3. **波次收敛统计与完整 Token 账本**：
   - Wave 1–15 每波次活跃底物数、唯一去重底物数、总 LLM 请求数、`input_tokens / output_tokens / reasoning_output_tokens / total_tokens`（价目快照写 `未核实`）；
4. **落盘文件清单与三道门禁核验结果**。

---

## 七、 核心代码附录（`mineralization_sink.py` 骨架规范）

```python
"""PPV1 确定性完全矿化与宿主中心碳代谢终点判定器 (ppv1-mineralization-sink-v1)。

零 LLM、零外部状态、100% 基于 RDKit 分子拓扑与精确连通性身份判定。
严格兑现 2026-11-11 CC 拍板的三道硬门槛：
1. A0 无碳无机物 + A 档直接无机碳 (CO2 / H2CO3)；一碳有机物 (CH3OH/CH2O/HCOOH/HCN/urea)
   与乙醛 (CH3CHO) 显式排除，必须继续氧化至 CO2 或乙酸；
2. B 档宿主中心碳代谢核心白名单 (~22 个 TCA/糖酵解下段/短链酰基-CoA 核心分子)，
   外源毒害基团一票否决；
3. 儿茶酚、原儿茶酸、龙胆酸、苯甲酸等未开环漏斗中间体显式排除，必须开环裂解后汇入中心代谢池。
"""
from __future__ import annotations

from dataclasses import dataclass
from rdkit import Chem, RDLogger
from rdkit.Chem import inchi
from rdkit.Chem.MolStandardize import rdMolStandardize

RDLogger.DisableLog("rdApp.*")

MINERALIZATION_POLICY_VERSION = "ppv1-mineralization-sink-v1"

# 冻结标准中心碳代谢核心池名称 -> 标准中性 SMILES (模块导入时由 RDKit 计算精确 InChIKey-14 + 分子式签名)
CENTRAL_CARBON_SINK_CANONICAL_SPECS: dict[str, str] = {
    # TCA 循环与乙醛酸支路
    "citrate": "O=C(O)CC(O)(CC(=O)O)C(=O)O",
    "cis_aconitate": "O=C(O)CC(=CC(=O)O)C(=O)O",
    "isocitrate": "O=C(O)CC(C(O)C(=O)O)C(=O)O",
    "2_oxoglutarate": "O=C(O)CCC(=O)C(=O)O",
    "succinate": "O=C(O)CCC(=O)O",
    "fumarate": "O=C(O)/C=C/C(=O)O",
    "malate": "O=C(O)CC(O)C(=O)O",
    "oxaloacetate": "O=C(O)CC(=O)C(=O)O",
    "glyoxylate": "O=CC(=O)O",
    # 糖酵解下段与丙酮酸节点
    "glyceraldehyde_3_phosphate": "O=CC(O)COP(=O)(O)O",
    "dihydroxyacetone_phosphate": "O=C(CO)COP(=O)(O)O",
    "1_3_bisphosphoglycerate": "O=C(OP(=O)(O)O)C(O)COP(=O)(O)O",
    "3_phosphoglycerate": "O=C(O)C(O)COP(=O)(O)O",
    "2_phosphoglycerate": "O=C(O)C(CO)OP(=O)(O)O",
    "phosphoenolpyruvate": "C=C(OP(=O)(O)O)C(=O)O",
    "pyruvate": "CC(=O)C(=O)O",
    "lactate": "CC(O)C(=O)O",
    # 短链中心碳汇入点（注意：乙醛 CC=O 不入池，须继续氧化至乙酸或乙酰-CoA）
    "acetate": "CC(=O)O",
    "acetoacetate": "CC(=O)CC(=O)O",
    # 核心短链酰基-CoA 汇入点
    "acetyl_coa": "CC(=O)SCCNC(=O)CCNC(=O)C(O)C(C)(C)COP(=O)(O)OP(=O)(O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1OP(=O)(O)O",
    "propionyl_coa": "CCC(=O)SCCNC(=O)CCNC(=O)C(O)C(C)(C)COP(=O)(O)OP(=O)(O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1OP(=O)(O)O",
    "succinyl_coa": "O=C(O)CCC(=O)SCCNC(=O)CCNC(=O)C(O)C(C)(C)COP(=O)(O)OP(=O)(O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1OP(=O)(O)O",
    "acetoacetyl_coa": "CC(=O)CC(=O)SCCNC(=O)CCNC(=O)C(O)C(C)(C)COP(=O)(O)OP(=O)(O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1OP(=O)(O)O",
}
```
