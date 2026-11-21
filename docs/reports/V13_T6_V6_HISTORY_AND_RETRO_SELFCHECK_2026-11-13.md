# V13 T6：v6 口径历史复算 + retro 自记录判据核查（2026-11-13）

> **一句话结论**：T6-1 完成——5 个历史配置 × 2 域按 v4 / v6 双口径重算（另附 T2-G 六臂 12 批），
> **全部 `lost = 0`**，v6 相对 v4 在 `[biosysmodb121]` 提升 `+29…+36` 题、`[dev-298]` 提升 `+1…+3` 题，
> 与 v6 讨论稿既有数字一致。T6-2 完成——`check_retro_self_record` **方向没有判反**
> （RetroRules 对同一反应双向各生成模板，生产路径按「底物匹配 lhs」取候选，判据与消费方式一致），
> 真实缺陷是**单侧不完整**（缺反向判定 + 要求全部金标组分）；对该判据的历史 ex-self 数字
> **实测影响为 0**（受影响题集与命中集不相交）。

## 0. 结论摘要

| 结论项 | 判定 | 依据 |
| :--- | :--- | :--- |
| T6-1 双口径复算 | 完成，10 个主批 + 12 个附录批全部跑通 | §3 / §4，每批 `lost = 0` |
| v6 是否优于 v4 | 是，且只在披露口径上变化，严格 v4 侧逐位等于归档 `metrics_v4.json` | §3 表 |
| Exp-1b 调参集部分 | **不可重算**：三臂为 8 题纯合成题卷，与调参集交集 0 | §5.1 |
| Exp-2 调参集部分 | **不可重算**：本机无批次根（只有聚合与逐题标记产物） | §5.2 |
| `check_retro_self_record` 是否判反 | **否**（T5 报告「方向相反」的表述需更正） | §6.3 |
| 真实缺陷 | 单侧不完整：缺反向判定；`gold ⊆ rhs` 要求全部金标组分 | §6.4 |
| 历史 ex-self 数字影响 | **0**（POOL_COVERAGE 27 / 31 与 v1.1、v1.2 的 ex-self 数均不需重算） | §6.5 |
| 是否改了源码 | 没有（任务书要求只核查） | §7 |

## 1. 范围与红线

- 任务书：`dependingv43/docs/tasks/active/TASK_V13_42PCT_2026-11-13.md` §19（T6）。
- **只取调参集题**：所有被重算的批次本身就是调参集批次（B121 261 题 / 298 196 题），
  未触碰任何留出集批次、未重算全集历史基线。
- **零 LLM 调用**：本报告全部数字来自本机既有 run 产物的离线重放判分（`score_disclosure_v4cn.py`
  只读 `cases/` + `native_export/`）。
- 未读取 `~/.ppv1_holdout_token`，未访问金标 token，未改动封存 run。
- 逐题明细只落 `reports/manual_review/v13_t6_2026-11-13/`（gitignored）；本报告零 SMILES、
  零私有题号前缀（受影响的 6 道题用 `298-P1…P3` / `298-R1…R3` 标签指代，
  映射表在 `reports/manual_review/v13_t6_2026-11-13/T6_2_qid_labels.tsv`）。
- 冻结判分器 SHA256 前后一致：`evaluation.py = ac38ea39…63f41`、
  `s5b_scoring.py = 5a677550…456d`（与 `v13-base` 无差异）。
- 分支：`ocagent/261113-v13-t6-d6f5`（从 `ocagent/261113-v13-t5-b0f5` tip `a01deda` 切出；
  只本地 commit，不 merge / 不 push）。
- 未执行任何删除动作。

## 2. 口径定义

