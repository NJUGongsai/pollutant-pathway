# ppv1-criteria-v3 预注册**草案 v2**：表示层归一（互变异构 14 / 质子化 6）+ 形式归一（盐式 vs 酸式 7）

> ## 状态横幅（全文权威，先读这一段）
>
> - **本文件是草案 v2（2026-10-17 修订）：未预注册、未冻结。** mimo 场景 1 评审**已完成**
>   （`docs/mimo_criteria_v3_scene1_review_response.md`）且回应经主会话互证（含手性负控本地实测），
>   核心意见已并入本版——**先读下方「修订记录（v2）」**。化学同一性判断仍**待师姐确认**。
>   本文件**不产生任何生效口径**；链上任何出数、任何判读、任何对外表述均不得引用本文件为依据。
> - **化学实质判断部分标注「待师姐确认后生效」**：凡涉及"两种写法是否同一化学个体"的判词
>   （§4 档位选择、§5 化学实质待确认点、§6 记录侧"同一反应物"认定），一律以师姐确认
>   为前置；本草案只把判据写成**可判定的规则**，不替师姐做化学裁定。
> - 状态词使用纪律：本文件出现的「冻结」字样仅指**既有文件标题**（如 `*_FROZEN_V1_*`）
>   或**流程名称**（criteria 版本流程），不指本草案；本草案自身的状态词只有
>   **未预注册 / 未评审 / 未冻结**。（如需查既有文件的状态，以其自身头部登记为权威。）
> - 题域标签：**298 = RHEA 通用酶学 / 已见题（post-hoc）**。本文件全部数字挂在该标签下，
>   **不向 dev（B1 环境路径）外推**。
> - 零模型 / 零 API / 零费用：本草案为文档工作，未调用任何 LLM，未跑任何 pipeline，
>   未做可行性跑批。题集核对只做**只读 JSON 读取 + 计数 + 哈希**（命令见附录 B）。
> - 金标与题面零接触：本文件不含任何结构串（SMILES）、不含参考图内容、不含标准答案；
>   题集成员只用**来源文件 + 成员数 + 清单指纹（sha256）**三者钉住，不列 qid 明细
>   （需要明细时按附录 B 命令在来源文件上就地复算）。
>
> 依据（上游，按读取顺序）：`docs/TEACHER_TASK_GONGSAI_LINE_EXECUTION_2026-10-15(1).md` §三.4/5
> （T-D/T-E 定义与"化学同一性判断送师姐确认后冻结实施"）+ §四（收益叙事纪律）+
> `docs/TASK_GONGSAI_LINE_TODO_2026-10-16.md` #4/#5 行 +
> `docs/POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_2026-10-13.md`（结构参照模板）+
> `docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_2026-10-08.md` §1（身份键现状）+
> `docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md` §3.5（互变等价轴的历史落字）+
> `docs/S5B_CNONLY_FORMNORM_ROUND_DELIVERY_2026-10-13.md`（题集与上限口径的直接出处）。

---

## 修订记录（v2，2026-10-17；依据 mimo 场景1 回应 + 主会话互证实测）

1. **档位（§4.2 A-4）**：三轴本轮一律走**披露档（档 A）**；档 B 从"主设计"改为**条件解锁**（三冻结条件，见 A-4 修订版）。
2. **轴 A 诚实命名（§4.2 A-2）**：默认配置下轴 A 应称「互变归一（互变中心立体容忍）」——mimo Q1：判等在逻辑上蕴含"参考侧立体被抹"（14 对预测侧 13/14 无立体却判等，唯一机制即立体描述符被消除）。
3. **手性负控已实测（新证据，准入闸门）**：`docs/review_evidence/mimo_criteria_v3_scene1_2026-10-17/chirality_control_probe.py`——**默认臂（removeSp3Stereo=True）L/D-丙氨酸与 L/D-乳酸全部塌缩（2/2，负控 FAIL）**；立体保留臂（False）0 塌缩（PASS）且真互变（2-羟基吡啶/2-吡啶酮）两臂均救回；远离互变体系的手性不受影响。⇒ 默认配置不得进 strict（mimo Q2 闸门坐实）；档 B 须以立体保留臂为主臂。
4. **双臂设计（§4.2 A-2 增补）**：默认臂与立体保留臂（`CleanupParameters.tautomerRemoveSp3Stereo=False`，bond stereo 按 Sitzmann 保持）同批双跑、分开报数——立体保留臂仍能救回的数量才是"互变救回"的干净口径。
5. **C1 口径修正（§4.4）**：原「19 条 ISOMER-TRUE 配对」在来源数据（`cnonly_repr_classification_data.json`）中**不可复得**（该文件仅含题级计数：ISOMER-TRUE=**23 题**，2026-10-17 实测复算一致）；「19 条配对」无出处，本版一律按 **23 题**表述，旧口径作废。
6. **参数指纹（§3 条 3 / §8）**：指纹 = sha256(算子参数 + tautomerRemoveIsotropicHs / tautomerReassignStereo / maxRestarts + transforms 文件指纹 + **RDKit 版本串**)——canonical SMILES 与互变模板集跨 RDKit 版本可变（mimo Q5 实质缺口①）。
7. **轴间单归属（§6）**：计算上**双轴都算**（A 轴、B 轴布尔各自落披露字段），计数仍单归属——「取先」从顺序依赖的归因变成有证据的归因（mimo Q5 实质缺口②）。
8. **芳香 0 题固定句**：任何对外表述附「本批 AROMATIC-REPR=0，该轴未启用、覆盖未证」；「三类表示差已覆盖」类表述判违规。
9. **含碳质子化对（§4.3 B-6 升级）**：从分子名名单升级为**机读物种规则 + 指纹**（防名单漂移/静默扩围），B 轴披露字段登记每条排除的机读原因；理由补强（mimo Q3）：碳酸体系（CO₂/HCO₃⁻/CO₃²⁻）在 RHEA 里本身就是反应参与物对，归一相等会抹掉真实反应的两侧——不止 V2 相容性问题。
10. **T-E 增补（§5.2 前提 2）**：逐行披露「归一改写了哪些原子（电荷/质子）」，并检查**模板匹配原子是否落在被改原子上**——落在则登记"过度对齐风险"信号行交人工复核。

