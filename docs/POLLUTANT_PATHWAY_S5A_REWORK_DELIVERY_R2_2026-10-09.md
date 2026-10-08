# pollutant_pathway_v1 S5a 回修 r2 交付书

日期：2026-10-09（Asia/Shanghai）。实施：S5a 回修 r2 唯一实施代理。
基线：`1ef9e4840ff1be233dedcb543b967447cd591276`（直接父）。
范围：评审 `docs/POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_R2_2026-10-09.md`
§4 唯一残余 P1 [S5A-02]（显式非规范/键量纲不支持的要求单位被披露
但不参与判决，丢弃后授 compatible/conflict）有限收口，按 §8 提示词
逐字执行；S5A-01/03/04、S4/S3、ISO-01 保持关闭不重开；A1/C1 及
其它晨报 P2 保持登记不扩门；不实施 S5b；不触金标/题面/封存逐题
run/dependingv4/原 v3 评价资产；判分零 LLM、零外部模型调用（mimo
请求只写文档不发送）、零网络、零费用、不 push。

**状态口径**：本轮只收工程接口缺口。科学状态仍由用户/teacher 按
预注册裁定；本交付不产生任何 dev/298 科学性能声明（工程数字不
外推 dev/298）；`interface_verified_only` 只是程序模式标志。

---

## 1. 五入口矩阵（ConditionScope 条件链路；逐入口 → 本轮变化）

| 入口 | 位置（`src/pathway_v43/pollutant/`） | 事实消费 | 本轮变化 |
| --- | --- | --- | --- |
| validate | `reference_graph._validate_condition_scope`（schema 形状：`unit` 必须在场但是自由字符串，枚举只查 status/required）+ `evaluation.validate_evaluation_input` | 形状级校验，不判单位语义 | **不变**（单位支持能力是消费侧语义；reference-graph-1 字段形状零变化） |
| map | `evaluation._map_condition_scope_to_requirement`（ConditionScope → 冻结 Requirement 构造 kwargs）+ `_build_frozen_facts`（事实 → `build_condition_fact`，事实 unit 原样入冻结构造器） | 旧：单位只 append 披露、kwargs 不含 unit，非规范/意外单位后仍返回 kwargs ⇒ 值按键规范单位直比 | **S5A-02 r2 单位支持能力在映射首消费处决定**：带量纲键显式非规范单位（K/F）⇒ 无合法表示 ⇒ 返回 None（沿既有不支持路线）+ 机读披露 `requirement_unit_noncanonical`（保留原 key/unit/value/allowed_units/reason）；无量纲键（物种/枚举/matrix）显式单位（mg/L）⇒ 同路 `requirement_unit_unexpected` 返回 None；空要求单位（temperature_C）⇒ **canonical-by-key 默认合法不降档**（披露 `requirement_unit_not_declared`/reason=`requirement_unit_canonical_by_key`，note 更正为按键规范单位约定）；显式规范单位（°C/C/celsius、pH/pH/dimensionless）⇒ 合法（正控保持）。**事实侧不动**：来源单位三态（canonical/source_unit_unknown/unit_mismatch）仍由冻结同源 `_assess_requirement` 裁决 |
| classify | `classify_condition_requirement`（公共单条）→ `_classify_condition_requirement_detailed` | kwargs=None ⇒ 分类 `condition_unknown` + reason `requirement_not_representable` | 同一 unknown 族路线（沿既有不支持路线），**reason 区分单位原因**：披露含单位 kind ⇒ reason=`requirement_unit_not_representable`（机读可判别；preference 轴遇不可表示单位同沿 unknown） |
| classify_sample | `classify_sample_conditions`（节点 condition_scope + 边 condition_requirements × 导出 contexts condition_facts → buckets/details/mapping_disclosures） | 单位不可表示案原落 compatible/essential_conflict 桶 | 落 `condition_unknown` 桶；details 行 reason 携带 `requirement_unit_not_representable`；mapping_disclosures 机读保留原 unit/value/key（sample 级透传代码本身零改动——分类桶/reason 自动传导）；note 同步 |
| aggregate | `evaluate_scientific` → `_aggregate_metrics`（environment_conflict_rate 分桶） | 四降案计入 compatible/essential_conflict 分桶 | 计入 `condition_unknown` 分桶（聚合代码零改动，只消费分类桶；**公开 sample 结果 → 聚合不再记 compatible/conflict**）；metric note 同步单位收口说明 |

