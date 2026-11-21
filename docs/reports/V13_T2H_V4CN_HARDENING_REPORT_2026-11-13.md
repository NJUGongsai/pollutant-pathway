# v4-cn 电荷中和披露口径的护栏加固（T2-H，零调用）

> 分支：`ocagent/261113-v13-t2g-4821`（T2-G 同一分支，连续交付）。
> 任务书：`dependingv43/docs/tasks/active/TASK_V13_42PCT_2026-11-13.md` §6。
> 依据：`dependingv43/docs/mimo_v4cn_charge_neutral_review_response_2026-11-13.md`
> （mimo 只读化学评审；**采信到与程序证据互证的程度为止**，不背书其执行性结论）。
> 红线：零 LLM / 零外部 API；冻结判分器只读且前后核 SHA256；
> 逐题含金标产物只写 gitignored；本报告零 SMILES、零私有题号前缀。
> 题域标签：`[biosysmodb121·调参集 N=261]`、`[dev-298·调参集 N=196]`；不含留出集。

## 1. 交付物与改动面

| 文件 | 改动 |
|:--|:--|
| `scripts/eval/score_disclosure_v4cn.py` | 重写算子层：9 条护栏 + 扩展自检 + 算子行为表 + 遗留差异分桶 |
| `tests/unit/test_v4cn_guards.py` | 新增 12 项单测（合成夹具，非金标/题面） |
| `docs/reports/v4cn_operator_behavior_table_2026-11-13.json` | 25 夹具机读算子行为表（无 SMILES） |

**未改**：`src/` 下任何冻结判分代码（`evaluation.py`、`s5b_scoring.py` 等）。
SHA256 前后一致：

- `evaluation.py` = `ac38ea393bfb91e420e98730415cba334df2f9d3d9de4ecfde90914f45363f41`
- `s5b_scoring.py` = `5a677550ef54a3a1e16d5b5a1ce4dd8d2cdcb55dd56224e8a148f50511dc456d`

脚本自身：加固前（commit `78654bf`）`dfa771ee…`，加固后 `0ffb8b71…`；
加固前版本以 `git show 78654bf:scripts/eval/score_disclosure_v4cn.py` 取回，
作为 legacy 基线做逐题对照（不覆盖、不入仓）。

## 2. 九条护栏的落实位置

| 任务书 §6 | 护栏 | 实现位置 | 机读状态 |
|:--:|:--|:--|:--|
| 1 | 中和不变量：重原子图/键级/元素序列/同位素/立体（含增强立体）/自由基/组分数 | `_invariant_signature()` + `neutralize_checked()` 的顺序检查 | `invariant_broken` |
| 2 | 身份同源：走 v4 参考侧同一 CXSMILES 身份机器，不纯 `MolToSmiles` 往返；逐条幂等自检 | `_identity_key()`；`strict_identity_of(key) == key` | `failed: identity_roundtrip_failed` |
| 3 | 净电荷保护 | 三段：`zero_to_nonzero` / `sign_flip` / `charge_grew` | `net_charge_changed` |
| 4 | 盐 / 反离子单列 | `_classify_salt()`（多组分一律不中和） | `salt_not_normalized` |
| 5 | 排除清单：碳酸体系 / NH₃-NH₄⁺ / CN⁻-HCN / SCN⁻ / H⁺-H₃O⁺ | `EXCLUDED_FAMILIES` + `_excluded_identity_registry()`（按严格身份匹配） | `excluded_family` |
| 6 | 逐侧留痕 | `_neutral_graph()` / `_neutral_payload()` 记录；`_record_summary()` 汇总；`_attribution()` 标注产物侧/底物侧 | 见 `flips_v4cn_*.jsonl` |
| 7 | 派生字段一致 | **选择“只改写身份轴”**：重算 `smiles_isomeric` / `cn_identity` / `formal_charge`，`state_id` 保持原值，逐条记 `v4cn_derived_fields_policy=identity_axis_only` | 见 §5 限制 2 |
| 8 | 自检扩展：幂等 / 零异常 / 零静默回退 + 固定夹具算子行为表 | `_self_check_neutralization()`、`probe_operator_table()`、`--self-check` / `--emit-operator-table` | `self_check_<domain>.json` |
| 9 | 重算各批 + 加固前后差异按原因分桶 | `--legacy-flips` + `legacy_comparison` + `guard_bucket` | 见 §4 |