未改动：题集与指纹（§2 实测复算一致）、fail-closed 公共约定（§3）、V2 正交断言、退出条件框架；师姐确认点 C1/C2/C3 保留（证据面更强）。

---

## 0. 一页总览

| 轴 | 题组 | 作用层位 | 题数 | 性质（叙事纪律分类） | 待裁定人 |
|---|---|---|---|---|---|
| **T-D-A** 互变异构归一 | 互变异构写法差 | 判分侧**身份比较轴**（参考节点匹配） | 14 | 判据修正类 ⇒ 只能表述「测量修正」 | 化学实质：师姐；档位：CC |
| **T-D-B** 质子化写法归一 | 酸式/盐式质子化写法差 | 判分侧**身份比较轴** | 6 | 判据修正类 ⇒ 「测量修正」 | 化学实质：师姐；档位：CC |
| **T-E** 形式归一 | 记录侧盐式 vs 题底物酸式 | **检索/编译侧（记录侧归一）**，判据身份面零触碰 | 7 | 池策略级（非判据级） | 化学实质：师姐；范围：CC |
| 并集 | — | 跨层，**不可相加成一个预期** | **26**（14+6+7 −1 交叉） | 全部为**上限口径**，非命中 | — |

一句话：三组题都能写成规则级判据，但**它们不在同一层**（两组动判分身份轴、一组动检索/编译侧），
因此"26 题"只是三层毛上限的并集，**不是一个 hit@1 预期**；三组各自的判据、正控/负控、
fail-closed 与披露字段在 §4–§6 给出，化学实质待师姐确认、档位与范围待 CC 拍板。

---

## 1. 版本号判定（为什么接 V3）

- 谱系：`..._FROZEN_V1_2026-10-08.md`（V1 身份键 = 冻结的 canonical CXSMILES 稳定哈希，
  电荷敏感、立体敏感）→ `..._V2_PREREGISTRATION_2026-10-13.md`（V2 = teacher T-1 裁定的
  **参与物集合比较豁免**，版本 token `ppv1-criteria-v2`，承载于
  `src/pathway_v43/pollutant/evaluation.py:842-844` 的 `PPV1_CRITERIA_V1/V2` ⇒ 既有
  `PPV1_CRITERIA_VERSIONS` 白名单 `evaluation.py:844`）。
- **本草案取版本号 V3 / token `ppv1-criteria-v3`，理由三条**：
  1. 上游明文要求新版本号：`docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md`
     §3.5 原文「**互变异构等价轴本轮不加**……互变等价升严格身份 = 改判据版本，须 v2 起新评；
     如确需只能作非严格披露轴走评测器版本升级 + 预注册，仍不授 strict」——本草案正是"改判据版本"
     的那一轮。
  2. v2 槽已被占用且语义已定（T-1 豁免；其自身头部为该文件状态的权威）。同名再挂第二套语义
     会让"v2"在批次间指向两套判据，违反"判据变更走 criteria 版本流程"的可追溯要求。
  3. 与 V2 的边界面不同：V2 明写「生成侧零改动、身份键/节点匹配/step_scope 零触碰」，
     只动**集合比较轴**；本草案第一、二组动的是**身份比较轴**（节点匹配），第三组动
     检索/编译侧 —— 承载面不同，须新版本承载并在实现中断言 V2 行为不变（§8）。
- 若 CC/评审判定应改号（例如把 T-E 拆出、或与 V2 合并为一轮），**冻结前调整即可**，本草案
  的判据文本与版本号解耦。

---

## 2. 题集来源与成员核对（只读核对，零金标）

### 2.1 三组题集的实际出处

任务书 §三.4/5 只给题数（互变异构 14、质子化 6、盐式 vs 酸式 7），**未给来源**；经核对，
三组题数**逐一来自 chain12 批次的既有分析**（同一批次：`chain12_s5b_298_v4b_20261012`，
题域 298/RHEA/已见题）：

