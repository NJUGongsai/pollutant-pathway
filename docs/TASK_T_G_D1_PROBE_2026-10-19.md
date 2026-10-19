# TASK — T-G Step D1 交集探针 + 模板映射完整性面侦察（执行任务书，2026-10-19）

> **状态**：执行任务书（可直接派子代理；自包含）。
> **题域标签**：**298 = RHEA 通用酶学 / 已见题（post-hoc）**；全部数字挂该标签，不外推 dev。
> **性质**：**探针 ≠ 预注册 ≠ 成绩**。零模型 / 零网络 / 零 LLM / 零费用。
> **上游**：`docs/TASK_T_G_FIX_ENGINEERING_2026-10-19.md` §3 Step D1（D1.1 探针 + D1.2 定刀）；
> 移交书 `docs/HANDOFF_TG_NEXT_PHASE_2026-10-19.md` §3.1。
> **基线**：HEAD 以执行时 `git rev-parse HEAD` 实测记录（写单时 `26ad119`，v4.3 分支）。

---

## 0. 背景（先读这段）

### 0.1 D1 要回答什么

A 通道（analog | no_alignment）误拒 56 件 pass 中有 **17 件**死于「模板映射不完整
（`transform_no_change`）」——即模板改动原子未带 map 号/半映射键，编译器在变换提取层即拒。
原设想的 D 线修法（rxnmapper 扩检索）在 D 探针已被证伪不对症；D1 改为：
**先探「rxnmapper 模板资产（32,832 条）与这 17 件的交集」，再定刀**——
交集有料→接线；交集≈0→转「确定性重映射工单」（对 EAWAG/enviPath 侧模板补映射）。

### 0.2 已由主窗口预查的事实（探针须机械复验，不得照抄）

| # | 事实 | 预查读数 | 探针动作 |
|---|---|---|---|
| 1 | frame_A 全抽样框 | 1,886 行 = **927 rhea + 959 env**（前缀 `tpl-rhea:`/`tpl-env:`） | 机械复算并写死 |
| 2 | rxnmapper 资产来源 | `reports/ppv1_s5b/d_probe_rxnmapper_2026-10-14/rxnmapper_templates_v1.jsonl`，**32,832 行、全部 rhea**（record_id 前缀唯一值 `rhea`） | 机械复算 |
| 3 | 17 件清单 | 15 env（EAWAG-BBD/SEDIMENT/SLUDGE）+ 2 rhea（`tpl-rhea:56149`、`tpl-rhea:36768`）——权威源=下表 case_id 清单 | 逐件对账 |
| 4 | 2 件 rhea 是否在资产内 | 均**不在**（资产覆盖 32,832 个 rhea id，10001–86965 区间但跳过这两件） | 机械复验 + 查原因（见任务 B） |
| 5 | 资产构建时排除面 | D 探针报告 §2.1：输入 37,098 行未映射 RHEA 行 → 映射成功 36,064 → **变换无变化排除 2,870** → QC 不过 358 → 超长 1,034 → 入库 32,832 | 查 2 件 rhea 的逐行映射结局归类 |

**17 件 case_id 权威清单**（与 `reports/ppv1_s5b/t_g_fix_2026-10-19/c2_probe/c2_probe_data.json`
`material.rows` 中 `judgement=="pass_expected" ∧ compile_reason=="transform_no_change"` 逐件一致）：

```
a-079a94f836d4f12f  a-0120308e05d147c6  a-2189433704e8d113  a-9039900ff1eb5891
a-075c0a3e10c5426f  a-4aae40f6257e0215  a-e7ecbab2b82004d8  a-070d5e433a26a408
a-a81b1aa0d4424778  a-3b5af887dda5ad41  a-1073f907dcd9bac0  a-aabe51304206920a
a-9014ac66da35eb39  a-190c2056ba5fd049  a-e9ef67eda2b805b6  a-4c01d0c5123aff2d
a-e03c5139816f99b9
```

（对应 record_key：`tpl-env:EAWAG-BBD:bt0349#r0152` / `tpl-env:EAWAG-BBD:bt0051#r0321` /
`tpl-env:EAWAG-BBD:bt0318#r1457` / `tpl-env:EAWAG-SEDIMENT:8f520f13-d1be-4542-8bb5-c0b147448c88` /
`tpl-env:EAWAG-SLUDGE:c3379514-8e5b-4d3d-9c38-b7ed3d53f484` / `tpl-env:EAWAG-BBD:bt0014#r0282` /
`tpl-env:EAWAG-BBD:bt0014#r1727` / `tpl-env:EAWAG-SLUDGE:19f04c3b-dacd-4413-a785-833aebd57962` /
`tpl-env:EAWAG-SLUDGE:efeb6775-fe7d-4252-a24f-948d7385d700` / `tpl-env:EAWAG-BBD:bt0014#r1623` /
`tpl-env:EAWAG-BBD:bt0014#r1727` / `tpl-env:EAWAG-BBD:bt0040#r1622` /
`tpl-env:EAWAG-SEDIMENT:f20c9b33-d836-45d0-9b86-6bb26936cc1f` /
`tpl-env:EAWAG-SLUDGE:19f04c3b-dacd-4413-a785-833aebd57962` / `tpl-env:EAWAG-BBD:bt0014#r1623` /
`tpl-rhea:56149` / `tpl-rhea:36768`。）

