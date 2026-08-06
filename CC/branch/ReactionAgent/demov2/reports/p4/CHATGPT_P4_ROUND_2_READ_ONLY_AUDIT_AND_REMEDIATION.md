# ChatGPT P4 Round 2 Read-Only Audit and Round 3 Remediation

**Audit date:** 2026-08-04  
**Audit type:** implementation correctness / scientific traceability / integration boundary review  
**Audited worktree:** `/Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2`  
**Audited branch:** `worktree-p4-strict-kernel`  
**Observed HEAD:** `2f9318219777288d55652bc213ba80180e484fbf`  
**Submitted entry:** `reports/p4/SUBMISSION_TO_CHATGPT_P4_ROUND_2.md`  
**Baseline:** `4eb463368e38f2faa3d3656a05974c4b1c1211a6`  

## 0. Audit verdict

**Verdict: P4 Round 2 does not pass the read-only audit. Round 3 remediation is required. P5 remains BLOCKED.**

This is not a rejection of the whole P4 implementation. Round 2 materially improved the local P4 machinery:

- P3 interface presence and current-run presence are now separated;
- fallback candidate construction was removed from `PredictionResultAdapter`;
- support features gained evidence-ID bindings;
- evidence-less structural scalars no longer produce strong support or an in-domain label;
- candidate-local weak/conflicted candidates no longer automatically abort every candidate;
- ranking now uses observable-feature denominator semantics;
- result-hash construction and external deep-copy behavior improved;
- the normal fixture suite and P0 contracts pass under the submitted environment;
- the real-input Gate remains honestly BLOCKED rather than claiming real performance.

However, the most important boundary is still incomplete: P4 does not yet prove that the authority, candidates, evidence observations and namespace it ranks all came from one verified P3/P1/P2 artifact chain. Several independent probes produced `completed`, including one labeled `real`, without such a chain. Therefore P4 cannot yet be accepted as a reliable downstream consumer.

Final status for this audit:

```text
CHATGPT_P4_ROUND_2_READ_ONLY_AUDIT_FAIL
P4_ROUND_3_REMEDIATION_REQUIRED
P5_BLOCKED
```

## 1. What was independently checked

The audit did not treat the submission narrative as proof. It independently checked:

1. source implementation for the P3 consumer, authority handle, pipeline boundary, evidence/support logic, immutable run store, Gate and mutation runner;
2. the Round 2 submission, structured evidence, worklog, changed-files manifest, final-state report, Gate report and mutation report;
3. Git base-to-HEAD scope and the actual current worktree state;
4. the P3 Round 8 interface artifacts available in the P3 worktree;
5. exact submitted test/Gate commands;
6. clean-environment command behavior without ambient `PYTHONPATH`;
7. independent counterexamples for authority construction, current-run validation, candidate binding, namespace completeness, run freezing, P2 receipt validation and mutation adjudication.

The independent probe script was temporary and did not become a repository deliverable:

```text
/private/tmp/p4_round2_independent_probes.py
```

## 2. Independent verification results

### 2.1 Test and Gate matrix

| Check | Independent result | Audit interpretation |
|---|---:|---|
| `PYTHONPATH=. ... pytest ... tests/p4` | **138 passed** | Confirms submitted local fixture suite when ambient import path is supplied. |
| `... pytest ... tests/contracts` | **290 passed** | Confirms P0 contracts did not regress in this worktree. |
| `PYTHONPATH=. ... scripts/run_p4_gate.py` | exit **2**, machinery 11/11 PASS, real input 3/3 BLOCKED | Honest current environment result, but some Gate checks are not sufficiently authoritative; see P4-R2-D. |
| `PYTHONPATH=. ... scripts/run_p4_mutations.py` | reported **14/14 CAUGHT** | The runner executes, but `caught` can still be awarded by prose substring rather than an exact typed failure code; see P4-R2-D. |
| `... pytest ... tests/p4` without ambient `PYTHONPATH` | **137 passed, 1 failed** | The direct Gate subprocess cannot import `reaction_agent`; the test then reads a pre-existing report. |
| direct `python scripts/run_p4_gate.py` without ambient `PYTHONPATH` | exit **1**, `ModuleNotFoundError` | The command recorded in structured evidence is not self-contained. |

