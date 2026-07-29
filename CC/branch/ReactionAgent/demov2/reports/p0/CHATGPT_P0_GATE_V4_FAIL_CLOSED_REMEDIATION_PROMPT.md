# ChatGPT → Qwen：P0 Gate V4 Fail-Closed 精确修复提示词

> **任务类型：** P0 第四轮精确修复  
> **执行模型：** Qwen  
> **审核模型：** ChatGPT  
> **工作目录：** `/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2`  
> **状态：** P1 继续 BLOCKED；本任务只修复 P0-G03，不得进入 P1  
> **原则：** 最小改动、测试先行、生产校验 fail-closed、不得通过修改权威设计来迁就现有代码

---

## 0. 你的角色和最终目标

你是本轮的代码实施者。ChatGPT 已完成第三轮只读审核，结论是：

```text
P0 第三轮：REJECTED
人工审核结果：9/10
失败 Gate：P0-G03
P1：BLOCKED
```

第三轮的大部分修复是有效的：

- 专用 `.venv` 环境满足版本约束；
- 270 个现有契约测试全部通过；
- 原先列出的 8 个假阳性都已经被现有复现脚本拒绝；
- JSON Schema 完整结构 freshness 检查有效；
- pytest skip/xfail 结构化统计有效；
- ADR/policy drift 检查有效；
- mapping/formal/mechanistic、dual ledger、confidence、MCP policy 等边界基本通过。

但当前 `P0-G03` 仍然存在一个根本性假阳性：

> 当 relation maps、query target context 或 relaxation policy relation 缺失时，校验器会跳过校验并接受 hypothesis。

本轮唯一目标是：

> 把 hypothesis/context validation 从“有上下文时才检查”的 opt-in 行为，修复为生产接纳路径上的 fail-closed 行为。

完成后必须确保：

```text
缺少验证所必需的上下文
≠ 暂时跳过验证
= 明确拒绝并返回 typed contract violation
```

---

## 1. 严格权限和范围

### 1.1 允许修改

只允许在 `demov2/` 内修改本任务直接需要的文件，预计包括：

```text
reaction_agent/schemas/hypothesis.py
reaction_agent/schemas/errors.py                  # 仅在确需新增单一 canonical error 时
reaction_agent/schemas/__init__.py                # 仅在导出 canonical error 时
tests/contracts/test_v3_hypothesis_relations.py   # 可扩展
tests/contracts/test_v4_fail_closed_context.py    # 推荐新增
scripts/run_p0_gate.py
scripts/reproduce_v3_false_positives.py            # 可扩展或保留
schemas/json/*.json                                # 仅通过真实 schema 重新导出
reports/p0/P0_GATE_REPORT.md
reports/p0/P0_GATE_REPORT.json
reports/p0/V4_REMEDIATION_WORKLOG.md
```

### 1.2 禁止事项

严禁：

- 进入或实现 P1；
- 修改 `plan/final_design.md`、`plan/final_plan.md`、`plan/final_discussion.md` 来合法化 fail-open；
- 修改 ADR 来宣称 relation validation 可以 opt-in；
- 删除、弱化或跳过现有测试；
- 使用 `skip`、`xfail`、`xpass` 掩盖失败；
- 只改报告，不改真实校验行为；
- 只在测试里硬编码特例；
- 为此任务建设数据库、repository framework 或复杂基础设施；
- 大范围重构无关 schema；
- 修改 rank、candidate generation、retrieval、mapping 算法等 P1 内容；
- 执行 `git add`、`git commit`、`git push`、`git reset`、`git clean`；
- 删除或覆盖用户已有设计文件。

本轮要求 surgical change。每一处改动都必须能追溯到本提示词中的一个失败反例或验收条件。

---

## 2. 开始编码前必须完整阅读

先阅读以下权威文件和现状文件，不要凭记忆修改：

