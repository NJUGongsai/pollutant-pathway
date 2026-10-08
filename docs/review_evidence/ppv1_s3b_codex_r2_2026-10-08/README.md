# PPV1 S3b-r2 Codex 独立复审永久证据

实际日期：2026-10-08（Asia/Shanghai）。HEAD：`2bedfc060a9b19019ba44aa2a56dcacb88450c3b`；父：`c1211183c0874b12c5b5461845d3c61f0a84719c`。

报告：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_R2_2026-10-08.md`。

**S3不通过，唯一 P1=S3B-01 后段冻结计划身份锚定。02～06关闭，S3a/真实化学链及不吞Audit异常成功保持。科学pending，判据未冻结，未到S3工程完成交接点。**

## 1. 导航与独立数字

| 目录/文件 | 内容 |
| --- | --- |
| `execution_specialist/README.md` | PPV1最终871/0/0（31文件）；父新20=13行为红+2形态红+5绿；父旧3=3失败/52绿、合计18/57；G01安全1473/8/17、287白名单输入SHA；全部命令/日志/JUnit/schema/源码vendor/metadata/精确输入，legacy/production父当前字节核对 |
| `recovery_specialist/README.md` | 25顶层观察=23符合+2同S3B01反例；四真公共硬杀、计划普通拒/省略合法、坏artifact隔离+独立C、三产物部分恢复与转换新context、双真实workflow.runner.resume_run barrier/工具计数/接管，全输入输出十五表/原始artifact |
| `protocol_specialist/README.md` | 21行为child、20单独执行收据（zero_depth同label覆盖限制详述）；novel实际工具/audit/准入/事件链、底物档案、stop持久blocked/多原因；badproof/坏state/工具失败三None/合法unknown；mimo行号事实互证与源标签P2 |
| `input_snapshot.json` / `workspace_integrity.json` | 根1028白名单既存文件SHA、HEAD/父/git差异与用户AGENTS差异保全，发布只两个新路径 |
| `review_execution_events.json` / `run_metadata.json` | 初次隔离V3根不一致与一次必要纠错、本轮零额度中断、probe早停/日志覆盖限制、最终数字来源与P1闭合集合 |
| `draft_crosscheck.json` | 三专项只读互证草稿、更正C06/H04标签、barrier位置/工具计数范围、缺novel内容非failed结算等；未改源码/断言/原证据 |
| `package_assembly.json` / `assemble_evidence.py` | 冻结三包逐manifest/源/复制SHA和控制清单核验，不导入项目、不运行测试、不打开数据库 |
| `manifest.json` / `SHA256SUMS` / `report.sha256` | 所有payload及嵌套manifest/控制SHA、外层manifest自身SHA和独立报告SHA |

三专项payload：2195+668+436=**3299文件，64,026,294 bytes**；内嵌控制3+3+2=8文件，原包纯复制3307文件。源码含vendor/必要metadata；合成SQLite二进制省略但有最终SHA和可读全表，不能说采到了未记录的运行前binarySHA。全部数字为工程合成规则级，不外推dev(B1环境路径中间步骤)/298(RHEA酶学)科学性能。

安全G01：287输入=227本仓白名单（含配置/脚本/非题面资产）+42普通v3/src+18非题面资产镜像，前后SHA同值。8缺席依赖=5真实冻结评价+1旧v4对照+2phase_d派生metadata；17排除=16slow+明确export项，全nodeid见 `execution_specialist/g01_exclusions_detail.json`。旧历史各轮1110/1138/1196/1250/1299/1389/1453数字不混计。本审没有进入缺席路径补数。

## 2. 唯一阻塞的完整取证入口

在 `recovery_specialist/adjudicated_summary.json` 找两项：

- `self_consistent_replaced_plan_after_bundle_written`（B3）。
- `self_consistent_replaced_plan_after_event_submitted`（B4）。

各自 `inputs/<case>_mutation.json` 保存旧/新完整artifact信封，`*_resume.json`为公开输入；`logs/<case>_resume.execution.json`及stdout/stderr含实际命令/env/返回；`tables/<case>_start.json`/`*_mutated.json`/`*_resume.json`保全十五表。只改变计划文件、重算其自身hash；原run身份/root摘要/task/DB不变。省plan公开resume成功并各新增一次phase-injected转换。

root原digest `880bf6c37d09af15db7a82ad19cfd9aa4b4d1d52eab0efe256e8dd08babdeb94`；artifact新digest `7164d4f966b107f19544e5e0a0cac7a4a80ce22e7f289f24a5ebc8c7fe3acd04`；plan_version保持ppv1-frozen-plan-1。改artifact前/后逻辑canonical十五表SHA同值，不冒称运行前SQLite二进制SHA（该项当时未采集）。这不是整库同步伪造要求；既存独立旧摘要可对照，但只在root retrieve实际运行时比较，B3/B4已done不再触达。源在包 `src/pathway_v43/pollutant/runflow.py:224/572/1262/1358`及 `source_review_lines.txt`。

已关闭反例定位：普通changed/decide_changed先拒、两坏bundle隔离、bad_bundle_independent_task只合法C工具1、三产物2/3硬杀补3/3、全部转换恢复phase-1、公开双resume工具1/原attempt预约复用、novel空非空event1/2、zero_depth原因/对象/repeat保持。精度/限制按各专项README，不把观察数当pytest或漏洞数。

## 3. 环境纠错、早停和日志限制

首次工程父进程V3根为absent_v3，worker清env后默认dependingv3，十项在代码身份门提前拒：PPV1初次861/10；父新20初次17/3。原stdout/stderr/JUnit保留。统一到同一隔离默认路径后，只完整重跑PPV1和受影响父新20；父更新3文件及G01一次。最终入口 `execution_specialist/independent_execution_results.json`；原 `execution_summary.json`仍描述首次，不把它覆盖成最终数字。**本轮无账号额度中断；首轮中断-续跑在首轮永久证据保持原样。**

父15红里2形态红：缺frozen_plan文件例没有进入篡改/恢复；transition pending_followup缺字段例已经resume并核转换done，但其尾部新context断言未执行。当前全量20通过；真正父绿五项与abstain空池父红按分类JSON，不按函数命名。交付旧表格54绿应52绿，合计18/57对。

协议controller旧observer字段导致补充捕获早停，完成child不重跑、余下未完/新合法控制分开。原zero_depth与resume共旧label，原worker日志被后次覆盖；第一次完整stop/counters保留在controller stdout/observations/zero_depth_initial_extraction.json，不能伪补两份独立worker原日志。其余20独立收据齐。raw源标签等更严oracle的false保留，P2与实际独立消费成功分开。全部控制限制及原错误stderr入包。

交付r2 worker调用低层start_ppv1_run/resume_ppv1_run（包括子进程并发）；根独立恢复专项才是两个workflow.runner.resume_run进程。该专项barrier在expand入口/工具之前，竞争方先拒后释放，真工具收据1；不把它误称toolbarrier，也不把最终event去重当唯一执行证明。

## 4. 只读清单验证

此命令仅读字节/JSON/SHA，不导入项目、不打开SQLite、不运行行为、不写本目录：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3b_codex_r2_2026-10-08/verify_evidence.py --evidence /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3b_codex_r2_2026-10-08 --report /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_R2_2026-10-08.md
```