The 138-passed suite is real, but it is not sufficient to close the findings below because the suite itself directly constructs the same authority object that production code is supposed to receive only from the verified consumer.

### 2.2 Independent behavioral counterexamples

| Probe | Observed behavior | Required behavior |
|---|---|---|
| Publicly construct `P3AuthorityHandle(source=p3_current_run, evidence_kind=real, ...)` and call P4 directly | `completed`, classification `real` | Reject: no verified P3 consumer result and no production evidence authority. |
| Change only the top-level current-run `evidence_kind` to `real`; leave nested query as `synthetic_fixture`, capability flags false and hashes as placeholders | Consumer grants `capability_available=True`, source `p3_current_run`, classification `real` | Typed BLOCKED/REJECTED. |
| P3 artifact contains `cand_ox_001`, but caller supplies `cand_not_in_p3_artifact` with product `CCC=O` | P4 completes and ranks `cand_not_in_p3_artifact` | Reject candidate not present in verified P3 artifact. |
| Query omits run/query/case/fold/snapshot hash/policy fields | P4 completes | Reject incomplete namespace at production boundary. |
| Create valid run → mutate decision without recomputing hash → freeze | Freeze succeeds; subsequent verify raises `RunHashMismatchError` | Freeze must verify first and fail atomically. |
| P2 report contains expected status plus arbitrary non-empty `receipt_hash` | G14 PASS | Recompute/verify receipt and its bound artifact, or remain BLOCKED. |
| Mutated Gate check has empty `failure_code`, but prose contains expected text | Mutation is counted `caught=True` | Exact typed `failure_code == expected_failure_code` required. |

These are executable results, not hypothetical code-review concerns.

## 3. Round 1 closure matrix

| Round 1 finding | Round 2 status | Audit conclusion |
|---|---|---|
| P4-R1-A P3 manifest/current-run consumer | **Partial** | Interface parsing improved, but current-run semantic/hash verification remains shallow. |
| P4-R1-B typed production authority | **Open** | The new handle is publicly constructible and production trusts its fields. |
| P4-R1-C no fallback candidate | **Partial** | Adapter fallback is closed, but the pipeline candidate list is still caller-supplied and not bound to P3. |
| P4-R1-D namespace isolation | **Partial** | Mismatching supplied fields are rejected; missing fields and most evidence/candidate bindings are accepted. |
| P4-R1-E immutable run/hash | **Partial** | Initial create verifies and copies deeply; mutate→freeze can store a frozen invalid run. |
| P4-R1-F Gate/mutation truth | **Open** | G14 accepts arbitrary receipt text; mutation matching uses prose substring; direct command depends on ambient path. |
| P4-R1-G evidence grounding | **Partial** | Evidence IDs must exist, but feature values and bindings remain caller assertions rather than verified observations from an authority bundle. |
| P4-R1-H per-candidate aggregation | **Closed for fixture machinery** | Strong candidate can remain eligible while a weak/conflicted candidate is disqualified. Keep regression tests. |
| P4-R1-I observable-feature ranking | **Closed for fixture machinery** | Denominator semantics match the stated policy. Keep regression tests. |
| P4-R1-J selective isolation/authority | **Open** | Train-only/fold authority is still not cryptographically/content-addressedly bound; G14 is not a valid authority check. |

## 4. Findings and mandatory remediation

### P4-R2-A — P3 authority and current-run verification are not authoritative (P0)

#### Evidence