| 口径 | 实现 | 说明 |
| :--- | :--- | :--- |
| v4（严格） | 归档 `metrics_v4.json` 的 `per_qid[].product_hit.rank` | 冻结判分器 `ppv1-criteria-v4`，主产物身份 + 底物身份严格匹配；两侧都做旧版质子化改写 |
| v6（加固披露口径） | `scripts/eval/score_disclosure_v4cn.py` 的 `v4cn` 块 | 质子化**不变身份**：只对「净电荷不变」的质子化/去质子化做归一；小分子排除清单照现行（碳酸体系、NH₃/NH₄⁺、CN⁻/HCN、SCN⁻、H⁺/H₃O⁺ 不参与归一）；`salt_not_normalized` / `net_charge_changed` / `invariant_broken` 一律不判命中 |

- v6 侧同时校验「严格 v4 不漂移」：脚本自算的 `strict_v4` 与归档 `metrics_v4.json` 逐批核对一致
  （差异 0 题），因此表中 v4 列可以直接读归档值。
- 表中「Δ@1」= v6 hit@1 − v4 hit@1；「新命中 / 丢失」取翻转文件的 `n_new_hit` / `n_lost_hit`。

## 3. T6-1 主表（5 配置 × 2 域，只含调参集）

### 3.1 `[biosysmodb121]`，N = 261

| 配置 | 批次根 | code identity（前 16） | 回复来源 | v4 hit@1/@3/@5 | v6 hit@1/@3/@5 | Δ@1 | 新命中 / 丢失 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| v1.0（v44-Next base） | `v44/reports/ppv1_s5b/v44_next_tuning_20261110/batch_b121_tuning_v44next` | `0dd58d25336f240b` | 当时新采样 | 57 / 76 / 77 | **86 / 111 / 114** | **+29** | 37 / 0 |
| v1.1 存档 | `v44/reports/ppv1_s5b/v44_next_v1_1_tuning_20261110/batch_b121_tuning_v44next` | `5daaabe34a6400cc` | 新采样（与 v1.0 模型回复 0/261 相同） | 54 / 75 / 87 | **90 / 111 / 122** | **+36** | 35 / 0 |
| v1.2 存档 | `v44/reports/ppv1_s5b/v44_next_v1_2_tuning_20261110/batch_b121_tuning_v44next_v12` | `cea82d12028a58be` | **100% 复用 v1.1 回复**（261/261 同 sha256） | 66 / 80 / 90 | **99 / 116 / 125** | **+33** | 35 / 0 |
| T2-R 臂 | `v44_v13/reports/ppv1_s5b/v13_t2_tuning_20261113/batch_b121_t2_r_v13` | `c463483f6980d52d` | 新采样（与 v1.1 0/261 相同） | 58 / 78 / 87 | **88 / 114 / 122** | **+30** | 35 / 0 |
| T2-T 臂 | `v44_v13/reports/ppv1_s5b/v13_t2_tuning_20261113/batch_b121_t2_t_v13` | `c463483f6980d52d` | 新采样（与 R 0/261 相同；R 基础上注入枚举候选） | 61 / 82 / 88 | **92 / 117 / 124** | **+31** | 36 / 0 |

### 3.2 `[dev-298]`，N = 196

| 配置 | 批次根 | code identity（前 16） | 回复来源 | v4 hit@1/@3/@5 | v6 hit@1/@3/@5 | Δ@1 | 新命中 / 丢失 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| v1.0（v44-Next base） | `v44/reports/ppv1_s5b/v44_next_tuning_20261110/batch_298_tuning_v44next` | `0dd58d25336f240b` | 当时新采样 | 73 / 98 / 103 | **74 / 102 / 107** | **+1** | 4 / 0 |
| v1.1 存档 | `v44/reports/ppv1_s5b/v44_next_v1_1_tuning_20261110/batch_298_tuning_v44next` | `5daaabe34a6400cc` | 新采样 | 77 / 102 / 108 | **78 / 105 / 111** | **+1** | 3 / 0 |
| v1.2 存档 | `v44/reports/ppv1_s5b/v44_next_v1_2_tuning_20261110/batch_298_tuning_v44next_v12` | `cea82d12028a58be` | **100% 复用 v1.1 回复**（196/196 同 sha256） | 91 / 113 / 117 | **94 / 118 / 122** | **+3** | 5 / 0 |
| T2-R 臂 | `v44_v13/reports/ppv1_s5b/v13_t2_tuning_20261113/batch_298_t2_r_v13` | `c463483f6980d52d` | 新采样（与 v1.1 0/196 相同） | 82 / 110 / 114 | **84 / 113 / 117** | **+2** | 3 / 0 |
| T2-T 臂 | `v44_v13/reports/ppv1_s5b/v13_t2_tuning_20261113/batch_298_t2_t_v13` | `c463483f6980d52d` | 新采样（与 R 0/196 相同） | 84 / 111 / 119 | **86 / 115 / 123** | **+2** | 4 / 0 |

