# ChatGPT → Qwen：P0 Gate 第三轮修复提示词

> 使用方式：将本文件完整交给 Qwen。  
> 当前裁决：第二轮实现有显著进步，但 ChatGPT 独立审核仍为 `REJECTED`。  
> 本轮目标：只修复剩余 P0 合同断点和 Gate 假阳性；完成后再次交给 ChatGPT 只读审核。  
> 禁止事项：不得进入 P1，不得实现 donor 检索、化学算法、prediction kernel、MCP Server 或 LLM Agent。

---

## 提示词正文

你现在是 ReactionAgent `demov2` 的 **P0 Gate 第三轮修复实施者**。

第二轮实现已经完成了一批有效修复：

- `StrictModel` 已启用 strict validation；
- atom/bond target 已改为 discriminated union；
- 已增加 hypothesis reference registry；
- formal mapping 与 mechanistic origin 已拆成独立 typed object；
- `PredictionResult` 主状态机已经补齐；
- eligibility policy 和 MCP side-effect policy 已成为正式产品 artifact；
- 原 `LineageHypothesis.confidence` 已删除；
- 现有 197 个测试可以运行通过；
- 当前落盘 JSON Schema 与当前模型实际相等。

但是 ChatGPT 第二轮独立审核仍然发现多个合同断点。当前正式裁决是：

```text
CHATGPT_P0_AUDIT_V2 = REJECTED
P0_STATUS = NOT_READY_FOR_CHATGPT_ACCEPTANCE
P1_ENTRY = BLOCKED
```

你必须修复本文列出的剩余问题，补充真实回归测试，重写 Gate 的薄弱检查，生成完整证据报告，然后停止等待 ChatGPT 第三次独立审核。

不得把现有：

```text
197 passed
10/10 Gate PASS
```

解释成 P0 已经被接受。现有 Gate 仍会对若干非法对象产生假阳性。

---

# 1. 唯一工作目录与权限边界

唯一允许写入的目录：

```text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2
```

必须遵守：

- `demov2` 外的全部文件只读；
- legacy ReactionAgent 只读；
- 不得删除、移动、清理或覆盖用户文件；
- 当前工作树中的未提交和未跟踪文件均属于用户；
- 不得执行 `git add`、`git commit`、`git push`、`git reset`、`git clean`；
- 不得通过弱化 final design、final plan 或 ADR 科学边界让 Gate 通过；
- 不得删除失败测试；
- 不得使用 `skip`、`xfail`、`xpass` 或 broad exception 掩盖失败；
- 不得在测试中重新手写一套与产品 artifact 无关的“参考常量”；
- 不得修改 ChatGPT 审核提示词来规避验收。

---

# 2. 开始前必须完整阅读

按顺序完整阅读：

1. `plan/final_design.md`
2. `plan/final_plan.md`
3. `plan/final_discussion.md`
4. `QWEN_P0_GATE_EXECUTION_PROMPT.md`
5. `reports/p0/CHATGPT_P0_GATE_V3_REMEDIATION_PROMPT.md`
6. 六份当前 ADR；
7. 当前 `reaction_agent/schemas/`；
8. 当前 `reaction_agent/policies/`；
9. 当前 `reaction_agent/contracts/`；
10. 当前 `tests/contracts/`；
11. 当前 `scripts/run_p0_gate.py`；
12. 当前 `reports/p0/P0_GATE_REPORT.md` 和 JSON 报告。

三份 final 文件仍然是最高权威输入。

如果发现三份 final 文件之间存在会实质改变 Schema 或 Gate 结果的冲突，停止并报告：

```text
BLOCKED_BY_AUTHORITY_CONFLICT
```

不得静默选择其中一种解释。

---

# 3. 本轮严格范围

本轮只允许修改：