`reaction_agent/schemas/p4/authority.py:76-117` defines `P3AuthorityHandle` as an ordinary public Pydantic model. The validator checks only a few enum combinations. For `source=p3_current_run`, both `real` and `synthetic_fixture` are accepted, and `capability_available` is simply:

```python
return self.source == AuthoritySource.p3_current_run
```

The class docstring says the handle is produced only by the consumer, but the implementation does not enforce that statement. P4 tests also construct it directly, demonstrating that type annotation alone is not an authority boundary.

`reaction_agent/adapters/p3_consumer.py:164-181` verifies field presence, optional namespace equality and the top-level evidence-kind enum. It does not recompute or validate:

- interface `schema_hash`;
- current-run manifest hash;
- request hash;
- normalized-query identity hash;
- candidate IDs and canonical product identities from their frozen preimages;
- candidate evidence-path hashes;
- trace candidate/transform/site/ledger equality with the candidate records;
- candidate and nested-record evidence-kind equality with the run header;
- current-run status/failure consistency;
- production capability/authority requirements for `evidence_kind=real`;
- actual P2 truth/isolation authority.

`resolve_authority()` then sets `schema_hash=""` and converts the unverified top-level label directly into P4 authority.

The shipped test fixture at `tests/p4/test_p3_consumer_authority.py:114-184` calls values such as `req_hash`, `manifest_hash` and `id_hash` valid, while all chemistry/snapshot/donor capability flags are false. This tests schema-shaped data, not a verified P3 run.

#### Independent reproduction

```text
forged_public_real_authority:
  status: completed
  classification: real
  completed_without_consumer: true

shallow_current_run_verification:
  capability_available: true
  classification: real
  nested_query_kind: synthetic_fixture
  chemistry_backend_available: false
  manifest_hash: manifest_hash
```

#### Required fix

1. Replace the separately constructible handle with one consumer-produced immutable `P3ConsumptionBundle` (name may differ) that contains:
   - the verified interface identity and schema hash;
   - full frozen `RunNamespace` and component versions;
   - verified current-run artifact hash;
   - immutable candidate map and candidate-content hashes;
   - verified trace/failure/capability state;
   - typed evidence classification;
   - typed blocked reasons when any required verification is unavailable.
2. Production `run_p4_pipeline` must accept that bundle, not a caller-created authority record.
3. If Python-level factory-only construction is used, the pipeline must still validate the bundle's sealed receipt/content digest. Merely renaming the class or prefixing a constructor with `_` is not sufficient.
4. Validate the current-run artifact using the actual frozen P3 schema/models or a strict consumer-side schema that implements the same preimages.
5. Recompute every advertised hash from content. A non-empty hash string is not proof.
6. Require nested classification consistency. A real header with synthetic nested query/candidates/trace must be rejected.
7. `real` must require the real P3 production-authority chain and the required P2/P1 authority receipts. Otherwise return typed BLOCKED.
8. Never derive capability from `source` text alone.

#### Required RED→GREEN tests

- direct public construction of a real authority cannot complete;
- top-level `real` plus nested synthetic is rejected;
- placeholder/recomputed-wrong manifest/request/query/candidate/path hashes are rejected one by one;
- false capability flags cannot yield real authority;
- changed status/failures/trace after hash creation is rejected;
- missing schema hash remains BLOCKED;
- real authority without verified P2/P1 receipt remains BLOCKED;
- valid synthetic fixture bundle remains usable only for machinery and never becomes real.

### P4-R2-B — candidates, evidence observations and namespace are not bound to one verified artifact bundle (P0)

#### Evidence

`reaction_agent/inference/predictor.py:143-163` accepts five independently caller-supplied objects:

- `query`;
- `evidence_records`;
- `candidates`;
- `structural_contexts`;
- `feature_evidence_ids`;

plus an authority handle that contains no candidate map. Nothing proves that the candidate ranked by P4 exists in the P3 artifact that supposedly granted authority.

