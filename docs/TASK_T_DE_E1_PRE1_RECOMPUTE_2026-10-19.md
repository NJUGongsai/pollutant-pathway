# TASK — T-D/E E1 前置1：来源批次逐行只读重算（执行任务书，2026-10-19）

> **状态**：执行任务书（可直接派子代理；自包含）。
> **题域标签**：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；不外推 dev。
> **性质**：**探针 ≠ 预注册 ≠ 成绩**；零模型 / 零网络 / 零 LLM / 零费用。
> **上游**：`docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V3_2026-10-19.md` §11 缺口 5
> （「逐行原始账易失 + 单批 ⇒ 冻结前须补『来源批次只读重算』作为持久证据」）+
> `docs/TASK_T_G_FIX_ENGINEERING_2026-10-19.md` §3 Step E1 前置子任务 1。
> 本重算**只做证据固化**：不改任何 src/tests/assets，不改任何冻结文本。

---

## 0. 背景（为什么做、做什么）

T-D/T-E 三组题集的冻结数字来自 chain12 批次的**易失脚本**（`/tmp/formnorm_probe/`、
`/tmp/cnonly_probe/`，均已不可依赖）。FROZEN_V3 缺口 5 要求：**在来源批次上逐行只读重算、
把持久证据落进新批次根**。本任务=把两套账重新算出并对锚：

- **账 1（T-E，82 行 / 31 题）**：记录侧形式归一的**对齐恢复账**（P3=64 行恢复、L1-pure 58/58）
  与负控（N8 基线 0 匹配、N9 映射基线 >0）；P4（compiled 10 行/7 题）按现行编译器口径
  如实重出（来源数字与现行口径若背离，**如实披露 + 归因**，不掩饰）。
- **账 2（T-D，A/B 轴 43 题母集分臂重算）**：14 题 TAUTOMER + 6 题 PROTONATION + 23 题
  ISOMER-TRUE 的**配对级分臂布尔**（默认臂 / 立体保留臂 / Uncharger 臂 / ChargeParent 臂）
  → P1/P2 待验值定数 + N1 负控 + B-5 双轴布尔预览 + 参数指纹（R03 要求的历史环境实测登记）。

## 1. 新批次根与产物

- 批次根：`reports/ppv1_s5b/t_de_e1_2026-10-19/pre1_recompute/`（新建，gitignored）；
- 产物：`pre1_recompute.py`（脚本）、`te_recompute_data.json`（T-E 机读）、
  `td_arms_recompute_data.json`（T-D 机读）、`pre1_recompute_summary.md`（报告）、
  `pre1_recompute_run.log`（日志：HEAD/命令/输入 sha256/耗时）。
- **输出纪律**：所有产物**零结构串**（不写 SMILES；布尔/计数/qid 头哈希/原因码/指纹即可）；
  逐行对账用 `qid` 或 `qid[:16]+record_key` 定位，不落结构内容。

## 2. 账 1：T-E 对齐恢复账（82 行 / 31 题）

### 2.1 行来源（持久）

- 权威行账：`reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/form_norm_experiment_data.json`
  的 `per_row_ledger`（82 条：qid/channel/record_key/disposition/outcome/method/reject_reasons）；
- 底物：`synced/batch_manifest.json` entries → `qid → substrate_smiles`；
- 记录侧变体重建：**逐字照抄**同目录 `form_norm_replay_snapshot.py` 的 `variants_for()`
  与资产加载（`library_full.jsonl` / `corpus_v1.jsonl` / `corpus_templates_v1.jsonl`，
  见该脚本 §assets）；
- 交叉核对：82 行/31 题；`by_channel` 应= recorded 17 / corpus 27 / analog 38；
  `L1-pure 58 / L1-candidate 24`；与 `noalign_layer_attribution_data.json` 的
  matrix L1-pure+recorded 17/corpus 27/analog 14 与 L1-candidate analog 24 对账
  （注意 matrix 的 L1-pure analog=14 与 ledger 的 58 总分口径关系，如实注释）。

### 2.2 归一口径（照抄来源实验，不改写）