```text
plan/final_design.md
plan/final_plan.md
plan/final_discussion.md
docs/decisions/ADR-0002-hypothesis-lanes.md
reports/p0/CHATGPT_P0_GATE_V3_REMEDIATION_PROMPT.md
reports/p0/P0_GATE_REPORT.md
reports/p0/P0_GATE_REPORT.json
reports/p0/V3_REMEDIATION_WORKLOG.md
reaction_agent/schemas/hypothesis.py
reaction_agent/schemas/errors.py
reaction_agent/schemas/__init__.py
tests/contracts/test_v3_hypothesis_relations.py
scripts/run_p0_gate.py
```

特别注意第三轮修复提示词的要求：

```text
ProductionSelectionHypothesis 必须额外验证：
- support lineage 必须属于某个 support reaction；
- transformation 必须来源于所引用的 lineage/evidence space；
- site 必须属于所选 transformation；
- transformation/site 必须属于当前 frozen context；
- 不能因为 transformation ID 和 site ID 分别存在就接受错误组合。

AgentProposedHypothesis 必须额外验证：
- atom target 必须存在于当前 query；
- bond target 必须存在于当前 query；
- relaxation ID 必须属于所选 relaxation policy。
```

不得把这些“必须验证”解释成“调用者可选择是否提供验证信息”。

---

## 3. 第三轮审核已确认的真实结果

### 3.1 环境和现有测试

ChatGPT 实际验证：

```text
Python    3.11.15   required >=3.11
Pydantic  2.13.4    required >=2.8,<3
pytest    9.1.1     required >=8.0
```

命令：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/contracts -q -p no:cacheprovider -ra
```

结果：

```text
270 passed
```

复现脚本：

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/reproduce_v3_false_positives.py
```

结果：

```text
原有 8 个 false positives：8/8 REJECTED
```

现有 Gate：

```bash
.venv/bin/python scripts/run_p0_gate.py
```

结果：

```text
10/10 PASS
READY_FOR_CHATGPT_AUDIT
```

但以下新增独立反例全部被接受，因此上述 G03 是假阳性。

### 3.2 新发现的三个 fail-open 反例

#### 反例 A：ProductionSelection 缺少 relation maps

```text
registry:
  reaction_ids = {r}
  lineage_ids = {l}
  transformation_ids = {t1, t2}
  site_ids = {s1}
  lineage_to_reaction_id = {}
  transformation_to_lineage_ids = {}
  site_to_transformation_id = {}

hypothesis:
  support_reaction_ids = [r]
  support_lineage_ids = [l]
  transformation_id = t2
  site_id = s1
```

实际结果：

```text
production_empty_relation_maps_mismatch: ACCEPTED
```

问题：

- 只能证明各 ID 分别存在；
- 无法证明 `l→r`；
- 无法证明 `t2→l`；
- 无法证明 `s1→t2`；
- 却被生产选择校验接受。

#### 反例 B：AgentProposed 缺少 query context

```text
hypothesis:
  transformation_family_id = ox
  typed_target_atom_or_bond_set = [AtomTarget(atom_id=999999)]

context:
  query_id = null
  query_atom_ids = {}
  query_bond_pairs = {}
```

实际结果：

```text
agent_empty_query_context_target: ACCEPTED
```

问题：

当前实现使用：

```python
if context.query_atom_ids or context.query_bond_pairs:
    validate_targets()
```

两个集合都为空时，整个 target membership validation 被跳过。

#### 反例 C：有 relaxation，但没有选择 policy

```text
hypothesis:
  transformation_family_id = ox
  allowed_relaxation_ids = [r1]
  relaxation_policy_id = null

registry:
  relaxation_ids = {r1}
```

实际结果：

```text
relaxation_without_selected_policy: ACCEPTED
```

问题：

- 只检查了 `r1` 全局存在；
- 没有证明 `r1` 属于任何被选择的 policy。

### 3.3 Registry 内部也可自相矛盾

当前可以构造：

```text
transformation_ids = {t}
site_ids = {s}
site_to_transformation_id = {s: not_known}
```

即 relation map 的 value 根本不在对应 ID set 中，registry 仍然构造成功。