### 3.3 读表提示

1. **v1.2 复用旧回复**：v1.2 与 v1.1 的 `s5b_responses/*.json` 中 `sha256` 字段两域全量相同
   （261/261、196/196），说明 v1.2 只改了建池/排序机制，模型回复是重放旧缓存；
   它的 v4 提升（54→66、77→91）来自候选池变化而非重新采样。
2. **回复复用与 v6 增量无交互**：v1.2 的 v6 增量（+33 / +3）与 v1.1（+36 / +1）量级相当，
   说明 v6 提升主要来自判据侧对质子化写法的归一，而不是某一次采样的偶然。
3. **严格侧未漂移**：表中 v4 列与各批归档 `metrics_v4.json` 的 `matched_product_hit_caliber`
   逐位相同（脚本自算 strict 亦相同）。
4. **两域不可互推**：B121 的增量（+29…+36，相对基数 ~55–66）远大于 298（+1…+3，相对基数 ~73–91）。
   这与 v6 讨论稿的既有观察一致（B121 题面里离子化/质子化写法更普遍）。

## 4. 附录：T2-G 六臂 × 两域（零调用重放，12 批）

来源：`reports/ppv1_s5b/v13_t2g_arms_20261113/<arm>/{batch,runs}`。
`*_on` 臂同时用作**正控**：其严格 v4 与 v6 数字都与 T2 付费批逐位一致。

| 臂 | 域 | v4 hit@1/@3/@5 | v6 hit@1/@3/@5 | Δ@1 | 新命中 / 丢失 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `b121_r_off` | B121 | 56 / 77 / 86 | 88 / 114 / 121 | +32 | 35 / 0 |
| `b121_r_on` | B121 | 58 / 78 / 87 | 88 / 114 / 122 | +30 | 35 / 0 |
| `b121_r_r1on` | B121 | 59 / 78 / 87 | 89 / 114 / 122 | +30 | 35 / 0 |
| `b121_t_off` | B121 | 52 / 80 / 87 | 82 / 115 / 123 | +30 | 36 / 0 |
| `b121_t_on` | B121 | 61 / 82 / 88 | 92 / 117 / 124 | +31 | 36 / 0 |
| `b121_t_r1off` | B121 | 60 / 82 / 88 | 91 / 117 / 124 | +31 | 36 / 0 |
| `298_r_off` | 298 | 72 / 100 / 106 | 73 / 102 / 108 | +1 | 2 / 0 |
| `298_r_on` | 298 | 82 / 110 / 114 | 84 / 113 / 117 | +2 | 3 / 0 |
| `298_r_r1on` | 298 | 82 / 110 / 114 | 84 / 113 / 117 | +2 | 3 / 0 |
| `298_t_off` | 298 | 75 / 104 / 111 | 76 / 106 / 114 | +1 | 3 / 0 |
| `298_t_on` | 298 | 84 / 111 / 119 | 86 / 115 / 123 | +2 | 4 / 0 |
| `298_t_r1off` | 298 | 84 / 111 / 119 | 86 / 115 / 123 | +2 | 4 / 0 |