外层清单不自我循环：SHA256SUMS钉外层manifest，所有嵌套manifest/控制本身入外层清单。`publish_evidence.py`只用于目标尚不存在时的一次发布，**已发布后不可运行**。验证回执放当时新tmp，不回写封存包。

## 5. 行为复现与仓库纪律

如确需复现，先整包复制到fresh tmp，包括src/vendor/metadata，再按专项README/script重设新runs_root、输入路径、V3根及当前HEAD；不可在永久目录或旧历史输入的绝对runs_root原地运行。不得为了重现工程数补真实金标/题面/封存评价。工程portable控制器仅AST校验，本审未额外执行；不能把其可携带性当已再次跑测。

`original_inputs/`含历史tmp路径，仅用于比对，禁止直接向那些根写数据。本审三产物给total预算30（旧20）留余量，化学/硬杀同规则，未宣称整体输入字节相同。SQL逻辑快照与binarySHA是不同指标。独立验证、交付自报、mimo只读推论、历史执行各有来源，不能互代。

主仓仅新增报告和本目录；无源码/测试/既有docs/AGENTS改动，无git提交/push，无真实模型/收费provider。仅原S3B-01有限回修，报告§8可交实施agent；S4/S5、判据冻结、真实评测仍须阶段交接裁定。本目录封存后只读。
