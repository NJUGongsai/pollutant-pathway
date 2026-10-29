# TASK_P2_FATALFIX_DEPLOY_RELOCK_2026-10-26 — 活体部署、重锁、批准包重绑、独立复验

> 前置：`docs/TASK_P2_FATALFIX_VERIFY_2026-10-26.md` 的隔离八项验收 **PASS**。
> 上游：`docs/HANDOFF_P2_FATAL_FIX_2026-10-26.md`、`docs/T_P2_FATAL_FIX_2026-10-26.md` §5/§8/§11。
> 口径：B（写侧 canonical CN）；不 commit/push；`source_commit` 保持 `11aeeaf…`。
> 性质：notebook 活体部署与重绑；零模型、零发车。

## 0. 前置与停点

### 0.1 隔离验收实测前提（2026-10-26，PASS_WITH_CONDITIONS）

- 硬门全绿：646/646 存量 CN 零漂移；46 题重放 91/91 可重放 completed、0 failure_kind（1 个 v2card 无 run）；旧态 646/646 `from_dict`；新 code identity `c565cd56…`（87 文件仅 `chemstate.py` 不同）。
- 环境条件（不指向修复缺陷）：
  1. 活体树**有 `.git`（0 commit）**，交接书说无；
  2. 活体 `tests/test_p2_v1card_mode.py` **已是修后字节** `4c18ab53…`（第三段 hunk 预置），直接 `patch` 会报已应用 ⇒ 用 `patch -p1 --forward` 并**以三件 SHA 为准**；
  3. patch 第三段缺 `diff --git` 头；GNU patch 正常；
  4. 全量 `2409 passed` 在 notebook 复现不了（缺 `langgraph.checkpoint.sqlite`，基线本身 93 失败）⇒ 验收口径 = **失败集与修前逐项相同 + 通过数 +11**（隔离实测 2298P/93F/18S/16D vs 基线 2287P/93F/18S/16D）；
  5. v1 off-path 18/20，2 项仅因 python/rdkit/v3-git 元数据差；
  6. fatal 重放需第三族身份适配（code identity `cfd74067→c565cd56`），否则停在 `IdentityMismatch`（设计后果）。

| # | 条件 | 动作 |
|---|---|---|
| 1 | 隔离八项验收 PASS | 引用证据目录与报告 |
| 2 | notebook 无并发 P2 作业 / 无同批根双发 | `ps`、`entry.pid`、协调目录、批根 mtime；发现即停 |
| 3 | 主 patch SHA = `b4e0fbf2…` | `shasum -a 256` |
| 4 | 可选 audit-wrap **不应用** | 不复制、不 patch |

## 1. 备份与 apply（活体树）

```bash
cd /root/v43_migration/v43cP2
cp -a src/pathway_v43/pollutant/chemstate.py{,.bak.fatalfix}
cp -a tests/test_p2_v1card_mode.py{,.bak.fatalfix}
patch -p1 --dry-run < /root/.../chemstate_cn_fix.patch   # 期望无 FAILED
patch -p1 < /root/.../chemstate_cn_fix.patch
```

## 2. 文件与解释器核对

| 文件 | 期望 SHA |
|---|---|
| `src/pathway_v43/pollutant/chemstate.py` | `495d3d0e8ad5fb40d7d557a865a51a1e07d8e51f73e8775a6d72f9842861fdeb` |
| `tests/test_p2_fatal_cn_fix.py` | `daa07201f6ff8ac2e20f8295e52aebd838685e64e05329b1bcdb7e95805a905d` |
| `tests/test_p2_v1card_mode.py` | `4c18ab53c540982ef6ceb25bbf507f0b6d147d17c00e683a62137e3437e96cfc` |

```bash
PYTHONPATH=/root/v43_migration/v43cP2/src python3 -c \
  "import pathway_v43; print(pathway_v43.__file__)"
# 必须指向 /root/v43_migration/v43cP2/src
```

## 3. 活体测试（notebook run env）