补充实现要点：

- **顺序固定**：排除清单 → 盐 → 中性短路 → 中和 → 不变量 → 净电荷 → 身份往返。
  先判“是否该动”，再判“动得对不对”，避免对不该中和的结构做无谓往返。
- **回退必带原因**：任何非 `applied` 且非 `not_applicable`（中性短路）的记录都有
  `reason`；自检把“非 applied 且无 reason”计为 `n_silent_reverts`，必须为 0。
- **不改判分链**：护栏只决定“喂给冻结 v4 的身份串”，v4 代码路径原样调用。

## 3. 算子行为表（25 夹具，mimo 2.1–2.8 覆盖）

机读表 `docs/reports/v4cn_operator_behavior_table_2026-11-13.json`
（只含夹具名与布尔/计数，**不含 SMILES**；夹具结构定义在脚本 `FIXTURES`）。

**汇总**：`applied=6`、`excluded_family=7`、`not_applicable=9`、`salt_not_normalized=3`。

| 夹具 | 状态 | 原因 | 改写 | 净电荷 前→后 | legacy 也会改写？ |
|:--|:--|:--|:--:|:--:|:--:|
| `quaternary_ammonium` | not_applicable | identity_unchanged | False | +1→+1 | False |
| `quaternary_ammonium_chloride` | salt_not_normalized | multi_fragment | False | 0→— | False |
| `pyridinium` | applied | charge_only_rewrite | True | +1→0 | True |
| `glycine_zwitterion` | applied | charge_only_rewrite | True | 0→0 | True |
| `betaine_inner_salt` | not_applicable | identity_unchanged | False | 0→0 | False |
| `nitro_neutral` | not_applicable | identity_unchanged | False | 0→0 | False |
| `n_oxide_neutral` | not_applicable | identity_unchanged | False | 0→0 | False |
| `azoxylium` | not_applicable | identity_unchanged | False | +1→+1 | True |
| `phosphate_dianion` | applied | charge_only_rewrite | True | −2→0 | True |
| `sulfate_monoanion` | applied | charge_only_rewrite | True | −1→0 | True |
| `sulfonate_aryl` | applied | charge_only_rewrite | True | −1→0 | True |
| `coa_thioester_like` | not_applicable | neutral_no_formal_charge | False | 0→— | False |
| `sodium_salt` | salt_not_normalized | multi_fragment | False | 0→— | **True** |
| `chloride_ammonium_salt` | salt_not_normalized | multi_fragment | False | 0→— | **True** |
| `enolate` | applied | charge_only_rewrite | True | −1→0 | True |
| `carbonate_dianion` | excluded_family | never_exempt_family | False | −2→— | **True** |
| `bicarbonate` | excluded_family | never_exempt_family | False | −1→— | **True** |
| `carbon_dioxide` | excluded_family | never_exempt_family | False | 0→— | False |
| `ammonium` | excluded_family | never_exempt_family | False | +1→— | **True** |
| `cyanide` | excluded_family | never_exempt_family | False | −1→— | **True** |
| `thiocyanate` | excluded_family | never_exempt_family | False | −1→— | **True** |
| `hydronium` | excluded_family | never_exempt_family | False | +1→— | **True** |
| `methyl_radical` | not_applicable | neutral_no_formal_charge | False | 0→— | False |
| `enhanced_stereo` | not_applicable | neutral_no_formal_charge | False | 0→— | **True** |
| `uncharged_acetate_acid` | not_applicable | neutral_no_formal_charge | False | 0→— | False |

（`legacy 也会改写？` = 旧脚本 `normalize_charge_smiles` 对该夹具的串有变动；
标 **True** 且新状态非 `applied` 的 10 条，就是“加固拦下的旧改写”。）

对 mimo 子项的对应关系：

