# FABLE5 P1c + 门禁误杀修复报告（T4 并行,不背指标）

> 日期:2026-09-29。分支 `v4.3`,改动全部留在工作树(未 commit)。
> 依据:`docs/FABLE5_REVIEW_RESPONSE.md` §1.1[P1]/§7-3(P1c)与
> `docs/TASK_V43_HIT60_PARALLEL_FABLE5_P1.md` §3-§4;门禁部分依据 S0 取证
> 报告 `reports/phase_s0_hit60/manual_review/gate_case_b978fd0b_forensics.md`
> (gitignored,含金标,本文不引用其分子原文)。
> 零 LLM 调用;不碰远端;不改评分口径;不在已见 298 上重算或宣称提升。

---

## 1. 评审与取证摘录

### 1.1 fable5 §1.1[P1] / §7-3(P1c)

> **[P1] domain/policy.py:77 字符串耦合 services**
> `src/pathway_v43/domain/policy.py:71-74` 硬编码 `_ANALOGY_FALLBACKS`
> 拒因词表,注释承认"避免 domain → services 反向依赖"但实际是脆弱的
> 字符串契约。`services/donor_applicability.py` 若改拒因字面量,
> `decide_prediction_route` 分支逻辑静默失效。
> 建议:将拒因枚举提到 `domain/models.py`(纯常量),或
> `decide_prediction_route` 改收结构化 `eligibility.status/fallback_reason`,
> 不依赖字面量对齐。

### 1.2 S0 取证结论(b978fd0b,§0/§4/§6)

> **误杀坐实。** 编辑执行后的产物与金标唯一产物 `cn_identity` 相等且
> RDKit canonical 相等(字符串级全同),门禁 `target_consistency` 却因
> `atom_id_map` 索引空间错位产生的 19 条 ID 级"拒因"拒收;canonical
> 等价判据因写在 `if not reasons` 之后(atom_tool.py:667)从未被触发。

根因(取证 §4,行号为当时快照):
- `execute_edits` 在**底物解析索引空间**建 `atom_id_map`(:421),随
  canonical 重序列化的 `product_smiles` 原样返回(:511-512);
- `check_target_consistency` 对 canonical SMILES **重新解析**(:610)得
  新索引空间,却套用旧映射(:611)→ 原子 ID 错位,产出"元素/电荷互换"
  类伪拒因(该案 19 条全伪,4 个 ID 落到错的元素上);
- :624 与 :667 使 canonical 等价终判只在 ID 级零拒因时才执行;
- :604-605 对同一 aid 两次取 ID 内嵌元素,恒等死检查,拦不住错位。

修法三方向(取证 §6):① canonical 等价判据前置为短路终判;② 统一
索引空间;③ 固定正/负例回归测试。

---

## 2. P1c 改动清单

| 文件 | 位置 | 改动 |
|---|---|---|
| `src/pathway_v43/domain/models.py` | :50-68 | 新增 `DONOR_FALLBACK_NO_MAPPING` / `DONOR_FALLBACK_MAPPING_AMBIGUOUS` / `DONOR_FALLBACK_APPLICABILITY_FAILED` / `DONOR_FALLBACK_APPLICABILITY_UNKNOWN` / `DONOR_FALLBACK_COMPETING_TRANSFORMS` 与全集 `DONOR_FALLBACK_REASONS`(纯常量,单一事实源) |
| `src/pathway_v43/domain/policy.py` | :15-26, :72-76, :154-155 | `_ANALOGY_FALLBACKS = frozenset(DONOR_FALLBACK_REASONS)`(删除五行硬编码词表);资格块未评估时的推断默认拒因 `applicability_unknown`/`no_mapping` 改用常量(原有第三处隐性字面量) |
| `src/pathway_v43/services/donor_applicability.py` | :34-41, :56-68 | 产出方 `FALLBACK_*` 五常量改为 `DONOR_FALLBACK_*` 的别名(字面量与既有落盘值不变);新增 `EMITTED_FALLBACK_REASONS` 显式声明本模块 fallback_reason 值域恰为全集 |

**方案选择说明**:评审给了两条路(枚举上移 / 改收结构化
`eligibility.status/fallback_reason`)。本仓 `decide_prediction_route`
**已经**在收结构化 `eligibility.status/fallback_reason`(policy.py
:133-135),问题只在 `fallback_reason` 的**值域**靠字面量对齐——所以
取"枚举上移 domain/models 纯常量"即可消除耦合,侵入最小;产出方
(services)与消费方(domain)共用同一常量集合,domain 不反向依赖
services,依赖方向不变。结构化改造(如 enum 类型)会改 eligibility 落盘
形状,触碰 run 恢复兼容,超出"行为逐字等价"的要求,不取。

