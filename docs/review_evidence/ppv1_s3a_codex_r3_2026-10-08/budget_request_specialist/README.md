# S3a-r3 独立专项：预算 / 请求 / stop

实际 HEAD `41d0cd55f3def050a62325f00235cf22da302d2e`；直接父 `dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`；2026-10-08 (Asia/Shanghai)。执行根 `/private/tmp/ppv1_s3a_r3_budget_1rhko3wp`。

**S3A-03 / S3A-04 各剩一个同合同 P1，S3A-05 保持关闭。** 原 R2 有效114个预算/请求/停止矩阵输入已全部执行并符合合同（recover可按既有最低验收结构化披露坏引用，不要求顶层一定抛异常），修正原63个停止优先级组合也保持。追加的公共请求状态消费反例说明预算冻结校验未接入状态消费；未知请求状态在 mark_request_failed 被当作可改写来源，这是实际成功写表，不能仅按缺专门错误码收口。

本包只执行合成工程输入。网络0、外部模型0，真实provider只登记合成额度账，不发送。未访问金标/题面/封存run/dependingv4，不改任何主仓/旧永久证据，不提交/push；PPV1/G01、完整事件权威由另专项承担。工程数不认证dev/298科学性能。

## 文件与实际执行

- `source/`：完整r3源码，包括vendor、pyproject、必要worker/测试；没有在源内生成bytecode/pytest缓存。
- `old_root/`、`old_search/`、`old_stop_input/`：R2永久证据原字节复制输入。原旧脚本历史HEAD/旧metadata不能作为本轮实际HEAD；实际每run metadata另登记当前HEAD/schema。
- `scripts/contract_probe.py` / `supplement.py`：原R2完整矩阵及补证，未修改原输入/期待。contract exit0，115案例 raw109符合/6不符合；其1个旧错误priority期待排除，5个recover旧期待按原验收允许的reference_integrity只读调整，最终114/114。
- supplement exit0，13 JSONL记录=10策略模式+63子集priority一条+exact旧stop一条+runtime一条。10模式均search_policy_block_corrupt零写拒，原2条frozen_expected期待identity_mismatch是旧R2期待，当前先消费冻结块拒，更强门守不算缺陷。
- `extra_probe.py`：31个完整新控制：18坏冻结策略×状态口实际接受写状态、3合法状态控制、5未知状态入口、5foreign-run入口。最后2个合法partial输入误丢既有必需version，注册拒后读取未注册run使脚本exit1；31案已完整输出并保存，不重跑。未执行末两正控，单独`legal_assembly.py`补合法带version两控制，exit0/2全部符合。
- `old_request` exit0/12JSONL(11行为+metadata)，`old_policy` exit0/5行为。`old_defer` exit1，首个已执行event拒defer，后两循环未执行；`old_root_observed` exit1旧schema断言停，内部未执行；`old_search_observed` exit1，先合法B3输出一案后异身份bundle写侧拒，内部未达不记过；`old_stop_observed` exit1旧exhausted期望不成立，same-input当前primaryNone由独立矩阵/supplement补证。
- `evidence/<run>/`：实际argv/cwd/env/exit/elapsed/stdout/stderr，旧DB只读全表快照。`contract_observations.json`、`extra_observations.json`记录每案全部输入/前后行；所有DB都在隔离tmp，冻结包只收JSON行日志，不收数据库。
- `sent_failed_control.py`：独立合法sent→failed一控制，exit0，预约未退款/网络0。
- `adjudicate.py`只读已经完成日志，不执行生产代码/不重跑；`adjudicated_summary.json`精确更正旧期待并钉住新残余。
- `scripts/reproduce.py`：便携复现入口，仅静态语法检查；把包复制到另一个新tmp后运行各原脚本（保留上述原raw异常），不在永久证据原地建库。
- `manifest.json` / `SHA256SUMS` / `manifest.sha256`：冻结包全附件SHA；manifest不含自身，manifest.sha256另记其hash。

## 裁定

见`SPECIALIST_REVIEW.md`；真实运行版本见`evidence/runtime/stdout.txt`，输入前后保全见input_snapshot/final_integrity。全部Python命令-B/PYTHONDONTWRITEBYTECODE=1。
