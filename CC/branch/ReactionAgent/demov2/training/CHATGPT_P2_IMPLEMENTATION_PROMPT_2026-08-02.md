# ChatGPT Prompt — Implement ReactionAgent P2 Safely and Prepare a Read-Only Audit Submission

> Intended recipient: a fresh AI coding-agent window with no prior conversation memory  
> Target: ReactionAgent demov2 P2 — mini snapshot, truth, fold isolation, funnel, baselines, and non-oracle pilot contracts  
> Starting authority: P0 and P1 are accepted; P2 is unblocked for implementation  
> Scientific rule: fixture evidence must never be presented as real audit or real performance  
> Git rule: do not commit, push, merge, reset, stash, clean, or overwrite user work  
> External rule: no network, dependency installation, Orchestra dispatch, or real LLM/provider call without explicit authorization

---

## 0. Mandatory first action

Read this entire prompt before taking action.

Your job is to implement the P2 code and tests that are scientifically safe to implement now, run proportionate local verification, and prepare a submission for ChatGPT read-only audit.

You must distinguish four different outcomes:

1. implementation code/tests are complete;
2. synthetic contract fixtures pass;
3. real audited P2 evidence is available;
4. the formal P2 Gate passes.

These are not interchangeable.

If the repository lacks 20–50 genuinely audited real cases or lacks the downstream strict-kernel capability needed for a real non-oracle pilot, implement all independent P2 machinery and tests, then report the exact Gate item as BLOCKED. Do not fabricate real evidence, performance, or PASS.

---

## 1. Target worktree

Perform all implementation in this isolated worktree:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra
~~~

Expected branch and commits at prompt creation:

~~~text
branch: codex/p2-orchestra
93a541a docs(p2a): add compact Orchestra worker context
55eab3e chore(p2): snapshot accepted ReactionAgent P1 baseline
working tree: clean
~~~

The demov2 project root is:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2
~~~

Before editing:

1. confirm the Git root;
2. confirm branch and HEAD;
3. run a read-only Git status check;
4. read all applicable AGENTS.md files;
5. confirm the target worktree is clean;
6. inventory existing P0/P1 code, tests, reports, scripts, and virtual environment;
7. do not assume the expected state if actual files disagree.

If this worktree is dirty:

- stop;
- list exact changed files;
- do not reset, stash, discard, or overwrite;
- ask the user how to proceed.

Do not implement P2 in the original dirty worktree:

~~~text
/Volumes/CC/Enzyme_Agent/depending
~~~

That path is a read-only source/reference for this task unless the user explicitly changes the authorization.

---

## 2. Authoritative documents

Read completely before designing P2 code:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2/plan/final_design.md
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2/plan/final_plan.md
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2/plan/final_discussion.md
~~~

Read the accepted P1 handback:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2/reports/p1/SUBMISSION_TO_CHATGPT_P1_FINAL_PASS.md
~~~

Read the bounded P2A interface contract:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2/docs/orchestra/P2A_COMPACT_CONTEXT.md
~~~

Read all P0 ADRs:

~~~text
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0001-authority-and-scope.md
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0002-hypothesis-lanes.md
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0003-ledger-and-source-semantics.md
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0004-partial-eligibility.md
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0005-scientific-decision-authority.md
/Users/frank_gong/Documents/Codex/2026-07-13/new-chat/ReactionAgent-p2-orchestra/CC/branch/ReactionAgent/demov2/docs/decisions/ADR-0006-mcp-side-effects.md
~~~

Authority order:

~~~text
final_design.md
→ final_plan.md
→ final_discussion.md
→ ADRs and accepted P1 contracts
→ P2A_COMPACT_CONTEXT.md as a bounded implementation clarification
→ current code/tests
→ historical model plans only as non-authoritative reference
~~~

Do not modify final_design.md, final_plan.md, final_discussion.md, or ADRs to make implementation easier.

If a genuine conflict is discovered:

1. stop the affected implementation;
2. document the exact conflict;
3. propose an ADR/design correction;
4. do not silently change product semantics.

---

## 3. Accepted P1 baseline

P1 final acceptance recorded:

~~~text
standalone full test suite: 906 passed
fail/error/skip/xfail/xpass: 0/0/0/0/0
P0 Gate: 10/10 PASS
P1 Gate: 10/10 PASS
P1 Gate mutations: 91/91 caught
G10 Round 3 agreement: 44/44 = 1.0
G10 H1–H7: PASS
G10 Q1–Q4: PASS
~~~