| 组 | 实际来源（evidence 文件，只读） | 成员定义（机器判据） | 成员数 | 成员清单指纹 sha256 |
|---|---|---|---|---|
| **T-D-A 互变异构** | `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/cnonly_repr_classification_data.json`（人类可读版同目录 `cnonly_repr_classification.md`） | `qids[].qid_class == "TAUTOMER"` | **14** | `337fb836842575921a831e66916241657a76a50926da5b73d0485771062ca0ff` |
| **T-D-B 质子化** | 同上文件 | `qids[].qid_class == "PROTONATION"` | **6** | `8e93b660834335f38351d16366233c1b807c58e4fbd74bb1f41e758d7b8ff84d` |
| **T-E 盐式 vs 酸式** | `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/form_norm_experiment_data.json`（人类可读版同目录 `form_norm_experiment.md`） | `compiled_rows[].qid` 去重（即"对齐恢复后走公开编译入口得到编译候选"的题） | **7** | `dc105d46b42fe838754f8ce7c4dafc7e0d482af6f7575eca4ff856569c04db38` |
| 并集（同批预注册面） | 前两行并集 | 三组 qid 并集 | **26**（含 1 题交叉） | `bd42407d5d7842ccd43a794711f544e3a64bebcf627135083088fd04431358b0` |

- 指纹口径：`sha256("\n".join(sorted(qids)))`，UTF-8；复算命令见附录 B。明细清单**不写入本文件**
  （题集核对只到"题数与来源一致"层面；需要点名时按附录 B 就地打印）。
- 母集可追溯性（同一批次、同一批分析）：
  - T-D-A/B 的母集 = H 桶 cn_only **43 题**（`C2_gap_cn_only_x1` 42 + `C5_gap_cn_only_x2` 1；
    来源 `analysis/hbucket_attribution.json` + `analysis/rescore_detail.json`），43 题指纹
    `33192ab8c0919ed17e4d97364b0d6e912a5d1db4ecb7bcd2663de4cafc2e26e9`；
    其中 AROMATIC-REPR 0 题、ISOMER-TRUE 23 题（21 纯立体差 + 2 骨架/电荷真差）。
  - T-E 的母集 = L1 家族 no_alignment **82 行 / 31 题**（`analysis/noalign_layer_attribution_data.json`），
    中间账 82 → 对齐恢复 64（L1-pure 58/58）→ compiled 10 行 / **7 题**。
- **p0_ambiguity 题集的定位（防串台）**：`reports/ppv1_s5b/p0_ambiguity_2026-10-15/`
  （38 组 / 108 题歧义面）属于**信息饥饿/证据卡那条线**，**不是** T-D/T-E 的题集来源。
  本草案仅把它当作**零金标的成员存在性交叉核**（§2.2）。

### 2.2 核验结果（本草案实际执行，命令见附录 B）

| 核对项 | 结果 |
|---|---|
| 与老师任务书 §三.4/5 题数对应 | **逐项一致**：互变异构 **14** / 质子化 **6** / 盐式 vs 酸式 **7**（三组均有可指认来源文件，非二手转述） |
| T-D-A 成员数 = 14 | **一致**（来源文件 `qid_class=="TAUTOMER"` 计数 14） |
| T-D-B 成员数 = 6 | **一致**（同一文件 `qid_class=="PROTONATION"` 计数 6；含 1 题复合形态题按最深类计入） |
| T-E 成员数 = 7 | **一致**（`compiled_rows` 10 行 → 去重 7 题） |
| 三组并集与交叉 | **并集 26 / 交叉 1 题**（`(A∪B) ∩ C = 1`）⇒ 与来源交付书「毛上限 26 题（20+7−1）」逐字一致 |
| 成员全部落在 298 批次内 | **26/26 命中** `synced/batch_manifest.json`（298 条、qid 唯一 298） |
| 成员全部落在 298 全卷零金标分组内 | **26/26 命中** `reports/ppv1_s5b/p0_ambiguity_2026-10-15/p0_ambiguity_groups.json`（298 行） |
| 是否存在"核对不到"的成员 | **0**（三组均为全命中；无一成员只存在于二手转述） |

> 说明：`chain12` 批次分析文件位于 `reports/ppv1_s5b/`，按仓库 `.gitignore:57` 属
> **本仓不入库**目录；T-E 的逐行原始账（`/tmp/formnorm_probe/formnorm_rows.jsonl`）为
> **易失件**（来源交付书自述），本草案据此把"逐行复算"列为冻结前的必做项（§11 缺口 5）。

---

## 3. 草案的公共约定（三组共用）

1. **可判定优先**：每组判据写成"输入 → 确定性算子 → 布尔结论 + 机读原因"的规则，不写个案罗列。
2. **fail-closed 优先**：任何不可解析、算子异常、参数缺失 ⇒ **不授归一相等**（不猜、不凑、不造数据）。
3. **参数版本化**：所有 RDKit 归一算子及其参数写成常量 + 指纹（sha256），参数改动 = 判据版本升号。
4. **无第三态**：每个被审对象在每条轴上**恰好一个标签**（授/不授），实现内加单归属断言。
5. **披露优先于静默**：归一发生时逐对象机读披露（轴名、归一后身份指纹、参数指纹、原状态标签）。
6. **正控 + 负控缺一不可**：正控过、负控也过，才可作为"判据已就位"的证据；负控任一条失败 ⇒
   该轴停用待审（§10）。
