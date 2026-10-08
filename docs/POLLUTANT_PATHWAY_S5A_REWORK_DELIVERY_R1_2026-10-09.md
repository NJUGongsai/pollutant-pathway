# pollutant_pathway_v1 S5a 回修 r1 交付书

日期：2026-10-09（Asia/Shanghai）。实施：S5a 回修 r1 唯一实施代理。
基线：`2e1e7af3c4bef9e98db9481167a835cabd3c088e`（直接父）。
范围：评审 `docs/POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_2026-10-09.md`
§4 四组 P1（S5A-01/02/03/04）有限收口；S4/S3、ISO-01 保持关闭，
不实施 S5b；不触金标/题面/封存 run/v4/原 v3 评价资产；零外部模型、
判分零 LLM、零网络、零费用、不 push。

**状态口径**：本轮只收工程接口缺口。科学状态仍由用户/teacher 按
预注册裁定；本交付不产生任何 dev/298 科学性能声明（工程数字不
外推 dev/298）；`interface_verified_only` 只是程序模式标志。

---

## 1. 入口与消费事实矩阵（validate / load / match / evaluate / aggregate / persist）

| 入口（模块 `src/pathway_v43/pollutant/evaluation.py`） | 事实消费 | 本轮变化 |
| --- | --- | --- |
| `validate_evaluation_input`（validate） | §8.1 必填字段/枚举/版本绑定（evaluator/export schema）；混合题域/轨道拒绝（S5-21/22）；lossy 投影契约 | 不变 |
| `validate_split_manifest` / `check_leakage`（validate/aggregate 前置） | §6.3 划分/防泄漏；失败 ⇒ blocked_leakage 零聚合 | 不变 |
| `native_export_reader_from_ledger`（load） | §3.1 S4 公开入口 `read_native_export` 首消费（integrity→版本→digest→权威引用→策略→staleness） | 不变 |
| `match_reference_nodes`（match） | 参考节点 × 导出 states（`strict_identity_of`/`cn_identity` 与生产同源）；distinct occurrence 保留 | **S5A-01**：先消费 `structure_identity_scope` 许可再授严格档 |
| `match_reference_edges`（match） | 逐参考边：from/to 严格命中集 → 候选事件（step_scope/参与物覆盖分轴；备选不合并；共同产物保留） | **S5A-03**：逐声明必要节点核严格命中，空集不入 union |
| `classify_condition_requirement` / `classify_sample_conditions`（evaluate） | 参考条件要求 × 导出 contexts 的 condition_facts | **S5A-02**：登记 ConditionScope→冻结 Requirement/事实映射，消费 `path_context.aggregate_environment_fit` 同源规则（同根闭合） |
| `check_endpoint_claims` / `budget_omission_from_export` / `depth_metrics_from_export` / `unknown_partial_summary_from_export` / `outside_reference_edges_from_export`（evaluate） | §9.3–9.8 分轴披露 | 不变（P2 面不本轮收口，见 §6） |
| `evaluate_scientific`（aggregate） | 串联 §11 流程；`_aggregate_metrics` 按 match_status 桶聚合 | 语义不变（S5A-01/03 新状态 `unmatched_required_node_uncovered`、S5A-02 新桶 `condition_unsupported_key`/`requirement_status_not_representable` 自动流入聚合分桶） |
| `persist_evaluation_output`（persist） | S5-27 金标写入守卫 | **S5A-04**：核验与写入同一解析后实际规范路径 |

四同根规则同源闭合点：条件规则 = `path_context._assess_requirement`（冻结判据四实现；评测侧直接 import `aggregate_environment_fit`/`build_requirement`/`build_condition_fact`，不另写第二套）；身份规则 = `chemstate.strict_identity_of` + `domain.identity.cn_identity`（生产同源）；泄漏/状态/零 LLM/provider 面 = 不变。

## 2. 契约版本登记变化