P1 is the sole data authority for:

- snapshot identity and content hashes;
- complete reaction evidence;
- participant roles;
- formal mapping status;
- fragment-lineage resolution;
- source ledgers;
- candidate-ledger skeleton contracts;
- eligibility decisions;
- quarantine;
- provenance;
- production/diagnostic/quarantine index boundaries.

P2 must consume P1 authority. It must not create a second incompatible snapshot, mapping, lineage, ledger, or eligibility vocabulary.

P1 acceptance does not mean that real P2 truth or a P3 strict kernel already exists.

---

## 4. P2 objective

Implement the frozen P2 phase:

~~~text
P2-T1 Mini snapshot
P2-T2 Multi-answer truth
P2-T3 Fold-specific views and leakage isolation
P2-T4 Stage funnel
P2-T5 Baseline contracts and executable baselines where dependencies exist
P2-T6 Non-oracle pilot runner and preregistration
P2 Gate with eight checks and anti-false-positive resistance
~~~

The formal P2 purpose is:

- validate a small but trustworthy train/test evidence chain;
- prevent test-label leakage;
- preserve all X in the denominator;
- support multi-answer truth;
- expose where the scientific pipeline fails;
- compare fair train-only baselines;
- run a non-oracle pilot when all required capabilities and real evidence exist;
- make an honest Go/No-Go decision.

P2 is evaluation authority. It must not silently implement or redefine P3 strict chemical execution.

---

## 5. Non-negotiable scientific rules

1. User/runtime input is X only.
2. Donor selection must be automatic and train-only in a formal pilot.
3. Test reactions, test evidence, and test labels are not runtime resources.
4. All X remain in the denominator, including invalid, OOD, failed, abstained, no-donor, and incomplete-truth cases.
5. Multi-answer truth must not collapse to one preferred SMILES.
6. Chemical equivalence must use audited/precomputed identity keys or an authorized chemistry backend, never ad-hoc string heuristics.
7. Incomplete truth is retained but not scored as hit or miss.
8. Oracle donor is diagnostic-only and cannot contaminate primary metrics.
9. Fixture results are contract evidence only.
10. A fixture cannot satisfy the real 20–50 audited-case requirement.
11. No unaudited generated label may become ground truth.
12. Database absence is not a negative reaction label.
13. Formal mapping is not mechanistic atom origin.
14. COFACTORS remain role/retrieval priors, never destructive deletion rules.
15. P2 evaluation code cannot create or repair SMILES.
16. Scientific non-evaluability and infrastructure/system failure remain distinct.
17. Do not predeclare T accuracy, Y accuracy, or other performance thresholds not established by real data.
18. Old 41.5%, 23.5%, 79.5%, A1/A2, or legacy metrics remain provisional.
19. Formal P2 PASS requires current-run evidence for all eight Gate items.
20. A status string cannot promote a failing or blocked Gate.

---

## 6. Authorization boundary

This prompt authorizes:

- P2 code, schemas, scripts, tests, synthetic fixtures, reports, and manifests inside demov2;
- local test execution using already available dependencies and virtual environments;
- read-only inspection of legacy/P1 evidence needed to bind interfaces;
- generation of honest synthetic contract fixtures labeled synthetic;
- generation of real-candidate inventories from existing real sources without silently declaring them audited truth;
- writing P2 preflight and BLOCKED/FAIL/PASS reports.

This prompt does not authorize:

- network access;
- package installation or upgrade;
- real LLM/provider calls;
- Orchestra dispatch;
- modifying model endpoints or credentials;
- writing legacy source;
- modifying original raw datasets;
- modifying frozen final documents or ADRs;
- modifying P0/P1 evidence or changing their PASS strings;
- commit, push, merge, PR creation, or worktree deletion;
- destructive Git operations;
- fabricating manual annotation;
- claiming a real audit was performed by a synthetic test;
- implementing P3/P4/P5 under P2 names.

If a missing dependency, human audit, mapper, real truth annotation, or strict-kernel capability is required for a formal Gate item, report BLOCKED and continue with independent P2 code that can safely be completed.

---

## 7. Required P2 architecture

Prefer the existing final-plan package separation. Adjust names only when necessary and document the reason.

Expected additions may include:

~~~text
reaction_agent/schemas/evaluation.py
reaction_agent/evaluation/__init__.py
reaction_agent/evaluation/truth.py
reaction_agent/evaluation/isolation.py
reaction_agent/evaluation/funnel.py
reaction_agent/evaluation/baselines.py
reaction_agent/evaluation/pilot.py
reaction_agent/evaluation/reports.py
reaction_agent/evidence/mini_snapshot.py
scripts/p2_preflight.py
scripts/build_mini_benchmark.py
scripts/run_pilot.py
scripts/run_p2_gate.py
scripts/run_p2_mutations.py
tests/p2/
tests/fixtures/p2/
reports/p2/
~~~

Do not create duplicate synonyms for existing P1 types.

All new Pydantic schemas must inherit:

~~~python
reaction_agent.schemas.common.StrictModel
~~~

They must preserve:

- extra=forbid;
- strict typing;
- assignment/default validation;
- no unknown fields;
- no confidence, LLM confidence, biological probability, enzyme probability, or similar forbidden fields.

Use existing:

~~~python
reaction_agent.hashing.canonical_hash
reaction_agent.hashing.stable_id
reaction_agent.schemas.p1_entities.SnapshotManifest
reaction_agent.schemas.p1_entities.SnapshotRecord
reaction_agent.snapshot.loader.load_snapshot
~~~

Do not duplicate P1 hashing or loader logic.

---

## 8. P2A — Strict evaluation schemas and multi-answer truth

Implement strict types for at least these concepts. Exact class names may differ if clearer.

### 8.1 Audited product identity

A product identity should be able to carry precomputed audited keys for:

- canonical/exact identity;
- stereo-aware identity;
- stereo-agnostic identity;
- tautomer-family identity;
- salt/neutralized-family identity;
- multi-product component-set identity where applicable.

Requirements:

- P2 evaluation selects among supplied keys according to policy.
- Missing keys never fall back to raw string guessing.
- Evaluation code does not generate chemistry structures.
- Identity source/provenance and policy version are preserved.

### 8.2 Truth policy

Use controlled enums for:

- exact comparison;
- stereo-aware comparison;
- stereo-agnostic comparison;
- tautomer-equivalent comparison;
- salt/neutralization-equivalent comparison;
- multi-product target semantics.

Do not use unconstrained free-text policy modes.

### 8.3 Truth record

A truth record must bind:

- case_id;
- query_id;
- fold_id;
- snapshot_id;
- snapshot_hash;
- truth policy version;
- allowed_product_set;
- context tags;
- annotation completeness;
- explicit incomplete reason codes;
- source/provenance;
- multi-product policy;
- stereo policy;
- audit status.

Complete truth must have at least one allowed product target.

Incomplete truth remains in the all-X case registry but is not scoreable.

### 8.4 Prediction binding

Candidate evaluation input must bind:

- case_id;
- query_id;
- fold_id;
- snapshot ID/hash;
- truth policy version;
- frozen candidate IDs;
- precomputed candidate identity keys;
- run/prediction identifier.

Reject cross-case, cross-query, cross-fold, cross-snapshot, and cross-policy scoring.

Duplicate candidate IDs must not inflate results.

### 8.5 Match result

Distinguish:

~~~text
matched
not_matched
not_evaluable
~~~

Record:

- matched candidate ID;
- matched truth target ID;
- equivalence rule used;
- non-evaluable reason;
- candidate count before/after deduplication;
- binding identities.

Do not overload a boolean to represent all states.

---

## 9. P2B — Fold-specific views and leakage isolation

Implement three separate capabilities:

~~~text
train evidence view
validation/calibration view
test label view
~~~

Do not create one permissive object with optional labels.

### 9.1 Train view

May expose:

- train donor/evidence handles;
- safe snapshot/fold metadata;
- train-only source/reaction/evidence IDs;
- cache identity;
- retrieval/scoring reference handles.

Must not expose:

- test query IDs;
- test truth records;
- allowed test products;
- test reaction/evidence IDs;
- label serialization.

### 9.2 Validation/calibration view

May expose validation/calibration handles for model selection or calibration.

Must not expose test labels.

### 9.3 Test-label view

A separate evaluation-only capability available only after predictions are frozen.

The runtime/retrieval API must not accept it.

### 9.4 Split manifest

Bind:

- snapshot ID/hash;
- fold ID;
- split version;
- split manifest hash;
- train/validation/test query IDs;
- train/validation/test source reaction IDs;
- train/validation/test evidence IDs;
- provenance;
- audit completeness.

Reject:

- duplicates within a partition;
- overlaps across forbidden partitions;
- unknown partition names;
- caller-forged split hash;
- snapshot mismatch.

Semantically set-like collections must produce stable identities independent of input ordering.

### 9.5 Cache keys

Cache identity must include:

- fold ID;
- snapshot hash;
- split manifest hash;
- partition kind;
- resource kind;
- relevant policy version.

Cross-fold or cross-snapshot reuse must fail.

### 9.6 Leakage audit

Compute leakage findings from authoritative sets. Do not trust a stored leakage=0 string.

Report overlap separately for:

- query identity;
- reaction identity;
- evidence identity;
- source/provenance identity where supported;
- product/truth identity where appropriate.

Leakage zero must be derived from findings.

Distinguish:

~~~text
zero_detected_overlap
audit_complete
~~~

Empty identity sets do not prove a complete audit.

---

## 10. P2-T1 — Mini snapshot

The formal real mini snapshot must contain 20–50 audited cases and cover, as supported by real evidence:

- single reactant;
- multiple reactants;
- single product;
- multiple products;
- oxidation/reduction;
- hydroxylation;
- hydrolysis;
- transfer;
- cleavage;
- multiple compatible sites;
- no compatible site;
- OOD;
- mapping ambiguity;
- invalid input;
- equivalent SMILES;
- stereo;
- known lineage regressions.

Requirements:

1. test X and labels are independent from train evidence;
2. train evidence contains no test reactions;
3. difficult cases are retained when grouping fails;
4. all cases have stable identity and provenance;
5. each claimed coverage tag is derived from serialized evidence or audited annotation;
6. no synthetic fixture is counted as a real audited case;
7. no real case is labeled audited without the required audit records;
8. snapshot and split identities are content-addressed;
9. before/after counts and every exclusion reason are recorded;
10. P1 eligibility/quarantine remains authoritative.

### 10.1 Required preflight decision

Inspect current real evidence and report:

- available real eligible records;
- available real audited truth records;
- mapping/lineage quality;
- whether 20–50 cases can honestly be assembled;
- coverage gaps;
- required human annotations;
- whether test/train separation can be proven;
- whether a strict pilot dependency exists.

If real audited truth is missing:

- implement mini-snapshot schemas, builder, audit validators, fixture tests, and candidate-inventory tooling;
- create a real-candidate inventory if possible;
- mark formal P2 Gate item 1 BLOCKED;
- do not invent truth labels.

### 10.2 Real-versus-fixture manifest

Maintain:

~~~text
reports/p2/fixture_vs_real_evidence_manifest.json
~~~

For every artifact record:

- artifact path;
- evidence kind: real, synthetic_fixture, derived_diagnostic, or protocol_only;
- source snapshot;
- audit status;
- permitted use;
- prohibited claims;
- hash;
- record count.

Gate must validate this manifest rather than trust prose.

---

## 11. P2-T4 — Stage funnel

Record these frozen stages:

~~~text
input_valid
donor_retrieved
correct_donor_available
lineage_resolved
correct_transform_built
correct_site_enumerated
correct_candidate_generated
candidate_validated
candidate_ranked_top_k
answered_or_abstained
~~~

### 11.1 Runtime versus evaluation authority

Prevent leakage by separating:

Runtime trace may record observed execution events without test correctness labels.

Post-run evaluation may add:

- correct_donor_available;
- correct_transform_built;
- correct_site_enumerated;
- correct_candidate_generated;
- ranked correctness;

only after the prediction/run is frozen and through the test-label evaluation capability.

Runtime retrieval code must never access those correctness labels.

### 11.2 Funnel invariants

- every registered X has exactly one funnel record;
- stages are ordered and monotonic where logically required;
- first miss has exactly one primary reason;
- additional reasons may be secondary but cannot replace the primary reason;
- invalid/OOD/no-donor/no-lineage/no-site/no-candidate/failed/abstained cases remain visible;
- system failure is not scientific abstention;
- incomplete truth is not scored as a scientific miss;
- denominator is derived from the case registry, not successful predictions;
- duplicate run/case records are rejected;
- unknown stages are rejected;
- stale report-only status cannot pass.

Use controlled reason enums, not arbitrary strings.

---

## 12. P2-T5 — Baselines

Freeze these baseline identities:

1. random order;
2. generation order;
3. nearest donor;
4. fixed Morgan top-K;
5. legacy template;
6. deterministic strict kernel;
7. oracle donor upper bound, diagnostic-only.

