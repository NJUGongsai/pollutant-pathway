# ChatGPT P4 Round 3 Read-Only Audit and Round 4 Remediation

**Audit date:** 2026-08-04  
**Audit type:** implementation correctness, scientific provenance and integration-boundary review  
**Audited worktree:** `/Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2`  
**Audited branch:** `worktree-p4-strict-kernel`  
**Audited HEAD:** `2f9318219777288d55652bc213ba80180e484fbf` plus the submitted uncommitted Round 3 working-tree changes  
**Submitted entry:** `reports/p4/SUBMISSION_TO_CHATGPT_P4_ROUND_3.md`  

## 0. Verdict

**P4 Round 3 does not pass the read-only audit. Round 4 directed remediation is required. P5 remains BLOCKED.**

Round 3 made real progress and closed several local machinery defects:

- `tests/p4`: independently reproduced **205 passed**;
- `tests/contracts`: independently reproduced **290 passed**;
- direct module Gate command now runs without ambient `PYTHONPATH`;
- Gate honestly exits `2` with machinery 11/11 PASS and real checks 3/3 BLOCKED;
- mutation runner reports 14/14 and now adjudicates against typed failure-code lists instead of prose substring;
- candidate lists were removed from the public P4 call and candidates are read from a bundle;
- missing query namespace fields are rejected;
- in-place run mutation is removed and freeze is failure-atomic;
- run versions/upstream hash fields are included in replay identity;
- the unresolved P3 interface ambiguity remains honestly BLOCKED.

The remaining blocker is narrower but fundamental: Round 3 replaced the old caller-written handle with several caller-recomputable hashes. A digest proves that content has not changed **since that digest was computed**; it does not prove that the content came from P3, P2, P1, an accepted interface owner or a deterministic scientific derivation. Because the code exposes every constructor and every digest preimage, a caller can change the content and recompute all hashes/receipts/seals. Independent probes then produced a `completed` result labeled `real`, an arbitrary product structure and decisions based on invented feature values.

```text
CHATGPT_P4_ROUND_3_READ_ONLY_AUDIT_FAIL
P4_ROUND_4_REMEDIATION_REQUIRED
P5_BLOCKED
```

## 1. Independent verification summary

### 1.1 Submitted matrix replay

| Check | Independent result | Conclusion |
|---|---:|---|
| `python -m pytest -q -p no:cacheprovider tests/p4` | **205 passed** | Local P4 suite is green. |
| `python -m pytest -q -p no:cacheprovider tests/contracts` | **290 passed** | P0 contract suite is green. |
| `python -m scripts.run_p4_gate` | exit **2** | 11 machinery PASS; G12–G14 honestly BLOCKED. |
| `python -m scripts.run_p4_mutations` | **14/14 CAUGHT** | Exact expected code must appear in `failure_codes`; prose-only matching is closed. |
| P1 suite | submitted result: 300 passed, 48 failed due missing inherited legacy file | Not counted as P4 regression or P4 PASS. |
| P2/P3 suites | absent in this worktree | Integration remains BLOCKED. |

### 1.2 Independent synchronized-recomputation probes

The temporary audit probe was:

```text
/private/tmp/p4_round3_independent_probes.py
```

It modified no repository source or contract. Results:

| Probe | Observed result | Required result |
|---|---|---|
| Relabel synthetic bundle as `real`; create self-hashed P1/P2 receipts; recompute public bundle seal | `completed`, result classification `real`, receipt issues `[]` | Reject/BLOCKED: no accepted upstream execution authority. |
| Change bundle candidate product to `N#N`; recompute candidate content hash, map and bundle seal | `completed`; returned product is `N#N` | Reject: P4 must not accept a caller-authored candidate structure. |
| Change `donor_similarity` ordinal; recompute derivation receipt | Accepted; decision changed to `abstained` | Reject: receipt recomputation is not proof of a scientific derivation. |
| Change evidence reaction/source while retaining evidence ID/snapshot ID | `completed` | Reject: evidence content must match the frozen evidence authority. |
| Construct `P3InterfaceConsumer(..., apply_pin=False)` over local real-labeled fixture and self-hashed receipts | returns `p3_current_run`, `real`, `capability_available=True` | Production bypass must not exist. |
| Remove manifest hash, request hash, identity hash and path hash | consumer still grants synthetic current-run capability | Missing mandatory upstream identities must be typed BLOCKED. |
| Change P4-owned pin status to `accepted` and verify the test fixture as live interface | `verified=True`, no reasons | P4 must not be able to accept its own fixture as the upstream canonical authority. |

