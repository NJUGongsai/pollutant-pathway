# TASK — T-H Stage 0 独立复核与分诊成文（120 题，零模型）

> **题域：298 = RHEA 通用酶学 / 已见题，post-hoc。** 所有计数只在该题域内成立，不向
> dev、新题或其他题域外推。
>
> **任务性质：只读复核 + 成文。** 不重跑实验、不重判、不调模型、不改源码、不读金标 /
> reference_graphs / 题面 / 候选 SMILES / state 载荷。主会话已跑通一次 dry run；执行者
> 独立重跑、核验、写 brief，并在任何计数不一致时停下来报告。
>
> **执行者：** 只读分析子代理（general）。**不 commit、不 push、不改 src/tests/docs/AGENTS.md。**
>
> **交付：** `docs/review_evidence/t_h_stage0_triage_2026-10-20/stage0_brief.md` +
> 复核后的 `stage0_summary.json` / 三份 prefix CSV / `SHA256SUMS`；回传一段结论。

## 0. 一句话

T-H 的 209 个未命中里，**32 题排序 + 41 题覆盖 + 47 题二级旧候选**是可分诊的 120 题。
主会话 dry run 的结论是：**排序层 32/32 个被评分 strict 对照的 matched 事件都是模型
自排位（model_selection），这些 matched 事件没有系统 fallback（同组全部 178 个事件里
另有 9 个 deterministic_fallback，不在 matched 集合）；覆盖层 41 题的模型自报状态不能
当评分覆盖缺口的代理；二级 47 题全部都有 rank1 候选，失败更像结构/匹配，而不是“没候选”
或“没排序”。** 执行者要独立确认这三句话，
并把“能做什么 / 不能做什么”写成 brief。

## 1. 背景与现状（只读）

| 项 | 值 |
|---|---|
| T-H headline | 89 / 298（criteria-v2） |
| 209 未命中分层 | 近失排序 32、近失覆盖 41、二级旧候选 47、旧口径无候选 47、空池 40、零调用 2 |
| 本任务范围 | 32 + 41 + 47 = **120 题** |
| 不在范围 | 旧口径无候选 47、空池 40、零调用 2（供给/合约层，另线） |
| 主分析 | `docs/T_H_HIT1_RECOVERY_ARCH_OPTIONS_2026-10-20.md` |
| 分诊脚本 | `docs/review_evidence/t_h_stage0_triage_2026-10-20/` |
| 封存批 | `t_h_s5b_298_20261020r2`（build 46954982 / run 46958084 / score 46969374） |

### 1.1 主会话 dry run 的期望计数（执行者必须逐项确认或证伪）

| 指标 | 期望值 |
|---|---:|
| 记录数 | 120 |
| 分组 | near_rank 32 / near_coverage 41 / secondary_old_candidate 47 |
| native_result 找到 | 120 / 120 |
| manifest found / run_id mismatch / pool mismatch | 120 / 0 / 0 |
| native 多文件 | 0 |
| `selection_model_order` | **32** |
| `selection_fallback_or_inherited` | 0 |
| `coverage_model_declared_incomplete` | 23 |
| `coverage_has_complete_but_partial` | 18 |
| `secondary_rank1_partial_unmatched` | 43 |
| `secondary_rank1_complete_unmatched` | 4 |
| `supply_no_events` / `supply_rank1_missing` | 0 / 0 |
| `rank_map_missing` / `native_missing` | 0 / 0 |

> 注：`selection_fallback_or_inherited = 0` 只指 32 个被评分 strict 对照的 matched
> 事件。同组全部 178 个事件里另有 9 个 `deterministic_fallback`、11 个
> `model_rank != effective_rank`（9 fallback + 2 model_selection）、1 个带继承标记；
> 这些都不是 matched 事件，不能把“matched 无 fallback”外推成“全组无 fallback”。

排序 32 题细节：