- ADR 权威措辞；
- Pydantic Schema skeleton；
- hypothesis/ledger reference validation contract；
- mapping/mechanism cross-field contract；
- eligibility policy 与 ADR 的一致性；
- forbidden confidence contract；
- canonical exception contract；
- JSON Schema export/freshness contract；
- P0 合同测试；
- P0 Gate runner；
- P0 Markdown/JSON 证据报告；
- 必要的 README P0 说明。

本轮禁止实现：

- donor retrieval；
- canonical identity 化学算法；
- atom mapping 算法；
- fragment-lineage 解析算法；
- transformation extraction；
- site enumeration 算法；
- graph edit；
- candidate generation；
- chemical validation engine；
- ranking；
- decision policy 算法；
- prediction kernel；
- MCP Server；
- MCP 网络 handler；
- LLM Agent；
- generalized lane 业务实现；
- external retrieval；
- multistep search；
- benchmark 性能结论。

P0 只冻结合同，不实现 P1+ 业务。

---

# 4. 修复前必须复现的残留假阳性

编码前先在当前实现上复现以下对象仍被接受，并把复现结果记录到工作日志。

这些是 ChatGPT 第二轮审核已经实际确认的残留问题：

```text
site_transform_mismatch                 ACCEPTED
target_not_in_query                     ACCEPTED
unknown_source_ledger_reference         ACCEPTED
donor_context_not_assumption            ACCEPTED
qualitative_confidence_note             ACCEPTED
self_bond_target                        ACCEPTED
mechanistic_evidence_mismatch           ACCEPTED
formal_assignment_method_mismatch       ACCEPTED
```

此外确认：

```text
reaction_agent.schemas.UnknownReferenceError
is not
reaction_agent.schemas.errors.UnknownReferenceError
```

本轮完成后，上述所有情况必须被拒绝或消除，且必须成为自动化回归测试。

---

# 5. 修复 authority 的最后一个冲突

README 已经明确 `final_discussion.md` 是权威文件，但 ADR-0001 仍然写：

```text
All discussion files — decision evidence only
```

这按字面仍然包含 `final_discussion.md`，与同一 ADR 中的“三份 final 文件是唯一权威集合”冲突。

必须把 ADR-0001 改为精确措辞，例如：

```text
All non-final discussion drafts are historical decision evidence only.
```

或显式列出非 final discussion：

```text
chatgpt-discussion.md
CLAUDE_discussion.md
qwen_discussion.md
```

要求：

- `final_discussion.md` 必须始终属于三份当前权威之一；
- 不得用任何 wildcard 把它归入历史文件；
- README 与 ADR-0001 必须使用相同的权威集合；
- Gate 必须同时检查 README 和 ADR-0001，而不是只检查 README；
- Gate 必须验证三份 final 文件存在；
- Gate 必须验证已知旧权威草稿有清晰 historical banner。

新增负例测试：

```text
ADR-0001 contains "All discussion files" → FAIL
README historical wildcard includes final_discussion → FAIL
non-final authority-claiming document without historical banner → FAIL
```

---

# 6. 把 reference registry 从“集合存在性”升级为“关系完整性”

当前 registry 只有彼此独立的 ID 集合：

```text
reaction_ids
lineage_ids
transformation_ids
site_ids
transformation_family_ids
relaxation_policy_ids
relaxation_ids
source_ledger_ids
```

它只能证明每个 ID 单独存在，不能证明这些 ID 构成合法组合。

必须建立最小 typed relation contract。可以采用 mapping 或 typed relation records，但至少表达：

```text
lineage_id → reaction_id
transformation_id → source_lineage_ids
site_id → transformation_id
query_id → valid atom IDs
query_id → valid bond identities
relaxation_policy_id → allowed relaxation IDs
source_ledger_id → reaction_evidence_id
```

如果 query 在 hypothesis 中需要显式 ID，应在 validation envelope 中加入：

```text
query_id
```

或者把 query target context 作为独立 typed validation context 提供。