### 0.3 机件清单（现成可复用）

| 件 | 路径 | 用法 |
|---|---|---|
| 全抽样框 | `reports/ppv1_s5b/p0_1_initiation_input_2026-10-17/frame_A.json` | 1,886 行；字段 row_id/question_id/record_key/channel/reason/substrate_smiles/dedupe_key |
| 材料包（155） | 同目录 `material_packs_A.json` | record_content.templates（全部模板，非仅首条） |
| 抽样清单（155） | 同目录 `sampled_A.json` | 与 frame 的 row_id 对账 |
| 判读读数 | 同目录 `judgement_glmsub_v3_A_batch{1..5}.json` + `judgement_pass_confirm_codex.json` | pass_expected/reject_correct/uncertain |
| 记录内容解析 | `reports/ppv1_s5b/chain13_glm/analysis/c_redesign_base_tables.py`（`CBT.resolve(channel, record_key)`，材料包同源） | frame 全框模板解析 |
| C2 探针（复刻先例） | `reports/ppv1_s5b/t_g_fix_2026-10-19/c2_probe/c2_death_cause_probe.py`（§材料包段 466-570 行的 API 用法为权威口径） | 复刻机械结局 |
| 编译器 | `src/pathway_v43/pollutant/s5b_compiler.py`：`template_elements_fit`(:169)、`extract_mapped_transform`(:296)、`compile_donor_template`(:1172) | 只读 import |
| 供给函数 | `src/pathway_v43/pollutant/s5b_builder.py`：`analog_cosub_supply`、`_cosub_strip_map` | 只读 import |
| rxnmapper 资产 | `reports/ppv1_s5b/d_probe_rxnmapper_2026-10-14/rxnmapper_templates_v1.jsonl`（32,832 行；字段 mapped_lhs/mapped_rhs/record_id/center_atoms/qc_flags/probe_meta） | 只读 |
| rxnmapper 逐行映射结果 | 同目录 `tmp/results_rhea_mapped.jsonl`（37,098 行，含失败分类/耗时） | 只读；查 2 件 rhea |
| 语料源 | `assets/v3_reactions/corpus_env/corpus_v1.jsonl`（rxnmapper 输入源：source_type=rhea 且有 reaction_smiles 的未映射行） | 只读；查 2 件 rhea 是否在输入集 |

**复刻口径（与 §0.4 侦察/C2 探针逐字一致，不得改写）**：逐件取 `record_content.templates[0]`；
`analog_cosub_supply(mapped_lhs, mapped_rhs, substrate_smiles)` → 若 status==supply 且 supply 非空
则 `sub2 = substrate + "." + "." .join(次组分)`，否则 `sub2 = substrate`；`gate_raw =
template_elements_fit(lhs, substrate)`；`gate2 = template_elements_fit(lhs, sub2)`；
`compile_donor_template(mapped_lhs=lhs, mapped_rhs=rhs, center_atoms=[], substrate_smiles=sub2,
record_id=str(t["record_id"]))`；结局 = `status=="compiled"` 或 `reason` 原样。

---

## 1. 任务 A — 全抽样框 1,886 件机械结局分桶（D1.1 主账）

**做什么**：对 frame_A 全部 1,886 行，按上表复刻口径逐行定「机械结局」（绕过前置门的直编口径，
与 §0.4/C2 探针同源），产**全框 transform_no_change 占比与来源分桶**。

**逐行输出（机读）**：row_id、record_key、source（rhea/env）、env_sub（env 二级前缀：
`EAWAG-BBD`/`EAWAG-SEDIMENT`/`EAWAG-SLUDGE`/其它，按 `tpl-env:` 后第一段）、n_templates、
supply_status、gate_raw、gate2、mechanical_outcome（`compiled` 或 reason 原样）。

**汇总（必须给）**：
1. 全框机械结局直方图；**transform_no_change 行数 ÷ 1,886**（占比）；
2. 同上按 source 分列（rhea/env 各自的行数、占比）；env 再按 env_sub 分列；
3. 与 §0.4/C2 探针锚对账：抽样清单（sampled_A.json 的 155 行 row_id 集合）子集上
   **必须逐项复现 `89 no_alignment + 66 transform_no_change`**（155 件直编结局口径），
   且子集中的 56 件 pass（judgement==pass_expected）**必须复现 `39 no_alignment + 17
   transform_no_change`**——**对不上即停，报回主窗口，不得自圆**；