| 指标 | 期望值 |
|---|---:|
| matched 事件找到 | 32 / 32 |
| matched rank_basis | model_selection 32 |
| model_rank == effective_rank | 32 / 32 |
| `n_candidate_events == n_events` | 32 / 32 |
| `main_rank <= n_candidate_events` | 32 / 32 |
| 每个 main_rank 唯一对应事件 | 32 / 32 |
| matched 事件自报状态 | partial 32 |
| rank1 事件自报状态 | partial 28 / declared_complete 4 |
| main_rank 分布 | 2:17, 3:8, 4:5, 5:1, 6:1 |
| matched 事件参与物数 | 2:29, 3:3 |

覆盖 41 题细节：

| 指标 | 期望值 |
|---|---:|
| 全部假设自报 partial | 23 |
| 至少一个自报 complete，评分仍 partial | 18 |
| rank1 自报状态 | partial 29 / declared_complete 12 |
| 假设状态合计 | partial 177 / declared_complete 30 |
| bookkeeping missing refs > 0 | 0 |

二级 47 题细节：

| 指标 | 期望值 |
|---|---:|
| 无事件 | 0 |
| rank1 存在 | 47 |
| rank1 自报状态 | partial 43 / declared_complete 4 |
| 旧口径 rank1 | 20 |
| 至少一个自报 complete | 15 |

退化叠加：

| 指标 | 期望值 |
|---|---:|
| 120 范围内退化题 | 12（8 排序 + 3 覆盖 + 1 二级） |
| 其中三批稳定损失 | 8 |
| 稳定损失分类 | selection 6 / coverage_has_complete 1 / secondary 1 |

## 2. 目标与非目标

**目标：**

1. 独立重跑 120 题提取，确认 120/120、32/41/47、无 missing / mismatch。
2. 核对 32 题排序：是否全部 `model_selection`，matched 事件是否唯一、`main_rank` 是否
   与 `effective_rank` 一致。
3. 核对 41 题覆盖：23 / 18 的 split 是否成立；明确“自报 partial 不等于评分 partial”。
4. 核对 47 题二级：是否全部有 rank1；43 / 4 的 split 是否成立；明确“有 rank1 但
   unmatched”不是供给/排序问题。
5. 写 brief，把“能确认的层 / 不能确认的层 / 需要什么新数据”讲清楚。

**非目标：**

- 不证明任何题“可恢复”；不对 35%–40% 线做预测。
- 不做候选级 / 事件级金标匹配；不判断“匹配器误拒”还是“候选结构错”。
- 不重跑 T-H，不改判据，不调模型，不碰封存批。
- 不为覆盖层或二级层写生产代码；本任务只出分诊结论。
- 不把 47 无候选 / 40 空池 / 2 零调用混进 120 的结论。

## 3. 红线

1. **不读**金标、reference_graphs、题面、候选 SMILES、state 载荷、`contexts` / `paths` /
   `alternatives` / `deferred_entries.object` / `blocked_entries` 正文、`s5b_responses` 正文。
2. **不打印**任何 `smiles`、`inchi`、`formula`、`state` 载荷；只允许 ID 前缀、计数、状态、
   side/role 字符串、rank 字段。
3. **不重跑**实验、不重判、不调模型；只读 `native_result.json`、`batch_manifest.json`、
   本地 metrics / seed。
4. **不写** HPC 的 batch/runs；只允许在 HPC home 放一个临时 seed 文件，用完立刻删。
5. **不 commit / 不 push / 不改** `src/`、`tests/`、既有 `docs/`、`AGENTS.md`。
6. 计数不一致时停下报告，不猜、不补、不“修正”原始数据。

## 4. 输入与工具

### 4.1 本地文件