不得建设数据库或 repository framework；P0 只需最小、明确、可测试的 registry/context。

## ProductionSelectionHypothesis 必须额外验证

- support lineage 必须属于某个 support reaction；
- transformation 必须来源于所引用的 lineage/evidence space；
- site 必须属于所选 transformation；
- transformation/site 必须属于当前 frozen context；
- 不能因为 transformation ID 和 site ID 分别存在就接受错误组合。

必须拒绝：

```text
registry contains t1, t2, s1
s1 belongs to t1
hypothesis selects t2 + s1
```

## AgentProposedHypothesis 必须额外验证

- atom target 必须存在于当前 query；
- bond target 必须存在于当前 query；
- bond 两个端点不得相同；
- bond identity/端点必须与 query context 一致；
- relaxation ID 必须属于所选 relaxation policy；
- transformation family 必须存在于当前注册词表；
- target 不得只做“非负整数”检查。

必须拒绝：

```text
AtomTarget(atom_id=999999) when query does not contain atom 999999
BondTarget(begin_atom_id=4, end_atom_id=4)
BondTarget whose edge is absent from query
relaxation ID exists globally but is not allowed by selected policy
```

## 推荐合同形式

可以实现等价于：

```text
HypothesisValidationContext
├── reaction_ids
├── lineage_to_reaction_id
├── transformation_to_lineage_ids
├── site_to_transformation_id
├── transformation_family_ids
├── relaxation_policy_to_allowed_ids
├── query_id
├── query_atom_ids
├── query_bond_pairs
└── source_ledger_to_reaction_id
```

具体命名可以调整，但语义不能缺失。

---

# 7. 为 CandidateAnalogyLedger 实现真实 source reference validation

当前 `CandidateAnalogyLedger.source_ledger_id` 只验证非空。

以下对象当前仍被接受：

```text
source_ledger_id = "DOES_NOT_EXIST"
```

必须增加最小 ledger reference validation contract，例如：

```text
LedgerReferenceRegistry
├── source_ledger_ids
├── source_ledger_to_reaction_id
├── candidate_ids
└── evidence_ids
```

或复用统一 validation context。

必须验证：

- `source_ledger_id` 真实存在；
- candidate ledger 引用当前 run/context 中的 source ledger；
- 必要时，candidate 支持 lineage/reaction 与 source ledger 的 reaction evidence 一致；
- `candidate_id` 属于当前 validation context；
- unknown source ledger ID 被拒绝。

必须修正误导性测试：

当前名为：

```text
candidate ledger references unknown source ledger
```

的测试实际上只测试字段完全缺失。

第三轮必须同时保留两个独立负例：

```text
missing source_ledger_id → reject
unknown but non-empty source_ledger_id → reject
```

---

# 8. 强制 donor-derived context 永远是 assumption

当前：

```python
is_assumption: bool = True
```

注释写“always True”，但 Schema 接受：

```python
is_assumption=False
```

必须改成类型系统强制，例如：

```python
is_assumption: Literal[True] = True
```

或等价的 validator。

要求：

- `False` 必须拒绝；
- 缺省序列化必须明确输出 `true`；
- donor cofactor、stoichiometry、participant role 不得被标记为 X→Y 已证明事实；
- CandidateAnalogyLedger 的 inherited donor context 必须始终保留 assumption 语义。

新增负例：

```text
InheritedDonorContext(is_assumption=False) → reject
```

---

# 9. 删除 `confidence_note` 绕过

当前 `QueryCandidateAdaptation` 中存在：

```python
confidence_note: NonEmptyStr
```

它允许：

```text
confidence_note = "high confidence"
```

这绕过 ADR-0005 的 qualitative confidence 禁令。

必须删除该字段，不要只把它加入 forbidden 名单。

如需要表达 adaptation 的验证状态，使用明确、受控、非 confidence 语义的枚举，例如：

```text
adaptation_verification_status
  - unverified_analogy
  - formally_mapped
  - evidence_supported
```

