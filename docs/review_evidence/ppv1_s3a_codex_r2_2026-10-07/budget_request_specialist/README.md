# S3a-r2 专项独立审核：预算 / 请求 / stop

实际源码 HEAD：`dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`；直接父：`9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`。
日期：2026-10-07；执行目录：`/private/tmp/ppv1_s3a_r2_budget_resumed_0rxegzu0`。

**逐组裁定：S3A-03、S3A-04 未闭合；S3A-05 可保持关闭。** 已执行 event 经 defer 退预算的原反例已翻绿，但已冻结策略坏块的默认补全仍可突破原总额度。请求原登记反例已翻绿，但现存请求坏引用复用、状态消费与恢复未共用完整合法归属门。

本包只执行合成工程案例，不证明 dev（B1 环境路径中间步骤）或 298（RHEA 通用酶学）的科学性能。未访问真实金标、题面、封存 run、dependingv4；未调用模型；网络请求 0。`provider_kind=real` 仅登记账表；所有发送/响应/失败状态调用都使用 scripted/fake。未修改仓库源码、测试、旧 docs、AGENTS、永久证据；未提交或 push。PPV1/G01 与 TOCTOU 专项由其他审核者负责，本包不重复。

## 固定验收与适用入口

依据首轮 `POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_2026-10-07.md` §4 S3A-03/04/05、§7 放行面及 r2 交付入口矩阵。不给 S3b 触发、机制库或科学性能加门。

| 规则 | 适用入口 | 本轮结果 |
| --- | --- | --- |
| 已执行额度不得 defer 退款 | defer、预算复算、后续 claim | 原 capped 公共提交链拒退款，额度保持 1，第二备选 claim 被拒；未执行释放、registered real 占额保留成立 |
| 冻结坏策略不得默认补全 | 注册、`_limits` 的预算/入队/claim/请求登记/恢复读消费 | 原四值在注册与读取均拒；`null`/缺版本在存储读取漏闸，见下面残余 |
| 同键同内容且引用合法 | 请求登记、已有 request 复用 | 原 payload/purpose/action/retry/hash 冲突及坏 caller 引用拒；现存行 run/attempt 损坏仍 unchanged |
| 请求执行权与归属闭合 | sent/response/failed、恢复 | action 状态和非空 attempt 归属/状态部分成立；foreign run、expand 空 attempt、恢复坏 pending 仍漏 |
| 不漏未完成工作 | stop、预算与恢复 B1 | claimed/open 明示，合法停止、零资源、六原因优先级成立 |

细节见 [SPECIALIST_REVIEW.md](SPECIALIST_REVIEW.md)。

## 执行、数字与更正

- 旧请求输入：原脚本未改，完整 11 案 + 1 条历史 metadata，exit 0；旧策略原脚本完整 5 案，exit 0。历史 `input_snapshot.json` 和旧脚本的 HEAD 是首轮历史字段，**不能当成本轮 HEAD**；本包 `run.json` 和外层 input snapshot 记录真实当前源码。
- 旧 observed root 断言：exit 1，在 schema 旧值断言先停，内部全部行为断言未执行。它不是“修复已过”的证据。
- 旧 search observed：exit 1，合法 B3 正控 1 行后，首次异身份 bundle 写侧被当前合同拒；后续完整原脚本内部未达。预算/stop 后续以独立合同矩阵和原 stop 的单块提取补证。
- 旧三 event 退款脚本：exit 1，首次已提交 event 的 defer 被拒，stdout 0 行；原循环后两轮未执行，不能记三轮全过。数据库后态完整保留。
- 旧 stop 原块独立提取：exit 1，原 `exhausted_search` observed 断言翻转；随后精确同输入合同捕获为 primary=None、claimed=1、open=1。
- 自写矩阵：完整输出 115 行案例 + metadata/summary；raw 92 通过 / 23 不通过。经过下列两处审核断言更正，**114 个有效原矩阵案例中 91 符合合同、23 不符合**：S3A-03 为 34/40，S3A-04 为 43/60，S3A-05 为 14/14。这些是入口与正负控数量，不是漏洞数，不和 pytest 相加。
- 补证：13 JSONL 记录 = 10 个策略模式 + 1 个精确旧 stop + 1 个优先级案例（63 子集）+ 1 条 runtime。与前矩阵有意重叠，不相加算独立漏洞。

自写输入/断言错误全部保留：

1. 初始源码复制误以为存在仓根 `vendor/`，exit 1；实际 vendor 在 `src/pathway_v43/vendor`。另建新 scratch，复制完整 src（含 vendor）后才执行。
2. 六原因 expected list 初始把 awaiting_prediction 放在 no_local_candidate 前，造成 2/63 子断言误红。原父源码与当前顺序均是 user_stop → budget_limit → depth_limit → no_local_candidate → awaiting_prediction → exhausted_search。原错误案例排除，补证按原顺序 63/63 绿；不是源码缺陷。
3. missing-version claim 的泛化“有结构化拒绝”不足以证明策略门：原总预算 0 导致 budget_exhausted，坏版本实际未拒。补证按 search_policy_block_corrupt 精确断言，登记为同合同残余；raw 原始结果保持不改。
4. 一次静态 git show 从 scratch 执行报非 git 目录；改显式 repo cwd 后读取父常量，未执行旧源码。证据为 `priority_source_comparison.json`。

## 证据导航

- `evidence/input_snapshot.json`：完整源码、worker、测试和旧脚本输入 SHA-256；实际 HEAD、父、边界。
- `evidence/{old_request,old_policy,old_defer,old_search_observed,old_root_observed,old_stop_observed,contract,supplement}/`：实际 argv/cwd/env/耗时/exit、stdout/stderr SHA、原始输出；`postexecution_db_rows.json` 为只读打开隔离库后的完整表。
- `evidence/contract_observations.json`：每案输入、前后 rows、实际返回/异常及 raw 断言；`adjudicated_summary.json` 明示两处 oracle 更正，不重写原日志。
- `evidence/supplement/stdout.txt`：原完整冻结块、单字段 mutation、各入口、expected policy 是否传入、精确错误 kind。
- `source/`：完整隔离 src（含 vendor）、pyproject、三份必要测试/worker。
- `old_root/`、`old_search/`、`old_stop_input/`：原复制输入；原件 hash 与 extraction说明保留。
- `scripts/`：实际执行的控制器与合同脚本。`reproduce.py` 是便携模板，仅 AST/静态检查，没有重跑上述完整矩阵。
- `manifest.json` + `SHA256SUMS` + `manifest.sha256`：冻结包清单，manifest 不含自身；manifest.sha256 单独记录 manifest 哈希。

Python 命令全部 `-B` + `PYTHONDONTWRITEBYTECODE=1`，源复制排除 pyc/pytest 缓存。未执行 pytest。实际环境 Python 3.11.16，SQLite 3.53.4，RDKit 2026.03.6；恢复策略 schema 为 search-2/profile-10/store-9/search-limits-3。源与 probe 无 bytecode/pytest cache 残留。