- 四套 `*_on`（`b121_r_on` / `b121_t_on` / `298_r_on` / `298_t_on`）的 v4 与 v6 数字
  分别等于 §3 中 R / T 两臂的对应数字 → **正控成立**（同一批回复、同一判据实现，跨目录复现）。
- 六臂的 Δ@1 全部落在 +30…+32（B121）与 +1…+2（298），与主表同一量级。

## 5. Exp-1b / Exp-2 为何不可重算

### 5.1 Exp-1b

- 仓内可找到的 Exp-1b 批次根为 `v44/reports/ppv1_s5b/exp1_impl_smoke_2026-11-06b/{arm_a,arm_b,arm_c}/batch`，
  每臂 8 题，题卷来源 `questions.jsonl`。
- 三臂题号的形态是 `EXP1B-SMOKE-Q*`（合成冒烟题），与 B121 261 题、298 196 题的题号集合
  **交集为 0**（三臂均 0/8）。
- 因此「Exp-1b 各臂的调参集部分」为空集，没有可重算的行。同名的
  `exp1b_smoke_qids_{b121,298}.txt` 只是 3 行指针文件，指向调参集里被用来冒烟的真实题，
  它本身不是一个批次根，也没有可判分的 run 产物。

### 5.2 Exp-2

- 本机只有 `v44/reports/manual_review/exp2_hybrid_compile_2026-11-08/`：
  `declared_bucket_per_qid_*_{a,b,c}.json`、`per_qid_flags_*.tsv`、`private_flips_and_qids_*.json`、`holdout_audit/`。
- 这些是**聚合与标记级**产物（declared bucket、flag 表），不含 `batch_manifest.json` /
  `reference_graphs/` / `cases/` / `native_export/`；报告正文亦记载 Exp-2 的实际批次跑在远端 HPC。
- 双口径重算需要「参考图 + 每题原生导出」才能重建候选并判分，故本机无法执行；
  需要用 HPC 侧批次根回传后另开任务。

## 6. T6-2：`check_retro_self_record` 方向核查

### 6.1 位置与语义

- 定义：`src/pathway_v43/services/retro_source.py:1510`（`def check_retro_self_record`）。
- 输入：候选 spec / `RetroDonorRef`，加题目的 `question_source_ids`、`substrate_smiles`、
  `gold_principal_smiles`。
- 判据（两路取或）：
  1. `by_reaction_id`：规则的 `parent_reaction_ids`（`RHEA:xxxx` / `MNXR…`，含跨库同 `TEMPLATE` 映射）
     与题目来源 ID 有交集；
  2. `by_strict_pair`：`substrate` 的严格身份组件集 ⊆ 规则 `lhs` 组件集，**且全部**金标主产物组件
     ⊆ 规则 `rhs` 组件集（`gold_keys <= rhs_keys`）。
- 返回值：`is_self_record` / `by_reaction_id` / `matched_reaction_ids` / `by_strict_pair` /
  `matched_lhs_strict` / `matched_rhs_strict`。

### 6.2 全部调用点

| 位置 | 用途 | 说明 |
| :--- | :--- | :--- |
| `scripts/eval/pool_coverage_eval.py:275` | **唯一生产/评估侧调用** | `_is_self_recorded()` 的 `chan == "retrorules"` 分支；结果写 `is_self_record_gip8` 与 `gip_*_ex_self` |
| `tests/unit/test_retro_source_phase2b.py:206` | 单测：按反应 ID 命中 | 正控 |
| `tests/unit/test_retro_source_phase2b.py:221` | 单测：按严格底物+主产物对命中 | 正控（把规则 lhs 组件当底物、rhs 组件当金标喂入，固定了现有字段语义） |
| `tests/unit/test_retro_source_phase2b.py:232` | 单测：不匹配负控 | 负控 |
| `src/pathway_v43/**` 其他位置 | **无调用者** | 生产链（`s5b_builder` / `compile_retro_ref` / `bridge_occurrence_to_spec`）不调用它；它是离线覆盖率评估专用 |
| `v44/scripts/eval/pool_coverage_eval.py`、`dependingv43/scripts/eval/pool_coverage_eval.py` | 同源副本的同名调用 | 两处历史副本逻辑相同，修改需三处同步（本次不改） |