typed registry 必须至少对当前 hypothesis 所依赖的 key/value 提供内部一致性保障。

---

## 4. 根因：必须准确理解后再修

当前 `HypothesisReferenceRegistry` 中所有 relation maps 默认都是空：

```python
lineage_to_reaction_id = {}
transformation_to_lineage_ids = {}
site_to_transformation_id = {}
relaxation_policy_to_allowed_ids = {}
```

生产关系校验使用：

```python
if lid in registry.lineage_to_reaction_id:
    ...

if tid in registry.transformation_to_lineage_ids:
    ...

if sid in registry.site_to_transformation_id:
    ...
```

这套逻辑只能发现：

```text
关系映射存在 + 显式关系不一致
```

不能发现：

```text
关系映射缺失
当前 ID 未被映射覆盖
调用者忘记提供上下文
registry 自己引用未知 key/value
```

本轮修复不能只增加更多“映射存在时的 mismatch”测试。核心是把：

```text
if relation available: validate
```

改为：

```text
production acceptance requires relation:
    relation unavailable -> reject
    relation inconsistent -> reject
    relation consistent -> accept
```

---

## 5. 冻结的实现语义

以下行为是本轮必须实现的合同，不得自行弱化。

### 5.1 ProductionSelectionHypothesis：当前引用链必须完整覆盖

生产选择 hypothesis 被接受前，至少必须证明：

```text
support_reaction_id exists
support_lineage_id exists
support_lineage_id → support_reaction_id
transformation_id exists
transformation_id → source_lineage_ids
selected support lineage supports transformation
site_id exists
site_id → selected transformation_id
```

具体规则：

1. `support_reaction_ids` 不得为空；
2. `support_lineage_ids` 不得为空；
3. 每个引用的 reaction ID 必须存在；
4. 每个引用的 lineage ID 必须存在；
5. 每个引用的 lineage ID 必须在 `lineage_to_reaction_id` 中有映射；
6. lineage 的 owner reaction 必须出现在 `support_reaction_ids`；
7. 当前 `transformation_id` 必须存在；
8. 当前 transformation 必须在 `transformation_to_lineage_ids` 中有映射；
9. transformation 的 source lineage 列表不得为空；
10. 至少一个被引用的 support lineage 必须属于 transformation 的 source lineage；
11. 当前 `site_id` 必须存在；
12. 当前 site 必须在 `site_to_transformation_id` 中有映射；
13. site 的 owner transformation 必须等于所选 `transformation_id`。

如果当前对象引用的任一必需 relation 缺失，必须拒绝，不能跳过。

这里不要求 P0 建设数据库，也不要求整个 registry 覆盖全世界；只要求：

> 当前正在验证的 hypothesis 所引用的关系必须完整。

### 5.2 Production 与存在性诊断不得混淆

如果项目确实需要一个只验证 ID existence 的低层 helper，可以保留，但必须满足：

- 名称和 docstring 明确说明它不能用于生产接纳；
- 生产接纳路径必须调用 full context/relation validator；
- `P0-G03` 只认可 full validator；
- 不得把 existence-only helper 导出成看似“完整验证”的公共入口；
- 不得让调用者通过选择一个较弱 helper 绕过生产约束。

优先选择最简单的方案。不要为此建设新的 validator framework。

### 5.3 HypothesisReferenceRegistry 内部一致性

至少增加以下一致性校验：

```text
lineage_to_reaction_id:
  key ∈ lineage_ids
  value ∈ reaction_ids

transformation_to_lineage_ids:
  key ∈ transformation_ids
  every value ∈ lineage_ids

site_to_transformation_id:
  key ∈ site_ids
  value ∈ transformation_ids

relaxation_policy_to_allowed_ids:
  key ∈ relaxation_policy_ids
  every value ∈ relaxation_ids

source_ledger_to_reaction_id:
  key ∈ source_ledger_ids
  value 必须属于对应 reaction/evidence ID 集合；
  如果现有 registry 没有正确的目标 ID 集合，不要伪造校验，
  应说明并把该 relation 放到真正拥有双方 ID 集合的 registry/context。
```