- 主臂：`rdMolStandardize.Uncharger()` 默认配置（`neutralize=True`），**逐组分**施加后
  canonical SMILES 点号重接；analog 行**原子映射号保留**（`strip_map` 只用于对齐变体的
  donor 还原，映射原样进编译）；
- 次级臂：`ChargeParent` 逐组分（仅作并列敏感性，**不进主账**）；
- 对齐判据（**legacy 复现口径**）：`enumerate_template_alignments`（全供体匹配）已随
  s5b-compiler-4（C2 R2'）从 src 移除——**逐字 vendor 旧函数**：
  `git show 838f307^:src/pathway_v43/pollutant/s5b_compiler.py` 中
  `def enumerate_template_alignments(...)`（487-499 行）与 `_COMPILE_ALIGNMENT_LIMIT=64`；
  在脚本内注明「vendored verbatim from 838f307^（C2 前基线）」；
- 编译入口（**现行口径**，只读 import src）：analog→`compile_donor_template`；
  recorded/corpus→`compile_recorded_reaction`（来源实验同款调用参数，见快照脚本
  `run_arm`；`norm_side(mapped_lhs/mapped_rhs)` 用归一后字符串）。

### 2.3 必出读数（对照锚）

| # | 读数 | 锚（来源实验账，须对账） |
|---|---|---|
| P3 | 归一（记录侧）后对齐恢复行数 / 题数；L1-pure 恢复率 | **64 行 / 27 题；L1-pure 58/58**（分通道 recorded 17/17、corpus 27/27、analog 20/38） |
| P4 | 编译候选行数 / 题数 | 来源数字 **10 行 / 7 题（recorded 4 + corpus 6）**——按**现行编译口径**重出并对照；背离逐行归因（前提：C1/C2 已替换对齐判据，属**已登记工程变量**，如实说明） |
| N8 | 82 行原始形式（donor 原样 vs 底物原样）对齐匹配数 | **全 0**（82/82） |
| N9 | recorded/corpus 变体原始 `infer_reaction_mapping` | **全 > 0** |
| 附加 | 归因臂：仅记录侧归一（ru）/ 仅底物归一（su）各自匹配数 | 来源：64 条恢复**全部可由仅记录侧解释**；如实重出 |
| 附加 | 现行口径三读数 | 对 82 行，按现行 src 出三档：①基线（原样）②仅记录侧归一（**发货口径**）③双侧归一（uu 参考）——各自 compiled 行/题 + reason 迁移表 |

### 2.4 P4 背离处置（预先写死，不得临场自圆）

若现行口径 P4 ≠ 10/7：在报告中**单列披露表**（差异行、旧口径结局 vs 现行口径结局、
归因=对齐判据替换/C1/C2 边界/其它），标注「来源实验数字（冻结文本 §5.2 C-3 ②）与现行
口径读数的口径差」；**不改冻结文本，不改来源账**。若无法归因 ⇒ 停下报主窗口。

## 3. 账 2：T-D A/B 轴分臂重算（43 题母集）

### 3.1 配对来源（只读、金标内容进程内消费，零外写）

- 题集与类别：`analysis/cnonly_repr_classification_data.json`（43 题=TAUTOMER 14 +
  PROTONATION 6 + ISOMER-TRUE 23；全部 `identity_scope_cap=False`、strict 命中 0）；
- 配对结构：从 chain12 批次只读导出重建 cn_only 配对——沿 `scripts/s5b_offline_rescore.py`
  的离线读取通道（`synced/runs/<run_id>/native_export/<digest[:24]>/{manifest.json,payload.json}`
  + manifest 的 `graph_rel` 参考图；run_id 由 batch_manifest entries 按 qid 取）；
- 配对判据：镜像 `match_reference_nodes`——`pred_strict != ref_strict ∧ cn_identity 相等`
  ⇒ cn_only 配对（43 题 scope 无 cap；解析失败按 fail-closed 剔除并计数）；
