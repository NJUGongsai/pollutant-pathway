# T-I B4 新批全链报告（2026-10-21）

> **题域标签：[298 域] = 298 / RHEA 通用酶学 / 已见题（post-hoc）。** 本报告只含
> 工程准备面读数、批准件/锁/哈希、预检账与停点事实；不含题面、金标、结构正文、
> 模型自由文本或真实成绩。298 与 dev 双向不外推。
>
> **状态（2026-10-21 最终）**：B4 按 CC 的「诊断/复测口径」执行——两臂 build、
> 身份门、prepare/P2-face、10 题 test 全 **PASS**；full 298 在运行错误数超过
> 每臂 15 后**主动 `scancel` 停止**（GLM 22、DeepSeek 62），**未 score**。
> 结果一律标「**诊断/复测口径，非 T-I 正式放行**」。
>
> 过程回溯：C5 预检 DeepSeek timeout → 按冻结规则停在 C5 → CC 拍板 A 做计算
> 节点 RCA（RED）→ CC 新指令改为诊断/复测口径、绕过 C5/smoke 严格门。
>
> **2026-10-21 追加（CC 拍板 A）**：先做计算节点网络 RCA，绿了才允许单次重试
> DeepSeek C5。RCA 作业 `47080041` 判定 **RED**（代理 TCP 2/3、TLS 1/3、
> HTTP 2/3），按 CC 规则**未重试**、未写豁免、未启 B5；B4 维持停止。
>
> **2026-10-21 新指令（CC，诊断/复测口径）**：不换网络连接，直接开跑 B4；
> 按 chain13/14 的 build→test→score 路子，绕过 C5/smoke 严格门；失败题留
> 298 分母；结果标注「**诊断/复测口径，非 T-I 正式放行**」。waiver 落在
> `operations/t_i_coordination_t-i-298-20261021b4/b4_c5_retry_waiver.json`
> 与本报告 §13；该窗口结果不构成 T-I 正式放行。
>
> **CC 授权**：CC 2026-10-21 明确授权 B4 新批付费发车（本条为执行者收到的用户
> 指令文本记录；批准包内如实标注，未伪造 CC 签名）。

## 1. 阶段总表

| # | 阶段 | 结果 | 关键读数 |
|---|---|---|---|
| 1 | pre-state 快照 | **PASS** | `2026-10-21T09:26:40Z`；B2/B3/20261020 全量 SHA+mtime |
| 2 | B4 配置 + 重锁 + 批准包 | **PASS** | 14/14 锁过；仅 `ti_arm_config.json` 变；批准 `ca15d72c…` |
| 3 | C2/C4 工程门 | **PASS** | env 600、路径全空、flock 成立、两臂 base/params 同值 |
| 3 | C3 netcheck | **PASS** | `47075962` `COMPLETED 0:0`，`NETCHECK-PASS` |
| 4 | C5 两臂最小真实调用 | **FAIL** | GLM 200（21→37，58 tok）；DeepSeek timeout（127.4s，0 HTTP） |
| 4b | RCA（C5 重试前置，CC 拍板 A） | **FAIL / RED** | `47080041`；代理 TCP 2/3、TLS 1/3、HTTP 2/3；上游 401 正常 |
| 4c | DeepSeek C5 单次重试 | **未执行** | RCA 未绿；未写豁免、未重试 |
| 5 | 两臂 build | **PASS** | GLM `47081227` / DeepSeek `47081230`，均 `COMPLETED 0:0`，约 1h04m |
| 6 | build-gate + 身份门 | **PASS** | 两臂 `BUILD-GATE-OK`；指纹 `28dc2761…` 逐字相同；298 输入 |
| 7 | 两臂 prepare + P2-face | **PASS** | 八项 298/531/242/205/78/151/134/65；两臂同值 |
| 8 | 10 题 test（chain13） | **PASS** | GLM `47083814`、DeepSeek `47083816`；均 10/10、0 failed、calls=11 |
| 9 | full 298（chain13） | **STOP** | GLM `47084122` / DeepSeek `47084123` 已 `scancel`；运行错误 22 / 62，均 >15 |
| 10 | 同 qid 传输失败复核 | **未复现** | `RXNG_56d8…` 两臂均 completed、无 run_error |
| 11 | score | **未执行** | full 中止、pending>0；按 CC 规则停并回报 |
| 12 | 报告/证据 | **完成** | 本文件 + `docs/review_evidence/ti_b4_2026-10-21/` |

## 2. 时间线（UTC）

