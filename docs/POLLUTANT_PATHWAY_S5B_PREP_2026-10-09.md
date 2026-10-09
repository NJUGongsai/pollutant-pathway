# pollutant_pathway_v1 S5b 正式开跑前准备批（题集清点 / 转换规则草案 / provider 接线设计 / 冒烟方案 / 预注册一页选择题）

日期：2026-10-09。实施代理：本批唯一实施会话。仓库
`/Volumes/CC/Enzyme_Agent/dependingv43`，分支 v4.3，HEAD=`c91d557`
（与 S5a 正链终审 R4 审定 HEAD 一致，已推送）。

**定位**：本批是 S5b 正式开跑前的**纯准备文档批**。五任务合一：① 298
题集清点（本批首次触碰真实题面——用户已授权题源"就用我们之前 298
的题"）；② 金标 → 参考图转换规则草案（规则级+合成例）；③ 真实
provider 接线设计（只读调查+设计，不连通不花钱）；④ 冒烟标定方案
（不执行）；⑤ 预注册一页选择题草案。文末列"等用户/teacher 圈定项
清单"。

**本批不做**（硬边界，均遵守）：不执行任何真实模型调用、不花钱、
不启动正式 S5b 评测、不 push、不改任何 src/tests（零代码改动）、
不改冻结判据/S5a 已交付代码、Chenyu 远端只读（且本轮实际零写入零
读取成功——通道阻塞，见 §1.5）、金标内容永不入仓（本报告只含
计数/SHA/字段名/路径/合成例）。

依据：S5 任务书 `docs/POLLUTANT_PATHWAY_S5_SPEC_TASK_2026-10-08.md`
（§5/§7/§9/§10/§13）；S5a 终审
`docs/POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_R4_2026-10-09.md` §8
（题源 298、费用不限已拍板；金标转换规则、通过线、分母/独立性、
预注册口径仍待圈定）；Phase D 复测任务书
`docs/TASK_V43_EC298_PHASE_D_RETEST_298.md` §2（三冻结锚）；
`docs/CHENYU_ACCESS.md`（通道）；`AGENTS.md`（金标/费用/mimo 红线）。

---

## 1. 任务一：298 题集清点结果

清点证据落盘 `docs/review_evidence/ppv1_s5b_prep_2026-10-09/`
（`inventory_shas.txt`：全部重算命令与输出；`inventory_stats.json`：
计数级统计）。金标内容零写入——证据与本文只含
SHA/计数/字段名/路径。

### 1.1 三锚独立重算：全部对上

| 锚（Phase D 任务书 §2） | 重算 SHA256 | 本机命中（全部互为同字节副本） | 判定 |
|---|---|---|---|
| 题卷源 CSV `a3cb7955…` | `a3cb7955c1b9e9c1ae0d70636e9df057a35fc35f311f683835de4f19a02ffd0a` | ① `/Volumes/CC/Enzyme_Agent/ENZYMECAGE_POLLUTANT_REACTION_TEST_298_FINAL_V6_PAYLOAD_2026-09-21/ENZYMECAGE_…_PROVISIONAL_2026-09-21.csv`；② `…/dependingv4/evaluation/enzymecage_v6/…/`（同名 payload 目录） | PASS |
| `questions.jsonl` `9f5955d4…` | `9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c` | ① `…/ec298_phase_a_seal/ec298_gold_readonly/questions.jsonl`（Phase A 封存金标只读件，0444 权限）；② `…/dependingv4/runs/enzymecage298/questions.jsonl` | PASS |
| 运行侧 `exam_inputs.jsonl` `cb5996c9…` | `cb5996c9b960bb4a61fd5747d275077c65ef49bf2cdb74102b9d22dc7f11d703` | ① `…/ec298_phase_a_seal/dependingv43_dev/runs/ec298_v43r1/exam_inputs.jsonl`（首轮封存）；② 本仓 `runs/ec298_pd_retest_pre/local/exam_inputs.remote_copy.jsonl`（2026-09-28 从远端拉回的副本，gitignored）；③④ 同目录 `scratch_identity_C0/D3/exam_inputs.jsonl` | PASS |

（表中 `…` = `/Volumes/CC/Enzyme_Agent/`；全路径见证据文件。）

### 1.2 题数、字段结构与金标位置

- **题数**：`questions.jsonl` 与 `exam_inputs.jsonl` 均 298 行、298 个
  唯一 qid（前缀 `RXNG_`）；两文件 qid 集合与**顺序**完全一致；
  `input_index` 0–297 连续；逐题 substrate_smiles 两文件零不一致。
  题卷 CSV 299 行 = 表头 + 298 题，64 列。
- **`questions.jsonl` 字段**（题面+金标合体文件，金标侧字段加注）：
  `qid`(str)、`category`(str，金标侧)、`substrate_smiles`(str，题面)、
  `products_smiles`(list[str]，**金标**)、`raw_reaction`(str，**金标**，
  298/298 为 `反应物侧 >> 产物侧` 的方向化反应 SMILES)、
  `ambiguous_substrate`(bool)、`fallback_large`(bool)、
  `nucleotide_fallback`(bool)、`n_reactant_components`(int)、
  `n_product_components`(int)。
