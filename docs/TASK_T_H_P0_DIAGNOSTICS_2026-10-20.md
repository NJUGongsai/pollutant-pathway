# 任务书 — T-H hit@1 优化 P0：诊断契约与决议取数（2026-10-20）

> **题域：298 = RHEA 通用酶学 / 已见题（post-hoc）。** 全部读数只在该题域成立，
> 不外推到 dev、新题或其它题域。
>
> **本任务书对应** `docs/T_H_HIT1_OPTIMIZATION_PLAN_2026-10-20.md`（Codex 综合版核定稿）的
> **P0 诊断**。旧稿曾称“P1”，按综合版重定名为 **P0**。
> **执行者**：子代理（只读诊断）；**拍板者**：CC/老师。
> **性质：零模型调用、零判分改动、零付费、零代码改动。**
> 注意：零模型 ≠ 零成本，仍需计算、存储与工程时间。
>
> 规则来源（必读）：`docs/T_H_HIT1_OPTIMIZATION_CODEX_SYNTHESIS_2026-10-20.md`（SHA256
> `a92f79e8…b9dec0c0`）；本任务书已按它的**事实更正**改写，不沿用前稿的错读法。

## 0. 一句话

**先补齐“评分到底在哪一步失配”和“答案是否由所提编辑支持”两类证据，并为后续 P1/P2/P3
提供可复算的取数。** 本阶段不改候选、不改提交顺序、不改原判分。

## 1. 现状与正确读法（执行者先核，不要重算）

| 项 | 正确读法 | 来源 |
|---|---|---|
| 基线 | T-H r2，criteria-v2 headline **89/298 = 29.87%**；hit@3 118、hit@5 125；strict(U) 126 | `T_H_RESULT_2026-10-20.md` |
| 目标 | **至少 35% = 105 题（35.23%）**；**至少 40% = 120 题（40.27%）**；历史离散目标 104/119（34.90%/39.93%），保留原任务身份但不得写成 35%/40% | Codex 综合版 §2 |
| 73 近失组 | 排序 32（31 题 rank2–5 + 1 题 rank>5）+ partial 41；靠它进线需转化 **21.9% / 42.5%** | 归因报告/综合版 |
| 37 strict 非首位 | 固定事件集的**理想排序毛空间**，不是净收益；全局重排会同时损失旧命中 | 综合版 §2 |
| 52 老口径差集 | 宽松产物 any-of 与严格反应的差集；**失配定位线索，不是 52 个正确反应被误判** | 综合版 §2 |
| 47 无候选 | 旧口径也无匹配；固定事件集仅重排不能恢复，应查生成与执行 | 综合版 §2 |
| 60 空池 | 20 题仍 hit@1、40 题未中；空池 ≠ 无答案 | 归因报告 |
| 21 身份门 | 只确认 1 个旧 hit 在该影响面退化；跨批非单变量，**不称因果** | 综合版事实更正 |
| 23 归一配对 | 47 个适用配对中 13 互变 + 10 质子化获某轴归因；**不证明净增 23 题** | 综合版 §6 |
| 权限 | 封存批根 555/444 只读；runs 根可读 | 阶段 3b 报告 |

**Stage 0 已完成**：`docs/review_evidence/t_h_stage0_triage_2026-10-20/stage0_brief.md`
（120 题已核对：32/41/47 分组；32 个 strict matched 事件无 fallback；覆盖组模型自评
不能代替评分缺口）。本任务书**不重做 Stage 0**，只补它未闭合的执行对账与评分缺口。

## 2. 输入与权限

### 2.1 HPC（只读）

```bash
KEY=/Volumes/CC/Enzyme_Agent/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt
SSH="ssh -i $KEY -p 65091 -o BatchMode=yes -o ConnectTimeout=15 aclhl3hbth@wuzh02.hpccube.com"
```