**行为等价证明**:
1. 常量字面量与原 `_ANALOGY_FALLBACKS` 词表、原 `FALLBACK_*` 逐字符
   相同(`test_fallback_constants_single_source` 钉住全集与五个别名);
2. 路由输出逐字节不变:每个拒因值 → 受约束 novel(reason 前缀
   `<值>:`)或显式停留(`<值>_hold`)的映射,由
   `test_route_each_fallback_value_pinned` 逐值钉住;推断回退路径
   (有 refs → applicability_unknown,无 refs → no_mapping)由
   `test_route_inferred_fallback_paths` 钉住;applicable → analogy_edit
   由 `test_route_applicable_donor_to_analogy` 钉住;
3. 既有路由/预测测试(`tests/test_prediction_task.py` 路由纯函数节、
   `tests/test_phase_c_workflow.py`、`tests/test_reactant_similar.py`
   中对 fallback 字面量的断言)零改动全绿。

## 3. 门禁误杀修复(三方向落地)

| 文件 | 位置 | 改动 |
|---|---|---|
| `src/pathway_v43/services/atom_tool.py` | :511-526 | **方向 2(产出侧)**:`execute_edits` 成功路径新增内部字段 `product_mapped_smiles`——对执行图副本按原子 idx 设 `SetAtomMapNum(idx+1)` 后序列化;映射号随 canonical 排序穿越序列化/重解析,天然免疫重排。`product_smiles` 对外口径不变(不带映射号,消费端 `workflow/nodes.py` 存档的 `edit_execution` 也只取 ok/reasons/product_smiles,不泄漏) |
| `src/pathway_v43/services/atom_tool.py` | :586-608 | **方向 2(消费侧)**:新内部助手 `_exec_id_index(execution)`——优先重解析 `product_mapped_smiles` 按映射号还原 ID↔idx(与 canonical 重排无关);缺该字段/还原不完整(旧产物、手工 dict)fail-closed 回退旧行为 |
| `src/pathway_v43/services/atom_tool.py` | :655-671 | **方向 1**:`check_target_consistency` 在 ID 级对账**之前**加 canonical 等价短路终判——`target_smiles == product_smiles` **且** `cn_identity` 双口径一致才放行(返回 `note=canonical_equivalence_short_circuit` 供遥测);否则进入既有 ID 级对账 |
| `src/pathway_v43/services/atom_tool.py` | :676-683 | **死检查改写**:原 :604-605 对同一 aid 两次 `_id_element(aid)` 恒等;改为真比对——ID 内嵌元素 vs 目标节点标签元素(标签来自解析器 `parser.atoms`,模型改写标识体系仍被 `mapping_inconsistent:element_mismatch` 拦截) |
| `src/pathway_v43/services/atom_tool.py` | :684-688, :708-717 | 执行图改经 `_exec_id_index` 重建;新增 `internal:product_unparseable` 结构化防御;终判兜底(:708-717)保留——ID 级对账不比较立体,立体/互变异构差异仍由 canonical 终判拒收 |

### 3.1 索引空间统一方案说明

- **为什么选 atom-map SMILES 而非 RenumberAtoms**:`MolToSmiles` 的原子
  输出序由 canonical 排名决定,对 mol 内部重编号不保证重解析索引与
  `id_to_idx` 对齐;而 SMILES 原子映射号是**内容寻址**的(随原子走),
  canonical 排序只重排它们的出现顺序,不改变映射号与原子的绑定。
  重解析 `[O:1]=[N+:2]([O-:3])[c:4]1…` 后按 `GetAtomMapNum()` 还原,
  映射与索引空间由构造保证一致。
- **同空间链路**:`execute_edits` 构图(底物解析空间)→ 施加编辑 →
  sanitize → 同一 mol 副本打映射号(idx+1)→ `check_target_consistency`
  重解析该 mapped SMILES → `{aid: idx_of_map[idx+1]}` 重建 →
  `_id_graph_from_mol` 在该空间提元素/电荷/键。修复前合成夹具中 4 个
  ID 落到错的元素(S_N_1 落到 C 等,与取证 §4-b 表完全同型);修复后
  `test_exec_id_index_space_unified` 钉住逐 ID 元素对应。
- **兼容与 fail-closed**:旧形状 execution dict(无 `product_mapped_smiles`)
  回退旧消费路径——可能错位,但分子相同的已被方向 1 短路放行,真不同
  分子仍因图差异被拒,不会误放行(`test_short_circuit_covers_legacy_execution_dict`
  钉住止血独立性)。

### 3.2 "只放行 canonical 相同分子"的论证

