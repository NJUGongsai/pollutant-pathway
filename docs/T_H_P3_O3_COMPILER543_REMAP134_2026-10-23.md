# T-H P3 O3：编译器 543 与 remap 134 归因回放（2026-10-23）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本文所有候选行、
> 题数、事件数、比例只在该题域 T-H r2 批次成立；不外推到 dev、新题或其他批次。
>
> **性质：只读诊断（P3 分诊 O3；D2 级测量落地）。** 零模型调用、零付费、
> 零代码/判据改动、零金标/题面/`reference_graphs`/`env`/key 读取；未读封存逐题
> `payload.json` 的化学正文；HPC 只读（未写批根、未写代码树；`PYTHONDONTWRITEBYTECODE=1`
> 下经 ssh stdin 执行，stdout 回传本地）。**本文与证据目录零化学串**：化学内容只以
> sha256 / record_key / 计数 / 状态码出现。
>
> 任务书：`docs/T_H_P3_SUPPLY_TRIAGE_2026-10-21.md` §5.2、§5.4、§7.4；
> O2 输入：`docs/T_H_P3_O2_F5_864_AUDIT_2026-10-23.md`；
> 决议包：`docs/T_H_P0_DECISION_PACK_2026-10-20.md` §D-7/未知 3、4、8；
> remap 老师杠杆：`docs/T_H_TEACHER_LEVER2_REMAP_AUDIT_2026-10-21.md`。
> 证据目录（本报告唯一新增证据）：`docs/review_evidence/p3_o3_compiler543_remap134_2026-10-23/`
> （含 `SHA256SUMS`；目录名沿用任务书指定日期，实际执行 2026-10-26）。

## 0. 结论先行

**一句话：543 精确复现，且 543/543 都是“F5 defer 于 transform_no_change →
remap 生效 → 编译层 no_alignment”的同一条路径；但这不是“remap 造成损失”，
因为 remap-off 的对照结果是 transform_no_change 拒绝，不是“本来能编译”。
134 也精确复现：134 条就是 F5-pass 且已编译调度的 complement，其中 102 条
remap 规则无缺口、32 条属于“强制 remap 会动、但当前触发条件不触发”的规则
边界候选；134 不是 remap 欠账。**

| 判定项 | 结果 | 标签 |
|---|---|---:|
| compiler 543 复现 | **543 行 / 164 题 / 920 事件**；route 42 direct_raw + 494 no_supply_raw + 7 supplied | 已证 |
| 543 的 F5 defer 原因 | **543/543 = `transform_no_change`**（同参回放 probe） | 已证 |
| 543 的 remap 路径 | **543/543 remap applied**；**543/543 编译层 `no_alignment`** | 已证 |
| “remap 诱导”的路径占比 | **100%（543/543）**；但“remap 造成本来可编译候选失败”的反事实 = **0**（remap-off 为 tnc 拒绝） | 已证/解释 |
| 543 机制分类 | expression gate 161；asset in_pool 252；asset not_retrieved 122；real_missing 强 5 + 弱 3；**unknown 0** | 已证（机械） |
| 543 资产轴（题集互斥） | 池内已有锚 **344 行 / 99 题 / 552 事件**；锚存在但未进池 **189 行 / 55 题 / 326 事件**；全资产无锚 **10 行 / 10 题 / 42 事件** | 已证 |
| remap 134 复现 | **134 已调度 analog spec / 98 题 / 520 事件**；全部 `f5=pass`、全部编译成功、target 精确复现 | 已证 |
| 134 分类 | **102 不适用（no_gap）+ 32 规则边界候选（强 remap 会补 42 个 map）+ 0 无底物/无模板 + 0 触发但编译失败 + 0 unknown** | 已证/规则测量 |
| 234 / 242 / 151 对账 | 234 已调度 applied + 8 未调度 compiled = **242**；151 P2 题 = 149 已调度 applied 题 + 2 个零事件 NC-9 题；242−234 = **8 spec / 2 个新增题（3 题涉及）/ 0 事件** | 已证 |
| 543 与 864 / 162 / 184 | 候选行交集 **0**；题交集 135、并集 223；事件 920 + 1077 − 752 = 1245；不能相加 | 已证 |
| 最大 unknown | 机械分类 unknown = **0**；剩余最大 unknown 是 **189 行/55 题的检索缺路细节** 与 **8 行 real_missing 的化学真值（D3）** | unknown |

**回答任务书两问：**

1. **543 是否复现、各分类多少：** 复现 543/543。机制分类为
   expression 161、in_pool 252、not_retrieved 122、real_missing 强 5 + 弱 3；
   **unknown 0**。按资产轴（题集互斥）为 in_pool 344 行/99 题、not_in_pool
   189 行/55 题、no_anchor 10 行/10 题。
2. **134 是否复现、是否 remap 欠账：** 复现 134/134。134 是 F5-pass 且已编译
   调度的 complement，不是“134 个应 remap 但漏了”；102 条无缺口，32 条是
   “规则会补 map、但触发条件（仅 tnc）不触发”的边界候选，当前全部编译成功。

**不得把拒绝条数当收益**（P3 §9.2）：上表是“拒绝为什么发生”的归因，不是
“可回收 543 条/题”。543 覆盖的 164 题中仍有 40 题 hit@1、62 题 strict；
252 条 in_pool 行所在题中 23 题 hit@1；122 条 not_retrieved 行所在题中 12 题
hit@1。任何修复的净效果必须走同题配对 + 全 298 题新增/损失对账。

## 1. Provenance 与方法

