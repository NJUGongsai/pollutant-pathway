# 任务书 — T-I 模型配对两臂发车物（298 post-hoc，2026-10-20，草案）

> **题域标签：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本批全部数字只在该题域内成立，
> 与 dev 双向不外推。
>
> **文档状态：DRAFT_NOT_EXECUTABLE。** 本文件是发车任务书草案，不是发车指令。
> 执行前必须同时满足：①CC 已签 `docs/T_I_PREREG_2026-10-20.md` 的预注册并回填 SHA；
> ②CC 已落字付费/HPC 指令；③本任务书所需操作脚本改动已复核并锁定；
> ④§0 发车前清单全绿。缺一不发。
>
> **性质：模型配对探针，不是新科学成绩。** 两臂同题集同配置；唯一变量=模型。
> 上游：老师任务书 #9、主 TODO 行 9、T-H r2 结果、T-H 重启移交 §5/§7、
> `docs/T_I_PREREG_2026-10-20.md`（口径与判定线以该预注册为准）。

## 0. 一句话与发车前清单

一次批跑两臂：A=GLM-5.3-Flash（基线）、B=deepseek-v4.1-flash-1017（挑战臂）；
同 298 题卷、同代码、同编译池、同 profile/gate/超时/重试，只换模型。判分 v2 headline
+ v1 敏感性；预算模式=两臂 no-cap（CC 2026-10-20「全部都不设置buget」），无金额停点，
用量照记、金额事后回填。

> **CC 2026-10-20 晚决定：只保留 GLM/DeepSeek 两臂，T-I 按两臂 A/B 执行。** 原多臂方案作废；任务书、
> 预注册与 `ti_arm_config.json` 均以两臂为准。
>
> **D1 已拍板（CC 2026-10-20）：A 同批重跑**，两臂同一时间窗、同条件。T-H r2 的
> v2 headline 89/298（v1 84/298）**仅作历史参照，不参与本批复用**；不得用跨批差值
> 替代同批配对，也不得把历史数字写成本批 A 的读数。

发车前清单（全绿才可发）：

| # | 检查 | 判定 |
|---|---|---|
| 1 | 完整批准包 | `approval_status=preregistration_confirmed`；预注册/任务书/终审/脚本锁四份快照逐件 SHA 相符；Codex 代 CC/师姐来源 + 授权链；`no_cap_ack=true` |
| 2 | 付费/HPC 指令 | CC 落字；站点/分区/预算模式（no-cap）明确；Codex 终审代决已落报告 |
| 3 | 两模型凭证 | GLM `llm.env`、DeepSeek `llm_ds.env` 两份 env 在位；DeepSeek 模型 ID 已定名 |
| 4 | 模型 ID | A `ZHIPU/GLM-5.3-Flash`、B `deepseek-v4.1-flash-1017`，预检实核 |
| 5 | 客户端兼容 | temperature 不发；`reasoning_effort` 同值且被接受；两臂均不发 `max_tokens`（no-cap） |
| 6 | 题卷 | 298 行；SHA256 `9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c` 实核 |
| 7 | 代码 | 两臂同 commit `c9c6c7a`；科学代码聚合身份登记；脚本锁 SHA 清单在位 |
| 8 | 操作脚本 | `ti_operations.py`/`ti_run_wrapper.py`/`sbatch_ti_*` 已参数化并合成验收；sealed 名支持 |
| 9 | 预算 | 两臂 no-cap 已拍板；每臂 `budget_no_cap.json` 字段齐全（budget_mode+marker+日期）；无金额停点；usage 记录点明确 |
| 10 | 站点 | netcheck 全过（python/rdkit/layout/disk/flock/出口） |
| 11 | 旧批 | T-H/chain13 批根只读；T-I 两个新根均不存在或为空 |
| 12 | 监控 | 单协调者 flock；`monitor` 每 15 分钟巡检；两臂 smoke10 barrier；停点/`halt --cancel` 路径明确 |

## 1. 批根、运行根与记录

| 项 | 值 |
|---|---|
| 站点 | 乌镇 wuzh02，分区 `wzhcnormal` |
| SSH | `ssh -i "$KEY" -p 65091 aclhl3hbth@wuzh02.hpccube.com`；`KEY` 在 `/Volumes/CC/Enzyme_Agent/`，权限 600 |
| 代码树 | `~/EnzymeAgent/v43cTH`（科学源码与 T-H r2 同树） |
| Python | `~/ppv1_hpc/venv_v44run/bin/python`（rdkit 2026.03.5） |
| 题卷 | `~/ppv1_hpc/questions.jsonl`（298 行，SHA 全值见 §0） |
| env 目录 | `~/ppv1_hpc/env/`；两份 env 文件名见 §4，**不打印内容** |
| 两臂批根 | `~/ppv1_hpc/batch/t_i_298_20261020_{glm,deepseek}` |
| 两臂运行根 | `~/ppv1_hpc/runs/t_i_298_20261020_{glm,deepseek}` |
| 操作状态 | `~/ppv1_hpc/operations/t_i_298_20261020_{glm,deepseek}.json` |
| 批准记录 | `~/ppv1_hpc/operations/t_i_approved_record_20261020/`（CC 批准件 `preregistration_approval.json` + `budget_no_cap.json` + 两份文本快照；P2 探针由 prepare 调用） |
| 本地镜像 | `reports/ppv1_s5b/t_i_2026-10-20/{glm,deepseek}/`（gitignored；只拉指标/身份件） |
| 封存标记 | 批根 `ti_sealed.json`（`ti_operations.mutable()` 已识别；chmod 555/444） |

命名说明：两臂批名固定为 `t_i_298_20261020_glm` 与 `t_i_298_20261020_deepseek`；
发车前一次写死，不中途改。

## 2. 冻结面（两臂同值；详细口径见预注册 §2）