- **`exam_inputs.jsonl` 字段**（运行白名单，无金标）：仅
  `qid` / `substrate_smiles` / `input_index`——与首轮任务书 §2
  "每行仅有 qid、substrate_smiles 和输入索引"的白名单契约一致。
- **金标存放位置**（S5b 判分时才可打开的含答案文件）：
  本机两份同字节 `questions.jsonl`（Phase A 封存只读件 + dependingv4
  提取产物）；Chenyu 远端权威路径为
  `/usrdata/EnzymeCAGE_data/workspaces/ec298_gold_readonly/questions.jsonl`
  （Phase D 复测判分命令实际使用，见
  `docs/EC298_PHASE_D_RETEST_RAW_RUN_AUDIT_REPORT.md`）；
  `CHENYU_ACCESS.md` §2 所写 `dependingv4_v41/runs/enzymecage298/…`
  与首轮任务书 §1.4 的 2026-09-25 实查记录（该路径当时不存在）存在
  文档间分歧——以复测判分命令实际用过的 `ec298_gold_readonly` 为准，
  远端复核见 §1.5。
- **计数级画像**（不含任何金标取值；详见证据 `inventory_stats.json`）：
  - `products_smiles` 长度分布：1 个产物 253 题 / 2 个 41 题 / 3 个 4 题
    （合计 347 个金标产物分子；空产物 0 题；每个产物条目均单组分，
    底物也均单组分——`.` 分隔 0 例）；
  - 旗标：`ambiguous_substrate` 4 题、`fallback_large` 6 题、
    `nucleotide_fallback` 5 题；
  - 原始反应组分（剥离前）：反应物侧 1–11 组分、产物侧 1–9 组分
    （直方图见证据）；
  - `category` 有 18 个取值，但**最大"取值"是空串（111 题）**——
    即 111 题 category 为空（提取 stats 同证），故 category 不能直接
    当分组键；
  - **底物跨题重复**：298 题只有 209 个去重底物；53 个底物出现在
    >1 题（多出 89 题）。同一底物对应多条不同反应记录——这是
    转换规则 §2.4 与独立性口径的关键输入；
  - **跨题来源记录重叠**：provenance CSV 里 rhea/brenda/union 记录 ID
    无跨题共享，`enzymemap_record_ids` 有 5 个 ID 跨题共享（计数级）。

### 1.3 题卷构造与提取管线（只读核到的事实）

- 题卷 V6 构造（payload 自带 identity/build log/validation，2026-09-21）：
  V5 300 行 − 13 行 A 组（裁定"非降解"）+ 11 行替换（来自 637 池，
  chemistry_audit PASS、microbe confirmed）= 298 行；全卷
  `EXTERNAL_TEST_HOLDOUT`；15 项自校验全过。源数据库计数级画像：
  rhea_record_ids 非空 60 题、enzymemap 190 题、brenda 213 题、
  other 0 题；`unique_source_record_count` 1–155（106 题单一记录）；
  traceability 全 298 行 PASS。
- CSV→`questions.jsonl` 提取：老脚本
  `…/dependingv4/scripts/build_ec298_questions.py`（SHA256
  `d5d1fc4c58072f5ac3b9f2ef3b8f9093bfa74c817edcccebc20bc03766c40dea`），
  2026-09-22 审计修订 1 版（三个 patch：非有机元素剥离、GSH 精确
  SMILES 黑名单、空侧 fallback_large 营救）；剥离对象为无碳/超长
  (>80 chars)/金属络合物/GSH 辅因子（反应物侧共剥 473 项）；
  `products_smiles` = **剥离后的含碳有机产物组分**，底物同理。
  这条事实直接决定转换规则的 participant_list_status（见 §2.3）。

### 1.4 版本歧义：无

对 `/Volumes/CC/Enzyme_Agent` 全盘 `find` 扫描（含深层目录）：
`questions.jsonl` 仅 2 处、`exam_inputs*.jsonl` 仅 4 处、V6 题卷 CSV
仅 2 处（两个同名 payload 目录），**全部与锚 SHA 一致**；不存在任何
异版。无需用户挑版本。

### 1.5 Chenyu 远端只读核验：本轮通道阻塞（如实记录）

按 `CHENYU_ACCESS.md` §1 重建了 /tmp 只读 SSH 助手（expect 封装，
凭证运行时从 `dependingv4/.env.chenyu` 读取，不入脚本正文不入仓）。
实核结果（2026-10-09）：**当前隧道与 PREV 隧道均不通**——经本地代理
(127.0.0.1:7890) 三个通道均 `Connection closed by 127.0.0.1 port
7890`；对隧道域名两个解析出口 IP 直连 22890 端口均 `Connection
refused`（隧道后端不在线；.env 里 HOST/HOST_PREV 双套本就提示通道
会轮换）。**处置**：远端活体核验顺延到 S5b 发车前硬门（发车时按
当日实核重算远端 SHA）；本批以本地多副本互证（含 Phase A 封存只读
件与 2026-09-28 远端拉回副本）为准。本轮对远端零写入（未连接成功，
亦无任何改动意图）。通道恢复配方：CHENYU_ACCESS §1 + `.env.chenyu`
四变量（HOST/PORT/USER/PASS）。

---

## 2. 任务二：金标 → 参考图转换规则草案（规则级，供 mimo 评审 + 用户/teacher 圈定）

