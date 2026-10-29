# pollutant_pathway_v1 S4 回修 r1 正链复审（报告 R2）

日期：2026-10-08，Asia/Shanghai。正链 Codex 独立复审；三个专项子代理均为本会话协作执行，不调用外部模型。

**结论：S4 不通过。剩余 P1＝[S4-C02，S4-C04]。S4-C01、S4-C03 关闭；不重开 S3。完整 S4 完成交接点尚未成立，不交接 S5。**

**mimo 专项正式裁定：采信本次必要条件阻断不触发 criteria-v2。**冻结范围是判据一至五及 0d/0e，S4 endpoint 不在该范围；冻结正文及冻结记录逐字节不变。本批 endpoint 阻断是实际行为变化，已按 endpoint/policy-2 等契约族登记，不能把“冻结判据语义不变”扩大成“本批产品语义不变”。此裁定不等于 S4 放行，也不重新冻结判据。

## 1. 验收面、实际身份与执行边界

- 实际 HEAD：`0dd35d14d6539fbf134be18565f6709e852fc076`。
- 直接父：`8735601b75825388fe9f4a177a1131ef264054a1`。
- 唯一阻塞验收基线：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4_CODEX_CONFIRM_REVIEW_2026-10-08.md` §4 四组最低收口及 §7。
- 阶段契约：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4_IMPLEMENTATION_TASK_2026-10-08.md`，特别是 §2.B/C、§4.4、§5.1、§8。不得用“固定范围”掩盖同一首次消费契约的具体残余。
- 本轮交付：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S4_REWORK_DELIVERY_2026-10-08.md`；化学意见：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/mimo_ppv1_chem_review_response_r18.md`。
- 环境：conda `depending43`，Python 3.11.16、RDKit 2026.03.6、SQLite 3.53.4；准确运行 argv/env/exit/耗时、实际 schema 与 profile 见证据包。

所有写库探针在 fresh `/private/tmp` 源码副本执行，含 vendor/必要 metadata；父基线为 detached 稀疏 worktree，再建立运行副本。父子进程同级隔离 v3 根保持一致，不读取原 v3 assets/evaluation、v4、金标、真实题面或封存逐题 run。普通合成夹具不是科学性能数据，不外推 dev 或 298。判分零 LLM，不调用外部模型/真实 provider、不 push、不 commit。只新增本报告及本轮证据目录。

## 2. 独立执行数字及父基线分类

| 项目 | 本轮独立结果 | 分类与限度 |
|---|---|---|
| 当前 PPV1 全量 | **951 passed / 0 skipped，exit 0** | 实际 35 个 `test_ppv1*.py` 文件；不是交付表的 34 |
| 当前 G01 安全隔离 | **1553 passed / 8 skipped / 17 deselected，exit 0** | 295 项输入，执行前后 SHA-256 全部相同；不是原真实依赖环境全量 |
| 父 8735601：同字节新增回归 | **19 failed / 0 collection 红** | 11 未发生预期拒绝＋5 值断言＋2 缺 `ledger` 签名＋1 缺摘要字段；不能统称 19 个行为翻转 |
| 父：三个更新的既有测试文件 | **4 failed / 72 passed** | 4 个失败用例为版本字面量；实际 diff 有 9 处字面量改动行，不是交付称 6 处；72 绿包括合法与拒绝控制 |
| legacy 实际两树专项 | **4/4 产物逐字节相同** | 两个合成 run，每个两种产物；本轮重新执行两树，不借用旧产物冒充本轮执行 |
| legacy code identity | **52 文件聚合不变** | `18007e6a7cc239606eb30921f91045540446a7d7298108be30d47fce2f1374d6` |

951/G01 的首次有效执行均一次完成，本审没有账号额度中断或重跑已通过全量。旧反例脚本和本轮适配观测分别保存，不把旧脚本按设计拒绝后的未执行内部控制报成通过。

G01 的 8 项实际 skip：v4 对照 parser 不在隔离根 1 项；phase_d 的 v2 provenance/summary 未生成各 1 项；冻结 v3 真实评价依赖缺席 5 项（batch whitelist、evaluator dev CLI、wrong split、missing lines、route bucket）。17 deselect 为 16 个 slow 真实/对照工程节点及 1 个明确排除的 charge fixture 原评价资产依赖。完整 nodeid、时点和原始理由见 `execution/g01_exclusions_detail.json`；缺席不当作通过。与上一轮 932/1534/294 历史分别登记。

## 3. 四组逐项收口与继承验收

