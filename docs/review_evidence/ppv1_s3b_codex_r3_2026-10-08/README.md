# PPV1 S3b-r3 Codex独立复审与S3工程交接证据

日期2026-10-08（Asia/Shanghai）；实际HEAD `adf0287abef0c4803962fee0df0065d8e6f3793d`，父 `2bedfc060a9b19019ba44aa2a56dcacb88450c3b`。

报告：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_R3_2026-10-08.md`。

**S3通过，唯一残余S3B-01关闭，P1=[]。** S3a及02～06保持；达到S3工程完成交接点，自动回修循环停止。判据仍未冻结、科学性能pending、S4/S5未实施。报告§6为mimo v15改字/取证清单，§7为阶段交接。

## 1. 导航与数字来源

| 路径 | 内容 |
| --- | --- |
| `execution_specialist/README.md` | 独立PPV1879/0/0、32文件；父同字节新8=5行为红/3合法绿，0collection/版本/字段红；safe G011481/8/17、288输入SHA；全部日志/JUnit/命令/env/schema/源码vendor/metadata/精确允许字节；父合成全表及production/legacy/core字节核验 |
| `anchor_specialist/README.md` | 真workflow.runner公开B3/B4原反例翻转、11缺/坏/后段锚拒绝控制、四硬杀/坏输出隔离/转换四窗口/三产物/并发工具入口1，全部输入/输出/十五表/被改artifact及身份；38观察=36符合+2header-onlyP2 |
| `handoff_specialist/HANDOFF_READBACK.md` | mimo v15七改字及行号互证、历史父基线错误更正、完整P2/冻结/S4/S5路线。当前RDKit五写出/往返正控+六别名拒绝、九public生产控制、六仅读捕获语义断言；真实工具/audit/准入/提交trace及unknown/Audit异常 |
| `input_snapshot.json` / `workspace_integrity.json` | 4554明确白名单原文件SHA（含完整旧R2合成证据manifest路径）、HEAD/父/git差异与既存AGENTS用户改动保全；只两授权新路径 |
| `run_metadata.json` / `review_execution_events.json` | 各集合与P1闭合、科学/冻结状态、一次执行无环境纠错/额度中断、两novel请求数observer只读更正、headerP2不冒称版本拒 |
| `draft_crosscheck.json` | 三专项只读互证草稿，纠正文件数/用例数、逻辑表快照与binarySHA、当轮observer命名、license/scope范围及交接映射；未改源码/原日志/旧快照 |
| `package_assembly.json` / `assemble_evidence.py` | 三冻结包按pinned manifest和源/复制SHA纯归档，无项目导入/行为执行/数据库打开 |
| `manifest.json` / `SHA256SUMS` / `report.sha256` | 所有附件及嵌套manifest/控制自身SHA，外层manifest自身SHA与独立报告SHA |

三专项payload **1251+874+263=2388文件，56,246,203 bytes**；各3controls，原包纯复制2397文件。SQL二进制省略，以完整表/schema JSON及实际采集SHA保存；缺少的before binarySHA不倒补。读取/执行来源与实现方自报/mimo读码/历史执行分开。所有数字为工程规则级，不外推dev(B1路径中间步骤)/298(RHEA酶学)科学性能。

G01一次：288=228本仓白名单（含源码/测试/配置/脚本/非题面资产）+42普通v3src+18非题面镜像，源/副本SHA前后一致；8skip=5真实冻结评价+1v4对照+2phase_d派生metadata，17deselect=16slow+明确export项；全部nodeid/reason见 `execution_specialist/g01_exclusions_detail.json`。输入tar288成员逐SHA核验，不进入真实题面/金标/封存run/v4/原v3资产补数。

## 2. 唯一P1关闭的具体取证

`anchor_specialist/observations_r2.json` 是复制脚本的历史文件名，**实际HEAD为r3**；两case：

- `self_consistent_replaced_plan_after_bundle_written`（B3）。
- `self_consistent_replaced_plan_after_event_submitted`（B4）。

在 `adjudicated_summary.json`、`inputs/<case>_mutation.json`/`*_resume.json`、`logs/<case>_resume.execution.json`及stdout/stderr、`tables/<case>_start.json`/`*_mutated.json`/`*_resume.json`、`artifacts_final/<case>/results/run-plan/frozen_plan.json` 核对完整数据。

原根digest `880bf6c37d09af15db7a82ad19cfd9aa4b4d1d52eab0efe256e8dd08babdeb94`，新artifact `7164d4f966b107f19544e5e0a0cac7a4a80ce22e7f289f24a5ebc8c7fe3acd04` 与R2输入完全一致；root已done。省plan public resume现在 binding_mismatch，十五业务表同值；B3 event0/commit2、B4 event1/commit2不增，无新转换，被改文件逐字节保全。

`anchor_observations_r3.json` 中11拒绝控制有 `consumer_entries_resume=[]`、business_table_count15、表同值和artifact保全。代表kind：

- missing：`anchor_missing_anchor_after_bundle_written` / `...after_event_submitted`；另根行删除。
- corrupt：`anchor_corrupt_anchor_digest_after_bundle_written` / `...after_event_submitted`；另task_key列/载荷、不可解析/非dict。
- mismatch：`anchor_replaced_with_matching_argument_after_bundle_written`、`anchor_self_consistent_replaced_plan_done`。

消费instrument证明recover_run/drive/工具入口均0，拒绝先于B3事件/B4补账/调度/consume。代码以数据库根retrieve行的原digest、同一decision_task_key重算为独立权威，resume先核后recover。计划自hash不再当独立证书。合法同/省略/显式同计划、原转换、全部继承仍完整可执行，不以全面拒绝换通过。

## 3. 不夸大的限制与P2

父五红全部public resume正常返回后的未预期拒绝；后随零写/保全断言未执行，父最终表仅读已成数据归档，不能说负控所有内部断言执行了。三父绿完整执行。当前新8在879里，未额外重跑焦点。本轮没有环境误配/重试/额度中断；R2曾有环境纠正、首轮曾有额度事件，各旧快照保留原样，不改写。

两个本审novel observer错误期待请求恰1，实际3/2包括合法产品后续decide；按现成完整输出更正≥1，raw false保留，不重跑。另两header小控制改未知/删plan_version，plan/root/task原内容完全不变，B3仍消费原有效bundle，无新转换/工具重执行。loader未解释header；P2元数据规范/校验，不宣称该字段已拒/未来schema已认证，不把它冒称新计划内容接受。

锚与artifact不同DB/文件通道、同一run存储环境，不抗权威协同全改；同机flock不认证分布式/external exactly-once。driver.lock披露可重写，零写指业务表及被改输入保全。三产物夹具预算30（旧20）诚实披露。novel event appearance源标签仍synthetic-pool-spec，proposal_context/冻结响应可追溯，不认证现实来源或逐字全链一致。

未计算独立canonical表逻辑摘要，本包保全解码表比较与JSON文件SHA；不将文件hash说成前者或before SQLite binaryhash。Audit异常负控event0/hyp0、failed结算仍有commit3，不说全库零写。历史R4父绿11+1/人工widecatch负控未重跑，原证据保持。全部当前脚本/source头与真正HEAD、实际runtime/schema区分。

## 4. 只读哈希验证

下列命令只读字节/JSON/SHA，不导入项目、不执行行为、不打开SQLite、不写本目录：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3b_codex_r3_2026-10-08/verify_evidence.py --evidence /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3b_codex_r3_2026-10-08 --report /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_R3_2026-10-08.md
```

外层清单纳入嵌套manifest/SHA控制本身；SHA256SUMS再钉外层manifest，避免自身循环。handoff的alternate `MANIFEST_SHA256`也逐SHA核验。publisher为目标尚不存在时的一次发布器，**已发布后不能运行**。回执放当时新tmp，不回写封存包。

## 5. 复现与交接纪律

若需要行为复现，先整包复制到fresh tmp（src/vendor/metadata/脚本齐），按专项README重设新runs_root与同一隔离V3路径；不要直接执行旧original_inputs的历史绝对路径，不在永久证据建库或改日志。本审均禁bytecode/pytestcache；portable工程控制器只AST检查，未再次运行。

报告§6七项mimo改字尚需新冻结稿同步；本审不回写请求/回应/源码旧注释。§7先用户/teacher确认版本与proof_scope、完成文案与证据引用，然后另行启动S4终点/原生导出、S5数据/科学验收规格；科学数据/费用/金标授权另循红线。回修自动循环到S3停，不自动冻结或跨阶段。

仅新增本报告和本目录，既有源码/测试/docs/AGENTS与完整旧R2证据不变，无commit/push/外部模型/真实provider/网络。本目录封存后只读。
