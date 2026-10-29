# 任务书 — chain13 C 供给净负贡献归因轮（2026-10-15）

> 执行者：实施子代理（单代理串行）。主会话已完成的骨架结论见 §一，
> 本轮任务=把它闭环到 payload 级证据 + 出归因报告与拍板材料。
> 题域标签：**298=RHEA 通用酶学/已见题**，所有输出引用带此标签。

## 一、现状（主会话已核实，执行者以此为准，不必重推）

### 1. 批次与口径

| 件 | 值 |
|---|---|
| chain13 GLM 臂批根（HPC，**只读封存**） | `~/ppv1_hpc/batch/chain13_s5b_20261014`（wuzh02） |
| runs 根（HPC，只读） | `~/ppv1_hpc/runs/chain13_s5b_20261014`（全量 186M，payload 子集约 57M） |
| 本地判分产物 | `reports/ppv1_s5b/chain13_glm/{metrics.json(v2), metrics.json.v1, batch_report.json}` |
| chain12 基线（本地，含 synced 全量） | `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/synced/`（298 cases+runs，38M） |
| v1/v2 主数（GLM 臂） | v1 strict/partial/uncov = 114/52/132；v2 = 119/47/132；hit@1 v1=83 / v2=87 |
| chain12 基线（v1） | strict/partial/uncov = 130/43/125；hit@1=92 |

### 2. 主会话骨架结论（你要验证并细化，不是推翻）

**迁移矩阵（chain12→chain13 GLM，v1 口径，逐题）**：

| 迁移 | 全 298 | C 门开的 35 题 | 输入零变化 263 题 |
|---|---:|---:|---:|
| S→P | 10 | 4 | 6 |
| S→U | 13 | 1 | 12 |
| P→S | 2 | 0 | 2 |
| U→S | 5 | 0 | 5 |
| P→U | 8 | 0 | 8 |
| U→P | 9 | 2 | 7 |
| strict 净变化 | 130→114（-16） | 24→19（-5） | 106→95（-11） |

**已定事实**：

1. C 门（`analog_cosub_supply_rescued>0`）只在 35 题开；分布 263 题=0、30 题=1、4 题=2、1 题=3。
2. **模拟豁免 13 题（chain12 rescore `in_cs2c_13`）全部 rescued=0/declared=0——供给面与兑现面零交集**，0/13 根因在供给门，不在模型选择。
3. 实际 v2 豁免 5 题全部是 C 门开的题（rescued=1/declared=1），全 H₂O 家族；其中 3 题原 chain12 strict（S→P→救回，净零）、2 题原 uncovered（净 +2）。
4. C 35 题 v2 后 strict=24=chain12 水平（**C+v2 合并自效应净零**：+2/−1/−1/3 绕行）。
5. 代码链：chain12→chain13 生成侧改动只有 C 线提交 `873c323`（判分侧提交自证零生成改动；`0ba764f` Plan 只加 docs）。C 线的 run 期 fail-closed 门键控在 spec 声明键上，键不在=路径零变化（`production.py` `_verify_execution_input`/`_record_equation_provenance`）。
6. 交付书自证池字节等价：262 题全等+35 题纯新增+1 题补位互动（`docs/C_COSUB_SUPPLY_IMPL_DELIVERY_2026-10-14.md`）。

**由此待验证的核心命题**：263 题输入零变化却 -11 strict → 归因采样/服务端非确定性（需 payload 级证据+采样参数留痕），而不是 C 线。

## 二、红线（违反任何一条=立即停并报告）

1. **零 LLM、零模型调用、零判分重算**（不跑评测器、不改判分）；允许且仅允许：HPC 只读拉取（rsync/scp）+ 本地离线分析。
2. HPC 批根与 runs 根**只读**；不删、不改、不在其上跑分析（分析全在本地）。
3. 金标/题面永不入仓；分析输出只落 gitignored 的 `reports/ppv1_s5b/` 与本任务书指定文件。
4. 不动 `src/`、`tests/`、既有 docs/AGENTS.md；不 commit、不 push。
5. 对外数字一律带题域标签 298；探针≠预注册≠成绩。
6. 拼不出=诚实 unknown，不得硬归。

## 三、分步执行

### 步骤 A：拉 chain13 GLM synced 子集回本地

目标结构 `reports/ppv1_s5b/chain13_glm/synced/`（对齐 chain12 synced 形态，funnel 可直接吃）：