- **交叉锚**：重算的逐配对 `tautomer_canonical_equal`（默认臂布尔）必须与分类文件
  `pairs[].tautomer_canonical_equal` **逐对相等**（对不上的配对逐条披露——这是重算
  正确性的第一道自检；<100% 一致即停下报主窗口）。

### 3.2 分臂算子（常量按 FROZEN_V3 文本，不得改写）

- **A 轴默认臂**：`TautomerEnumerator(CleanupParameters(maxTransforms=1000, maxTautomers=1000,
  removeSp3Stereo=True, removeBondStereo=True))`（= 与来源分类脚本同参）→ `Canonicalize()`
  → canonical isomeric SMILES 相等；
- **A 轴候选主臂（立体保留）**：同上但 `removeSp3Stereo=False`；`removeBondStereo` 保持默认
  `true`（未核范围）→ 独立布尔；
- **B 轴 Uncharger 臂**：`Uncharger()` 默认配置逐组分+点号重接 → canonical isomeric SMILES
  （**保留立体**）相等；
- **B 轴 ChargeParent 臂**：`ChargeParent` 逐组分 → 同比较（仅敏感性披露）；
- fail-closed：任一侧不可解析/算子异常 ⇒ 不授相等 + 逐对机读原因，无第三态。

### 3.3 必出读数

| # | 读数 | 说明 |
|---|---|---|
| P1 | 14 题 TAUTOMER：**分臂**归一相等计数（pair 级 + 题级「任一配对相等」） | 待验值（来源分类=默认臂口径；立体保留臂救回数**未证**→ 本次定数） |
| P2 | 6 题 PROTONATION：Uncharger 臂 / ChargeParent 臂**分开**计数 | 待验值（来源为 OR 并集口径；单臂 6/6 未证） |
| N1 | 23 题 ISOMER-TRUE（21 纯立体差 + 2 其他真差）：两 A 臂**必须全不相等** | 任一相等 ⇒ **停**，报主窗口（这是我方口径错误的强信号） |
| N2 | AROMATIC-REPR 子集题数 | 来源=0；非 0 单列披露 |
| B-5 预览 | 43 题母集逐配对四布尔（A_默认/A_立体保留/B_Uncharger/B_CP）→ 矩阵计数（含 A∧B 双满足计数） | 供实施轮单归属 A→B 设计与披露数对照 |
| 指纹 | 各臂实际生效参数（含未显式设置项 `tautomerRemoveIsotopicHs`/`tautomerReassignStereo`/`maxRestarts` 的**实测有效值**——从 RDKit 对象/`CleanupParameters` introspection 取）、transforms 文件哈希（RDKit 数据目录 `tautomerTransforms.in`）、RDKit 版本串 → 分臂 `param_sha256` | R03 要求的历史环境实测登记（**不得以文档语义替代**） |

## 4. 红线与纪律

1. 只读：不改 src/tests/assets/封存批次文件；产物只写 §1 批次根；`PYTHONDONTWRITEBYTECODE=1`；
   长跑脚本可复制到隔离 tmp 执行（沿「审核证据在隔离目录执行」纪律），但**产物必须落批次根**；
2. 金标/题面内容（参考图结构串、底物结构串）**只在进程内消费**：任何产物文件（json/md/log）
   零结构串；报告里的逐行定位只用 `qid[:16]+record_key+布尔/原因码`；
3. 记录实际 HEAD（`git rev-parse HEAD`）、分支、Python/RDKit 版本、每个输入文件的 sha256；
4. 锚对不上（P3/N8/N9/交叉锚/§3.1 交叉一致）⇒ **停**，报主窗口，不得改口径；
5. 提交纪律：不 git add / 不 commit / 不 push（产物 gitignored）。

## 5. 回传三件套

1. 行数/清单集合：82 行逐行 outcome、43 题逐题布尔聚合（按通道/类别分列）；
2. 锚对账表：P3 / P4（+背离归因）/ N8 / N9 / §3.1 逐对交叉一致率 / N1 / 指纹；
3. 发现与风险清单：任何与 FROZEN_V3 文本数字的差异（逐项给机械原因），
   以及「现行口径 vs 来源数字」的口径差汇总（供 E1 实施任务书消费）。