| 项 | 值 |
|---|---|
| 模型 | A `ZHIPU/GLM-5.3-Flash`；B `deepseek-v4.1-flash-1017`（CC 2026-10-20 晚定名） |
| 唯一差异 | 模型 ID + 对应 env 文件 |
| 题卷 | 298 行，SHA 全值见 §0 |
| 代码 commit | **`c9c6c7a`（D7 主窗口技术默认，CC 可改）**；科学源码与 T-H r2 `c360e74` 零差异 |
| 科学代码聚合 | `a24700abf992fb7e9a32822268a4e407b8497ef5d1d216fc11bcfa6762ff6b85`（T-H r2 build identity） |
| 编译/池/来源/归一/路由/检索/排序 | `s5b-compiler-6` / `s5b-pool-policy-9` / `s5b-recorded-source-4` / `record-side-formnorm-1` / `s5b-analog-route-f1f4-1` / `s5b-corpus-retrieval-6` / `s5b-rank-policy-2` |
| 判分 | v2 headline + v1 敏感性 + v3 披露；零 LLM |
| profile_policy | `max_real_model_requests=3`；`max_format_feedback_rounds=2`；其余沿 `CHAIN13_PROFILE` |
| gate | RPM 200 / TPM 3,000,000 / max_calls 4,470；每臂独立 |
| workers | 8 / max_in_flight 8 |
| 证据卡 | 关 |
| 超时/重试 | 3600s/调用，timeout 不重试；传输失败自动重试 1 次；429 有界退避 |
| 温度 | 不发（policy `temperature=None`） |
| 最大 token | no-cap 模式不发 `max_tokens`（两臂一致，与 T-H 同） |
| 金额帽 | 无（`no_monetary_cap_user_decision`，2026-10-20）；gate/速率/并发守卫照旧 |
| 数据面/分母 | `real`；298 固定；失败/零调用不剔题 |

## 3. build 策略（D6 主窗口技术默认：两臂独立 build + 指纹一致硬门）

> **D6 状态：主窗口技术默认，CC 可改。** 默认按两臂各自独立 build（两个新批根），
> 两臂使用**同一 `batch_tag=t-i-298-20261020`**。原因：`run_id` 含 `batch_tag` 并进入
> `build_identity_fingerprint`；若逐臂用不同 tag，“两份指纹逐字相同”的硬门不可达。
> 若 CC 改为逐臂不同 tag，必须同步改身份比较口径：只比代码/版本/资产事实与 pool
> canonical 内容，不得比 raw `run_input_sha256`。

### 3.1 两臂 build

在 HPC 登录节点执行（重活由 sbatch 到计算节点；build 零模型零网络）：

```bash
TI_WS="$HOME/ppv1_hpc"
TI_CODE="$HOME/EnzymeAgent/v43cTH"
TI_PY="$TI_WS/venv_v44run/bin/python"
cd "$TI_CODE"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1

for arm in glm deepseek; do
  "$TI_PY" -B scripts/hpc/ti_operations.py launch --phase build \
    --arm "$arm" --ws "$TI_WS" --code "$TI_CODE" \
    || { echo "STOP: build submit $arm"; exit 1; }
done
```

- `launch` 按臂解析 `BATCH_ROOT`/`BATCH_TAG`/`QUESTIONS`/`V3_CODE_ROOT`，job 名为
  `ti-{arm}-build`，提交前写 `pending_submission` 意图；无可靠 job id 时禁止盲重投。
- 每臂完成判据：作业 `COMPLETED 0:0` 且日志含 `TI-BUILD-PASS`；再跑 build-gate：
  ```bash
  for arm in glm deepseek; do
    root="$TI_WS/batch/t_i_298_20261020_$arm"
    "$TI_PY" -B scripts/hpc/chain13_gate.py build-gate --batch-root "$root" \
      || { echo "STOP: build-gate $arm"; exit 1; }
  done
  ```

### 3.2 D6 身份门（两臂逐项同值）

```bash
"$TI_PY" -B scripts/hpc/ti_operations.py verify-identity --ws "$TI_WS"
```

判据（任一不过即停，不得只改一臂旁件）：

1. `batch_tag` 两臂相同；
2. `batch_manifest.json` 字节级 SHA 相同；
3. `build_identity_fingerprint` 相同且为 64 位小写 hex；
4. `build_identity.run_inputs` 的逐题 `(qid, run_input_sha256)` 完全相同，共 298 条；
5. manifest 的 `build_identity_ref` 指纹与 `build_identity.json` 一致。

期望身份事实（与 T-H r2 同代码/同资产）：`code_identity_aggregate_sha256=a24700ab...`、
`compiler_version=s5b-compiler-6`、`pool_policy_version=s5b-pool-policy-9`、
`recorded_source_version=s5b-recorded-source-4`、`corpus_retrieval_version=s5b-corpus-retrieval-6`、
`formnorm_version=record-side-formnorm-1`、`route_version=s5b-analog-route-f1f4-1`、
`rdkit_version=2026.03.5`、`n_run_inputs=298`。`build_identity_fingerprint` 以本批实测为准，
不要求等于 T-H r2；但两臂必须逐字相同。

> 若身份门不过：停，查代码/资产/题卷/环境差异；不得进入 prepare/run，不得用“改一臂旁件”
> 或“重算新 ID”洗掉差异。CC 若改 D6 为 seed build + 拷贝，需按拷贝方案重写本节命令，
> 并保持同一身份判据。

## 4. 环境变量、凭证与模型切换

### 4.1 只写变量名与文件路径，不写值

| 臂 | env 文件 | 模型 ID |
|---|---|---|
| A GLM | `~/ppv1_hpc/env/llm.env` | `ZHIPU/GLM-5.3-Flash` |
| B DeepSeek | `~/ppv1_hpc/env/llm_ds.env` | `deepseek-v4.1-flash-1017`（CC 2026-10-20 晚定名） |

> DeepSeek：主窗口/运维已在 HPC 备份 `llm_ds.env`（如 `.bak.20261020`），只把
> `V43_LLM_MODEL=` 一行改为 `deepseek-v4.1-flash-1017`；base 仍为 dashscope。
> 本代理未连 HPC，未读取 key 内容；发车前只核模型名与 base host。

- 客户端只读取 `V43_LLM_BASE_URL`、`V43_LLM_API_KEY`、`V43_LLM_MODEL`，可选
  `V43_LLM_TIMEOUT_S`、`V43_LLM_REQUEST_PARAMS`、`V43_LLM_MAX_HTTP_RETRIES`、`V43_LLM_RATE_GATE`。