The adapter-level fallback was correctly removed, but `PipelineOutcome._enriched_candidates()` reconstructs its candidate map from the same caller-supplied candidates. Therefore it checks consistency against P4's own input, not against P3's verified output.

`_validate_namespace_binding()` at `predictor.py:90-115` compares a query field only **if present**. Missing run/query/case/fold/snapshot hash and policy are accepted. Evidence records are checked only for `snapshot_id`; they do not bind snapshot hash, fold view, case, query, run, policy or source-view authority. Candidate and trace namespaces are not checked there at all.

Feature values still originate in caller-provided `structural_contexts`. `feature_evidence_ids` proves only that an ID exists in the resolution; it does not prove that the identified evidence produced the supplied ordinal value. This is a useful fixture interface, but not yet a production evidence authority.

#### Independent reproduction

```text
candidate_not_bound_to_p3_artifact:
  p3_candidate_ids: [cand_ox_001]
  submitted_candidate_id: cand_not_in_p3_artifact
  ranked_ids: [cand_not_in_p3_artifact]
  status: completed

missing_request_namespace_accepted:
  submitted_fields: [fold_view_id, query_smiles, snapshot_id]
  status: completed
```

#### Required fix

1. Candidate selection must come from the verified immutable P3 bundle. Do not accept an independent production `candidates` list.
2. Every ranked candidate must exact-match a P3 candidate by ID and decision-relevant content, including canonical product, lane, validation, transform/site/path/ledger lineage, namespace and evidence kind.
3. Production requests must carry every frozen namespace field. Missing is an error, not a wildcard.
4. Bind evidence to the accepted P1 snapshot and P2 fold/view authority using snapshot ID **and hash**, fold ID/view, case/query/run IDs, policy/config/component versions and evidence-manifest hash.
5. Replace raw production `structural_contexts` and `feature_evidence_ids` with typed, content-addressed feature observations. Each observation must bind:
   - candidate ID/content hash;
   - evidence IDs/content hashes;
   - namespace/fold/snapshot;
   - derivation component/version;
   - ordinal value and its deterministic derivation receipt.
6. Synthetic fixture builders may retain convenience inputs, but they must enter through an explicitly synthetic fixture adapter that cannot be relabeled or used by the real Gate.
7. Derive trace candidates/transform/site/ledger IDs from the verified bundle and final adjudication, not independent caller lists.

#### Required RED→GREEN tests

- P3 contains candidate A, caller attempts candidate B → reject;
- same candidate ID with changed product/validation/path/ledger → reject;
- missing any namespace field → reject;
- cross-snapshot-hash/fold/view/case/query/run/policy/component → reject;
- valid evidence ID plus invented feature value → reject;
- observation for another candidate/fold/snapshot → reject;
- synthetic bundle cannot be consumed as real;
- permutation of one valid verified candidate set remains deterministic.

### P4-R2-C — a hash-invalid active run can be frozen (P0)

#### Evidence

`reaction_agent/runtime/run.py:74-81` correctly verifies on initial `create()`.

But:

- `mutate()` at lines 95-102 replaces fields without recomputing or verifying `result_hash`;
- `freeze()` at lines 88-93 changes the freeze state and stores the object without verifying first;
- the result is a frozen run whose hash fails verification.

This violates the advertised immutable/content-addressed contract and can contaminate replay or P5 benchmark inputs.

`ImmutableRunManifest.classification` and `capability_status` also remain free strings at `reaction_agent/schemas/p4/run.py:51-53`, rather than the frozen typed vocabulary.

#### Independent reproduction

```text
freeze_unverified_mutation:
  freeze_state: frozen
  post_freeze_verify: RunHashMismatchError
```

#### Required fix

Choose one coherent model and test it:

