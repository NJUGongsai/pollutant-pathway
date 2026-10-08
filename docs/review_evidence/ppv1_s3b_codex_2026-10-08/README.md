# S3b／完整S3 Codex独立复审永久证据

日期：2026-10-08（Asia/Shanghai）。实际HEAD：`c1211183c0874b12c5b5461845d3c61f0a84719c`；父：`b7f2bba02ca49edd0a45a13bc9b8434909d99175`。

报告：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_2026-10-08.md`。

**结论：S3不通过，P1=S3B-01～06。** S3a已放行及实际化学生产／AuditContractError不吞成功义务保持。未到工程完成交接点，科学性能pending，判据未冻结。

## 1. 目录及独立数字

| 目录／文件 | 内容 |
| --- | --- |
| `execution_specialist/` | PPV1 **851／0／0，30文件**；父两旧文件 **4失败／64通过＝3行为红＋1缺字段**；四新文件4 collection红；安全G01 **1453／8／17、286输入SHA**；完整stdout／stderr／JUnit、命令环境、源／测试副本、safe输入tar、skip／排除逐项、legacy身份差异 |
| `production_specialist/` | 17个合成案一次执行，原raw13／4、只读重判和早停说明；真实AtomTool／donor／converter／audit／admission／提交轨迹、15表／artifact；实际production宽捕获零写与driver窄捕获失败结算分别实证；mimo事实纠错及已接受P2 |
| `queue_recovery_specialist/` | 全部公开workflow.runner探针、四硬杀／新进程恢复／双进程执行barrier、冻plan／H07／B4多产物与转换／novel／depth停止披露反例；完整输入、worker命令、输出、15表、原失效injector和捕获错误；34＋6顶层观察不是40测试通过 |
| `input_snapshot.json` | 1006既存文件SHA、实际HEAD／父、初始tracked diff／工作树及R4永久材料只读清单 |
| `INTERRUPTION_RESUME.json` | 全部行为验证及专项封包后，额度中断与用户授权续跑；仓／输入未变化，续跑零suite／probe重跑 |
| `package_assembly.json`、`assemble_evidence.py` | 三原冻结包按manifest纯拷贝，逐SHA／大小／sidecar；286安全tar成员只读检查，不解压，不复制数据库／缓存／链接 |
| `draft_crosscheck.json`、`run_metadata.json` | 草稿互证更正、各独立执行集合／版本／P1／边界／数字来源 |
| `workspace_integrity.json` | 发布前后1006文件不变、HEAD／父／原用户差异保全、仅两个授权新路径 |
| `manifest.json`、`SHA256SUMS`、`report.sha256` | 所有附件及嵌套控制SHA、外层manifest自身SHA及独立报告SHA |

原嵌套包：873＋190＋624＝**1687 payload**，各3个sidecar，纯复制共1696文件。原包SHA钉在assembly与外层清单，源码含vendor／metadata；合成DB二进制省略，仅其大小／SHA及可读全表保存。完整命令与输入输出均在子包；不使用实施方／主会话日志替代本审执行。

## 2. P1证据定位

| P1 | 关键公开分案／现成结果 |
| --- | --- |
| 01 冻结输入恢复 | `frozen_plan_same`合法；`frozen_plan_omitted`、`frozen_plan_changed`、`frozen_plan_decide_changed`沿旧task消费空／新池 |
| 02 坏artifact绕过 | `public_artifact_hash_bad`、`public_artifact_json_bad`：recover认坏，driver仍真工具重执行、0→1event；合法`crash_after_bundle_written`同output控制 |
| 03 调度完整集合 | `three_products_normal`为3／3；`three_products_after_two_corrected`仅2／3；`transition_normal`phase-1，`transition_after_transition_enqueued_before_attach`已done转换但phase-0，`transition_after_event_submitted`丢转换 |
| 04 公共双恢复执行权 | `public_concurrent_resume`：两个不同PID、同action／attempt／逻辑owner，各自实际tool_entered；最终event幂等不证明单执行 |
| 05 novel生产消费者 | `model_novel_nonempty`只计1新提案却扩原B，`model_novel_empty`空池不进入model；合法弃权不强制停规则池 |
| 06 深度原因／对象遗漏 | `zero_depth_existing_extraction.json`只读旧输出：budget主因正确，但depth_limit其他原因与blocked假设不进stop；scheduled blocked1、stop blocked0 |

具体case JSON在 `queue_recovery_specialist/inputs/`，命令／stdout／stderr／exit在 `logs/`，15表在 `tables/`，实际工具barrier收据在 `runtime_barrier_receipts/`。关键源指针、完整正常／异常控制、最小回修在专项说明和报告§4／§8。H07实际源码错误支段为search.py:3057–3066、3076–3085；专项早期notes指2999–3024仅循环／done，原字节留存，主报告更正。

## 3. 只读哈希验证

下面只读文件，不导入项目、不运行行为、不打开SQLite、不写本目录：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3b_codex_2026-10-08/verify_evidence.py --evidence /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3b_codex_2026-10-08 --report /Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_2026-10-08.md
```

`publish_evidence.py`为只允许两个新路径均不存在的一次发布器，带原输入／git差异守卫；已发布后不能在此运行它。清单不自我循环，嵌套manifest／SHA控制纳入外层SHA；验证回执只写执行时新tmp，封存证据不回写。

## 4. 行为复现纪律与早停

若确需复现，先将**完整对应包复制到新tmp**，含src／vendor／metadata／scripts；按其README用depending43 `-B`。禁止在本目录、旧永久证据或历史tmp实验库原地执行。单案输入记录历史绝对runs_root，复现须生成新的JSON并改到新批次根，不覆盖历史输入。公共单案命令形状：

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<新tmp>/src /Users/cc/miniconda3/envs/depending43/bin/python -B <新tmp>/scripts/probe_public.py worker <新tmp>/inputs/<case>.json
```

部分补充分案用 `probe_supplemental.py worker`；双resume需两个独立进程，按原controller的barrier／日志协议，不能只顺序运行。原首controller最后distinct-worker捕获空stdout exit1，前34观察完整，补controller只补未完成／原失效注入／计划内补充。旧多产品injector未触发不是故障恢复通过。两H07观察false正是实际坏链，不改成通过。生产3项评审期待／字段错误只读纠正，4个原fail不抹去，旧重判常量错误exit1也保留。

当前新64在851之内，父旧64是另一集合；四collection红内部新64未执行。硬杀原交付worker用底层入口，本审公开入口另有独立执行。B2为0event／1commit／1registered请求／network0，非四案皆1event／4commit。raw观察数、测试数、SHA文件数都不是漏洞数或科学性能；数字不外推dev或298。

## 5. 额度中断与原包时序

行为执行和三个专项包完成在前，主报告／最终归档完成在后。汇总期间两个专项出现ChatGPT用量上限，用户明确为额度限制非代码错误，并授权继续。2026-10-07 23:12:22 UTC（2026-10-08 07:12:22本地）恢复盘点：HEAD／父／tracked diff／status与1006输入全未变。续跑只补归档、文档、静态互证和SHA，**无测试／探针重跑**。

各冻结专项的“执行无quota中断”／metadata false字段只描述其已成执行期快照，不能回写改变原哈希；根 `INTERRUPTION_RESUME.json` 记录之后的汇总中断。用户描述约4500行未经独立精确计数，不作为指标。

不访问真实金标／题面／封存run／dependingv4，不调用外部模型／实际provider，无commit／push。仅新增报告与本目录，科学pending、判据未冻结，不自动实施S4／S5。本目录封存后只读。