- 任何日志、任务书、报告不得出现 key；env 文件权限 600；只打印「文件存在/模型名/键是否存在」布尔。
- 两份 env 的 `V43_LLM_REQUEST_PARAMS` 必须逐字同值；发车前只读核对，不打印值。
  若 DeepSeek 不接受其中某参数（例如 `reasoning_effort`），**停批**，交 CC 决定统一
  去掉还是分臂登记；不得静默删掉后继续。

### 4.2 预检（付费调用前，两臂各一次最小调用）

1. 文件与权限：
   ```bash
   for f in "$TI_WS/env/llm.env" "$TI_WS/env/llm_ds.env"; do
     test -f "$f" && test "$(stat -c '%a' "$f")" = "600" \
       || { echo "STOP: env missing/perm $f"; exit 1; }
   done
   ```
2. 只读模型名（不打印 key）：
   ```bash
   for f in "$TI_WS/env/llm.env" "$TI_WS/env/llm_ds.env"; do
     grep -E '^V43_LLM_MODEL=' "$f" | sed 's/^/MODEL /'
   done
   ```
3. `s5b_cli envcheck --env-file <env>`：只作参考；T-H 现场有 `configured=false` 的老自检假阴性，
   **不得单独以它判死**。
4. 最小真实调用（每臂 1 次；计入 usage 账，no-cap 下无金额帽）：先在该预检进程内加载 env
   （`set -a; . "$ENV_FILE"; set +a`；不 `cat`、不打印），再用 `OpenAICompatibleClient`
   发一个固定短提示，核对：HTTP 200、非空 content、usage 可解析、模型 ID 与预期一致、
   无 400/401/403/402。记录 input/output tokens 与耗时；不写 prompt 到报告，不读金标。
   该调用**不走批内 gate**（no-cap 下亦无金额守卫），必须单独写入
   `$TI_WS/operations/preflight_calls.json`（臂、模型、tokens、时间、金额或 unknown），
   并计入两臂 usage 账；不得只算批内 usage。金额无快照时记 unknown，不估算、不编单价。
   预检可用较短超时（例如 300s，仅预检、不作为批参数）；超时即停，不重试。

   预检脚本骨架（只打印 ok/status/model/usage，不打印 key；`ENV_FILE` 已 export）：

   ```bash
   set -a; . "$ENV_FILE"; set +a
   "$TI_PY" - <<'PY'
   import json
   from pathway_v43.adapters.llm_client import OpenAICompatibleClient
   c = OpenAICompatibleClient.from_env()
   c.timeout_s = 300.0  # 仅预检短超时；批内仍 3600s
   r = c.complete(mode="preflight",
                  system_prompt="Reply with the single token OK.",
                  user_payload="OK")
   print(json.dumps({"ok": r.ok, "status": r.status, "model": c.model,
                     "usage": r.usage, "elapsed_s": r.elapsed_s,
                     "error_kind": r.error_kind}, ensure_ascii=False))
   PY
   ```

   若 `ok=false` 或 `status` 非 200，停；把 `error_kind`/`error_detail` 脱敏后报 CC。
5. 若任一臂返回 temperature 400：政策本就不发 temperature，说明 env/请求参数另有温度键；
   停，查配置，不临时加/删参数。
6. 若某臂预检失败：停全部两臂，不 build/不 run；保留错误文本（不含 key），报 CC。

### 4.3 模型配置冻结与身份核验

- `orchestration.json` 不冻结模型 ID；模型 ID 在每次 run 的 `run_identity.prediction` 块。
  不建议为 T-I 改 `orchestration.json` 的冻结 schema（会引入 orchestrator 版本/身份语义变化）；
  用 `arm_config.json` + smoke 时的 `run_identity` 核对达到同等的操作冻结。
- 每臂根新增 `arm_config.json`（操作件，不改科学判据），至少含：
  ```json
  {
    "arm": "glm|deepseek",
    "expected_model_id": "ZHIPU/GLM-5.3-Flash|deepseek-v4.1-flash-1017",
    "env_file_basename": "llm.env|llm_ds.env",
    "code_commit": "<发车 commit>",
    "questions_sha256": "9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c",
    "preregistration_sha256": "<签字后 SHA>",
    "batch_tag": "t-i-298-20261020",
    "created_at": "<ISO8601>",
    "note": "不含密钥；模型身份以 run_identity 为准"
  }
  ```
- smoke2 后，每臂读头两个 `runs/*/run_identity.json`：`prediction.model_id` 必须与
  `arm_config.json` 逐字一致；前两个 run 的 `prediction` 块（含 `request_params`、
  `timeout_s`、`prompt_versions`、`policy_version`）必须逐字一致。任一项不符 ⇒
  立即 scancel 该臂并停全部两臂，报 CC。
- 两臂不得共享同一个 runs 根；不得把 A 的 runs 根复用给 B。

## 5. 发车链（命令级）

以下命令在 HPC 登录节点执行；重活一律 `sbatch`，不在登录节点跑。

### 5.0 一次设定

```bash
TI_WS="$HOME/ppv1_hpc"
TI_CODE="$HOME/EnzymeAgent/v43cTH"
TI_PY="$TI_WS/venv_v44run/bin/python"
export TI_WS TI_CODE TI_PY
export PYTHONPATH="$TI_CODE/src"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
cd "$TI_CODE"
```

### 5.1 netcheck（硬门）

```bash
WS="$TI_WS" sbatch --parsable scripts/hpc/sbatch_th_netcheck.sh  # 共享只读；不改该脚本
```

判据：`COMPLETED 0:0` 且日志含 `NETCHECK-PASS`。
注意：该脚本当前把 `CODE` 写死为 `$HOME/EnzymeAgent/v43cTH`，且只检查 DashScope 端点
可达，不检查模型级开通；模型开通由 §4.2 预检负责。

### 5.2 两臂 build（D6）

按 §3 执行：两臂独立 build + `verify-identity` 指纹一致硬门。
build 不含模型调用；`ENV_FILE` 不参与 build。

### 5.3 批准件 + no-cap 标记 + P2 探针（每臂）

#### 5.3.1 批准件与文本快照

在 `$TI_WS/operations/t_i_approved_record_20261020/` 预放**完整批准文书包**：