```
synced/
  metrics.json        # 从 HPC 批根拷（v2 版）
  metrics.json.v1     # 同上
  batch_manifest.json
  batch_report.json
  cases/<qid>.json    # 298 件，从 HPC 批根 cases/ 拷
  runs/<run_id>/native_export/<digest>/payload.json   # 只拉 payload.json（rsync 过滤）
  run_identity/<run_id>.json  # 298 件小文件，代码/资产身份留痕
```

命令（Mac 本地发起；HPC 坑见 §五）：

```bash
H="ssh -i ~/.ssh/hpc_wuzh02_key -p 65091 -o BatchMode=yes aclhl3hbth@wuzh02.hpccube.com"
B=~/ppv1_hpc/batch/chain13_s5b_20261014   # 远端批根
R=~/ppv1_hpc/runs/chain13_s5b_20261014    # 远端 runs
D=reports/ppv1_s5b/chain13_glm/synced     # 本地目标
mkdir -p $D
scp -i ~/.ssh/hpc_wuzh02_key -P 65091 -o BatchMode=yes \
  aclhl3hbth@wuzh02.hpccube.com:$B/{metrics.json,metrics.json.v1,batch_manifest.json,batch_report.json} $D/
rsync -av -e "ssh -i ~/.ssh/hpc_wuzh02_key -p 65091 -o BatchMode=yes" \
  aclhl3hbth@wuzh02.hpccube.com:$B/cases/ $D/cases/
# runs 只要 payload.json（约 57M）
rsync -av -e "ssh -i ~/.ssh/hpc_wuzh02_key -p 65091 -o BatchMode=yes" \
  -f '+ */' -f '+ payload.json' -f '- *' \
  aclhl3hbth@wuzh02.hpccube.com:$R/ $D/runs/
# run_identity 快照（小，298 件）
for 试一次批量: rsync -av -f '+ */' -f '+ run_identity.json' -f '- *' 同上 → $D/run_identity/
```

验收：`ls $D/cases | wc -l` =298；`find $D/runs -name payload.json | wc -l` =298；
`find $D/run_identity -name '*.json' | wc -l` =298；metrics 行数 per_qid=298。

### 步骤 B：跑既有 funnel（标准口径，零改动）

```bash
python3 scripts/s5b_offline_funnel.py reports/ppv1_s5b/chain13_glm \
  reports/ppv1_s5b/chain13_glm/analysis --label chain13_glm
```

产出 `funnel_chain13_glm.json/_summary.md`；与 chain12 的
`analysis/funnel_chain12_r2.json` 对照分桶（仅描述统计，不判归因）。

### 步骤 C：归因主脚本（新建 `reports/ppv1_s5b/chain13_glm/analysis/attr_chain13_c.py`）

零依赖第三方（只用 stdlib+已有 json），输出 `attr_chain13_c.json` + `attr_chain13_c_summary.md` 到同目录。内容分五块：

**C1. 迁移矩阵×C 暴露复核**：用本地 metrics 重算 §一矩阵；对不上一行就停并报告（不得硬凑）。
hit@1 面补一张 rank 迁移表：chain12 rank1↔chain13 rank（只对两批都 strict 的题），
用来分解 v2 headline 87 vs 92 的 -5 中「覆盖损失」vs「rank 掉出 top1」。

**C2. C 35 题 payload 级声明链追踪**：对每题从 payload 抽：
- cosub 候选是否被选中执行（`search_actions`/`alternatives`/`expansion_outcomes` 里
  定位带 `record_equation`/`cosubstrate_event_contract`/`execution_input_smiles` 的 spec；
  manifest `pool_diagnostics.candidates` 逐候选行有 channel/outcome 可参照）；
- 事件是否带 participants/声明（`events`、`audit_production_reports` 的
  `production_payload`、hypothesis `provenance_refs`、`payload.provenance_records`）；
- ProductionContractError 痕迹（cases 的 run_error/结构化拒 kind=`execution_input_*`）。
产出 35 行表：qid × {选中?, 执行?, 参与物事件?, 声明链?, v1 状态迁移, v2 状态迁移, 证据字段}。
**重点题**：S→U 那 1 题（是不是 fail-closed 拒了？）、S→P→P 那 1 题（哪个家族没豁免）、
U→P→S 那 2 题（净赚路径长什么样）。

**C3. 损失题候选集差分（S→P 10 题 + S→U 13 题）**：对每题对比 chain12 vs chain13
payload：选中候选集（spec 身份/来源 channel）、model 排序（`model_rank_by_id`）、
novel proposals 数、dedup。按 C 暴露分组输出。非 C 题预期结论：**输入零变化而选择集变了**
（=采样/服务端非确定性证据）；如实记录例外。