1. Preferred: remove in-place semantic mutation. Any changed result becomes a new child run with a new run ID, parent ID, recomputed hashes and full verification.
2. If active mutation must remain, recompute the result hash from the updated content atomically and verify before replacing the store entry. Never allow caller updates to set the hash independently.
3. `freeze()` must verify the current run before transition and verify the frozen representation before storing. On failure, leave the original entry unchanged.
4. Make classification/capability typed and include their exact values in the hash preimage.
5. Add failure-atomicity tests: after a rejected mutate/freeze, the prior valid run must remain unchanged and verifiable.

#### Required RED→GREEN tests

- valid create → decision mutation → freeze must fail or create a verified child;
- invalid hash cannot enter frozen state;
- failed freeze leaves original active run unchanged;
- caller cannot supply its own replacement result hash;
- nested decision/ranking/support/trace mutation is covered;
- classification outside the frozen enum is rejected.

### P4-R2-D — Gate and mutation receipts can still overstate verification (P0/P1)

#### D1. Gate command depends on ambient `PYTHONPATH`

`scripts/run_p4_gate.py:27` imports `reaction_agent` before inserting `DEMOV2_ROOT` into `sys.path` at line 30. Thus the direct command recorded in `P4_ROUND_2_AUDIT_EVIDENCE.json` fails in a clean environment:

```text
ModuleNotFoundError: No module named 'reaction_agent'
```

The test `test_gate_does_not_fake_pass_with_missing_real_input` then finds and reads a pre-existing Gate report after the subprocess failure. It does not first require the expected exit code `2`, a current session nonce, or a newly created report.

#### D2. G14 accepts arbitrary receipt text

`scripts/run_p4_gate.py:681-704` treats expected status plus any non-empty `receipt_hash` as verified P2 truth authority. It never recomputes the hash or validates the receipt's artifact, namespace, command, current-run identity or P2 Gate execution authority.

Independent result:

```text
status: READY_FOR_CHATGPT_P2_AUDIT
receipt_hash: totally-unverified-string
=> P4-G14 passed: true
```

#### D3. mutation expected-code matching is substring matching

`scripts/run_p4_mutations.py:121-125` concatenates prose evidence and `failure_code`, then checks `expected in evidence_blob`. This is not the claimed exact typed-code match. A mutation with empty typed failure code was counted caught because unrelated prose contained the expected words.

The current Round 2 mutation result records have blank `failure_code` values. Therefore `14/14 CAUGHT` proves that each target check became non-PASS and emitted matching prose, but not that a stable typed invariant caught the intended defect.

#### Required fix

1. Make Gate directly runnable from repo root without ambient `PYTHONPATH`:
   - move path bootstrap before package imports, or
   - standardize on `python -m scripts.run_p4_gate` and record that exact command.
2. Gate contract tests must delete/use a unique temp report, require subprocess return code exactly matching the expected state, and verify report session nonce/run ID belongs to that subprocess.
3. G12/G13 must consume the verified bundle from P4-R2-A, not trust handle fields.
4. G14 must parse and independently validate a typed P2 authority receipt, recompute its content hash, validate namespace/fold/snapshot binding and require accepted current-run execution evidence. If the required P2 artifact does not exist, remain BLOCKED.
5. Every machinery check must emit a stable typed `failure_code` when failing.
6. Mutation success with an expected code must require exact equality:

   ```python
   actual_status == "FAIL" and mutated.failure_code == expected_failure_code
   ```

7. Do not search prose for failure codes.
8. Prefer isolated subprocess mutation cases with per-case execution receipts. At minimum, prove monkeypatch restoration and prohibit shared-state leakage.
9. Keep the honest distinction: fixture machinery may pass while real-input Gate remains BLOCKED.

#### Required RED→GREEN tests

- direct Gate command succeeds in import and returns exit 2 in current blocked environment without ambient `PYTHONPATH`;
- stale prior Gate report cannot satisfy a failed subprocess;
- arbitrary P2 receipt hash is rejected;
- P2 receipt with content changed after hash is rejected;
- empty typed failure code plus matching prose is not caught;
- wrong typed code plus matching prose is not caught;
- exact typed code is caught;
- mutation execution exception remains ERROR, never CAUGHT;
- Gate G12/G13 reject directly constructed handles.