不要默默保留一个永远不使用、也无法验证的 relation field。

对重复 relation values，可根据当前 schema 语义选择：

- 保持 list，但在 validator 中去重或拒绝重复；
- 或改成 frozenset；

只做最小必要改动，不要引入新容器体系。

### 5.4 AgentProposed：query target context 必须可区分“未提供”和“合法为空”

不能继续用两个默认空集合表达所有状态，因为它无法区分：

```text
调用者未提供 query context
```

和：

```text
query 的合法 bond 集为空
```

推荐的最小语义：

```python
query_atom_ids: frozenset[int] | None = None
query_bond_pairs: frozenset[tuple[int, int]] | None = None
```

其中：

- `None` 表示上下文未提供；
- `frozenset()` 表示已提供，但合法集合为空；
- AgentProposed 完整验证至少要求 `query_atom_ids is not None`；
- 当出现 AtomTarget 时，atom 必须属于 `query_atom_ids`；
- 当出现 BondTarget 时，`query_bond_pairs` 必须不是 `None`；
- BondTarget 必须属于 `query_bond_pairs`，允许正反端点等价；
- BondTarget 的两个 endpoint 也必须属于 `query_atom_ids`；
- 缺少所需上下文时必须拒绝。

`query_id` 是否强制非空，可保持现有设计允许 context 由外部作用域绑定；但不能因为 `query_id=None` 就放弃 atom/bond membership 校验。

如果你采用另一种能够严格区分 omitted/explicit-empty 的简单实现，可以使用，但必须用测试证明上述语义。

### 5.5 Relaxation 与 Policy 的成对不变量

必须实现：

```text
allowed_relaxation_ids 非空
    ⇒ relaxation_policy_id 非空
    ⇒ policy ID 存在
    ⇒ policy relation map 覆盖该 policy
    ⇒ 每个 relaxation ID 全局存在
    ⇒ 每个 relaxation ID 属于该 policy
```

建议同时规定：

```text
relaxation_policy_id 非空
    ⇒ policy relation map 必须包含该 policy
```

即使该 policy 当前允许集合为空，也必须显式表示：

```python
policy_id: []
```

而不是把“关系未知”误认为“允许集合为空”。

合法情况：

```text
relaxation_policy_id = null
allowed_relaxation_ids = []
```

非法情况：

```text
relaxation_policy_id = null
allowed_relaxation_ids = [r1]
```

非法情况：

```text
relaxation_policy_id = p1
allowed_relaxation_ids = [r1]
policy relation map 中没有 p1
```

非法情况：

```text
policy p1 只允许 r1
hypothesis 使用 r2
```

---

## 6. Typed error 要求

缺失验证上下文必须产生 typed contract violation。

可选择以下最小方案之一：

### 方案 A：复用现有 canonical exception

继续使用：

```python
UnknownReferenceError
```

但错误消息必须明确区分：

```text
unknown ID
missing relation coverage
relation mismatch
missing query context
relaxation policy missing
```

### 方案 B：新增一个 canonical context error

如果确实需要语义更准确的异常，只允许新增一个简单异常，例如：

```python
class IncompleteValidationContextError(ContractViolation):
    pass
```

要求：

- 只在 `reaction_agent/schemas/errors.py` 定义一次；
- 通过 `reaction_agent/schemas/__init__.py` 统一导出；
- 不得在多个模块重复定义同名类；
- 新增 canonical identity 测试；
- 不要建设异常框架或错误码体系。

优先选择改动最少且错误语义清晰的方案。

无论选择哪个方案，Gate 只需验证它属于 canonical `ContractViolation` 体系，并且缺失上下文不再被接受。

---

## 7. 必须采用测试先行

### 7.1 先记录 baseline

先运行：

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2

PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest tests/contracts -q -p no:cacheprovider -ra

PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/reproduce_v3_false_positives.py