- **2.1 季铵/吡啶鎓**：季铵中和不了（身份不变，`permanent_charge_retained=True`，
  不产生误合并）；配对阴离子盐一律 `salt_not_normalized`（不会多/少组分）。
- **2.2 两性离子**：甘氨酸型 `applied`（N⁺ 去质子、COO⁻ 加质子）；甜菜碱型
  因 N⁺ 不可中和、身份不变，不误合并。
- **2.3 硝基/N-氧化物/偶氮鎓**：三者中和后身份不变（`identity_unchanged`），
  不会与别的结构合并；偶氮鎓有旧改写被拦。
- **2.4 磷酸/硫酸单酯与二酯**：磷酸二价阴离子 −2→0、硫酸单酯 −1→0，`applied`。
- **2.5 磺酸根**：芳香磺酸 −1→0，`applied`。
- **2.6 辅酶 A 硫酯**：中性简化硫酯探针 `neutral_no_formal_charge`；另由
  **不变量闸**兜底——任何水解/断键式改写都会被 `invariant_broken` 拦下
  （见 §5 限制 4）。
- **2.7 金属/卤素阴离子盐**：`sodium_salt` / `chloride_ammonium_salt` 均
  `salt_not_normalized`，且旧脚本本会改写它们（正是 mimo 不同意的场景）。
- **2.8 烯醇负离子**：−1→0，`applied`。

## 4. 重算结果与加固前后差异（16 套批）

复算范围：**v1.1 存档、v1.2 存档、T2 的 R/T 各两态、R1 各一套**——共 16 套，
两域 457 题 × 16。每套同时跑加固脚本（`hardened/`）与 legacy 基线（`legacy/`），
输出落 `reports/manual_review/v13_t2g_2026-11-13/v4cn/`（gitignored）。

| 域·分集 | 批 | strict v4 @1/@3/@5 | v4-cn 加固 @1/@3/@5 | v4-cn legacy @1/@3/@5 | 翻转数 | 中和状态 applied/excluded/salt/n-a/failed | 幂等违规/静默回退 | 拦下旧改写 | 逐题 after_rank 差异 |
|:--|:--|:--|:--|:--|:--:|:--|:--:|:--:|:--:|
| `[biosysmodb121·调参集]` N=261 | v1.1 存档 | 54/75/87 | 90/111/122 | 90/111/122 | 40 | 1349/64/0/1097/0 | 0/0 | 11 | **0** |
| `[biosysmodb121·调参集]` N=261 | v1.2 存档 | 66/80/90 | 99/116/125 | 99/116/125 | 40 | 1349/64/0/1110/0 | 0/0 | 11 | **0** |
| `[biosysmodb121·调参集]` N=261 | R 臂·机制关 | 56/77/86 | 88/114/121 | 88/114/121 | 39 | 1367/69/0/1057/0 | 0/0 | 10 | **0** |
| `[biosysmodb121·调参集]` N=261 | R 臂·机制开 | 58/78/87 | 88/114/122 | 88/114/122 | 40 | 1363/70/0/1068/0 | 0/0 | 10 | **0** |
| `[biosysmodb121·调参集]` N=261 | R 臂·R1 开 | 59/78/87 | 89/114/122 | 89/114/122 | 40 | 1363/70/0/1068/0 | 0/0 | 10 | **0** |
| `[biosysmodb121·调参集]` N=261 | T 臂·机制关 | 52/80/87 | 82/115/123 | 82/115/123 | 37 | 1354/61/0/1101/0 | 0/0 | 17 | **0** |
| `[biosysmodb121·调参集]` N=261 | T 臂·机制开 | 61/82/88 | 92/117/124 | 92/117/124 | 38 | 1354/61/0/1109/0 | 0/0 | 15 | **0** |
| `[biosysmodb121·调参集]` N=261 | T 臂·R1 关 | 60/82/88 | 91/117/124 | 91/117/124 | 38 | 1354/61/0/1109/0 | 0/0 | 15 | **0** |
| `[dev-298·调参集]` N=196 | v1.1 存档 | 77/102/108 | 78/105/111 | 78/105/111 | 3 | 150/48/0/1625/0 | 0/0 | 26 | **0** |
| `[dev-298·调参集]` N=196 | v1.2 存档 | 91/113/117 | 94/118/122 | 94/118/122 | 5 | 150/54/0/1623/0 | 0/0 | 26 | **0** |
| `[dev-298·调参集]` N=196 | R 臂·机制关 | 72/100/106 | 73/102/108 | 73/102/108 | 2 | 152/46/0/1601/0 | 0/0 | 9 | **0** |
| `[dev-298·调参集]` N=196 | R 臂·机制开 | 82/110/114 | 84/113/117 | 84/113/117 | 3 | 153/54/0/1593/0 | 0/0 | 9 | **0** |
| `[dev-298·调参集]` N=196 | R 臂·R1 开 | 82/110/114 | 84/113/117 | 84/113/117 | 3 | 153/54/0/1593/0 | 0/0 | 9 | **0** |
| `[dev-298·调参集]` N=196 | T 臂·机制关 | 75/104/111 | 76/106/114 | 76/106/114 | 3 | 136/53/0/1628/0 | 0/0 | 15 | **0** |
| `[dev-298·调参集]` N=196 | T 臂·机制开 | 84/111/119 | 86/115/123 | 86/115/123 | 4 | 136/60/0/1621/0 | 0/0 | 15 | **0** |
| `[dev-298·调参集]` N=196 | T 臂·R1 关 | 84/111/119 | 86/115/123 | 86/115/123 | 4 | 136/60/0/1621/0 | 0/0 | 15 | **0** |