**C4. 13 题模拟面复核**：13 题 rescued=0 已定；补两件事：
(a) 这 13 题的 chain13 事件里有没有金标缺失的那个共底物参与物（有参与物但无声明链=
生成面差一口气；连参与物都没有=供给面差）；参与物身份从 chain12 rescore 数据
`per_qid_partial_attribution[].events_reviewed` 的既有披露字段取（不读金标原文件）。
(b) 记录 13 题在 chain13 的终态（8 partial/4 uncov/1 strict 已知，逐一列 qid）。

**C5. 采样参数与身份留痕**：从 `run_identity`（code_identity aggregate_sha256）、
`synced/runs/*/s5b_real_calls.jsonl` 若拉了则抽 1-2 行的 model/temperature 参数、
batch_report 的 budget_mode、chain12 synced 的对应字段，写进 meta。
chain12 的调用参数在 `reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/synced/runs/`
下同名字段（若结构不同如实记录差异，不硬凑）。

### 步骤 D：归因报告

写 `docs/CHAIN13_C_NETNEG_ATTRIBUTION_2026-10-15.md`（技术版）+
`docs/CHAIN13_C_NETNEG_ATTRIBUTION_PLAIN_2026-10-15.md`（大白话版+术语对照表）。
骨架：

1. 结论先行三句：C 线+v2 合并自效应净零（24→24）；-16 v1 strict 的主损失在输入零变化
   263 题（-11，证据=候选集差分+采样留痕，诚实标注"非确定性无法逐题定责"）；13 题兑现
   0/13 根因=供给门未开（面不交集）。
2. 迁移矩阵全表+rank 面；35 题追踪表；损失题差分表；13 题面错配表。
3. 拍板材料：C 线三选一（回滚/收窄/重设计）的证据面——
   - 若 C2 显示 S→U 题=fail-closed 误拒 → 收窄修复点；
   - 13 题钥匙重设计方向=供给门资格面（让 partial 面题的共底物进袋：analog 前置门
     拒绝+Tanimoto 伴生救援的资格条件为什么没罩住这 13 题——从 manifest
     `pool_diagnostics.candidates` 逐候选行与 corpus_diagnostics 找证据，只描述不修）；
   - 方差治理：同协议重复批的期望波动（引用两臂 hpc2 A/B 与本批 churn 量级做参照，
     不冒充 CI）。
4. provenance：命令、文件哈希（对 synced 关键 json 算 sha256 落报告）、红线遵守声明。

## 四、回传义务

完成后回报：①synced 拉取验收数字；②funnel 分桶对照一行；③C1-C5 各一块结论
（每块≤5 行）；④与 §一骨架结论的任何不一致（**有不一致必须显式列出，不得静默改口径**）；
⑤两份报告路径。主会话将抽查：矩阵数字、35 题表中重点 4 题、13 题参与物判定、
run_identity sha256。

## 五、排障表（HPC 已知坑，全踩过）

| 症状 | 处置 |
|---|---|
| scp/ssh 放的 /tmp 文件找不到 | 登录节点轮转 /tmp 不共享；**中转一律走家目录** `~/` |
| ssh 输出混 perl locale 警告 | 无害，stderr 过滤即可 |
| rsync 报不认参数/不建父目录 | 本地 Mac rsync 发起没问题；远端侧只读不动 |
| 连接超时 | `-o ConnectTimeout=15` 重试一次；再败停并报告 |
| rsync 过滤后 payload 数<298 | 检查 `-f '+ */'` 在前；仍缺则逐 run 列缺失 id 报告，不补跑 |

## 六、涉及路径速查

- 本地仓：`/Volumes/CC/Enzyme_Agent/dependingv43`（分支 v4.3，HEAD 461844e，**不 commit**）
- `/tmp/cexposed_qids.json`（35 题清单，主会话已生成）、`/tmp/sim13_qids.json`（13 题）、
  `/tmp/rescue5_qids.json`（5 题）——执行者拷进 analysis 目录留存
- chain12 rescore 13 题源：`reports/ppv1_s5b/chain12_s5b_298_v4b_20261012/analysis/criteria_v2_rescore_data.json`（`per_qid_partial_attribution[].in_cs2c_13`）
- C 线实现参考：`git show 873c323`；交付书 `docs/C_COSUB_SUPPLY_IMPL_DELIVERY_2026-10-14.md`