### 12.1 Baseline contract

Every baseline run records:

- baseline ID and version;
- fold/snapshot/split identity;
- train-only resource identity;
- input case registry identity;
- configuration hash;
- seed where randomness exists;
- donor policy;
- oracle flag;
- output run hash;
- failure/tool/cost counters;
- all-X denominator;
- execution availability.

### 12.2 Fairness rules

- primary baselines receive only X at runtime;
- retrieval references are train-only;
- random seed is explicit and reproducible;
- generation order cannot access truth;
- nearest donor cannot use test reaction identity;
- fixed Morgan configuration is frozen;
- legacy baseline limitations are documented;
- deterministic strict-kernel baseline must use an actual available kernel, not a fixture result;
- oracle donor results are stored in a separate diagnostic namespace;
- oracle results cannot enter primary metrics or Go/No-Go performance.

### 12.3 Missing P3 capability

P3 strict one-step kernel is a downstream stage in final_plan.

Do not implement P3 secretly inside P2.

If deterministic strict-kernel execution is unavailable:

- implement and test the capability interface;
- mark baseline availability false with a typed blocker;
- do not generate fake outputs;
- mark affected pilot/Gate items BLOCKED;
- document the dependency explicitly.

---

## 13. P2-T6 — Non-oracle pilot

Formal pilot requirements:

- runtime input is X only;
- donor retrieval is automatic;
- train-only donor evidence;
- no human donor hint;
- no human transformation hint;
- no human site hint;
- run configuration is frozen;
- stage/failure/tool/cost records are complete;
- oracle upper bound is executed and reported separately, if available;
- all X remain in denominator;
- real audited mini snapshot and frozen split are used;
- P1 snapshot identity is bound;
- no test label enters runtime resources.

### 13.1 Pilot preregistration

Before any real pilot, write:

~~~text
reports/p2/pilot_preregistration.md
~~~

It must freeze:

- exact snapshot and split;
- case count;
- inclusion/exclusion rules;
- truth policies;
- all-X denominator;
- baseline configurations;
- primary versus diagnostic outputs;
- unavailable capabilities;
- failure taxonomy;
- metrics to report;
- no unproven performance threshold;
- stop conditions;
- report paths.

### 13.2 Honest pilot blocking

If the 20–50 real audited mini snapshot is unavailable, or the necessary automatic donor/strict-kernel capability does not exist:

- do not run a synthetic fixture and name it a formal pilot;
- run only protocol/unit/integration smoke tests;
- mark pilot result BLOCKED;
- record the exact missing capability/evidence;
- keep code/test completion distinct from formal scientific completion.

---

## 14. P2 Gate

Implement a P2 Gate with these eight frozen checks:

1. Mini snapshot audited.
2. Leakage equals zero.
3. Multi-answer truth operational.
4. All X denominator enforced.
5. Funnel operational.
6. Donor automatic.
7. Oracle separated.
8. Pilot report and Go/No-Go decision exist and are valid.

### 14.1 Gate evidence rules

Each Gate item must:

- validate current-run machine-readable evidence;
- bind report hashes and source artifact hashes;
- reject missing files;
- reject stale run IDs;
- reject status-only promotion;
- reject real/fixture mislabeling;
- reject upstream P0/P1 failure;
- reject contradictory Markdown/JSON;
- distinguish PASS, FAIL, and BLOCKED;
- include a reason and evidence paths;
- avoid overwriting historical evidence silently.

Overall formal PASS requires all eight items PASS.

A BLOCKED item cannot be promoted to PASS because implementation code exists.

An implementation FAIL cannot be hidden by a real-evidence BLOCKED status.

### 14.2 Anti-false-positive mutation tests

At minimum create mutations for:

1. change Gate status string to PASS without evidence;
2. delete real-audit manifest;
3. relabel fixture as real;
4. drop a failed X from denominator;
5. inject train/test query overlap;
6. inject train/test reaction overlap;
7. inject train/test evidence overlap;
8. remove a second valid truth product;
9. score incomplete truth as a miss;
10. use raw-SMILES string fallback for missing audited key;
11. leak test labels through train-view serialization;
12. remove fold ID from cache key;
13. copy oracle results into primary metrics;
14. mark donor automatic while a donor hint is present;
15. mark pilot complete without strict-kernel capability;
16. use stale snapshot hash;
17. use stale split manifest hash;
18. make funnel miss reason empty or multiple-primary;
19. convert a system failure into abstention;
20. remove P1 snapshot authority binding;
21. corrupt report hash;
22. remove pilot preregistration;
23. contradict JSON and Markdown verdict;
24. fail P0/P1 upstream while leaving P2 PASS;
25. delete a required Gate artifact.

