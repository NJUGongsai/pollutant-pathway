# 任务书 T1a：S5b 池层逐候选谱系诊断（2026-10-12）

> 主会话起草，交实施子代理照书执行。零上下文可接。
> 背景决策链：GPT chain11 丢分分析（v44/docs/SYSTEM_PROBLEMS_AND_298_LOSS_ANALYSIS_2026-10-12.md §6.1 P0-2）→ CC 拍板"漏斗账两步走+谱系先行"→ 三路只读侦察定稿本设计。

## 0. 一句话目标

给 `s5b_builder.py` 的池构建过程加**逐候选诊断行**：每个候选（无论编译成功、编译失败、被合并去重、被池宽截断）都在 `batch_manifest.json` 的 `pool_diagnostics.candidates` 里留一行明细，终结"死在建池阶段的候选只有聚合计数、无逐条记录"的现状。**不改任何管线行为。**

## 1. 为什么是这个刀口（侦察定稿，勿扩大）

只读侦察结论（v43 主仓，分支 v4.3）：

- 候选全链 = `build(池构建) → retrieve → decide(prepare+去重+排序+调度) → expand(执行→审计→准入→提交) → score`。
- **decide 之后的所有丢失点已有逐条记录**：去重折叠有 `dedup_rejections`（runflow.py:992-1008）、调度落选有 deferred 行（queue.py:276-290，导出为 `deferred_entries`）、执行/准入有 `expansion_outcome`/`production_report` artifact。这些**不动**。
- **唯一黑箱在池构建**：编译失败只有 `compile_failure_histogram` 聚合计数（s5b_builder.py:687-688；recorded 侧 failure_hist 在 recorded_source.py:1217-1251）、池宽截断 `merged[:max_pool]`（:690）无逐项留痕。
- 因此本任务**只改 s5b_builder.py + 版本常量 + 新测试**。runflow.py / production.py / queue.py / store.py / 判分侧（s5b_scoring.py / evaluation.py）**零改动**。这条边界是设计定稿，越界即返工。

## 2. 现状表（实施前先读这些位置）

| 位置 | 现状 |
|---|---|
| `src/pathway_v43/pollutant/s5b_builder.py:434-693` | `default_pool_provider.provider`：三通道逐候选构建（EAWAG recorded `find_recorded_exact` / corpus 直通 `find_corpus_recorded_exact` / 类比模板 `AnalogSourceResolver` + `compile_donor_template`），编译成功才进池 |
| `s5b_builder.py:630-647` | 同净反应签名去重：被并 spec 的 key 追加进幸存者 `compile.merged_source_keys`（已有留痕） |
| `s5b_builder.py:690` | 池宽截断 `merged[:max_pool]`（S5B_POOL_MAX=8 于 :420 附近） |
| `s5b_builder.py:648-689` | `diagnostics` 聚合直方图（n_unique_net_reactions / n_pool_returned / compile_failure_histogram 等） |
| `s5b_builder.py:763-776` | `build_question_batch` 把 `pool_diagnostics` 写进 `batch_manifest.json` entries |
| `s5b_builder.py:418` 附近 | `S5B_POOL_POLICY_VERSION` 当前值（实施时查实际值） |

## 3. 设计定稿

### 3.1 candidates 行 schema（每候选一行）

```json
{"channel": "recorded|corpus|analog",
 "record_key": "<record_id 或 tpl key>",
 "outcome": "compiled|compile_rejected|merged_into|pool_truncated",
 "reason": "<compile_rejected 时的拒因短码；其他 outcome 为 null>",
 "merged_into": "<被并入的幸存 spec key；仅 merged_into 时非 null>",
 "pool_rank": <截断前排序位，int；compiled/pool_truncated 时有，其他 null>,
 "signature_head": "<净反应签名前几个 token，仅 compiled 时非 null，诊断显示用>"}
```

- 三通道的候选产出点各插一处记录；spec_key 若在产出时尚未生成，用 record_key 定位即可（幸存 spec 的 key 规则 `tpl-…`/`rec-…` 见 s5b_compiler.py:1060、builder 覆写 :599）。
- **manifest 规模控制**：先全量保留实测单题最大行数与 manifest 增量；若批 manifest 增长超过现状 5 倍，停下来在回传里报告实测数字与建议（截断规则待主会话裁定，不自行截断）。

### 3.2 版本承载

- `S5B_POOL_POLICY_VERSION` 语义化升版（当前值 +1，如 `...-1` → `...-2`，以实际格式为准）：池诊断从聚合升为逐候选是池策略可观测性变化。
- 不动 `EDIT_PROTOCOL_VERSION` / `ATOMTOOL_VERSION` / `CORPUS_RETRIEVAL_VERSION`（本任务不碰它们的语义面）。

### 3.3 明确不做（边界，越界即返工）