### 6.3 方向定案：没有判反

三条独立证据：

1. **数据侧**：RetroRules 官方说明「对同一反应的两个方向分别生成模板」
   （引自 `v44_retrorules_archive_20261012/docs/TASK_V44_RETRORULES_INTEGRATION_2026-10-11.md:92`）。
   载入侧（`retro_loader.py`）按 `template_direction=as_stored` 原样入库，**不交换左右侧**。
2. **消费侧**：`bridge_occurrence_to_spec`（`retro_source.py:640` 起，核心在 692 / 734 行）
   与 `compile_retro_ref`（`retro_source.py:999`）都是**用规则 lhs 去匹配题目底物**，再
   `rxn.RunReactants((substrate_mol,))` 朝产物方向实例化。也就是说，池里能出现的 RetroRules 候选
   必然满足「底物 ⊆ lhs」，`by_strict_pair` 的「底物 ⊆ lhs ∧ 金标 ⊆ rhs」正是这条链的实际语义；
   若改成「金标 ⊆ lhs ∧ 底物 ⊆ rhs」，对正向模板会全部判否。
3. **实测侧**：用 134,738 条 rhea 模板对调参集逐题比对
   （`reports/manual_review/v13_t6_2026-11-13/probe_t6_2_direction.py`）：

   | 域 | 正向（底物⊆lhs ∧ 金标⊆rhs） | 反向（金标⊆lhs ∧ 底物⊆rhs） | 并集 |
   | :--- | :--- | :--- | :--- |
   | B121（261 题） | 18 条规则 / **18 题** | 21 条规则 / **18 题** | 18 题 |
   | 298（196 题） | 49 条规则 / **49 题** | 49 条规则 / **48 题** | 52 题 |

   两个方向都能命中同一批记录题 → 说明双向模板都在库里，不是「方向写反」。
   （另测：全库 134,738 条方向化模板中完全镜像对仅 12,460 条/9.2%，但记录题所在反应的两向模板
   都存在——因此「镜像率低」不能反证方向问题，只能说明多数模板来自不同反应。）

**对 T5 报告的更正**：`docs/reports/V13_T5_VERIFIER_REPORT_2026-11-13.md` §3.1 / §4 中
「`check_retro_self_record` 假设的是 lhs=底物/rhs=产物，直接套用会把方向判反」的说法**不成立**，
应在下一轮更正为「判据与生产路径一致，但只覆盖单侧」。T5 自己的验证器采用方向无关的双侧判定
（`scripts/eval/v13_t5_verifiers.py:756` 两侧都试），其结论不受影响。

### 6.4 真实缺陷：单侧不完整（两处）

1. **缺反向判定**：只查「底物⊆lhs ∧ 金标⊆rhs」。若某题在库里只存在反向模板，就会被判成「非自记录」
   （漏检）。
2. **要求全部金标组分**：`gold_keys <= rhs_keys` 是子集判断，多产物题里若规则只覆盖部分金标产物
   （例如小半径局部模板、或共底物未入模板），也会被判成「非自记录」（漏检）。

实测规模（`probe_t6_2_selfrecord.py`，只读 rhea 索引 + 题卷）：

| 域 | 多产物题 | 完整自记录（现判据可抓） | 部分覆盖（现判据漏） | 仅反向（现判据漏） |
| :--- | :--- | :--- | :--- | :--- |
| B121（261） | 0 | 18 题 | **0 题** | **0 题** |
| 298（196） | 28 | 49 题 | **3 题**（P1–P3） | **3 题**（R1–R3） |

- 6 道「仅反向」题的反向规则 lhs 与底物**没有任何组件重合**（`matchable = 0`），
  而生产路径是先「lhs 匹配底物」才执行规则，因此这些规则根本产不出候选。