| 项目 | 本轮实际证据 | 裁定 |
|---|---|---|
| S4-C01 | 原 7 个公开 start/resume 输入＋严格 endpoint/native/v3 读回；必要 oxygen 未知及冲突均进入阻断并保留全文；已知、兼容、无必要条件支持控制保持；原 5 边界控制均保持 | **关闭** |
| C01 历史/来源边界 | 文献参考 basis 不强制阻断；旧 unknown→新阶段已知仍保留旧未知，旧已满足→新阶段相反不重评旧边；同源条件摘要随 endpoint 首消费使用 | 3 个补充控制通过；不是世界真实条件认证 |
| S4-C02 已修部分 | 四种 manifest-only 改坏拒；自洽换 run/版本/策略拒；漏一项引用而原文件仍在、坏 H07 文件仍在均拒；原正常导出保持 | 自 digest/run/版本/策略及存在项集合比对有效，但**必要文件缺席残余未闭合**，见 §4 |
| S4-C03 | 原公共反例 4/4 soutc 全文聚合；空 task_key 的 child 不再漏，`no_local_candidate`/`unresolved_continuation` 保留；坏 child 在 build/read 双拒；manifest 同源索引 | **关闭**；C02 文件消失集合问题归 C02，不重复挂组 |
| S4-C04 已修部分 | 裸假 native＋真引用构建拒；投影-only 自洽换内容＋真引用读取拒；真来源正常无/有 ledger 均可读 | 原两案翻转，但**无 ledger 来源版本首消费残余未闭合**，见 §4 |
| 公共完整链与确定性 | start/resume 三次公开恢复、同进程重导出及独立子进程 payload/manifest 逐字节保持；正常链预算/事件不重复 | 工程正控保持，不代替异常消费证明 |
| S3/首消费/恢复继承 | 当前全量中的 S3a/S3b、E01/E02/C06/H04、硬杀/barrier/H07/H08 等实际执行节点及已有关联控制保持；production/store/search/queue/model_protocol/runner 与父字节不变 | 未见回退；没有声称把历轮每一份历史探针全部重跑 |
| legacy/export_v3/AtomTool/G2 | 52 文件 identity 与两树四产物 byte 专项不变，production 字节不变 | 保持，不触冻结 legacy |
| 八拒绝 kind / 12 损失轴 / 空池 | 当前回归实际执行并通过；原生/v3 有损分工、反向禁止、诚实 unknown 及空答卷保持 | 保持 |

当前版本登记：profile-17、endpoint/policy-2、native-result-2、native-export/policy-2、v3-projection-2；store-10、runflow-5 等未升项仍由实际 profile 及 code identity 覆盖。`runflow.py` 本批将生产读投影接入 `ledger=ledger`；因此不能声称全部源文件或接口字节零改动。

## 4. 剩余 P1 与最低验收

### S4-C02：文件与引用一起消失，必要集合就被缩小，坏权威继续被接受

**原验收归属：**上一轮 §4 C02 明定“自洽换新 digest＋单项/全部引用遗漏＋坏/缺 artifact”，必要集合从原生实际消费、action/task 与冻结计划权威列举；任务书 §2.B、§4.4 G02、§5.1。不是全库协同改写攻击。

**本轮公开反例：**从合法 start 的同一原生导出出发，删除 `stask-exp_186406fb43fba8a83c9e/production_report` 文件，只从 manifest 删除对应唯一引用，正确重算 manifest core/export_digest 并新目录落盘。公开 `read_native_export(ledger, run_dir, new_digest)` **接受**；请求原 digest 则正确拒 `export_reference_mismatch`。原 native payload 字节、新目录 payload 字节、native artifact 和数据库全部 17 表均不变，缺文件形态被保全，恢复原文件后的原 digest 正控通过。

**必要性独立证据：**对应 action `sact_c2fd17ef5a301a19c212` 是 done expand，有已登记 attempt、真实 commit 和 event `ppev_dbcef960767edb493ec0`；原生 `audit_production_reports` 引用同 task/action，所含 production_payload 与被删报告整对象相同。不是把尚未生产的候选文件一概当必需。详见 `export_chain/metadata/necessary_report_basis.json`，保存来源表行及整对象核对。

**代码：**`src/pathway_v43/pollutant/native_export.py:167` 的 `_necessary_artifact_reference_keys`，`:190–191` 对 `envelope is None` 直接 continue；`:677–692` 因而只比较“目前仍存在”的集合。`:612` 清单逐行校验能拒原 digest，但新清单把缺项摘掉后不再消费它，无法证明原生声明依赖完整。