| 契约 | 之前 | 本轮 | 承载 |
| --- | --- | --- | --- |
| `ppv1-evaluation-1` | S5a 首批 | **ppv1-evaluation-2** | S5A-01 匹配语义（scope 许可）+ S5A-02 分类语义（同源条件规则）+ S5A-03 匹配语义（必要节点闭合）+ S5A-04 写侧语义（同一实际路径）——匹配/分类/写侧语义变更不偷换同一已登记契约 |
| `ppv1-preregistration-template-1` | S5a 首批 | **ppv1-preregistration-template-2** | proposed 文字与实现证明范围同步（仍 proposed 不冻结；identity scope 许可、必要节点闭合、条件同源口径、写边界根规则、角色/系数状态集合口径、unknown==unknown 实现披露限定、新增 `output_write_boundary_policy` proposed 块） |
| `ppv1-profile-20` | S5a 首批 | **ppv1-profile-21** | 身份块携带 evaluation-2 / preregistration-template-2 |
| `ppv1-reference-graph-1` / `ppv1-split-manifest-1` | S5a 首批 | 不变 | 字段形状零变化（scope 许可是消费侧语义，由 evaluation-2 承载） |
| 判据一–五 / 0d–0h / store / runflow / endpoint / native-result / native-export / v3-projection | — | 全部不变 | criteria-v1 冻结正文 SHA `7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4` 与 FREEZE_RECORD SHA `6e046e2970a102c63e693cebb81f2564b5d79fea1b6a7a776b0fc00c09662610` 逐字节复核一致（未动） |

改动文件（git diff 全集，legacy/G2/AtomTool/export_v3/production 零触碰）：
`src/pathway_v43/pollutant/{evaluation,preregistration,profile}.py`（+707/−124 行）
与 4 个既有测试文件的字面量/断言更新，加新回归
`tests/test_ppv1_s5a_rework_r1.py`（42 用例）。

## 3. 逐 P1：入口 → 行为 → 正负控 → 证据 → 有限残留

### 3.1 S5A-01 参考身份 scope 先消费许可，再授严格档

- **入口**：`match_reference_nodes`（evaluation.py；边/聚合经
  `strict_by_node` 与 `match_status` 桶自动传导）。
- **行为**：`structure_identity_scope ∈ {cn_only, partial, unknown}`
  ⇒ 许可封顶——内容严格相等也只作 CN 旁证（`match_status=cn_only`，
  旁证 state 并入 `cn_only_state_ids`，机读 `identity_scope_cap`
  披露 `content_strict_equal_state_ids`/`capped_to`）；不授
  `strict_structure`、不进 `strict_by_node`/边严格候选/严格指标。
  scope=`strict_structure` 才允许严格档；真实 CN 旁证（对映体/
  同位素/电荷）与合法 strict 控制保持；不全面拒绝带标签或有限图
  （样本仍 scored、条目保留）。
- **负控翻转**（评审 identity 六 scope 案逐案）：
  `reference_intermediates_{cn_only,partial,unknown}` 与
  `reference_all_{cn_only,partial,unknown}`：修复前每案中间体（或全
  部节点）`strict_structure`、两备选边 `matched_strict`、聚合
  `matched_strict=2`；修复后节点 `cn_only`（封顶披露在场）、边
  `unmatched_required_node_uncovered`、聚合 `matched_strict=0`。
  节点→边→聚合逐层翻转（key_intermediate_recall 严格档同样归零、
  cn_only 档计数 2）。
- **正控保持**：`strict_control`（合法完整图）两条边 `matched_strict`
  聚合 2 保持；`strict_mismatch_isotope/charge`（真实严格差异）节点
  `cn_only`、边不严格保持；stereo 单元控制保持；5 个节点条目/
  occurrence 全保留。