| 项 | 值 |
|---|---|
| 执行位置 | HPC `aclhl3hbth@wuzh02.hpccube.com:65091`（只读；脚本放 `~/p3o3_tmp`，不写批根/代码树） |
| 批根 | `~/ppv1_hpc/batch/t_h_s5b_298_20261020r2`；`batch_manifest.json` sha256 `640249d0…c1006e`；`build_identity.json` sha256 `49a1d86a…1583e2` |
| run 根 | `~/ppv1_hpc/runs/t_h_s5b_298_20261020r2`（只读 `native_export/*/payload.json` 白名单字段） |
| 代码（只读回放） | `~/EnzymeAgent/v43cTH/src`；5 个关键文件（`s5b_compiler.py`/`s5b_builder.py`/`recorded_source.py`/`services/analog_source.py`/`chemstate.py`）与本仓 r2 提交 `c9c6c7a` **逐字节同 sha256** |
| catalog | `~/EnzymeAgent/v43cTH/assets/analog/corpus_templates_v1.jsonl`，sha256 `8f3f2c1a…ccfad92`，与 `build_identity.asset_identity.analog_corpus_sha256` 程序内核对 True |
| 判据单源 | `compile_donor_template` / `center_anchor_probe` / `complete_template_mapping` / `extract_mapped_transform` / `build_center_query` / `enumerate_center_alignments` / `analog_cosub_supply` / `normalize_record_side_transaction` 直接 import，不另建实现 |
| RDKit / 编译器 | `rxn` env **2026.03.5**；`S5B_COMPILER_VERSION=s5b-compiler-6`、`_CENTER_QUERY_SHELL=2`、`_COMPILE_ALIGNMENT_LIMIT=64` 运行时断言 |
| 模型调用 / 付费 | 0 / 0 |
| 本地 HEAD | `966bc56`（审计对象是 r2 提交 `c9c6c7a` 的代码；HPC 5 文件与 r2 逐字节一致） |

**方法五步**（脚本全文在 `scripts/`，日志在 `logs/`）：

1. **S1 分母复现**（`p3o3_s1_extract_denominators.py` → `logs/s1_rows.jsonl`）：
   从 manifest 复现 543 行、F5 计数器、543/134/234/242/368 题集；从 298 个
   `native_export` payload 白名单投影 368 条已调度 analog spec（`template_remap`、
   edit op 名、center map 标签、target sha256；**不输出 SMILES**）。
2. **S2 同参回放**（`p3o3_s2_replay.py` → `logs/s2_replay.jsonl`）：
   对全部 1548 条 F5-defer analog 候选行与 368 条已调度 analog spec：
   ①按 record_id 解析 catalog 全部 occurrence；②按 route 重建 F4，**sha256 对上
   冻结 `execution_input_sha256` 才进入判定**；③同参回放 `center_anchor_probe`
   与 `compile_donor_template`；④对 543 行补测 remap 后 shell=1/shell=2 命中、
   全 catalog 中心锚扫描、同题池内锚检查；⑤对 134 条无 remap spec 补测
   pre-flight 与 `complete_template_mapping` 状态（不改运行时路径）。
3. **S2c 正负控**（`p3o3_s2c_controls.py` → `logs/s2c_controls.jsonl`）：
   合成正控/负控 + 543 模板全部 occurrence 的“remap 不删原子/幂等”不变量。
4. **S2d occurrence 身份歧义**（`p3o3_s2d_occurrence_ambiguity.py` →
   `logs/s2d_occurrence_ambiguity.jsonl`）：按“F4 hash + f5 defer + compile
   no_alignment”三条件统计每行可匹配的 catalog occurrence 数。
5. **S3 本地 join**（`p3o3_s3_local_join.py` → `s3_summary.json`、
   `compiler543_rows_classified.csv`、`remap134_specs_classified.csv`、
   `scheduled_analog_368.csv`、`qid_denominators.csv`）：
   分类 × 题/事件/hit/strict；与 O2 的 864/162/184、P2 的 242/151 对账。

**Occurrence 消歧（必须披露）：** catalog 有 148 个重复 `record_id`
（17,183 行 / 17,035 唯一 id）。S2 对每个候选保留全部 hash 一致的 occurrence，
用冻结的 `f5` 状态 + 冻结的 compile outcome/reason 选回运行时实际消费的那一条；
首遍 10 条不一致全部由重复 occurrence 造成，消歧后 **probe replay mismatch = 0**。
这是“用冻结结果做 occurrence 身份解析”，不是第二次独立运行；F4 sha256 是独立
匹配条件。543 中 510 行只有 1 个 hash 一致 occurrence，33 行有 2–6 个；按
“F4 hash + f5 defer + compile no_alignment”三条件筛选后，**511 行唯一命中 1 个
occurrence，32 行仍有 2–4 个 occurrence 同时满足**，本轮按确定性排序取第一条，
这 32 行的唯一身份仍 unknown（见 §10 第 9 项）。

## 2. 分母复现（全部对上）

| 口径 | 本审计 | 冻结/P3 | 一致 |
|---|---:|---:|---|
| compiler 543 候选行 | 543 | 543 | ✓ |
| 543 题（≥1 行） | 164 | 164 | ✓ |
| 543 事件（164 题已提交） | 920 | 920 | ✓ |
| 543 route：direct_raw / no_supply_raw / supplied | 42 / 494 / 7 | —（本审计 direct 字段） | ✓ |
| 全局 F5 reject route（**不是 543 分母**） | — | 50 推断 / 407 / 407 | 不同分母，不互换 |
| 543 source：raw / supplied | 536 / 7 | 536 / 7 | ✓ |
| F5 checked / deferred / skipped | 3398 / 1548 / 864 | 同 | ✓ |
| F5 defer 的 probe 原因 | **1543 tnc + 5 alignment_limit_exceeded** | 之前 unknown | ✓（D2 新测） |
| tnc 候选行（analog，f5=defer） | **1543** | 之前 unknown | ✓ |
| `no_alignment` 拆分 864/543/178 | 同 | 同 | ✓ |
| 已调度 analog spec | **368**（366 唯一 qid+key） | P3 未单列 | ✓ |
| remap applied / no-remap | **234 / 134** | 234 / 134 | ✓ |
| remap new maps / zero-new / applied-false | **728 / 0 / 0** | 728 / 0 | ✓ |
| `remove_atom`/`delete_atom` ops | **0** | 0 | ✓ |
| 234 题 / 134 题 / 368 并集题 | **149 / 98 / 205** | 151（P2 题面上界） | ✓（见 §4） |
| 234 事件 / 134 事件 / 368 并集事件 | **874 / 520 / 1130** | 874（151 题） | ✓ |
| 242 compiled F5-defer 行 / 151 题 | **242 / 151** | 242 / 151 | ✓ |
| 376 compiled analog 行 | **376 = 242 + 134** | 242 + 134 | ✓ |