1. 不改 runflow/production/queue/store/判分侧任何代码；
2. 不改 `run_inputs/<qid>.json` 的任何字节（plan.pools 冻结内容不变）；
3. 不改既有 `pool_diagnostics` 聚合字段（candidates 是追加字段，向后兼容）；
4. 不改池构建的控制流（排序、去重判据、截断位置、失败补位逻辑原样）；
5. 已知限制如实记录不修：池 spec 在 decide 层 prepare 失败会导致整个 decide run 级失败（runflow.py:870 无逐条容错），该丢失点只有 case 级 failure_kind 可见——**本任务不改这个行为**，交付书里作为已知限制披露。

## 4. 红线（违反任何一条即停止并报告）

1. 判分侧零污染：`s5b_scoring.py` / `evaluation.py` 零改动；manifest 加字段经侦察确认判分为白名单式消费（s5b_orchestrator.py:315-351 先例：未知字段不拒），仍需定向验证判分对新 manifest 正常跑通。
2. 金标/题面零触碰：不读 `reference_graphs/` 内容、不读金标 tsv。
3. 封存 run 只读：所有探针在新 tmp/新批次根做。
4. export_digest 零影响：不往 facts 表/artifact payload 塞任何字段（本设计天然满足，复核即可）。
5. 不 push、不调用外部模型、零网络。

## 5. 分步命令

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
# 1. 读现状
sed -n '410,700p' src/pathway_v43/pollutant/s5b_builder.py   # provider 全段
sed -n '700,790p' src/pathway_v43/pollutant/s5b_builder.py   # manifest 写入
# 2. 实施改动（s5b_builder.py + 新测试 tests/test_ppv1_s5b_pool_lineage.py）
# 3. 定向测试
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider tests/test_ppv1_s5b_pool_lineage.py -q
# 4. 相关既有测试零回退
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -p no:cacheprovider tests/test_ppv1_s5b_hit50_w23456.py tests/test_ppv1_s5b_runtime.py tests/test_score_report.py -q
# 5. 全量回归（not slow，基线 2061 passed/0 failed/16 deselected 附近）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider tests/ -q -m "not slow"
# 6. 字节等价探针：同输入 build 前后 run_inputs/*.json 逐字节一致；manifest 除 pool_diagnostics 新字段与版本号外等价（新 tmp 批次根，勿写封存目录）
# 7. 父 HEAD 红绿对照：隔离 worktree 检出父 HEAD，新测试应红（新字段不存在）、既有测试不因本改动翻转
```

（注：python 解释器路径以仓内实际为准——`.venv/bin/python` 不存在时查 `docs/` 近期交付书的跑法先例，或用 conda env depending43。）

## 6. 测试矩阵（新文件 tests/test_ppv1_s5b_pool_lineage.py）

| 类 | 用例 | 断言要点 |
|---|---|---|
| 正控 | 编译成功候选 | candidates 行 outcome=compiled、channel/record_key/pool_rank 在位 |
| 正控 | 编译失败候选 | outcome=compile_rejected + reason 短码，与聚合计数闭合（histogram 计数 = 同 reason 行数） |
| 正控 | 被合并候选 | outcome=merged_into + 指向幸存 key，与 merged_source_keys 闭合 |
| 正控 | 池宽截断候选 | outcome=pool_truncated + pool_rank>max_pool，计数 = n_unique_net_reactions − n_pool_returned |
| 不变量 | manifest 兼容 | 判分/worker 对新 manifest 正常消费（白名单不拒） |
| 不变量 | run_inputs 字节等价 | 同输入 build 两次 plan.pools 冻结内容一致 |
| 不变量 | 版本升版 | S5B_POOL_POLICY_VERSION 值 +1 |
| 负控 | 聚合字段不变 | 既有 pool_diagnostics 聚合键与语义零变化 |

## 7. 排障表

| 症状 | 处置 |
|---|---|
| conftest 依赖 `../dependingv3`/`../dependingv4` 缺席 | 自动 skip 属预期；全量数字相应减少，如实回传实际数字 |
| 字节等价探针失败 | 停下报告差异字段，不得用"顺带修好"的方式改 run_inputs 生成逻辑 |
| manifest 规模超标（>5x） | 不自行截断，回传实测数字等裁定 |
| 既有测试翻转 | 逐 nodeid 分类回传（行为红/字面量红），不得静默改断言凑绿 |

## 8. 回传义务（最终消息必须含）

1. 改动文件清单 + 每文件改动性质摘要（不贴全 diff，讲清楚改了什么）；
2. 定向/相关/全量三层测试的实际数字（passed/failed/skipped/deselected）；
3. 字节等价探针结果（run_inputs 一致性 + manifest 差异面清单）；
4. 父 HEAD 红绿对照结果（新测试红几件、为什么）；
5. 单题 candidates 行数实测分布（min/median/max）与 manifest 增量比例；
6. 交付书草稿落 `docs/POLLUTANT_PATHWAY_S5B_POOL_LINEAGE_T1A_DELIVERY_2026-10-12.md`（含 §3.5 已知限制）；
7. 所有证据（探针脚本、前后 manifest 样本）留 `/tmp/s5b_t1a_lineage/`，路径写进交付书。