枚举名称可调整，但不得：

- 使用 `confidence` 字样；
- 接受任意 high/medium/low 文本；
- 暗示 enzyme activity probability；
- 暗示实验成功概率。

Forbidden field 检查必须递归扫描所有 JSON Schema：

- 顶层 `properties`；
- `$defs`；
- nested objects；
- union branches。

至少拒绝字段名：

```text
confidence
qualitative_confidence
confidence_note
llm_confidence
llm_confidence_text
biological_probability
enzyme_activity_probability
enzyme_probability
enzyme_feasibility
```

此外测试必须确认没有任意自由文本字段可以被用作 LLM qualitative confidence。

---

# 10. 消除 MappingReport 的双事实来源

当前同时存在 typed object 和 legacy flat fields：

```text
formal_mapped_source_assignment.assignment_method
source_assignment_method

formal_mapped_source_assignment.assignment_quality
source_assignment_quality

formal_mapped_source_assignment.assignment_ambiguity
source_assignment_ambiguity

mechanistic_atom_origin.evidence_ids
mechanistic_origin_evidence_ids
```

代码注释称它们必须一致，但当前 validator 没有执行一致性。

以下矛盾对象当前会通过：

```text
mechanistic_atom_origin.evidence_ids = ["E1"]
mechanistic_origin_evidence_ids = ["E2"]
```

以及：

```text
formal_mapped_source_assignment.assignment_method = manual_curation
source_assignment_method = formal_mapped
```

必须选择一种明确方案：

## 推荐方案 A：typed object 是唯一权威

- 删除重复的 legacy flat fields；
- 如确实需要兼容输出，使用只读 derived property/serializer alias；
- 不允许两个可独立提交的事实来源。

## 可接受方案 B：保留兼容字段但强制一致

- typed/flat 同时提供时必须完全一致；
- 只提供 typed 时，flat 必须由 validator/serializer 确定性派生；
- 只提供 flat 时，必须明确是否允许，以及是否只能用于 legacy import；
- evidence ID 集合必须完全一致；
- assignment method/quality/ambiguity 必须一致；
- 冲突必须拒绝。

不要继续保留“注释说一致、Schema 实际不检查”的状态。

---

# 11. 把 mapping 中剩余的 arbitrary dict 改成 typed skeleton

当前：

```text
FormalSourceAssignment.mapped_atom_pairs: list[dict]
MechanisticAtomOrigin.mechanistic_atom_pairs: list[dict]
```

仍允许任意内部键值。

建立最小 typed pair，例如等价于：

```text
FormalMappedAtomPair
├── reactant_participant_id
├── reactant_atom_map
├── product_participant_id
└── product_atom_map
```

以及：

```text
MechanisticAtomPair
├── source_participant_id
├── source_atom_identifier
├── target_participant_id
├── target_atom_identifier
└── evidence_id
```

字段可根据 final design 调整，但必须满足：

- formal 与 mechanistic pair 使用不同 typed object；
- unknown nested fields 被拒绝；
- atom identifier 使用 strict integer 或明确 typed ID；
- mechanistic pair 必须引用已有 mechanistic evidence；
- P0 只定义对象，不实现 mapping 算法。

---

# 12. 正式决定 unbound mechanistic evidence 语义

当前代码允许：

```text
mechanistic_origin_evidence_ids 非空
mechanistic_atom_origin = null
```

并把它称为：

```text
unbound evidence
```

但 ADR-0003 没有定义该状态。

必须进行明确决策，并写回 ADR-0003：

## 方案 A：禁止 unbound evidence

- `mechanistic_origin_evidence_ids` 非空时必须存在 `mechanistic_atom_origin`；
- 没有 origin 时拒绝。

## 方案 B：允许 unbound evidence

必须在 ADR 中明确：