**F5 defer 1548 的精确分解：**

| 分量 | 行数 | 说明 |
|---|---:|---|
| `transform_no_change`（tnc） | **1543** | 全部进入 remap 路径测量 |
| `alignment_limit_exceeded` | **5** | 非 tnc；编译层同因拒绝，不属于 543 |
| 合计 | **1548** | 与 `analog_center_admission_deferred` 一致 |

**231 条 `transform_no_change` 的原因码不是 1543：** manifest 的 reason
直方图 `transform_no_change=231` 是“最终拒因”计数，= **223 条 analog tnc
（remap no_gap，最终仍 tnc）+ 8 条 corpus 行**。1543 是“F5 defer 且 probe
为 tnc”的候选行；两者单位不同，不能混用。

**543 的 route/source/formnorm：**

| 维度 | 值 |
|---|---|
| route | direct_raw 42、no_supply_raw 494、supplied 7 |
| execution_input_source | raw 536、supplied 7 |
| record_side_form_norm | applied 166、not_applicable 377 |
| 唯一模板 record_key | 233 |
| 唯一 raw 底物 | 107 |

## 3. compiler 543：复现与四类归因

### 3.1 复现事实（同参回放）

- **543/543** 的 F5 probe 回放为 `defer:transform_no_change`（不是 absent、不是
  center_empty、不是 alignment_limit）。
- **543/543** 的 `complete_template_mapping` 返回 `remapped`（applied=true）；
  新增 map 数 1–66。
- **543/543** 的 `compile_donor_template` 回放为 `unsupported:no_alignment`。
- 543/543 的 F4 重建 sha256 与冻结 `execution_input_sha256` 一致；原始底物
  与 F4 上的 shell=1/shell=2 计数完全相同（supply bag 对这 543 行没有改变
  中心命中）。
- 三层一致：**F5 defer 原因 = tnc；remap 状态 = applied；编译拒因 = no_alignment**。
  这三层在 543 行上完全重合，没有一条是“F5 defer 于其它原因、编译却出
  no_alignment”的异常。

### 3.2 机制分类（互斥，优先级从上到下）

| 类 | 判据 | 候选行 | 题 | 事件† | 题内 hit@1 | 题内 strict | 唯一模板 |
|---|---|---:|---:|---:|---:|---:|---:|
| unknown_* | 模板/F4/回放/remap 异常 | **0** | 0 | 0 | — | — | — |
| remap_expression_gate_shell2 | remap 后中心 shell=1 命中 >0、shell=2 =0 | **161** | **96** | **535** | 18 | 32 | 54 |
| remap_asset_face_in_pool | shell=1 =0；catalog 有其它 shell=2 锚，且在同题池内 | **252** | **82** | **458** | 23 | 33 | 122 |
| remap_asset_face_not_retrieved | shell=1 =0；catalog 有锚但不在同题池 | **122** | **48** | **289** | 12 | 18 | 66 |
| remap_real_missing_asset_level_strong | 全 catalog 无 shell=2 锚，且无 shell=1 锚 | **5** | **5** | **24** | 0 | 0 | 3 |
| remap_real_missing_asset_level_weak | 全 catalog 无 shell=2 锚，但有 shell=1 锚 | **3** | **3** | **9** | 1 | 3 | 1 |
| **合计** | | **543** | **164（并集）** | **920（并集）** | **40** | **62** | **233** |

† 事件列是题级上下文分母，各类题集互相重叠，**不能相加**：161+252+122+5+3=543 行，
但题数 96+82+48+5+3=234 > 164；事件 535+458+289+24+9=1315 > 920。

**partial 披露：** 252 条 in_pool 中有 **8 条** `any_s2_in_pool=partial`
（该底物 shell=2 锚数超过 500 上限截断，池内命中检查不完整；同 O2 的 TK_CAP=500
披露）。影响 ≤8 行的分类置信，方向不变；资产轴表中这 8 条计入 in_pool。

**读法：**

- **161 条（29.6%）是 expression gate 形态**：remap 后中心 L1 骨架在 F4 上
  shell=1 可命中，但 `shell=2` 双壳层零命中。这是编译表达/门定义面，不是
  “底物完全没有中心”。
- **382 条（70.3%）remap 后 shell=1 也零命中**：中心在编译输入上根本不落位。
  其中 252 条的同题池内已有其它可锚定模板（该行拒绝本身不构成供给损失），
  122 条锚存在但没进池（真供给缺路候选），8 条全资产无锚（资产级真实缺失）。
- **252 条 in_pool 行**：同题 analog 池里已经有别的 shell=2 可锚模板；这些行
  是“不适配的模板被正确拒”，不是该题无候选。
- **122 条 not_retrieved 行**：catalog 有锚，但同题池内没有任何锚定模板；
  与 O2 的 162 条同类但**候选行不相交**（见 §6）。

### 3.3 资产轴（题集互斥，可加）

| 资产轴 | 候选行 | 题 | 事件 | hit@1 | strict | partial | unmatched |
|---|---:|---:|---:|---:|---:|---:|---:|
| 同题池内已有其它 shell=2 锚 | **344** | **99** | **552** | 26 | 40 | 18 | 41 |
| catalog 有锚但未进池 | **189** | **55** | **326** | 12 | 18 | 8 | 29 |
| 全 catalog 无锚 | **10** | **10** | **42** | 2 | 4 | 2 | 4 |
| **合计** | **543** | **164** | **920** | **40** | **62** | **28** | **74** |

**这是 543 唯一可加的题/事件切分**：三类题集互斥（99+55+10=164），事件
552+326+42=920。其他切分（机制类、shell 类）题集重叠，不能相加。

- 344 行（63.4%）的拒绝行所在题**已有可用锚**；这些行不是供给缺口。
- 189 行（34.8%）是“资产有锚、检索/池没送到”的缺路候选；其中 122 行
  shell=1 也零命中（not_retrieved 类），67 行 shell=1 命中但被 shell=2 挡
  （expression 类里“池内无锚”的子集）。