7. **单批不宣称稳定**：本草案全部数字来自 chain12 单批 298 post-hoc 已见题；不得据此宣称
   泛化能力或"机制成立"。

---

## 4. T-D-A / T-D-B：判分侧身份比较轴归一（14 + 6 题）

### 4.1 现状与作用点（实现事实，读码所得）

- 参考节点匹配在 `src/pathway_v43/pollutant/evaluation.py:1369`（`match_reference_nodes`）：
  严格档要求 **两侧严格身份逐字相等**（`evaluation.py:1432` 区域：`pred_strict == ref_strict`，
  `ref_strict = strict_identity_of(参考节点 structure_smiles)`）；不相等但
  `cn_identity`（`src/pathway_v43/domain/identity.py:46`，= Uncharger 电荷归一 + 立体盲 canonical）
  相等 ⇒ 落 `cn_only`（旁证档，**不授严格**）。
- **S5A-01 许可门**（`evaluation.py:1414-1416`）：参考节点声明
  `structure_identity_scope != "strict_structure"` ⇒ 即使内容严格相等也只作 CN 旁证
  （`identity_scope_cap`）。**本草案的任何归一都不得越过这道门**。
- 因此本组轴的性质是：**把部分 `cn_only` 配对提升判据档位**（或仅作披露轴，见 4.4 档位），
  与 V2 的"集合比较轴豁免"是**不同轴**（V2 明写身份键与节点匹配零触碰）。

### 4.2 A 轴：互变异构归一（14 题）

**A-1 适用面**：仅当参考节点 `structure_identity_scope == "strict_structure"` 时，本轴才对
该节点的 `cn_only` 配对生效；`cn_only/partial/unknown` 的节点沿用 V1 封顶，本轴不放宽。

**A-2 归一算子（常量，版本化）**：`TAUTOMER_NORM_V1 = rdMolStandardize.TautomerEnumerator()`
**默认配置**（`maxTransforms=1000, maxTautomers=1000, removeSp3Stereo=True, removeBondStereo=True`，
与 chain12 分类脚本同参），`Canonicalize()` 后取 canonical isomeric SMILES 作为该分子的
**互变归一身份** `taut_id`。参数随本判据版本冻结，改动须升版本号。

**A-3 判定**：双侧可解析且 `taut_id(ref) == taut_id(pred)` ⇒ 该配对标记
`normalized_identity_axis = "tautomer"`；是否据此提升判据档位见 A-4。

**A-4 档位（v2 修订：本轮一律披露档；档 B 条件解锁，不再预选）**：

| 档位 | 判据效果 | 状态（v2） |
|---|---|---|
| **档 A（仅披露轴，本轮唯一启用）** | 归一相等只产出披露档（如 `cn_only_normalized`），**不授 strict、不进 hit@1**；三轴同此 | 与 `docs/POLLUTANT_PATHWAY_S5B_PREREGISTRATION_2026-10-09.md` §3.5「如确需只能作非严格披露轴……仍不授 strict」逐字相符 |
| **档 B（判据档提升，条件解锁）** | 归一相等 **且** A-1 许可门通过 ⇒ 计入 `strict_structure` | **三冻结条件缺一不生效**（mimo Q2 + 负控实测）：①**主臂改立体保留配置**（`tautomerRemoveSp3Stereo=False`；默认臂降为敏感性披露）；②**合成手性负控 0 授**——已实测：默认臂 2/2 塌缩=FAIL、立体保留臂 0 塌缩=PASS（`chirality_control_probe`）；③**师姐对 14 对逐题确认**（C1 判据化：逐对输出原子级溯源——被抹立体原子是否为变换参与原子、在规范互变体中是否仍为 sp3 立体中心） |

**A-5 fail-closed**：任一侧不可解析、`Canonicalize` 抛错或返回空 ⇒ 该配对**不授**归一相等，
逐对机读原因（`normalized_identity_axis_reason`），无第三态。

**A-6 披露字段（草案）**：逐节点/逐配对 `normalized_identity_axis`、`tautomer_param_sha256`、
`normalization_source`（`tautomer_enumerator_default_v1`）、原状态（`strict/cn_only/unmatched`）；
批级汇总 `tautomer_normalized_pairs`、`tautomer_promoted_nodes`（档 B 时）。

**A-7 正控 / 负控矩阵（本轴能否成立的全部证据面）**：