| 事件 | 时间 |
|---|---|
| pre-state 快照 | `09:26:40Z` |
| B4 配置/重锁/批准包落盘 | `09:30:26Z` |
| 14 件锁复核 PASS | `09:30Z` 后 |
| 批准包只读复验 exit 0 | `09:31Z` |
| C2/C4 完成 | `09:32:04Z` |
| C3 netcheck 提交 / 作业启动 | `~09:32:05Z` / `09:32:07Z` |
| C3 netcheck `COMPLETED 0:0` | `09:32:07Z` 起，Elapsed `00:00:04` |
| C5 GLM 预检完成（seq 7） | `09:33:20Z` |
| C5 DeepSeek 预检超时结束 | `09:35:27Z` |
| post-state 快照 / 审计 | `09:38:21Z` / `09:40Z` |
| 预检账修正（仅记账） | `09:45Z` |
| RCA 作业 `47080041` 提交 / 计算节点启动 | `11:11:4xZ` / `11:11:48Z` |
| RCA 判定 RED / 作业结束 | `11:12:28Z` |
| 追加报告与证据更新 | `11:1xZ` |

## 3. 第 1 步：pre-state 与零触碰证明

在任何 B4 写操作前（`09:26:40Z`）对以下面逐文件计算 `size/mtime_ns/sha256`，
并对映射做 canonical JSON 摘要（含 mtime；任何写入都会改变摘要）：

| 面 | 文件数 | 摘要（pre=post） |
|---|---:|---|
| `batch/t_i_298_20261020_glm` | 620 | `3af61d4c…`（同） |
| `batch/t_i_298_20261020_deepseek` | 648 | `a61c4665…`（同） |
| `runs/t_i_298_20261020_glm` | 20 | `2370d61b…`（同） |
| `runs/t_i_298_20261020_deepseek` | 168 | `773b1ad9…`（同） |
| `operations/t_i_coordination_t-i-298-20261020` | 8 | `78641eda…`（同） |
| `batch/t_i_298_20261021b2_glm` | 671 | `4882696d…`（同） |
| `batch/t_i_298_20261021b2_deepseek` | 649 | `b3ca909c…`（同） |
| `runs/t_i_298_20261021b2_glm` | 2 | `6751872d…`（同） |
| `runs/t_i_298_20261021b2_deepseek` | 187 | `3e73fd9b…`（同） |
| `operations/t_i_coordination_t-i-298-20261021b2` | 8 | `6b523366…`（同） |
| `batch/t_i_298_20261021b3_glm` | 672 | `bdb2055b…`（同） |
| `batch/t_i_298_20261021b3_deepseek` | 649 | `91ed3354…`（同） |
| `runs/t_i_298_20261021b3_glm` | 188 | `f017a6a0…`（同） |
| `runs/t_i_298_20261021b3_deepseek` | 180 | `8ab0a59b…`（同） |
| `operations/t_i_coordination_t-i-298-20261021b3` | 12 | `d62db236…`（同） |

- 三份 `stop.json` SHA+mtime 前后完全相同：20261020 `164b9a6b…`、B2 `fb1d1627…`、
  B3 `bc71cfa7…`。
- 六份两臂 ops state 前后 SHA+mtime 完全相同。
- `$TI_WS` 自 pre-state 起的**越界写入 = 0**；允许面仅 B4 证据目录、批准记录目录
  与 `preflight_calls.json`（后者为预检账，权限 600）。
- B4 批根/runs/协调目录/state **从未创建**（post-state 复核 `still_absent=true`）。

## 4. 第 2 步：B4 配置、重锁、批准包

### 4.1 配置（唯一允许的代码树改动）

`~/EnzymeAgent/v43cTH/scripts/hpc/ti_arm_config.json`：

| 字段 | B3 | B4 |
|---|---|---|
| `batch_tag` | `t-i-298-20261021b3` | `t-i-298-20261021b4` |
| `arms.*.batch_name` | `t_i_298_20261021b3_*` | `t_i_298_20261021b4_*` |
| `arms.*.runs_name` | `t_i_298_20261021b3_*` | `t_i_298_20261021b4_*` |
| `paths.coordination_dir` | `…t-i-298-20261021b3` | `…t-i-298-20261021b4` |
| `immutable_batch_names` | 5 项（含 B2） | 7 项（新增 B3 两臂） |
| config SHA | `84181c56…` | **`032bc890ac16c9277dc797a495918b13d5b289f27f6d24e3a1fcf6c44165137a`** |

**其余 13 件锁定文件逐字不变**（逐件重算 + 与 B3 锁比较，`changed_files` 恰为
`scripts/hpc/ti_arm_config.json` 一项）。

### 4.2 14 件重锁

| 项 | 值 |
|---|---|
| `lock_verify.py` | **14/14 OK，`mismatches=0`，`missing=[]`，`T-I-LOCK-VERIFY PASS`** |
| 新锁 SHA | **`e9abf523c75ff0d6cff7314bb8b11f1b53b57bbcb30e7c73f91097aee177e762`** |
| 新增块 | `relock_b4_rebatch`（新 tag/根/协调目录；B3 两臂加入 immutable；自述「非新批准、非签名」） |
| 旧锁备份 | `T_I_SCRIPT_LOCK_2026-10-20.json.bak.20261021_b4` |

### 4.3 批准包重绑

批准 JSON 在 B3 版基础上新增 `b4_rebatch` 块（schema `ti-b4-rebatch-1`）：