- 新增 11：`pytest tests/test_p2_fatal_cn_fix.py -q`
- 定向 57：`tests/test_p2_v1card_mode.py tests/test_p2_v2_chemfix.py tests/test_p2_fatal_cn_fix.py`
- 全量：`pytest -m "not slow" -q -p no:cacheprovider` → notebook 验收口径 **失败集与修前逐项相同 + 通过数 +11**（修前基线 2287P/93F/18S/16D；期望 2298P/93F/18S/16D）；`2409 passed` 只在有 langgraph 的本地环境成立，不作为 notebook 门。
- chemfix 19/19、fatal 复现 novel-1/2、v1 零漂移 20/20（命令见修复报告 §11.3，路径换 notebook）
- RDKit 2026.03.5（run env）；若与本地 2026.03.6 数字不同，必须至少重跑新增测试 + 19 探针 + 复现探针，确认 CN/state_id 结论一致；否则停。

## 4. 新配置（新 batch_tag）

按交接书 §3.9 与 CC 决策：**新 `batch_tag = p2-298-20261026`**。

| 字段 | 值 |
|---|---|
| `batch_tag` | `p2-298-20261026` |
| seed 根 | `batch/p2_nb_seed_20261026` |
| 两臂 batch_name/runs_name | `p2_298_20261026_{v1card,v2card}` |
| `coordination_dir` | `operations/p2_coordination_nb_20261026` |
| `date_stamp` | `20261026` |
| `source_commit` | 保持 `11aeeaf…`（不 commit） |
| `identity_expectations.code_identity_aggregate_sha256` | `c565cd56…` |
| `identity_expectations.rdkit_version` | 部署 run env 实测（预期 2026.03.5） |
| `record_dir` | 保持 `operations/p2_approved_record_20261021` |
| 配置路径 | `/root/p2_nb_entry_20261026/p2_arm_config_nb_20261026.json` |

用入口 `new-tag-config` 派生后改上述字段，并用锁内 `load_config` 复核；同时更新部署树内 `scripts/hpc/p2_arm_config.json`（如存在）的 code_identity/source_commit/rdkit 字段。

## 5. 重锁（24 条清单，按修复报告 §5）

生成 `docs/T_P2_SCRIPT_LOCK_2026-10-26.json`（部署树内同名）：
- `files`：src 90 件 + `scripts/hpc` 8 件 + 文档 3 件，按部署树**字节实测**重算；`chemstate.py`=`495d3d0e…`；`p2_arm_config.json`=新配置 SHA。
- `identity.code_identity_aggregate_sha256`=`c565cd56…`；`identity.measured_on`=新部署树/日期；`source_commit` 保持 `11aeeaf…`。
- `patches` 追加 `chemstate_cn_fix.patch`（`b4e0fbf2…`）；不加 optional audit-wrap。
- `generated_at` 更新；`missing=[]`；`approval_binding` 的 prereg/chem/task SHA 保持不变。
- 部署到 `~/ppv1_hpc/operations/p2_approved_record_20261021/`。

## 6. 批准包重绑（不入预注册正文）

| 字段 | 动作 |
|---|---|
| `script_lock_sha256` / `preregistration_docs.script_lock.sha256` | 新锁 SHA |
| `identity_expectations.code_identity_aggregate_sha256` | `c565cd56…` |
| `batch_tag` | `p2-298-20261026`（新 tag；披露） |
| `source_commit` | 保持 `11aeeaf…` |
| `preregistration_text_sha256` / `preregistration_docs.prereg.sha256` | 保持 `86242516…` |
| `chem_review_doc_sha256` | 保持 `1bea16b2…` |
| `task_doc_sha256` | 保持 `01b1896f…` |
| `approval_sha256` | 按 canonical JSON（排除自身与算法说明）重算 |
| `SHA256SUMS` | 重生成；加入补充披露/复审请求（如入包） |

重绑后用 `p2_operations.py approval-package`（或锁内校验）复核；任何字段不符 ⇒ 停。