These probes directly contradict the submission claims that the consumer is the only bundle producer, that synthetic cannot be relabeled real, that feature values are derivation-authoritative and that the pin is integrator-owned.

## 2. Round 3 finding closure matrix

| Round 2 finding | Round 3 status | Audit conclusion |
|---|---|---|
| P4-R2-A verified authority bundle | **Open** | Tamper-after-seal is detected, but caller can change content and recompute the public seal and receipts. |
| P4-R2-B candidate/evidence/observation binding | **Open** | Candidate list moved into bundle, but bundle, candidate hash, feature receipt and evidence records remain caller-authored/self-hashed. |
| P4-R2-C immutable run/freeze | **Closed for current machinery** | In-place mutation removed; freeze verifies before storing; child hash is recomputed and verified. Keep regression tests. |
| P4-R2-D Gate/mutation receipts | **Partial** | Import and exact typed mutation matching fixed; P1/P2 receipt authority and cross-session binding remain incomplete. |
| P4-R2-E canonical interface pin | **Partial/BLOCKED** | Ambiguity is honestly blocked, but P4 owns the pin declaration and can set it accepted; public bypass remains. |
| P4-R2-F audit coordinates/reporting | **Open** | Changed-file counts and session binding are inconsistent. |
| P4-R2-G versions/upstream hashes | **Closed as replay metadata, not as authority** | Values affect hashes, but their upstream authenticity still depends on R3-A/R3-B. |

## 3. Mandatory findings

### P4-R3-A — bundle, receipts and interface pin are self-attested rather than upstream-authoritative (P0)

#### Evidence

`reaction_agent/schemas/p4/bundle.py:85-158` exposes an ordinary public `P3ConsumptionBundle`, public `compute_seal()` and public `verify_seal()`. The seal is an unkeyed canonical hash over fields the same caller controls. It detects a stale seal after mutation, but the caller can recompute the correct new seal.

`verify_receipts()` calls `_verify_receipt_hash()` at lines 258-272. That function checks only:

- self-consistency of a caller-provided hash;
- presence of any non-empty `run_id`;
- presence of any non-empty `session_nonce`.

It does not prove that the receipt was produced by P1/P2 Gate execution authority. It does not require receipt run/session/snapshot/fold/artifact identities to match the P3 bundle. It does not validate the expected upstream schema, accepted Gate items, command receipt or artifact root.

`P3InterfaceConsumer.__init__` exposes `apply_pin=False` at `reaction_agent/adapters/p3_consumer.py:419-429`. The fixture builder uses the same production consumer with this public bypass. Any caller can therefore bypass the unresolved live pin and make the consumer seal a self-consistent local artifact.

`reaction_agent/adapters/p3_interface_pin.py` calls the pin “integrator-owned”, but the pin is stored and generated under `reports/p4/`, and `status` is just a string in a P4-owned JSON file. `producer_commit`, `canonical_source_path` and `accepted_evidence_kinds` are recorded but not used as acceptance checks. Changing only status/reasons to `accepted` allowed the test fixture file to verify as the live interface.

#### Independent proof

```text
caller_resealed_real_bundle:
  seal_verified: true
  receipt_issues: []
  status: completed
  classification: real
  result_classification: real

public_apply_pin_false_real_bundle:
  source: p3_current_run
  classification: real
  capability_available: true
  blocked_reasons: []

p4_owned_pin_status_flip:
  verified: true
  reasons: []
```

#### Required Round 4 fix

1. Separate production and fixture types and entrypoints. They must not be one enum-labeled Pydantic model:
   - `VerifiedProductionP3Bundle` or equivalent;
   - `SyntheticP3FixtureBundle` or equivalent;
   - production pipeline and synthetic machinery pipeline must be explicit and non-interchangeable.
2. Remove `apply_pin=False` from the production consumer API. Fixture loading must live in a test/fixture-only adapter and produce only the synthetic type.
3. Do not use a public, caller-recomputable content hash as production authority.
4. Introduce an execution-authority or capability boundary analogous to the accepted P3 production/fixture isolation:
   - production consumer verifies the fixed integrator/P3-owned pin and fixed current-run artifact;
   - it registers an independent canonical snapshot with an internal authority registry;
   - the production pipeline requires registry exact-match for the object it consumes;
   - a copied, reconstructed, relabeled or re-sealed object not registered by the verified production consumer is rejected.
5. For restart/persistent use, verify against a P3/integrator-published artifact root and accepted producer commit. P4 must not create or edit the acceptance status.
6. P1/P2 receipts must be validated by their owning frozen authority/verifier, not by a P4-defined generic self-hash function.
7. Require exact cross-binding between every upstream receipt and the P3 bundle:
   - run/case/query/fold/snapshot ID/hash;
   - artifact/root hash;
   - Gate version/schema;
   - execution session/command receipt;
   - expected accepted status and required Gate items.
