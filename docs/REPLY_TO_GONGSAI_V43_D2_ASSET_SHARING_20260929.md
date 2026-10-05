# 回复弓赛：v4.3 D2题卷拼合资产共享

日期：2026-09-29  
回复人：陈浩然线  
用途：回应《hit@1→60%题卷拼合的资产共享知会与请求》

## Chenyu资产位置速查（已实地核验）

以下路径均位于Chenyu，可直接只读访问；本轮所需资产**无需本地另发**：

| 用途 | Chenyu绝对路径 | bytes / SHA256 | 使用状态 |
|---|---|---|---|
| BIOSYSMOdb121拆步B1 | `/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Returned_Result_Summaries/biosysmodb121_B1_biosysmodb121_b1_step_gold_freeze_20260928.tar.gz` | `876022` / `6858c165660eef411a1e43eea187d7ef9b64e9a8a071f7e2b87c2841a5a363f2` | 直接使用包内`B1/`正式文件 |
| BIOSYSMOdb121完整B0输入 | `/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Inputs/biosysmodb121_step_enzyme_ranking_inputs_20260928.tar.gz` | `28476186` / `f7ff8653bfd9e4be1ce4831a0f4308628719a02a4f8c27bfad59e7ef388b569e` | 原始表、FASTA、许可、G1与旧298清洗载荷 |
| RHEA broad-87 | `/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Returned_Result_Summaries/rhea142_broad87_reaction_enzyme_benchmark_freeze_20260920.tar.gz` | `2338154` / `847f061eecc13960ae2242ccd999dcd00caca5b47587786307f1d87473181606` | 候选题源；结合primary-product补丁使用 |
| RHEA primary-product补丁 | `/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Inputs/rhea142_broad87_local_product_gold_patch_three_model_blind_20260920/rhea142_broad87_primary_product_gold_local_patch_r1_20260920.tar.gz` | `17912` / `cf09025d020663ce44b7bf139e11e388b4f470b3c2f40e082a2c177af5fe95d2` | 修正原product gold的副产物混入 |
| BRENDA extra-213 | `/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Returned_Result_Summaries/brenda2026_brenda_only_broad_biodegradation_extra213_benchmark_20260920.tar.gz` | `4743751` / `00eaa6341bc4a3ce487b508497764c444642a35fe6fedd0dd2b512c1f02760e9` | 仅候选池，不能直接作严格盲卷 |
| 旧298冻结题卷 | `/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Inputs/pollutant298_three_model_reaction_benchmark_freeze_20260921.tar.gz` | `114037` / `a404f06777196d72984b09cb22799affbc63ad85da84e8884ae2651d1d857524` | 仅作重复/泄漏对照 |
| v6训练对照run | `/usrdata/EnzymeCAGE_data/training_runs/enzymecage_v6_298_rhea142_brenda_enzgfm650m_retrain_20260922/` | 目录资产，无单一归档SHA | 只读提取冻结reaction-group与sequence SHA作查重 |
| G5-R1三题smoke | `/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Returned_Result_Summaries/biosysmodb150_g5_return_v1_6_20260929T080539Z.tar.gz` | `4928464` / `0877668089a174a19486a9fdfebaf6e5e1b6943883a9d0c1ebe7b496b635abe7` | 工程smoke证据，不是正式模型排名 |

Chenyu上的`25_...`、`26_...`是本地文档编号，不是远端数据入口；请以上表中的`HPC_Inputs`、
`HPC_Returned_Result_Summaries`及`training_runs`绝对路径为准。

## 一、先确认：是的，你要的就是我们最终121条BIOSYSMOdb路径

你信中所说“BIOSYSMOdb 121题拆单步”，对应黄老师最终批准后的正式集合，不是早期127/126口径。

我们已经完成拆步并冻结了B1单步gold，当前权威数量是：

```text
formal pathways=121
step occurrences=533
unique directed source reactions=460
participant rows=2473
enzyme gold rows=1355
enzyme-step links=1349
unique enzyme IDs=880
unique normalized EC=373
STEP-scope organism rows=1869
```

533是case级step occurrence分母；相同化学反应可能出现在不同路径，所以化学反应去重后是460。
建议题卷主键保留`case_id + step_occurrence_id`，另报460反应层结果，不要混分母。

## 二、可直接共享的冻结资产

### 1. 已拆单步的B1正式包（优先使用）

Chenyu已核验只读归档：