**结论**：

1. **加固前后 16 套批的逐题 `after_rank` 差异全部为 0**；strict 列与 v4-cn 列在
   `hardened`/`legacy` 两版下**逐项相同**。即护栏**没有改变任何已披露/已引用的
   v4-cn 数字**，T1-A/T2 报告里的 v4-cn 数可直接沿用。
2. 但护栏**确实拦下了旧脚本会做的改写**：每套 9–26 条（16 套合计 223 条次，
   B121 99 / 298 124）。
   原因分布：多为盐/多组分、排除清单成员、自由基与增强立体、以及“身份本就没变”
   的往返改写。这些改写在本批数据上恰好不影响命中判定的最终 `after_rank`，
   属于“结果等价但契约更严”，不是“什么都没做”。
3. 翻转归因（加固后）：298 侧全部 `product_side`（+ 1 题 `both_sides`）；
   B121 侧 `product_side` 19–20 题、`both_sides` 17–21 题。即 v4-cn 的增益主要
   来自金标/预测**产物侧**的写法统一，与设计意图一致。
4. 16 套批的 `failed`、`n_silent_reverts`、`n_idempotence_violations` 全为 0；
   真实批次里**没有**多组分盐结构（`salt=0`），盐护栏只在合成夹具与旧改写
   拦截计数中体现。

## 5. 已知限制与偏离（必读）

1. **净电荷保护取“保守读法”，偏离任务书 §6.3 的字面表述**。§6.3 写“净电荷的
   符号或‘是否为零’发生变化 → 回退”；若按字面执行，乙酸根 −1→0、磷酸 −2→0、
   磺酸 −1→0 全部回退，v4-cn 将退化为空操作，与 mimo 已同意的 §2.4/2.5/2.8
   自相矛盾。实现取“中和只能降低带电程度”：`0→非 0`、符号翻转、`|q|` 变大
   一律回退；`带电→0` 或 `|q|` 变小放行。该偏离已写入模块 docstring 第 3 条，
   并由 `net_charge_changed` 的三段原因机读留痕。
2. **`state_id` 不重算**。任务书 §6.7 允许“或明确披露只改写了身份轴”。本实现
   选后者：`smiles_isomeric` / `cn_identity` / `formal_charge` 同步更新，
   `state_id` 保持原值（它是不透明出现键，重算会使事件引用失配）。已核
   `evaluation.py` 不调用 `chemstate.validate_state_object`，故不会触发
   `state_fact_rederivation_mismatch`；逐条 payload 带
   `v4cn_derived_fields_policy=identity_axis_only`。