| 字段 | 值 |
|---|---|
| `approved_at_preserved` | `2026-10-20T15:49:53Z`（原值） |
| `approval_basis_preserved` | `原预注册+任务书+本终审增补` |
| `approval_source_kind_preserved` | `codex_delegated_cc_shijie` |
| `approval_source_preserved` | Codex 代 CC/师姐原文（逐字） |
| `no_cap_ack_preserved` | `true` |
| `cc_paid_launch_authorization` | CC 2026-10-21 授权付费 B4 新批（文本记录，非签名） |
| `previous_script_lock_sha256` | `c555eb03…` |
| `new_script_lock_sha256` | `e9abf523…` |
| `old_batches_preserved_immutable` | 20261020 两根 + B2 两根 + B3 两根 |
| `old_batch_zero_write` / `old_stop_json_untouched` | `true` / `true` |

- 三份 prose 快照（预注册/任务书/终审）SHA 逐字不变。
- 批准 JSON SHA：`84babafa…` → **`ca15d72cce91e2c7fea3e9c52830a130435960de150ceb0f96d3f0b43aa722b0`**。
- `approval-package` 只读复验：**exit 0 / stderr 0 字节**。
- 记录目录 `SHA256SUMS` `7e2e910f…`、`SHA256SUMS.external` `9ee391b1…`；5/5 与
  6/6 校验通过。
- 旧批准/锁/SHA256SUMS 均留 `.bak.20261021_b4` 备份。
- **未新增 CC 签名**；`approved_at`/`approval_source`/`approval_source_kind`/
  `no_cap_ack` 逐字保留。

本地镜像（未提交、未 push）：`scripts/hpc/ti_arm_config.json`、
`docs/T_I_SCRIPT_LOCK_2026-10-20.json`、`docs/T_I_APPROVAL_PACKAGE_2026-10-20/`
已同步为 B4 值；`SHA256SUMS` 5/5 OK。

## 5. 第 3 步：C2 / C4 / C3

### 5.1 C2（凭证/路径/磁盘/flock/immutable）

| 项 | 结果 |
|---|---|
| 两份 env 存在、权限 | `llm.env`、`llm_ds.env` 均 `600` |
| key/base 存在性（只布尔） | 两臂均 `has_api_key=true`、`has_base_url=true` |
| B4 新路径（批根/runs/state/lock/协调目录） | **全部不存在** |
| 磁盘 | `/work` 3.5T，free **847.5 GB**（used 77.4%），>100GB 门通过 |
| flock（父持锁子拒/父释放子得） | 两项均 true |
| immutable 语义 | 20261020/B2/B3 六根全部 `REFUSED_IMMUTABLE`；B4 `ALLOWED` |

### 5.2 C4（两臂模型/base/REQUEST_PARAMS）

| 项 | GLM | DeepSeek |
|---|---|---|
| 模型 | `ZHIPU/GLM-5.3-Flash` | `deepseek-v4.1-flash-1017` |
| 模型与冻结期望一致 | true | true |
| base | `https://dashscope.aliyuncs.com` | 同值（SHA 相同） |
| `V43_LLM_REQUEST_PARAMS` | 未设置（None） | 同值（None） |
| 禁用温度/思考键 | 无 | 无 |
| env 变量名（只列名） | BASE_URL/API_KEY/MODEL | 同 |

`c2_pass=true`、`c4_pass=true`。

### 5.3 C3 netcheck（硬门）

| 项 | 值 |
|---|---|
| 提交命令 | `WS=$TI_WS sbatch --parsable scripts/hpc/sbatch_th_netcheck.sh`（唯一直接 sbatch 的脚本） |
| job | **`47075962`**，`th-netcheck`，`COMPLETED 0:0`，Elapsed `00:00:04` |
| 日志 | `NETCHECK-PASS: python/rdkit/layout/disk/flock/dashscope 全过` |
| 日志开头 | `== netcheck @ 2026-10-21T09:32:07Z node=a01r3n15 ==` |
| 关键读数 | Python 3.11.15、rdkit 2026.03.5、`pathway_v43 import ok`、df 790G free、flock 成立、DashScope API 层应答 |

## 6. 第 4 步：C5 两臂最小真实调用（付费）

在登录节点、各臂 env 由子 shell `set -a; . env; set +a` 注入，Python 端只记录
status/usage/耗时；超时 300s（仅预检）；不打印 key/base/prompt。

| seq | 臂 | 模型 | status | input | output | total | 耗时 | 金额 |
|---|---|---|---:|---:|---:|---:|---:|---|
| 7 | GLM | `ZHIPU/GLM-5.3-Flash` | **200** | 21 | 37 | 58 | 18.168s | unknown |
| — | DeepSeek | `deepseek-v4.1-flash-1017` | **timeout** | — | — | — | 127.432s | unknown |

- GLM：`ok=true`、`content_nonempty=true`、`model_matches_expected=true`；
  记录写入 `$TI_WS/operations/preflight_calls.json`（seq 7）。