| 路径 | 权限 | 用途 |
|---|---|---|
| `~/ppv1_hpc/batch/t_h_s5b_298_20261020r2/` | **555/444 只读** | manifest、run_inputs、p2_face_measure、criteria_v3_disclosure、batch_report、monitoring |
| `~/ppv1_hpc/runs/t_h_s5b_298_20261020r2/` | 可读 | 逐 run `native_result.json`、`s5b_real_calls.jsonl` 元数据 |
| `~/EnzymeAgent/v43cTH/` | 可读 | 代码（只读） |
| `~/ppv1_hpc/batch/t_h_s5b_298_20261020/` | 只读 | 旧事故批（对比） |
| `~/ppv1_hpc/batch/chain13_s5b_20261014/`、`chain14a/b_s5b_20261015/` | 只读 | 历史对比 |

### 2.2 本地

- `reports/ppv1_s5b/t_h_2026-10-20/r2/`（27 件，SHA256SUMS 已校验）
- `reports/ppv1_s5b/chain13_glm/`、`chain14_a/`、`chain14_b/`（metrics + .v1）
- `docs/T_H_R2_HIT1_LOSS_ATTRIBUTION_2026-10-20.md`
- `docs/T_H_HIT1_OPTIMIZATION_PLAN_2026-10-20.md`（修订稿）
- `docs/T_H_HIT1_OPTIMIZATION_CODEX_SYNTHESIS_2026-10-20.md`
- `docs/review_evidence/t_h_stage0_triage_2026-10-20/`

### 2.3 严禁

金标、`reference_graphs/`、`questions.jsonl`、`llm.env`、私钥内容、逐题 case 化学正文、
候选 SMILES 清单。**允许**读取的字段仅限 §3 各任务列出的元数据/聚合字段。
不写封存批根；所有产物写本地 `docs/review_evidence/t_h_p0_2026-10-20/`。

## 3. 任务（P0-A..P0-D + 决议取数）

> 统一要求：每项一个 JSON + 一个 markdown 摘要；计数必须能对上前述锚点；
> 对不上先停下报告，不自行改口径；所有“上限”注明是毛空间/口径上限，不是收益承诺。

### P0-A 候选谱系（支撑 D-2 排序归因）

**问题**：非首位 strict 是“模型显式排序”“缺席/null 默认补齐”还是“fallback 池序”？
（注意：**不能**再说“32/32 都是模型显式自排”；只能确认解析规范化后的 `model_selection`；
rank 缺席/null 会按 proposals 顺序补齐 —— `model_protocol.py:223`、`runflow.py:1089`。）

**取数**：
1. 从 `metrics.json per_qid` 取 `matched_strict` 且 `rank>1` 的 37 题（含空池 5 题）。
2. 从 runs 元数据取：`rank_basis`、`model_rank`、`effective_rank`、`dedup_rejections`、
   `folded_model_rank`、原始 rank 是否存在（缺失/null/显式空分开记）。
3. 输出 `p0a_candidate_lineage.json`：
   `{total:37, explicit_model_rank:n, null_default_order:n, fallback:n, unknown:n, empty_pool_subset:5, by_rank_bucket:{2_5:36, gt5:1}}`。
4. 摘要：模型序 vs 默认补齐 vs fallback 三栏；未知项写缺字段。

**验收**：总数 37；与 Stage 0 的 32 个非空池 matched 事件对账，差异逐条解释。

### P0-B 声明产物 vs 执行产物对账（支撑 D-6 效度）

**问题**：事件产物取自模型声明的 `product_smiles`，是否与它自己 edits 的执行结果一致？
**不能简单比较两个 SMILES 字符串**；按同源严格结构身份与组分多重集对账。

**取数**：
1. 读事件元数据（只读）：声明为实际生成的产物组分、执行碎片、execution expectation、
   copy 来源、主产物归属；按 origin 与首位/后位汇总。
2. 输出 `p0b_declared_vs_executed.json`：
   `{n_events, applicable:n, consistent:n, inconsistent:n, unknown:n, not_applicable:n, inconsistent_and_hit:n}`。
3. 合成正负控（本地）：多碎片、合法 copy、立体差、明确矛盾、解析失败；**原提交与判分不变**。
4. 摘要：只报 qid 前缀与计数；不输出 SMILES；unknown 不洗成通过。

**验收**：事件总数与已披露 1586 条对账；四态（consistent/inconsistent/unknown/not_applicable）互斥。

### P0-C 评分缺口诊断（支撑 D-3 partial）

