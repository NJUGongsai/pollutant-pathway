# 任务书 — L1 扩罩编译重放探针（锁1/锁2 重立项第一步，2026-10-15）

> 派单：CC。执行者：分析/代码执行代理（纯离线分析+只读 import，零 src 改动）。
> 上游决策链（自包含背景，执行者不必另读，但开工前扫一遍上游文件头部勘误注）：
> - 锁3 已关闭（L3 Phase A 证伪：普通门无可声明面，0 行/0 题——
>   `docs/L3_IMPL_DESIGN_NOTE_2026-10-15.md`）；
> - CC 拍板（冻结）：**转向锁1（前置门资格）/锁2（编译能力）重新立项**；
> - GPT 分档设计（`docs/L1_TIERING_DESIGN_RESPONSE_GPT_2026-10-15.md`）§2：
>   任何新档先在**冻结的当前编译器**上做零模型重放——「资格→编译→池变化→
>   声明可消费」四道门，零新增编译存活或零有效池变化就不装；
> - 主会话互证（`reports/ppv1_s5b/chain13_glm/analysis/l1_tier_interlock_2026-10-15.md`）：
>   W 档上界面 E_cap=42（预算 0，no-go）、P 档 E_cap=0 但 9 题面卡编译存活、
>   G=4 no-go——**本探针就是把「卡编译存活」从代理面变成实测数**。
> 题域标签：**298=RHEA 通用酶学/已见题**；探针≠预注册≠成绩；本探针不决定装载，
> 只产出重立项拍板材料。

## 一、一句话目标

把「若给 L1 分档资格，被拒候选在**当前冻结编译器**上能不能编过、能不能改变
最终池、声明链能不能被 v2 消费」这三件事，用**离线重放**（import 仓内编译函数
只读调用）实测出数——同时给锁2（对齐/枚举容量）出底数。

## 二、红线（违反任一=停）

1. **零 src/tests 改动**：探针脚本 import 仓内函数只读调用；`git status` 收尾
   必须零 tracked diff。运行加 `PYTHONDONTWRITEBYTECODE=1`（不写 .pyc）。
2. 零模型、零网络（不 pip install / 不 curl）、零判分重算（strict 题集只从
   metrics 读）。
3. 零金标零题面：题目输入只用 manifest `substrate_smiles` 批准字段。
4. 产物只落 gitignored `reports/ppv1_s5b/l1_replay_2026-10-15/`；不 commit 不 push。
5. 拼不出=诚实 unknown；存活率不许从拒因外推，只报重放实测。
6. **Harness 验证失败=停**（§四 Stage 0 复现不了 chain13 已知救援结果，后续
   数字一律不可信，停下报告，不得硬跑）。
7. 对外数字一律带题域标签 298。

## 三、数据面（全部本地已验证存在）

| 件 | 位置 |
|---|---|
| 逐候选谱系（5540 行） | `reports/ppv1_s5b/chain13_glm/synced/batch_manifest.json` → entries[].pool_diagnostics.candidates |
| 族判定/resolve/自检模板 | `reports/ppv1_s5b/chain13_glm/analysis/c_redesign_base_tables.py`（**必复用 import**，禁复制改写） |
| R0 探针行级数据+严格快照口径 | `reports/ppv1_s5b/chain13_glm/analysis/r0_probe_p1p3_data.json`（rows_all_5540 含 primary_family） |
| 判分状态 | 同目录 `synced/metrics.json(.v1)` + chain12 `…/chain12_s5b_298_v4b_20261012/synced/metrics.json` |
| 语料三源 | `assets/v3_reactions/corpus_env/corpus_v1.jsonl`、`assets/analog/corpus_templates_v1.jsonl`、`assets/v3_reactions/library/library_full.jsonl` |
| **冻结编译器（只读 import）** | `src/pathway_v43/pollutant/s5b_builder.py`（analog 前置门/救援资格门/`analog_cosub_supply`/`compile_donor_template`/池策略函数）、`src/pathway_v43/pollutant/recorded_source.py`、`src/pathway_v43/domain/identity.py`（cn_identity） |
| 解释器 | `/Users/cc/miniconda3/envs/depending43/bin/python`（带 rdkit） |
| 仓根 | `/Volumes/CC/Enzyme_Agent/dependingv43`（HEAD `461844e`，分支 v4.3——**收尾时 HEAD 必须仍是它**） |

## 四、探针设计（五段，按序；GPT 四道门映射见括号）

### Stage 0 — Harness 验证（最强锚，不过此关全停）

用当前代码的**既有救援资格门**重导出「C-eligible ∧ 被拒」的 analog 候选
（读码定位资格判定函数，直接调用，不改），对它们跑救援编译重放。**预期必须
逐题复现 chain13 实测救援结果**：35 题获救、rescued 件数分布 {30 题×1、
4 题×2、1 题×3}（manifest `analog_cosub_supply_rescued` 逐题核对）；sim13
13 题内 17 次尝试存活 0。**复现=重放机忠实；任何偏差逐题列出并停**。

### Stage 1 — 分档资格面（门一：资格）