Mutation runner must report caught/escaped/error distinctly.

Formal Gate cannot PASS with any escaped anti-false-positive mutation.

---

## 15. Required tests

Write tests before implementation where practical.

### 15.1 Schema/strictness

- unknown fields rejected at every nesting level;
- strict coercion rejected;
- forbidden confidence/probability fields absent;
- controlled enums enforced;
- complete truth with empty allowed set rejected;
- invalid cross-field combinations rejected;
- snapshot/fold/policy binding required.

### 15.2 Truth

- multiple allowed products;
- exact identity;
- stereo-aware;
- stereo-agnostic;
- tautomer equivalence;
- salt/neutralization equivalence;
- multi-product target;
- incomplete annotation;
- missing audited equivalence key;
- duplicate candidate IDs;
- cross-case/fold/snapshot/policy rejection;
- no raw string heuristic fallback.

### 15.3 Isolation

- train/validation/test disjointness;
- query/reaction/evidence overlap detection;
- test labels inaccessible to train view;
- serialization hides test fields;
- unknown partitions rejected;
- cache key includes fold/snapshot/split/partition/resource;
- order-invariant set hashes;
- caller cannot forge leakage zero;
- audit_complete independent of zero overlap.

### 15.4 Mini snapshot

- 20 minimum and 50 maximum enforced for formal real manifest;
- synthetic fixtures cannot satisfy real audit;
- audit records required for real claim;
- hard cases retained;
- coverage tags validated;
- P1 snapshot hash mismatch rejected;
- eligibility/quarantine authority preserved;
- content-addressed reproducibility.

### 15.5 Funnel

- exactly one record per X;
- all-X denominator;
- ordered stage invariants;
- exactly one primary miss reason;
- system failure separated;
- incomplete truth not scored;
- post-run correctness enrichment cannot enter runtime;
- duplicate case/run rejected.

### 15.6 Baselines/pilot

- automatic donor contract;
- no donor/transform/site hints;
- train-only resource binding;
- random seed determinism;
- oracle namespace separation;
- oracle cannot enter primary metrics;
- unavailable strict kernel returns typed blocker;
- formal pilot rejects synthetic-only evidence;
- preregistration required.

### 15.7 Gate/mutations

- eight checks;
- current-run binding;
- report/JSON coherence;
- PASS/FAIL/BLOCKED aggregation;
- all mutations above caught;
- upstream P0/P1 required;
- stale artifacts rejected.

### 15.8 Regression

Run all existing P0/P1 tests unchanged.

Do not delete, skip, xfail, or weaken existing tests to make P2 pass.

---

## 16. Required reports and manifests

Create:

~~~text
reports/p2/P2_PREFLIGHT.md
reports/p2/P2_PREFLIGHT.json
reports/p2/P2_IMPLEMENTATION_WORKLOG.md
reports/p2/P2_GATE_REPORT.md
reports/p2/P2_GATE_REPORT.json
reports/p2/P2_MUTATION_RESULTS.json
reports/p2/SUBMISSION_TO_CHATGPT_P2.md
reports/p2/mini_snapshot_manifest.json
reports/p2/mini_snapshot_audit.md
reports/p2/mini_snapshot_audit.json
reports/p2/fixture_vs_real_evidence_manifest.json
reports/p2/split_manifest.json
reports/p2/leakage_audit.md
reports/p2/leakage_audit.json
reports/p2/pilot_preregistration.md
reports/p2/pilot_funnel.json
reports/p2/pilot_results.md
reports/p2/pilot_go_no_go.md
reports/p2/cross_stage_interface_manifest.json
reports/p2/dependency_matrix.md
reports/p2/merge_ownership.md
reports/p2/integration_worklog.md
~~~

Only create a report when its producer exists. A missing formal artifact must remain missing or BLOCKED rather than be filled with invented content.

### 16.1 P2 preflight

Record:

- repository/branch/HEAD;
- Python/interpreter path;
- dependency availability;
- P0/P1 baseline verification;
- P1 snapshot ID/hash;
- real eligible record count;
- real audited truth count;
- candidate coverage;
- strict-kernel availability;
- automatic donor retrieval availability;
- blocker list;
- fixture-versus-real boundary;
- safe tasks that can proceed.