- unbound evidence 的正式字段和名称；
- 它不等于 proven mechanistic origin；
- UI/report 必须如何标识；
- strict eligibility 是否受影响；
- 如何绑定到 mechanistic origin；
- 为什么不能复用 `mechanistic_origin_evidence_ids` 造成误解。

如果选择允许，推荐把字段命名成更准确的：

```text
candidate_mechanistic_evidence_ids
unbound_mechanistic_evidence_ids
```

不要只在 Python 注释和测试中做决定。

ADR、Schema、测试和 Gate 必须一致。

---

# 13. 统一 ADR-0004 与 eligibility policy

当前已存在实际漂移：

ADR-0004：

```text
partial_cofactor
```

正式 policy：

```text
partial_cofactor_stoichiometry
```

必须选择一个稳定 warning ID，并在以下位置完全一致：

- ADR-0004；
- `reaction_agent/policies/partial_eligibility.py`；
- tests；
- Gate；
- JSON/报告中引用的枚举或值。

此外 policy 有：

```text
research_or_diagnostic_eligibility
```

ADR-0004 表格没有这一列。

必须更新 ADR-0004，使每行完整表达：

```text
state
strict_eligibility
required_warnings
quarantine_behavior
evaluation_bucket
research_or_diagnostic_eligibility
```

Gate 必须验证 ADR 与正式 policy 的一致性。

不要只验证 policy 内部自洽；必须能够发现 ADR/policy drift。

可采用：

- ADR 中稳定的机器可解析表；
- ADR 显式链接一个 canonical machine policy，并测试关键枚举/行完全一致；
- 生成稳定的 policy manifest 并做结构比较。

不得再次依赖两个独立手写副本而没有 drift check。

---

# 14. 统一 canonical exception

当前存在两个不同的 `UnknownReferenceError`：

```text
reaction_agent.schemas.errors.UnknownReferenceError
reaction_agent.schemas.hypothesis.UnknownReferenceError
```

必须只保留一个 canonical 定义：

```text
reaction_agent.schemas.errors.UnknownReferenceError
```

要求：

- hypothesis validator 从 `schemas.errors` 导入；
- ledger validator 也复用 canonical exception；
- package `__init__` 只导出该 canonical class；
- `UnknownReferenceError` 继承 `ContractViolation`；
- 调用方捕获 canonical class 时能捕获所有 unknown reference failure；
- 删除重复类。

新增测试：

```python
from reaction_agent.schemas import UnknownReferenceError as exported
from reaction_agent.schemas.errors import UnknownReferenceError as canonical
assert exported is canonical
```

---

# 15. 修复 JSON Schema freshness 的假检查

当前 freshness 测试只比较：

```text
title
top-level property names
```

这不能发现：

- minLength 变化；
- required 变化；
- enum 变化；
- discriminator 变化；
- nested `$defs` 变化；
- numeric constraints 变化；
- defaults 变化；
- union branch 变化。

ChatGPT 已在隔离副本中实测：

```text
把 AgentProposedHypothesis.json 的 minLength 从 1 改成 999
```

之后当前 Gate 仍然：

```text
197 passed
10/10 PASS
READY_FOR_CHATGPT_AUDIT
```

必须改为对全部正式导出 Schema 做完整结构化比较：

```python
exported_json == schema_cls.model_json_schema()
```

要求：

- 覆盖 `scripts/export_json_schemas.py` 中全部 SCHEMAS；
- missing file → FAIL；
- extra stale file → 明确处理并报告；
- 任意 nested constraint 不同 → FAIL；
- JSON object key 顺序不同不应失败；
- 内容结构不同必须失败；
- Gate 不得在检查过程中自动重写 JSON 后再比较；
- export 与 verify 是两个明确步骤。

新增 mutation-style 回归测试或等价测试，至少证明：

```text
property name unchanged but minLength changed → freshness FAIL
enum changed → freshness FAIL
nested $defs changed → freshness FAIL
required changed → freshness FAIL
```