四同根规则同源闭合点不变：条件规则 = `path_context._assess_requirement`
（冻结判据四实现；评测侧直接 import `aggregate_environment_fit`/
`build_requirement`/`build_condition_fact`，无第二套规则）；本轮
**只收适配首消费缺口**，冻结 path_context/criteria-v1/FREEZE_RECORD
逐字节未动（证据层 shasum 核验，`frozen_integrity.json`：正文
`7fd35aab…`、记录 `6e046e29…` 与父一致）。

## 2. 契约版本登记变化

| 契约 | 之前（r1） | 本轮（r2） | 承载 |
| --- | --- | --- | --- |
| `ppv1-evaluation-2` | r1 四组 P1 语义 | **ppv1-evaluation-3** | S5A-02 r2 要求侧单位首消费收口（映射首消费决定单位支持；不可表示 ⇒ unknown/unsupported 族 + 机读保留原 unit/value/key/原因；空单位 canonical-by-key 默认合法）+ B2 文案纠错（文字与实现同真）——分类语义变更不偷换同一已登记契约 |
| `ppv1-preregistration-template-2` | r1 proposed 同步 | **ppv1-preregistration-template-3** | `condition_policy` proposed 文字同步（要求侧单位收口 + B2 事实更正限定；仍 proposed 不冻结，§10.1 全部 TBD） |
| `ppv1-profile-21` | r1 | **ppv1-profile-22** | 身份块携带 evaluation-3 / preregistration-template-3 |
| `ppv1-reference-graph-1` / `ppv1-split-manifest-1` | r1 | **不变** | 字段形状零变化（单位是消费侧语义，由 evaluation-3 承载） |
| criteria-v1 冻结正文 / FREEZE_RECORD | — | **逐字节不改** | SHA 核验一致（见 §1）；判据一–五与 0d–0h 消费语义零触碰 |

改动文件（git diff 全集；legacy/G2/AtomTool/export_v3/production
零触碰）：`src/pathway_v43/pollutant/{evaluation,preregistration,profile}.py`
（+187/−48 行）+ 4 个既有测试文件字面量/文案断言更新 + 新回归
`tests/test_ppv1_s5a_rework_r2.py`（18 用例）。

## 3. S5A-02 r2：入口 → 行为 → 正负控 → 证据 → 残留

- **入口**：`_map_condition_scope_to_requirement`（单位支持能力首
  消费决定点）→ `_classify_condition_requirement_detailed`（reason
  区分）→ `classify_condition_requirement` / `classify_sample_
  conditions`（sample 桶/披露）→ `_aggregate_metrics`（聚合分桶）。
- **行为**：
  - 显式非规范单位（temperature_C=298 unit=K / 25 unit=K / 77
    unit=F）与无量纲键声明单位（electron_acceptor=O2 unit=mg/L）
    ⇒ **无合法冻结表示** ⇒ 分类 `condition_unknown` +
    reason `requirement_unit_not_representable` + 机读披露保留原
    key/unit/value/allowed_units/原因（不丢弃单位后授相容/冲突、
    不做 K/F 换算、不猜测单位语义）；
  - 空要求单位（temperature_C=25 unit 空）⇒ **canonical-by-key
    默认合法不降档**（披露 reason=`requirement_unit_canonical_by_
    key`，note 说明按键规范单位约定消费；评审 §4.2.2"不要求全面
    拒空"）；
  - 显式规范单位（unit=C）⇒ 合法（正控保持 compatible）；
  - **要求侧 canonical-by-key 默认与事实侧来源单位三态分立**：
    事实侧 temperature 缺单位仍 `source_unit_unknown` ⇒ unknown、
    事实侧 K ⇒ `unit_mismatch` ⇒ unknown、事实侧 C ⇒ canonical
    （既有正控全部保持）。