- `preregistration_approval.json`（Codex 代 CC/师姐代决版；字段见下）；
- `budget_no_cap.json`（两臂共用同一份；与 `budget_guard.json` 互斥，不得并存）；
- 四份文本快照（按原字节保存；源文件可保持历史草案）：
  `T_I_PREREG_2026-10-20.md`、`TASK_T_I_LAUNCH_2026-10-20.md`、
  `T_I_CODEX_FINAL_REVIEW_2026-10-20.md`、`T_I_SCRIPT_LOCK_2026-10-20.json`；
  文件名与 `preregistration_docs.<key>.path` 的 basename 一致。

批准 JSON 必填字段（`ti_operations.py prepare` 与首付费 `run` 共用同一验证；
缺失/空 docs/SHA 不符/`no_cap_ack=false`/来源非 Codex 代决链 ⇒ 非零退出，不发车）：

| 字段 | 冻结值/要求 |
|---|---|
| `approval_status` | `preregistration_confirmed` |
| `approval_basis` | `原预注册+任务书+本终审增补` |
| `approval_source_kind` | `codex_delegated_cc_shijie` |
| `approval_source` | 写 Codex 代 CC/师姐及授权来源；**不得伪填 CC 本人已改原文** |
| `approval_authorization_chain` | CC 2026-10-20 授权 → Codex 代决 → 终审报告决议链 |
| `approved_at` | 真实 ISO8601（终审决议 `2026-10-20T15:49:53Z`），不得 TBD |
| `preregistration_id` | `prereg-t-i-298-2026-10-20` |
| `budget_mode` / `user_decision_date` | `no_monetary_cap_user_decision` / `2026-10-20` |
| `no_cap_ack` | **必须 true** |
| `cost_cap_cny` | `null` |
| `preregistration_docs` | 恰含 `prereg`/`task`/`final_review`/`script_lock` 四键，各带仓库相对 `path` 与 64 位 SHA256 |
| `preregistration_text_sha256` | 预注册文本快照 SHA；**不得填批准 JSON 自身哈希** |

生成/校验命令（本机或 HPC 登录节点；`--docs-root` 默认仓库根）：

```bash
"$TI_PY" -B scripts/hpc/ti_operations.py approval-package \
  --record-dir "$TI_WS/operations/t_i_approved_record_20261020" \
  --docs-root "$TI_CODE" --create --approved-at 2026-10-20T15:49:53Z
# 复核（不带 --create 只校验）：
"$TI_PY" -B scripts/hpc/ti_operations.py approval-package \
  --record-dir "$TI_WS/operations/t_i_approved_record_20261020" \
  --docs-root "$TI_CODE"
```

仓库内规范包：`docs/T_I_APPROVAL_PACKAGE_2026-10-20/`（批准 JSON + 四份快照 +
`SHA256SUMS`）；部署到 HPC 记录目录时整包复制，不改内容。

#### 5.3.2 `budget_no_cap.json` 生成（no-cap 执行方式）

CC 2026-10-20 拍板两臂全部不设金额帽。在 HPC 登录节点生成（字段沿 T-H r2 先例）：

```bash
REC="$TI_WS/operations/t_i_approved_record_20261020"
mkdir -p "$REC"
cat > "$REC/budget_no_cap.json" <<JSON
{
  "budget_mode": "no_monetary_cap_user_decision",
  "marker": "no_monetary_cap_user_decision_2026-10-20",
  "note": "CC 2026-10-20 拍板两臂全部不设金额帽;金额检查跳过、金额预约/结算不启用;调用数门(gate_max_calls=4470)/速率门(RPM 200/TPM 3M)/并发门(max_in_flight=8)照常生效;usage(token/调用数)照记;金额无快照记 unknown;与 budget_guard.json 互斥",
  "recorded_at": "$(date -u +%FT%TZ)",
  "schema": "v44-budget-no-cap-1",
  "user_decision_date": "2026-10-20",
  "user_decision_record": "CC 2026-10-20: 全部都不设置buget"
}
JSON
```

核对（只打印字段，不涉及任何密钥）：

```bash
"$TI_PY" - <<'PY'
import json, os
p = os.path.join(os.environ["TI_WS"], "operations",
                 "t_i_approved_record_20261020", "budget_no_cap.json")
d = json.load(open(p))
assert d["budget_mode"] == "no_monetary_cap_user_decision"
assert d["user_decision_date"] == "2026-10-20"
assert "2026-10-20" in d["marker"]
print("TI-BUDGET-NOCAP-PASS", d["schema"], d["marker"])
PY
```

> `recorded_at` 必须是生成时的真实 UTC 时间，不得手填。`ti_operations.py prepare`
> 复制并校验 `preregistration_approval.json` 与 `budget_no_cap.json`，并校验
> `schema/budget_mode/marker/user_decision_date/user_decision_record`；两臂批根各得一份副本。

#### 5.3.3 usage 记录点与金额回填义务

| 记录点 | 内容 | 落盘 |
|---|---|---|
| 预检 | 每臂 1 次最小调用：模型、input/output tokens、耗时、金额或 unknown | `operations/preflight_calls.json` |
| smoke2 | 每臂 2 题：usage、失败原因 | 运行根/`batch_report` |
| smoke10 | 每臂 10 题：usage、外推 total tokens、失败/零调用 | 运行根/`batch_report` |
| full | 每臂 298 题：input/output/total tokens、调用数、重试、零调用、`usage_missing_calls` | `usage`/`batch_report` |
| 金额 | 有账单/价格快照才回填；否则 `cost_status=no_snapshot`、`cost_known_cny=null` | 结果报告费用节 |

- no-cap 下无金额停点；金额未知不阻塞任何阶段。
- 不得用 token×单价估算，不得编造单价；金额一栏只写真数与 unknown。

复制批准件到每臂根并跑 prepare：

```bash
for arm in glm deepseek; do
  "$TI_PY" -B scripts/hpc/ti_operations.py prepare \
    --arm "$arm" --ws "$TI_WS" --code "$TI_CODE" --config "$TI_CODE/scripts/hpc/ti_arm_config.json" \
    || { echo "STOP: prepare $arm"; exit 1; }
done
```

`prepare` 会：核对批准文本 SHA、`approval_status`、build 身份、科学源码两文件 SHA、
no-cap schema/marker、复制批准件，写 `record/ti_operations.json`、`arm_config.json`，
并跑 P2 探针写 `p2_face_measure.json`。
期望（同代码/同资产/同题卷）：`specs_total=531`、`remap_applied=242`、
`remap_add_atom_ge1=205`、`remap_add_atom_ge2=78`、`questions_remap=151`、
`questions_with_add=134`、`questions_with_multi_add=65`、`files=298`。
不符 ⇒ 停，先查 build 是否用了同一代码/资产；不得改探针口径。

