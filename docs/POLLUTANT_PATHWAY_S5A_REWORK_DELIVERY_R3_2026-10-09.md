# pollutant_pathway_v1 S5a 回修 r3 交付书

日期：2026-10-09（Asia/Shanghai）。实施：S5a 回修 r3 唯一实施代理。
基线：`39d739d04f9b3e6e7ad78cb0ec5f1547ac54c962`（直接父，r2）。
范围：评审 `docs/POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_R3_2026-10-09.md`
§4 唯一阻塞 P1 [S5A-05]（生产上下文首消费引用绑定：旧
`ctx:<context_ref>` 地址下换入自洽新 `context_id` 的上下文，公开
resume 仍接受并提交事件）有限收口，按 §8 提示词逐字执行；
S5A-01/02/03/04、S4/S3、ISO-01 保持关闭不重开；A1/C1 及其它晨报
P2 保持登记不扩门；不实施 S5b；不触金标/题面/封存逐题
run/dependingv4/原 v3 评价资产；判分零 LLM、零外部模型调用
（mimo 请求只写文档不发送）、零网络、零费用、不 push。

**状态口径**：本轮只收工程接口缺口。科学状态仍由用户/teacher 按
预注册裁定；本交付不产生任何 dev/298 科学性能声明（工程数字不
外推 dev/298）；`interface_verified_only` 只是程序模式标志。

---

## 1. 入口矩阵（load_context 上下文消费链路；逐入口 → 本轮变化）

| # | 入口 | 位置（`src/pathway_v43/pollutant/`） | context_ref 来源 | 消费 | 本轮变化 |
| --- | --- | --- | --- | --- | --- |
| 1 | `runflow._Driver._run_decide` | `runflow.py:845` | 调度行动行 `receipt["context_ref"]`（root retrieve 完成时以根 context_id 落账） | build_substrate_profile / prepare_hypothesis（派生）/ 模型提案 / 子行动调度 | **共用守卫**（经 `production.load_context`，见 §3） |
| 2 | `runflow._Driver._run_expand` | `runflow.py:1113` | 同上 | `expand_hypothesis_production` → audit_hypothesis + admission + 事件提交 | **共用守卫** |
| 3 | `runflow._Driver._run_transition` | `runflow.py:1281` | 同上 | `derive_child_context`（父对象派生前先消费）+ persist 子 ctx + followup 调度 | **共用守卫**；子 ctx 恒存**新地址** `ctx:<新 ID>` 并沿新引用（案 5 正控） |
| 4 | `endpoint._inherited_unresolved_dependencies` | `endpoint.py:324` | `search_actions` 表 DISTINCT context_ref | F02 依赖继承 | **共用守卫**；绑定错配时包成 `endpoint_context_consumption_failed`（错误文本披露原 kind） |
| 5 | `endpoint._route_condition_assessments` | `endpoint.py:389` | 同上 | 路线条件评估（历史快照消费） | 同 4 |
| 6 | `endpoint._route_conditions_snapshot` | `endpoint.py:451` | 同上 | 条件事实快照 | **共用守卫**；绑定错配直接上抛 `ConditionContractError` |

写入侧（本轮零改动，列出仅为闭环）：`persist_context`
（`production.py`）恒写 `ctx:<context.context_id>` 并返回该 ID 为
存储键/引用；root 上下文（`runflow.py:1512`）、expand 子上下文
（`:934`）、transition 子上下文（`:1286`）三处写入全部自洽——
**合法链天然满足地址=身份**；只有外部突变（评审反例）才出现
地址≠身份。六个消费入口全部经同一 `production.load_context`，
**复用同一守卫而不各自造规则**（复审 §4.3 要求；静态守门见
`tests/test_ppv1_s5a_rework_r3.py::test_s5a_r3_entry_matrix_static_guard`）。

冻结侧零触碰：`path_context.py`（含 `from_dict` 内容身份判决）
逐字节不改（SHA `971ad00f…` 与父一致，`frozen_integrity.json`）；
S5A-05 守卫全部在 `production.load_context` 消费侧（复审 §4.3 与
仓内约定一致：改冻结侧才须停下回报——未发生）。

## 2. 契约版本登记变化