**问题**：53 partial 与 119 unmatched 分别缺什么？注意：覆盖用两侧 `state_ref` **集合**；
系数只披露；scope 不一致另入 `structure_only`（`evaluation.py:2343`、`:2434`、`:2482`）。

**取数**：
1. 用**冻结 scorer** 的诊断输出（不改判分）：必要节点 gap、两侧 extra/missing/mixed、
   豁免原因、scope、覆盖状态。
2. 输出 `p0c_scoring_gaps.json`：
   `{partial:53, unmatched:119, partial_classes:{extra:n, missing:n, mixed:n, scope:n, unknown:n}, by_pool:{nonempty,empty}, by_remap:{...}}`。
3. 摘要：可行动子集与不可行动子集分开；**不拿模型自报 partial 推缺口**。

**验收**：partial=53、unmatched=119 可回对；分类互斥且总数闭合；unknown 写明缺什么。

### P0-D 供给漏斗（支撑 D-7 供给投入）

**问题**：无已调度 recorded 候选的题卡在哪一层？`no_alignment` 同码多义能否拆开？
**注意锚点**：T-H r2 同逻辑实测 **193**；207 是 chain14 A/B 跨批口径，**不是 T-H 不变量**。

**取数**：
1. 检索命中/超阈/截断；F3/F5 预门跳过；真实编译失败；remap 加/减/未尝试/失败；
   执行失败；去重与预算。
2. 保留旧 reason 兼容字段并增加细分维度；`deferred` 按 reason 直方图（Stage 0/mimo 已有部分）。
3. 输出 `p0d_supply_funnel.json`：
   `{no_recorded:193, reasons:{corpus,retrieval,compile,unknown}, no_alignment_split:{f3,f5,true,unknown}, remap:{added,removed,not_attempted,failed}, deferred_by_reason:{...}}`。
4. 摘要：最大闸门；区分 spec/题/事件分母。

**验收**：193 分母可对（若参考 chain14 的 207，须注明跨批差异）；`deferred_by_reason` 总和 = 2366 或说明差在哪；选中候选身份/顺序不变。

### 决议取数 T1/T4/T5（只取数，不拍板）

| 任务 | 对应决议 | 取数 | 必须写明的限制 |
|---|---|---|---|
| **T1** | D-1 v3 归一研究 | 47 个适用配对中 13 互变 + 10 质子化；映射到 qid、主口径 rank、事件位次；按完整计分链（去重题数→必要节点→边 exact→首位）给**题级**潜在变化 | **不能**写“≤23 题收益”；边覆盖、首位、未披露配对未闭合；v3 是判据研究，不是提分实验 |
| **T4** | D-4 价态异常分诊 | 12 题 `AtomValenceException` 的逐题事件、是否仍 hit、其它事件数 | **不能**写“隐式氢必撞墙/缺脱氢能力”；代码让 sanitize 重算隐式氢（`atom_tool.py:413/486/529`）；12 题不足以定位缺失能力 |
| **T5** | D-5 立体能力缺口 | T-H 纯立体差题数（有字段就取，没有就 unknown）；区分“声明产物带立体”与“edits 设置立体” | **不能**写“novel 不可能有立体/21 题是硬天花板”；声明 `product_smiles` 可带立体（`production.py:390/413`）；21 是 chain12 口径 |

### 决议包（汇总）

合成 `docs/T_H_P0_DECISION_PACK_2026-10-20.md`：每项写证据摘要、可动子集、
**若做下一步的单变量实验设计要点**、**若不做的反证**、未知项。**不替 CC/老师拍板**；
本阶段不要求 CC 预先拍七个技术选择。

## 4. P0 完成门（回放零漂移；本轮未执行）

在独立复制/隔离环境，用冻结历史输入、已保存模型响应等载荷、冻结 scorer 做诊断开关回放：
- 排除新增诊断字段后，**候选成员、事件、提交位次、判分语义零漂移**；
- 复现 **hit@1=89、strict=126、partial=53、unmatched=119**；
- 此门**不重新调用模型**；新模型运行按配对统计验收，不要求逐事件相等。

未过此门 ⇒ P1/P2 不得启动。

## 5. 红线