- 3 道「部分覆盖」题的多产物金标里，规则只覆盖一部分，单条候选无法满足 GIP@all。

### 6.5 对历史 ex-self 数字的影响量级

| 数字来源 | 原值 | 受影响题集与命中集的交集 | 判定 |
| :--- | :--- | :--- | :--- |
| `POOL_COVERAGE_2026-11-09` S4-mnx+rhea `GIP_at_all_ex_self`（B121） | 75 → **27** | 受影响 0 题 | **不变** |
| 同上（298） | 98 → **31** | 6 题在 `dev-298_S4-mnx+rhea/per_qid_coverage.tsv` 里 `gip_rb_8/16/all` 全为 `False`、`is_self_record_gip8` 全为 `False` → 不在任何 GIP 命中集里 | **不变** |
| v1.1 `v4 ex-self` hit@1（B121 / 298） | 51 / 73 | B121 交集 0；298 的 6 题里 5 题四批 `product_hit.rank` 全为 `None`（不可能计入 ex-self） | **不变** |
| v1.2 `v4 ex-self` hit@1（B121 / 298） | 62 / 87 | 同上（v1.2 复用 v1.1 回复，逐题位次一致） | **不变** |
| 唯一例外：298-R2 | v1.1 / v1.2 `product_hit.rank = 1` | 该题胜出假设的来源是 `s5-rule:envipath:*` 通道（另有 4 个假设，事件参与者只有底物/主产物/共产物），与 RetroRules 自记录无关；且它属「仅反向」，生产路径产不出该规则候选 | **不变** |

**结论**：在这次核查覆盖的三个 ex-self 出口上，判据的「方向/完整性」缺陷都**没有**改变已公布数字。
保守上界：若把「部分覆盖」也并入自记录，理论上最多影响 298 的 3 题（1.5% of 196），
B121 为 0；但该 3 题在既有产物里既非 GIP 命中、也非 LLM 命中，所以实测影响为 0。

**残余不确定性（如实披露）**：v1.x 的 `v4 ex-self` 剔除口径在公开产物里没有逐题落盘
（`metrics_v4.json` 的 `per_qid` 只有位次，没有「本题是否被剔除」的标记），
因此本报告用的是「受影响题集 × 命中集」的集合级界定，而不是逐位复现该剔除过程。
集合级界定已足够区分 0 与「有几题」的差别。

### 6.6 最小补丁建议（本次不改源码，供下一轮实施）

1. **补反向判定，但不改既有字段语义**：
   ```
   by_reverse_strict_pair = bool(gold_keys ⊆ lhs_keys and sub_keys ⊆ rhs_keys)
   is_self_record = by_reaction_id or by_strict_pair or by_reverse_strict_pair
   ```
   并把 `by_reverse_strict_pair` 单列返回。理由：`tests/unit/test_retro_source_phase2b.py:221`
   已把「底物喂 lhs、金标喂 rhs」固定为 `by_strict_pair=True`，改字段含义会直接打断该单测，
   也无法和已归档的 ex-self 数字对齐。
2. **部分覆盖只披露、不自动并入**：新增 `partial_gold_coverage` 与
   `matched_gold_component_fraction` 两个字段，由调用方（`pool_coverage_eval._is_self_recorded`）
   决定是否计入。直接并入会把「规则只覆盖一个产物」的普通候选误判为自记录，静默改变已公布数字。
3. **口径变更必须重放**：若要把部分覆盖计入 ex-self，需重跑 `POOL_COVERAGE` 全批次并登记
   `ex_self_criterion_version`，不允许只改代码不重算。
4. **补单测**（合成夹具，不含题面/金标）：①反向模板正控（金标⊆lhs ∧ 底物⊆rhs 应判 True）；
   ②部分覆盖负控（默认 False，且 `partial_gold_coverage=True`）；③现有三条用例保持通过。
