# S3a-r4 Codex独立复审永久证据

日期：2026-10-08（Asia/Shanghai）。实际HEAD：`b7f2bba02ca49edd0a45a13bc9b8434909d99175`；父：`41d0cd55f3def050a62325f00235cf22da302d2e`。

报告：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R4_2026-10-08.md`。
结论：**S3a通过，P1清零，S3b可启动**。缓存同构边界接受为限定范围P2，不能据此声称所有检索消费历史真实性已认证。科学性能pending、判据未冻结。

## 1. 独立执行与目录导航

| 目录 | 内容／本审结果 |
| --- | --- |
| `execution_specialist/` | PPV1 787／0；父基线78红／12绿，77行为＋1缺字段；安全G01 1389／8／17及277输入SHA；源码／测试隔离副本、完整命令日志／JUnit、CX及化学精度控制、静态互证说明 |
| `authority_specialist/` | 原54必要集合坏案＋9合法，B3零event新增，四硬杀／双进程barrier，旧行级与artifact／提交控制，上限1双链、7缓存同构控制；原输入输出、全表JSON、正确只读断言、历史早停说明 |
| `budget_request_specialist/` | 原冻结策略／未知状态31完整控制、合法装配两案、35全表补充、有效114矩阵、63优先级、10冻结块控制，原失败脚本与只读合同裁定 |
| `input_snapshot.json` | 1002既存输入文件SHA、实际HEAD／父、初始tracked diff和工作树；包括R3永久材料只读清单 |
| `package_assembly.json`、`assemble_evidence.py` | 只复制各冻结包manifest声明附件；逐SHA、无链接／缓存／数据库二进制；安全输入tar只读成员校验，不解压 |
| `run_metadata.json` | 本轮身份／版本、独立数字、执行边界、当前轮无额度中断和归档零重跑记录 |
| `workspace_integrity.json` | 发布前后1002输入不变、实际HEAD／父不变、旧差异保全、主仓仅新增报告与本目录 |
| `manifest.json`、`SHA256SUMS`、`report.sha256` | 全部归档附件含嵌套manifest的SHA，外层manifest自身SHA，报告SHA；清单不自我循环 |

三个专项包有独立README及说明（工程的 `STATIC_FINDINGS.md`，权威的 `AUTHORITY_REVIEW.md`，预算请求的 `SPECIALIST_REVIEW.md`）。嵌套包原manifest／SHA控制逐字保留。执行命令、stdout／stderr、退出码、完整分案输入输出及相关表快照在对应子目录。

## 2. 只读复核

下面命令只校验文件与报告哈希，不导入项目，不开数据库，不运行测试，不写本目录：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_r4_2026-10-08/verify_evidence.py --evidence /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_r4_2026-10-08 --report /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R4_2026-10-08.md
```

实际Python路径以工程专项run metadata为准；如环境安装根不同，使用该已登记depending43解释器。本轮永久发布工具 `publish_evidence.py` 只允许两个目标均不存在时新增，带source guard；已发布后不能在此原地再运行它。

如确需复现行为，**先复制相关完整专项包到新tmp**，按包中实际命令与新批次根执行；不得在本目录或R3永久证据原地建库／写日志／改结果。安全G01的输入tar只含已白名单普通输入，任何额外真实数据不可补入。此目录附源码是证据快照，不是实施目标。

## 3. 数字与早停边界

测试数字是工程合成验证，非漏洞数、非dev或298题域科学性能。当前90新回归是PPV1 787子集，不能再加；父78红只有77行为，缺键那案内部后段没执行；12父绿准确11合法＋1既有拒绝控制。

原漏洞观察assert在修复后按设计失败，旧上限1末断言仍期待2commits、done旧assert异常类期待不同；两案IO已先完整保存，正确断言只读它们，无重跑。复合原探针正确拒后未到内部段不能报通过；本轮用分段完整捕获验证适用反例。原R3预算补充脚本末段装配夹具误删version，前31案完整，后两未运行，合法带version两案已独立执行。历史raw矩阵6个旧期待偏差和正确合同裁定分别保存，原日志未重写。

普通上限1坏链合法首提可已保存event，最终2events／1commit／used1，不能误报零event或两次成功完成；B3六坏案确为前置零event新增。缓存合法与同时删检索ref＋row形态14表同构（仅时间戳排除），这一范围限制真实执行并披露。账中real sent的network_request_count=1仅账接口控制，实际网络0。

## 4. 纪律与中断归属

本轮未发生账号用量中断；用户先前r3续跑及旧目录里的中断记载属于历史，未将其算作本轮事件。全部本审测试各自一次执行，归档、交叉核对和SHA核验零行为重跑。不用实施／主会话输出替代独立执行。

源码／测试／既有文档／AGENTS.md及旧证据保持；没有访问真实金标、题面、封存逐题run、dependingv4，没有调用外部模型／provider，没有commit或push。所有实验数据库在新tmp，永久目录无SQLite二进制；相关账表JSON与被省略文件大小／SHA清单保全。本目录封存后只读。