- 10 行（1.8%）全 catalog 无锚：5 强 + 3 弱 real_missing + 2 条 expression
  但 any_s2=0。**8 条 real_missing 的 8 个题全部落在 O2 的 18 条 real_missing
  题集内**（见 §6），是同一批“资产级无锚”底物的 remap 面重现。

### 3.4 expression 161 的池内/池外拆分（E-E 的直接分母）

| expression 子集 | 候选行 | 题 |
|---|---:|---:|
| 同题池内已有其它锚 | **92** | **59** |
| catalog 有锚但未进池 | **67** | **35** |
| 全 catalog 无锚 | **2** | **2** |
| 合计 | **161** | **96** |

（行互斥；题集也互斥：59+35+2=96。）

**读法：** 即使 shell=1 放行这 161 行，只有 **69 行/37 题**（67 未进池 + 2
无锚）可能是“新增供给”；另外 **92 行/59 题** 的同题池内已经有锚，shell=1
即使编译成功也不增加该题的可选模板。E-E 的净新增空间必须按 37 题这个子集
报，不能按 161 行直接推。

### 3.5 route × 机制类

| route | expression | in_pool | not_retrieved | real_missing 强 | real_missing 弱 | 合计 |
|---|---:|---:|---:|---:|---:|---:|
| direct_raw | 25 | 11 | 4 | 2 | 0 | 42 |
| no_supply_raw | 135 | 236 | 117 | 3 | 3 | 494 |
| supplied | 1 | 5 | 1 | 0 | 0 | 7 |
| **合计** | **161** | **252** | **122** | **5** | **3** | **543** |

**读法：** 7 条 supplied 中 5 条 in_pool、1 条 not_retrieved、1 条 expression；
供给袋对这 543 行的中心落位没有实质贡献。

### 3.6 “remap 诱导”到底是多少

| 口径 | 值 | 含义 |
|---|---:|---|
| 543 中 tnc 触发 remap 的行 | **543/543 = 100%** | 路径上全部经过 remap |
| 543 中 remap applied 的行 | **543/543 = 100%** | 没有 no_gap/fail_closed |
| 543 中 remap-off 反事实可编译的行 | **0/543** | remap-off 的对照是 transform_no_change 拒绝 |
| 全部 tnc 行（1543）中 remap applied | 1320 / 1543 = 85.5% | 其余 223 为 no_gap |
| 全部 tnc 行中 remap applied 后 no_alignment | 543 / 1320 = 41.1% | 543/1543 = 35.2% |
| 全部 tnc 行中 remap 后编译成功（compiled+merged+truncated） | 517 / 1543 = 33.5% | 517/1320 = 39.2% |
| 全部 tnc 行中 remap applied 后其它拒因 | 260 / 1320 = 19.7% | ambiguous 163、new_atom 39、product_identity 33、execution 14、aromatic 9、center_empty 2 |

**结论：** “remap 诱导”是**路径归因**（100%），不是**损失归因**（0%）。
把 543 写成“remap 害得本来能编译的候选失败”没有证据；把 543 写成
“remap 后仍然不能对齐的候选”才是准确的。`remove_atom` 0 只否定“remap
删原子”这一条机制；不能否定“remap 改变映射导致中心偏移”仍可能是其中
382 条 shell=1 零命中的成因——但那是 E-D 的新规则实验，不是本轮结论。

## 4. remap 134：复现与分类

### 4.1 复现事实

- **134/134** 是已调度 analog spec，`template_remap` 键缺失（`has_key=false`），
  即运行时未触发 tnc/remap。
- **134/134** 的 manifest 候选行 `f5=pass`、`outcome=compiled`；route 为
  supplied 78、direct_raw 46、no_supply_raw 10。
- **134/134** 同参回放 `compile_donor_template` 编译成功，且
  `expectation.target_smiles` 与冻结 target **精确相等**（不是字符串宽松比较）。
- **134/134** 的模板 normalize 后 pre-flight `extract_mapped_transform` 均为
  **ok**（不是 tnc），所以“未触发 remap”与代码事实一致。

### 4.2 分类（互斥）

| 类 | 判据 | spec | 题 | 事件 | hit@1 | strict |
|---|---|---:|---:|---:|---:|---:|
| not_applicable_no_gap | `complete_template_mapping` = no_gap（无未映射分量） | **102** | **78** | **400** | 26 | 38 |
| trigger_rule_gap_candidate | pre-flight ok，但强制调用 `complete_template_mapping` = remapped（n_new_maps>0） | **32** | **26** | **158** | 7 | 10 |
| not_applicable_no_template / no_substrate | 模板解析不到 / 无底物 | **0** | 0 | 0 | — | — |
| triggered_compile_failed | tnc 触发但编译失败 | **0** | 0 | 0 | — | — |
| unknown | 回放/身份/规则异常 | **0** | 0 | 0 | — | — |
| **合计** | | **134** | **98（并集）** | **520（并集）** | **31** | **46** |

**32 条“规则边界候选”的 map 缺口：** 22 条补 1 个新 map、10 条补 2 个新 map，
合计 42 个新 map。**这不是已证缺陷**：这些 spec 当前不触发 remap 也能编译成功；
强制 remap 会改变模板 map 号，可能改变对齐/编辑/产物，必须走 E-D 的单变量
测量与化学评审，不能直接上线。

### 4.3 134 与 234 / 242 / 151 的分母关系

| 集合 | 单位 | 数量 | 题 | 事件 | 与其它集合的关系 |
|---|---|---:|---:|---:|---|
| 已调度 analog spec | spec | **368** | 205 | 1130 | = 234 applied + 134 no-remap（spec 可加） |
| remap applied 已调度 | spec | **234** | 149 | 874 | 全部来自 F5 defer tnc；全部编译成功 |
| remap not attempted | spec | **134** | 98 | 520 | 全部来自 F5 pass compiled；不是欠账 |
| 234 与 134 题交集 | 题 | — | **42** | **264** | 题/事件不可加：98+149=247，但并集 205 |
| compiled F5-defer pool 行 | 行 | **242** | 151 | 874 | = 234 已调度 + 8 未调度（3 题，2 个新题） |
| P2 remap 题面 | 题 | — | **151** | 874 | = 149 已调度 applied 题 + 2 个零事件 NC-9 题 |
| compiled analog 行 | 行 | **376** | 207 | — | = 242 defer + 134 pass |