### 5.4 run（每臂 smoke2→smoke10→barrier→full）

```bash
for arm in glm deepseek; do
  "$TI_PY" -B scripts/hpc/ti_operations.py launch --phase run \
    --arm "$arm" --ws "$TI_WS" --code "$TI_CODE" \
    --config "$TI_CODE/scripts/hpc/ti_arm_config.json" \
    || { echo "STOP: run $arm"; exit 1; }
done
```

`launch` 按臂解析 `ENV_FILE`/`BATCH_ROOT`/`RUNS_ROOT`/job 名（`ti-{arm}-run`），
并强制批准包（四份文书快照 + 代决来源 + `no_cap_ack=true`）、`arm_config`、
模型 ID、env 权限/内容、no-cap schema、build 身份与两臂停点前置检查。
`sbatch_ti_run.sh` 依次跑 smoke2→smoke10→**两臂 barrier**→full；作业内做
零 CX/失败留证的阶段门与终态门，任一停点写
`$TI_WS/operations/t_i_coordination_t-i-298-20261020/stop.json` 并（可执行时）
`scancel` 两臂 run 作业。

两臂同步放行：任一臂 smoke10 未通过时 barrier 超时并停两臂；**不得先跑完 A
整臂再测 B**。两臂 run 作业提交后，另投一个监控作业（每 15 分钟巡检，单协调者
flock；越线自动停两臂）：

```bash
"$TI_PY" -B scripts/hpc/ti_operations.py monitor --submit \
  --ws "$TI_WS" --code "$TI_CODE" --config "$TI_CODE/scripts/hpc/ti_arm_config.json"
```

手工巡检/急停（登录节点，零模型）：

```bash
"$TI_PY" -B scripts/hpc/ti_operations.py monitor --ws "$TI_WS" --checks 1
"$TI_PY" -B scripts/hpc/ti_operations.py halt --ws "$TI_WS" \
  --reason "manual coordinator halt" --cancel
```

> **运行中 fatal 停派发（TI-F1 2026-10-21 回修）**：把隔离 worktree 补丁
> `docs/review_evidence/ti_f1_fatal_2026-10-21/orchestrator_stop_dispatch.patch`
> 应用到部署代码树的 `src/pathway_v43/pollutant/s5b_orchestrator.py`（主树不合并，
> 待 Codex 复审后合并）。补丁给 `run_s5b_batch` 增加默认 `None` 的 `stop_check`
> 回调；部署树支持时，T-I wrapper 收割 fatal 后立即写两臂停点并停止派发新 qid。
> 未打补丁时仍由 phase/monitor 末端兜底，但不满足“收割后立即停派发”。
> 已在途请求不撤回，取消时点照实记录。

并行/顺序：

- 默认建议（D8 主窗口技术默认，CC 可改）：两臂预检全过后**并行**发车，保持同一时间窗；每臂独立 gate。
  **两臂 run 作业必须都提交后**，任一臂才可能在 barrier 等到对侧 smoke10；不得先提交
  A 整作业并等它结束后再提交 B（A 会卡在 barrier 直到超时停臂）。
- 若账号级 429/TPM 挤兑：改为错峰提交（两臂作业仍都提交，仅用调度延迟/依赖错开），
  每臂 smoke10 后先核 usage/tokens 与失败率；仍须两臂 smoke10 都通过后才准任一 full。
  顺序会引入时间窗差异，结果披露。no-cap 下不因金额改跑法。

### 5.5 smoke 判据（每臂；Codex 2026-10-20 终审 §3 冻结）

以下判据由 `ti_operations.py phase/run-gate` 机器强制，不靠人看日志：

smoke2 后立即检查：

1. 至少 1 题 completed **且真实模型调用可核**（`model_calls>0`）；
2. 所检 2 题均终态（pending=0）；
3. `run_identity.prediction.model_id` 与 `arm_config.json` 一致；前两个
   `prediction` 块逐字一致；
4. usage 可解析（completed 且有调用的题必须 `usage.present=true` 且
   input/output/total 三键为整数）；
5. 无 fatal 信号（auth/quota/402/403/401/identity/integrity/no-cap marker/
   `unregistered_cx_class`）。

任一项不满足 ⇒ 停两臂，不进入下一阶段。

smoke10 后：

1. 10 题全部终态（仍有 pending ⇒ 停）；
2. 非豁免 `failed > 0` ⇒ 停该臂并停另一臂（终态 failed 必须先处置，不能以
   “模型内容”口头豁免）；
3. 未登记结构性原因的零调用 `>0` ⇒ 停两臂；已登记 NC-9
   （`ProductionContractError / cosubstrate_copy_in_expectation`，
   `counts.events=0`）按未中登记、豁免；
4. 按「实测每调用 token × 预期 298 次调用」外推该臂 total tokens；写入运行记录
   并与预注册 §6.3 的规划带并列披露；
5. **不设 token/金额硬停**（no-cap）；外推显著超规划带上沿（>8.06M）只告警并报 CC，
   不自动停 full；
6. 任何 429 风暴、连续传输故障（连续 2 个不同 qid 未按冻结策略恢复）⇒ 停报。

任一臂 smoke10 不过 ⇒ 停全部两臂，保留现场；**两臂 smoke10 都通过并写入
barrier 放行件后**，才准任一臂进入 full。不单独让其它臂跑 full。

### 5.6 score（每臂）

full 门通过后：

```bash
for arm in glm deepseek; do
  "$TI_PY" -B scripts/hpc/ti_operations.py launch --phase score \
    --arm "$arm" --ws "$TI_WS" --code "$TI_CODE" \
    --config "$TI_CODE/scripts/hpc/ti_arm_config.json" \
    || { echo "STOP: score $arm"; exit 1; }
done
```

默认判分顺序 v1→v2；根文件 headline=v2；输出 `metrics.json{,.v1,.v2}`、
`report*.md*`、`ti_score_complete.json`。可选用 `TI_INCLUDE_V3=1`（经 `launch` 环境传入）
打开 v3 纯披露：顺序 v1→v3→v2，追加 `.v3` 与 `criteria_v3_disclosure.json`，并做
v3/v2 稳定字段对账；差异即停交付。两臂都 score 完成后才拉回。