消费目标：S5a 已交付的 `ppv1-reference-graph-1`
（`src/pathway_v43/pollutant/reference_graph.py`，S5a 终审 R4 确认
interface_verified_only）+ S5 评测器输入契约（`ppv1-evaluation-3`）。
**每条规则均标 proposed / 待圈定**；真实金标内容不进本节，示例全部
为合成例（下文 §2.6）。

转换的**中间产物纪律**：转换脚本与含金标产物（每题的参考图 JSON，
含真实产物 SMILES）只在 S5b 正式批写 gitignored 目录（建议
`reports/phase_s0_hit60/manual_review/` 同级新目录，如
`reports/ppv1_s5b/reference_graphs/`，进 .gitignore——由 S5b 实施
批提变更，本批不动 .gitignore）；仓内只落计数/SHA/规则文本。

### 2.1 总体形状（proposed）

298 题是单步微生物酶促转化（底物 → 金标产物）。**基本映射：一题
一个参考图对象**，但存在同底物多题（209 去重底物 / 298 题）——两个
候选形状，交用户/teacher 圈定：

- **方案 G1（一题一图，proposed 默认）**：298 个
  `ReferenceGraph`，每个 `reference_graph_id = rg298-<qid 派生稳定
  ID>`；同底物跨题重复时 root_entity 的
  `entity_id` 同、图不同（distinct occurrence 语义天然保留，S5-04
  不按结构首现合并）。分母天然 298 题（与老 hit@K 分母同构，
  结果可比性最好）。
- **方案 G2（一底物一图）**：209 个图，同底物各题转为同一 root 下
  的**多条备选参考边**（S5-02 备选反应保留语义）。分母变 209 根
  底物，指标语义变为"根底物级重建率"，与老 298 分母不同构。
- 差异一句话：G1 答的是"298 条已知反应边各能否重建"，G2 答的是
  "209 个底物各能否给出正确转化集合"。**倾向 G1**（与既有 298 指标
  话语一致、歧义小），待圈定。

### 2.2 根对象（root_entity）（proposed）

- `structure_smiles_raw` = 题面 `substrate_smiles`（均单组分）；
- `strict_structure_identity` = 由 PPV1 既有严格身份机制对
  substrate_smiles 现算（298 题底物全部是显式 SMILES，**不缺结构**，
  不走 §7.2 的 cn_only 有限范围分支）；
- `formal_charge` / `stereo_information_status` /
  `isotope_information_status`：由底物 SMILES 本身确定性派生
  （含未指明立体中心 → stereo_information_status 如实标
  `unspecified_partial` 之类的字符串值；具体字符串表 TBD）；
- `source_refs` = `[qid, global_reaction_id]`（+ provenance CSV 的
  源记录 ID 引用，TBD 是否入图——记录 ID 是来源身份不是金标化学，
  但保守起见同 TBD 一并圈定）。

### 2.3 参考边（每题一条边）（proposed + 三个关键待圈定点）

一题一条边：`from_node_ids=[根节点]`，`to_node_ids=[该题全部金标产物
节点]`。关键字段草案：

- **step_scope（待圈定，mimo 面一）**：候选 `net_reaction` /
  `unknown`。298 反应源自数据库方向化记录（RHEA/EnzymeMap/BRENDA
  的 master/directional 反应），是**总包反应**而非机理基元步。
  proposed：`net_reaction`；理由：数据库记录口径即净转化，标
  `elementary_step` 会过度声明机理，标 `multistep_summary` 又与
  "单步题"的卷面语义冲突。留 `unknown` 作保守选项。
- **共同产物与角色分配（待圈定，mimo 面二）**：`participants` 每项
  `role` 的候选规则：
  (a) **全部金标产物 = `principal_product`**（与老 scorer caliber v3
  "全主产物组分命中"同构——直译旧口径）；
  (b) 按化学常识分主/共（如小分子副产物 CO₂/水/氨标 `coproduct`）——
  需要逐题化学判断，零 LLM 纪律下只能靠规则或人工/mimo 抽审；
  (c) 全部标 `principal_product` 但在 `coverage_statement` 声明
  "主/共未区分"。proposed：(a)（继承已冻结的旧判分口径，最可比、
  零新增判断）；(b) 是更强的化学声明、留给 teacher 升级选项。
- **participant_list_status（待圈定，mimo 面三）**：题面金标产物是
  **辅因子剥离后的含碳组分**（§1.3 事实）。完整 `raw_reaction` 还含
  辅因子/共底物（NAD、ATP、GSH、水、金属等，剥离计数 473 项）。
  候选：(a) `partial` + `coverage_statement` 显式披露"参与物列表 =
  剥离后含碳组分；辅因子/共底物按 2026-09-22 提取规则未列"
  （proposed，如实）；(b) `source_complete`——把 raw_reaction 全组分
  解析进 participants（需要新解析器 + 处理 11 组分大反应，且把共底物
  与金标主产物混列会冲击角色语义）；(c) `declared_complete`——
  仅当 teacher 认定"剥离后列表即该题可判分完整列表"时用。proposed
  (a)。
- `coefficient_status`：`unknown`（题卷无配平系数；proposed）。
- `transformation_ref` = qid 派生；`transformation_signature_status`
  = `unsigned_directional_record` 之类字符串（具体表 TBD）。
