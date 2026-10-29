# TASK_P2_REBUILD_AFTER_SRCFIX_2026-10-26 — fatal 修复动 src 后的重建与再验收

> 触发条件：CC 修复线对 `state_fact_rederivation_mismatch`（`cn_identity` writer/validator 不同源）的修复**触碰 `src/`**。
> 口径：正式批次-单臂（B=v2card）；A 臂暂不 full。
> 前置：本文件经 CC 确认后执行；未确认不得重建、不得发车。

## 0. 为什么必须重建

- `build_identity.code_identity_aggregate_sha256` 覆盖 87 个 `.py`；`chemstate.py` 一变，聚合变化。
- 现有 10-23 build 记录 `cfd74067…`，修复后代码不再匹配 ⇒ `check_build_identity` / run_identity 身份门会 fail-closed。
- 因此：**修复 + 重建 + 新身份 + 补充披露**四件必须一起做，旧 build 不得用于正式批。

## 1. 前置（缺一不动）

| # | 条件 | 证据 |
|---|---|---|
| 1 | 修复 commit 落地且相关测试全绿 | commit SHA、测试日志 |
| 2 | 修复口径已由 CC 拍板：**B（写侧跟验侧；CN 从去映射号的规范身份算；无映射号存量 CN 不变；带映射号输入改 canonical CN）** | CC 2026-10-26 决策 |
| 2b | patch + sha256 已交付（本地不 push），附改动文件清单与测试命令/结果 | patch 文件、`sha256sum`、`git diff --stat` |
| 2c | B 口径零漂移验收：无映射号静态输入 CN 逐条不变；带映射号 = 去映射 canonical；旧录制态兼容 | 验收脚本与输出 |
| 3 | 46 题回归集零模型重放通过（`cn_identity` 分歧 0、无新门） | 回归证据目录 |
| 4 | 单元性质通过：工厂产物必过首消费验（含括号冗余写法） | 性质测试日志 |
| 5 | CC 批准"重建 + 补充披露"路径 | 本文档签注 |

## 2. 代码身份确认（notebook，只读）

```bash
cd /root/v43_migration/v43cP2
git rev-parse HEAD 2>/dev/null || echo "NO_GIT"
# 按 run_identity.code_identity 同法重算 87 个 .py 聚合
PYTHONPATH=src python3 -B - <<'PY'
# 复用 src/pathway_v43/.../run_identity.code_identity 的实现，输出聚合 SHA
PY
```

要求：记录 HEAD、聚合 SHA、与修复 commit 一致；不一致则停。

> **彩排发现（2026-10-26）**：notebook 部署树**无 `.git`**，HEAD 无法在机复核。正式重建必须用以下二者之一补证：①从 HPC/本地仓记录修复 commit SHA + 87 个 `.py` 聚合三处互证；②迁移 git 元数据后再复核。补充披露里必须写明所用证据类型。

## 3. 重建（零模型，约 50 分钟）

新根命名（不动 10-23 根）：
- seed：`/root/v43_migration/ppv1_hpc/batch/p2_nb_seed_20261026`
- 两臂：`.../batch/p2_298_20261026_v1card|v2card`
- 配置：`config/p2_arm_config_nb_20261026.json`（`batch_tag` 仍 `p2-298-20261021`；`batch_name/runs_name` 用 20261026；`coordination_dir=operations/p2_coordination_nb_20261026`；`source_commit=<新 commit>`；`code_identity_aggregate_sha256=<新值>`）

```bash
cd /root/v43_migration/v43cP2
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 \
python3 -B -m pathway_v43.pollutant.s5b_cli build \
  --questions /root/v43_migration/ppv1_hpc/questions.jsonl \
  --batch-root /root/v43_migration/ppv1_hpc/batch/p2_nb_seed_20261026 \
  --batch-tag p2-298-20261021 \
  --provider-kind real --pool-mode template --recorded-source \
  --max-pool 8 --pool-threshold 0.45 \
  --v3-code-root /root/v43_migration/dependingv3 \
  --assets-root /root/v43_migration/v43cP2/assets
# → chain13_gate.py build-gate
# → p2_operations.py build-copy --config <新配置> --seed-root <新 seed>
# → 两臂 prepare --config <新配置> --batch-root <新臂根> --source-commit <新 commit>
```

**关键检查**：新 build 的 298 份 `run_inputs` 与 298 份 `reference_graphs` 必须与 20261023 build **逐字节相同**（静态输入 0 CN 分歧的预期结果）。任何差异 ⇒ 停，先解释差异再继续。

## 4. 新身份归一 + 披露 v2

- 对 `p2_nb_seed_20261026` 与两臂重做路径归一（方法复用 `normalize_identity.py`）；记录新指纹、与 HPC 口径的差异字段。
- 产出 `docs/review_evidence/p2_nb_identity_2026-10-26-v2/`：新 build 指纹、298/298 字节证据、`source_commit` 变化、`code_identity` 变化、重建说明、预注册 §6.2 身份门偏离。
- qwen3.8max 代 Codex 复审通过后生效。

## 5. fatal 再验收

- 单元性质 + 46 题回归集零模型重放（用新代码、新 build 副本；响应走 blob）。
- 期望：`cn_identity` 分歧 0；无 `state_fact_rederivation_mismatch`、无新门；`s5b_real_calls` 零新增；源批根哈希不变。

## 6. 入口与发车

- 部署入口 v2.1（含 `FULL_ARMS=v2card` 拒发硬闸、U7 代码源核对）。
- `deploy_3` 的 U7 必须对**新 build** 通过；`plan` 全绿；`dryrun` 6/6。
- 然后 smoke2 → smoke10 → full(B) → score。停点照预注册 §6.2。
- 发车命令必须带 `FULL_ARMS=v2card LAUNCH_CONFIRMED=CC-20261026 NOT_A_DRILL=yes`。

## 7. 时间账

重建 ~50 min；身份归一 + 证据 ~15 min；qwen 复审 ~20 min；入口部署+预检 ~10 min；smoke 若干；full 待测速外推。

## 8. 红线

- 不动 10-23 旧批根/旧 build；新根新配置。
- 不改锁内脚本、不改判据/评分/门阈值；修复只来自 CC 修复线。
- 零模型完成 build/prepare/身份/回归；金标只取哈希。
- 任何身份/差异异常 ⇒ 停，报告，不绕过。

## 9. 变更记录

- 2026-10-26：初版，等待 CC 修复口径与 commit。
- 2026-10-26 彩排结果（零模型，当前代码）：build 48m53s、build-gate OK、build-copy PASS、两臂 prepare 八项全中；298 run_inputs 与 298 reference_graphs **逐字节相同**，manifest/identity 0 字段差异；彩排指纹 `de19dc6e…` → 归一 `76858eb4…`（selfcheck 9/9）。结论 **PASS_IDENTICAL**；证据 `docs/review_evidence/p2_rebuild_rehearsal_2026-10-26/`。正式重建时 `date_stamp` 用 `20261026`。