1. 零模型调用、零重判、零付费；不改 `src/`、`tests/`、`scripts/`。
2. 不写封存批根（只读 555/444）；不覆盖旧批；不 push。
3. 不读金标/`reference_graphs`/`questions.jsonl`/`llm.env`/私钥；不输出候选 SMILES。
4. 不把毛空间当净收益、不把关联当因果、不把模型自报状态当评分事实。
5. 数据缺口写 unknown，不估算、不编造。
6. 所有产物写 `docs/review_evidence/t_h_p0_2026-10-20/`，带 `SHA256SUMS`。

## 6. 分步命令（骨架）

```bash
cd /Volumes/CC/Enzyme_Agent/dependingv43
mkdir -p docs/review_evidence/t_h_p0_2026-10-20
export PYTHONDONTWRITEBYTECODE=1

KEY=/Volumes/CC/Enzyme_Agent/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt
ssh -i "$KEY" -p 65091 -o BatchMode=yes aclhl3hbth@wuzh02.hpccube.com \
  'B=~/ppv1_hpc/batch/t_h_s5b_298_20261020r2; stat -c "%a %n" $B $B/metrics.json; ls $B/th_sealed.json'

# 建议顺序：P0-A → P0-C → P0-B → P0-D → T1 → T4 → T5
# 每步对账：37 / 53+119 / 1586 / 193+2366（T-H r2；chain14 为 207）/ 47+23 / 12 / 实测或 unknown
```

## 7. 排障表

| 症状 | 处置 |
|---|---|
| SSH locale/perl 警告 | 忽略；只看 RC |
| 封存批根读不到 | 检查 555/444；只读应可读；**不要 chmod** |
| `rank` 字段缺失/null | 记 null/default，不伪造成显式 rank |
| 事件数对不上 1586 | 先查 2 题 NC-9 的 0 事件口径 |
| 复算脚本想写批根 | 立刻停；改写证据目录 |
| 发现与四份报告冲突 | 以机读数据为准，记录冲突并在决议包披露 |
| 想用配对数当收益 | 停；必须走完整计分链到题级 |

## 8. 回传义务

每项完成回报：做了什么 / 读数 / 与锚点对账 / 下一步。
最终 ≤25 行：P0-A..P0-D 核心计数；T1/T4/T5 限制与 unknown；回放门是否具备执行条件；
决议包路径；与四份报告的冲突。

## 9. 验收（主窗口）

- 4 个 P0 JSON + 3 个决议取数 + 决议包 + 证据目录（SHA256SUMS）；
- 锚点对上或差异有解释（37 / 53+119 / 1586 / 193+2366（T-H r2；chain14 为 207）/ 47+23 / 12）；
- 零代码改动、零模型调用、封存批根零写入；
- unknown 清单完整，无编造；
- 决议包不替 CC/老师拍板。

## 10. 不在本任务书范围

- **P0b**：把诊断字段写进 `native_result`/`native_export`/`s5b_builder`/`s5b_compiler`/`production`
  （输出 schema 与版本升位），另立任务书 + 审核。
- **P1-A** NC-9 隔离与 **P1-B** 对账硬门：P0 出数后另立。
- **P2** 证据卡 v2 实施：按冻结设计，排在 T-I 之后。
- **P3** 供给工程：P0-D 分诊后另立。
- v3 归一研究：另立测量议题。

## 11. 参考

- 优化方案（修订稿）：`docs/T_H_HIT1_OPTIMIZATION_PLAN_2026-10-20.md` / `_PLAIN.md`
- Codex 综合版：`docs/T_H_HIT1_OPTIMIZATION_CODEX_SYNTHESIS_2026-10-20.md`
- 三份原始意见：`V43_HIT1_OPTIMIZATION_RECOMMENDATIONS_2026-10-20.md`、
  `T_H_HIT1_RECOVERY_ARCH_OPTIONS_2026-10-20.md`、`T_H_ARCH_OPT_PROPOSALS_2026-10-20.md`
- 归因报告：`docs/T_H_R2_HIT1_LOSS_ATTRIBUTION_2026-10-20.md`
- Stage 0：`docs/review_evidence/t_h_stage0_triage_2026-10-20/stage0_brief.md`