4. 多模板记录（n_templates>1）清单：n 条、其模板间结局是否一致（一致性统计）；
   主账仍按 templates[0]，多模板面另列。

**样本量说明**：155 → 全框的推广只是「抽样读数的全框化」，两个数都要报，不得混。

## 2. 任务 B — 17 件 × rxnmapper 资产交集（D1.1 定刀依据）

**做什么**：对 §0.2 清单的 17 件逐一查三处：

1. `rxnmapper_templates_v1.jsonl` 按 `record_id` 全等查（17 件的 record_id = record_key 去掉
   `tpl-` 前缀：`rhea:56149`、`EAWAG-BBD:bt0349#r0152`、…）；输出逐件命中数；
2. 对 2 件 rhea：查 `assets/v3_reactions/corpus_env/corpus_v1.jsonl`——
   （a）是否在 rxnmapper 输入集（source_type=rhea ∧ 有 reaction_smiles ∧ 未映射）；
   （b）在 `tmp/results_rhea_mapped.jsonl` 中的逐行结局（成功/超长/变换无变化排除/QC 不过/无映射侧）；
   （c）若都不在：查它们是否已带原生映射（已映射行不进 rxnmapper 输入集），并如实记录
   「不在输入集」与「输入集内被排除」的区别；
3. 对 15 件 env：机械复验 `rxnmapper_templates_v1.jsonl` 的 record_id 前缀分布（必须=纯 rhea），
   输出「D 库覆盖面不含 env 前缀」的机读断言。

**汇总**：交集 = **同 record 模板命中件数**（预期 0，须机械证实）；如 >0，逐件给出其模板的
`extract_mapped_transform` / 编译结局（用 0.3 复刻口径）。**交集≈0 时明确写「rxnmapper 库
不覆盖此 17 件面」**（含 15 env 无交集 + 2 rhea 各自的原因归类）。

## 3. 任务 C — 17 件映射缺口的结构画像（定刀输入，仅聚合）

对 17 件（可加全框 transform_no_change 面）：解析 `mapped_lhs`/`mapped_rhs`，聚合统计
**未映射原子的变化结构**（只报计数与桶名，不在报告里出现结构串）：

- 未映射原子数（lhs/rhs 各自）、未映射原子连通分量的**附着签名分类**：
  `one_side_only`（只在一侧出现的未映射组分——离场/新增）、`both_sides`（两侧都有、需对应）、
  `mixed`；
- 半映射键数（键一端带 map 一端不带）、涉及 map 号的变更原子上的半映射边数；
- 每件的「最小补映射承诺」分桶：`removed_group_only` / `added_group_only` / `substituent_swap`
  / `ring_change` / `other`（规则化定义见下，桶名+计数即可）。

规则化定义（子代理按此实现，不得自由发挥）：对 `U_L`（lhs 未映射原子）与 `U_R`（rhs 未映射原子）
分别求连通分量（分量内仅经未映射原子相连）；每个分量签名 =（元素多重集，边界原子元素及
其映射邻居 map 号集合的排序元组）；按签名在两侧配对：
- 仅 U_L 有分量 ⇒ `removed`；仅 U_R 有 ⇒ `added`；两侧各一分量签名相等 ⇒ `matched`；
- 件级桶：只含 removed ⇒ `removed_group_only`；只含 added ⇒ `added_group_only`；
  含 matched 且 matched 分量与已映射骨架相接于同一保留原子 ⇒ `substituent_swap`（若两侧
  签名相等分量的原子数≥3 或成环 ⇒ `ring_change`）；其余 ⇒ `other`。

## 4. 任务 D — 干跑原型：确定性补映射 v0（只读、内存内，不写资产）

**目的**：给 D1.2 定刀一个**上限预览**——若对未映射变化原子做规则级补映射，
`extract_mapped_transform` 能救回多少（**只报变换提取层迁移，不宣称编译/收益**）。

**v0 规则（严格按此，不得扩展）**：
1. 解析双侧；对任务 C 分到 `removed` 的 U_L 分量：给其全部原子分配新 map 号（从
   `max(现有 map ∪ {0}) + 1` 起递增，顺序=按原子索引确定性排序），仅写回 lhs 侧；
2. 对 `added` 的 U_R 分量对称处理（仅写回 rhs 侧）；
3. `matched`（两侧对应）分量**不处理**（v0 无对应规则；逐件计数「需要对应规则」）；
4. 重新调用 `extract_mapped_transform(mapped_lhs', mapped_rhs')`：
   - 不再抛 `transform_no_change` ⇒ 记 `extract_recovered`（记录新变化的桶：
     有 bond_changes/added/removed 哪些）；
   - 仍抛 ⇒ 记原样 reason；其他 S5bCompileError（如 `transform_unmapped`）记原样；
   - 解析失败 ⇒ `fail_closed` 计数。