### P4-R2-E — P3→P4 interface selection and ownership are inconsistent (P0 integration blocker)

#### Evidence

The P4 branch adds this P3-owned path:

```text
reports/p3/p3_p4_interface_manifest.json
```

It is byte-identical to P3 Round 6's wrapped `p3-p4-3` artifact:

```text
P4 branch copy sha256:
b6a57963fde874492841aa70f4daa294bf88548c7cfa4a548a7deb87cdb1d8c6

P3 round_6 copy sha256:
b6a57963fde874492841aa70f4daa294bf88548c7cfa4a548a7deb87cdb1d8c6
```

But the current unversioned P3 worktree path has different content:

```text
P3 current unversioned sha256:
efd878ba2de21b7a4b3fa75daf6ecb0ef37ec473591cf9123394bf65a5d392d7
manifest_version: p3-p4-1
```

P3 Round 8 structured evidence embeds `p3-p4-3` with schema hash:

```text
07ab8f71ba3d4e15026ba09d0d2d5f73260ead9e7eaa79ef84f55bac85f63aae
```

Thus P3 itself has a packaging ambiguity between its current unversioned path and the interface embedded in later Round evidence. P4 silently resolved the ambiguity by copying an older round artifact into a P3-owned path. That is not a valid integration decision, especially because the original P4 instruction forbade modifying P3-owned files/contracts.

#### Required fix

1. Do not modify `reports/p3/*` from the P4 worker.
2. The integrator/P3 owner must explicitly publish one canonical accepted P3→P4 interface artifact and its SHA-256/schema hash.
3. P4 should pin that artifact in its dependency/interface manifest by:
   - producer commit;
   - absolute/repo-relative canonical source path;
   - file SHA-256;
   - inner schema hash;
   - manifest version;
   - accepted evidence kind/capability semantics.
4. If P4 needs a test copy, place it only under `tests/fixtures/p4/`, label it `synthetic_fixture`, and record the exact producer hash. It must not masquerade as the live `reports/p3` authority.
5. Until the interface ambiguity is resolved, P4 integration must be typed BLOCKED.
6. Do not change P3 contracts to fit P4 implementation. Adapt P4 to the integrator-selected frozen interface.

#### Required RED→GREEN tests

- mismatch between pinned file hash and actual interface → BLOCKED;
- mismatch between wrapper schema hash and recomputed inner schema hash → BLOCKED;
- stale/unversioned interface version mismatch → BLOCKED;
- fixture interface cannot become live P3 authority;
- canonical accepted interface loads read-only without P4 writing `reports/p3`.

### P4-R2-F — submission receipts do not describe the audited tree accurately (P1)

#### Evidence

1. Submission line 7 reports final HEAD `a85c231...`; observed HEAD is `2f93182...`.
2. `P4_ROUND_2_FINAL_WORKTREE_STATE.md` reports HEAD `309fe5d...`, also stale.
3. `P4_ROUND_2_CHANGED_FILES.json` reports:

   ```json
   {"count": 0, "files": []}
   ```

   but `git diff --name-status 4eb4633..2f93182` contains **77 added files** and `11,605` inserted lines.
4. The submission says no P3 frozen contract was modified, but the branch adds `reports/p3/p3_p4_interface_manifest.json`.
5. The original worker instruction said not to commit; the P4 branch contains multiple P4 commits. They were not pushed or merged, but the scope deviation must be disclosed rather than omitted.
6. Current inherited dirty state includes modified P0/P1 reports and an untracked `no:cacheprovider` path outside the `demov2` directory. The P4 worker must not delete or absorb inherited user changes, but final evidence must distinguish inherited state from P4-created state.
7. The structured command strings omit the environment prefix needed by the current direct Gate script.