**正式裁定：**mimo r18 第 63 条的读码警告已由本审执行证实，属于既定 P1 残余。不能仅写“集合闭合不抗全库协同改写”或风险说明后放行。本例没有改 DB/native 权威，不在该范围外豁免内。

**最低收口：**共用索引保留，但必须在读文件之前依据已完成 action/task/commit、实际原生消费和计划确定“应有必要项”；应有项缺文件不能变合法缺席。完整集合与每行有效分开核。覆盖删文件且引用仍在、仅删引用、文件＋引用同删＋自洽新 digest，至少 production_report 及同契约其它实际必需项；先结构化拒、零业务写、改坏/缺席形态保全。合法未生产、空池、deferred 和适用的共享/去重正控保持，不要求所有索引候选都存在。

证据：`export_chain/independent/results.json::single_ref_missing`；`independent/single_ref_missing/inputs.json` 及 `run_snapshots/` 保存原/新 manifest、原/新 payload、源文件和全表。观测脚本 exit 0 只是完成记录，**不是产品通过**。

### S4-C04：无 ledger 投影首读仍不核原生来源版本

**原验收归属：**上一轮 §4 C04 的“共用原生消费/绑定源”“已验证原生 manifest/payload”“API 可明示 ledger/已验证原生输入及版本”；任务书 §5.1 明定 v3 适配首次消费必须核版本，§5.4 旧资料按版本规则读取。不是新增数据库新鲜度要求。

**公开最小反例 A：**只把真实引用来源 manifest 的 `schema_version` 改成 `ppv1-native-export-UNKNOWN`，正确重算 core、新 export digest，并让投影 reference/投影 digest 指向该文件。不改原生 payload 任一字节，不改 steps，不改 DB。`read_native_export` 正确拒 `export_version_unknown`；`read_v3_projection(..., ledger=ledger)` 正确包装拒；**`read_v3_projection(..., 无 ledger)` 接受**。

**反例 B：**只把来源 manifest `contract_versions.profile` 改成 `ppv1-profile-UNKNOWN`，同样自洽重封装，payload/DB 不变。相同三入口分布：原生拒、带 ledger 拒、无 ledger 接受。另有 `native_result_version=UNKNOWN` 的文件变体无 ledger 也接受；这例改变 payload content_digest，带 ledger 先因原生 artifact 内容身份拒，因此不冒充三个版本门均独立到达。

**代码：**`v3_projection.py:578` 读取 API 的 ledger 可选；`:616–618` 仅带 ledger 才走 `read_native_export`。`:659–737` 的 `_load_bound_native_export` 核自 hash、字节、reference/run/图摘要，却没有核原生 schema、contract_versions 或 native_result_version，再由当前 adapter 派生字段而返回。`_load_projection` 核的是投影自己的版本，不能替代父对象版本门。文件自洽不是已登记可消费版本的证书。

**正式裁定：**无 ledger 不核 DB freshness 的文件级分工可接受，坏 H07/重封假原生的无 ledger 个别观测仅按该边界登记；本组阻塞限定于来源版本，不混入数据库真实性。拒 unknown/unsupported 父版本只需文件与共用版本登记源，不要求新增分布式签名、机制证明或科学门。

**最低收口：**构建、带 ledger 首读、无 ledger 文件级首读消费同一版本规范；至少来源 manifest schema/契约版本组与 native payload 版本齐全且已登记可读。缺失/未知/不一致分别结构化拒，先于当前 adapter 解释内容；若支持历史版本须显式登记对应 schema/adapter，不能用当前 adapter 默猜迁移。保留合法无 ledger 已登记源读取、有 ledger 完整授信、旧文件保全、12 轴/空答卷、零原生/业务写。

证据：`export_chain/independent/results.json::{unknown_export_schema,unknown_contract_profile,unknown_native_result}`；`metadata/unknown_source_version_scope.json` 钉定两最小案 payload bytes/steps/全表不变。

## 5. mimo 专项、交付一致性及 P2

冻结稿范围 §1（第 5–8 行）是判据一至五、0d/0e；第 46–48 行明排除 S4 endpoint；冻结记录 §8 对该范围定义下一判据版本触发。冻结稿 SHA-256 为 `7fd35aabdb4d2d5b67b0bf58693dab6f8765ad872efedf5f886503c4907064e4`，对父和冻结入库 `0e345e8` 均字节相同，冻结记录也不变。C01 是在既有同源条件评估基础上修复终点消费者缺失，且终点契约族已升版本。本审认可 mimo 对 criteria-v2 的专项结论；只采信到实际字节、运行及版本互证为止。