8. Until actual P1/P2/P3 authority is present, production bundle construction must be impossible and return typed BLOCKED. Synthetic machinery may still run through the separate fixture entrypoint.
9. Keep hashes for integrity/replay, but never describe them as the origin authority by themselves.

#### Required RED→GREEN tests

- caller copies a synthetic bundle, changes classification to real, recomputes every hash/receipt/seal → production rejects;
- caller directly constructs a production bundle → rejects before pipeline execution;
- caller invokes fixture adapter and passes result to production pipeline → rejects by type/authority;
- caller bypasses pin with any public argument/path → no such production path exists;
- P1/P2 self-hashed local dictionaries do not establish authority;
- receipt from a different run/session/fold/snapshot/artifact root rejects;
- accepted receipt with changed command/Gate item rejects;
- unregistered but byte-identical production object rejects if execution authority is required;
- accepted canonical upstream bundle passes only in a controlled integration fixture owned by the verifier, never as `real` evidence.

### P4-R3-B — candidate structures, feature values and evidence content remain caller-recomputable (P0 scientific correctness)

#### Candidate structure

`VerifiedCandidateContent` is publicly constructible. `content_hash` is an unkeyed hash over the same fields the caller can change. `P3ConsumptionBundle.to_candidates()` reconstructs `Candidate` objects without independently checking an upstream P3 authority or recomputing/validating the candidate against a registered P3 artifact.

Round 3 moved candidates inside the bundle, but a caller can change `canonical_product`, recompute `content_hash`, update `candidate_content_hashes`, recompute `sealed_receipt`, and obtain a completed P4 result containing that structure.

Independent proof:

```text
caller_resealed_candidate_structure:
  bundle_seal_verified: true
  status: completed
  products: [N#N]
```

This violates the central scientific contract that P4 ranks candidates produced by P3 and never creates/accepts caller-created chemical structures.

#### Feature observations

`P4FeatureObservation.compute_receipt()` is also a public self-hash. `_validate_observations()` checks equality with that recomputation but does not verify a trusted derivation producer or independently derive the value.

The Round 3 RED test changes `ordinal_value` **without recomputing the receipt**. It does not test the actual audit requirement: a caller changes the value and synchronously recomputes every exposed receipt. That synchronized change was accepted and changed the decision.

`derivation_component` and `derivation_version` are free strings; there is no accepted component registry. `ordinal_value` also lacks a schema constraint to `0..3`.

#### Evidence content

`_validate_observations()` checks only that an evidence ID appears in the submitted list. `evidence_content_hashes` is never used outside its own receipt preimage. The bundle's `evidence_manifest_hash` is derived from P3 trace donor IDs and snapshot metadata, not recomputed against the full submitted `ReactionEvidence` records.

Changing a reaction/source while retaining reaction ID and snapshot ID was accepted and completed:

```text
changed_evidence_same_id_accepted:
  changed_raw_reaction: N#N>>[N-]=[N+]=N
  status: completed
```

Evidence namespace checking still checks only `snapshot_id`; it does not bind full content hash, snapshot hash, fold view, case/query/run identity or accepted P1/P2 manifest root.

#### Counterevidence context

`counterevidence_contexts` remains a raw caller dictionary. Candidate ID and allowed key names are checked, but the values have no upstream/derivation receipt. A caller can therefore introduce or remove allowed conflict contexts without proving their evidence source.

#### Required Round 4 fix

1. The production pipeline must not accept independent `evidence_records`, `feature_observations` or `counterevidence_contexts` from a caller.
2. Consume one verified production input set containing:
   - P3 candidate snapshot exact-matched to the upstream authority registry/root;
   - P1 evidence snapshot/fold-view authority with full record content hashes;
   - P2 isolation/truth receipt where required;
   - candidate-specific feature observations generated by a trusted deterministic component or verified upstream artifact.
3. Prefer deriving P4 features inside P4 from verified candidate/evidence records using versioned pure functions. If a feature is not deterministically available, mark it unobservable; do not accept a caller scalar.
4. If observations are upstream-provided, require them inside the verified authority bundle and exact-match their content against the registered artifact. A self-hash is only an integrity field.
5. Require `evidence_content_hashes` for every bound evidence ID and compare them to canonical hashes of the actual submitted/frozen evidence records.
6. Bind the evidence manifest to full record identities/content, snapshot ID/hash, fold/view, case/query/run and version roots.
7. Candidate IDs, candidate hashes and every required nested path hash must be mandatory and recomputed using the actual frozen P3 preimages. Missing values are BLOCKED, never synthesized by P4.
8. Derive counterevidence from verified evidence records. If a context artifact is necessary, type and bind it through the same authority chain.
9. Add schema bounds and uniqueness:
   - ordinal must be `0..3`;
   - only frozen feature keys accepted;
   - duplicate candidate/feature observations rejected;
   - missing derivation component/version rejected.