---

# 16. Gate 必须真正验证环境版本

当前 `pyproject.toml` 已正式记录：

```text
requires-python = ">=3.11"
pydantic>=2.8,<3
pytest>=8.0
```

Python 从 3.12 调整到 3.11 已写入 ADR-0001，因此 Python 3.11 本身不再是未披露问题。

但是当前正式报告运行的是：

```text
pytest 7.4.0
```

低于 `pytest>=8.0`。

当前 Gate 虽然读取 `pyproject.toml`，但完全没有解析版本，仍然 PASS。

必须使用实际版本比较，建议使用 `packaging.version` 和 `packaging.specifiers`，或等价可靠机制。

Gate 至少验证：

```text
current Python satisfies requires-python
current Pydantic satisfies project dependency specifier
current pytest satisfies dev dependency specifier
```

不得只检查版本字符串存在。

要求：

- 不满足任何 specifier → G10 FAIL；
- 报告 expected 与 actual；
- 报告精确 failure；
- 不得静默降低 pytest requirement；
- 如果无法获得 pytest>=8 环境，输出：

```text
BLOCKED_BY_UNSUPPORTED_ENVIRONMENT
```

不得在 pytest 7.4 下再次声明 Gate 全通过。

如果为了运行 Gate 需要新增 `packaging` 依赖，应在 `pyproject.toml` 中以最小、明确方式声明，不要假设环境偶然存在。

---

# 17. 精确验证 skip/xfail/xpass

当前 Gate 使用字符串：

```python
if "skip" in output.lower()
```

这种方法不可靠。

必须获取结构化 pytest 统计。可使用：

- `pytest-json-report`；
- pytest terminal summary 的可靠解析；
- 自定义最小 pytest plugin；
- 或等价结构化结果。

Gate 必须明确得到：

```text
collected
passed
failed
errors
skipped
xfailed
xpassed
```

P0 通过条件：

```text
failed == 0
errors == 0
skipped == 0
xfailed == 0
xpassed == 0
passed == collected
```

不得只因为 pytest exit code 为 0 就通过。

注意：当前 authority tests 中存在：

```python
pytest.skip if historical file missing
```

P0 Gate 要求零 skip，因此这类测试应改为：

- 文件是 required → missing 直接 fail；
- 文件是 optional → 不要为它生成一个 skip test，改成明确 inventory contract。

---

# 18. 扩展 Gate 的十项真实检查

## P0-G01

必须检查：

- 六份 ADR 存在；
- 精确 `Status: Approved`；
- 每份 ADR 必需章节存在；
- acceptance checklist 不与实际 Schema/policy 明显冲突；
- traceability 存在。

## P0-G02

必须检查：

- 三份 final 权威文件；
- README 权威集合；
- ADR-0001 权威集合；
- `final_discussion.md` 不被归为历史；
- 旧权威文件 historical banner；
- README/ADR 不存在 wildcard 冲突。

## P0-G03

必须检查：

- 两条 lane；
- origin；
- lane mixing；
- basic ID existence；
- lineage–reaction relation；
- transformation–lineage relation；
- site–transformation relation；
- target–query membership；
- relaxation–policy membership。

## P0-G04

必须检查：

- typed SourceReactionLedger；
- typed CandidateAnalogyLedger；
- missing source linkage reject；
- unknown source linkage reject；
- `is_assumption=False` reject；
- nested unknown fields reject；
- source fact/candidate assumption 不混用。

## P0-G05

必须检查：

- 八个状态；
- 六个规定字段；
- policy integrity；
- ADR/policy drift；
- warning ID 一致；
- quarantine/excluded；
- strict prohibited/non-production；
- conditional warning propagation contract。

## P0-G06

必须检查：

- formal assignment typed object；
- mechanistic origin typed object；
- mechanistic evidence contract；
- mapper 不自动填 mechanism；
- typed/flat fields 不可矛盾；
- unbound evidence 语义与 ADR 一致；
- nested atom pair typed；
- fraction strict/range。