对 mimo 四项的主审回应：C01 条件性文字建议采纳，执行收口关闭；C02 不能当全文字条件，第 63 条程序风险已实证，继续 P1；C03 同意并已执行关闭；C04 原两案同意，但本审额外同契约首消费版本证据使整组未清零。源码行号已抽核，第 50 条引 `native_export.py:667` 作为目录命名落点错位，实际写/读目录在 415/461 附近；不把行号引用当执行结果。

交付数字及多数原案修复属实，然而“C02 整集闭合、坏/缺 H07 拒”“C04 首消费来源绑定已闭合”证明范围过大。新 19 回归不覆盖文件＋引用同时消失，也不覆盖无 ledger 未知父版本；全绿不能替代这两条消费规则闭合。交付第一段和用户转述“条件全文字级”不成立，r18 自己已经保留程序待验证项。

下轮应一并精确落字，均不单独阻塞：

- 19 红分为 16 行为/值红＋2 签名红＋1 字段红，0 collection；新测试头第 26 行仍误写 collection。版本更改 9 行对应 4 失败用例，不能报 6 个红。35 文件，72 绿含负控制，数字不是漏洞数。
- “879/914/932 存量零改动”限定为既有测试除披露字面量，不扩大成 endpoint/导出/投影行为零改动；本轮全量 951 也不能全叫存量。mimo 请求的 0f.11/0g.12 旧绝对表述仍待同步。
- 0f.1“评估只由证据决定”须同时引用必要条件限制，0h.6 的“0f/0g 化学含义都不变”缩回冻结一至五/0d/0e；历史快照、必需条件来源级及 observed 文献参考不强加门写清。
- 24 字符目录、endpoint 先消费后的拒绝优先级、H07 信封与内容身份分层、multi-reactant 公共生产未覆盖、stop 副本与权威分工继续披露，不追加本轮机制/性能验收。
- 无 ledger 文件级版本/内容证明与有 ledger 当前 DB 完整授信分写；保留 full coordinated DB/artifacts 改写范围外，只不能用来豁免 §4 的最小文件变体。

只读校验实施归档：实际 manifest **304 条记录**，记录与 SHA256SUMS 相符。其 `head_at_execution` 是父提交＋未提交源改动，不能冒充本轮独立已提交 HEAD 执行。两项环境准备 suite 事故、一次控制器 IndentationError、旧探针预计早停见原 metadata；本审留副本但不重签来源，不把准备失败当产品 P1。

## 6. 证据、准备错误与完整性