1. **短路条件是合取**:`target_smiles == product_smiles`(RDKit
   canonical,含立体/电荷)且 `cn_identity(target) == cn_identity(exec)`
   (判分同源口径,电荷归一 + 立体盲)。canonical 字符串相等本身已蕴含
   cn 相等;cn 口径作为第二道同源校验(且两侧 cn 任一解析失败即不短路,
   fail-closed)。
2. **真不同分子进不了短路**:位置异构体、元素不同、电荷不同、立体
   异构体的 canonical SMILES **必不相同**(RDKit canonical 是全分子
   决定性序列化)——它们的判据不满足,走 ID 级对账 + canonical 终判,
   与修复前同样被拒。负例测试逐一钉住:邻位 vs 间位位置异构体、
   质子化醛(电荷)、硫代醛(元素)、E/Z 与对映异构体(立体,
   cn 相同但 canonical 不同,绝不短路)。
3. **放行语义**:canonical 相同 = 同一分子(判分口径下同一 cn)。
   ID 级差异此时只能是原子编号置换/ID 分配错位,不是化学差异;
   b978fd0b 的 19 条拒因正属于此类(取证 §3:目标与执行产物
   `target_smiles` 逐字符相同)。
4. **评分口径不动**:本修复只改 AtomTool 门禁的接受判据实现,不改
   `cn_identity`、不改判分器、不在已见 298 上重算。

### 3.3 合成回归夹具(不含任何真实金标 SMILES)

正例底物:间硝基苄醇(**硝基前置写法**,输入解析序 ≠ canonical 输出序,
正是触发索引置换的条件;与真实案例仅"取代基位置对调",分子不同),
编辑 = 苄位 C–O 单键升双键(醇→醛)。修复前该夹具产出 **17 条伪拒因**
(元素/电荷互换 + 键错位,与 b978fd0b 的 19 条同型,已实测复现);
修复后 PASS。

| 测试(tests/test_edit_protocol.py 新节) | 类型 | 断言 |
|---|---|---|
| `test_same_molecule_scrambled_numbering_passes` | 正例 | 同分子、目标按底物 ID 分配、执行侧 canonical 重排 → ok=True + note=canonical_equivalence_short_circuit |
| `test_exec_id_index_space_unified` | 方向 2 | `_exec_id_index` 重建后逐 ID 元素对应;旧形状 dict 回退可用 |
| `test_short_circuit_covers_legacy_execution_dict` | 方向 1 独立性 | 缺 mapped SMILES 的 execution dict,分子相同仍放行 |
| `test_positional_isomer_target_still_rejected` | 负例 | 邻位硝基苯甲醛(≠ 间位执行产物)→ 拒(target_edit_mismatch) |
| `test_charge_and_element_variants_still_rejected` | 负例 | 质子化醛(电荷)、硫代醛(元素)→ 拒 |
| `test_stereo_different_target_not_short_circuited` | 负例(fail-closed 红线) | E/Z(cn 相同、canonical 不同)→ canonical_smiles_diff 拒;对映体(ID 内嵌 R/S)→ 拒 |

P1c 测试(tests/test_domain_policy.py 新节):见 §2"行为等价证明"。

## 4. 测试结果

- 全仓:`conda run depending43 python -m pytest tests/ -q` →
  **470 passed,0 failed**(两次全量确认:467 → 470,差值来自并行
  代理 P1a/P1b 期间新增的测试;基线 456 + 本次新增 11(policy 钉住 4 +
  门禁回归 7)+ 并行代理新增)。
- 既有 `tests/test_edit_protocol.py`、`tests/test_atom_tool.py`、
  `tests/test_domain_policy.py`、`tests/test_donor_applicability.py`、
  `tests/test_prediction_task.py` 全绿(102/102)。
- 注:同工作树另有并行代理的 P1a(rate_gate)/P1b(reaction_finder
  schema 版本)改动与其测试,全仓 470 为两组合改动的合计绿数;
  本报告改动可独立回滚(仅 §2/§3 清单内 6 个文件)。

## 5. 未尽事项

- `check_target_consistency` 的 ID 级对账仍不做立体比较(立体差异由
  canonical 终判兜底,负例已钉);如未来要在 ID 级出更具体的立体拒因,
  需另行设计,本次不动评分相关口径。
- 修复不回放历史:已见 298 的 b978fd0b 失分不做重算/改账,按任务书
  "不背指标"纪律执行。
- `product_mapped_smiles` 仅是 execute_edits 返回 dict 的内部附加字段,
  未进入 `workflow/nodes.py` 的 atomtool_checks 落盘;如需在产物里审计
  映射,可后续在 checks["edit_execution"] 透出(本次未做,避免产物
  schema 变更)。