.venv/bin/python scripts/run_p0_gate.py
```

把 baseline 结果写入：

```text
reports/p0/V4_REMEDIATION_WORKLOG.md
```

### 7.2 先新增负例，确认 RED

推荐新增：

```text
tests/contracts/test_v4_fail_closed_context.py
```

至少包含以下负例：

1. ProductionSelection 各 ID 单独存在，但所有 relation maps 为空 → reject；
2. relation maps 非空，但没有覆盖当前 selected site → reject；
3. relation maps 非空，但没有覆盖当前 transformation → reject；
4. cited lineage 没有 `lineage→reaction` mapping → reject；
5. ProductionSelection 的 support reactions 为空 → reject；
6. ProductionSelection 的 support lineages 为空 → reject；
7. AgentProposed target 存在，但 query atom/bond context 未提供 → reject；
8. BondTarget 存在，但 `query_bond_pairs=None` → reject；
9. BondTarget endpoint 不属于 query atoms → reject；
10. `allowed_relaxation_ids` 非空但 policy 为 null → reject；
11. policy 非空但 policy relation map 未覆盖该 policy → reject；
12. registry 的 site map value 不属于 transformation IDs → registry construction reject；
13. registry 的 transformation map 引用了未知 lineage → registry construction reject；
14. registry 的 lineage map 引用了未知 reaction → registry construction reject；
15. registry 的 relaxation policy map 引用了未知 relaxation → registry construction reject。

先运行新测试，确认这些测试在旧实现上出现预期失败。将 RED 结果写进 worklog。

不得直接修改测试断言让旧代码通过。

### 7.3 再实现最小修复，确认 GREEN

只修改实现这些不变量所必需的代码。

实现后运行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  tests/contracts/test_v4_fail_closed_context.py \
  -q -p no:cacheprovider -ra
```

然后运行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  tests/contracts/test_v3_hypothesis_relations.py \
  tests/contracts/test_hypothesis_lanes.py \
  tests/contracts/test_v4_fail_closed_context.py \
  -q -p no:cacheprovider -ra
```

最后运行全部契约测试。

---

## 8. 必须保留的正例

不能只让所有输入都失败。至少增加或保留以下正例：

### 8.1 完整 ProductionSelection

```text
reaction_ids = {rxn1}
lineage_ids = {l1}
transformation_ids = {t1}
site_ids = {s1}

lineage_to_reaction_id = {l1: rxn1}
transformation_to_lineage_ids = {t1: [l1]}
site_to_transformation_id = {s1: t1}

hypothesis:
  support_reaction_ids = [rxn1]
  support_lineage_ids = [l1]
  transformation_id = t1
  site_id = s1

expected: ACCEPT
```

### 8.2 合法 AtomTarget

```text
query_atom_ids = {0, 1, 2}
target = AtomTarget(1)
expected: ACCEPT
```

### 8.3 合法 BondTarget

```text
query_atom_ids = {0, 1, 2}
query_bond_pairs = {(0, 1), (1, 2)}
target = BondTarget(1, 2)
expected: ACCEPT
```

### 8.4 显式空 bond 集

```text
query_atom_ids = {0}
query_bond_pairs = {}
target set only contains AtomTarget(0)
expected: ACCEPT
```

该正例用于证明：

```text
explicit empty
```

没有被错误当作：

```text
context missing
```

### 8.5 合法 relaxation

```text
relaxation_policy_ids = {p1}
relaxation_ids = {r1}
relaxation_policy_to_allowed_ids = {p1: [r1]}

hypothesis:
  relaxation_policy_id = p1
  allowed_relaxation_ids = [r1]