- **证据**：`docs/review_evidence/ppv1_s5a_rework_r1_2026-10-09/
  probe_before|probe_after/`（六 scope 案完整输入/输出/DB 快照）、
  `probe_flip_result.json` 6 项 scope 检查全过；回归
  `test_s5a01_*`（7 用例：六 scope + 单元许可差）+ 正控
  `test_s5a01_legal_strict_and_real_cn_controls_kept`。
- **有限残留**：`_pair_exports_to_samples` 的样本↔导出配对仍按根
  实体严格内容身份配对——配对只做样本关联不授任何严格指标（根
  节点匹配仍由 `nodes[]` 的 scope 封顶管辖）；root_entity 侧
  `identity_scope` 声明目前只由 schema 层强制（§7.2），不参与配对
  判定（P2 表示语义，见 §6）。

### 3.2 S5A-02 条件分类沿冻结同源规则（登记映射）

- **入口**：`classify_condition_requirement`（公共）与
  `_classify_condition_requirement_detailed`（详细：分类 + 冻结
  reason 码 + 机读映射披露）；`classify_sample_conditions` 端到端
  消费。
- **登记映射**（`_map_condition_scope_to_requirement` /
  `_build_frozen_facts`，映射限定机读披露）：key 须在冻结条件键集；
  level→Requirement.level；区间键（pH/temperature_C）`lo-hi` 字符串
  规范为 `{lo,hi}`（range）、单数值为点值（point）、其余字符串按
  定性标签（label，注册表为空 ⇒ 冻结侧 unknown）；物种/枚举/matrix
  键字符串按 entity；要求侧声明单位参与消费（非规范/未声明 ⇒
  机读披露 + unknown 族，首版无换算）；`source_refs` 原样映射；
  `subject_scenario_ref` → 评估场景（事实按冻结适用性规则过滤）。
  缺表示能力 ⇒ unknown/unsupported 族 + 机读披露（不发明 label 库/
  换算/负要求/必要性）。
- **同源规则消费**：`aggregate_environment_fit`（冻结判据四实现）
  裁决单位三态、实体/数值/异值 absence、多事实保守 unknown、
  necessity 来源、适用场景/阶段、声明 value_basis；评测侧不再有
  字符串首条/`or ""`/字符串区间解析的第二套规则（旧
  `_value_matches` 已删除）。
- **18 可比 case**（评审 conditions 20 案同案构造，保留映射限定）：
  5 同义正控保持（missing_fact→unknown、same_present→compatible、
  opposite_present→essential_conflict、same_absent→essential_conflict
  （冻结 `required_value_known_absent`）、canonical_unit→compatible）；
  13 分歧全部翻转为冻结结果：异值/数值/异实体 absence →
  condition_unknown（`other_value_known_absent_not_determining`/
  `numeric_absence_semantics_undefined`/`entity_not_among_known_
  facts`）；温度无单位/K/F → condition_unknown（`source_unit_
  unknown`/`unit_mismatch`）；矛盾事实正/反序 → 双向
  condition_unknown（`conflicting_applicable_facts`）；necessity 无
  源 → condition_unknown（`necessity_unsourced_not_gating`）；零点/
  负区间/区间 dict → compatible（`point_match`/`within_range`）；
  matrix 未注册标签 → condition_unknown（`matrix_value_unresolved`）。
- **2 required_absent 案**：单列新桶
  `requirement_status_not_representable`（冻结 Requirement 无负要求
  表示；机读披露 kind 同名；不伪称冻结矛盾、不推断负要求——参考
  schema 语义待用户/teacher 裁定，评测侧不代定）。
- **正控保持**：preference 永不门禁（不满足 ⇒
  `preference_unsatisfied`，满足 ⇒ compatible，经同源值轴探针）；
  `scenario_transition_changed` 桶保持（现消费全部同键事实，不再
  首条说了算）；历史来源条件原样保留（S5-15）。