**干跑对象**：① 17 件；② 155 件样本中的全部 transform_no_change 件（66 件，含 reject/uncertain，
用判读类别分组报数）；③ 全框 transform_no_change 件（任务 A 产物）。三档分开报。

**负控纪律**：干跑只改内存中字符串副本；**不写任何资产文件**；对 `judgement==reject_correct`
的件，即使 extract_recovered 也**不得**表述为收益（其化学该拒，后续层必拒或负控见下）。

**报告纪律**：任务 D 的所有数字标注「**原型干跑 ≠ 修复 ≠ 编译**」，只作 D1.2 定刀输入。

---

## 5. 验收锚（对不上即停）

| 锚 | 期望值 | 来源 |
|---|---|---|
| frame_A 行数 | 1,886（927 rhea + 959 env） | 主窗口预查 + 本任务机械复算 |
| 155 子集机械结局 | `89 no_alignment + 66 transform_no_change`（**s5b-compiler-3 口径**） | §0.4 / C2 探针（`c2_probe_data.json` anchors） |
| 56 pass 子集 | `39 + 17`（**s5b-compiler-3 口径**） | 同上 |

> **执行后订正（2026-10-19 晚，D1 探针实测）**：上述两条锚的 `no_alignment` 分量是
> **C2 R2'（`838f307`，s5b-compiler-4）落地前**的读数；R2' 用 F5 中心锚定准入替换旧整侧
> 元素账准入后，155 子集在 HEAD 口径为 `62 no_alignment + 66 transform_no_change`、
> 56 pass 为 `22 + 17`（漂移行迁往 charge/stereo/compiled，逐行披露在
> `d1_probe_summary.md`）。**`transform_no_change` 分量（66 / 17）与 17 件清单两口径完全一致**
> ⇒ 本任务 B/C/D 结论不受该漂移影响；探针已用 `838f307^` 隔离快照复证 compiler-3 口径
> （`d1_probe_data.json` → `anchor_caliber_crosscheck`）。后续任务书引用本 §5 时以该订正为准。
| 17 件清单 | 与 §0.2 逐件一致（case_id 全等） | c2_probe_data.json |
| rxnmapper 资产 | 32,832 行、record_id 前缀唯一值 = {rhea} | 机械复算 |
| 17 件 × 资产交集 | 逐件命中数（预期 0；>0 则给逐件结局） | 本任务 |
| 任务 D 全框 | 逐件态 + 三档分组计数 | 本任务 |

## 6. 红线与纪律（逐条）

1. **零模型/零网络/零 LLM**；不调用任何外部服务。
2. 只读 import `src/`；**不改 src/tests/configs/assets**（任务 D 只在内存改副本）。
3. 产物只写 `reports/ppv1_s5b/t_g_fix_2026-10-19/d1_probe/`（gitignored），不写别处；
   `PYTHONDONTWRITEBYTECODE=1`；如跑 pytest 加 `-p no:cacheprovider`。
4. 金标/题面零接触：不读任何含金标/题面的文件；输出报告 md **零结构串**（机读 json 只含
   row_id/record_key/计数/桶名/map 号，不含 SMILES 串）。
5. 记录实际 HEAD（`git rev-parse HEAD`）、分支、命令、输入文件 sha256（frame_A、
   material_packs_A、rxnmapper 资产、corpus_v1）。
6. 对不上锚 ⇒ **停**，把差异原样报回，不得静默改口径。
7. 提交纪律：本探针**不提交**（产物 gitignored；报告随下一轮由主窗口决定）。

## 7. 产物与回传

**产物**（`reports/ppv1_s5b/t_g_fix_2026-10-19/d1_probe/`）：
- `d1_probe.py`（脚本，含运行入口与随机性零依赖说明）；
- `d1_probe_data.json`（机读：任务 A 全框逐行 + 任务 B 逐件 + 任务 C/D 聚合）；
- `d1_probe_summary.md`（报告：结论先行 + 锚对账表 + 分桶表 + 任务 D 上限预览 + 口径与边界）；
- `d1_probe_run.log`（运行日志，含 HEAD/命令/sha256）。

**回传三件套（给主窗口）**：① 行数/清单集合（全框分桶计数 + 17 件逐件交集结果）；
② 锚对账结果（全对/差异逐项）；③ 任务 D 上限预览数字（三档分组）。
**下一步选项**：按交集结果给「接线 / 确定性重映射工单」的倾向建议（附数字依据），
**决定权在主窗口/CC，不在子代理**。