- `edge_status`：`observed` vs `reference_only`（待圈定，mimo 面四
  之一）：题卷反应是数据库记录（`recorded` 只表示库中有记录，§7.5
  不自动升格实测）。proposed：`reference_only`（最诚实）；
  `observed` 选项留给 teacher 若认定 V6 卷的 microbe-confirmed 筛选
  构成"已观察"。同理根/产物节点的 `node_status`：proposed
  `reference_only`（全卷统一），候选 `observed`。
- `condition_requirements` = 空列表（298 卷无逐题条件/环境元数据；
  `scenario_scope` = `"rhea_generic_enzymology_no_scenario"` 之类的
  显式串，具体表 TBD）。S5 §5.1 298 题域本就是"RHEA 通用酶学"，
  不带环境场景——这与 dev 题域的 scenario 语义分开，不互推。

### 2.4 source group（研究来源组）（proposed + 待圈定）

S5 §6.2：`source_group_id` 是独立性边界，不等于数据库记录 ID。
298 卷的可用分组材料（全部计数级，不含取值）：global_reaction_id
（题级唯一）、rhea/enzymemap/brenda 记录 ID（enzemap 有 5 个跨题
共享）、gold_accessions/organisms/lineages（微生物身份）、
底物重复（53 底物跨题）、category（111 空取值，不可用）。

候选分组规则（待圈定）：

- **S1：一题一组**（`source_group_id = qid`，proposed 默认）。理由：
  跨题材料重叠极小（rhea/brenda 零共享、enzemap 5 个），且 V6 卷
  构造时每题已是唯一 global_reaction_id；`independence_status`
  对 enzymemap 共享的 5 ID 相关题标 `related`（可选加严）。
- **S2：按底物归并**（53 个重复底物的题并入同组）——把"同底物多
  反应"视为同研究家族，独立性更保守；代价是 CI 有效样本数缩小。
- **S3：按微生物 lineage/菌株归并**——最强保守，但 298 卷的
  microbe 元数据是"文献确认株"聚合，同株≠同研究，可能过度合并。
- proposed：S1（+5 个共享 enzymemap ID 标 related 披露）；S2/S3
  列为敏感性分析选项。**source group 与 G1/G2 形状联动**：选 G2
  （一底物一图）时 S2 天然成立。

### 2.5 known/unseen 轨道（待圈定，mimo 面四之二）

问题：298 题对我们是"已见题"（首轮 2026-09 + Phase D 复测跑过、
分数在案），按 S5 §5.2 应归哪条轨道？

- **选项 T1：轨道 A `known_evidence_reconstruction`（proposed）**。
  依据：(i) 首轮与复测结果已存在且影响了仓内决策——不是对系统的
  未见数据；(ii) 题卷反应源（RHEA/EnzymeMap/BRENDA）与检索语料的
  潜在重叠**未经审计**（首轮任务书 §4 原文披露），不满足轨道 B
  "冻结排除直接证据"的前置条件；(iii) §5.2 轨道 A 定义"允许纳入
  检索支持范围的反应记录"正是 298 卷与语料的现实关系。结论句式：
  "在已见 298 题、冻结配置下的已知证据重建成绩"，与 Phase D 复测
  的 `seen298_post_hoc_repair_check` 标注精神一致。
- **选项 T2：轨道 B `unseen_path_inference`**：需先冻结排除清单
  （把 298 反应的源记录从语料/池中排除并留 manifest），工作量大且
  首轮分数在案的事实仍使其"非未见"。**不建议**，但如实列出。
- **选项 T3：双轨**（主报 A，同时冻结排除清单后跑一小子集 B）——
  费用翻倍、排除实施复杂，列为远期选项。
- 附带：`split_assignment.split` 候选 `held_out`（proposed：PPV1
  本体从未跑过 298）vs `independent_confirmation`（更强声明，但
  旧版本结果在案，独立性存疑）。proposed `held_out` + 披露。

### 2.6 合成例（全部虚构，不含真实金标）

例 A（单产物，最简形状）：