- DeepSeek：`ok=false`、`status=null`、`error_kind=timeout`、`http_attempts=0`、
  `usage={}`、`content_nonempty=false`；未返回任何 usage。原始回执
  `c5_deepseek.out`；按 B3 同款脚本设计，失败尝试不写成功 `calls` 数组，已另记
  `failed_attempts[0]`（含耗时、0 HTTP 尝试、金额 unknown）。
- **累计账**（含历史）：成功调用 7 次，input 198 / output 571 / total 769 tokens；
  失败尝试 1 次（B4 DeepSeek）；所有金额 `cost_status=no_snapshot`、
  `cost_known_cny=null`，**不估算**。
- 预检账 `totals.calls` 存在与 B3 相同的记账缺陷（按不存在的逐条 `calls` 字段求和
  得 0），本轮已就地修正为 `len(calls)=7`；token 汇总未受影响。修正脚本与输出
  `fix_preflight_ledger.py` / `ledger_fix.out`。

### 6.1 为什么停

| 依据 | 原文/要点 |
|---|---|
| 冻结任务书 §4.2 第 4 条 | 「预检可用较短超时（例如 300s，仅预检、不作为批参数）；**超时即停，不重试**」 |
| 冻结任务书 §4.2 第 6 条 | 「**若某臂预检失败：停全部两臂，不 build/不 run**；保留错误文本（不含 key），报 CC」 |
| B4 任务硬约束 | 「所有付费动作必须留 receipt；费用未知记 unknown；……**异常即停**」 |

因此未重试 DeepSeek 预检（否则为第 3 次付费动作，违反冻结的 no-retry 规则），
未进入 build/prepare/run/score。

### 6.2 同期网络读数（免费，无 key）

| 探针 | 结果 |
|---|---|
| `dashscope.aliyuncs.com:443` TCP 连接 3 次 | `ok 0.176s / 0.068s / 0.062s` |
| 经代理 HTTPS GET `https://dashscope.aliyuncs.com/` | HTTP 404，2.115s（链路通） |
| 代理端点（不打印凭据） | `http://10.15.2.115:3000`（`has_userinfo=true`），两臂同一代理 |
| 计算节点 netcheck | `47075962` `NETCHECK-PASS`（09:32:07Z） |
| 两臂 base URL | 同值（scheme+host 同、SHA 同） |

**读法**：不是 401/403/402/400，不是模型 ID 不符，不是站点全断；是「连接/响应
在 127 秒内未到达 HTTP 层」的传输级超时，代理或模型网关瞬时卡住的可能性大。
但按冻结门，C5 不因「看起来瞬时」而放行。

### 6.3 计算节点 RCA（CC 拍板 A；免费、零模型调用）

作业 `47080041`（`ti-b4-rca`，节点 `a01r4n18`，`wzhcnormal`，
`2026-10-21T11:11:48Z`–`11:12:28Z`）；每层 3 次、每次超时 15s：

| 层 | 探针 | 成功 | 逐次耗时（s） |
|---|---|---:|---|
| L1 TCP | 计算节点 → 代理 `10.15.2.115:3000` | **2/3** | 7.011（timeout）, 0.0, 1.002 |
| L2 TLS | 代理 CONNECT + TLS → `dashscope.aliyuncs.com:443` | **1/3** | 7.014（timeout）, 3.655（TLSv1.3）, 7.008（timeout） |
| L3 HTTP | 代理 → `https://dashscope.aliyuncs.com/` | **2/3** | 7.024（timeout）, 0.568（404）, 0.534（404） |
| L3 API 路径 | 代理 → `/compatible-mode/v1/models`（未认证） | 3/3 | 0.634 / 0.555 / 1.403（均 401） |

- 判定门（CC）：TCP/TLS/HTTP 任一未 3/3 ⇒ 不绿。**L1/L2/L3 均未 3/3 ⇒ RED。**
- 直连对照：计算节点无直连 DNS/出口（`gaierror` 0/3），**无法对照**，记 unknown；
  不计入代理门失败。
- 代理连接数/日志：计算节点无 `ss`、代理侧无权限 ⇒ **unknown**。
- 上游 DashScope：只要连上代理，API 路径 3/3 在 0.55–1.40s 内回 401 ⇒ **上游正常**。
- 失败类别：代理连接建立阶段 ~7.0s 卡住；与 DeepSeek C5「127.4s、0 HTTP 尝试、
  0 usage」同族；GLM 当次只是抽到健康连接。

### 6.4 重试决策（按 CC 规则）

| 项 | 结果 |
|---|---|
| RCA 是否绿 | **否（RED）** |
| `b4_c5_retry_waiver` | **未写**（豁免前置未满足） |
| DeepSeek C5 单次重试 | **未执行** |
| B5 | **未启** |
| build/prepare/run/score | **未执行** |
| 结论文件 | `docs/review_evidence/ti_b4_2026-10-21/rca/RCA_CONCLUSION.md` |

## 7. 未执行阶段与现场状态