#### Required fix

1. Define immutable audit coordinates:
   - `baseline_commit`;
   - `implementation_commit` or audited working-tree diff hash;
   - `deliverables_commit` if reports are committed separately;
   - current HEAD at submission time;
   - exact dirty/untracked state.
2. Generate changed files from `baseline_commit..implementation_commit` plus scoped uncommitted changes, not from an empty post-commit working-tree diff.
3. Do not create another commit after claiming a final HEAD. If report commits are unavoidable, report implementation and deliverable commits separately.
4. Record full commands including relevant environment variables and cwd.
5. Record exit code, started/finished timestamps, stdout/stderr hash, parsed test counts and report artifact hash.
6. Clearly mark inherited dirty files and P4-owned changes. Preserve inherited files; do not modify them to make the tree look clean.
7. Do not push, merge or rewrite history. Do not create additional commits unless the user explicitly authorizes it.

### P4-R2-G — run versions and classifications are not derived from accepted upstream artifacts (P1)

#### Evidence

`reaction_agent/inference/predictor.py:419-428` hardcodes:

```text
kernel_version = p3-blocked
candidate_version = p3-blocked
```

even on a purported `p3_current_run` path. `P3AuthorityHandle.schema_hash` is set to an empty string, `RunNamespace.component_versions` defaults to `{}`, and the consumer does not populate real P3 versions. For a partial query, the manifest may also record `snap_unknown` outside the authority namespace.

This makes replay provenance misleading: a result can claim current P3 capability while its immutable manifest records blocked P3 versions.

#### Required fix

1. Derive P1/P2/P3 snapshot, schema, kernel, candidate and component versions from the verified consumption bundle.
2. Reject missing mandatory version/hash fields in production mode.
3. Use the authority namespace as the single source for snapshot ID/hash; do not fall back to independent query defaults after validation.
4. Type `classification` and `capability_status` in the run manifest.
5. Include interface hash, current-run artifact hash, evidence manifest hash, P2 authority receipt hash and candidate-set hash in the immutable result preimage.
6. Add replay tests showing that changing any upstream version/hash changes run/result identity or causes a typed mismatch.

## 5. Scope controls for Round 3

The Round 3 worker must follow all of these controls:

- Work only in the existing P4 worktree/branch unless the user explicitly changes the location.
- Do not modify P0/P1/P2/P3 implementation, final design/plan/discussion, ADRs or legacy source.
- Do not overwrite the P3 interface path to make P4 pass.
- Do not delete or reset inherited dirty files.
- Do not install dependencies, access the network, invoke external LLM/MCP/Orchestra or generate real performance.
- Do not push or merge.
- Do not create a new commit without explicit user authorization.
- P2 formal authority remains BLOCKED unless a separately accepted P2 artifact is actually available and verified.
- P3 real current-run capability remains BLOCKED unless the canonical accepted artifact and production authority exist.
- Synthetic fixtures may prove machinery only.
- P4 Gate must not PASS from synthetic fixtures.
- P5 remains BLOCKED until ChatGPT accepts P4.

## 6. Required implementation order

Use this order because later fixes depend on earlier contracts:

1. **P4-R2-E:** resolve/pin the canonical P3→P4 interface through an integrator-owned declaration; if unresolved, preserve typed BLOCKED and use only an explicitly labeled fixture for tests.
2. **P4-R2-A:** implement the verified immutable P3 consumption bundle and real/synthetic authority separation.
3. **P4-R2-B:** make candidates, evidence observations and namespace derive from/bind to the verified bundles.
4. **P4-R2-G:** derive versions and all upstream hashes from those bundles.
5. **P4-R2-C:** make run mutation/freeze content-addressed and failure-atomic.
6. **P4-R2-D:** rebuild Gate/G12-G14/mutation receipts on the new authority boundary.
7. **P4-R2-F:** generate accurate Round 3 evidence from immutable audit coordinates.
8. Run the complete regression matrix and only then write the Round 3 submission.