### 16.2 Cross-stage interface manifest

P1 snapshot/lineage/ledger/eligibility remains the only data authority.

Record proposed P2 outputs consumed downstream:

- fold/split manifest;
- truth view;
- leakage report;
- case registry;
- funnel;
- baseline/pilot run manifests;
- P2 Gate status.

Do not predeclare P3/P4/P5 authority.

---

## 17. Execution order

Follow this sequence.

### Step 1 — Read-only preflight

- verify clean worktree;
- read authorities;
- inventory P1 API and reports;
- identify existing virtual environment;
- inspect real evidence availability;
- inspect strict-kernel/automatic donor capability;
- write P2 preflight;
- do not install dependencies.

### Step 2 — Freeze internal P2 interfaces

Before broad implementation:

- define schema names and ownership;
- define real/fixture evidence types;
- define split/fold capabilities;
- define truth policy;
- define funnel runtime/evaluation separation;
- define baseline and pilot availability statuses;
- define Gate evidence schema.

Write RED contract tests.

### Step 3 — P2A truth and isolation

Implement:

- strict evaluation schemas;
- multi-answer truth;
- pure matching;
- split manifests;
- capability-separated views;
- cache identities;
- leakage audit.

Run focused tests and P0 contracts.

### Step 4 — P2B mini-snapshot tooling

Implement:

- formal manifest validators;
- real/fixture boundary;
- audit record requirements;
- coverage inventory;
- candidate selection tooling;
- reproducible hashes;
- fixture tests.

If real audit inputs are missing, mark formal item BLOCKED.

### Step 5 — P2C funnel/baseline/pilot contracts

Implement:

- all-X case registry;
- runtime funnel;
- post-run correctness evaluator;
- primary miss reasons;
- baseline registry;
- train-only binding;
- oracle separation;
- pilot preregistration and runner;
- capability-unavailable blockers.

Do not fake P3.

### Step 6 — P2D Gate and mutation resistance

Implement:

- eight Gate checks;
- current-run evidence binding;
- PASS/FAIL/BLOCKED aggregation;
- report coherence;
- mutation runner;
- anti-false-positive tests.

### Step 7 — Integration verification

Run:

- P2 focused tests;
- all P0/P1/P2 tests;
- P0 Gate;
- P1 Gate;
- P2 Gate;
- P1 mutations if proportionate/required;
- P2 mutations;
- static checks;
- git diff --check.

### Step 8 — Submission

Write SUBMISSION_TO_CHATGPT_P2.md with evidence matching the current worktree.

Do not call P2 PASS unless the formal Gate really passes.

---

## 18. Multi-agent option

If your platform supports subagents, you may use a bounded team:

### Agent A — Truth and schema

Owns:

- schemas/evaluation.py;
- truth.py;
- truth tests.

### Agent B — Isolation and leakage

Owns:

- isolation.py;
- split/fold/leakage tests.

### Agent C — Funnel, baseline, and pilot contracts

Owns:

- funnel.py;
- baselines.py;
- pilot.py;
- associated tests.

### Integrator — Mini snapshot, Gate, reports, and final review

Owns:

- mini snapshot tooling;
- scripts;
- Gate;
- mutations;
- shared exports;
- manifests/reports;
- integration.

Rules:

- no two agents edit the same file;
- shared schema decisions are frozen before parallel edits;
- each agent returns changed files, assumptions, tests, and blockers;
- integrator reviews every change;
- formal Gate remains sequential;
- subagents do not install dependencies, call real models, or modify Git state.

If subagents are unavailable, execute the same ownership sequence serially.

---

## 19. Test interpreter and dependencies

First discover the actual available interpreter.

An existing accepted P1 virtual environment may be available at:

~~~text
/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
~~~

You may use an existing interpreter read-only from the isolated worktree if it resolves correctly, but:

- do not modify that virtual environment;
- do not install packages;
- record the exact interpreter path/version;
- record installed dependency versions used;
- ensure tests import code from the isolated P2 worktree, not the original dirty source;
- verify working directory and PYTHONPATH behavior.

If no suitable interpreter exists, report the dependency blocker and request authorization before installation.

---

## 20. Stop conditions

Stop the affected path and report honestly if:

- target worktree is dirty;
- frozen authorities conflict;
- P1 Gate no longer passes;
- P1 snapshot identity cannot be verified;
- real truth/audit is missing;
- mapping/lineage evidence is not adequate;
- fixture is the only evidence for a real Gate requirement;
- train/test isolation cannot be proven;
- donor selection requires test labels;
- automatic donor capability is unavailable;
- formal pilot requires an unavailable P3 kernel;
- oracle contaminates primary results;
- all-X denominator cannot be reconstructed;
- unknown fields or silent coercion enter schemas;
- a system failure is converted into abstention;
- mutation tests escape;
- dependencies require installation;
- network/real provider access appears necessary.

A blocker does not prevent implementation of independent schemas, pure functions, fixtures, contract tests, or Gate skeletons. Continue safe independent work but do not promote the blocked formal item.

---

## 21. Verification reporting

For every command record:

- exact command;
- working directory;
- interpreter;
- exit code;
- pass/fail/error/skip/xfail/xpass counts;
- duration;
- report/output path;
- whether it modified generated reports.

Model statements are not verification evidence.

At the end, report:

- changed files;
- new tests;
- existing tests modified, with justification;
- real evidence used;
- synthetic evidence used;
- unverified assumptions;
- blockers;
- P0 result;
- P1 result;
- P2 result;
- mutation result;
- Git status;
- whether any dependency/network/model call occurred.

---

## 22. P2 submission requirements

SUBMISSION_TO_CHATGPT_P2.md must include:

1. executive outcome;
2. exact scope implemented;
3. exact scope deferred;
4. authority documents read;
5. starting and ending Git state;
6. changed-file table;
7. P1 snapshot ID/hash;
8. P2 schema/interface summary;
9. truth-policy summary;
10. fold/isolation summary;
11. leakage audit;
12. all-X denominator evidence;
13. funnel summary;
14. mini-snapshot real/fixture classification;
15. baseline availability;
16. automatic donor availability;
17. strict-kernel availability;
18. pilot status;
19. oracle separation evidence;
20. P0/P1/P2 test results;
21. Gate results item by item;
22. mutation results;
23. blocked items;
24. no-network/no-install/no-real-model declaration;
25. final verdict.

Allowed final verdicts:

~~~text
P2_PASS_READY_FOR_CHATGPT_READ_ONLY_AUDIT
P2_IMPLEMENTATION_COMPLETE_GATE_BLOCKED
P2_REMEDIATION_REQUIRED
P2_FAILED
~~~

Use P2_PASS_READY_FOR_CHATGPT_READ_ONLY_AUDIT only when all eight formal Gate items have current-run PASS evidence.

If code/tests are complete but real audit or strict-kernel/pilot dependency is missing, use:

~~~text
P2_IMPLEMENTATION_COMPLETE_GATE_BLOCKED
~~~

Do not end with a generic READY if Gate is blocked.

---

## 23. Definition of implementation complete

Implementation may be called complete when:

- strict schemas exist;
- truth matching is operational;
- split/fold capabilities are isolated;
- leakage audit is computed;
- all-X case registry exists;
- funnel exists;
- baseline/pilot contracts exist;
- mini-snapshot validators exist;
- Gate and mutations exist;
- focused tests pass;
- P0/P1 regressions pass;
- reports honestly classify real versus fixture;
- unavailable formal capabilities are typed blockers.

Formal P2 PASS additionally requires:

- 20–50 genuinely audited real mini-snapshot cases;
- zero proven leakage;
- operational multi-answer truth;
- all-X denominator;
- operational funnel on the real run;
- automatic donor in the real run;
- oracle fully separated;
- valid non-oracle pilot report and Go/No-Go decision;
- no escaped mutation;
- upstream Gates passing.

---

## 24. Final response to the user

Return:

1. concise outcome;
2. absolute path to SUBMISSION_TO_CHATGPT_P2.md;
3. absolute path to P2_GATE_REPORT.md/json;
4. exact test and Gate counts;
5. real versus fixture evidence counts;
6. exact blockers;
7. changed files;
8. Git status;
9. whether installation/network/model calls occurred;
10. final verdict.

Do not commit, push, merge, modify the original worktree, or call a real model.

The last line of your response and submission must be exactly one of:

~~~text
P2_PASS_READY_FOR_CHATGPT_READ_ONLY_AUDIT
P2_IMPLEMENTATION_COMPLETE_GATE_BLOCKED
P2_REMEDIATION_REQUIRED
P2_FAILED
~~~