| 项 | 状态 |
|---|---|
| B4 批根 `batch/t_i_298_20261021b4_{glm,deepseek}` | **不存在** |
| B4 runs 根 `runs/t_i_298_20261021b4_{glm,deepseek}` | **不存在** |
| B4 协调目录 `operations/t_i_coordination_t-i-298-20261021b4` | **不存在**（无 `stop.json`） |
| B4 ops state / lock | **不存在** |
| run/score/monitor 作业 | **未提交**；`squeue` 空 |
| B4 批根文件数 | 0（未 build） |
| 证据/批准目录写入 | 仅 B4 证据目录、批准记录目录、预检账（白名单内） |

## 8. 费用与调用数

| 项 | 值 |
|---|---|
| B4 成功付费调用 | 1 次（GLM preflight） |
| B4 失败付费尝试 | 1 次（DeepSeek preflight，timeout；是否计费 unknown） |
| B4 token（成功） | input 21 / output 37 / total 58 |
| B4 token（失败） | 无 usage 返回，unknown |
| 金额 | 全部 `no_snapshot` / `unknown`，不估算 |
| 金额帽 | 无（CC 2026-10-20 `no_monetary_cap_user_decision`；`no_cap_ack=true` 保留） |
| 批内调用 | 0（未 build/run/score） |

## 9. unknown / 未核（诚实登记）

| # | 项 | 状态 |
|---|---|---|
| U1 | DeepSeek 预检超时的具体网络路径（代理 vs 模型网关） | 未取到传输层 detail；同期免费探针正常，无法定位到单跳 |
| U2 | 该次超时是否被计费 | unknown；无 usage、无账单快照 |
| U3 | B4 两臂指纹 / build / prepare / P2-face / smoke / full / score | 未执行（C5 硬门阻断），一律 N/A |
| U4 | B3 失败 qid 是否在 B4 复现 | 未进入 run，无法核 |
| U5 | 本地镜像未提交 | `scripts/hpc/ti_arm_config.json`、锁、批准包为未跟踪文件；未 commit、未 push |

## 10. 建议与下一决策点（CC）

1. **RCA 已做且为 RED**（`47080041`）：代理 TCP 2/3、TLS 1/3、HTTP 2/3；连上后
   上游 401 正常。问题在代理/连接建立路径，不在 DashScope 上游、模型或凭证。
2. **按 CC 规则未重试**：未写 `b4_c5_retry_waiver`、未跑 DeepSeek C5、未启 B5；
   冻结的「超时即停、不重试」规则继续有效。
3. **先修代理再做**：运维检查 `10.15.2.115:3000` 的连接上限/新建连接限速、
   空闲超时、健康检查与到 DashScope 的出口质量；修复后用同一 RCA 脚本复测，
   要求 L1/L2/L3 各 3/3。
4. **复测绿后的授权顺序**：CC 先看 RCA 绿证据，再显式授权一次 DeepSeek C5
   重试（第 3 次付费动作）并落 `b4_c5_retry_waiver`；通过后才 build → 身份门 →
   prepare → run → score。执行者不自行重试、不改 300s 预检超时、不绕过 C5。
5. **若代理长期不稳定**：评估稳定出口/直连白名单；不要在未绿时烧付费 full；
   也不要在同一窗口反复试跑（会污染预检账与时间窗）。
6. **若未来 run 阶段同一 qid
   `RXNG_56d8303ebd8a99f21974e52e9174f3a453c7e59071d517fc128b0a9bcd3162ec`
   再次 `real_model_transport_failure`**：按 B4 任务第 10 条立即停、不启 B5，
   写网络 RCA 升级建议并回报。

## 11. 红线自查

- 未 build、未 prepare、未 run、未 score、未发 monitor；未直接 `sbatch
  sbatch_ti_run.sh`。
- 未读 key 值、金标、题面、`reference_graphs`、`run_inputs` 内容；未输出
  SMILES/结构正文/模型自由文本。
- 未改 `src/`、判据、池、检索、排序、评分、探针口径、三份 prose 批准文本；
  未回退 TI-F1 补丁。
- 未写 20261020/B2/B3 批根、runs、协调目录、`stop.json`（快照摘要前后相同）；
  未清任何 stop。
- 未碰 P2 工作树/文书/证据；未封存；未 commit；未 push。

## 12. 证据

目录：`docs/review_evidence/ti_b4_2026-10-21/`（含 `SHA256SUMS`、`RUN_NOTES.md`）。