### 5.7 拉回与封存

- 只拉：默认 v1/v2 的 metrics/report、`batch_report.json`、`orchestration.json`、
  `profile_policy.json`、`build_identity.json`、`p2_face_measure.json`、`arm_config.json`、
  失败登记、usage/费用摘要、批准记录副本。落到 `reports/ppv1_s5b/t_i_2026-10-20/<arm>/`。
  v3 未打开时不拉 `.v3` 文件。
- 不拉：题卷、`reference_graphs/`、逐题 case/state/run 正文、含模型自由文本的大件。

拉回示例（本地执行；只列白名单文件；`KEY` 指本机 600 权限私钥路径）：

```bash
TI_WS_REMOTE=/work/home/aclhl3hbth/ppv1_hpc
for arm in glm deepseek; do
  mkdir -p "reports/ppv1_s5b/t_i_2026-10-20/$arm"
  for f in metrics.json metrics.json.v1 metrics.json.v2 \
           report.md report.md.v1 report.md.v2 \
           report_plain.md report_plain.md.v1 report_plain.md.v2 \
           batch_report.json orchestration.json profile_policy.json build_identity.json \
           p2_face_measure.json arm_config.json ti_score_complete.json ti_full_status.json; do
    scp -i "$KEY" -P 65091 \
      "aclhl3hbth@wuzh02.hpccube.com:$TI_WS_REMOTE/batch/t_i_298_20261020_$arm/$f" \
      "reports/ppv1_s5b/t_i_2026-10-20/$arm/" || { echo "STOP: pull $arm/$f"; exit 1; }
  done
  # 仅当 TI_INCLUDE_V3=1 时追加拉取：
  # metrics.json.v3 report.md.v3 report_plain.md.v3 criteria_v3_disclosure.json
done
```

> 不要用远端通配符拉整目录；不要拉题卷/金标/逐题 case 正文。

- 每臂用 `seal` 子命令封存：校验 `ti_score_complete.json` 与全部产物 SHA，写
  `ti_sealed.json`，目录 555/文件 444；runs 根不封：

```bash
for arm in glm deepseek; do
  "$TI_PY" -B scripts/hpc/ti_operations.py seal \
    --arm "$arm" --ws "$TI_WS" --code "$TI_CODE" \
    || { echo "STOP: seal $arm"; exit 1; }
done
```

- 封存前确认 score 完成、SHA 清单一致；封存后只读，不再补评分、不再写。
- `ti_sealed.json` 已在 `mutable()` 的 sealed 名单内（默认值即该名）。

## 6. 操作入口：已采用 `ti_operations.py`（独立参数化入口）

**实施状态：已参数化；TI-F1/F2 回修后本机合成正负控 55 项 + 公共链 15 场景 + 实际调度探针 2 场景。**
未使用既有 T-H 入口的直接改写，而是新建薄入口 `ti_operations.py` + `ti_run_wrapper.py`
+ `sbatch_ti_*`，保留 T-H 的调度/恢复/评分安全语义，只参数化操作面。尚未真实发车；
合成绿不等于真实可跑。

| # | 面 | 实现 |
|---|---|---|
| 1 | 臂/批/运行根/job 名 | `ti_arm_config.json` 两臂（glm/deepseek）；job 名 `ti-{arm}-{phase}` |
| 2 | batch_tag | `t-i-298-20261020`，两臂同值（D6 指纹门需要） |
| 3 | prepare source commit | `--source-commit` 参数化；默认读 config `c9c6c7a`；`arm_config.json` 记录实际值 + 预注册文本 SHA + 批准包 SHA |
| 4 | sealed 名 | `mutable()` 识别 `ti_sealed.json`（含 `sealed.json`/`th_sealed.json`/`SEALED`/`.sealed`） |
| 5 | 评分 | 默认 v1+v2；根 headline=v2；`--include-v3` 才跑 v3 纯披露并做 v3/v2 稳定字段对账；full 门 schema/digest 阶段末复核 |
| 6 | no-cap | `budget_no_cap.json` schema+mode+marker+date+user_decision_record 校验；与 `budget_guard.json` 互斥 |
| 7 | 发车防重 | `pending_submission` 意图、同阶段重投一次上限、封存/旧批拒写 |
| 8 | D6 身份门 | `verify-identity` 比 manifest SHA/fingerprint/逐题 run_input sha；缺指纹或空 sha 直接停 |
| 9 | TI-F1 阶段门 | `phase`/`run-gate` 按唯一 qid 计数：smoke2 身份/usage、smoke10 failed/未登记零调用/pending、full >15 运行失败、fatal、连续故障、恢复一次/二败 |
| 10 | 两臂协调 | `barrier`（两臂 smoke10 都过才准 full）、`stop.json` 首写生效、`monitor` 15 分钟单协调者、`halt --cancel`/自动 `scancel` |
| 11 | TI-F2 批准包 | `approval-package` 生成/校验；`prepare` 与首付费 `run` 共用四文书 + 代决来源 + `no_cap_ack` + 文本/批准哈希分列校验 |
| 12 | 运行中 fatal 停派发 | 隔离 worktree 补丁 `docs/review_evidence/ti_f1_fatal_2026-10-21/orchestrator_stop_dispatch.patch`；`run_s5b_batch(stop_check=...)` 默认 None（其它批行为不变），收割 fatal 后不再派发新 qid；T-I wrapper 在部署的 orchestrator 支持时自动开启 |

不要改的部分：`phase_guard` 的恢复家族白名单、重试一次/二败停、flock 单协调者、
`prebuild` 非空拒、评分语义。任何改动不得触碰 `src/`、`tests/` 与判分语义。

发车前把实际使用的脚本 SHA 落 `docs/T_I_SCRIPT_LOCK_2026-10-20.json`，部署后逐文件核对；
本报告与证据目录已给出当前 SHA256 清单。

## 7. 停点与失败处置

### 7.1 停点表（Codex 2026-10-20 终审 §3 冻结；代码执行位置）