- **证据**：`probe_before/conditions_summary.json`（20 案公开桶 vs
  冻结同源逐案对照，修复前 13 分歧）→ `probe_after/`（20 案全部与
  冻结同源一致）；`probe_flip_result.json` 20 项条件检查全过；回归
  `test_s5a02_*`（24 用例：20 案参数化公共分类器 + 冻结 reason/
  披露 + 缺表示能力四型 + preference/scenario 轴 + 端到端多事实/
  单位不匹配）。
- **处置路线**：按 §8-02 登记映射 + 沿冻结同源规则 + 缺表示能力
  机读披露路线（未走"评测侧独立口径"，未改冻结正文；若 teacher
  另选独立口径须另行裁定/独立版本/分歧报告）。
- **有限残留**：冻结键集外的条件键（如参考图自造键）→
  `condition_unsupported_key`（unknown 族，机读披露冻结键集清单）；
  事实条目无法冻结表示（如 oxygen 枚举外值、区间键字符串值）⇒
  跳过 + 披露（该键按缺事实保守 unknown）；要求侧
  `status=known_present` 之外的 `unknown` 早退保留。既有端到端夹具
  的 `redox_regime`（键集外）从 `condition_unknown` 改桶为
  `condition_unsupported_key`（unknown 族语义不变；测试同步更新并
  披露）；既有单元夹具的 pH 事实值由字符串 "7" 改数值 7（冻结契约
  区间键事实须数值/区间形状）、missing-fact 案改用冻结键
  `electron_acceptor`（保持 S5-13 缺事实 ⇒ unknown 语义）。

### 3.3 S5A-03 声明必要 from/to 参考节点空命中不被 union 吞

- **入口**：`match_reference_edges`（evaluation.py）。
- **行为**：逐边逐声明节点核 `strict_by_node` 命中；任一必要
  from/to 节点无许可严格命中 ⇒ 该边不产生严格候选（候选块整体
  跳过——空集合不并入整侧 union、不被删除）；状态落
  `unmatched_required_node_uncovered`（未覆盖分桶，不判错、不冒充
  已匹配）；逐节点机读 `required_node_gaps`（node_id/side/
  node_match_status）恒输出（空列表 = 无缺口）。参与物覆盖比较因此
  消费完整声明节点集合（不能只证明缩小子集精确）。
- **负控翻转**（评审 required_node 案构造）：两核心案
  （reactant/product × unmatched_structure：原合法 declared_complete
  边新增必需反应物/共同产物 C，from/to 与 participants 同源完整、
  schema 通过）：修复前真实 CCO→CC=O 事件仍 `matched_strict`、聚合
  `matched_strict=2`；修复后该边 `unmatched_required_node_uncovered`
  （gaps=[n-required-missing]）、聚合 `matched_strict=1` +
  `unmatched_required_node_uncovered=1`；另一条边合法严格保持。
  `limited_duplicate` 两变体（必需节点同结构但声明 cn_only）经
  S5A-01 封顶后同样不 strict（两修复联动闭合）。
- **正控保持**：合法图 `required_node_gaps` 恒空、两边
  `matched_strict`；事件侧超集/缺共同产物的覆盖失配披露
  （`matched_participant_coverage_partial`，partial_subset/superset）
  保持不被吞；共同产物保留、独立备选不合并保持。
- **范围限定（评审 §4.3 明示 P2）**：仅 participants 新增而
  from/to 未列的多视图案**不进门禁**（`test_s5a03_participants_
  only_node_deferred_p2` 钉住现行为 `matched_strict` 保持）；不新增
  角色/系数/计量门、不要求任意骨架投影字段强等、不加 occurrence
  一一对应门。
- **证据**：`probe_before|after/required_node_*.json`（六变体完整
  回执：schema 通过、真实 native、全部 node 条目与聚合）；翻转核对
  6 项全过；回归 `test_s5a03_*`（6 用例）。

### 3.4 S5A-04 persist 核验与写入同一实际规范路径

