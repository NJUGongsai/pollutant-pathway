# T-H 老师杠杆 1：37 题位次成因分类表（2026-10-21）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 本表所有题数、比例、位次读数只在该题域成立；
> 与 dev（B1 环境路径中间步骤）双向不外推。
>
> 批：`t_h_s5b_298_20261020r2`（封存只读；build 46954982 / run 46958084 / score 46969374）。
> 性质：**只读诊断，零模型调用、零新批次、零金标/reference_graphs 内容、零结构正文输出**。
> 判分口径：v2 headline；分母固定 298；本表只分类成因，不改判分、不改批次。
>
> 本表不是收益承诺。**37 是池；若 37 题全部排到首位是 +37 的数学上限；实际能兑现多少 unknown**
> （无同题 A/B、无 prompt 消融）。分类计数为「已证」观察值，不是「可回收」预测值。

## 0. 结论先行

| 判定项 | 结果 | 标签 |
|---|---|---:|
| 37 题是否全闭合 | **37/37 闭合**（每题都有唯一 strict 对照事件 + 完整 rank 字段） | 已证 |
| 成因分类 | **model_ranking 37 / execution_assembly 0 / fallback_default 0 / unknown 0** | 已证 |
| strict 事件 rank_basis | `model_selection` 37/37；`deterministic_fallback` 0 | 已证 |
| 显式 rank 声明 | `model_rank` 显式整数 37/37；默认补齐 0；null 0 | 已证 |
| 模型 rank = effective rank | 37/37 | 已证 |
| strict 事件提交位次 = effective rank | 37/37 | 已证 |
| 折叠导致 strict 事件丢位次 | **0 题**；2 题有 dedup，均未让 strict 事件后移（1 题反而前移） | 已证 |
| 与 P0-A 37/37 显式结论一致 | **一致，逐字段零 mismatch** | 已证 |

**按老师任务书 §一 Day 2 分支：`model_ranking` 占主导（37/37），本周期不实施执行/装配层修复，
不立项 chain15；模型侧排序提示词变量写入 T-I 下一轮候选清单**
（`docs/T_I_PROMPT_RANK_VARIABLES_2026-10-21.md`）。
清单**不塞进当前 T-I 单变量（模型）批**，只作后续轮次的预注册候选。

## 1. 分类口径

| 分类 | 判定条件（互斥，按序） | 本表计数 |
|---|---|---:|
| `fallback_default` | strict 事件 `rank_basis=deterministic_fallback`，或 `model_rank=null` | 0 |
| `execution_assembly` | strict 事件提交位次 ≠ effective_rank，或 effective_rank ≠ model_rank，或 strict 提案被折叠且未继承位次 | 0 |
| `model_ranking` | 显式 `model_selection` 且位次 >1；提交位次 = effective_rank = model_rank；折叠若有也只前移 | **37** |
| `unknown` | 事件不唯一、payload 缺失或关键字段缺失 | 0 |

补充说明：

- 「模型原始 rank」取 `search_actions[].payload.model_rank`；「模型自排名」另用
  `expansion_outcomes[].outcome_payload.outcome.detail.model.model_rank_by_id` 交叉核对。
  37 题里 36 题两者相同；1 题（`RXNG_330b8f55167f5f3`）模型自排第 4，因折叠继承升到第 3。
- 「最终提交位次」按 `events[].created_at` 升序（同秒按 `event_id`）编号，与 P0-A 同法；
  提交记录 `search_commit_records[].created_at` 同步核对。
- 通道映射：`rec-` → recorded；`tpl-` → analog（模板 analog）；`novel-*` → novel。
  事件 payload 的 `logical_proposal_id` 为主证据，hypothesis `origin_group_key` /
  `proposal_context.output_origin` 为独立交叉核对；37/37 一致。

## 2. 37 题逐题分类表

**证据图例**（每行只列字段名；全值见 `docs/review_evidence/t_h_lever1_rank_2026-10-21/lever1_rank.json`）：

- `M` = `reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json`：`per_qid[].main.rank`
- `A` = `payload.json`：`search_actions[].payload.{model_rank,effective_rank,rank_basis,logical_proposal_id,model_rank_inherited_from}`
- `C` = `payload.json`：`search_commit_records[].created_at` + `events[].created_at`（提交序）
- `D` = `payload.json`：`expansion_outcomes[].outcome_payload.outcome.detail.model.dedup_rejections`
- `A.mr`/`A.er` = 模型 rank / effective rank；`C.pos` = 提交位次；`D=yes` 见 §3。