**关键等式：**

- **368 = 234 + 134**（spec 级；这是唯一可以直接相加的一层）。
- **242 = 234 + 8**（行级）；242−234 = **8 spec / 2 个新增题（3 题涉及）/ 0 事件**，不是 8 题。
- **151 = 149 + 2**（题级）；两个新增题是 `RXNG_7a886593dd02…`、
  `RXNG_ed3d70729ea7…`，即 P0 记录的零调用 NC-9 题；它们没有已提交事件，
  所以 242/151 的事件仍为 874。
- **376 = 242 + 134**（行级）；134 是 F5-pass compiled，234 是 F5-defer
  compiled 的已调度子集。
- **368 题的并集 205，不是 247；事件并集 1130，不是 1394**（134 与 234 题
  交集 42、事件交集 264）。

**读法：** 134 不是“remap 机会漏掉 134 条”；它是 F5-pass 已编译调度的
complement。234 也不是“全部 remap 成功”——234 是从 1543 条 tnc 里被
编译成功且被调度的那一部分；242 是编译成功的全部 F5-defer 行，多出的 8 条
只是没被调度。

## 5. 全部 tnc 的 remap 账（1543 行）

| remap 状态 | 行数 | 编译 outcome / 拒因 | 行数 |
|---|---:|---|---:|
| applied | **1320** | compiled（独特池 spec） | 242 |
| applied | | merged_into（编译后并池） | 272 |
| applied | | pool_truncated | 3 |
| applied | | unsupported:no_alignment | **543** |
| applied | | unsupported:ambiguous_alignment | 163 |
| applied | | unsupported:new_atom_placement_incomplete | 39 |
| applied | | unsupported:product_component_identity_invalid | 33 |
| applied | | unsupported:execution_failed | 14 |
| applied | | unsupported:aromatic_new_bond_unsupported | 9 |
| applied | | unsupported:center_empty:removed_only | 2 |
| no_gap | **223** | unsupported:transform_no_change | 223 |
| **合计** | **1543** | | **1543** |

**读法：**

- remap 生效后 **517/1543 = 33.5%** 走到编译成功（242 compiled + 272 merged +
  3 truncated）；**543/1543 = 35.2%** 落到 no_alignment；**260/1543 = 16.9%**
  落到其它拒因；**223/1543 = 14.5%** 连 remap 都没补（no_gap，仍 tnc）。
- 543 是 remap 路径上最大的单一失败出口，但不是“唯一失败出口”；ambiguous 163、
  new_atom 39、product_identity 33 也是 remap 生效后的真实拒因。
- **223 条 no_gap 不是 543**：它们没有未映射分量可补，remap 规则不适用；
  与 8 条 corpus tnc 合计才是 manifest 的 `transform_no_change=231`。

## 6. 交叉对账：543 与 864/162/184，134 与 234/242/151

### 6.1 543 与 864/162/184/18

| 项 | 543 | 864（O2） | 交集 | 并集 | 说明 |
|---|---:|---:|---:|---:|---|
| 候选行 | 543 | 864 | **0** | 1407 | F5 defer vs F5 reject，按定义互斥 |
| 题 | 164 | 194 | **135** | **223** | 题交集大；不能相加 |
| 事件 | 920 | 1077 | **752** | **1245** | 920+1077−752=1245 |
| 唯一 raw 底物 | 107 | 134 | **86** | 155 | 543-only 21 |

| 543 机制类 | 行 | 题 | 对应 O2 类 | O2 行 | O2 题 | 题交集 |
|---|---:|---:|---|---:|---:|---:|
| expression 161 | 161 | 96 | expression_gate_shell2 | 184 | 96 | **25**（543-only 71） |
| not_retrieved 122 | 122 | 48 | asset_face_not_retrieved | 162 | 50 | **38**（543-only 10；864-only 12） |
| real_missing 强+弱 8 | 8 | 8 | real_missing 强+弱 | 18 | 12 | **8**（543 的 8 题全部在 O2 的 12 题内） |
| in_pool 252 | 252 | 82 | asset_face_in_pool | 500 | 124 | **74**（543-only 8；864-only 50） |

**必须这样读：**

- **候选行交集 = 0**：543 是 F5 defer，864 是 F5 reject；162/184/18 是 864
  的子类。所以 543 与 162/184/18 在行级不可能相交；把它们相加会重复计题。
- 题/事件交集很大（135 题/752 事件），因为同一题可以同时有 F5 reject 行和
  F5 defer 行；**题数不能相加**。
- 底物交集 86/107，说明多数 543 底物也在 O2 扫描过；21 个 543-only 底物是
  O2 未覆盖的新面（其 any_s2 由本轮扫描给出，但 O2 类归属 unknown）。
- **122 not_retrieved 与 162 not_retrieved 是同一“资产有锚、池内无锚”机制在
  两个 F5 分支上的重现**：题交集 38、543-only 10、864-only 12；不是同一批行。
- **8 real_missing 与 18 real_missing 的题集完全嵌套**：543 的 8 个题全部在
  O2 的 12 题内。这是“资产级无锚”底物在 remap 面的独立重现，不是新增资产
  缺口数量的证据。
- **expression 161 与 184 的题交集只有 25**：两者题集几乎是两批不同的题
  （543-only 71，O2-only 71）。F5 reject 的 shell=2 敏感面和 remap 后的
  shell=2 敏感面不是同一批题。

### 6.2 134 与 234 / 242 / 151

| 关系 | 结论 |
|---|---|
| 134 + 234 spec | **368**，spec 级可加 |
| 134 + 234 题 | 98 + 149 = 247，但并集 **205**；交集 42；题级不可加 |
| 134 + 234 事件 | 520 + 874 = 1394，但并集 **1130**；交集 264；事件级不可加 |
| 242 vs 234 | 242 行 = 234 已调度 + 8 未调度；差 8 行 / 3 题 / 2 个新题（NC-9）/ 0 事件 |
| 151 vs 149 | 151 P2 题 = 149 已调度 applied 题 + 2 个零事件 NC-9 题；事件都是 874 |
| 134 vs 242 | 134 不是 242 的子集（242 是 F5-defer compiled，134 是 F5-pass compiled）；题交集 42 |
| 376 compiled analog | 376 = 242 F5-defer + 134 F5-pass；这是 compiled 行级唯一互斥拆分 |