| 契约 | 之前（r2） | 本轮（r3） | 承载 |
| --- | --- | --- | --- |
| `ppv1-search-production-1` | r2（production 链） | **ppv1-search-production-2** | S5A-05 `load_context` 首消费引用绑定核验（请求 context_ref == 恢复载荷 context_id；旧地址下自洽新身份 ⇒ 结构化拒；selfhash 重算正确不能替代旧引用绑定）；production 链其余行为零变化 |
| `ppv1-profile-22` | r2 | **ppv1-profile-23** | 身份块聚合登记：search-production-2（S5A-05）+ evaluation-3/template-3 的五处拟冻结前 P2 文案同步（版本号不变） |
| `ppv1-evaluation-3` | r2 | **不变（版本号）** | 五处文案同步之二（模块 docstring B2 bullet + 详细分类器 docstring）：known×unknown 限定物种键、删合法链"顺序相关"尾巴 + 准确披露（condition_unknown 具体枚举/canonical-by-key 代价/value 仅 repr/实体只证存在/指标只分桶分母 TBD）。**拟冻结前文字修正，非语义变更，不拒 -3 输入**（复审 R3 §5 原文："五处文案为proposed冻结前P2必同步"） |
| `ppv1-preregistration-template-3` | r2 | **不变（版本号）** | 五处文案同步之三/之四（模块 docstring + condition_policy proposed 文字）；仍 proposed 不冻结，§10.1 全部 TBD |
| `ppv1-reference-graph-1` / `ppv1-split-manifest-1` | r2 | **不变** | 字段形状零变化 |
| criteria-v1 冻结正文 / FREEZE_RECORD | — | **逐字节不改** | SHA 核验一致（`7fd35aab…`/`6e046e29…`，`frozen_integrity.json`）；判据一–五与 0d–0h 消费语义零触碰 |

改动文件（git diff 全集；legacy/G2/AtomTool/export_v3/runflow/
endpoint/search/path_context/store **零触碰**）：
`src/pathway_v43/pollutant/{production,evaluation,preregistration,profile}.py`
（+151/−34 行，其中 production.py 为 P1 修复、其余三者为 P2 文案
与版本登记）+ 5 个既有测试文件版本字面量更新（profile-22→23；
`test_ppv1_s5a_schema.py` 的合成输入串同更，父上不构成红）+ 新
回归 `tests/test_ppv1_s5a_rework_r3.py`（14 用例）。

## 3. S5A-05：入口 → 行为 → 五案 → 正负控 → 证据 → 残留

### 3.1 修复行为（`production.load_context`，三层守卫逐层分测）

1. H07（既有）：信封可解析/hash（`read_search_artifact`，保全
   原文件）；
2. from_dict 内容身份（既有）：载荷 context_id 与全语义字段同源
   重算一致（案 2 的 `context_content_identity_mismatch` 保持，
   **先于绑定层**）；
3. **新增（r3）引用绑定**：`context.context_id != context_ref` ⇒
   `ConditionContractError`（与内容身份同族错误类；公共 resume
   边界同形结构化失败上抛、不吞成 run_error），detail 披露
   `expected_context_ref` / `recovered_context_id` /
   `storage_key` / `parent_context_ref`，kind=
   `context_reference_binding_mismatch`。消息明示：旧引用不复用；
   合法重建须用新 context_id 存**新地址**并沿新引用首消费；坏
   artifact 保全，不重封覆盖、不猜迁移、不默发新引用；selfhash
   重算正确不能替代引用绑定。

拒后行为：零派生/零评估/零 audit/零坏上下文事件提交（公开链
案 3/4 实测 events 0、endpoint_records/stop_reason_records 0 增量）；
输入 artifact 保全（字节等于突变形态）；无新 ctx 文件签发。

### 3.2 五案矩阵（1–3 复用复审 R3 §4.2 mimo 专项原输入；4/5 本轮
自构造，如实标注**不冒称复审已执行**——复审的 4 号补控未执行
（平台拦截）、5 号须构造）