| # | qid 前缀 | strict rank | strict 通道 | 模型 rank | rank_basis | dedup 折叠 | 提交 pos/eff | 归属 | 分类 | 证据字段引用 |
|---:|---|---:|---|---:|---|---|---|---|---|---|
| 1 | `RXNG_16560019e952c8d` | 2 | novel | 2 | model_selection | r5:novel:noinh | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=yes |
| 2 | `RXNG_18a3c06e4220c1a` | 2 | recorded | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 3 | `RXNG_1c56dceb435794a` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 4 | `RXNG_3c9d29b41b6fe86` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 5 | `RXNG_3f134aaae71514b` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 6 | `RXNG_57e0d0320b6da42` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none; pool=0 |
| 7 | `RXNG_5d15fc190935315` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 8 | `RXNG_5d62b57e8f2b22f` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none; pool=0 |
| 9 | `RXNG_5e86f7ef4c770cc` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 10 | `RXNG_61667af8d9ca477` | 2 | recorded | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 11 | `RXNG_675fcec2d1552c0` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 12 | `RXNG_8335f1e8d985cbd` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 13 | `RXNG_94c56325db7601a` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 14 | `RXNG_9b313824f01c1f9` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 15 | `RXNG_b139babc703701f` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 16 | `RXNG_b978fd0b540c4b5` | 2 | analog | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 17 | `RXNG_ddbcc56d1537bfe` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none; pool=0 |
| 18 | `RXNG_e5bcfa56a186e67` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 19 | `RXNG_e97de46f27c0238` | 2 | analog | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none; 序列缺 rank4（见 §3.2） |
| 20 | `RXNG_ebe7683e257c827` | 2 | novel | 2 | model_selection | none | 2/2 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=2/er=2; C.pos=2; D=none |
| 21 | `RXNG_068c774f44f8a28` | 3 | novel | 3 | model_selection | none | 3/3 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=3/er=3; C.pos=3; D=none |
| 22 | `RXNG_0c352348a848d6e` | 3 | novel | 3 | model_selection | none | 3/3 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=3/er=3; C.pos=3; D=none |
| 23 | `RXNG_28cc9c753e5ca9b` | 3 | novel | 3 | model_selection | none | 3/3 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=3/er=3; C.pos=3; D=none; pool=0 |
| 24 | `RXNG_330b8f55167f5f3` | 3 | novel | 3（自排 4） | model_selection | r3:novel:inh（自排 r4→r3） | 3/3 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=3/er=3; C.pos=3; D=yes |
| 25 | `RXNG_4c2cd0c3e1c5a7e` | 3 | novel | 3 | model_selection | none | 3/3 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=3/er=3; C.pos=3; D=none |
| 26 | `RXNG_65536b469cf8aac` | 3 | novel | 3 | model_selection | none | 3/3 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=3/er=3; C.pos=3; D=none |
| 27 | `RXNG_81e16d35d51128d` | 3 | novel | 3 | model_selection | none | 3/3 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=3/er=3; C.pos=3; D=none |
| 28 | `RXNG_cddca61c61d63bc` | 3 | novel | 3 | model_selection | none | 3/3 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=3/er=3; C.pos=3; D=none |
| 29 | `RXNG_d30a28d0eca9e17` | 3 | novel | 3 | model_selection | none | 3/3 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=3/er=3; C.pos=3; D=none |
| 30 | `RXNG_1ad8c653ea1b432` | 4 | novel | 4 | model_selection | none | 4/4 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=4/er=4; C.pos=4; D=none |
| 31 | `RXNG_365fb0be778d863` | 4 | novel | 4 | model_selection | none | 4/4 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=4/er=4; C.pos=4; D=none |
| 32 | `RXNG_4a529de4652697f` | 4 | novel | 4 | model_selection | none | 4/4 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=4/er=4; C.pos=4; D=none |
| 33 | `RXNG_a7f229a532310d0` | 4 | novel | 4 | model_selection | none | 4/4 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=4/er=4; C.pos=4; D=none |
| 34 | `RXNG_baa4bda400eaa40` | 4 | novel | 4 | model_selection | none | 4/4 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=4/er=4; C.pos=4; D=none |
| 35 | `RXNG_a685d0ed38678a3` | 5 | novel | 5 | model_selection | none | 5/5 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=5/er=5; C.pos=5; D=none; pool=0 |
| 36 | `RXNG_fee48640c910421` | 5 | novel | 5 | model_selection | none | 5/5 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=5/er=5; C.pos=5; D=none |
| 37 | `RXNG_e47fbe85b234d1f` | 6 | novel | 6 | model_selection | none | 6/6 | model_selection:explicit_int | **model_ranking** | M.rank; A.mr=6/er=6; C.pos=6; D=none |