| 文件 | 内容 |
|---|---|
| `pre_state.json` / `post_state.json` / `post_audit.json` | 全量逐文件 SHA+mtime 快照、零触碰审计 |
| `b4_rebind.json` / `b4_rebind.py` | 配置/重锁/批准包重绑的旧新 SHA 与保留字段 |
| `lock_verify.txt` / `lock_verify.py` | 14 件逐件重算 + 旧锁 diff（PASS） |
| `approval_revalidate.out` / `.err` | 批准包只读复验（exit 0，stderr 空） |
| `c2_c4.json` / `c2_c4_b4.py` | C2/C4 原始读数与可复跑脚本 |
| `c5_glm.out` / `c5_deepseek.out` / `c5_preflight_b4.py` | C5 两臂回执与脚本 |
| `c5_netdiag.txt` | 代理/ TCP / HTTPS 免费探针（无凭据、无 key） |
| `preflight_calls.json` / `ledger_fix.out` / `fix_preflight_ledger.py` | 预检账（含失败尝试）与修正记录 |
| `netcheck_47075962.out` / `netcheck_submit.out` / `sacct_netcheck.txt` | C3 原始日志与作业终态 |
| `squeue.txt` | 停点时队列为空 |
| `ti_arm_config.json.b4` / `T_I_SCRIPT_LOCK_2026-10-20.json.b4` / `preregistration_approval.json.b4` / `SHA256SUMS.b4` / `SHA256SUMS.external.b4` | B4 版批准件与配置/锁的只读副本 |
| `snapshot_b4.py` / `audit_b4.py` | 快照与审计脚本（只读） |
| `rca/` | 计算节点三层 RCA：脚本、`rca_compute.json`、`slurm_rca_47080041.out`、`RCA_CONCLUSION.md`、`SHA256SUMS` |
## 13. 2026-10-21 诊断/复测口径 waiver（CC 新指令）

> **本节是执行偏离记录，不是新批准、不是 T-I 正式放行，未伪造 CC 签字。**

### 13.1 指令与落盘位置

| 项 | 值 |
|---|---|
| CC 指令日期 | 2026-10-21 |
| 指令原文 | 「不换网络连接，直接开跑 B4。按 chain13/14 的 build→test→score 路子，绕过 C5/smoke 严格门；失败题留 298 分母；结果标“诊断/复测口径，非 T-I 正式放行”。」 |
| waiver 文件 | `~/ppv1_hpc/operations/t_i_coordination_t-i-298-20261021b4/b4_c5_retry_waiver.json` |
| 本地副本 | `docs/review_evidence/ti_b4_2026-10-21/b4_c5_retry_waiver.json` |
| schema | `ti-b4-waiver-1` |
| 结果口径 | `diagnostic_retest_not_t_i_formal_release` |

### 13.2 偏离项（相对冻结 T-I 任务书）

| 项 | 冻结 T-I | 本窗口（CC 豁免） |
|---|---|---|
| C5 预检 | 两臂 200 才可 build | **不再阻断**；GLM 200，DeepSeek timeout 记录在案，不重试、不加付费预检 |
| smoke2 | n_completed≥1 + 真实调用可核 + usage/身份/fatal | 改走 chain13：**n_completed≥1**；10 题 test 用 chain13 gate |
| smoke10 | failed=0、未登记零调用=0、pending=0 | 改走 chain13：**n_completed≥2**；失败留 298 分母 |
| full | 运行失败 >15 停；pending>0 停 | **298 全终态、pending=0**；失败允许并留分母；每臂失败 >15 停 |
| run 入口 | `ti_operations.py launch --phase run` + `sbatch_ti_run.sh` | **`chain13_run_wrapper.py`**（同一 `CHAIN13_PROFILE`）；不提交 `sbatch_ti_run.sh` |
| 同 qid transport_error | 连续 2 个不同 qid 未恢复 ⇒ 停 | 本次口径**只记录、不停批**（该题留分母） |
| 结果性质 | 正式 T-I 批 | **诊断/复测口径，非 T-I 正式放行**；不启 B5；不换代理/网络 |

### 13.3 证据基线

| 项 | 值 |
|---|---|
| RCA | `47080041` RED：代理 TCP 2/3、TLS 1/3、HTTP 2/3；上游 401 正常 |
| GLM C5 | 200，21→37→58 tokens，18.168s |
| DeepSeek C5 | `timeout`，127.432s，0 HTTP attempts，0 usage |
| 批准包保留 | `approved_at=2026-10-20T15:49:53Z`、`approval_source`、`approval_source_kind=codex_delegated_cc_shijie`、`no_cap_ack=true` 逐字保留；approval SHA `ca15d72c…` 不变 |
| 脚本锁 | `e9abf523…` 不变（本窗口不改代码树/配置） |

### 13.4 执行计划（本窗口）

1. 两臂 build（`ti_operations.py launch --phase build`，零模型）→ build-gate → D6 身份门 → prepare + P2-face 八项。
2. 每臂 10 题 test（`chain13_run_wrapper.py --limit 10`）→ `chain13_gate.py run-gate --label smoke10`（n_c≥2）；每臂失败 >3/10 ⇒ 停。
3. 两臂 full 298（同 wrapper 不带 `--limit`）→ `run-gate --label full`（298、pending=0）；每臂失败 >15 ⇒ 停。
4. `chain13_score_v2.py` 零模型判分；报 hit@1/strict/partial/unmatched、失败 qid/数、调用/usage。
5. 所有结果标「诊断/复测口径，非 T-I 正式放行」；不启 B5；不换代理/网络。

## 14. 诊断/复测口径执行结果（2026-10-21，[298 域]）