### 6.3 禁止相加清单（本轮实测）

- **543 + 864 = 1407 行**，但并集题只有 223；不能写“1407 行/358 题”。
- **543 机制类题数 96+82+48+5+3=234**，但并集 164；不能写“234 题”。
- **543 机制类事件 535+458+289+24+9=1315**，但并集 920；不能写“1315 事件”。
- **资产轴是唯一可加切分**：344+189+10=543 行，99+55+10=164 题，
  552+326+42=920 事件（三类题集互斥）。
- **134 题 + 234 题 = 247**，但并集 205；**134 事件 + 234 事件 = 1394**，
  但并集 1130。
- **242 − 234 = 8 行**，但只多 2 题、0 事件；不能写“多 8 题”。
- **543 与 162/184/18 行级交集 0**，但题/底物交集非零；不能把 543 加到
  162/184 上，也不能把 122 not_retrieved 加到 162 上。

## 7. 正负控与回放一致性

### 7.1 合法正控（已知可编译）

- **368/368** 已调度 analog spec 同参回放编译成功，且
  `expectation.target_smiles` 精确等于冻结 target。
- 其中 **234/234** remap applied spec：pre-flight 全部 tnc、remap 全部
  remapped、编译全部成功、target 全部精确；新增 map 合计 **728**。
- 其中 **134/134** no-remap spec：pre-flight 全部 ok、编译全部成功、target
  全部精确；102 no_gap、32 remapped（规则边界）。
- 这 368 条同时是“回放管线没有把拒绝原因写死”的正控：如果管线只会复制
  manifest 的 reason，不会得到 368/368 compiled + target 精确。

### 7.2 真实错误负控（已知不可表达）

| 负控 | 结果 |
|---|---|
| 合成“中心确实不在底物” | probe `absent:no_alignment`；compile `no_alignment`；remap no_gap；**通过** |
| 合成 tnc | probe `defer:transform_no_change`；remap no_gap；compile `transform_no_change`；**通过** |
| 合成 malformed 模板 | `complete_template_mapping=fail_closed`；compile `unsupported`；**通过** |
| 223 条 no_gap analog tnc 行 | 回放仍 `transform_no_change`；没有一条被 remap 放行；**通过** |
| 543 条 remap applied no_alignment | 回放仍 `no_alignment`；没有一条被误判 compiled；**通过** |
| 543 模板全部 248 个 occurrence | remap 前后原子数 **248/248 不变**；二次调用 **248/248 no_gap**；**通过** |

**结论：** 正控 368/368、负控 4/4 合成项 + 223 行 + 543 行 + 248 occurrence
全部通过。回放管线对“真无中心/真 tnc/坏模板”可靠拒绝，对“已知可编译”可靠
放行；没有为了凑分类而放宽判据。

## 8. 单变量实验设计：E-D（remap 触发/规则）与 E-E（编译表达）

> 两个实验都是**零模型、编译/审计级**；不产生 hit@1 结论，不替代评分实验。
> 任何改变候选成员/顺序的改动都必须按新 pool policy 版本预注册；全 298 题
> 报新增/损失/净增，不只在失分题展示。

### 8.1 E-D：remap 触发/规则单变量

| 项 | 内容 |
|---|---|
| 假设 | 当前“仅 tnc 触发 remap”的规则边界，使 32 条 F5-pass spec 的未映射分量从未被补；强制 remap 可能改变/改善这些 spec，也可能改变 543 中 remap 后的中心 |
| 固定输入 | 冻结 F4（含 supplied 袋重建）、catalog、冻结编译器/remap 规则、RDKit 2026.03.5、occurrence 消歧规则 |
| 唯一变量 | 阶段 1 无（披露型）：对 134 的 32 条规则边界 spec 与 543 的 1320 条 applied spec，逐条披露 `complete_template_mapping` 的补 map 分量与前后中心查询；阶段 2 才允许**只改触发条件**（tnc-only vs 对 32 条强制）或**只改配对规则**（matched 分量是否处理）之一，不能同时改 |
| 正控 | 234 条 applied spec 必须仍 234/234 编译成功、728 map、target 不变；368 条已调度 spec 必须仍 368/368 精确 |
| 真实错误负控 | 223 条 no_gap analog tnc 必须仍 `transform_no_change`；malformed 必须仍 `fail_closed`；543 必须仍 `no_alignment`（除非新规则有化学评审与正控） |
| 主读数 | 32 条强制 remap 后：compiled / still-rejected / target 改变 / edits 改变 / alignment 改变；543 的 1320 条：补 map 前后 shell1/shell2 迁移、compiled 新增/损失 |
| 停点 | 368 正控任一条 loss；223 负控翻 compiled；543 任一条无化学评审就编译成功；任何 target/edits 改变但未做化学评审；未升 pool policy 版本 |
| 分母 | 32 spec / 26 题 / 158 事件；134 / 98 / 520；234 / 149 / 874；543 / 164 / 920；1320 applied；223 no_gap |
| 可证伪形态 | 32 条强制 remap 后 spec/target 完全不变 ⇒ “规则边界”无实际影响，E-D 不立项；32 条有改变但无合法正控/化学评审 ⇒ 停；543 在新配对规则下新增 compiled 且负控不失守 ⇒ 才进入新规则预注册 |
| 结论（本轮） | **不值得按“触发开关”单独立项**：543 已全部 remap applied，切换触发不改变它们；32 条当前已编译成功，强制 remap 只会引入 spec 身份变化风险。若要做，只能作为“新 remap 配对规则”研究，需化学评审与预注册，不是工程 patch |

### 8.2 E-E：编译表达（center shell）单变量