永久目录：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s4_codex_r2_2026-10-08/`。

- `execution/README.md`：独立 PPV1/G01/父基线/legacy，完整 stdout/stderr/JUnit/argv/env/exit，295 输入 SHA、8/17 逐 nodeid、实际身份及 schema；当前和父测试同字节。
- `endpoint_contract/README.md`：复制旧输入、七公开场景/五边界/历史及文献参考控制、严格读回、冻结与行号互证。夹具 basis 名及转换必要参数准备错误原 log 保留，修正输入后单次补证；不改产品、旧永久证据或原断言。
- `export_chain/README.md`：旧两脚本逐字复制到 tmp 的早停、原/补充控制、本轮独立逐案输入输出与全表快照、正常公共恢复/子进程字节控制；原脚本拒绝后未跑段明确不报通过。
- `root_audit/`：125 项原仓输入与旧确认永久目录 357 文件 SHA 快照、交付归档只读 SHA 审计、材料/源码片段及精度判断；`workspace_integrity.json` 验发布前后唯一新增两路径。
- `manifest.json`、`SHA256SUMS`：全附件相对路径 SHA-256；外层包含子包控制文件，只自排除外层 manifest/SHA 两文件。`report.sha256` 绑定本报告；子包各有独立 manifest。

本审无额度中断，所有有效全量已完成不重复。启动时旧轮执行 agent 名已失效，重新派本轮三个子代理，未借此重复已完成 suite。root 一次读错源码包路径立即按 rg 定位修正，无验证结论依赖该失败。root 完整 inventory 核验还发现出口首封包按 basename 排除过宽，漏算 47 份嵌套业务 manifest；保留首包不动，在新 `package_complete` 保存初次清单/脚本/遗漏说明，按根目录控制文件重新完整封装。只补哈希，不改行为输入输出、不重跑探针；发布前外层及三个子包完整清单均已验证。探针早停与准备输入错误详见各包；旧化学/系统断言按原目的保留，不反改旧证据。外层发布后只读哈希验证，不在永久目录运行任何写库程序。

执行 wrapper 使用 `-B`、`PYTHONDONTWRITEBYTECODE=1`、pytest cache 关闭；G01 既有非 PPV1 子进程仍在 tmp 生成 7 个 pyc，记录副作用并不归档，源码哈希不变。本审没有对 G01 全进程做 socket 计数，未主动调用模型/provider 与专项脚本网络零要分开。SQLite 二进制不归档；逐案探针保存全行 JSON/schema/hash，suite 库仅最终 SHA/schema/count，不当逐案全行证据。

## 7. 正链放行条件与 S5 前置

**S4 仍不通过，仅剩 C02/C04。**C01/C03、S3 与已证正控保持关闭；下一轮只收 §4 两组及相关 P2，不扩展科学门、不重做冻结。两组须同入口矩阵覆盖合法与坏输入，先拒、零业务写、保全原文件，并由公开链及独立探针互证。当前 951/G01、冻结正文、legacy、正常链及确定性可确认；完整必要来源集合与所有首读版本门尚不可确认。

两组清零后按既定阶段收口，S4 完成交接点正式成立；届时 S5 的任务书、评测域/留出、统计预注册、阈值、费用、真实 provider、金标/题面及 teacher 边界仍由用户另行授权。当前不访问这些材料、不宣布科学性能、不自动启动 S5。既有 `ppv1-criteria-v1` 冻结记录有效；今后若改一至五/0d/0e 冻结口径，另行登记 criteria-v2 请求及用户裁定，不借本次专项授权。

## 8. 下轮有限范围回修提示词（可直接转交实施 agent）

```text
你在 /Volumes/CC/Enzyme_Agent/dependingv43 实施 pollutant_pathway_v1 S4 回修。
读仓内 AGENTS.md、POLLUTANT_PATHWAY_S4_CODEX_REVIEW_R2_2026-10-08.md §4/§5/§7、
S4 任务书 §5.1/§5.4；HEAD 基线 0dd35d14d6539fbf134be18565f6709e852fc076。
只收剩余 S4-C02/S4-C04 与精度 P2；C01/C03、S3、合法控制保持关闭，不加新科学门。

开工先列 build_native_result/build_native_export/read_native_export/
build_v3_projection/read_v3_projection（带和不带ledger）/公开start-resume 的入口矩阵，
每口登记必要集合、独立权威、版本/身份/hash/证明范围及合法缺席。

1. C02：应有必要artifact不能由“目前文件存在”决定。依原生实际消费与已完成
action/task/commit/计划同源闭合，再分别核集合和每行。
复现本报告 single_ref_missing：删已完成任务production_report＋删manifest同ref＋
自洽new digest，DB/native均不改，必须先结构化拒，零业务写，缺席形态保全。
同规则其它实际必需项适用；合法未生产/空池/deferred/共享去重正控保持，别一刀切所有候选。

2. C04：无ledger文件级投影首读先核父manifest schema/contract_versions和native payload
版本；与有ledger及构建共用登记源，不用当前adapter默猜未知或缺失版本。
至少unknown_export_schema、unknown_contract_profile两最小案（payload/DB不改）拒；
native_result版本与版本组缺失/冲突覆盖。历史版本若支持须显式对应adapter。
无ledger不强加DB新鲜度，但不得把未知来源版本包装成已验证结果。
合法无/有ledger读取、有损12轴/空答卷、旧文件保全和零原生/业务写保持。

P2同步本报告§5：35文件，19红=11缺拒绝+5值+2签名+1字段，0collection；
9字面量行/4失败用例/72控制绿；旧“零改动”限定测试字面量例外；
endpoint实际变化与criteria-v1冻结范围分写；mimo第63条不是纯文字条件。

新增回归对直接父0dd35d1跑同字节，区分行为/形态/字段/版本/collection与正控；
独立PPV1全量/G01安全隔离，逐项缺席披露，输入SHA前后核对。
将本轮永久证据脚本复制fresh tmp，不在旧证据内建库或修改断言；复合早停后未执行段单列。
附入口→行为→验收、逐案输入输出、全表/文件保全、命令/exit和SHA证据，自包含mimo请求
只含规则及合成例，不外发题面/金标。代码语义/身份按既有版本规范登记，不改冻结判据。
不动legacy/G2/AtomTool，不含S5；不访问金标/题面/封存逐题run/原v3评价资产。
实施交付按仓规本地显式路径提交，不push；Codex报告/回应/旧证据不代为提交。
```