## 3. 汇总与关键证据

### 3.1 计数

| 维度 | 值（37 题内） | 标签 |
|---|---:|---|
| 分类 `model_ranking` | 37 | 已证 |
| 分类 `execution_assembly` | 0 | 已证 |
| 分类 `fallback_default` | 0 | 已证 |
| 分类 `unknown` | 0 | 已证 |
| strict 通道：novel / recorded / analog | 33 / 2 / 2 | 已证 |
| rank1 事件通道（37 题内）：analog / recorded / novel | 18 / 11 / 8 | 已证 |
| rank 桶：2–5 / >5 | 36 / 1 | 已证 |
| 显式整数 `model_rank` | 37 | 已证 |
| dedup 折叠行 / 折叠条数 | 2 / 2 | 已证 |
| strict 提案本身被折叠 | 0 | 已证 |
| 折叠导致 strict 事件丢位次 | 0 | 已证 |
| 折叠使 strict 事件前移 | 1 | 已证 |
| `effective_rank` 序 = 提交序 | 36（1 题缺 rank4，strict 位次不受影响） | 已证 |
| 与 P0-A 逐字段对账 | 37/37，0 mismatch | 已证 |

**失败池内的通道描述（不是因果）：** 37 题里模型首位是 analog 18 / recorded 11 / novel 8，
而 strict 正确答案是 novel 33 / recorded 2 / analog 2；其中 17 题「首位 analog → strict novel」、
8 题「首位 recorded → strict novel」。这是 37 个失败题的池内描述，**不是全批通道偏置证明**
（89 个 hit 题不在本表分母内，也没有同题 A/B）。

### 3.2 两个 dedup 行与一个序列缺口

| qid 前缀 | 折叠内容（元数据） | 对 strict 事件的影响 |
|---|---|---|
| `RXNG_16560019e952c8d` | novel 提案 r5 折叠，`rank_inherited=False` | strict 事件是 r2，不受影响；折叠只影响池内序列，未丢位次 |
| `RXNG_330b8f55167f5f3` | novel 提案 r3 折叠进 strict 提案，`rank_inherited=True` | strict 提案自排 r4，继承折叠者 r3 **前移到 r3**；不是丢位次 |
| `RXNG_e97de46f27c0238` | 无 dedup；序列 `[1,2,3,5]` | 缺 rank4 是单条候选执行失败（`execution_failed:...AtomValenceException`）没有提交事件；strict 事件 r2 的提交位次仍是 2，位次来源不受影响 |

> 老师任务书 §一 的 T-F 折叠丢位次 bug 在真实批触发为 **0/298**。本表 2 条 dedup 是
> `s5b-rank-policy-2` 的正常同签名折叠与位次继承，**没有一条把 strict 事件往后挤**；
> 本表**没有**把 37 题套到 T-F bug 上。折叠前后的完整模型 rank 序列见 JSON
> `pre_fold_model_rank_sequence` 与 `effective_rank_sequence`；`rank_shift` 汇总为
> same 36 / up 1 / down 0。

### 3.3 空池子集（5 题）

5 个空池 strict 非首位题：`RXNG_57e0d0320b6da42`、`RXNG_5d62b57e8f2b22f`、
`RXNG_28cc9c753e5ca9b`、`RXNG_a685d0ed38678a3`、`RXNG_ddbcc56d1537bfe`。
它们的 strict 事件全部是 **novel** 通道，模型显式排到 2/2/3/5/2 位；没有 recorded/analog
候选可排，也没有 fallback 顶替。分类仍为 `model_ranking`。

### 3.4 与 P0-A 结论的一致性

| 项 | P0-A | 本表 | 一致 |
|---|---:|---:|---|
| strict 非首位题数 | 37 | 37 | 是 |
| `rank_basis=model_selection` | 37 | 37 | 是 |
| `model_rank` 显式整数 | 37 | 37 | 是 |
| fallback / 默认 / unknown | 0 / 0 / 0 | 0 / 0 / 0 | 是 |
| rank 继承题 | 1 | 1 | 是 |
| dedup 条数 / 涉及题 | 2 / 2 | 2 / 2 | 是 |
| `effective_rank` 序 = 提交序 | 36 | 36 | 是 |