| 控 | 对象 | 期望 | 依据 |
|---|---|---|---|
| 正控 P1 | §2 的 14 题（指纹钉住） | 在只读重算下**逐题归一相等 14/14** | 来源分类报告 `TAUTOMER` 类 14 题 |
| 负控 N1 | 43 题母集中的 **ISOMER-TRUE 23 题全体** | 归一后**必须仍不相等**（尤其其中 21 条纯立体差） | 防"立体擦除冒充互变救回"（见 §5 待确认点 C1） |
| 负控 N2 | 43 题母集中的 **AROMATIC-REPR 子集（0 题）** | 不适用；若重算时非 0 须单列披露 | 本批该类为 0，不得凭 0 宣称"芳香拼写差已解决" |
| 负控 N3 | V2 已登记的豁免面 | v3 启用时 **V2 tier 计数与 v2 逐位一致**（正交性断言） | V2 边界"身份键零触碰"必须保持 |
| 负控 N4 | 参考节点 `structure_identity_scope != strict_structure` 的节点 | 档 B 下**仍不得**升严格 | S5A-01 许可门 |

**A-8 退出条件**：N1/N3/N4 任一失败；或归一被用于洗白机制主张；或本轴被当作"能力提升"对外表述。

### 4.3 B 轴：质子化写法归一（6 题）

**B-1 归一算子（常量，版本化）**：`PROTONATION_NORM_V1` = RDKit
`rdMolStandardize.Uncharger()` **默认配置**（`neutralize=True`），逐组分施加后点号重接；
等价判据 = 归一后 **canonical isomeric SMILES 逐字相等**（**保留立体**）。
**不使用** V1 `cn_identity` 的立体盲归一 —— 立体盲是 cn 旁证档的口径，本轴要的是"同式同构、
仅质子化书写不同"。

**B-2 备选臂必须分开报告**：来源分类脚本的判据是"`Uncharger` 相等 **或** `ChargeParent` 相等
即授"，两臂判据不同、合并即掩差异。本草案要求 **默认只启用 Uncharger 臂**；ChargeParent 臂
仅作**并列敏感性披露**（同批双跑），不作默认。

**B-3 净电荷差 vs 写法差**：归一后仍不相等、且两侧净电荷不同（来源数据中有 1 条同时带立体差）
⇒ **不授**；**禁止**引入"净电荷对齐"策略来扩面（那属检索侧另一工单，见 C-4）。

**B-4 fail-closed**：同 A-5。

**B-5 轴间单归属**：一条配对最多挂一个归一轴标签；两轴同时满足（如"既互变又质子化"）时按
预注册轴序 **A → B** 取先，并**披露双满足计数**（不得静默吞掉另一轴）。

**B-6 含碳质子化对的硬边界（与 V2 相容性）**：V2 §四 对豁免清单有**零碳构造非法断言**，
并登记「CO₂/HCO₃⁻ 是 v2 未来冲突点」。本轴对此**采取同向保守处置**：`CO₂/HCO₃⁻/CO₃²⁻`
等含碳质子化对**默认排除**在本轴之外（fail-closed），并在 §11 缺口 2 登记；若要纳入，
**须先重开 V2 的裁定**，不得由本轮静默绕过。

**B-7 正控 / 负控矩阵**：

| 控 | 对象 | 期望 |
|---|---|---|
| 正控 P2 | §2 的 6 题（指纹钉住） | 只读重算下 Uncharger 臂**逐题归一相等 6/6** |
| 负控 N5 | 43 题母集其余 37 题（14 + 23） | 质子化轴**不得误授**（轴间单归属断言 + 计数披露） |
| 负控 N6 | 含碳质子化对（CO₂/HCO₃⁻ 系） | 必须**不授**（B-6 硬边界） |
| 负控 N7 | V2 豁免面 | 同 N3（正交性） |

### 4.4 化学实质待确认点（**待师姐确认后生效**）

| # | 问题 | 为什么必须有人裁定 |
|---|---|---|
| **C1** | 互变归一算子里 `removeSp3Stereo=True / removeBondStereo=True` 的**立体擦除范围**是否可接受 | chain12 数据里 14 条 `TAUTOMER` 配对的布尔画像为：`stereo_only_difference=True` 14/14、参考侧有立体 14/14、预测侧有立体 1/14、`tautomer_canonical_equal=True` 14/14；而 `ISOMER-TRUE`（**23 题**，题级实测复算一致；原「19 条配对」为来源数据不可复得的旧口径，v2 修正）的画像与之几乎同形（`stereo_blind_canonical_equal=True`、参考侧有立体、预测侧无立体），只差 `tautomer_canonical_equal=False`。⇒ **本轴的"救回"部分来自"立体被擦除"而非"互变异构"**——mimo 判等逻辑论证：预测侧 13/14 无立体却全等，唯一机制即参考侧立体描述符被消除；手性负控实测已坐实擦除覆盖化学稳定手性中心（L/D-丙氨酸塌缩）。判定交给师姐：**逐对原子级溯源**（被抹立体原子是否为变换参与原子、规范互变体中是否仍为 sp3 立体中心）。（来源报告已做 7 题人工读图抽查、8/8 一致，但抽查不覆盖"擦除范围"这一维。） |
| **C2** | 质子化写法差（Uncharger 归一后相等）是否构成**同一化学个体** | 涉及 pKa/生理 pH 下的真实电离态 vs 纯书写习惯；结构性影响 judge 口径 |
| **C3** | 记录侧归一（T-E）后，"酸式底物匹配到盐式记录"是否算**同一反应物** | 决定 T-E 能否立项，以及是否影响 run 身份的缓存/复现口径（见 §11 缺口 5） |