```json
{"schema_version": "ppv1-reference-graph-1",
 "reference_graph_id": "rg298-SYNTH-A",
 "domain": "298", "track": "known_evidence_reconstruction",
 "root_entity": {"entity_id": "synth-root-A",
   "structure_smiles_raw": "CCO",
   "strict_structure_identity": "<由 PPV1 严格身份机制现算>",
   "formal_charge": 0, "stereo_information_status": "no_stereocenters",
   "isotope_information_status": "none", "source_refs": ["SYNTH-Q001"]},
 "nodes": [
   {"node_id": "n-root-A", "state_identity": "<…>", "structure_smiles": "CCO",
    "structure_identity_scope": "strict_structure", "role": "root",
    "occurrence_id": "occ-A-0", "source_group_refs": ["sg-A"],
    "condition_scope": [], "provenance_refs": ["prov-A"],
    "node_status": "reference_only"},
   {"node_id": "n-prod-A1", "state_identity": "<…>", "structure_smiles": "CC=O",
    "structure_identity_scope": "strict_structure", "role": "principal_product",
    "occurrence_id": "occ-A-1", "source_group_refs": ["sg-A"],
    "condition_scope": [], "provenance_refs": ["prov-A"],
    "node_status": "reference_only"}],
 "edges": [
   {"edge_id": "e-A", "from_node_ids": ["n-root-A"],
    "to_node_ids": ["n-prod-A1"],
    "transformation_ref": "SYNTH-Q001",
    "transformation_signature_status": "unsigned_directional_record",
    "participants": [
      {"node_id": "n-root-A", "side": "reactant", "role": "substrate",
       "coefficient": null, "coefficient_status": "unknown"},
      {"node_id": "n-prod-A1", "side": "product",
       "role": "principal_product", "coefficient": null,
       "coefficient_status": "unknown"}],
    "participant_list_status": "partial",
    "coefficient_status": "unknown", "step_scope": "net_reaction",
    "condition_requirements": [],
    "scenario_scope": "rhea_generic_enzymology_no_scenario",
    "provenance_refs": ["prov-A"], "source_group_refs": ["sg-A"],
    "evidence_basis": "database_recorded_reaction",
    "edge_status": "reference_only"}],
 "endpoint_annotations": [], "source_groups": [
   {"source_group_id": "sg-A", "independence_status": "independent",
    "member_records": ["SYNTH-Q001"], "note": "合成例:一题一组"}],
 "split_assignment": {"split": "held_out", "split_rule_version": "synth-v0",
   "route_group_keys": ["SYNTH-Q001"]},
 "coverage_statement": {"covered_axes": ["single_step_net_reaction"],
   "known_gaps": ["cofactors_cosubstrates_stripped_per_extraction_rules",
                  "no_per_question_conditions_metadata",
                  "principal_vs_coproduct_undistinguished"],
   "not_evaluable_node_ids": [], "not_evaluable_edge_ids": []},
 "provenance_manifest": [
   {"provenance_id": "prov-A", "source_group_id": "sg-A",
    "source_origin": "synthetic_example", "evidence_basis": "rule_level",
    "citation_ref": "SYNTH", "structure_match_scope": "strict",
    "observation_scope": "none", "source_conditions": [],
    "independent_status": "independent"}],
 "creation_review": {"review_status": "synthetic_rule_level",
   "reviewer": "s5b_prep_batch", "note": "合成例,非真实题"}}
```

例 B（双产物，演示共同产物保留）：同 A 但 `to_node_ids` =
`["n-prod-B1","n-prod-B2"]`、`occurrence_id` 各 `occ-B-1/2`——
两产物是**同一条边**的产物侧（S5-03 共同产物不被报告 K 删除语义），
不拆成两条边。合成示意：`CCOCC → CCO + CCO`（醚键水解裂解、
共同生成两份同结构含碳产物；两份产物 occurrence 各一、不合并成
一份——纯示意）。合成例分子均经与 298 金标集合做字符串零重叠
核验后选用（教科书级小分子的巧合命中已主动排除）。

例 C（同底物跨题，G1 vs G2 的分叉演示）：两题 qid `SYNTH-Q010/
Q011` 同底物 `CCCCCC`（己烷）不同产物（一题到 `CCCCCCO` 羟化形状、
一题到 `CCCCCC=O` 氧化形状，纯示意）：
G1 = 两个独立图（root entity_id 同、occurrence 不同）；G2 = 一个图
root 下两条备选边（S5-02 备选不合并）。两者的分母与指标语义差异
见 §2.1。

### 2.7 转换后规模（计数级预估，供预注册样本量讨论）

298 图（G1）或 209 图（G2）；根节点 298/209；金标产物节点 347
（G1）；参考边 298（G1）或 209 root × 各自备选边数（G2，边数仍
298）；来源组 298（S1）。逐题深度天然全为"第 1 条反应边"档
（§9.7 深度分层对 298 域只有一档——如实披露，不装出多档）。

---

## 3. 任务三：真实 provider 接线设计（只读调查 + 设计，不执行）

### 3.1 现状（两套并行事实）

- **PPV1（S5b 要用的管线）**：真实模型调用的**记账与闸门骨架已
  交付、发送适配器未接**。`search.py`（ppv1-search-6）的
  `model_requests` 表 + `register_model_request`：`provider_kind ∈
  {real, scripted, fake}`；**real 即时占 `max_real_model_requests`
  额度（默认 0，范围 0–10000，profile.py 十上限之一；失败/超时/
  悬空均占、永不释放）**；状态机 registered → sent（real 计
  `network_request_count=1`，脚本/fake 恒 0）→ responded/failed/
  abandoned。`runflow._model_proposals` 目前消费的是**冻结计划里
  的 scripted 响应文本**（`plan.model.responses`），真实 provider
  默认 off——登记被预算拒 ⇒ 网络发送被阻止（S5-26 纪律的现行实现）。