5. **三处副本同步**：`v44_v13` / `v44` / `dependingv43` 的 `retro_source.py` 与
   `pool_coverage_eval.py` 是同源副本，改动需三处一致（本次不动）。

## 7. 合规自查

| 项 | 结果 |
| :--- | :--- |
| 零 LLM 调用 | 是（只有本地文件读取与 RDKit 判分） |
| 读取 `~/.ppv1_holdout_token` | 否 |
| 触碰留出集 / 全集基线 | 否（只跑调参集批次） |
| 冻结判分器 SHA256 | 前后一致（`ac38ea39…63f41` / `5a677550…456d`） |
| 改 `src/` 源码 | 否（task 要求只核查） |
| 报告中含 SMILES / 私有题号前缀 | 否（6 道受影响题用 P/R 标签） |
| 删除文件 | 否（一次也没有） |
| push / merge / reset --hard | 否 |

## 8. 复现命令

```bash
cd "${REPO_ROOT:-.}"
export PYTHONPATH=src \
       V43_ASSET_ROOT="${V43_ASSET_ROOT:-assets}" \
       V3_CODE_ROOT="${V3_CODE_ROOT:-<V3_CODE_ROOT>}"
PYTHON="${PYTHON:-python3}"

# 每批一次（示例：v1.1 / B121）；其余批次把 --batch-root/--runs-root/--out-dir 换掉即可
$PYTHON scripts/eval/score_disclosure_v4cn.py \
  --batch-root <ARCHIVE_ROOT>/v44_next_v1_1_tuning_20261110/batch_b121_tuning_v44next \
  --runs-root  <ARCHIVE_ROOT>/v44_next_v1_1_tuning_20261110/runs_b121_tuning_v44next \
  --out-dir reports/manual_review/v13_t6_2026-11-13/v11_b121 \
  --domain-tag biosysmodb121
# 产物：reports/manual_review/v13_t6_2026-11-13/<name>/disclosure_v4cn_<domain>.json
#       reports/manual_review/v13_t6_2026-11-13/<name>/flips_v4cn_<domain>.jsonl

# T6-2 复算（只读 rhea 索引 + 调参集题卷）
$PYTHON reports/manual_review/v13_t6_2026-11-13/probe_t6_2_direction.py
$PYTHON reports/manual_review/v13_t6_2026-11-13/probe_t6_2_selfrecord.py

# 冻结判分器复核
shasum -a 256 src/pathway_v43/pollutant/evaluation.py src/pathway_v43/pollutant/s5b_scoring.py
```

## 9. 假设与遗留

**假设**

1. v6 = 「加固后的 `score_disclosure_v4cn.py`（质子化不变身份）+ 现行小分子排除清单」；
   本次直接用当前仓库实现跑，未另写判据副本。
2. 「调参集题」= 各批 `batch_manifest.json` 的 `registration_order` 全集（这些批次本身只含调参集题）。
3. v1.0 指 v44-Next 的 base 批次（`v44_next_tuning_20261110`）；任务书只要求 v1.1 / v1.2 / R / T，
   v1.0 为额外补充行。
4. T2-G 六臂仅作附录，不参与「5 配置」主表（它们是重放臂，不是独立采样配置）。

**遗留**

1. T5 报告 §3.1 / §4 的「方向相反」表述需更正（建议主窗口在下一轮改文档；本次未改 T5 报告）。
2. v6 **尚未冻结**：本报告数字是「当前加固实现」的结果；判据冻结属用户裁定（AGENTS.md 自迭代条款），
   本报告不作冻结声明。
3. v1.x `v4 ex-self` 的逐题剔除口径没有落盘，无法逐位复现（§6.5 已披露）；若主窗口需要逐位对齐，
   需要先补「ex-self 逐题标记」到评测产物。
4. Exp-2 需 HPC 批次根回传后才能重算（§5.2）。
5. `check_retro_self_record` 的修复属下一轮实施；本报告只给最小补丁建议，未改任何源码。