| 项 | 内容 |
|---|---|
| 假设 | 543 中 161 条（96 题/535 事件）是 remap 后 shell=1 命中、shell=2 零命中的 expression gate 形态；把编译期中心查询从 shell=2 降到 shell=1，可能让其中一部分编译成功 |
| 固定输入 | 同本审计 F4 重建、同一 catalog、同一 compiler、RDKit 2026.03.5；只改 `_CENTER_QUERY_SHELL` 的编译期取值（隔离副本/patch，不改冻结源码） |
| 唯一变量 | center query shell：2（基线）vs 1；同批候选、同编译器、同评测面 |
| 正控 | 368 条已调度 spec 在 shell=1 下**预期**仍 368/368 编译成功（shell=1 匹配集是 shell=2 的超集；但更多匹配可能引入歧义/截断，故这是停点而非数学保证）；234 applied + 134 no-remap 的 target 必须不变 |
| 真实错误负控 | 223 条 no_gap tnc 必须仍拒绝；8 条 real_missing 必须仍拒绝（shell=1 也零命中）；合成“中心确实不在底物”必须仍 absent；543 中 382 条 shell=1 零命中的行必须仍拒绝 |
| 主读数 | 161 条 expression 行的 compiled / still-rejected / new reason；其中 **69 行/37 题**（池内无锚）是潜在新增供给，**92 行/59 题**（池内已有锚）是冗余对照；全 298 题新增/损失/净增候选数 |
| 停点 | 368 正控任一条 loss；8 real_missing 或 223 no_gap 负控翻 present；shell=1 新放行的候选没有化学正控；候选成员/顺序改变但未升 pool policy 版本 |
| 分母 | 161 / 96 / 535（expression）；69 / 37（潜在新增子集）；92 / 59（冗余子集）；543 / 164 / 920；368 / 205 / 1130；223 no_gap；8 real_missing |
| 可证伪形态 | shell=1 无新增 compiled ⇒ “expression gate 是编译表达瓶颈”被推翻；有新增 compiled 但负控失守 ⇒ 现门是保护性的，不改；有新增 compiled 且正负控全过 ⇒ 才进入新 pool policy 预注册 |
| 结论（本轮） | **值得做“测量级”立项，不值得直接改门**：它是 543 中唯一有清晰正负控、且存在 69 行/37 题潜在新增供给的表达面；但 92/161 行是冗余，不能按 161 条推收益 |

### 8.3 不立项/后置的部分

- **不按 543 条数立项**：344/543 行所在题已有池内锚；252 条 in_pool 行本身
  不是供给缺口。
- **不按 122 not_retrieved 直接立项**：这 122 条 remap 后 shell=1 也零命中，
  E-E 覆盖不到；它们需要 O2 E-B 的检索缺路定位（阈值/排名/top-k）。E-E 覆盖的
  是另一批 69 行（67 有 catalog 锚但未进池 + 2 无 catalog 锚）的 expression 行，
  两者不要混成同一分母。
- **不按 8 real_missing 立资产扩建项**：数量小且化学真值（D3）unknown；
  不能以 8 行反推资产投资额。
- **不把 134 的 32 条当缺陷修**：它们当前编译成功；强制 remap 是规则研究，
  不是 bug fix。

## 9. 不做什么及反证

| 不做 | 反证（本轮实测） |
|---|---|
| **不要全局放宽 `no_alignment`** | 543 中 533 行底物在 catalog 有 shell=2 锚；344 行所在题池内已有锚；189 行锚未进池；10 行无锚。全局放宽会把“检索缺路/资产无锚”混在一起，且没有负控 |
| **不要把 543 当“可回收 543 条/题”** | 543 是候选行；164 题中 40 题 hit@1、62 题 strict；252 条 in_pool 行所在题已有锚；543 不是净收益 |
| **不要把“remap 诱导 100%”写成“remap 造成 543 条损失”** | remap-off 的对照是 `transform_no_change` 拒绝；0/543 有“本来可编译”的反事实 |
| **不要把 134 当 remap 欠账** | 134 = F5-pass compiled 已调度；102 no_gap，32 规则边界但当前编译成功；0 无模板/无底物；0 触发但编译失败 |
| **不要强制 remap 134 的 32 条后直接上线** | 强制 remap 会改变 map 号；32 条当前 target 精确；无化学评审前不能改 spec 身份 |
| **不要把 543 与 864 相加** | 行交集 0，但题交集 135、事件交集 752；543+864=1407 行，题并集只有 223 |
| **不要把 543 加到 162/184/18 上** | 162/184/18 是 864 的子类；与 543 行级交集 0，但题/底物交集非零（not_retrieved 题交集 38、expression 25、real_missing 8） |
| **不要把 134 与 234 的题/事件相加** | 368 spec 可加；题 98+149=247 但并集 205；事件 520+874=1394 但并集 1130 |
| **不要把 242−234 读成 8 题** | 差 8 spec / 3 题 / 2 个新题（NC-9）/ 0 事件 |
| **不要用 0 removed 证明 remap 化学正确** | `remove_atom=0` 只否定“删原子”；382 条 shell=1 零命中仍可能是 remap 映射偏移（E-D 未做），8 条 real_missing 化学真值 unknown |
| **不要用机械分类替代化学评审** | 161 expression、122 not_retrieved、8 real_missing 都是 RDKit 存在性/门定义判定，不认证化学正确性或机制可行性 |
| **不要用 543 的 8 条 real_missing 推资产投资** | 8 行/8 题，化学级真实缺失（D3）unknown；O2 的 18 条也不是投资额 |

## 10. 未知清单（不估算）

1. **8 条 real_missing 的化学真值（D3）**：全 catalog 无 shell=2 锚是机械事实；
   “底物化学上是否真的不需要该中心”仍需化学评审/金标。
2. **189 行/55 题“锚存在但未进池”的检索缺路细节**：阈值挡、排名深、还是
   相似度键不命中；本轮只能测“池内有没有”，不能测“为什么没进”。O2 E-B 承接。
3. **161 条 expression 的 shell=1 编译净效果**：其中 69 行/37 题可能新增供给，
   92 行/59 题冗余；是否有新 compiled、是否化学正确，需 E-E。
4. **32 条规则边界 spec 强制 remap 后的 spec 变化**：target/edit/alignment 是否
   改变、是否仍合法，需 E-D + 化学评审。
5. **543 中 remap 补 map 的化学正确性**：0 removed 只是机械不变量；补的 map
   是否对应正确原子，未评审。