```text
/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Returned_Result_Summaries/biosysmodb121_B1_biosysmodb121_b1_step_gold_freeze_20260928.tar.gz
bytes=876022
sha256=6858c165660eef411a1e43eea187d7ef9b64e9a8a071f7e2b87c2841a5a363f2
```

B1中可直接读取：

```text
B1/formal_121_cases.tsv
B1/step_queries.tsv
B1/step_participants.tsv
B1/step_gold_enzymes.tsv
B1/step_gold_organisms.tsv
B1/enzyme_sequence_crosswalk.tsv
B1/REACTION_VIEW_AUDIT.tsv
B1/GOLD_COVERAGE.json
B1/counts.json
B1/validation/VALIDATION_GATES.json
B1_mutations/MUTATION_RESULTS.json
```

包内同时保留了`B1_attempts/crash*`和`crosswalk_work/v1_parsebug`开发证据；这些不是正式输入，必须忽略。

B1状态：

```text
PASS_B1_STEP_GOLD_FROZEN_WITH_TYPED_LOW_COVERAGE
validator=30/30
mutations=7/7
```

### 2. 完整输入/来源/许可包

如果需要原始BIOSYSMOdb表、FASTA、来源与许可，使用B0包：

```text
/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Inputs/biosysmodb121_step_enzyme_ranking_inputs_20260928.tar.gz

bytes=28476186
sha256=f7ff8653bfd9e4be1ce4831a0f4308628719a02a4f8c27bfad59e7ef388b569e
validator baseline=49 gates PASS
archive validator=57 gates PASS
mutations=10/10
```

包内含原始Pathways/Reactions/Enzymes/Organisms、compound表、蛋白注释、FASTA、G1 gold、老师批准、
build/validator和许可文件。

许可：

```text
BIOSYSMOdb overall=CC BY-NC-SA 4.0
使用时需署名BIOSYSMOdb及原始来源
非商业
衍生物同许可共享
UniProt/MibPOPdb/ChEBI等子来源同时遵循其各自许可
```

## 三、重要限制：533步不是533道现成的序列级排序题

反应方向和accepted enzyme注释覆盖533/533，但`enzyme_id/accession -> 唯一蛋白sequence`严格映射目前很低：

```text
GOLD_COMPLETE=1 step
GOLD_PARTIAL=10 steps
NO_STRICT_GOLD=522 steps
resolved enzyme records=30
ambiguous records=207
unresolved records=1118
unique strict accessions=44
```

因此：

- 如果E1–E4评价的是酶名/EC检索，533步都可作为题源；
- 如果评价的是EnzymeCAGE式蛋白序列候选排序，当前不能把533步全部计入hit@1；
- 需要先做sequence gold补映射，并预注册`MODEL_EVALUABLE`分母；
- `GOLD_PARTIAL`存在漏报accepted gold风险，不能与`GOLD_COMPLETE`混成严格盲测主分母。

所以BIOSYSMOdb121可以作为dev/盲测卷的主体**候选源**，但仅靠当前严格sequence gold不足以直接切出
50–100 dev +100–150 blind。需要与RHEA/BRENDA补源并继续做sequence closure。

## 四、RHEA/BRENDA留出资产现状

构建口径、归档和脚本仍在，但还不能直接承诺“约100题严格留出集已就绪”。

### RHEA侧

已有：

```text
/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Returned_Result_Summaries/rhea142_broad87_reaction_enzyme_benchmark_freeze_20260920.tar.gz

bytes=2338154
sha256=847f061eecc13960ae2242ccd999dcd00caca5b47587786307f1d87473181606

reaction families=87
blind parent cases=85
strict enzyme gold pairs=390
```

反应/酶gold本体通过；原product gold曾有副产物混入问题，primary-product补丁也已在Chenyu在盘。对于单步酶排序，
RHEA broad-87是当前最接近可用的第二题源，但仍需与旧298、新训练集和BIOSYSMOdb533做统一方向/规范化/sequence overlap审计。

Chenyu补丁路径：

```text
/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Inputs/rhea142_broad87_local_product_gold_patch_three_model_blind_20260920/rhea142_broad87_primary_product_gold_local_patch_r1_20260920.tar.gz
bytes=17912
sha256=cf09025d020663ce44b7bf139e11e388b4f470b3c2f40e082a2c177af5fe95d2
```

### BRENDA侧

Chenyu候选包：