- **负控翻转**（评审 R2 §4.1 六 B1 真实公开案逐案，评审方
  `mimo_conditions_probe.py` + `assert_B1_contract.py` **逐字节复制
  到 fresh tmp 复跑**，真实 `start_run → 带 ledger read_native_
  export → evaluate_scientific → 聚合` 公共链）：

  | 参考要求 | 真实同源事实 | before（父字节） | after（r2 字节） |
  | --- | --- | --- | --- |
  | temperature_C=298，unit=K | 25 C | essential_conflict | **condition_unknown**（reason=requirement_unit_not_representable） |
  | temperature_C=25，unit=K | 25 C | compatible | **condition_unknown** |
  | temperature_C=77，unit=F | 25 C | essential_conflict | **condition_unknown** |
  | electron_acceptor=O2，unit=mg/L | O2、无单位 | compatible | **condition_unknown** |
  | temperature_C=25，unit=C | 25 C | compatible | **compatible 保持** |
  | temperature_C=25，unit 空 | 25 C | compatible | **compatible 保持**（披露改 canonical-by-key 约定） |

  B1 契约断言 before 4 FAIL/2 PASS exit1 → after **6/6 PASS exit0**
  （`flip_check.json`）；17 案公开桶 diff：**恰好 4 案变化（四降），
  13 案保持**（含 B2 十案两序、B3 点值、两 B1 正控——B2/B3 零影响）。
- **判别回归**（评审 §4.2.3）：`test_s5a02_r2_unit_branch_not_
  masked_by_missing_facts` —— 合法事实（25 C known_present）在场 +
  necessity 来源（source_refs 非空）在场 + 非规范要求 unit（K）⇒
  unknown 的 reason 是 `requirement_unit_not_representable`（断言
  reason **不含** no_applicable_fact/necessity_unsourced）；同案把
  unit 改空 ⇒ essential_conflict/compatible（证明 unknown 来自单位
  分支，**不是 facts=[] 天然 unknown 冒充**）。
- **端到端 + 聚合**：六 B1 案走真实公共链（`_run`/`_evaluate_
  graph`），sample `environment_conflicts.buckets` 与聚合
  `environment_conflict_rate.buckets` 同源断言 `{condition_unknown:1}`
  （四降案）/`{compatible:1}`（两正控）；details reason 码 +
  mapping_disclosures 原样断言（unit/value/key）。
- **B2 文案纠错**（文字与实现同真；代码/文档三处同步）：
  - 事实（钉住）：合法公共链的 unknown 事实经 checked
    `build_condition_fact` **值清 None**（不带身份）⇒ 同键**相反**
    present×absent 事实两序均 `condition_unknown`；known×unknown
    混合两序均按首条已知事实裁决（present ⇒ compatible / absent ⇒
    essential_conflict）——mimo r22 的"任意多事实 unknown 且顺序
    相关"读码推论在合法公共链不成立，已按评审 §5-B2 正式更正；
  - 登记为 P2（不属本契约）：直接 dataclass 绕过 checked 构造器
    的低层次序差异（`same[0]` 顺序相关）是低层支持边界，改冻结侧
    物种语义归用户/teacher 裁定，本轮不动 src；
  - 同步位置：`evaluation.py` 模块 docstring（r2 段 + r1 段措辞
    精确化"同键相反事实"）、`_classify_condition_requirement_
    detailed` docstring、`classify_sample_conditions` note、
    `preregistration.condition_policy` proposed 文字。