按 GPT 谓词对全批 analog 通道 `compile_rejected ∧ 族∈FAM` 候选（上界 962 件：
W/H₂O 396、P/Pi 30、PP/PPi 0、G/糖基 79、D/机制 457）落地**代码级精确判据**：
`new_eligible = analog ∧ front_gate_rejected ∧ !current_C_eligible ∧
family_complete（记录反应物侧完整多重集，禁剪袋）∧ declaration_precheck ∧
unambiguous_existing_main_component（最大 Tanimoto 主组分唯一）∧ quota（每题
每档 1 件，按既有遍历序取首件，失败不递补）`。逐档出：件数/题数/被配额挡
件数 + E_cap/E_cup/E_now（∩稳 strict 107 / ∩宽 137 / ∩chain13 v1∪v2 strict，
qid 清单落 JSON）。

### Stage 2 — 编译重放（门二：编译；锁2 容量底数）

对 Stage 1 各档 X_new 逐件调救援编译机（同 Stage 0 用过的函数路径），逐件记录：
`compile_status` + `compile_reject_reason`（对齐失败/枚举截断/键合贡献/
无结构对应等，映射到 GPT 字段名 `alignment_status`/`enumeration_truncation_reason`/
`bond_contribution_status`/`structure_mapping_status`）。**全量重放**（D 档
虽不获资格也重放——锁2 容量测量，D 的拒因分布就是 L2 工程的工单）。产出
分档×族×拒因交叉表（件数/题数，题级去重）。

### Stage 3 — 池变化（门三：近似+如实披露）

对 Stage 2 存活件：用 src 池策略的签名函数算净反应签名，做 (a) 存活件之间
去重；(b) 与既有池成员的碰撞检查——**既有池成员签名只有 `signature_head`
前缀（行级数据不含全签名）**，碰撞检查用前缀近似并如实标注「近似」；
(c) 逐题报 `pool_size`（manifest）+ 存活件加入后的 `pool_size+n` 是否超
max_pool（截断风险）。**全签名精确去重需重建整池=超出本探针范围，如实
登记为重立项后的补测项，不硬算**。

### Stage 4 — 声明可消费（门四：凭证）

对 Stage 2 存活件：调救援路径的声明面 attach（同源函数），核验
`record_equation`+`record_equation_ref` 成对在场、逐条目 smiles 经 cn_identity
可解析、方向与记录一致（对应 GPT 字段 `v2_declaration_consumable`）。坏形状
=如实记 fail-closed，不修。

### 收尾 — provenance

JSON meta 落：git HEAD、关键 src 文件 sha256（s5b_builder/recorded_source/
identity）、语料三源 sha256、`PYTHONDONTWRITEBYTECODE`、运行时长、Stage 0
复现明细。摘要 md 大白话+表格，每表带 298 标签与「探针≠预注册≠成绩」。

## 五、自检锚点（对不上=停并报告，不得硬凑）

| # | 锚 | 来源 |
|---|---|---|
| 1 | Stage 0 复现 rescued 分布 {0:263, 1:30, 2:4, 3:1}、35 题、sim13 17 尝试 0 存活 | manifest 实测 |
| 2 | analog 族合格 compile_rejected 上界 962 件（W396/P30/PP0/G79/D457） | 主会话互证 |
| 3 | bag×donor 交叉表：69 条 analog compiled 行 {1:1→43, 2:2→22, 3:3→4}，bag=1∧donor≥2=0 | L3 设计书 |
| 4 | strict 快照 114/130/稳107/宽137；cexposed=35 | metrics 复算 |
| 5 | rhea:14570/56586 donor 单组分（水在产物侧）——族扫描口径缺陷背景 | corpus_v1 直读 |
| 6 | Stage 1 各档 X_new ≤ 上界面（W≤136 题 E_cap≤42、P≤9 题 E_cap=0、G≤12 题 E_cap≤4），精确谓词只会更小 | 主会话互证 |

## 六、产物

```
reports/ppv1_s5b/l1_replay_2026-10-15/
  l1_replay_probe.py        # 探针脚本（import base 模板+src 只读）
  l1_replay_data.json       # 全量：meta/Stage0-4/逐件明细（962+17 件）
  l1_replay_summary.md      # 大白话+表格（每表 298 标签）
```

## 七、回传义务（≤30 行）

①Stage 0 复现结果（逐题对上/偏差）；②各档 X_new 件数/题数 + E_cap/E_cup/E_now；
③各档编译存活件数/题数 + 拒因交叉表（锁2 工单）；④池变化近似结果+披露口径；
⑤声明可消费计数；⑥锚点核对清单逐项；⑦三产物路径。主会话将抽查：Stage 0
复现明细、P 档逐件结果、D 档拒因分布、HEAD/工作树零 diff。

## 八、排障表

| 症状 | 处置 |
|---|---|
| rdkit 导入失败 | 解释器用错，回 conda depending43 |
| import src 模块报相对导入错 | sys.path 插仓根后 `from pathway_v43.pollutant import s5b_builder` 形式 import |
| 救援资格门函数读码定位困难 | 沿 `analog_cosub_supply`/`S5B_ANALOG_COSUB_SUPPLY_VERSION`/`_attach_analog_cosub_supply_fields` 反查调用链（873c323 提交是权威地图） |
| Stage 0 复现偏差 | 停，逐题列偏差+可能原因（如需 run 期状态而本地无），不硬调参凑数 |
| 重放 962 件超 15 分钟 | 正常可等；超 1 小时排查缓存/重复解析 |
| 某候选 resolve 失败 | base 模板 meta.ambiguities 有 10 条已知歧义，按同口径处理并计数 |

## 九、明确不在本任务范围

- 任何资格放宽的实施（只测不改）；L2 编译能力工程；判分侧；产物侧口径
  （CC 已拍板不放宽）；chain14 发车物；金标/题面任何接触。