| 阶段/信号 | 最终阈值 | 处置（`ti_operations.py` 执行位置） |
|---|---|---|
| 预检 | 任一模型 401/403/402/400、模型 ID 不符、env 缺失、`reasoning_effort` 不兼容 | 停全部；不 build/不 run；报 CC（`require_env` / `_launch_preconditions`） |
| build | 作业非零、无 `TI-BUILD-PASS`、build-gate 失败 | 停；不 run；查日志（`sbatch_ti_build.sh`） |
| D6 身份 | manifest/fingerprint/逐题 run_input sha 任一不同；缺指纹/空 sha | 停；不进入 prepare/run（`verify_identity`） |
| prepare | 批准包缺件、文本/脚本锁 SHA 不符、`no_cap_ack!=true`、来源非 Codex 代决链、缺 build_identity、P2 分母异常 | 停；不改审批、不改探针（`validate_approval_package` / `prepare`） |
| smoke2 | 无“completed 且真实调用可核”的题；仍有 pending；模型/`prediction` 身份不符；usage 不可解析；fatal 信号 | 停两臂，不进入下一阶段（`evaluate_stage` label=smoke2） |
| **smoke10** | **非豁免 `failed>0`，或未登记结构性原因零调用 `>0`，或仍有 pending** | **停该臂并停另一臂，不进入 full**（`evaluate_stage` label=smoke10；`barrier_full`） |
| **full** | **非模型内容运行失败 `>15`（第 16 个失败 qid 起停）**；pending>0；fatal 信号 | **停两臂、保全现场，不在无效批上判模型**（`evaluate_stage` label=full；monitor 每 15 分钟） |
| 任一阶段致命信号 | 任一次 auth/权限/欠费/配额不可用；模型/身份/完整性/no-cap marker 错误；未登记 CX；持续限流或连续传输故障未按冻结策略恢复（连续 2 个不同 qid） | 立即停两臂并保全，不等累计（`classify_case` fatal / `consecutive_outage`） |
| 恢复 | 仅原 prediction_recovery 白名单、同题同参一次、先保全；二败停 | 不新增重试（`phase_guard` retry_count / recovery_second_failure） |
| token/金额 | **无 token/金额硬停**；超规划带只告警登记；金额 unknown | gate 调用数/速率/并发上限保持；不估造金额（`token_projection`，`action=warn_only`） |
| score | 全 qid 未终态；full 门回执 schema/digest 与现存 case 不符；V3 稳定字段差异；评分回执 SHA 不符 | 停；不交付；不抬分（`score_all` 阶段末完整性复核） |
| 任何范围外 | 新参数、新 prompt、新判据、换模型、改分母 | 一律停；另立预注册 |

两臂协调：任一臂触发停点写 `coordination_dir/stop.json`（首个写入者生效，不覆盖），
并（可执行时）`scancel` 两臂 run 作业；另一臂在每个阶段前查停点。monitor 作业
每 15 分钟巡检两臂，单协调者 flock；手工急停用 `halt --cancel`。

> **TI-F1 状态（2026-10-21 回修）**：smoke2/smoke10/full 阈值、两臂 barrier、monitor、
> stop/scancel 路径已写入 `ti_operations.py` / `sbatch_ti_run.sh` /
> `sbatch_ti_monitor.sh`。**2026-10-21 复审补洞**：`classify_case` 对
> `status=completed` 内嵌 `run_error`（如真实 worker 的 `forbidden_permanent`）
> 在 completed 提前返回前判为 fatal；连续故障按分类事实而非仅 `status=failed`
> 计数。运行中停派发需部署隔离 worktree 补丁
> `orchestrator_stop_dispatch.patch`（主树未合并），T-I wrapper 在支持时传入
> `stop_check`，收割 fatal 后不再派发新 qid。本机正负控 55 项 + 公共链 15 场景 +
> 实际调度探针 2 场景通过；**待 Codex 按固定面复核**，复核关闭前不宣布发车。

### 7.2 实施默认（主窗口技术默认，CC 可改）

| 代号 | 当前实施默认 | 备注 |
|---|---|---|
| D6 | **两臂独立 build + 指纹一致硬门**（`verify-identity`） | 主窗口技术默认，CC 可改；改 seed+拷贝需重写 §3 并保持同一身份判据 |
| D7 | **代码冻结 `c9c6c7a`** | 主窗口技术默认，CC 可改；两臂同一提交，科学源码两文件 SHA 已锁 |
| D8 | **两臂并行**（同时间窗；每臂独立 gate） | 主窗口技术默认，CC 可改；账号级 429/TPM 挤兑时改顺序（同参） |
| D9 | **DeepSeek 模型 ID `deepseek-v4.1-flash-1017`** | CC 2026-10-20 晚定名；批中不得换名 |
| TI-F1 | **监控/双臂阶段硬停已写入代码**（smoke2/smoke10/full 阈值、致命信号、恢复一次/二败、15 分钟 monitor、双臂 barrier、stop/scancel 路径）；**2026-10-21 补 completed+run_error fatal 分类与实际调度停派发** | 2026-10-21 回修；`ti_operations.py` + `ti_run_wrapper.py` + `sbatch_ti_run.sh` + 隔离 worktree 补丁；待 Codex 复核关闭 |
| TI-F2 | **批准包首次消费校验已写入代码**（四份文书快照、逐件 SHA、代决来源/授权链、`no_cap_ack=true`、文本 SHA 与批准 JSON SHA 分列） | 2026-10-20 回修；`validate_approval_package`/`validate_batch_approval` 由 prepare 与 run 首消费共用；待 Codex 复核关闭 |

> **TI-F1/TI-F2 当前状态：已实施 + 本机合成正负控通过；未过 Codex 固定面
> 复核前不宣布发车。** 证据：`docs/T_I_TI_F1_F2_REPORT_2026-10-20.md` 与
> `docs/review_evidence/ti_f1f2_2026-10-20/`。

> 以上是操作/工程默认，不改变预注册判定线与冻结面；改动必须在发车前落字并同步
> `ti_arm_config.json`、预注册/任务书与本报告，不得批中改。

## 8. 出数后的交付义务

产出 `docs/T_I_RESULT_2026-10-20.md`（技术版）+ `_PLAIN.md`（大白话版），至少含：

1. **身份表**：两臂模型 ID、env basename、代码 commit、科学代码聚合、build fingerprint、
   题卷 SHA、判分版本、profile/gate/超时/重试、`evidence_card=false`；