10. Keep synthetic convenience builders under the fixture-only entrypoint; their results must remain `synthetic_fixture` and cannot enter production.

#### Required RED→GREEN tests

- change candidate product/validation/path/ledger and synchronously recompute all public hashes → production rejects;
- change feature ordinal and recompute receipt → rejects unless recomputed by the trusted derivation component/authority;
- change evidence content while preserving ID → rejects;
- provide empty/wrong evidence content hashes → rejects;
- evidence from another snapshot hash/fold/view/run/case/query → rejects;
- duplicate conflicting observations in opposite orders → both reject, never last-write-wins;
- ordinal outside `0..3` → typed schema rejection;
- caller-added counterevidence context → rejects without verified context artifact;
- fixture feature/evidence/candidate objects cannot enter the production pipeline.

### P4-R3-C — upstream hash and interface validation remain optional or self-declared (P1)

#### Evidence

`_verify_artifact_hashes()` validates manifest/request/identity/candidate/path hashes only **if the fields are present**. The current-run required-field lists do not require most of these identities. Removing manifest hash, request hash, normalized identity hash and evidence-path hash still granted current-run capability.

```text
missing_advertised_hashes:
  capability_available: true
  classification: synthetic_fixture
  blocked_reasons: []
```

The interface verifier:

- does not require `canonical_source_path` to resolve to the actual verified path;
- does not validate that `producer_commit` is the accepted P3 producer commit;
- does not enforce `accepted_evidence_kinds` against the run;
- accepts a status string edited in the P4-owned pin;
- treats schema hash as producer-attested but does not obtain the attestation from a separately trusted artifact.

#### Required fix

1. Derive mandatory field requirements from the one integrator-selected frozen P3→P4 schema; do not support several partially compatible versions with optional semantics in the production path.
2. Require every decision-relevant hash/ID declared by that contract. Missing is a typed blocker.
3. Validate candidate ID/content/path IDs using exact P3 preimages or the actual P3 typed models, not a consumer-invented approximation.
4. The canonical pin must be published outside P4 ownership and referenced read-only.
5. Verify producer commit, canonical path, raw file hash, inner content hash, schema hash and accepted evidence-kind policy together.
6. The fixture path can be verified only by the fixture adapter; it can never satisfy the production pin even if byte-identical.
7. Do not allow P4 tests to set production pin status to accepted and then call that production authority.

### P4-R3-D — Round 3 audit receipts and changed-file counts are internally inconsistent (P1)

#### Evidence

1. Submission/worklog says the changed-files report covers **110 files**.
2. `P4_ROUND_3_CHANGED_FILES.json` reports `total_count: 121`.
3. Normalizing repo prefixes and taking the unique union produces **103 unique paths**.
4. `total_count` double-counts 18 files present in both `baseline..HEAD` and uncommitted changes.
5. The structured evidence top-level session nonce is `0a10d87...`; the versioned Gate report nonce is `47b2ae0a...`.
6. The versioned mutation report has no run ID or session nonce.
7. The evidence generator says one session nonce binds every receipt, but it launches Gate/mutations that create independent receipts and does not cross-bind them.
8. Gate's report command string still records `python scripts/run_p4_gate.py`, while the verification matrix invokes `python -m scripts.run_p4_gate`.
9. The generator's `p4_owned_rows` classification omits modified `reports/p4/*` rows and is not a reliable ownership partition.

These are reporting defects, not the main scientific blocker, but the submission cannot claim immutable audit coordinates until the artifact set is actually one bound run.

#### Required fix

1. Normalize all paths to one repo-relative form before union/counting.
2. Report separate committed/uncommitted/untracked counts and one deduplicated `unique_total_count`.
3. Use the same count in JSON, worklog and submission.
4. Generate one parent audit session nonce and explicitly pass it to Gate and mutation subprocesses.
5. Gate/mutation reports must contain the parent session nonce plus their own child run IDs/nonces.
6. Audit evidence must verify the returned report nonce, command, cwd, exit code and artifact hash before including it.
7. Record the exact executed command, including `-m` and environment.
8. Mutation report must contain run/session identity and registry hash.
9. Ownership partition must compare captured Round 3 starting state to final state, rather than infer ownership from path prefixes alone.