- **入口**：`persist_evaluation_output`（evaluation.py，公开落盘）。
- **行为**：`Path.resolve()` 一次；授权判定、目录创建、写文件三处
  用同一解析后路径。显式 `repo_root`：relative target 基准 = 相对
  cwd 解析（声明根即核验根）；解析后实际路径逃出声明根（错 cwd、
  绝对路径越界、任意层 symlink 逃根）⇒ 结构化先拒
  （`gold_content_outside_declared_root`；零新文件/目录）；根内
  再核 repo 相对路径是否授权 gitignored 根
  （`gold_content_unauthorized_path`）。未声明 root ⇒ 含金标一律
  拒（`gold_content_root_required`——根规则明确，不做未解析路径名
  授权）。`contains_gold=False` 普通非敏感写入保持原行为。回执
  `path` = 实际写入路径。
- **五案翻转/保持**（评审 write_boundary 探针同案，全合成占位
  `synthetic-placeholder-not-gold`）：错 cwd 相对路径（修复前真实
  写 cwd 外 + 回执）→ 拒、零新文件（翻转）；相对 symlink 逃根
  （修复前真实写根外）→ 拒、外部目录零新文件（翻转）；两绝对路径
  案父基线已拒 → 保持拒（kind 升级为
  `gold_content_outside_declared_root`）；合法授权根相对正控 →
  接受且回执=实际路径（保持）。
- **证据**：`probe_before|after/write_boundary.json`（含写前存在性/
  写后文本与 SHA）；翻转核对 5 项全过（2 翻转 + 2 保持 + 1 正控）；
  回归 `test_s5a04_*`（3 用例：错 cwd / symlink 逃根 + 绝对越界 +
  合法正控 / 无根拒绝 + 根内非授权拒绝 + 普通写入保持）。
- **有限残留**：不新增内容 DLP、完整沙箱或敌意并发 symlink-race
  防御（评审 §4.4 明示无需）；无 root 含金标写入从"字面授权"改为一
  律拒绝（根规则变化由 evaluation-2 登记；既有测试的该负控期望 kind
  同步更新并披露）。

## 4. 数字（全部合成规则级工程数字，不外推 dev/298）

| 项 | 结果 |
| --- | --- |
| PPV1 全量（仓内树，41 文件，最终字节） | **1087 passed / 0 skipped / 0 failed，exit 0**（1045 既有 + 42 新） |
| 父 `2e1e7af` 同字节（5 个新+更新文件，detached worktree，最终字节） | **41 failed / 94 passed / 0 collection errors，exit 1** |
| 父红逐 nodeid 分类 | S5A-01 行为 7；S5A-02 行为 19 + 详细分类器实现缺失 1（AttributeError，非行为翻转）；S5A-03 行为 4 + 披露字段缺失 3（KeyError `required_node_gaps`，非行为翻转）；S5A-04 行为 3 + 拒绝 kind 1；版本字面量 3（profile-21/evaluation-2 ×2 处） |
| 父绿保持 | 5 条件同义正控（公共分类器同值）+ preference/scenario 轴 + 其余 89 项合法用例 |
| G01 安全隔离（沿 R7→s5a 控制器谱系 +1 新输入，304 白名单输入，fresh tmp） | **1689 passed / 8 skipped / 17 deselected，exit 0**（期望 1647 评审实测 + 42 新，recorded not enforced） |
| G01 输入 SHA 前后 | 304 输入（源树 244 项）拷贝时/运行后复核零变化、零缺席 |
| G01 逐项缺席披露 | 8 skip：v4 对照根 1（`test_analog_assets.py:95`）、v2 provenance/summary 2（`test_analog_v2_corpus.py:62,153`）、冻结 v3 真实评价 5（`test_batch_runner.py:52`、`test_score_report.py:110,163,172,184`）；17 deselect = 16 slow + 1 显式（`test_export_v3.py::test_charge_fixture…`，沿 R7 谱系）；缺席不算通过 |
| 探针翻转核对（before/after，fresh tmp） | **40/40 全过**（六 scope + 必要节点 6 变体 + participants-only P2 保持 2 + 20 条件 + 写边界 5 + 正控） |
| 冻结正文/FREEZE_RECORD | `7fd35aab…` / `6e046e29…` 逐字节一致（未动） |
| 证据封包 | `docs/review_evidence/ppv1_s5a_rework_r1_2026-10-09/`：123 文件，manifest.json + SHA256SUMS 全纳哈希（含嵌套业务 manifest/全表快照 SHA），仅排根控制文件；`shasum -c` 全过 |

