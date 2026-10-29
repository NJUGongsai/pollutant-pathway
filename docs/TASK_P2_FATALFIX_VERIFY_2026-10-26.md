# TASK_P2_FATALFIX_VERIFY_2026-10-26 — B 口径 cn_identity 修复的独立验收

> 触发：CC 修复线交付 patch + sha256 + 改动文件清单 + 测试命令/结果。
> 口径：CC 2026-10-26 拍板 **B**（写侧跟验侧；`cn_identity` 从**去映射号的规范身份**算；无映射号存量 CN 不变；带映射号**且已落库**输入改 canonical CN）。
> 性质：独立验收，不重复修复工作；不改批根/不改锁内/不调模型。

## 0. 输入清单（缺一不开工）

| # | 输入 | 检查 |
|---|---|---|
| 1 | patch 文件 | `shasum -a 256` 与交付值一致 |
| 2 | 改动文件清单 | 与 patch 实际 diff 一致；列明是否动 schema/兼容层 |
| 3 | 测试命令/结果 | 可复跑；无结果则本验收自行跑 |
| 4 | 修复 commit SHA（或 patch 基准 commit） | 用于 code_identity 与披露 |

## 1. 隔离树与 patch 应用

```bash
BASE=/private/tmp/p2_fix_verify_20261026
git -C /Volumes/CC/Enzyme_Agent/dependingv43 worktree add --detach "$BASE/tree" 966bc56
cd "$BASE/tree"
git apply --check <patch> && git apply <patch>
shasum -a 256 <changed files>   # 与清单逐项比
git diff --stat                  # 与文件清单一致
```

记录：基准 HEAD、patch sha、应用后各文件 sha、`git diff` 全文。
**红线**：只在隔离树应用；主树、notebook `v43cP2`、批根、config、env 一律不动。

## 2. 八项验收

### V1 patch 完整性

- 应用 `--check` 无冲突；改动文件数/路径 = 清单；
- 若 patch 改 schema/兼容层，必须单独列出并说明迁移路径。

### V2 单元性质（同源）

- 对一组输入（无映射号、带映射号 1–19、立体、电荷、同位素、带显式 H 的括号写法）：
  `st = build_chemical_state(x, STRUCTURE_ORIGIN_SOURCE_PRODUCT)` 后
  `validate_state_object(st)` 与 `ChemicalState.from_dict(st.to_dict())` 均不得抛错；
- 期望：writer 与 validator 用同一 CN 来源，0 异常。
- 若 fatal 原始串只存在于 notebook `/tmp` 副本，则在副本上做一次同性质检查；**不打印串**。

### V3 无映射号存量零漂移（硬门）

- 读迁移的 117 个 run DB/状态产物（只读），对 **646 个已落库 state** 用**打补丁后的代码**重算 CN；
- 与落库 CN 逐条比：**必须 646/646 相同**；
- 任何一条不同 ⇒ 红停；列出 state_id/哈希（不打印结构）。

### V4 带映射号且已落库

- 普查已知：存量 0 条；若实现后仍为 0，记 0/0 并引用 `batch_scan/map_number_census.json`；
- 若发现 >0：CN 必须等于「去映射号 canonical CN」，列出 qid/state_id/条数，并确认无键冲突。

### V5 46 题回归（零模型）

- 用打补丁后的代码 + 录制响应 blob，重放 46 题（含 fatal 题）：
  - `failure_kind` 不再出现 `state_fact_rederivation_mismatch`；
  - 无新门（`raw_identity_mismatch` 等换字段也算失败）；
  - `s5b_real_calls` 零新增、`model_requests` 无新行；
  - 源批根哈希不变。

### V6 旧录制态兼容

- 读取旧 case/state store 的路径（`ChemicalState.from_dict`、store 首消费）不得因 B 口径产生新 mismatch；
- 期望：0 新 mismatch；若有，按缺陷回修，不得靠跳过校验通过。

### V7 评分零漂移（能离线则做）

- 45 个非 fatal 回归题：用修复前后代码分别离线评分（零 LLM），headline/hit@1/@3/@5/strict/partial/unmatched 逐题一致；
- fatal 题：修复后可评（不再是 failed 无导出）；
- 若评分链路依赖模型/环境不可离线，如实标 unknown，不伪造。

### V8 代码身份与不可变性

- 按 `run_identity.code_identity` 同法重算 87 个 `.py` 聚合，记录新值；
- 源批根/旧 build/锁内脚本哈希不变；无 `.pyc` 写入；notebook 业务树 0 新文件。

## 3. 判定与产出

- 总裁定：**PASS / PASS_WITH_CONDITIONS / NO-GO**；
- 逐项红绿表 + 未过项的最小回修；
- 产出 `docs/review_evidence/p2_fatal_fix_verify_2026-10-26/`：
  `VERIFY_REPORT.md`、`patch_info.json`（sha/文件清单）、`cn_zero_drift.json`（646 条哈希级）、`regression_46.json`、`score_drift.json`、`code_identity_after.json`、`SHA256SUMS`。
- 全绿后：补充披露（新 commit、code_identity、重建说明）→ qwen 代审 → 重建 → 新身份归一 → 入口预检 → smoke/full。

## 4. 红线

- 零模型、零 DashScope；金标只取哈希、不打印题面/结构；
- 只读 notebook 业务目录；不改批根/源码/配置/批准包；不 push；
- 任何"换字段报错""跳过校验""回填旧回执"均不算通过。

## 5. 变更记录

- 2026-10-26：初版，按 CC B 口径与 8 项验收单编写。