3. **盐只单列、不做去反离子**。多组分结构一律保留原串并计
   `salt_not_normalized`，不静默去盐、也不静默计命中。代价是“同一产物写成盐”
   在 v4-cn 下仍算不同——这是有意的保守：去盐会把单个卤素阴离子改写成对应的
   中性酸分子，属明确的错误改写。
4. **中性但非规范书写的串不归一**（例如互变异构、芳香/凯库勒写法、电荷分离式
   的中性表示）：本算子只做电荷中和，不做互变归一；这类差异仍计入未命中。
   另外 `coa_thioester_like` 夹具是**中性简化硫酯**，未覆盖带磷酸负电荷的完整
   CoA；但任何断键/水解式改写都会被不变量闸判 `invariant_broken`。

## 6. 自检与测试

| 检查 | 命令 | 结果 |
|:--|:--|:--|
| 护栏单测（12 项） | `pytest tests/unit/test_v4cn_guards.py` | 12 passed |
| 既有离线工具单测（8 项，含 `_neutralize` 兼容） | `pytest tests/unit/test_v13_offline_tools.py` | 8 passed |
| 16 套批严格路径自检 | `--self-check`（不中和路径复现该批 `metrics_v4.json`；重放批为 `metrics_v4_replay.json` 副本） | **diffs=0（16/16，457 题/套）** |
| 16 套批中和路径自检 | 幂等 / 零静默回退 / 零 failed / 身份往返 | **全部 0** |
| 算子行为表 | `--emit-operator-table` | 25 夹具，`applied=6 / excluded=7 / n-a=9 / salt=3` |

单测覆盖：夹具状态表、回退必带原因、`applied` 输出走 `strict_identity_of` 幂等、
中和幂等、盐不被剥离、增强立体/自由基保留、净电荷三段（`zero_to_nonzero` /
`sign_flip`）、不变量闸（人为改键级必须回退）、派生字段与 `state_id` 策略、
图/载荷记录且不改原对象、算子表零 SMILES、`_record_summary` 统计被拦旧改写。

## 7. 复现命令

```bash
PYTHON=${PYTHON:-python3}
REPO_ROOT=${REPO_ROOT:-$(pwd)}
export PYTHONPATH=$REPO_ROOT/src

# 单套（示例：v1.2 存档 B121）
$PYTHON scripts/eval/score_disclosure_v4cn.py \
  --batch-root <ARCHIVE_ROOT>/v44_next_v1_2_tuning_20261110/batch_b121_tuning_v44next_v12 \
  --runs-root  <ARCHIVE_ROOT>/v44_next_v1_2_tuning_20261110/runs_b121_tuning_v44next_v12 \
  --out-dir    reports/manual_review/v13_t2g_2026-11-13/v4cn/v12_b121/hardened \
  --domain-tag biosysmodb121 --self-check

# 加固前后对照（legacy 基线，从 commit 78654bf 取回，不入仓）
git show 78654bf:scripts/eval/score_disclosure_v4cn.py > /tmp/legacy_v4cn.py
$PYTHON /tmp/legacy_v4cn.py --batch-root ... --runs-root ... --out-dir ... --domain-tag ... --self-check

# 护栏单测
$PYTHON -m pytest tests/unit/test_v4cn_guards.py tests/unit/test_v13_offline_tools.py -q
```

重放批（`reports/ppv1_s5b/v13_t2g_arms_20261113/`）的 `batch/metrics_v4.json`
是驱动脚本从 `metrics_v4_replay.json` 复制的副本，仅供 legacy 脚本读取；
两者内容一致，均 gitignored。

## 8. 红线核对

- 冻结判分器未改（SHA256 见 §1），`scripts/eval/` 之外的 `src/` 零改动；
- 零 LLM / 零外部 API：全部输入为已存导出与已判分 metrics；
- 逐题翻转明细（含 qid）只落 `reports/manual_review/...`（gitignored）；
  报告与算子表零 SMILES、零私有题号前缀；
- 未读留出令牌、未触碰留出集；未 push。