| 路径 | 用途 |
|---|---|
| `reports/ppv1_s5b/t_h_2026-10-20/stage0/seed.json` | 120 题 seed（full qid；gitignored） |
| `reports/ppv1_s5b/t_h_2026-10-20/stage0/stage0_raw.json` | 主会话 dry-run 原始提取（959K） |
| `reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json` | 主口径 / 旧口径 per_qid |
| `docs/review_evidence/t_h_r2_loss_attr_2026-10-20/r2_run_meta.json` | pool_size / model_calls |
| `docs/review_evidence/t_h_r2_loss_attr_2026-10-20/degradations_16.csv` | 16 退化题 |
| `docs/review_evidence/t_h_stage0_triage_2026-10-20/make_seed.py` | seed 复算 |
| `docs/review_evidence/t_h_stage0_triage_2026-10-20/extract_stage0.py` | HPC 只读提取 |
| `docs/review_evidence/t_h_stage0_triage_2026-10-20/summarize_stage0.py` | 本地汇总 |
| `docs/T_H_HIT1_RECOVERY_ARCH_OPTIONS_2026-10-20.md` | 主分析 |

### 4.2 HPC

```bash
ssh -i ~/.ssh/hpc_wuzh02_key -p 65091 -o BatchMode=yes \
  aclhl3hbth@wuzh02.hpccube.com
```

| 路径 | 用途 |
|---|---|
| `~/ppv1_hpc/batch/t_h_s5b_298_20261020r2/batch_manifest.json` | qid / run_id / pool_size |
| `~/ppv1_hpc/runs/t_h_s5b_298_20261020r2/<run_id>/results/run-native-result:*/native_result.json` | 只读事件/rank/participant 元数据 |
| `~/ppv1_hpc/runs/t_h_s5b_298_20261020r2/<run_id>/s5b_responses/` | 只数文件数，不读正文 |

### 4.3 提取白名单（脚本已实现）

允许输出：qid、group、run_id 前缀、pool_size、main status/rank、old rank、remap/add、
native schema/created_at/payload_hash 前缀、事件数、假设数、action 数、outcome 数、
s5b 文件数、事件 ID/hypothesis ID/parent path ID 前缀、participant 数、side/role 计数、
state_ref 计数、ambiguous 计数、`participant_list_status`、`step_scope`、requirements/
assumptions 计数、action kind/status、model_rank、effective_rank、rank_basis、
rank_policy_version、inherited 布尔、report product 数 / basis 计数 / dedup_notes 计数、
bookkeeping 计数/状态。

禁止输出：任何化学字符串、state payload、candidate SMILES、reference/gold、题面、
`contexts`/`paths`/`alternatives`/`deferred_entries.object`/`blocked_entries` 正文、
`s5b_responses` 正文、participant `entry_id`、coefficient 数值。

## 5. 分诊口径（描述性，不是因果）

| 类别 | 定义 | 能说什么 / 不能说什么 |
|---|---|---|
| `selection_model_order` | 32 题里 matched 事件 `rank_basis=model_selection` 且 `model_rank=effective_rank` | 能说“系统没有重排，模型自己把它放在第 N 位”；不能说“换个 ranker 就能捞回” |
| `selection_fallback_or_inherited` | matched 事件 rank_basis 非 model_selection，或 model/effective 不一致 | 能说“系统排序参与”；本批期望 0 |
| `coverage_model_declared_incomplete` | 41 题里所有假设 `participant_list_status=partial` | 只能说“模型从未自报 complete”；**不能说**“评分 partial 的成因就是模型少列参与物” |
| `coverage_has_complete_but_partial` | 41 题里至少一个假设自报 complete，但评分仍 partial | 能说“自报 complete 也不够”；参考侧缺口 / 匹配器 unknown |
| `secondary_rank1_partial_unmatched` | 47 题里 rank1 事件存在且自报 partial，但评分 unmatched | 能说“不是没候选、不是没排序”；结构/覆盖/匹配器 unknown |
| `secondary_rank1_complete_unmatched` | 同上但 rank1 自报 complete | 更像结构/匹配问题；仍不能定因 |
| `supply_no_events` / `supply_rank1_missing` | 无事件 / 有事件但无 rank1 | 供给或 rank 元数据问题；本批期望 0 |