Every item must begin with a RED test that reproduces the exact audit counterexample. A test that only checks a field exists is not sufficient.

## 7. Mandatory verification matrix for Round 3

At minimum run and report:

```bash
PYTHON=/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
W=/Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2
cd "$W"

PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m pytest -q -p no:cacheprovider tests/p4
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m pytest -q -p no:cacheprovider tests/contracts
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m pytest -q -p no:cacheprovider tests/p1
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m pytest -q -p no:cacheprovider tests/p2
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m pytest -q -p no:cacheprovider tests/p3
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m scripts.run_p4_gate
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m scripts.run_p4_mutations
```

If an upstream suite is unavailable in this P4 worktree, report it as an integration blocker with the exact missing path/commit. Do not silently omit it and do not copy upstream implementation into P4.

Additionally, provide explicit machine-readable results for every P4-R2-A through P4-R2-G negative probe. Required properties:

- all expected rejections have typed failure codes;
- no rejection is counted from an uncaught exception unless the contract explicitly defines it as typed system ERROR;
- mutations have PASS-capable baselines;
- expected and observed typed failure codes match exactly;
- no stored status string is accepted as authority;
- report hashes are independently recomputed;
- current run identity and session nonce bind all Gate/mutation receipts.

## 8. Required Round 3 deliverables

Create under `reports/p4/`:

1. `SUBMISSION_TO_CHATGPT_P4_ROUND_3.md`
2. `P4_ROUND_3_AUDIT_EVIDENCE.json`
3. `P4_ROUND_3_REMEDIATION_WORKLOG.md`
4. `P4_GATE_REPORT_ROUND_3.json`
5. `P4_GATE_REPORT_ROUND_3.md`
6. `P4_MUTATION_RESULTS_ROUND_3.json`
7. `p4_p5_interface_manifest_round_3.json`
8. `P4_ROUND_3_CHANGED_FILES.json`
9. `P4_ROUND_3_STARTING_WORKTREE_STATE.md`
10. `P4_ROUND_3_FINAL_WORKTREE_STATE.md`
11. `P4_ROUND_3_COUNTEREXAMPLE_RESULTS.json`
12. `P4_ROUND_3_UPSTREAM_INTERFACE_PIN.json`

The changed-files report must show base-to-audit-target changes and must not report zero merely because files were committed.

The submission must answer P4-R2-A through P4-R2-G one by one with:

- original RED command/result;
- code change;
- focused GREEN command/result;
- adversarial/mutation result;
- exact changed files;
- remaining blocker, if any;
- whether evidence is synthetic, diagnostic, blocked or real.

## 9. Allowed final status

Given the currently absent real P3/P2 authority, the expected honest terminal line is:

```text
P4_ROUND_3_IMPLEMENTATION_COMPLETE_REAL_GATE_BLOCKED_READY_FOR_CHATGPT_AUDIT
```

Use `READY_FOR_CHATGPT_P4_READ_ONLY_AUDIT` only if every real-input authority is actually present and independently verified in the current run. Do not claim P4 Gate PASS from fixture machinery.

P5 must remain BLOCKED pending the next ChatGPT P4 audit.

## 10. Concise handoff instruction for the implementation agent

Read this entire file and implement every mandatory P4-R2-A through P4-R2-G remediation in the specified order. Start with the included independently reproduced RED cases, preserve upstream/user files, keep real Gate honestly BLOCKED when authority is absent, generate all Round 3 deliverables, and stop with P5 BLOCKED for ChatGPT read-only audit.

```text
CHATGPT_P4_ROUND_2_READ_ONLY_AUDIT_FAIL
P4_ROUND_3_REMEDIATION_REQUIRED
P5_BLOCKED
```