**边界不变：** P0-A 的「37/37 显式模型位次」不等于「模型显式自排就可捞回」；
本表同样只证明成因在模型侧排序，不证明换 prompt 后能回收多少。回收率 **unknown**。

### 3.5 全批 strict 背景（辅助，不改变 37 行分类）

全 126 个 `matched_strict` 题的 strict 事件通道：novel 64 / recorded 41 / analog 21。
按是否首位拆开（同一批、同一 payload 元数据，只作描述，不作因果）：

| strict 通道 | 总 strict 题 | 其中首位 | 其中非首位 | 非首位占该通道 |
|---|---:|---:|---:|---:|
| novel | 64 | 31 | 33 | 51.6% |
| recorded | 41 | 39 | 2 | 4.9% |
| analog | 21 | 19 | 2 | 9.5% |

**读法：** 模型不是不会排 recorded/analog——这两个通道的 strict 正确事件绝大多数被排到首位；
**novel 正确事件有一半落在非首位**。这是严格匹配事件内的描述性关联，不是通道质量结论，
也不是“novel 更难”的因果证明；但它解释了为什么 T-I 变量清单把“通道中性 / novel 不降权”
排在较高优先级。126 = 89 首位 + 37 非首位（37 已含在内），不是两组独立样本。
证据文件：`strict126_channel_context.json`。

## 4. 老师分支判定与下一步

- **本周期不实施执行/装配层修复**：`execution_assembly=0`，没有提交序/折叠丢位次可修。
  不启用「位次继承或显式 rank 优先的传递」修复，不做封闭 run 离线重放对照（没有可修对象）。
- **不立项 chain15**：老师任务书 §四 的 chain15 预注册草稿只在「执行层修复已实施」分支产出；
  本批不走该分支。
- **T-I 提示词变量清单**：`docs/T_I_PROMPT_RANK_VARIABLES_2026-10-21.md`
  （3–5 个模型侧排序候选；只作下一轮候选，**不塞进当前单变量 T-I 批**）。
- **T-F 折叠 bug**：维持「登记捎带」状态，本表不把它写成 37 题成因，也不推动单独补修。

## 5. 证据与复现

- 分类表：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/T_H_TEACHER_LEVER1_RANK_TABLE_2026-10-21.md`
- 机读证据：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/t_h_lever1_rank_2026-10-21/`
  - `extract_lever1_rank.py`：只读取数脚本（不选 SMILES/结构正文）
  - `lever1_rank.json`：37 行全量字段 + 汇总 + P0-A 对账 + 源文件 SHA256
  - `strict126_channel_context.py` / `strict126_channel_context.json`：全 126 strict 的通道背景（辅助）
  - `SHA256SUMS`：脚本与 JSON 哈希
- 只读源：
  - `reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json`
  - `/tmp/t_h_p0_r2/runs/<run_id>/native_export/*/payload.json`（从封存 HPC run 根只读下载的
    本地镜像；易失，逐文件 SHA256 已写入 JSON）
  - 权威路径（只读）：`~/ppv1_hpc/runs/t_h_s5b_298_20261020r2`
- 复现命令：

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
python3 -B docs/review_evidence/t_h_lever1_rank_2026-10-21/extract_lever1_rank.py \
  --payload-root /tmp/t_h_p0_r2/runs \
  --out docs/review_evidence/t_h_lever1_rank_2026-10-21/lever1_rank.json
```

## 6. 仍缺字段 / unknown

| 项 | 状态 | 影响 |
|---|---|---|
| 换 prompt/换 ranker 后的实际回收率 | **unknown** | 无同题 A/B；本表分类不是收益承诺 |
| 37 题「模型为什么把正确答案排第二」的语义理由 | **unknown** | payload 只有 `rank_hypotheses` 位次，没有逐位理由字段；需要下一轮提示词变量才可观测 |
| T-F 折叠 bug 在本批的影响 | **已证 0/298** | 本表不套用；该 bug 维持登记捎带 |
| 5 个空池题的 recorded/analog 候选 | **无候选（池=0）** | 只能靠 novel 通道；模型已显式排序，非装配丢失 |