**关键 caveat（必须写进 brief）：**

- 32 个评分 strict 的 matched 事件**全部**自报 `participant_list_status=partial`。
  所以 `participant_list_status` 是模型自评，不是评分覆盖缺口的代理；23 题
  “全部自报 partial”不能当成 23 题可补全。
- 41 题覆盖层目前**没有** per-event / per-participant 的评分侧缺口明细；brief 必须把
  “可行动子集”标成 unknown，而不是给一个拍脑袋的数字。
- 47 题二级全部有 rank1 候选；这说明供给/排序不是主因，但不能反过来说“结构错”已被
  证明，只能标“structure/matcher/coverage unknown”。

## 6. 执行步骤

### Step 0 — 预检（本地）

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
git status --short
python3 - <<'PY'
import json
s=json.load(open("reports/ppv1_s5b/t_h_2026-10-20/stage0/seed.json"))
print(s["n"], {g:sum(1 for r in s["records"] if r["group"]==g) for g in
      ("near_rank","near_coverage","secondary_old_candidate")})
PY
shasum -a 256 docs/review_evidence/t_h_stage0_triage_2026-10-20/*.py
```

期望：seed n=120，分组 32/41/47；工作树没有与本任务冲突的改动。若有冲突，停下报告。

### Step 1 — 独立重跑 HPC 提取

```bash
scp -i ~/.ssh/hpc_wuzh02_key -P 65091 -o BatchMode=yes \
  reports/ppv1_s5b/t_h_2026-10-20/stage0/seed.json \
  aclhl3hbth@wuzh02.hpccube.com:~/ppv1_hpc/stage0_seed_20261020.json

ssh -i ~/.ssh/hpc_wuzh02_key -p 65091 -o BatchMode=yes \
  aclhl3hbth@wuzh02.hpccube.com \
  'python3 - ~/ppv1_hpc/stage0_seed_20261020.json' \
  < docs/review_evidence/t_h_stage0_triage_2026-10-20/extract_stage0.py \
  > reports/ppv1_s5b/t_h_2026-10-20/stage0/stage0_raw_verify.json

ssh -i ~/.ssh/hpc_wuzh02_key -p 65091 -o BatchMode=yes \
  aclhl3hbth@wuzh02.hpccube.com \
  'rm -f ~/ppv1_hpc/stage0_seed_20261020.json'
```

若 SSH 失败：最多重试 1 次；仍失败则停下，报告“HPC 不可达”，不要用 dry-run 结果冒充
独立复核。

### Step 2 — 对比 dry run 与 verify

```bash
python3 - <<'PY'
import json
a=json.load(open("reports/ppv1_s5b/t_h_2026-10-20/stage0/stage0_raw.json"))
b=json.load(open("reports/ppv1_s5b/t_h_2026-10-20/stage0/stage0_raw_verify.json"))
A={r["qid"]:r for r in a["records"]}; B={r["qid"]:r for r in b["records"]}
print("qids",len(A),len(B),"same_set",set(A)==set(B))
diff=[q for q in A if A[q]!=B[q]]
print("diff_qids",len(diff),[q[:16] for q in diff[:10]])
PY
```

- 若 0 diff：在 brief 里写“独立重跑逐记录一致”。
- 若有 diff：列出 diff 字段（不要打印化学字符串），判断是时间戳/顺序还是事实差异；
  事实差异必须停下报告，不得强行合并。

### Step 3 — 汇总（用 verify raw）

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  docs/review_evidence/t_h_stage0_triage_2026-10-20/summarize_stage0.py \
  reports/ppv1_s5b/t_h_2026-10-20/stage0/stage0_raw_verify.json \
  > /tmp/stage0_summary_verify.json
```

检查 `docs/review_evidence/t_h_stage0_triage_2026-10-20/stage0_summary.json` 的
`inputs.raw.path` 应指向 verify 文件；计数应与 §1.1 一致。

### Step 4 — 抽检 5 题（只读，不打化学字符串）

从三组各抽 1–2 题（建议 2 排序 + 2 覆盖 + 1 二级），对每题核对：

1. `native_result.json` 的 `events[].hypothesis_id` 与 `search_commit_records[].event_id`
   能对上；
2. `search_actions[].payload.model_rank / effective_rank / rank_basis` 与提取 JSON 一致；
3. `hypotheses[].payload.participant_list_status` 与提取 JSON 一致；
4. `events[].payload.participants` 的 side/role 计数与提取 JSON 一致；
5. 排序题：`effective_rank == main_rank` 的事件只有一个。

把抽检结果写进 brief 的“抽检”小节（qid 前缀 + pass/fail，不写化学）。

### Step 5 — 写 brief

新建 `docs/review_evidence/t_h_stage0_triage_2026-10-20/stage0_brief.md`，建议结构：

```markdown
# T-H Stage 0 分诊简报（120 题，零模型）

> 题域... 只读... 不承诺收益...

## 0. 结论先行（4 条以内）
## 1. 范围与完整性（120/120、32/41/47、0 missing）
## 2. 分层表（5 类 + unknown）
## 3. 32 排序题：32/32 model_selection；17 题只差一位；8 个稳定损失里 6 个在这层
## 4. 41 覆盖题：23 all-partial / 18 has-complete；自报 partial 不是评分 partial 的代理；
##    可行动子集 unknown
## 5. 47 二级题：47/47 有 rank1；43 partial / 4 complete；不是供给/排序，
##    结构/匹配 unknown；旧口径 rank1 20
## 6. 对恢复路线的影响：选择层是唯一干净杠杆；覆盖层需要评分侧明细；
##    二级层需要候选级诊断；供给/空池/零调用不在本任务
## 7. Unknown / 下一步
## 8. 复现命令与证据哈希
```

**brief 必须写死的三句话：**

1. “32/32 个被评分 strict 对照的 matched 事件是模型自排位，没有系统 fallback；这只
   说明位次来自模型，不证明换卡 / prompt 一定捞回。同组全部事件里另有 9 个
   deterministic_fallback，不在 matched 集合。”
2. “32 个评分 strict 的匹配事件全部自报 partial；所以自报状态不能当覆盖缺口信号，
   23 题 all-partial 不是 23 题可补全。”
3. “47 题二级全部有 rank1 候选；失败不是没候选/没排序，结构/覆盖/匹配器无法从本数据
   分层。”

### Step 6 — 哈希与回传

```bash
cd docs/review_evidence/t_h_stage0_triage_2026-10-20
shasum -a 256 make_seed.py extract_stage0.py summarize_stage0.py \
  seed_summary.json stage0_summary.json stage0_summary_auto.md \
  rank32_prefix.csv coverage41_prefix.csv secondary47_prefix.csv \
  stage0_brief.md > SHA256SUMS
shasum -a 256 -c SHA256SUMS
```

回传格式（给主会话）：

```
Stage 0 复核：PASS / FAIL
- 120/120；分组 32/41/47；native 120；manifest mismatch 0
- 32 排序：model_selection 32；model_rank=effective 32；rank2 17
- 41 覆盖：all-partial 23；has-complete 18；可行动子集 unknown
- 47 二级：rank1 47；partial 43；complete 4；旧 rank1 20
- 退化：12 在范围；稳定 8（6 排序 / 1 覆盖 / 1 二级）
- 抽检：5/5 PASS（或列出 fail）
- 新增/修改文件：...
- 未 commit；未读金标/题面/候选 SMILES；未重跑/调模型
```

## 7. 验收标准

- [ ] 120 条记录，32/41/47，native 120，manifest mismatch 0。
- [ ] 32 排序：32/32 `selection_model_order`，32/32 `model_rank=effective_rank`，
      32/32 `n_candidate_events=n_events`，每个 main_rank 唯一事件。
- [ ] 41 覆盖：23/18 split；brief 明确“自报 partial ≠ 评分 partial”。
- [ ] 47 二级：0 no-event；47 rank1；43/4 split；brief 明确“不是供给/排序”。
- [ ] 退化叠加：12 在范围，8 稳定（6/1/1）。
- [ ] 抽检 5 题全 PASS，或 fail 有解释。
- [ ] 无化学字符串；无金标/题面/候选 SMILES；无 HPC batch/runs 写入。
- [ ] `SHA256SUMS` 全部 OK。
- [ ] 未 commit。

## 8. 排障表

| 现象 | 处理 |
|---|---|
| SSH 失败 | 重试 1 次；仍失败停下报告，不用 dry-run 冒充 |
| native_result not found | 记录 qid 前缀，标 `native_missing`；不要猜 |
| `n_candidate_events != n_events` | 停下，检查 rank 映射；不要强行汇总 |
| main_rank 对应多个事件 | 标 `rank_map_missing`，停下报告 |
| seed 分组不是 32/41/47 | 停下，重跑 `make_seed.py` 并对比 metrics |
| verify 与 dry run 有事实 diff | 列出字段，停下报告；不要合并 |
| `participant_list_status` 全 partial | 这是本批已知现象，不是脚本 bug；写进 caveat |
| 输出里出现 `smiles`/`Cl`/`state` 载荷 | 立即停止，删除该输出，修白名单后重跑 |
| HPC 临时 seed 忘记删 | 立即删；不要留在 home |

## 9. 文件清单

| 文件 | 性质 |
|---|---|
| `docs/TASK_T_H_STAGE0_TRIAGE_2026-10-20.md` | 本任务书 |
| `docs/review_evidence/t_h_stage0_triage_2026-10-20/make_seed.py` | seed 复算 |
| `.../extract_stage0.py` | HPC 只读提取（白名单） |
| `.../summarize_stage0.py` | 本地汇总 / CSV / 自动表 |
| `.../seed_summary.json` | seed 计数（无 qid） |
| `.../stage0_summary.json` | 分诊计数（无 full qid） |
| `.../stage0_summary_auto.md` | 自动表 |
| `.../rank32_prefix.csv` / `coverage41_prefix.csv` / `secondary47_prefix.csv` | 前缀级明细 |
| `.../stage0_brief.md` | **执行者交付的简报** |
| `.../SHA256SUMS` | 哈希 |
| `reports/.../stage0/seed.json` | full qid（gitignored） |
| `reports/.../stage0/stage0_raw.json` | dry-run 提取（gitignored） |
| `reports/.../stage0/stage0_raw_verify.json` | 独立复核提取（gitignored） |
| `reports/.../stage0/*_full.csv` | full qid 明细（gitignored） |

## 附录 A — 期望计数的来源

- 主会话 dry run：`stage0_raw.json` + `summarize_stage0.py`（2026-10-20）。
- 32 排序题：`near_rank` 32；matched 事件由 `main_rank == effective_rank` 唯一映射；
  `n_candidate_events == n_events` 32/32。
- 41 覆盖题：`near_coverage` 41；模型自报状态合计 177 partial / 30 declared_complete。
- 47 二级题：`secondary_old_candidate` 47；rank1 47；旧口径 rank1 20。
- 退化：`degradations_16.csv` 与 120 seed 的交集 12；三批稳定损失 8。

## 附录 B — 一句话给非本线读者

这次不是“再跑一遍模型”，而是把 120 道没中的题按“模型自己排错位 / 参与物没列全 /
候选结构不对 / 根本没候选”分开。分完发现：排序层最干净（32 题全是模型自己排的），
覆盖层现有数据分不动（模型自报 partial 不可信），二级层不是没候选（47 题都有 rank1），
更像结构问题。所以下一步先做排序层的证据卡 A/B，覆盖层要补评分侧明细，二级层要候选级
诊断；不要拿这份分诊当“能捞 30 题”的承诺。
