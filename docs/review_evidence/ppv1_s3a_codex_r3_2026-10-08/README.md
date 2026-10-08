# S3a-r3 Codex 独立复审证据

日期：2026-10-08（Asia/Shanghai）。实际HEAD：`41d0cd55f3def050a62325f00235cf22da302d2e`；直接父：`dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`。

**S3a 不通过；S3b 暂不可启动。** 原 S3A-01／05 保持关闭，R2行级旧反例已修，但三组各有同合同内残余：02必要预约集合缺项；03请求状态口未核冻结策略；04未知状态可正常写failed。

报告及有限回修提示词：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R3_2026-10-08.md` §4／§8。

## 数字与证据入口

| 独立执行 | 实际结果 | 证据 |
| --- | --- | --- |
| PPV1全量 | 697 passed／0 skipped／0 failed | execution专项套件日志／JUnit |
| 父dcb7同字节新增49项 | 40 failed／9 passed／0 collection error | execution专项父日志与逐case分类 |
| 40失败细分 | 28 Integrity＋3 Contract＋2 Recovery＋2 IdentityConflict未发生预期异常，5值断言 | 35未拒＋5值断言，全行为红 |
| 9保持控制 | 4合法＋5既有坏输入拒绝控制 | 不是9合法化学样例 |
| 安全G01 | 1299 passed／8 skipped／17 deselected | execution专项完整skip／deselect nodeid及理由 |
| 白名单输入 | 276=当前仓216＋ordinary v3 source42＋本仓普通资产镜像18 | tar成员及前后SHA，未取缺席依赖 |
| 必要集合 | 54坏案接受、9合法保持；另上限1两条完整链对照 | authority专项完整输入／前后表／返回 |
| 预算／请求／停止旧矩阵 | 114／114符合合同，63停止优先级组合保持 | budget_request专项只读裁定与原日志 |

当前49通过从697全量JUnit筛出，不相加。本审没有把交付方额外49、23及更新既有1／22跑数作为独立重跑。工程合成数字不代表dev（B1环境中间步骤）或298（RHEA通用酶学）科学性能。

实际环境depending43 Python3.11.16／RDKit2026.03.6／SQLite3.53.4，profile11／search3／store9／limits3。所有运行在新仓外tmp，Python -B、禁bytecode／pytest cache。

## 三个冻结专项

- `execution_specialist/README.md`、`STATIC_FINDINGS.md`：PPV1、父新49、安全G01、逐item红分类与缺席依赖、runner双入口、legacy身份、store事务／幂等；窄化学15案＋RDKit实际CX token7案及mimo八条件。含完整stdout／stderr／JUnit、argv／cwd／env／exit／耗时、HEAD／schema、完整隔离source／vendor／metadata、同字节测试和276安全输入tar。
- `authority_specialist/README.md`：旧27分案、120分段（111坏拒、9合法）、done2、四硬杀＋双进程barrier、H07／H08、defer坏行与合法共享／非expand／failed attempt控制；新增必要集合63与上限1完整双链。每反例完整14表前后JSON、实际原输入／输出与脚本／适配diff；旧crash按原6表控制快照，另含worker完整输入输出／schema。省略238合成SQLite二进制，`omitted_databases.json`逐SHA／大小登记，未丢原公共参数与输出日志。
- `budget_request_specialist/README.md`、`SPECIALIST_REVIEW.md`：原有效114、63优先级、null／缺版本10消费模式拒，18坏策略请求状态案实际写入与合法控制、unknown→failed、foreign-run范围边界、原脚本失败与只读裁定。含逐案全输入／表前后／返回／异常和source／metadata／脚本／SHA。

子包manifest原字节保持：execution266 payload、authority409、budget_request150；加各自清单／SHA控制后268、412、153文件。实际路径、复制前后SHA及tar内276成员安全哈希见`package_assembly.json`。没有把省略库清单当待复制文件，也没有打开或解压tar执行。

## 早停、准备错误与采信边界

旧observed按修前缺口断言，在修复后按设计失败，未到内段不记通过。done2已完整捕获后adapter误期待SearchIdentityConflict，实际为SearchContractError；只读更正断言，没有重跑两案。预算补充末段合法装配控制误删version，前31案已捕获；未到后段保留失败，另补正确带version控制。各专项保留原stdout／stderr／exit及更正解释，不改旧输出充绿。

本轮执行、三个专项包与暂存归档均已完成，永久发布前被ChatGPT账号用量上限中断；用户恢复额度后授权续跑，2026-10-07 18:04:51 UTC恢复盘点。`INTERRUPTION_RESUME.json`登记时间、来源与复用结果；中断准确起止未知，用户称约5800行输出未独立计数。本次只补文档与SHA发布，未重跑任何已完成套件／探针，也未复用实施方套件输出冒充独立执行。mimo v11为外部既有只读回应，不由本审调用；代码和执行互证。真实CX token／外异常类与内reason.kind／失败诊断和下游audit各轴范围分开，详见报告§6，不凭读码宣称运行。

两事务间不持锁、保守defer拒未归因event、foreign-run pending作用域省略为既登记P2边界；未知状态实际写failed有原生命周期证据，不能仅当缺错误名。S3b生产caller／调度仍未交付，不提前增门。

## 完整性与只读核验

`input_snapshot.json`、`workspace_integrity.json`：1072个明确既存输入SHA、HEAD／父、tracked diff及status前后核对，原AGENTS差异、.zcodeignore、旧评审资料／永久证据保留。主仓只新增报告及本目录，未commit／push。

`run_metadata.json`、`report.sha256`、`manifest.json`、`SHA256SUMS`：实际结果、报告SHA与全部本目录附件（包括嵌套manifest／SHA）。外manifest排除自身和根SHA256SUMS；根SHA256SUMS另外覆盖manifest本身。

以下只读核验不导入项目、不打开数据库、不执行probe：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_r3_2026-10-08/verify_evidence.py \
  --evidence /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_r3_2026-10-08
```

`assemble_evidence.py`／`publish_evidence.py`是本轮实际一次归档控制器，不是再次测试证据；包含原tmp路径，仅供记录，不在永久目录重跑。

若需复现实验，先按专项README把脚本、合成输入、完整src／vendor／metadata复制到新的仓外tmp，给新输出根。便携控制器仅静态语法校验的，不能当已执行实验。不得在本目录原地写库／日志，不改历史manifest。

不访问真实金标／题面／封存逐题run／dependingv4，不真实provider／网络／外部模型，判分零LLM；不宣布判据冻结、科学性能或S4／S5完成。