- **legacy 298 管线（老 298 跑法的真实出口）**：
  `src/pathway_v43/adapters/llm_client.py` 的
  `OpenAICompatibleClient`（OpenAI 兼容 `/chat/completions`，urllib
  零三方依赖）：凭证只从 env 读（`V43_LLM_BASE_URL/API_KEY/MODEL/
  TIMEOUT_S/REQUEST_PARAMS/MAX_HTTP_RETRIES/RATE_GATE`，密钥只在
  内存）；429 有界指数退避+抖动（尊重 Retry-After，封顶 60s）；
  401/403/402 置全局闸门停止；`Idempotency-Key` 头；usage 归一
  （input/output/cached/reasoning tokens）；`sent_at/done_at`
  epoch 供在途重叠核算。`adapters/rate_gate.py` 的 `FileRateGate`：
  跨进程 flock 状态文件（RPM 60s 滑窗预检、TPM 事后记账、429 全局
  冷却、付费停止、批次调用数预算、`in_flight/peak_in_flight`
  原子记账、临时文件+os.replace 原子落盘）。`batch.py` 协调器：
  worker 派生 env 注入（只传 `V43_LLM_*` 键，不落盘不打印）、
  费用账（known-usage 小计 + 缺 usage 不冒充总费用）。
- 老 298 参数身份（Phase D 复测任务书 §1.4 与
  `runs/ec298_pd_retest_pre/local/provider_price_snapshot_2026-09-29.json`）：
  DashScope 北京按量 `ZHIPU/GLM-5.3-Flash`；llm_timeout_s=3600、
  retries=4、reasoning_effort=max；价格快照 2026-09-29：输入
  0.8 元/Mtok、输出 2.8 元/Mtok（thinking 按输出计）、缓存读
  0.23 元/Mtok、RPM 200、TPM 3,000,000、输入上限 1,048,576、
  输出上限 131,072。凭证从 Chenyu 受限 env
  `/usrdata/EnzymeCAGE_data/workspaces/.dependingv43-dashscope.env`
  注入（远端文件，不复制不打印）。

### 3.2 S5b 接线点设计（proposed，S5b 实施批做，本批不改码）

**接线点唯一**：`runflow._model_proposals` 的"取响应"一步
（现为 `self._next_model_response()` 消费计划内 scripted 文本）。
设计：新增一个**real provider 适配入口**（S5b 新代码，走正常代码
评审），把"取响应"替换为：

1. **组 prompt**（proposals 协议：冻结池假设 ID 列表 + novel
   proposal_context/reaction_spec 契约说明；prompt 版本入身份）；
2. **登记**：先 `register_model_request(provider_kind="real",
   purpose="proposals", request_key=…)`——预算在
   `max_real_model_requests` 上显式放开（S5b 预注册冻结值，不再用
   默认 0；额度即 S5-26 的授权闸门：无授权=0=零网络请求）；
3. **发送**：`record_request_sent`（network=1）后调
   `OpenAICompatibleClient.complete`（复用 legacy 客户端整套传输/
   429/闸门/usage 语义，不重写）；携带 `Idempotency-Key`；
4. **记账**：响应/超时/传输失败/孤儿按 model_requests 状态机落
   盘 + usage（缺 usage 保守预留，不冒充已知总额）；
5. **解析**：`record_request_response` →
   `parse_model_proposals`（**同一确定性解析器**，scripted 与
   real 殊途同归——S5a 契约不变）；格式反馈轮走
   `register_format_feedback_round(provider_kind="real")`
   （real 反馈轮同样占额度，受 max_format_feedback_rounds 约束）。

**身份与预算冻结**：request_params（reasoning_effort 等）、
timeout_s、retries、prompt 版本、`max_real_model_requests`、
`max_format_feedback_rounds` 全部进批次身份（PPV1 profile 块 +
run identity 已有这些槽位）；跨身份 resume 逐字段核对拒绝。
**PPV1 的 max_real_model_requests 是逐 run 计的**（每题一个 run），
全局总量由协调器侧的 FileRateGate 批次预算承担——两层预算：run
级（每题真实请求数上限）+ 批级（闸门 max_calls，S5b 预注册冻结；
用户已拍板费用不设上限 ⇒ 闸门不设费用停止线，只保留 401/403/402
付费停止与 429 冷却，issued 计数照记不截断——沿 Phase D 任务书 §3
"不设 issued 停止线"纪律）。

### 3.3 凭证注入（密钥不入仓不入日志）

- 远端跑（推荐，沿老 298）：Chenyu 上 S5b worktree，凭证从
  `.dependingv43-dashscope.env` 只在 worker env 注入
  （`batch.py` 既有 `load_env_file` 只取 `V43_LLM_*` 键）；
- 本地跑（备选）：用户在本地提供同形 env 文件（gitignored），
  通道同 §1.5 需先修好；
- 日志纪律：`real_provider_env()` 只报存在性布尔；任何 stderr/
  报告/证据文件出现密钥即违规（既有测试守门）。

### 3.4 并发控制（目标 80 路在途）

- 用户倾向 80 路并发（问过"能不能开 80 路"）。**机制上可行**：
  老协调器 `max_in_flight` + FileRateGate `in_flight/peak_in_flight`
  原子记账已支持任意目标值；但 80 路在途**从未实测**（Phase D 复测
  目标 40 路的实测峰值是 C0=33 / D-3=32 个提供方正常响应在途，
  见 `docs/EC298_PHASE_D_RETEST_REPORT.md`；工程验收单列）。