---

## 5. T-E：检索/编译侧形式归一（记录侧盐式 vs 题底物酸式，7 题）

### 5.1 层位声明（关键，防越层记功）

T-E **不在判分身份面**：它归一的是**记录侧（donor）反应物写法**，作用在检索/编译链的
**对齐层**；判据一（分子身份）与 strict 定义**零改动**。来源交付书自身把该项定为
**池策略级**（「记录侧形式归一（检索/编译侧，不动判据）| 池策略级 | 7 题（compiled，产物待验）」）。

### 5.2 判据草案

**C-1 归一算子（常量，版本化）**：`RECORD_SIDE_FORMMORM_V1` = 仅对**记录侧** SMILES 施加
`Uncharger()` 默认配置（逐组分 → 点号重接）；**底物侧不施加**（来源实验的归因臂结论：
64 条对齐恢复**全部**是"仅归一记录侧即可"，底物侧无需归一）；analog 行的原子映射号保留。

**C-2 对齐判据（与编译层同源）**：`s5b_compiler.enumerate_template_alignments` 的
`GetSubstructMatches(lhs, uniquify=False, useChirality=False, maxMatches=64)`；记录反应物
**整侧**（多组分同查）为 query；零匹配 = `no_alignment`。

**C-3 三层口径必须分开报（禁止混报）**：

| 层 | 口径 | 本轮数字（298 标签） | 可否称"命中" |
|---|---|---|---|
| ① 归一后对齐通过 | 候选**行**恢复 | 64 行 / 27 题（L1-pure 58/58） | **否**（上限） |
| ② 走到 compiled | 生成 spec 的行 | 10 行 / **7 题**（corpus 6 + recorded 4） | **否**（上限） |
| ③ 严格命中 | 产物对题验证后进 hit@1 | **本轮 unknown（未验）** | 只有此层可称命中 |

**C-4 不得并入本轴的邻接项（各自独立工单）**：
- NAD(P)⁺ 阳离子型底物 10 行（Uncharger 中和**反而失配**）⇒ 属「净电荷对齐策略」，独立工单；
- 救不动的 18 行（全 analog·L1-candidate：阳离子型 10 + 两侧本就中性 7 + 底物 q=−2 一条）⇒ 不并入；
- 编译层既有拒因（`transform_unmapped`、`stereo_edit_unsupported`、`mapping_enumeration_truncated`、
  `product_set_mismatch`、`partial_dearomatization_inconsistent`、`charge_edit_unsupported` 等
  54 行）⇒ 由既有编译墙处理，本轴不认领。

**C-5 fail-closed / 披露**：归一后新产生对齐但编译拒 ⇒ 拒因原样披露（不得用"归一已恢复"掩盖）；
逐行机读标签 `record_side_form_norm ∈ {applied, not_applicable, failed}`；算子参数指纹随批级输出。

**C-6 正控 / 负控矩阵**：

| 控 | 对象 | 期望 | 来源实验既有结果 |
|---|---|---|---|
| 正控 P3 | 82 行变体在归一后对齐 | 恢复 64 行、其中 L1-pure **58/58** | 已过（须重算复现） |
| 正控 P4 | compiled 行数 | 10 行 / 7 题 | 已过（须重算复现） |
| 负控 N8 | 82/82 变体以**原始形式**重放对齐 | **0 匹配**（忠实复现原始 no_alignment） | 已过 |
| 负控 N9 | recorded/corpus 变体原始 `infer_reaction_mapping` | **全 > 0**（证明原拒因是 no_alignment 而非 no_structure_correspondence） | 已过 |
| 负控 N10 | 既有 strict 结果 | 本轴**不得**改变同批既有 strict 判定（同批前后对照） | 待补（重算项） |

### 5.3 待确认点

- **C3**（§4.4）：归一后的"记录=底物"是否算同一反应物（师姐）。
- **实施前置（工程，非化学）**：记录侧归一改变记录字符串 ⇒ 是否进入 run 身份/缓存 key，
  须在实施设计轮明确（AGENTS「身份与完整性在首次消费时闭合」）；本草案只登记，不实施。

---

## 6. 三轴关系、去重与不可加性

1. **成员交叉**：`(A∪B) ∩ C = 1 题`（可复算，见附录 B）⇒ 并集 26；**26 是毛上限**，不是预期。
2. **层位不同不可相加**：A/B 在判分身份面、C 在检索/编译面；两层的"恢复"不是同一种事实。
   交付书原文即写明合账「基本可加：毛上限 26 题（20+7−1）」且「全为上限口径」。
3. **与 V2 正交**：V2 动集合比较轴（参与物 extras 豁免），本草案动身份轴/记录侧；
   v3 实现必须断言 V2 行为不变（N3/N7）。
4. **与 p0 歧义面不同轴**：108 题歧义面（信息饥饿）与本题集**无成员关系**，不得互相引用计数。

---

## 7. 题集与批次标签（本草案全部数字）