> **口径标签：诊断/复测口径，非 T-I 正式放行。** 失败题留 298 分母；
> 本节数字不得当作 T-I 正式成绩、不得与 dev 互推。

### 14.1 build（零模型）

| 项 | GLM（baseline） | DeepSeek（challenger） |
|---|---|---|
| job | `47081227` | `47081230` |
| 终态 / 墙钟 | `COMPLETED 0:0` / `01:04:19` | `COMPLETED 0:0` / `01:03:32` |
| 日志判据 | `TI-BUILD-PASS` + `BUILD-GATE-OK n=298` | 同 |
| build-gate | exit 0 | exit 0 |

### 14.2 身份门（D6）

| 字段 | 值 |
|---|---|
| 门 | `TI-BUILD-IDENTITY-PASS`（prepare 前后各一次，exit 0 / stderr 0 字节） |
| `build_identity_fingerprint` | **`28dc2761b16b9f0d13639a7c3b1dfb6da9c574c3258d69f4b121636c20148253`** |
| `manifest_sha256` | **`da644d4cfc0c10907bbf001b6797912b7adde7ecadc36f2dedca1a992e0b6e41`** |
| `n_run_inputs` | 298 |
| 两臂 `build_identity.json` SHA | `33d789c784491761d957281f17b82e434c3b619a23292d839af22aa8c15445c5`（同值） |
| 备注 | 与 B3 `f7fc8c83…` 不同属预期（B4 新 tag 进入 `run_id`）；两臂逐字相同 |

### 14.3 prepare + P2-face

| 项 | GLM | DeepSeek |
|---|---|---|
| exit / stderr | 0 / 0 字节 | 0 / 0 字节 |
| `prepared_at` 指纹 | `28dc2761…` | 同值 |
| P2-face 八项 | 全符 | 全符（逐项相同） |
| `p2_face_measure.json` SHA | `ac267feff5d592154ac105925e63bfab716d4053ac7bec5a1d53d08013a2fede` | 同值 |

P2-face 八项：`files=298`、`specs_total=531`、`remap_applied=242`、
`remap_add_atom_ge1=205`、`remap_add_atom_ge2=78`、`questions_remap=151`、
`questions_with_add=134`、`questions_with_multi_add=65`。

### 14.4 10 题 test（chain13 宽容门）

| 项 | GLM | DeepSeek |
|---|---|---|
| job | `47083814` | `47083816` |
| 墙钟 | 912.0s | 361.4s |
| 终态 | 10 completed / 0 failed / 0 pending | 同 |
| `chain13_gate run-gate --label smoke10` | **PASS**（n_c=10≥2） | **PASS** |
| 模型调用 | 11 | 11 |
| usage（input/output/total） | 33,538 / 259,779 / 293,317 | 34,274 / 130,367 / 164,641 |
| usage 缺失调用 | 0 | 0 |
| 运行错误 qid | 无 | 无 |
| 缺失导出 qid | 无 | 无 |
| 模型身份 | 10/10 `ZHIPU/GLM-5.3-Flash`；前两个 `prediction` 块逐字相同 | 10/10 `deepseek-v4.1-flash-1017`；同 |
| orchestration 冻结 | workers=8、RPM 200/TPM 3M/max_calls 4470、`evidence_card_enabled=false`、max_real=3 | 同 |

**判定**：两臂 0/10 失败 ≤ 3/10 阈值 ⇒ 允许进入 full。

### 14.5 full 298（主动停止，未 score）

| 项 | GLM | DeepSeek |
|---|---|---|
| job | `47084122` | `47084123` |
| 启动 / 停止 | `12:58Z` / `13:19:58Z` | 同 |
| 终态 | `CANCELLED`（主动 `scancel`），Elapsed `00:19:59` | `CANCELLED`，Elapsed `00:19:55` |
| 已落终态题 | 55 / 298 | 165 / 298 |
| 未跑题（pending） | 243 | 133 |
| `status=failed` | 0 | 0 |
| **completed + `run_error`** | **22**（40.0% of 55） | **62**（37.6% of 165） |
| 运行错误类型 | `real_model_transport_failure`，均 `model_calls=1`、无 usage | 同 |
| 模型调用（含 10 题 test） | 56 | 171 |
| 其中 test 段 | 11 | 11 |
| 其中 full 段 | 45 | 160 |
| usage 合计（含 test） | input 103,109 / output 707,216 / total 810,325 | input 313,339 / output 886,821 / total 1,200,160 |
| 失败调用无 usage | 22 | 67 |
| 目标 qid `RXNG_56d8…` | **completed、无 run_error、1 call** | **同** |

**停止依据**：CC 规则「每臂失败 >15 ⇒ 停并回报」。两臂 completed+run_error
分别为 **22** 与 **62**，均已超过 15，故在 55/165 题处主动停止两臂，未等待
298 终态、未 score。`chain13_gate run-gate --label full` 未执行（pending>0）。