## 4. Keep these Round 3 fixes

Do not regress or rewrite the following working behavior:

- 205-test P4 suite and 290 P0 contracts;
- typed classification fields in run manifest;
- upstream hashes included in run/result identity;
- missing request namespace rejection;
- per-candidate disqualification and observable-only ranker behavior;
- no in-place run mutation;
- verify-before-freeze and verified child runs;
- direct module Gate import without ambient `PYTHONPATH`;
- fresh Gate report path override;
- exact mutation failure-code-list matching;
- mutation execution exception remains ERROR;
- real Gate stays BLOCKED while P1/P2/P3 production authority is absent;
- P3 p3-p4-1/p3-p4-3 ambiguity remains BLOCKED pending upstream owner resolution;
- no P5 work.

## 5. Round 4 execution order

Use this order:

1. Write RED tests for all synchronized-recomputation probes in P4-R3-A.
2. Split production and fixture bundle types/entrypoints; remove the public production pin bypass.
3. Add production execution-authority/registry exact-match and upstream-owned P1/P2/P3 receipt verification.
4. Move candidate/evidence/feature/counterevidence inputs into verified production authorities or deterministic P4 derivation; remove caller-authored production inputs.
5. Make all frozen P3 identities mandatory and exact to the selected interface.
6. Rebuild G12–G14 on the new production authority boundary.
7. Keep the current immutable run and exact mutation-code changes.
8. Repair audit session/changed-file evidence.
9. Run the full matrix and submit Round 4 with real authority still honestly BLOCKED.

Do not solve this by adding another public checksum around the same caller-controlled content. The required change is the **origin/authority boundary**, not one more digest layer.

## 6. Scope controls

- Work only in the existing P4 worktree/branch.
- Do not modify P0/P1/P2/P3 implementation, final design/plan/discussion or ADRs.
- Do not modify P3-owned interface artifacts to fit P4.
- Do not delete/reset inherited dirty files.
- Do not install dependencies, use network services or invoke external LLM/MCP/Orchestra.
- Do not push or merge.
- Do not create a commit without explicit user authorization.
- Synthetic fixtures may prove machinery only.
- Do not claim real evidence or real Gate PASS.
- Keep P5 BLOCKED.

## 7. Mandatory Round 4 verification

Run in the P4 worktree without ambient `PYTHONPATH`:

```bash
PYTHON=/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2/.venv/bin/python
W=/Volumes/CC/Enzyme_Agent/depending/.claude/worktrees/p4-strict-kernel/CC/branch/ReactionAgent/demov2
cd "$W"

PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m pytest -q -p no:cacheprovider tests/p4
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m pytest -q -p no:cacheprovider tests/contracts
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m scripts.run_p4_gate
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m scripts.run_p4_mutations
```

Also run focused RED→GREEN tests that reproduce every P4-R3-A through P4-R3-D finding, including the exact synchronized re-sealing/re-hashing cases from this audit.

## 8. Required Round 4 deliverables

Create under `reports/p4/`:

1. `SUBMISSION_TO_CHATGPT_P4_ROUND_4.md`
2. `P4_ROUND_4_AUDIT_EVIDENCE.json`
3. `P4_ROUND_4_REMEDIATION_WORKLOG.md`
4. `P4_GATE_REPORT_ROUND_4.json`
5. `P4_GATE_REPORT_ROUND_4.md`
6. `P4_MUTATION_RESULTS_ROUND_4.json`
7. `P4_ROUND_4_COUNTEREXAMPLE_RESULTS.json`
8. `P4_ROUND_4_CHANGED_FILES.json`
9. `P4_ROUND_4_STARTING_WORKTREE_STATE.md`
10. `P4_ROUND_4_FINAL_WORKTREE_STATE.md`
11. `P4_ROUND_4_AUTHORITY_BOUNDARY_MANIFEST.json`
12. `p4_p5_interface_manifest_round_4.json`

The submission must answer P4-R3-A through P4-R3-D one by one with original RED evidence, implementation change, GREEN evidence, synchronized-recomputation negative tests, exact changed files and remaining blockers.

## 9. Allowed final status

The expected honest terminal line remains:

```text
P4_ROUND_4_IMPLEMENTATION_COMPLETE_REAL_GATE_BLOCKED_READY_FOR_CHATGPT_AUDIT
P5_BLOCKED
```

Do not use a real/PASS terminal status unless actual upstream production authority exists and is independently verified in the same bound audit run.

```text
CHATGPT_P4_ROUND_3_READ_ONLY_AUDIT_FAIL
P4_ROUND_4_REMEDIATION_REQUIRED
P5_BLOCKED
```