- 三个现实约束（如实披露）：(i) **RPM 200 / TPM 3,000,000 是账号级
  共享限速**——80 路在途不等于 80 RPM；按每题最多 3 次真实调用
  （max_llm_calls 同构上限，S5b 待预注册）×298 题的上界估算总
  调用数约 ≤894（加格式反馈轮的余量待冒烟标定）；TPM 窗口按
  thinking=max 的输出 token 率是真正的瓶颈（思考链按输出计费、
  输出上限 131,072 token/请求），TPM 事后闸门 + 429 冷却兜底；
  (ii) 当日 RPM/TPM/价格**发车前必须重新刷新**（2026-09-29 快照只作
  历史记录，Phase D 任务书 §3.1 原纪律）；(iii) 撞限速自动降并发：
  429 冷却窗口全局生效（全部 worker 停发起）即事实上的自动降并发，
  峰值如实记录（`peak_in_flight`），**不为凑 80 发伪请求**（老任务
  书 §3.3 原文纪律沿用）。
- proposed：并发目标 80 在途写进预注册 TBD（60/80/100 三档候选），
  实测峰值与达标与否单列工程验收，不替代科学结论。

### 3.5 费用记账口径（沿老规矩 + 用户"不设上限"）

逐调用记 issued/response/超时/传输失败/孤儿 + usage；缺 usage
保守预留；known-usage 小计与总费用分开（有任何缺失 ⇒ 总额
"unknown"）；运行后以服务商账单回填核对；价格用发车当日快照。
用户已授权费用不设上限——不设停止线、不以费用预估阻断发车，
但记账纪律全部保留（S5 任务书 §4.3 与 AGENTS 红线不变）。

---

## 4. 任务四：冒烟标定方案（不执行，执行等用户看完预注册拍板）

四段递进；**烟测用非 298 合成夹具先做连通/计费检查**（Phase D
任务书 §3.4 纪律），再上正式题（正式题请求即计入正式批次，按同一
身份续跑，不得借 298 看结果后调配置）。

- **段 0（非 298 合成夹具，先花钱最少）**：2–3 个合成底物
  （如 CCO→乙醛形状的假题），走完整 PPV1 链：real 登记占额 →
  发送 → 429/usage 记账 → 解析 → 导出。验收点：网络请求计数=1/
  请求、usage 回填率、费用小计算式、闸门 in_flight 计数、密钥
  零泄漏（全产物扫描）。独立烟测账单列。预算：≤10 次调用。
- **段 1（正式题 5–10 题串行，计入正式批次）**：从冻结 qid 顺序
  取前 5–10 题，串行（并发=1）。测：单题墙钟（3600s timeout 下的
  实际时长分布）、每题真实调用数（decide + 反馈轮）、单题费用、
  解析成功率（proposals 协议 400 形状率）。产出：单题时长/费用
  分布 → 推全量费用与时长（×298，留置信区间，不冒充精确值）。
- **段 2（正式题小批 80 路并发，续同批次身份）**：再取 ~80 题按
  目标并发跑。测：`peak_in_flight` 实测、429 频率与冷却行为、
  TPM 窗口占用率、闸门降并发实际轨迹。产出：并发安全值建议
  （若 80 不可达，如实报实测峰值与原因——老任务书"不为凑数字
  发伪请求"纪律沿用）。
- **段 3（推全量）**：用段 1+2 实测数推全量时长/费用/调用总数
  预估（区间表述），连同并发安全值一起进**预注册冻结值提案**，
  交用户/teacher 拍板后才跑全量。
- 断点续跑/恢复：沿 PPV1 既有 resume 契约（同身份幂等、已持久化
  响应不重复请求、悬空调用记孤儿）+ 闸门状态文件原子落盘。
- 所有段全程 `OMP_NUM_THREADS=1`；远端跑时长任务 nohup 落盘 +
  短连接轮询（CHENYU_ACCESS §1 长任务纪律）。

---

## 5. 任务五：预注册一页选择题草案（全部 TBD，不代定任何值）

按 S5 任务书 §10.1 二十项 TBD 收敛成下表（每项 2–3 候选+一句人话
理由；**本批不圈定任何值**）。编号沿用 §10.1。