| 项 | 值 |
|---|---|
| 题域标签 | **298 = RHEA 通用酶学 / 已见题（post-hoc）** |
| 批次 | `chain12_s5b_298_v4b_20261012`（三组题集同批；T-E 实验 HEAD `731cfe0a…`） |
| 判据版本现状 | 该批次出数口径为 V1（V2 自 chain13 起承载）⇒ 本题集是**在 V1 口径下**被识别出的表示差 |
| 单批/单 seed 声明 | 本批次为单批实测；小改动判定 ≥3 seed 的要求在本轮**未满足**，不得据单批宣称稳定效应 |

---

## 8. 版本承载与开关（草案，实施前须再过设计轮）

- 新增常量 `PPV1_CRITERIA_V3 = "ppv1-criteria-v3"`，扩展
  `PPV1_CRITERIA_VERSIONS`（`evaluation.py:844`）与 `resolve_criteria_version`
  （`evaluation.py:956`）白名单；非法值仍结构化拒（不猜、不迁移）。
- **缺省 v1 字节不变；显式 v2 行为不变；v3 为显式启用**（新批次经预注册启用）——
  与 V2 的开关形态同构（`evaluation.py:1469` keyword-only `criteria_version`；
  `s5b_scoring.py:203/541` 的批级透传）。
- 承载面：A/B 轴在判分侧（evaluation 输出 + s5b_scoring 批级块）；C 轴在检索/编译侧
  （记录侧归一，属池策略面）。
- **不动**：`PPV1_EVALUATION_VERSION`（`profile.py:396`，评测器 schema 版本）、
  `EDIT_PROTOCOL_VERSION`、`ATOMTOOL_VERSION`、以及 V2 的豁免代码路径。
- 双口径纪律：v3 与 v1/v2 的**同批只读重算并列披露**（rescore 先例
  `scripts/s5b_offline_rescore.py`）；旧批零回写。

---

## 9. 预期（上限口径，非承诺；叙事纪律按老师 §四）

| 面 | 数字（298 标签） | 性质 |
|---|---|---|
| 表示层可救**上限** | **20 题**（互变 14 + 质子化 6 + 芳香 0） | 43 题 cn_only 的分类上限，**非命中** |
| 互变轴单列 | 14 题 | 同上；档 A 下进 hit@1 = 0 |
| 质子化轴单列 | 6 题 | 同上 |
| 记录侧编译候选**上限** | 7 题（compiled） | 产物对题未验 |
| 三层并集毛上限 | 26 题 | 不可加成一个预期 |

- 叙事纪律：A/B 属**判据修正类 ⇒ 只能表述「测量修正」**，禁止表述为系统能力提升；
  C 属池策略级损耗面，须附**同口径修复前后对照**（老师 §四）。
- 任何 hit@1 预期必须等：只读重算 + 正负控全过 + T-H 批跑后的实测；本草案**不承诺任何数值**。

---

## 10. 退出条件

1. 任一负控（N1–N10）失败 ⇒ 对应轴**停用待审**；
2. 归一被用于洗白机制主张 / 被表述为能力提升 ⇒ 停用待审；
3. 含碳质子化对（CO₂/HCO₃⁻ 系）进入 B 轴而未经重开 V2 裁定 ⇒ 视为越界，回退；
4. 参考侧 `omitted_coproduct_scope` 类条款落地导致 V2 废止时，本草案与 V2 的相容性须重评；
5. 重算结果与来源实验数字出现实质背离（如同批 14/6/7 不可复现）⇒ 冻结流程中止并回查。

---

## 11. known gaps（预注册登记，不隐藏）

1. **TAUTOMER 类立体擦除疑点（最高优先）**：见 §4.4 C1。14 条配对的布尔画像与 19 条
   ISOMER-TRUE 近乎同形，差别只在互变归一算子是否把二者合并 ⇒ 本轴成立与否**依赖"擦除
   范围限定在互变中心"**这一化学实质判断，本草案不替师姐裁定。
2. **含碳质子化对**：CO₂/HCO₃⁻/CO₃²⁻ 与 V2 零碳断言冲突，本草案保守排除（B-6），登记不重开。
3. **题集全部抽自 H 桶 43 题 cn_only**：这是**失败样本内部**的分层，不是全卷普查
   ⇒ 20/14/6 全部是**上限**，不能反推全卷表示差规模。
4. **T-E 的 7 题只是"编译候选"**：产物对题**未验证**（来源实验自述"零读取题面/金标，无法
   也不会给命中结论"）；①层 64 行同样只是对齐恢复。
5. **逐行原始账易失 + 单批**：T-E 逐行账在 `/tmp/formnorm_probe/`（易失）；三组题集同批单次，
   无 seed 重复 ⇒ 冻结前须补"来源批次只读重算"作为持久证据。
6. **记录侧归一与 run 身份**：见 §5.3 实施前置，未评估即实施会踩「身份在首次消费时闭合」。
7. **hpc/费用面与本题无关（零模型）**：本草案不产生调用、不产生费用；
   引用上游 chain12 数字时须保留其自身 usage/金额披露口径（不在本文件）。