**读法**：失败不是题目级可复现问题——B3 的失败 qid `RXNG_56d8…` 在 B4 两臂
均干净完成；失败分散在大量不同 qid，且均为「1 次调用、无 usage」的传输失败，
与 RCA RED（代理连接建立间歇卡住）一致。full 段的 40%/38% 运行错误率说明
当前代理路径不足以支撑正式 full；继续跑只会烧钱并产出大面积缺预测的批。

> **本节结果一律标「诊断/复测口径，非 T-I 正式放行」；未 score，不写 hit/strict。**

## 15. 最终结论与费用（诊断/复测口径）

### 15.1 结论

| 项 | 结果 |
|---|---|
| build / build-gate / D6 身份 | **PASS**（两臂指纹 `28dc2761…` 逐字相同） |
| prepare / P2-face 八项 | **PASS**（298/531/242/205/78/151/134/65，两臂同值） |
| 10 题 test | **PASS**（两臂 10/10、0 failed、calls=11） |
| full 298 | **主动 STOP**：GLM 22 / DeepSeek 62 个 completed+run_error，均 >15 |
| score | **未执行**（full pending>0；按 CC 规则停并回报） |
| B3 失败 qid `RXNG_56d8…` | **未复现**：两臂 completed、无 run_error、1 call |
| 结果性质 | **诊断/复测口径，非 T-I 正式放行**；不启 B5；不换代理/网络 |

**一句话**：工程链（build→身份→prepare→test）是绿的；但当前代理路径在 full
段造成 37–40% 的传输失败，按 CC 的 >15 止损线主动停了，没花完 298 题的钱，
也没有把残缺批拿去判分。

### 15.2 费用 / 调用数

| 段 | GLM | DeepSeek |
|---|---|---|
| C5 预检 | 1 次成功：21/37/58 tok，18.168s | 1 次超时尝试：0 usage，127.432s |
| 10 题 test | 11 calls；33,538 / 259,779 / 293,317 tok | 11 calls；34,274 / 130,367 / 164,641 tok |
| full 段（增量） | 45 calls；69,571 / 447,437 / 517,008 tok | 160 calls；279,065 / 756,454 / 1,035,519 tok |
| run 合计（test+full） | 56 calls；103,109 / 707,216 / 810,325 tok | 171 calls；313,339 / 886,821 / 1,200,160 tok |
| 无 usage 的失败调用 | 22 | 67 |
| 金额 | `no_snapshot` / unknown，不估算 | 同 |

> token 合计只含**有 usage 的成功调用**；失败调用（transport）无 usage，故实际
> 计费输入可能高于表中值，金额一律 unknown。金额帽：无（`no_cap_ack=true`）。

### 15.3 建议（下一决策点）

1. **先修代理再谈正式 full**：运维检查 `10.15.2.115:3000` 的连接上限/新建连接
   限速、空闲超时、健康检查与到 DashScope 的出口质量；修复后用同一 RCA 脚本
   复测到 L1/L2/L3 各 3/3。
2. **不要 resume 本 B4 full 当正式成绩**：已落终态的 22/62 个 run_error 题是
   `status=completed`，resume 会跳过它们，无法修正；且 pending 仍 >0。
3. **正式重跑建议新窗口（B5 或新 tag）**：build/身份/prepare 可复用同一代码与
   题卷，但新批根重跑全部 298，避免残缺批/失败题被静默跳过；是否开新窗口由
   CC 拍板。
4. **不 score 本残缺批**：pending 243/133，失败题缺预测，hit/strict 会被系统性
   压低，不能当模型比较。
5. **任何正式放行仍需 T-I 原冻结门**；本报告只提供诊断/复测读数，不构成放行。

### 15.4 本窗口新增证据

| 文件 | 内容 |
|---|---|
| `b4_c5_retry_waiver.json` | CC 新指令 waiver（协调目录同源） |
| `b4_chain13_run.py` / `run_chain13_b4.sbatch` | 诊断 run 入口（chain13 profile，evidence card off） |
| `build_submit_*.out` / `build_gate_*.out` / `verify_identity_*.out` | build/身份门原始回执 |
| `prepare_*.stdout.log` / `.stderr.log` | prepare 输出逐字 / stderr 空 |
| `p2_face_aggregates.json` | P2-face 八项期望 vs 两臂 |
| `test_*.out` / `gate_smoke10_*.out` / `test10_summary_*.json` / `sacct_test10.txt` | 10 题 test 与宽容门 |
| `full_*.out` / `full_partial_summary_*.json` / `sacct_full.txt` | full 段中止现场与逐题聚合 |
| `target_qid_check.txt` | B3 失败 qid 在 B4 的复核（未复现） |
| `run_identity_check.txt` | 两臂模型身份与 prediction 块一致性 |
| `netcheck_47083806.out` / `netcheck_b4run_submit.out` | 发车前 C3 复测（PASS） |
| `full_watch.log` | full 巡检记录（10 分钟粒度） |
| `summarize_b4.py` | 只读聚合脚本（不读题面/金标/模型文本） |