```text
/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Returned_Result_Summaries/brenda2026_brenda_only_broad_biodegradation_extra213_benchmark_20260920.tar.gz
bytes=4743751
sha256=00eaa6341bc4a3ce487b508497764c444642a35fe6fedd0dd2b512c1f02760e9
status=NOT_RUN
```

该包当前审计结论不允许直接用作严格盲测：

```text
selected broad cases=213
exact/reverse enviPath overlap=0
但污染物范围仍偏宽
direct enzyme accession出现character-split bug
98条与RHEA/EnzymeMap表示存在分歧
product gold仍偏宽
```

因此BRENDA 213只能作为候选池，必须先修复structured accession、污染物范围、表示等价和gold角色，
不能直接并入新盲卷。

### 当前能否凑够

数量上候选容量足够，但“100–150条严格、零重叠、sequence-resolved盲题”尚未冻结。建议先做一个
D2专用CPU-only preflight，把以下候选统一去重和审计后再报真实可用量：

```text
BIOSYSMOdb B1 533 steps
RHEA broad-87
BRENDA corrected holdout candidates
```

## 五、重叠审计对照

以下只读对照已经在Chenyu，可在你方新建独立run后读取，不要修改源目录：

```text
旧298：/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Inputs/pollutant298_three_model_reaction_benchmark_freeze_20260921.tar.gz
训练对照：/usrdata/EnzymeCAGE_data/training_runs/enzymecage_v6_298_rhea142_brenda_enzgfm650m_retrain_20260922/
BIOSYSMOdb B1：使用本文开头B1归档中的533条step_queries及sequence SHA
RHEA/BRENDA：使用本文开头两个候选归档及其provenance
```

按你信中纪律，建议预注册并同时报告：

```text
exact directional reaction
reverse-equivalent
model-cleaned canonical reaction
parent reaction
gold sequence SHA
candidate sequence SHA
enzyme accession
```

旧298冻结题卷为114037 bytes，SHA256=`a404f06777196d72984b09cb22799affbc63ad85da84e8884ae2651d1d857524`。
旧298清洗脚本还在B0包的`authorities/cleaning/`中；RHEA/BRENDA完整构建链和返回归档也都保留。
但请不要把“exact/reverse为0”自动解释成所有规范化和sequence层都零泄漏。

## 六、五模型裸测状态

当前只有三题G5工程smoke，不是完整科学裸测：

```text
Chenyu返回：/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Returned_Result_Summaries/biosysmodb150_g5_return_v1_6_20260929T080539Z.tar.gz
bytes=4928464
sha256=0877668089a174a19486a9fdfebaf6e5e1b6943883a9d0c1ebe7b496b635abe7
HTTP 200=15/15
R1五模型=11/15可用JSON，G5 FAIL
失败原因：4个length截断
```

老师后续裁决改为四家族一类一款：

```text
qwen3.8-max
deepseek-v4.1-flash
ZHIPU/GLM-5.3
kimi/kimi-k3
统一max_tokens=65536
```

新的G5-R2包尚在修复首槽回传分支，未真实执行；因此E4模型选型暂时没有可交付的完整裸测结论。

## 七、请避开的目录/批次

以下远端资产均只读：

```text
/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Inputs/ 中本文列出的冻结输入
/usrdata/EnzymeCAGE_data/EnzymeCAGE-master/HPC_Returned_Result_Summaries/ 中现有B0/B1/B2/B2-R1/B3归档
/usrdata/EnzymeCAGE_data/workspaces/biosysmodb121_step_enzyme_ranking_20260928/
```

不要使用：

```text
quarantine 29题作为正式题
早期127/126口径
B1_attempts/下的crash中间产物
旧B3A含空selected_uid和无model_key reaction work item的版本
任何已看过模型输出后才重新选择的题
```

你方请新建独立目录，例如：

```text
/usrdata/EnzymeCAGE_data/workspaces/v43_hit60_d2_question_assembly_20260929/
```

## 八、建议下一步

可以立即把B1 tar作为只读题源交付，让你方先完成reaction-level去重和dev/blind预划分代码；但在
sequence gold与统一重叠审计完成前，不应冻结最终hit@1盲卷。

本次请求涉及的归档均已在Chenyu，不需要从陈浩然本地另发。请按本文开头的绝对路径与SHA读取；
如某个文件实际读取失败，先报具体路径和报错，不要改用同名工作区中间产物。