## P0-G07

必须检查：

- 完整 PredictionResult 状态机；
- scientific abstention/system failure 分离；
- 所有导出 Schema 和 nested `$defs`；
- 不存在 `confidence_note` 等绕过；
- 不存在 LLM qualitative confidence 字段。

## P0-G08

保持正式 MCP policy 检查，并验证：

- 五个工具条目；
- predict immutable append；
- get read-only；
- local expand child run；
- external post-MVP network；
- 三条 idempotency；
- 四条 run invariant；
- ADR/policy 无明显 drift。

## P0-G09

继续检查：

- README legacy metrics provisional；
- ADR-0001 legacy metrics provisional；
- 不把旧数字声明为 v2 KPI。

## P0-G10

必须检查：

- Python/Pydantic/pytest 版本；
- 全部合同测试；
- 零 fail/error/skip/xfail/xpass；
- 全部 JSON Schema 完整结构相等；
- 报告证据完整；
- 任一失败返回非零退出码。

---

# 19. 必须新增的第三轮回归测试

至少新增以下真实负例：

```text
1. site exists and transformation exists, but site belongs to another transform → reject
2. lineage exists and reaction exists, but lineage belongs to another reaction → reject
3. transformation exists but does not derive from cited lineage → reject
4. AtomTarget points to atom absent from current query → reject
5. BondTarget points to bond absent from current query → reject
6. BondTarget begin_atom_id == end_atom_id → reject
7. relaxation exists globally but not under selected policy → reject
8. CandidateAnalogyLedger source_ledger_id is non-empty but unknown → reject
9. CandidateAnalogyLedger candidate_id is unknown when context validation is required → reject
10. InheritedDonorContext(is_assumption=False) → reject
11. QueryCandidateAdaptation carries high/medium/low confidence text → impossible/reject
12. mechanistic typed evidence IDs conflict with flat compatibility IDs → reject
13. formal typed assignment method conflicts with flat method → reject
14. typed assignment quality conflicts with flat quality → reject
15. typed ambiguity conflicts with flat ambiguity → reject
16. arbitrary nested mapped atom pair field → reject
17. exported UnknownReferenceError is canonical schemas.errors class
18. ADR-0001 "All discussion files" wildcard → fail authority check
19. ADR/policy partial-cofactor warning ID mismatch → fail
20. JSON minLength drift with same property names → fail
21. JSON enum drift → fail
22. nested JSON $defs drift → fail
23. pytest version below pyproject spec → Gate fail
24. one skipped test → Gate fail
25. one xfailed test → Gate fail
```

测试必须调用真实产品 Schema、正式 policy、正式 registry/context 或 Gate helper。

不得在测试中构造一个与产品无关的假 policy，然后只测试假 policy。

---

# 20. 完整报告合同

重新生成：

```text
reports/p0/P0_GATE_REPORT.md
reports/p0/P0_GATE_REPORT.json
```

如果保留：

```text
training/P0_GATE_REPORT.md
```

则它必须与正式 Markdown 报告一致，或明确说明用途和差异。

Markdown 和 JSON 报告至少包含：

- UTC timestamp；
- working directory；
- Python actual version；
- Python required specifier；
- Pydantic actual version；
- Pydantic required specifier；
- pytest actual version；
- pytest required specifier；
- 每项 environment requirement 是否满足；
- 权威文件清单；
- 六份 ADR 清单与精确 status；
- 所有新增文件；
- 所有修改文件；
- 所有实际执行命令；
- 每条命令退出码；
- pytest collected；
- passed；
- failed；
- errors；
- skipped；
- xfailed；
- xpassed；
- JSON Schema expected count；
- JSON Schema exported count；
- full structural freshness result；
- 十项 Gate PASS/FAIL；
- 每项 Gate 的 ADR 证据路径；
- 每项 Gate 的 Schema/policy 证据路径；
- 每项 Gate 的测试证据路径和测试名；
- 偏差；
- 假设；
- 已知风险；
- 工作树中用户已有文件及保护说明；
- 是否进入 P1；
- 最终状态。