| # | 待定项 | 候选（勾选其一） | 一句话理由 |
|---|---|---|---|
| 1 | 主指标 | A. 参考边召回（金标边命中率，hit@1/@3/@5 同构）　B. 关键中间体召回　C. A+B 双主指标 | 298 是单步题，边召回即老 hit@K 的科学化表述；中间体与边在本域几乎同义 |
| 2 | 主指标通过线 | A. 对齐老 298 首轮 116/128/130（scorer v2）附近某档　B. 全新档位（如 TBD%）　C. 不设线只报数 | "过线"必须独立于本轮结果拍板，不能赛后倒推；A 最可比 |
| 3 | 分母规则 | A. 固定 298（失败/unknown/空答/预算漏展开全算未命中）　B. 298 减去参考覆盖不足题　C. 298 减失败题 | A 沿老任务书 §12 放行语义与 Phase D"失败题留分母"；B/C 都是"剔题后命中率"，红线禁 |
| 4 | K 档位 | A. @1/@3/@5 三档全报　B. 只 @3 单档 | A 与历史可比；B 简洁但丢排序信息 |
| 5 | 置信区间方法 | A. Wilson 95%（按题）　B. bootstrap（按 source group 重采样）　C. 只报点值不设 CI | 53 底物跨题重复+enzemap 5 ID 共享 → 简单二项 CI 略偏乐观；B 更贴独立性口径 |
| 6 | 小样本处理 | A. 不足 30 的层标 insufficient_sample 不合并　B. 允许合并相邻层 | A 是任务书 §9.7 原文要求 |
| 7 | 轨道选择（§2.5） | A. 轨道 A known_evidence_reconstruction（proposed）　B. 轨道 B unseen　C. 双轨 | 首轮跑过+语料重叠未审计 ⇒ A 最诚实；B 需先做排除清单 |
| 8 | 图形状（§2.1） | A. G1 一题一图（proposed）　B. G2 一底物一图 | A 分母 298 与老口径同构；B 分母 209 语义变根底物级 |
| 9 | split 标注 | A. held_out（proposed）　B. independent_confirmation | 旧版本同卷结果在案，"独立确证"声明偏强 |
| 10 | 共同产物角色（§2.3） | A. 全 principal（proposed，承旧口径）　B. 规则分 principal/coproduct | A 零新增判断最可比；B 是更强化学声明需 mimo/teacher 抽审支撑 |
| 11 | step_scope | A. net_reaction（proposed）　B. unknown | 数据库方向化记录=净转化；unknown 更保守但丢可判性 |
| 12 | participant_list_status | A. partial+披露（proposed）　B. source_complete | 提取规则本就剥离辅因子；B 需新解析器且混淆角色 |
| 13 | node/edge_status | A. reference_only（proposed）　B. observed | recorded≠实测（§7.5）；B 需 teacher 认定 microbe-confirmed 即"已观察" |
| 14 | identity_scope（匹配侧） | A. 严格结构为主+CN 旁证　B. CN 为主 | PPV1 评测器已按严格分层+cn_only 封顶实现（S5A-01）；A 直接消费；B 与旧判分口径倒挂 |
| 15 | 重复采样 | A. 不允许（每题一次冻结配置）　B. 允许 n=3 报均值 | A 沿"首跑不可因分数改写"；B 费用×3 且需方差口径 |
| 16 | 费用记账 | A. 逐调用+缺 usage 保守预留+账单回填（proposed，沿老规矩）　B. 只记总数 | 用户已拍板不设上限，A 是唯一合规记账；无 B 实质选项 |
| 17 | 并发目标 | A. 80 在途（proposed）　B. 60　C. 100 | 用户倾向 80；实测峰值如实披露，达标单列工程验收 |
| 18 | 失败/超时/孤儿 | A. 全占额度+全留分母+失败题单独表（proposed）　B. 重试后再算 | A 沿 Phase D §3/§4；B 会稀释口径 |
| 19 | 人工化学抽审 | A. mimo 三触发点按 AGENTS 执行（本批 r25 已备请求）　B. 增加逐题抽审范围 TBD | 三触发点已有用户定的纪律；B 的范围留 teacher |
| 20 | 最终状态枚举 | A. 沿任务书 §12 九值枚举（evaluated_* 须全门过）　B. 简化三值 | A 是冻结语义；B 需改任务书 |

另两项前置（不在二十项内但必须先拍）：**P1 预算上限值**
（`max_real_model_requests` 每 run 与闸门批级值——费用不设上限但
**请求计数上限仍需冻结数值**，防失控；候选：每 run 3+2 反馈轮 /
批级 894+冒烟余量，数值待冒烟后定）；**P2 题集冻结确认**
（本批清点三锚对上、无版本歧义——用户确认以 2026-09-21 V6 卷 +
2026-09-22 修订提取产物为 S5b 题源，S5b 发车前再核一次 SHA）。

---

## 6. 等用户/teacher 圈定项清单（本批产出汇总）

1. **§5 表 1–20 全部**（预注册选择题，勾选即冻结）；
2. **P1/P2 两个前置项**（预算数值、题源确认）；
3. **mimo 评审请求 r25**
   （`docs/mimo_ppv1_chem_review_request_r25.md`，四判断面：单步
   边 step_scope / 共同产物口径 / participant_list_status 与辅因子
   剥离 / known-unseen 轨道+recorded 语义）——按 AGENTS 三触发点
   之 1（题源/结构判据冻结前），由用户送 mimo，回复原文落盘
   `docs/`，采信到与程序证据互证为止；
4. **远端通道修复**（§1.5 阻塞——S5b 发车硬门之一；不修则本地跑
   或推迟）；
5. **发车时机**：用户看完本报告+预注册提案+冒烟方案后拍板；拍板后
   顺序 = 冻结预注册 → 段 0 烟测 → 段 1/2 标定 → 全量。

## 7. 提交与证据

- 本批提交（v4.3 本地，不 push）：本报告 +
  `docs/mimo_ppv1_chem_review_request_r25.md` + 证据目录
  `docs/review_evidence/ppv1_s5b_prep_2026-10-09/`。零 src/tests
  改动；评审侧未跟踪文件零触碰；金标内容零入仓。
- 证据目录内容：`inventory_shas.txt`（三锚重算命令与输出、全盘
  版本歧义扫描记录）、`inventory_stats.json`（计数级统计：字段名/
  直方图/交叉核对结论/远端通道阻塞记录）。
- 遵守环境纪律：`~/miniconda3/envs/depending43/bin/python -B`、
  `PYTHONDONTWRITEBYTECODE=1`；清点脚本放 `/private/tmp` 执行，
  不入仓。
