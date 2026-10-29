# C 线共底物伴生供给实施·本地预审报告（替 Codex 先审，2026-10-14）

> provenance：本地预审（主会话派 3 个子代理并行），**不替代正链 Codex 最终裁定权**；正审仍走通道 B fork。
> 题域标签：**298=RHEA 通用酶学/已见题，与 dev 双向不外推**。本文数字为实施验收/探针口径，**非判分成绩、非预注册投影**。
> 零金标零题面外带：输出仅聚合计数+qid 代称+文件行号+可复现命令。

## 审谁与基线

- 被审：`873c323`（C 线实施，10 文件 +1423/−22，以 `git show --stat 873c323` 为准；交付书 §五笔误 +1422 以 git 为准）。
- 父：`873c323^=7e7855c`；线性栈 `0ba764f`(doc-only，2117/0/16)→`7e7855c`(+4，2121/0/16)→本任务 `873c323`(+10，2131)→`dda852b`(P1fix2，+4)→HEAD **2135/0/16**。
- 实际 HEAD：`dda852b`；`git diff 873c323..dda852b --name-only` 仅 P1fix2 四文件，与本任务零重叠。
- 输入：冻结设计书 `docs/C_COSUB_SUPPLY_DESIGN_PREREG_2026-10-14.md`、任务书 `docs/TASK_C_COSUB_IMPL_2026-10-14.md`、交付书 `docs/C_COSUB_SUPPLY_IMPL_DELIVERY_2026-10-14.md`、证据 `reports/ppv1_s5b/c_impl_2026-10-14/`。
- 方法：只读+隔离 tmp 执行（`PYTHONDONTWRITEBYTECODE=1`，pytest `-p no:cacheprovider`），未改 src/tests/docs，未写 `reports/` 原目录，未 push，未调外部模型。python：`~/miniconda3/envs/depending43/bin/python`，cwd：`dependingv43` 根。

## 总判定：有条件通过（无 P1，条件见下，均无需改码，确认即放行）

- P1：0；P2：1（文档笔误）；P3：6（见下）。三路分判定：builder 有条件通过／production 通过／tests 通过。
- 放行条件（逐条确认）：①交付书 +1422 笔误以 git +1423 为准；②P3-1/P3-2 按“实现侧更严、逐份真相在 refs/participants/执行输入”理解；③P3-3/P3-4 仅手造 spec 可达、现行判分零分值影响。

## P2/P3 清单

| # | 级 | 事 | 结论 |
|---|---|---|---|
| P2-1 | 文档 | 交付书 §五 +1422 vs git +1423 | 笔误，以 git 为准；验收数字本身无误 |
| P3-1 | builder `s5b_builder.py:602-606` | 主不可解析分支与探针分类器口径不同 | 锚面 0 实例，实现侧 fail-closed 更安全，零面差 |
| P3-2 | builder `s5b_builder.py:810-814` | contract.co_substrates 摘要去重 | 逐份真相在 state_refs/participants/execution_input，去重仅摘要层 |
| P3-3 | production `production.py:804-829,652-653` | NC-10 反应物侧集合语义，同身份份数删减不拒 | 现行判分集合比较零分值影响，仅手造 spec 可达 |
| P3-4 | production `production.py:549-561,206-207,1150-1152` | 声明在位但 execution_input 缺失回落裸底物 | corpus 旁观既有语义，analog 正常链恒携带，仅 stripped-key 手造可达 |
| P3-5 | tests | PC-S5 纯版本字符串断言 | 语义由另 5 文件同步+字节探针承载，可接受 |
| P3-6 | evidence | W4 补位 1 题一致性确认；全量 2135 未重跑 | 方向对（供给抬高独特数→不降阈值）；全量算术已验，6 分钟级未跑如实标注 |

## 分域结论