6. **344 条 in_pool 行为什么仍被拒**：同题池内已有其它锚，但选中模板仍
   no_alignment；是模板质量/映射问题，不是供给缺口。未做逐条化学评审。
   其中 8 条是 `partial`（锚数 >500 截断），池内命中检查不完整。
7. **2 条 expression 且 any_s2=0 的行**：shell=1 命中但全 catalog 无 shell=2
   锚；是 expression 还是资产边缘，需化学评审。
8. **21 个 543-only 底物的 O2 类归属**：本轮扫描给出 any_s2/any_s1，但 O2 的
   864 类没有覆盖这些底物；O2 交叉类 unknown。
9. **148 个重复 record_id 的 occurrence 语义**：543 中 32 行在“F4 hash + f5 defer
   + compile no_alignment”三条件下仍有 2–4 个 occurrence 同时满足，本轮取确定性
   第一条；这 32 行的唯一模板身份 unknown。本审计只覆盖 analog；corpus/
   recorded 通道是否受 resolve last-wins vs 检索多 occurrence 影响，未审计。
10. **候选级→事件/题级归因**：事件是题级上下文，不是候选级贡献；543 的 920
    事件不能写成“543 条候选造成 920 事件损失”。
11. **任何 hit 回收/净增**：需模型运行与评分实验；不在 P3 本轮。
12. **223 条 no_gap 是否可被另一种 remap 规则救**：当前规则无缺口；换规则是
    新契约，不是触发开关，需预注册与化学评审。

## 11. 边界声明

- 本报告是**只读诊断**：未改代码、未改判据、未写批根/代码树、未调模型、
  未 push、未读金标/题面/`reference_graphs`/`env`/key/封存逐题 payload 化学正文。
- 报告与证据目录**零化学串**：化学内容只以 sha256/record_key/计数/状态码出现；
  逐候选表的全部列均为标识符/哈希/计数/状态码。
- 代码身份：回放用 HPC `~/EnzymeAgent/v43cTH`，5 个关键文件与本仓 r2 提交
  `c9c6c7a` 逐字节同 sha256；catalog sha256 与 `build_identity` 程序内核对一致。
- 所有“in_pool/not_retrieved/real_missing/expression”都是**资产级/门定义级机械
  判定**（RDKit 子结构存在性 + 同题池成员检查），不认证化学正确性或机制可行性。
- 不替 CC/老师拍板：E-D/E-E 是否立项、shell 是否放宽、remap 规则是否改、
  资产是否扩建，均待拍板；本报告不预注册、不承诺收益、不把 543/134 当回收空间。

## 附录 A：证据清单（`docs/review_evidence/p3_o3_compiler543_remap134_2026-10-23/`）

| 文件 | 内容 |
|---|---|
| `SHA256SUMS` | 本目录全部文件哈希 |
| `provenance.json` | HPC/代码/输入哈希、环境、命令、边界 |
| `scripts/p3o3_s1_extract_denominators.py` | 543/134/234/242/368 分母复现 + payload 白名单投影（HPC stdout） |
| `scripts/p3o3_s2_replay.py` | 1548 F5-defer + 368 已调度 spec 同参回放；543 分类；全 catalog 锚扫描；occurrence 消歧 |
| `scripts/p3o3_s2c_controls.py` | 合成正负控 + 248 occurrence 的 remap 不删原子/幂等不变量 |
| `scripts/p3o3_s2d_occurrence_ambiguity.py` | 543 行 occurrence 身份歧义计数（hash+f5+compile reason 三条件） |
| `scripts/p3o3_s3_local_join.py` | 本地 join：分类 × 题/事件/hit/strict + O2/P2 对账 + CSV |
| `logs/s1_rows.jsonl` | 聚合 + 543 行 + 368 spec（无化学串） |
| `logs/s2_replay.jsonl` | 聚合 + 1543 tnc 行 + 543 分类行 + 368 已调度回放行 |
| `logs/s2c_controls.jsonl` | 4 项合成控 + 248 occurrence 不变量 |
| `logs/s2d_occurrence_ambiguity.jsonl` | 543 行 occurrence 命中分布（1/2/3/4 个）与 32 行歧义明细 |
| `logs/s3_summary.txt` / `logs/s3_stderr.txt` | 本地 join 输出/错误（stderr 空） |
| `compiler543_rows_classified.csv` | 逐候选表（qid/record_key/hash/路由/分类/计数；零化学串） |
| `remap134_specs_classified.csv` | 134 条逐 spec 表（qid/key/tref/分类/pre-flight/remap 状态/compile/target 哈希） |
| `scheduled_analog_368.csv` | 368 条已调度 analog spec 全表 |
| `qid_denominators.csv` | 各集合题/事件/hit/strict/partial/unmatched |
| `s3_summary.json` | 分类分母、资产轴/ shell 轴、交叉对账、controls、closure |

## 附录 B：关键等式闭合

- **543** = 161 expression + 252 in_pool + 122 not_retrieved + 5 strong + 3 weak（行级）
- **543** = 344 in_pool_asset + 189 not_in_pool_asset + 10 no_anchor（行级，题集互斥）
- **164** = 99 + 55 + 10（资产轴题级互斥）；**920** = 552 + 326 + 42（事件级互斥）
- **1548** = 1543 tnc + 5 alignment_limit（F5 defer）
- **1543** = 1320 remap applied + 223 no_gap
- **1320** = 242 compiled + 272 merged + 3 truncated + 543 no_alignment + 260 other reject
- **368** = 234 applied + 134 no-remap（已调度 analog spec）
- **242** = 234 scheduled applied + 8 unscheduled compiled
- **376** = 242 F5-defer compiled + 134 F5-pass compiled
- **205** = 98（134 题）+ 149（234 题）− 42（题交集）
- **1130** = 520（134 事件）+ 874（234 事件）− 264（事件交集）
- **231**（manifest `transform_no_change`）= 223 analog no_gap + 8 corpus
- **864** = 500 + 162 + 184 + 18（O2，行级互斥；与 543 行级交集 0）
- **1245** = 920（543 事件）+ 1077（864 事件）− 752（题交集事件）