2. **两臂主表**（v2 headline；v1 敏感性并列）：hit@1/@3/@5、strict(U)、三桶计数、分母 298；
3. **主比较**：B−A（唯一主比较）；配对 b/c/net/n_disc、精确 McNemar 双侧 p；
   Newcombe 95% CI（Wald 敏感性并列）；不做多重校正；
4. **桶迁移**：A 锚定的 partial/unmatched→hit 与 strict→非 hit 的计数；chain13 锚定对照表；
   按 M2 主判定 + M1 严格敏感性并列给判定；
5. **判定矩阵**：逐臂给「模型有效 / 弱效应 / 结构性线索 / 无差异 / 负效应」，并引预注册条款；
6. **费用/usage**：每臂 input/output/total tokens、missing calls、重试、金额；no-cap 下无金额帽，
   金额=事后账单回填，无快照如实写 unknown，不估算；
7. **失败/零调用**：逐题原因、是否影响分母、是否结构性；
8. **限制**：单批、单次、模型默认采样、两臂并行/顺序的时间窗、共享 batch_tag/run_id、
   max_tokens 未显式设置、两臂无金额帽（费用事后回填/可能 unknown）等；
9. **题域标签**：每张表带 298 标签；不写通用能力；
10. **封存/证据路径**：两臂批根、本地镜像、SHA 清单、作业号。

叙事纪律：

- 只有「5pp + M2 桶迁移」全过，才可写「模型有效（本任务形态）」；
  S2 下 McNemar p 仅强制报告、不作单独否决；M1 结果必须并列披露；
- 仅总分差 ⇒「弱效应」，不立项；
- 两臂无差异 ⇒「单模型形态天花板坐实，转架构议题」；
- 任一臂负效应 ⇒ 如实写，不救；
- 不把 chain13/T-H 历史数字当本批同批对照；跨批差异必须标注配置/时间差。

## 9. 机坑（T-H 移交书 §7 + T-I 新增）

| # | 坑 | 处置 |
|---|---|---|
| 1 | ZCode 子代理 token-plan 配额耗尽 | 代审/监控改 CC 亲验或手动搬运；不阻塞批跑 |
| 2 | Codex 额度窗口 | 本批不依赖 Codex；评审走 CC 指定通道 |
| 3 | tar 从外置盘带 `._*` | HPC 解包后 `find . -name "._*" -delete` |
| 4 | HPC 钥匙在 `/Volumes/CC/Enzyme_Agent/` | `chmod 600`；不进仓、不打印 |
| 5 | `budget_no_cap.json` 缺 `budget_mode`/marker | 必须含 `budget_mode="no_monetary_cap_user_decision"` + 日期 marker；与 `budget_guard.json` 互斥 |
| 6 | 3600s 超时不重试 | 慢调用可能挂近 1h；不早杀；timeout 不重发 |
| 7 | sbatch 日志写在提交 cwd | 在 `$TI_CODE` 提交，日志 `th_*.out`；拉回时按作业号找 |
| 8 | 节点 `/tmp` 满导致 heredoc 炸 | 门逻辑写实体脚本；本任务书的 heredoc 只在登录节点短命令使用 |
| 9 | 登录节点跑重活被静默 SIGKILL | 一律 sbatch 到计算节点 |
| 10 | HPC 登录节点 `/tmp` 轮转不共享 | 中转走家目录 |
| 11 | 老 rsync 不认 `--info`、不建多级父目录 | 先 `mkdir -p`；用兼容参数 |
| 12 | 模型返回 temperature 400 | policy `temperature=None`；若仍 400，查 env 是否混入温度键，停报 |
| 13 | `envcheck` 报 `configured=false` 的老假阴性 | 只作参考；以最小真实调用为准 |
| 14 | 两臂并行可能撞账号级 RPM/TPM | 模型级池先例不代表账号级无限；429 风暴则停/改顺序（同参） |
| 15 | no-cap 两臂无金额帽 | 费用=事后账单回填，金额未知记 unknown、不估算；用量（token/调用数）照记；gate_max_calls=4470/臂仍是硬上限 |
| 16 | 两臂共享 `batch_tag`/`run_id`（D6 独立 build 但同 tag） | 结果与证据显式披露；若逐臂不同 `batch_tag`，必须改比较口径（不得比 raw 输入 sha） |
| 17 | `launch` 的 pending_submission 意图 | 无可靠 job id 时先核 squeue/sacct，禁止盲重投 |
| 18 | 封存后误写 | `ti_sealed.json` 或 `sealed.json`；chmod 555/444；`mutable()` 名单同步 |
| 19 | 旧批只读 | T-H/chain13 批根零写入；新批根不存在或为空才发 |
| 20 | `PYTHONDONTWRITEBYTECODE=1`/`OMP_NUM_THREADS=1` | 全程带；避免 `__pycache__` 与线程超额 |

## 10. 红线

1. 预注册先于付费；无签字不发车、不预检付费调用。
2. 判分/评测零 LLM；模型只出 proposals。
3. 金标隔离：题卷/参考图/逐题 case 只留 HPC；本地只拉指标/身份件。
4. 一批跑完、禁止修一点跑一点；批中零代码/配置/prompt/模型改动。
5. 封存旧批只读；两臂新批根；旧批零回写。
6. 不 push；push 时机归 CC。
7. 题域标签处处带；298 与 dev 双向不外推。
8. 单变量=模型；任何额外差异=停报 CC。
9. 失败/零调用不剔题；不换题、不补跑换题。
10. 探针≠预注册≠成绩；弱效应不写成模型有效；单批排序不写成稳定结论。

## 11. 回传义务

- 每步完成回报「做了什么/读数/下一步」：预检、build、身份门、prepare、每臂 smoke2、
  每臂 smoke10、每臂 full、每臂 score、拉回封存，各一次；
- 预检失败/用量异常/429 风暴/CX/身份错误/连续失败 ⇒ 立即停并报 CC，不自动处置
  （no-cap 下无金额停点；金额未知不阻塞，账单异常单独报）；
- 出数后按 §8 出技术版+大白话版，刷主 TODO 行 9 与 T-H 移交书 §6 挂账；
- 不 push；不新增付费批；不把本批结果写进老师既定目标的达成声明。