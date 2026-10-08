# S3a-r2 Codex 独立复审证据

日期：2026-10-07，Asia/Shanghai。实际 HEAD：`dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`；直接父：`9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`。

结论：**S3a 不通过，S3b 暂不可启动。S3A-01/05 已关闭；S3A-02/03/04 三组残余 P1。** 报告：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R2_2026-10-07.md`。有限回修提示词在报告 §8。

## 已完成的独立执行

| 执行 | 结果 | 入口 |
| --- | --- | --- |
| PPV1 全量 | 648 passed /0 skipped /0 failed | `execution_specialist/ppv1_full/` |
| 父9b78同字节r2新增54项 | 52 failed /2 passed /0 collection error | `execution_specialist/baseline_r2/` |
| 父失败分类 | 48行为断言 +3返回形态TypeError +1旧异常kind先停 | `execution_specialist/baseline_case_classification.json` |
| 安全G01 | 1250 passed /8 skipped /17 deselected，275输入 | `execution_specialist/g01/`、`g01_exclusions_detail.json` |
| 四错误身份B3补证 | 父各event1/commit1；当前各0/0且artifact保全 | `execution_specialist/baseline_extended/`、`current_extended/` |
| 四硬杀及双独立进程barrier | 合法控制完整执行 | `authority_specialist/crash_observations.json` |

当前54通过只是648全量JUnit子计数，未单独重跑，不相加。安全G01的8缺席与17排除逐nodeid披露；与R7/R8/S3a旧数字分别登记。实际环境：depending43 Python3.11.16 /RDKit2026.03.6 /SQLite3.53.4，profile10/search2/store9/limits3。

## 三个专项及输入输出

- `execution_specialist/README.md`、`STATIC_FINDINGS.md`：工程套件、红绿分类、runner双入口/legacy identity/store事务、窄化学15案、mimo读码事实纠错；实际argv/env/cwd/exit/耗时、完整stdout/stderr/JUnit、源码/测试和275安全输入归档。
- `authority_specialist/README.md`、`AUTHORITY_REVIEW.md`：27旧分案、5硬杀/并发控制、120分段案、5补充案（3首提语义守卫+2窗口故障注入）、2 done复用；各案原输入/全部表前后/公共接口返回与异常、原脚本、观察断言。81坏行接受与2晚拒已写event是同组入口分布，不是83个漏洞。
- `budget_request_specialist/README.md`、`SPECIALIST_REVIEW.md`：旧请求/策略/预算退款/停止原输入与日志，有效114矩阵91符合/23不符合，另63优先级组合；oracle准备失误与更正只读判断分开保留。

旧 observed 断言在修复前现象消失后按设计失败；复合脚本早停后的内部控制不报通过。权威补充脚本最终异常类断言准备错误发生在5案已完整捕获之后，正确只读断言附存，没有重跑。便携复现包装器仅语法检查，没有假称第二次独立执行。旧脚本硬编码 HEAD/旧schema是历史输入；当前实际身份另有metadata。

## 中断与证据完整性

`INTERRUPTION_RESUME.json`：原轮ChatGPT账号用量限额中断，三个初次代理没有完成有效执行；用户授权恢复后复用初读与哈希，各套件只独立执行一次。实施方旧tmp结果未换作本审结果，归档不重跑测试。

`input_snapshot.json`、`workspace_integrity.json`：375个明确既存输入的SHA与仓库HEAD/父/tracked diff/status前后核对。原AGENTS.md差异、.zcodeignore、旧评审文档和永久证据保留。仓内只新增本报告与此目录，未commit/push。

`package_assembly.json`、`assemble_evidence.py`：逐文件按原三包清单复制并校验。三个子包原manifest分别264、495、132附件；含各自原SHA控制文件复制后为266、498、135文件。外层清单也包含嵌套manifest和SHA控制文件。权威包明确列出的**162个合成SQLite快照**保留原字节，仅复制/哈希，不在永久目录打开或运行写库；不含真实金标、题面、封存run或评价库。G01 tar为275白名单普通源码/资产输入，无链接/DB/cache。

`assembly_confirmation.json`、`verify_nested_archives.py`：子包分别167/104/80个来源输入哈希及275个tar成员再作只读核对，全部相符。最初tar名称映射遗漏固定g01_inputs/前缀而误报名称不匹配，原检查脚本和元数据另存`verify_nested_archives_initial.py`/`nested_verification_first_attempt.json`；更正后无字节不符，未解压、未重跑、未改子包。

`run_metadata.json`、`report.sha256`、`manifest.json`、`SHA256SUMS`：运行结论、报告哈希与本目录完整附件SHA。manifest排除其自身和外层SHA256SUMS；SHA256SUMS额外校验manifest本身。没有执行源码或打开DB的只读校验命令：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_r2_2026-10-07/verify_evidence.py \
  --evidence /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_r2_2026-10-07
```

复现实验必须先把所需脚本、完整隔离源码/vendor/metadata与合成输入复制到**新的仓外tmp**，按专项说明给全新输出目录，禁字节码与pytest cache。不要在本目录原地运行探针，不修改历史证据/manifest。

## 采信与边界

TOCTOU确定性主动外部SQL破库确证两个事务间无锁窗口；按固定顺序单消费/合法不可变writer模型登记P2，不增第4组P1。保守defer不释放未归因event亦登记接受边界。三组P1均有无竞态公共链证据。

本审不访问真实金标/题面/封存逐题run/dependingv4，不调用外部模型或真实provider，判分零LLM、网络0。mimo v10只读原回应与程序互证；虚构术语、错误版本和异常分支已在报告§6明确纠正。工程合成数字不外推dev（B1环境中间步骤）或298（RHEA通用酶学）科学性能，不宣布判据冻结或S4/S5完成。