8. **V1/V2 文本未改写**：本草案不改任何既有 criteria 文档；V2 的实际实现行为以源码与
   其自身证据为准（本草案只引用）。

---

## 12. 下一步（全部为 CC 拍板项，本单只列不做）

| # | 动作 | 责任 | 为什么是 CC 拍板 |
|---|---|---|---|
| 1 | **mimo 场景 1 评审请求另单起草**（自包含、零金标、零结构内容、按 §7 逐条格式） | 另单 | 仓库评审请求模式；本单不做 |
| 2 | **化学同一性判断送师姐确认**（§4.4 C1/C2 + §5.3 C3，逐条列问法） | CC 派发 | 老师 §三.4 明文：师姐确认后才有"冻结实施" |
| 3 | **档位与版本号裁定**（§4.2 A-4 档 A/档 B；§1 版本号是否顺延 V3） | CC | 改判据档位 = headline 定义变化 |
| 4 | **冻结走 criteria 版本流程**（版本号、生效登记、approval_source、双口径并列披露） | CC | criteria 版本流程的法定拍板点 |
| 5 | 冻结后：实现 + 只读重算 + 正负控 + 进 T-H 修复批 | 实施单 | 预注册先于付费；本单不实施 |

---

## 附录 A：三组题集的机器判据与参数（复算所需）

| 项 | 值 |
|---|---|
| A/B 组分类脚本 | `/tmp/cnonly_probe/cnonly_classify.py`（**易失件**；其参数绑定已抄录如下，报告 md 亦载） |
| TAUTOMER 判据 | `rdMolStandardize.TautomerEnumerator()` 默认配置，`Canonicalize()` 后 canonical isomeric SMILES 相等 |
| AROMATIC-REPR 判据 | `Kekulize(clearAromaticFlags=True)` + `SanitizeMol` 后 canonical 相等（自由基电子数不同不授） |
| PROTONATION 判据 | `Uncharger().uncharge` 相等 **或** `rdMolStandardize.ChargeParent` 相等（本草案要求两臂分开报） |
| 配对复刻 | `match_reference_nodes`：`cn_identity(ref) == cn_identity(state.smiles_isomeric)` ⇒ cn_only 配对；43 题全部 `identity_scope_cap == False`、strict 命中 0 |
| 节点类/题类规则 | 节点类 = 该节点全部配对中最浅类（救回 = 任一配对归一后相等）；题类 = 全部 cn_only 节点中最深类 |
| RDKit / Python | `rdkit 2026.03.6`；`~/miniconda3/envs/depending43/bin/python` |
| T-E 归一/对齐 | `Uncharger()` 默认（逐组分、点号重接）；对齐 = `enumerate_template_alignments`（`uniquify=False, useChirality=False, maxMatches=64`）；负控见 §5.2 C-6 |
| T-E 脚本 | `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/form_norm_replay_snapshot.py`（仓内快照） |

## 附录 B：本草案核验命令（只读，零模型零费用；复核人可原样复跑）

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43 && \
~/miniconda3/envs/depending43/bin/python - <<'PY'
import json, hashlib
B = 'reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/'
A = 'reports/ppv1_s5b/p0_ambiguity_2026-10-15/'
dag = lambda l: hashlib.sha256('\n'.join(sorted(l)).encode()).hexdigest()

cn  = json.load(open(B + 'analysis/cnonly_repr_classification_data.json'))
fn  = json.load(open(B + 'analysis/form_norm_experiment_data.json'))
man = json.load(open(B + 'synced/batch_manifest.json'))['entries']
p0  = json.load(open(A + 'p0_ambiguity_groups.json'))['rows']

taut = [q['qid'] for q in cn['qids'] if q['qid_class'] == 'TAUTOMER']
prot = [q['qid'] for q in cn['qids'] if q['qid_class'] == 'PROTONATION']
s7   = sorted({r['qid'] for r in fn['compiled_rows']})
union = sorted(set(taut) | set(prot) | set(s7))

for name, lst in (('TAUTOMER', taut), ('PROTONATION', prot), ('FORMNORM', s7),
                  ('UNION', union)):
    print(f'{name:12s} n={len(lst):3d} sha256={dag(lst)}')
print('A20 x C7 cross =', len(set(taut) | set(prot)) + len(s7) - len(union))
mq, pq = {e['qid'] for e in man}, {r['qid'] for r in p0}
print('manifest n=', len(mq), 'in_manifest=', len(set(union) & mq))
print('p0 rows  n=', len(pq), 'in_p0       =', len(set(union) & pq))
PY
```

**本草案执行结果（2026-10-16）**：
`TAUTOMER 14` / `PROTONATION 6` / `FORMNORM 7` / `UNION 26`，交叉 1，成员在
manifest 298 与 p0 分组 298 中**全命中（26/26）**，指纹与 §2.1 表逐字一致
（如 `TAUTOMER sha256=337fb836842575921a831e66916241657a76a50926da5b73d0485771062ca0ff`）。

---

*草案结束。本文件不构成预注册、不构成冻结、不构成任何化学裁定。*