JSON 报告必须结构化表达，不得只保存概括字符串。

只有满足：

```text
10/10 Gate PASS
all environment specifiers satisfied
passed == collected
failed == 0
errors == 0
skipped == 0
xfailed == 0
xpassed == 0
all JSON schemas full-structure fresh
all required negative tests reject
no unresolved authority/schema/policy drift
```

才能输出：

```text
READY_FOR_CHATGPT_AUDIT
```

否则必须输出：

```text
NOT_READY_FOR_CHATGPT_AUDIT
```

或准确阻塞状态。

不得输出：

```text
P0 accepted
P1 authorized
production ready
scientific performance validated
```

ChatGPT 独立审核通过之前，P1 始终是 blocked。

---

# 21. 推荐实施顺序

严格按以下顺序：

1. 完整阅读权威文件、本提示词和当前实现；
2. 复现 197 tests 与当前 10/10 Gate；
3. 复现本文列出的 8 个残留 ACCEPTED 反例；
4. 先把这些反例写成失败回归测试；
5. 修复 ADR-0001 wildcard；
6. 扩展 relation-aware hypothesis validation context；
7. 增加 target–query validation；
8. 增加 ledger reference validation；
9. 强制 `is_assumption=True`；
10. 删除 `confidence_note`；
11. 统一 canonical UnknownReferenceError；
12. 修复 MappingReport 双事实来源；
13. typed atom pair skeleton；
14. 正式决定 unbound mechanistic evidence；
15. 对齐 ADR-0004 与 eligibility policy；
16. 重写 full JSON Schema freshness；
17. 实现真实 environment specifier validation；
18. 实现结构化 pytest stats；
19. 扩展十项 Gate；
20. 在满足依赖版本的环境运行全部测试；
21. 从隔离新进程运行唯一 Gate 命令；
22. 生成完整 Markdown/JSON 报告；
23. 自审全部负例、ADR、Schema、policy 和报告；
24. 停止，不进入 P1。

---

# 22. 最终回复格式

完成后按以下格式回复：

## A. 修复摘要

逐项说明本提示词的哪些阻断项已修复。

明确：

```text
P0 only
No P1 implementation
```

## B. 文件清单

列出全部新增和修改文件。

## C. 环境合同

```text
Python actual / required / satisfied
Pydantic actual / required / satisfied
pytest actual / required / satisfied
```

## D. 残留反例回归

逐项列出本文第 4 节和第 19 节的非法对象是否已经拒绝。

## E. 命令与退出码

提供真实执行命令、退出码和结构化测试统计。

## F. 十项 Gate

```text
P0-G01 PASS/FAIL — exact evidence
P0-G02 PASS/FAIL — exact evidence
P0-G03 PASS/FAIL — exact evidence
P0-G04 PASS/FAIL — exact evidence
P0-G05 PASS/FAIL — exact evidence
P0-G06 PASS/FAIL — exact evidence
P0-G07 PASS/FAIL — exact evidence
P0-G08 PASS/FAIL — exact evidence
P0-G09 PASS/FAIL — exact evidence
P0-G10 PASS/FAIL — exact evidence
```

## G. 偏差、假设、风险

没有也必须明确写“无”。

## H. 最终状态

只有全部真实通过时输出：

```text
READY_FOR_CHATGPT_AUDIT
```

否则输出：

```text
NOT_READY_FOR_CHATGPT_AUDIT
```

现在开始：先复现残留八个假阳性，把它们变成真实失败测试，再逐项修复。完成 P0 Gate 和完整报告后停止，等待 ChatGPT 第三轮只读审核。