| 案 | 构造 | before（父 39d739d，fresh tmp 复跑） | after（r3，fresh tmp 复跑） | 裁定 |
| --- | --- | --- | --- | --- |
| 1 正常 | checked unknown 值 None（评审 control 原输入；公共链 start(after_claim)→resume） | load ok；resume ok；events 0→1 | **同**（保持；PPV1 正控 + G01 1719 绿） | 合法恢复不误伤 |
| 2 旧 id+改内容 | unknown 值改 O2、保留旧 context_id、重封 H07（评审原输入） | load/resume 拒 `context_content_identity_mismatch`；events 0 | **同**（保持；from_dict 层先于绑定层） | 既有防线不动 |
| 3 新 id+旧地址 | 同上+直构重算新 context_id（载荷自洽）、重封 H07、旧 ctx: 存储键与行动引用不动（评审原反例） | **load 返回新身份；resume 成功；events 0→1；派生子上下文**（P1） | **load 拒 binding mismatch（期望 pc_a72…/实际 pc_d99…）；resume 同错上抛；events 0** | **原反例翻转** |
| 4 checked 合法新内容+旧地址 | `build_path_context`+`build_condition_fact` 全 checked 产物（unknown 值恒 None）整体写入旧地址、重封（本轮自构造） | load ok；resume ok；events 1 | **load 拒 binding mismatch；resume 拒；events 0**；同载荷存自己的新地址可正常消费 | 内容合法不豁免地址绑定（复审 4 号补控补齐） |
| 5 合法新 ID 新地址+父链 | `derive_child_context`（显式 source_ref 转换）+公共链 transitions plan start→resume（本轮自构造） | 子 ctx 新 ID 新地址、followup 沿新引用、地址-身份全对应 | **同**（保持） | 冻结判据四"重建半边"合法半边不误伤 |

完整输入/输出/前后表/argv/env/exit/SHA：`mimo_cases/`（评审
`probe.py` 字节忠实复制，SHA `4e0000f2…` 与审方原件一致；
after/before 两树、五案裁定 `five_case_adjudication.json`）。

### 3.3 拒绝后无关写入逐表披露（不伪报全表零变化）

公开链案 3（拒绝）前后全表快照（17 张表全量；复审"十五表"口径
= 去除 `meta`/`search_runs` 两张建库/注册即写表后的业务表数）：

- **零增量**：events、endpoint_records、stop_reason_records、
  report_projections、expansion_plans、event_appearance_links、
  hypotheses、model_requests、provenance_records、
  search_attempts、state_appearances、states（末态 1/1 为 start
  期写入，非 resume 增量）；
- **既有无关 retrieve/claim 写入**（与复审 §4.2 对旧 id 案的观察
  同形，如实披露）：search_actions 1→2（B1 恢复完成 root
  retrieve 后调度 decide 并认领）、search_commit_records 0→1
  （retrieve 完成落账）、budget_reservations 3→4（retrieve 消
  费）——**首消费拒发生在 decide 加载上下文时，root retrieve
  相关业务已在恢复段完成**，故不能宣称整个 resume 零写；
- 拒绝形态：`ConditionContractError` 从 `_run_decide` 经 drive
  循环原样上抛出 `resume_run`（错误类不在 driver 捕获清单内，
  与案 2 的上抛路径同形）；decide 行保持 claimed 计入未完成。

案 4 公共链同形（events 0；同三表 +1；artifact 保全）。

### 3.4 正负控与守门

- 正控：案 1/5（合法恢复/合法新地址链/场景转换保持）；同载荷
  新地址可消费（案 4 后半）；r1/r2 既有 1105 用例全绿（PPV1
  1119 = 1105 + 14 新）；
- 负控：案 2/3/4（三层守卫分层拒）；endpoint 三入口对坏上下文
  的包卷拒绝（`endpoint_context_consumption_failed` + `__cause__`
  kind 断言）；
- 守门：入口矩阵静态守门（六调用点计数 + 绑定守卫源码标记 +
  runflow/endpoint 本轮零触碰的源码事实）；契约版本登记 +
  冻结守卫（skipif 隔离树模式，证据层 shasum 互证）；P2 文案
  守门（模板/evaluation/profile 三处"仅物种键"等短语断言）。

### 3.5 残留映射（不扩门）

- typed/restore 低层直构语义（`ConditionFact(**dict)` 不经 checked
  归一、unknown+值两序差异）——**已登记 P2，归用户/teacher**
  （复审 §5；本轮只加绑定守卫，不以文字宣称低层语义已修）；
- 直读 artifact 绕过 load_context 的路径不存在于生产消费入口
  （六入口闭合），但外部工具直读文件不在本轮守卫范围（评审
  mimo v24 判断面一问②已如实提问）；
- 拒绝后"隔离坏上下文但继续无关任务"的更细粒度工程处置未
  实现（当前同案 2 一致：首消费拒即停，错误上抛）——不默改
  语义，留待评审裁定；
- 其余晨报 P2（A1 有限参考根、C1 participant_list_status、
  roles/coefs/occurrence、聚合因果/kind 子桶、point 值 basis、
  endpoint helper/死键、R16 样本≠确认事件）按上一轮范围继续
  登记不扩门。