- **证据**：`docs/review_evidence/ppv1_s5a_rework_r2_2026-10-09/`
  （§6）；`conditions_before|after/`（17 案完整输入/输出/argv/env/
  exit/SHA + B1 断言 + 日志）、`flip_check.json`、回归
  `test_s5a02_r2_*`（18 用例：六 B1 分类器参数化 + 判别 + 两侧
  语义分立 + preference 轴 + 六 B1 端到端/聚合 + B2 守门 + r1 20
  案保持 + 版本/冻结守卫）。
- **处置路线**：沿 §8"共同映射先决定单位支持；无法合法表示 ⇒
  真正 unknown/unsupported + 机读保留原值；未能映射沿既有不支持
  路线"（未选独立评测口径、未改冻结侧、未做换算/label/负要求）。
- **有限残留（诚实清单）**：
  1. 不做 K/F→°C 换算、不建单位 label 库、不发明负要求表示、
     不扩 preference 语义（评审 §4.2.4 明示禁止）；
  2. pH 空单位本就合法（在键规范单位集内）⇒ 无 `requirement_
     unit_not_declared` 披露（与 temperature_C 空单位不同路，测试
     钉住）；species/enum/matrix 键空单位合法不变；
  3. 事实侧来源单位三态、多事实、necessity、场景/阶段轴全部
     冻结同源未动（r1 已收口，本轮 20 旧案全保持）；
  4. 直接 dataclass 低层顺序边界（B2 P2）保持登记不修；
  5. 单位维度不授完整相容/冲突 ⇒ 相容结论的"已评估维度"口径
     沿 §6 聚合说明（condition_unknown 桶不计冲突）。

## 4. 数字（全部合成规则级工程数字，不外推 dev/298）

| 项 | 结果 |
| --- | --- |
| PPV1 全量（仓内树，42 文件，r2 字节） | **1105 passed / 0 skipped / 0 failed，exit 0**（r1 1087 + 18 新；`ppv1/` 封包：argv/env/exit/stdout/stderr/junit/execution_record，HEAD+dirty 如实记录） |
| 直接父 `1ef9e48` 同字节（r2 的 5 个新+更新文件，detached worktree 覆盖 r2 字节） | **15 failed / 106 passed / 0 collection errors，exit 1**（`parent_baseline/` 封包 + junit + 逐 nodeid 分类） |
| 父 15 红分类 | **行为 10**（六 B1 分类器四案 + 端到端四案 + 判别案 + preference 轴案：父把非规范/意外单位要求判 compatible/essential_conflict）+ **字段缺失 1**（`[B1_requirement_unit_empty_25_vs_25C]`：父披露缺机读 `reason` 键 KeyError，分类 compatible 本身在父已正确）+ **版本字面量 4**（evaluation-3/template-3/profile-22 × r1/r2/profile/s4b 四处） |
| 父绿保持（106） | B1 两正控（C_25 分类器+端到端、unit_empty 端到端）、B2 守门全绿（checked 值清 None + 相反事实两序 + known×unknown 两序）、r1 20 条件案全保持、事实侧三态区分（source_unit_unknown/unit_mismatch/canonical）全绿 |
| G01 安全隔离（沿 R7→s5a→r1 谱系 +1 新输入=305，白名单树，fresh tmp） | 复跑 **1706 passed / 9 skipped / 17 deselected，exit 0**（r1 实测 1689 + 18 新 − 1 个守卫在隔离树内 skipif 跳过；8 旧 skip 类别不变 + 1 新 skip=冻结文本守卫，见 `g01/`）；首跑 1 failed 系本交付测试守卫读 docs/ 而白名单树不含 docs 的设计缺陷——已改 skipif 显式跳过并复跑，首跑摘要与失败定位如实登记于 `g01/incidents.json`（首跑完整 stdout 因复跑前清目录未保留，已如实注明，不计产品红） |
| G01 输入 SHA 前后 | 305 输入拷贝时/运行后逐项复核（`post_run_sha_result.json`）；与 r1 G01 304 输入 diff：+1 新（r2 测试文件）、7 个既有输入字节合法变化（evaluation/preregistration/profile + 4 测试文件，登记于 `preparation.json.changed_inputs_vs_r1_g01` 且集合一致性由脚本强制核对） |
| G01 逐项缺席披露 | 8 skip：v4 对照根 1、v2 provenance/summary 2、冻结 v3 真实评价 5（junit 逐 nodeid `post_run_sha_result.junit_skipped_nodeids`）；17 deselect = 16 slow + 1 显式（沿 R7 谱系）；**r2 冻结文本守卫在隔离树内 skipif 跳过（docs 不在白名单）——字节完整性由证据层 `frozen_integrity.json` 核验**；缺席不算通过 |
| B1 六案翻转核对 | before 4 FAIL/2 PASS exit1 → after **6/6 PASS exit0**；17 案 diff 恰好 4 变 13 保持（`flip_check.json`） |
| 冻结正文/FREEZE_RECORD | `7fd35aab…`/`6e046e29…` 逐字节一致（`frozen_integrity.json`） |
| 缓存口径 | 主命令 `-B` + `PYTHONDONTWRITEBYTECODE=1` + pytest `-p no:cacheprovider`；G01 隔离树测试子进程仍产生少量隔离 pyc（首跑观察 7 个，如实登记于 `post_run_sha_result.pyc_files_after_run`，不虚报"全部无 pyc"）；仓内树未见 pyc |