expected: ACCEPT
```

---

## 9. Gate 必须从假绿升级为真实检查

修改 `scripts/run_p0_gate.py` 中的 `P0-G03`。

### 9.1 G03 正例必须是完整关系链

当前 G03 positive 缺少完整 lineage/transformation relation。修复后 positive 必须提供：

```text
reaction
lineage
lineage→reaction
transformation
transformation→lineage
site
site→transformation
```

不能再把部分 registry 当作 relation-aware positive。

### 9.2 G03 必须直接执行的负例

Gate 自身至少直接验证：

```text
1. ProductionSelection + empty relation maps → reject
2. selected site 未被 site map 覆盖 → reject
3. AgentProposed + missing query context → reject
4. relaxation IDs 非空 + policy null → reject
5. inconsistent registry relation key/value → reject
```

任何一个被接受：

```text
P0-G03 = FAIL
Gate exit code != 0
status = NOT_READY_FOR_CHATGPT_AUDIT
```

不要只依赖测试文件名称存在。Gate 的 G03 必须自己执行最小核心负例。

### 9.3 G10 保持现有真实检查

不得破坏当前已经有效的：

- 环境 specifier 检查；
- pytest 结构化统计；
- zero skip/xfail/xpass；
- JSON Schema 完整结构 equality；
- stale JSON detection；
- 非零失败退出码。

---

## 10. JSON Schema 处理

如果本轮 schema 改动影响已导出的 JSON：

1. 通过项目已有的正式导出流程重新生成；
2. 不要手工只改 JSON 来迎合 freshness；
3. 重新运行 structural equality；
4. 报告 fresh count 必须与真实导出对象数量一致。

如果 `HypothesisValidationContext` 当前不在正式 JSON export 列表中，不要为了本轮擅自扩大对外 schema surface；只更新已经属于冻结 export contract 的 schema。

---

## 11. 报告必须诚实反映实现

更新：

```text
reports/p0/P0_GATE_REPORT.md
reports/p0/P0_GATE_REPORT.json
```

并新增：

```text
reports/p0/V4_REMEDIATION_WORKLOG.md
```

### 11.1 必须删除的错误口径

修复完成后，报告中不得继续出现：

```text
Relation-aware validation is opt-in
empty-map registry cannot detect relation violations by design
caller must supply context, otherwise validation silently passes
```

生产验证缺少上下文必须失败，因此这些不能再作为可接受 assumption/risk。

### 11.2 Deviations

不得同时写：

```text
Deviations: none
```

和：

```text
关系校验在缺少上下文时无法执行，但仍会接受
```

若仍存在任何 fail-open 行为，必须明确记录为 blocker，并保持：

```text
P1 = BLOCKED
```

### 11.3 Worklog 必须记录

`V4_REMEDIATION_WORKLOG.md` 至少包含：

- baseline 命令和结果；
- 新增负例在旧实现上的 RED 结果；
- 根因；
- 修改文件及每个文件的作用；
- schema 语义决策；
- targeted tests 结果；
- full contract tests 结果；
- Gate 结果；
- 独立反例结果；
- remaining deviations/risks；
- 明确声明未进入 P1；
- 明确声明未执行 git 写操作；
- 明确声明未删除用户文件。

---

## 12. 最终必须执行的命令

在项目根目录运行：

```bash
cd /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
```

### 12.1 Targeted tests

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  tests/contracts/test_v3_hypothesis_relations.py \
  tests/contracts/test_hypothesis_lanes.py \
  tests/contracts/test_v4_fail_closed_context.py \
  -q -p no:cacheprovider -ra
```

### 12.2 Full contract tests

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  tests/contracts -q -p no:cacheprovider -ra
```

要求：

```text
failed = 0
errors = 0
skipped = 0
xfailed = 0
xpassed = 0
passed = collected
```

### 12.3 Existing false-positive reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/reproduce_v3_false_positives.py
```

原有 8 个反例必须继续：

```text
8/8 REJECTED
```

### 12.4 P0 Gate

使用用户指定命令：

```bash
.venv/bin/python scripts/run_p0_gate.py
```

要求：

```text
P0-G03 PASS
P0-G10 PASS
10/10 PASS
READY_FOR_CHATGPT_AUDIT
exit code 0
```

注意：

> Gate 10/10 只是提交 ChatGPT 复核的前置条件，不代表 Qwen 可以自行宣布 P0 最终通过，更不代表可以进入 P1。

---

## 13. 最终独立行为矩阵