## 4. 搭车 P2 文字同步清单（复审 R3 §5 五处 + 准确披露；不改任何条件实现）

| # | 文件:位置 | 修改 |
| --- | --- | --- |
| 1 | `evaluation.py` 模块 docstring B2 bullet（原 77-78） | known×unknown **仅物种键**按实体已知事实裁决；**非物种键任一适用 unknown ⇒ condition_unknown**；删"既有实现，顺序相关"尾巴；直构/restore 低层为已登记 P2、不以文字宣称首消费绑定已通过 |
| 2 | `evaluation.py` `_classify_condition_requirement_detailed` docstring（原 1136-1138） | 同上限定；合法 checked 链两序结果一致（实测 20 对照） |
| 3 | `preregistration.py` 模块 docstring r2 段（原 20） | r2 段内 known×unknown 加物种键限定；新增 r3 段（五处同步说明） |
| 4 | `preregistration.py` condition_policy proposed 文字（原 137-141） | 同 1 限定 + 准确披露：condition_unknown 具体枚举（不用族名）、value 是 repr 展示串非原生 value_raw（禁止 eval）、实体事实只证存在不证浓度/阈值、指标只分桶且正式分母 TBD（未知桶独立披露，unknown ≠ 无冲突）、不作"声明越具体只能降档"/"分母已定包含 unknown"宽泛承诺 |
| 5 | `profile.py` -22 注释块（原 267-268） | B2 句加物种键限定；新增 -23 注释块（search-production-2/profile-23 登记） |
| 附 | `evaluation.py` 模块 docstring 新增 r3 段 | canonical-by-key 代价（想写 298 K 省略 unit ⇒ 按 temperature_C 读 298 °C，不猜意图）等五项准确披露 |

模板 `condition_policy` 仍 proposed 不冻结；版本号不变
（evaluation-3/template-3），不拒 -3 输入；模板既有断言
（`test_ppv1_s5a_rework_r1.py:744-750` 等子串）全部保持。

## 5. 数字（全部合成规则级工程数字，不外推 dev/298）

| 项目 | 数字 | 说明 |
| --- | --- | --- |
| PPV1 全量 | **1119 passed / 0 skipped / 0 failed，exit 0** | 43 文件（r2 的 42 + 新 r3 文件）；1105 既有 + 14 新；不是科学性能 |
| 父 39d739d 同字节红绿 | **12 failed / 123 passed / 0 collection / 0 skipped，exit 1** | 6 个当前新增/更新文件的 135 nodeid；detached worktree，src/tests/pyproject 同字节、六测试文件以当前字节覆盖父测试字节 |
| 父 12 红分类 | **5 行为 + 2 字段 + 5 版本字面量，0 collection** | 行为红 = 案 3/4（unit+公共链）+ endpoint 入口（父上 load 返回新身份不拒，DID NOT RAISE 实证）；字段红 = 入口矩阵静态守卫 + P2 文案守门；版本红 = search-production-2/profile-23 字面量（r3/r2/r1 登记、profile、s4b） |
| G01 安全隔离 | **1719 passed / 10 skipped / 17 deselected，exit 0** | 306 输入（305 r2 谱系 + 1 新 r3 测试文件）；r2 实际 1706 + 14 新 − 1 新守卫隔离树内 skip（与登记预期一致，recorded not enforced）；**首跑即成，全日志保留**（r2 教训已应用） |
| G01 输入 SHA | **306 前后复验零不符** | 复制时/执行后逐输入 SHA-256；9 个合法变更输入 vs r2 G01 集（4 src + 5 test）脚本强制披露 |
| G01 缺席披露 | 10 skip / 17 deselect 逐 nodeid | 8 旧类（原冻结 v3 真实评价 5、v4 parser 1、v2 provenance/summary 2）+ r2/r3 两代冻结文档守卫（白名单不含 docs ⇒ skipif，证据层 shasum 互证）；deselect = 16 slow + 1 明确 charge/evaluation 依赖（命令级记录） |
| G01 pyc | 7 个隔离树子进程 pyc | 与 r1/r2 同数；仓侧 0；不声称全无 pyc |
| mimo 五案 | 1/2/5 保持、3 翻转、4 补控翻转 | 评审 probe 字节忠实复跑 + 本轮自构造 4/5；before/after 两树 |
| 冻结完整性 | criteria `7fd35aab…` / record `6e046e29…` / path_context `971ad00f…` | 与父及评审登记逐字节一致（`frozen_integrity.json`） |