## 5. 晨报分列（非本轮新增科学放行门；保持登记不扩门）

- **A1（根配对）P2 保持**：`_pair_exports_to_samples` 按根内容
  严格身份配对，不消费 root `identity_scope`；有限身份参考根的
  维度差异可落 `not_evaluated_export_missing`/`native_export_
  missing` 归因。按评审 R2 §5-A1 固定范围归 P2（未授错误 strict、
  未计化学错误）；后续须区分 actual native missing 与 root_
  identity_unresolved——本轮**不**扩根模糊配对/CN 根配对/多样本
  归属算法。
- **C1（participant_list_status）P2 保持**：判定层不消费该字段
  （清单完整性/角色/计量门不新增）；"exact=与声明集合相等"与
  partial/unknown 清单超集/分母口径冻结前须 teacher 同步。
- **B3/B4/B5/B6 P2/teacher 保持**：点值 point 语义（B3：裸数值
  25 映 point 与事实 30 C 判 conflict 已公开登记，不代 teacher 改
  optimum）、私有 helper 坏事实跳过边界（B4：真实 start 构造期先
  拒，不是合法公共链反例）、preference 无源探针/枚举包含关系
  （B5/B6 读码建议）——均未额外执行程序证据，不报执行通过。
- **teacher 决策项**：§10.1 二十项仍 TBD；条件沿冻结同源 vs 独立
  评测口径（本轮继续前者）；负要求表示/数值 basis（ConditionScope
  无 value_basis 字段，裸数值按 point 登记披露）/participants-only
  表示语义/单位 label 库是否扩（若扩须换算/注册表属 teacher）。
- **建议主会话安排**：mimo 只读化学复核（请求 r23，`docs/mimo_
  ppv1_chem_review_request_r23.md`，自包含合成、程序事实标"待执行
  验证"）；Codex 正链有限复审。

## 6. 证据封包

`docs/review_evidence/ppv1_s5a_rework_r2_2026-10-09/`：

- `conditions_before|after/`：评审方探针逐字节复跑（17 真实公开
  条件案完整输入/输出/reader 回执/评测输出/冻结对照 + B1 契约
  断言 + logs 含 argv/cwd/固定 env/exit/elapsed/stdout/stderr SHA）；
  before 树=HEAD 1ef9e48 字节、after 树=r2 字节，共用 fresh tmp
  dependingv3 普通镜像与隔离 BBD_DATA_ROOT/V3_CODE_ROOT/V43_ASSET_ROOT；