1. builder（`s5b_builder.py` +547/−13）：主判定 `592-601` 与归因探针同参数（r2/b2048/立体盲，并列取后位）；供给精确多重集 `607-616`；裸通配 `620-623` 仅 `*` 拦；spectator `628-709` 按供给序逐条；记录方程 `712-728` 原样两侧；声明面 `731-862` 七件全；救援仅门拒分支 `1073-1163`；版本 `457` 7，常量 `458-462`（24/8/0.45/0.40/3）零动，排序截断融合无触碰，`s5b_compiler.py` diff 空；35 wildcard 维持拦截、139 电荷门无松动（2 行拒因前移已披露）。
2. production（`production.py` +185/−1）：fail-closed `247-324` 五种 kind 全覆盖；执行输入核验 `194-244` 四种 kind，多重集两侧 strict 身份比对；prepare `540-542` 传 provenance_refs，expand `1234-1238` 事件提交前 put（deferred/rejected/method_failed 零发射），幂等（同 payload 单行，异 payload 冲突）；无声明零调用（NC-S3 过）；NC-10 record_products=执行净产物（`s5b_builder.py:815-816`）与 record_equation 分开消费；判分侧 `evaluation/s5b_scoring/recorded_source` diff 空。
3. tests/evidence：新族 10 件正负控齐备（PC-S2 含 spectator，PC-S3 并入 S2 命名小瑕疵非缺失），非字符串自证（NC-S1 对 kind，S6/S7 真 e2e）；版本承载 5 文件最小字面量变更，lineage 负控子集式放行；T11 三字面量与 `recorded_source.py:401-404` 同词表；三 json 数复核 45/35（446+8=454）、5 exact/5×v1_exempt/5×resolved、262/35/1 drift 0 全对。

## 执行证据（隔离，已执行 vs 仅读诚实区分）

- 行号=HEAD 当前文件行号；`s5b_builder.py/production.py/新测试族/词表/lineage` 在 `873c323..dda852b` 间 diff 空（子代理已验），故等同 873 本体行号。主会话已抽验 `s5b_builder.py:602-623/808-818`、`production.py:247`、`S5B_POOL_* :457-463`、`s5b_compiler.py` diff 空、三 json totals，全对。
- 可复现命令（cwd=`/Volumes/CC/Enzyme_Agent/dependingv43`，python=`~/miniconda3/envs/depending43/bin/python`）：
  - `PYTHONDONTWRITEBYTECODE=1 <python> -m pytest tests/test_ppv1_s5b_cosub_supply.py -p no:cacheprovider -q` → 10 passed；
  - `PYTHONDONTWRITEBYTECODE=1 <python> -m pytest tests/test_ppv1_s5b_pool_lineage.py -p no:cacheprovider -q` → 8 passed；
  - `PYTHONDONTWRITEBYTECODE=1 <python> reports/ppv1_s5b/c_impl_2026-10-14/byte_invariance_probe.py`（输出改落隔离 tmp，跑后 `git status -- reports/` 为空）→ 262/35/1 drift 0；
  - `git show --stat 873c323 | tail -3` → +1423；`git diff 7e7855c..873c323 --name-only | grep -E "evaluation|s5b_scoring"` → 空；`git diff 873c323..dda852b --name-only` → 仅 P1fix2 四文件。
- 合成探针（子代理自造、仅补行为覆盖，不作主证据）：builder 4 锚行+5 合成单元、production 删减/缺键/幂等边界探针均过；散列截断不列，主证据以上述仓内命令+落盘 json 为准。追溯：builder `ses_ec6491bfcffefwpCM0EXLf1jb9`／production `ses_ec6491bfaffe78351E0mv8KfrW`／tests `ses_ec6491bd3ffeJnpPvWQyg77q0y`，隔离 tmp 在各子代理自有目录（主会话未独立重跑，如实标注转述边界）。
- 仅读：unlock/v2 两 json 落盘数已验盘（`face 45/35`、`row_reconciliation matched 446/drifted 0`、`totals exact_v1=0/exact_v2=5/exempted=5`，抽查 RXNG_3b8991e exact_v2=1），等价语义由 PC-S6/S7 已执行覆盖；全量 not-slow 2135 未跑（算术 2117+4+10+4=2135 已验）。

## 下一步

请求 md 已就绪（`docs/REVIEW_REQUEST_C_IMPL_CODEX_2026-10-14.md`），本报告可当附件发通道 B 正审；正审报告落盘命名建议 `C_COSUB_SUPPLY_IMPL_CODEX_REVIEW_2026-10-14.md`（未跟踪）。