提交前，逐项运行并把实际结果写入 worklog。不得只写“测试覆盖”。

| Case | 期望 |
|---|---|
| 完整、关系一致的 ProductionSelection | ACCEPT |
| 所有 ID 单独存在，但 relation maps 为空 | REJECT |
| site ID 存在，但 site relation 未覆盖当前 site | REJECT |
| site 属于另一 transformation | REJECT |
| transformation relation 未覆盖当前 transformation | REJECT |
| transformation 不来源于 cited lineage | REJECT |
| lineage relation 未覆盖 cited lineage | REJECT |
| lineage 属于另一 reaction | REJECT |
| registry relation 指向未知 ID | REJECT |
| AgentProposed AtomTarget 属于 query | ACCEPT |
| AgentProposed AtomTarget 不属于 query | REJECT |
| AgentProposed target 存在，但 query context 未提供 | REJECT |
| 合法 BondTarget 属于 query | ACCEPT |
| BondTarget 不属于 query | REJECT |
| BondTarget context 未提供 | REJECT |
| 无 policy 且无 relaxation | ACCEPT |
| 无 policy 但有 relaxation | REJECT |
| policy 存在且 relaxation 被允许 | ACCEPT |
| policy 存在但 relation map 未覆盖 policy | REJECT |
| relaxation 全局存在但不属于所选 policy | REJECT |

---

## 14. 完成标准

只有同时满足以下全部条件，才能提交 ChatGPT 第四轮只读审核：

- [ ] 新 fail-closed 测试先 RED、修复后 GREEN；
- [ ] ProductionSelection 当前引用链缺失任何 relation 都会拒绝；
- [ ] 各 ID 分别存在但关系未知时不会被生产接纳；
- [ ] Registry relation key/value 内部一致；
- [ ] AgentProposed 缺少 query context 时拒绝；
- [ ] 能区分 query context omitted 与 explicit-empty；
- [ ] relaxation 非空时必须有有效 policy；
- [ ] policy relation 缺失时拒绝；
- [ ] 原有 8 个 false positives 继续 8/8 REJECTED；
- [ ] 新行为矩阵全部符合预期；
- [ ] targeted tests 全绿；
- [ ] full contract tests 全绿；
- [ ] 零 fail/error/skip/xfail/xpass；
- [ ] JSON Schema fresh；
- [ ] Gate 10/10 PASS；
- [ ] Gate 失败时仍返回非零退出码；
- [ ] 报告不再把 relation validation 描述为 opt-in；
- [ ] P1 仍标记 BLOCKED，等待 ChatGPT 审核；
- [ ] 未执行 git 写操作；
- [ ] 未删除、移动或覆盖用户文件；
- [ ] 未修改权威设计来迁就实现。

---

## 15. 提交给 ChatGPT 时只提供这些内容

完成后向用户提供：

```text
1. /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.md
2. /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/P0_GATE_REPORT.json
3. /Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/reports/p0/V4_REMEDIATION_WORKLOG.md
4. 最终 Gate 命令：
   .venv/bin/python scripts/run_p0_gate.py
5. targeted/full tests 的精确统计
6. 行为矩阵的实际 ACCEPT/REJECT 结果
7. changed files 列表
```

不要自行写：

```text
P0 finally accepted
P1 authorized
```

只能写：

```text
READY_FOR_CHATGPT_ROUND_4_AUDIT
P1 BLOCKED pending ChatGPT audit
```

---

## 16. 最后提醒

本轮不是要求“再增加一些 map 字段”，因为这些字段第三轮已经存在。

本轮真正要修复的是：

```text
missing validation evidence must be a failure condition
```

最终生产合同必须满足：

```text
不存在关系证据
→ 不能证明组合合法
→ 不得进入生产候选
```

而不是：

```text
不存在关系证据
→ 暂时不检查
→ 接受候选
```

这是 Reaction Analogy Agent 保证 LLM 只在真实 evidence-derived transformation/site 空间中选择的核心边界，也是本次 P0 能否解锁 P1 的最后阻断项。