缓存口径：主命令 `-B` + `PYTHONDONTWRITEBYTECODE=1` + pytest
`-p no:cacheprovider`；本轮仓内与隔离树均未见 .pyc 落盘。

## 5. 晨报分列（非本轮新增科学放行门）

- **P2/待裁定（评审 §5 既有清单，本轮未冒充新门）**：unknown==
  unknown 进严格档（已执行披露，冻结前须裁定分桶口径——prereg
  proposed 文字已如实标注实现证明范围）；角色/系数状态集合口径
  （prereg 文字已同步"当前实现证明范围：不比较角色/系数"）；occurrence
  双轴/跨 occurrence 求和禁令；endpoint helper 三件最低口径与
  handoff 死键（读码级 P2，本轮未动 `check_endpoint_claims`）；
  R16 `confirmed_claim_events` 名实（样本数非独立确认事件数）。
- **teacher 决策项**：§10.1 二十项仍 TBD（题源/金标口径/独立性/
  分母/阈值/置信区间/费用等）；条件沿冻结同源 vs 独立评测口径
  （本轮按前者收口，后者如选须独立命名/版本/分歧报告）；负要求
  表示与数值 basis 映射限定；participants-only 多视图表示语义；
  G01 无 root 含金标写入的一律拒绝规则是否需放宽口径。
- **建议主会话安排**：mimo 只读化学复核（请求 r22，见
  `docs/mimo_ppv1_chem_review_request_r22.md`，自包含合成、程序事实
  标"待执行验证"）；Codex 正链复审。

## 6. 有限残留（诚实清单）

1. S5A-02 是"沿冻结同源 + 登记映射"收口：冻结键集外条件键/
   无法表示条目按 unknown/unsupported 族披露（不判冲突/相容）；
   是否扩键集/负要求表示属用户/teacher 裁定，评测侧不代定。
2. S5A-03 participants-only 多视图不进门禁（评审单列 P2）；本回归
   钉住现行为，冻结前须裁定表示语义同步。
3. `_pair_exports_to_samples` 根配对按内容严格身份（样本关联，
   不授指标）；root_entity `identity_scope` 声明的消费面属 P2 表示
   语义。
4. 既有测试的三处夹具更新（redox 桶名、pH 数值事实、
   electron_acceptor 缺事实键、s5_27 拒绝 kind）均为修复语义的
   如实同步，逐项披露于 §3；无削弱断言。
5. mimo v21 的 S1-2（预测侧重算/版本核对/差异轴分子桶）、S2-1/2/4
   （unknown==unknown、scope 未举证、outside 桶吸入）、面四/五/六
   建议为 proposed 冻结前收口项，非本轮四 P1 范围，未实施。
6. G01 期望数字按评审实测基线 1647+42=1689（旧交付书 70/1648 陈旧
   预期已被评审 §2 更正，不再沿用）。

## 7. 完成声明

S5A-01/02/03/04 四组 P1 已按评审 §8 最低收口闭合（反例逐案翻转、
正控保持、父基线真实红、G01 隔离绿、冻结正文零改动、契约版本按
规范登记）。S5a 阶段验收仍归正链复审与用户/teacher；本交付不宣布
科学性能、不启动 S5b、不代定任何阈值/分母/金标。