- `ppv1/`、`parent_baseline/`：完整 argv/env（固定相关环境）/exit/
  stdout/stderr/junit/execution_record（HEAD+dirty 如实记录）；父
  逐 nodeid 红绿分类 `baseline_classification.json`（行为/字段/版本
  分开，106 绿清单在内）；
- `g01/`：G01 隔离复跑完整封包（preparation/input_sha256/junit/
  stdout/stderr/execution_result/post_run_sha_result/incidents——
  首跑 1 failed 事件与复跑数字如实分列，首跑完整 stdout 未保留
  已注明）；
- `flip_check.json`：B1 六案 before/after + 17 案桶 diff（4 变 13
  保持）；`frozen_integrity.json`：冻结正文/FREEZE_RECORD shasum；
- `scripts/`：评审方两脚本逐字节副本（SHA 与评审包一致，见
  README）+ 本轮 runner/分类器/G01/封包脚本；
- `README.md` + `manifest.json` + `SHA256SUMS`：全部文件纳哈希
  （含嵌套 manifest 与子包 controls），**只排根两个自控制文件**
  （根 manifest.json 与 SHA256SUMS 本身）；`shasum -c` 全过。

## 7. 执行事件与未执行内段（如实登记）

- **G01 首跑 1 failed**：r2 测试 `test_s5a_r2_contract_version_
  registration_and_frozen_integrity` 原设计在单测内读 `docs/` 冻结
  文本，而 G01 白名单树不含 docs ⇒ FileNotFoundError。处置：改
  skipif（隔离树内显式跳过并注明"字节完整性由证据层 shasum 核验"）
  后复跑 1706 passed/9 skipped/17 deselected exit0；首跑摘要行与
  失败定位（nodeid + pathlib read_bytes FileNotFoundError）如实
  登记于 `g01/incidents.json`——首跑完整 stdout 因复跑前清目录
  未保留（已如实注明），不计产品红；这是**本交付自己的测试设计
  缺陷**，不是产品行为回归（两跑业务通过数均为 1706）。
- **调度失败**：本轮无（条件探针一次成功执行 17 案；无 CLI
  mode 调度错误）。
- **未执行内段（不凑全绿如实披露）**：r1 的 identity/必要节点/
  写边界专项与 40 检查探针本轮**未复跑**（S5A-01/03/04 已关闭，
  本轮范围仅 S5A-02 单位收口；其行为由 PPV1 全量 1105 绿中的
  r1 42 用例守门）；B2 四个直接 dataclass 低层对照本轮未复跑
  （P2 保持登记）；A1/C1 晨报 P2 未构造新夹具。
- **网络口径**：条件探针无 socket 仪表，不宣称全局网络计数实测
  为零；本轮无网络/模型调用代码。

## 8. 完成声明

S5A-02 唯一残余 P1 已按评审 R2 §8 最低收口闭合：显式非规范/
键量纲不支持要求单位在映射首消费处真正降 unknown/unsupported 族
并机读保留原 unit/value/key/原因（四 B1 真实公开案实际降档、两
合法正控保持、B1 契约 6/6、判别回归有事实有来源不冒充）；要求侧
canonical-by-key 默认与事实侧来源单位三态分立；B2 文案纠错同步；
18 旧同源条件 + 2 required_absent 单列全保持；版本按规范登记
（evaluation-3/template-3/profile-22，reference-graph-1/
split-manifest-1 不变）；冻结正文逐字节未动；父基线真实红 15
（10 行为 + 1 字段 + 4 版本）；G01 隔离含首跑缺陷如实登记。S5a
阶段验收仍归正链复审与用户/teacher；本交付不宣布科学性能、不
启动 S5b、不代定任何阈值/金标/分母/独立条件规则。