## 7. 独立复验（活体）

- fatal qid `RXNG_ebe76…` 的 novel-1/novel-2 零模型重放：不再 `state_fact_rederivation_mismatch`；
- 负控：raw 指向另一分子仍抛 `raw_identity_mismatch`；
- 记录 `pathway_v43.__file__`、文件 SHA、命令、HEAD/NO_GIT、预期/实际输出；
- 646/646 存量 CN 零漂移（活体代码只读复算）；
- 产出 `docs/review_evidence/p2_fatal_reverify_2026-10-26/` + `SHA256SUMS`。

## 8. 之后（不在本任务内自动执行）

- 重建：新 tag/新根 build → build-gate → build-copy → prepare；298 run_inputs/reference_graphs 与旧 build 逐字节相同；新指纹；
- 身份归一 v2 + 补充披露 + qwen 代审；
- 入口预检（新配置、`FULL_ARMS=v2card`、U7 对新 code identity）；
- smoke2 → smoke10 → full → score。

## 9. 红线

- 不 commit/push；不改预注册正文/签字字段；不碰 T-I 文件/旧批根/runs/stop。
- 金标只在 `/root/v43_migration`（700）；不打印、不入仓。
- 任何 SHA/身份/测试不符 ⇒ 停，不绕过。

## 10. 变更记录

- 2026-10-26：初版，按交接书与修复报告 §5 编写；等待隔离验收 PASS。

## 11. 执行结果（2026-10-26，活体）

| 项 | 结果 |
|---|---|
| apply | `patch -p1 --forward`；三件 SHA 全中（`495d3d0e…`/`daa07201…`/`4c18ab53…`）；v1card hunk 已预置跳过；无 `.orig/.rej` |
| 解释器 | `pathway_v43.__file__` 指向活体树 |
| 测试 | 新增 11、定向 57、chemfix 19/19、负控 2 passed；全量修后 **2313P/93F/3S/16D** vs 同环境修前 **2302P/93F/3S/16D**；失败集 93/93 逐项相同、+11 passed |
| 新配置 | `/root/p2_nb_entry_20261026/p2_arm_config_nb_20261026.json` SHA `f8089791…`；`load_config` OK；`batch_tag=p2-298-20261026` |
| 新锁 | `T_P2_SCRIPT_LOCK_2026-10-26.json` SHA **`828c527b0e0c342b7304bfba542941c2d3953af906a693d98e53ff4effeca959`**；101 files；`chemstate=495d3d0e…`；identity `c565cd56…`；`source_commit=11aeeaf…`；`patches` 含 `b4e0fbf2…`；`missing=[]` |
| 批准包 | 锁 SHA/path→`828c527b…`/`docs/T_P2_SCRIPT_LOCK_2026-10-26.json`；`batch_tag→p2-298-20261026`；新增 `identity_expectations`；canonical `approval_sha256=f0b782bb…`；文件 SHA `69765620…`；`approval-package` rc=0 |
| 复验 | fatal qid completed / `failure_kind=None`（修前 failed）；`detail_keys=[]`；`s5b_real_calls Δ0`、`model_requests Δ0`；states 2→5、actions 6→9；目标 state CN 34/`f6b6adde`/映射号 0；646/646 零漂移；`from_dict` 646/0；负控 2 passed |
| 条件 | 活体有 `.git`（0 commit）；全量 2409 不可复现（按基线+11）；批准包原无 `identity_expectations`/`source_commit`；入口默认 config 仍旧，发车须 `P2_NB_CONFIG`；重锁期间 6 个 `.pyc` 已删、最终 0 新 `.pyc` |
| 待补 | 已补：批准包绑定 `source_commit=11aeeaf…`、`run_config_path`、`run_config_sha256=f8089791…`；新 canonical `approval_sha256=d950bf1d…`、文件 SHA `c0b4c381…`；`approval-package` rc=0；锁 `828c527b…` 未变 |