## 6. 晨报分列（非本轮新增科学放行门；保持登记不扩门）

- 分母/阈值/题源/金标口径/独立性等 §10.1 全部 TBD 不代定；
  dev 与 298 双向不外推；不外推任何 dev 中间步骤数字；
- environment_conflict_rate 仍只分桶、无标量分母（本轮文字明确
  "正式分母 TBD、未知桶独立披露、unknown ≠ 无冲突"）；
- S5b 未授权未启动；proposed 评测契约不由本交付宣布冻结；
- mimo v24 请求（`docs/mimo_ppv1_chem_review_request_r24.md`）只写
  文档不发送，按既有主会话通道送审；程序事实标〔待执行验证〕。

## 7. 证据封包

目录：`docs/review_evidence/ppv1_s5a_rework_r3_2026-10-09/`。

- `manifest.json` + `SHA256SUMS`：根唯二控制文件（不纳自身
  SHA）；**其余全部实际文件（含嵌套 g01/attempt1 控制件、
  mimo_cases 子包、封包脚本本身）纳 SHA-256**，`shasum -c` 全绿；
- `ppv1/`：43 文件全量 argv/cwd/固定 env/exit/stdout/stderr/
  JUnit/执行记录；
- `parent_baseline/`：父树说明、12 红逐 nodeid 分类
  （`execution_record.json` `red_classification`，observed==
  declared 精确闭合）、全输出；
- `mimo_cases/`：评审 probe 字节忠实副本（SHA 与审方原件一致）、
  r3 案 4/5 脚本、五案裁定、after/before 两树结果与日志、
  `source_guard.json`（两树源码分别对账仓工作树/父树、v3 镜像
  为 source-only 副本不含评价资产）、`run_meta.json`（逐 run
  argv/env/exit）；SQLite 二进制与 run 目录不入包（tmp scratch
  保留，输入以 SHA 与 JSON 结果固化）；
- `g01/`：`attempt1/` 控制件全集（preparation/input_sha256/
  execution_result/junit/stdout/stderr/post_run + 输入树说明——
  243MB 白名单输入副本留 tmp 不入包）、`attempt1_console.txt`、
  `incidents.json`（**本轮零事故**；r2 首跑日志丢失的历史登记
  只读保留在 r2 证据内，不重裁定）；
- `frozen_integrity.json`：三冻结面 SHA 与父/审方登记对账；
- `scripts/`：G01 控制器、裁定/记录/收集/封包脚本（本身纳 SHA）。

## 8. 执行事件与未执行内段（如实登记）

- **本轮零事故**：G01 首跑即成（r2 教训应用：每次尝试独立输出
  根、不删日志）；无调度失败、无平台拦截、无续跑中断；
- 案 4/5 为本轮自构造（评审 4 号补控未执行、5 号须构造），全部
  标注不冒称复审已执行；评审 mimo 专项 1–3 用其原输入构造复现；
- **未执行内段**：r1/r2 的 identity/required-node/write-boundary
  专项探针与 17 桶业务探针本轮未重跑（S5A-01/02/03/04 已关；
  其行为由 1119 全量与 1719 G01 内的常驻回归守卫）；B2 四条
  直构低层两序探针未重跑（P2 裁定不变）；A1/C1 未造新夹具；
- 评审侧旧报告/永久证据一律只读未改；判分零 LLM；无 commit/
  push 前的任何远端操作。

## 9. 完成声明

S5A-05 有限收口完成：共同 `load_context` 首消费引用绑定核验
（requested context_ref == recovered context_id）落地，六消费入口
共用同一守卫；评审原反例（自洽新 ID 占旧地址被公开 resume 接受
并提交事件）在 fresh tmp 字节忠实复跑中翻转（events 1→0、结构化
拒、坏 artifact 保全）；案 4 补控（checked 合法内容+旧地址）与
案 5 正控（合法新 ID 新地址+父链+场景转换）按复审 §8 构造并通
过；合法恢复/子上下文/场景转换正控保持。搭车 P2 五处文案按
复审 §5 同步（版本登记 search-production-2 / profile-23；
evaluation-3/template-3 版本号不变）。criteria-v1 冻结正文、
FREEZE_RECORD、path_context 冻结判决逐字节不改。**阶段验收归
正链 Codex 复审与 mimo 化学评审（v24 请求已写、由用户送审）；
本交付不宣称 S5a 完成，科学性能 pending，全部 teacher TBD 不
代定。**
