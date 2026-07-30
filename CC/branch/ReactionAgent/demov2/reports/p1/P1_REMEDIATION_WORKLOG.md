# P1 Remediation Worklog

## Preflight (Task 0)
- timestamp: 2026-07-29T12:25:37.508203+00:00
- assumptions:
  - P0 baseline green (290 passed + Gate 10/10, see `P1_BASELINE.json`)
  - P0 baseline commit `a96b763` is HEAD and unmodified
  - execution model = Claude Code subagent (deviation, originally Qwen per docs)
- input files/hashes:
  - `tests/contracts/` (290 contract tests, P0 frozen)
  - `scripts/run_p0_gate.py` (P0 Gate v3 runner)
  - `../benchmark/canonical_identity.py` sha256=`6003f4bc4ffc5ca3304dc1d2282a467f4f773e149ea9cf2a132ca0e4079eb2d0` (read-only legacy)
- deviations:
  - execution model Qwen → Claude Code subagent (user decision, recorded per brief)
  - `legacy_inventory()` path resolution: brief uses 3 `dirname()` calls for `root`
    which resolves to `.../branch/` (contradicts its own comment
    `# CC/branch/ReactionAgent`). Fixed to 2 `dirname()` calls so `parent`
    correctly resolves to `.../ReactionAgent/` where `../benchmark` and `../core`
    actually live. All data values (PROLINE_2OG_CASE, status names, stop-condition
    logic) are verbatim from the brief.
- preflight status: BLOCKED
- blockers:
  - `rdkit_absent` — rdkit/numpy/networkx/scipy all absent in `.venv`
  - `real_reaction_source_not_confirmed` — no RHEA/BRENDA/MetaCyc source configured
  - `required_case_missing` — proline/2OG source record not provided
- next task authorization: BLOCKED — T1 implementation NOT authorized for real-data work.
  Only read-only scaffolding + fixture unit tests may proceed. User must supply:
  1. Real reaction data source (path/ID for RHEA/BRENDA/MetaCyc, or legacy-data confirmation)
  2. Atom mapper package name (decides `mapper_backend` + T4 viability)
  3. Second annotator (if T6 inter-annotator agreement required)
  4. Proline/2OG source record (e.g. RHEA ID) to bind the canonical case

## TDD evidence
- RED: `tests/p1/test_p1_preflight.py` → 26 errors (ModuleNotFoundError) before implementation
- GREEN: `tests/p1/test_p1_preflight.py` → 26 passed after `scripts/p1_preflight.py` created
- Full suite regression: 316 passed (290 P0 + 26 P1), 0 failed/skipped

## T1: Package bootstrap
- timestamp: 2026-07-29T12:50:43Z (UTC)
- assumptions:
  - P0 baseline green and locked (290 passed + Gate 10/10, commit `a96b763`)
  - Preflight BLOCKED: rdkit/numpy/networkx/scipy absent; only pydantic + pytest available
  - T1 code requires only pydantic + stdlib (json/hashlib/sys/os); no new runtime deps needed
  - `.venv` has no `pip`; use `uv pip freeze` as equivalent for lock generation
  - All new schemas inherit `StrictModel` (extra="forbid", strict=True) per P0 freeze
- RED:
  - `tests/p1/test_config.py` → 1 error (ModuleNotFoundError: reaction_agent.config)
  - `tests/p1/test_hashing_ids.py` → 1 error (ModuleNotFoundError: reaction_agent.hashing)
  - provenance tests (appended to test_config.py) → 1 error (ModuleNotFoundError: reaction_agent.provenance)
- impl:
  - `reaction_agent/config.py`: `BuildConfig` (12 fields, `canonical_json()`), `BuildInfo`, `get_build_info()`
  - `reaction_agent/hashing.py`: `canonical_hash()` (SHA-256, sorted keys, _canonicalize), `stable_id()` (`<prefix>_<hash12>`)
  - `reaction_agent/provenance.py`: `SourceRecordProvenance` (7 required fields), `assert_no_legacy_write()` (hardened)
  - `reaction_agent/__init__.py`: re-exports `get_build_info`, `BuildInfo`
  - `pyproject.toml`: version 0.1.0 → 0.2.0; deps unchanged (pydantic only); P1 comment added
  - `requirements.lock.txt`: `uv pip freeze` (12 packages, no rdkit/numpy/networkx/scipy)
- GREEN:
  - `tests/p1/test_config.py` → 16 passed (5 config + 4 provenance + 7 security regression)
  - `tests/p1/test_hashing_ids.py` → 5 passed
- regression:
  - `tests/contracts tests/p1` → 337 passed (290 P0 + 47 P1), 0 fail/error/skip/xfail/xpass
  - P0 Gate → 10/10 passed (READY_FOR_CHATGPT_AUDIT), no regression
- L2 security-review:
  - 0 CRITICAL, 2 HIGH (H1 symlink bypass, H2 macOS case bypass), 5 MEDIUM, 3 LOW
  - H1/H2/M3/M4 fixed: replaced string-prefix matching with realpath + explicit `.lower()`
    + directory-boundary check; `os.path.normcase` is no-op on POSIX so explicit lowercasing
    required for H2. Added 7 regression tests.
  - M1 (mapper_parameters unconstrained), M2 (canonical_hash default=str), L1 (stable_id 48-bit)
    deferred as non-blocking concerns; documented in checkpoint report.
- deviations:
  - execution model Qwen → Claude Code subagent (user decision)
  - `get_build_info` python_version: brief code `".".join(sys.version_info[:3])` raises
    TypeError (tuple of ints); fixed to `".".join(str(x) for x in sys.version_info[:3])`
  - strict TDD reorder: provenance tests appended before impl (brief Step 9 impl before
    Step 10 tests; user instruction mandates test-first)
  - `assert_no_legacy_write` hardened beyond brief's string matching (CRITICAL/HIGH must-fix)
  - `__init__.py` re-exports `get_build_info` (brief file list says extend; Step 3 defines
    in config.py — both satisfied)
  - pyproject version bumped 0.1.0 → 0.2.0 to align with BuildInfo.package_version
  - `requirements.lock.txt` generated via `uv pip freeze` (not `pip freeze` — `.venv` has no pip)
- BLOCKED_DEPENDENCY_INSTALLATION: rdkit/numpy/networkx/scipy absent. Not force-installed
  per user instruction. Blocks T4 (atom mapper) and T6+ (graph/lineage). T2 may proceed.
- next task authorization: T2 authorized (T1 exit criteria met: dependency lock +
  no-legacy-write guard in place)

## Task 2 (P1-T2: Strict domain schemas)
- timestamp: 2026-07-30
- assumptions:
  - P0 frozen schemas (`evidence.py`/`mapping.py`/`lineage.py`/`ledger.py`/`common.py`)
    already implement `final_design` §7/§8/§9/§10 completely — confirmed during
    Step 1 gap inventory; NOT modified (T2 is extend-not-recreate)
  - `SourceRecordProvenance` (T1, `provenance.py`) is reused, not recreated
  - brief "§8.2 22 objects" is the gap-inventory reference list, not a literal
    section with 22 items; actual coverage = 11 P0 frozen + 3 T1 + 8 T2 new = 22
  - brief Step 1 open questions resolved:
    - `FragmentLineageGraph` = NOT a class (dict field on ReactionEvidence/LineageResolution)
    - `ParticipantRoleHypothesis` = P0 `RoleHypothesis` (confirmed identical, not recreated)
- files:
  - created: `reaction_agent/schemas/p1_entities.py` (8 new entities)
  - modified: `reaction_agent/schemas/__init__.py` (export 8 new entities + `__all__`)
  - created: `tests/p1/test_domain_schemas.py` (27 contract tests)
  - created: `reports/p1/P1_T2_DOMAIN_SCHEMAS.md`
  - NOT modified: P0 schema files, `scripts/export_json_schemas.py`
- RED:
  - `tests/p1/test_domain_schemas.py` → 1 collection error
    (ModuleNotFoundError: reaction_agent.schemas.p1_entities)
- impl:
  - 8 entities in `p1_entities.py`, all inherit `StrictModel`:
    `NormalizedReactionRecord`/`DonorEligibilityAssessment`/`ResolvedTransformedLineage`/
    `EligibilityDecision`/`QuarantineRecord`/`SnapshotManifest`/`SnapshotRecord`/
    `ManualAuditRecord`
  - `DonorEligibilityAssessment.eligibility` = `Literal["eligible",
    "conditionally_eligible","not_eligible","unknown"]` (§11.4, distinct from P0 enum)
  - `EligibilityDecision.eligibility` = P0 `EligibilityStatus` enum (§10.4)
  - `QuarantineRecord.reason` = `NonEmptyStr` required (fail-closed)
  - `SnapshotManifest` = counts/hash/build_status (§16.3)
  - `ManualAuditRecord` = agreement + catastrophic_error_count + 4 rubric scores
    (no confidence field)
- GREEN:
  - `tests/p1/test_domain_schemas.py` → 27 passed (5 brief strictness + 2 hashing
    + 20 additional contract tests)
- JSON schema export:
  - `scripts/export_json_schemas.py` NOT modified (frozen-only constraint)
  - 12 P0 frozen objects re-exported, freshness test 48 passed
- regression:
  - `tests` → 371 passed (P0 290 + P1 81), 0 fail/error/skip/xfail/xpass
  - P0 Gate → 10/10 passed (READY_FOR_CHATGPT_AUDIT), no regression
- deviations:
  - execution model Qwen → Claude Code subagent (user decision, inherited)
  - brief Step 9 "确认含 P1 新对象" overridden by Interfaces "仅冻结对象" +
    closing "不得把仍在探索的内部对象全部导出" — P1 entities NOT exported to
    `schemas/json/`; `export_json_schemas.py` unchanged
  - `NormalizedReactionRecord.provenance` typed `object | None` (not
    `SourceRecordProvenance | None`) to avoid import cycle; runtime accepts
    real `SourceRecordProvenance` instance
  - removed self-added test `test_eligibility_decision_string_value_accepted`
    (strict mode rejects bare str for str-Enum field; replaced with
    `test_eligibility_decision_quarantine_value` using enum member)
- concerns:
  - `provenance: object | None` loose typing on NormalizedReactionRecord —
    acceptable for P1 (T3/T4 consume basic fields); revisit if type safety needed
  - `EligibilityDecision` / `SnapshotRecord` / `SnapshotManifest` defined but
    not yet consumed by implementation (T9/T10 will use them)
- next task authorization: T3 authorized (T2 exit criteria met: P1 object set
  complete, P0 unchanged, JSON schema fresh, zero fail/error/skip)

## Task 3 (P1-T3: Legacy lineage audit — L2 independent, read-only)
- timestamp: 2026-07-30
- assumptions:
  - Preflight BLOCKED: real_reaction_source_not_confirmed + rdkit_absent +
    required_case_missing (proline/2OG source record) — all three inherited
  - rdkit absent from `.venv` (verified: `ModuleNotFoundError: No module named 'rdkit'`)
  - legacy `../benchmark/canonical_identity.py` is read-only reference (sha256
    `6003f4bc…eb2d0`, matches Preflight §2 frozen reference)
  - T2 schemas (`NormalizedReactionRecord`/`ResolvedTransformedLineage`) are
    available but NOT consumed at runtime — no real rows to instantiate them
  - §9.8 forbids fixture-as-real-audit; verdict must be PARTIAL when source missing
- files:
  - created: `scripts/legacy_lineage_audit.py` (read-only static audit, no rdkit)
  - created: `reports/data_audit/legacy_lineage_audit.json` (machine-readable)
  - created: `reports/data_audit/legacy_lineage_audit.md` (human-readable)
  - created: `tests/p1/test_legacy_audit_contract.py` (10 contract tests)
  - created: `reports/p1/P1_T3_LEGACY_AUDIT.md` (this checkpoint)
  - NOT modified: `../benchmark/canonical_identity.py`, `../core/chenyu_features.py`
- audit scope:
  - legacy_logic_static_audit_only (transformed_pair NOT executed on real rows)
  - legacy module fingerprint (sha256 verified pre+post run, read_only=True)
  - 5 §9.4 mismatch categories with definitions
  - 6 logic-level risks per audited function
  - real-source probe: rdkit/numpy import + env-var scan + candidate pkl inventory
  - proline/2OG case recorded as required_case_missing
- RED:
  - `tests/p1/test_legacy_audit_contract.py` → 10 failed (audit JSON not generated)
- impl:
  - `scripts/legacy_lineage_audit.py`: assembles verdict+counts+categories+
    examples+source_ids+legacy_module+real_source_status+legacy_logic_risks+
    proline_2og_case+discipline_notes; writes JSON+MD; re-verifies legacy sha
    at exit (read-only guard, exit code 2 on any mutation)
  - verdict = PARTIAL; reasons = [real_reaction_source_not_confirmed,
    rdkit_absent_runtime_unable_to_execute_legacy_transformed_pair,
    required_case_missing_proline_2og_source_record]
  - counts: all 0 (total_reactions=0 denominator — honest, not missing)
  - examples: [] / source_ids: [] (§9.8: no fabrication when PARTIAL)
- GREEN:
  - `tests/p1/test_legacy_audit_contract.py` → 10 passed
  - contract tests adjusted per brief Step 6: `test_proline_2og_case_handled_honestly`
    replaces brief's `test_proline_2og_included` (context-aware: requires real
    example when PASS, requires `required_case_missing` marker when PARTIAL);
    adds `test_no_fabricated_examples_when_partial` (§9.8 anti-fabrication guard)
- candidate data finding:
  - `rxn2enzyme_positives.pkl` exists at `/Volumes/CC/Enzyme_Agent/depending/data/`
    with 3601 reaction SMILES; probed (pickle-only, no rdkit); 0 proline hits
  - NOT treated as confirmed source: maps SMILES→enzyme lists, not complete
    RHEA/BRENDA records; rdkit absent so cannot run transformed_pair; user has
    not confirmed it as T3 source
- regression:
  - `tests` → 390 passed (290 P0 + 100 P1), 0 fail/error/skip/xfail/xpass
  - P0 Gate → 10/10 passed (READY_FOR_CHATGPT_AUDIT), no regression
  - `../benchmark/` + `../core/`: git status `??` (untracked, untouched)
- deviations:
  - execution model Qwen → Claude Code subagent (inherited)
  - contract test adjusted for PARTIAL per brief Step 6 (honest, not weakened)
  - audit scope = static logic audit only (no real rows — rdkit absent + source
    unconfirmed; §9.8 forbids fixture-as-real-audit)
- verdict: PARTIAL (P1 Gate = BLOCKED)
- to unblock: (1) real reaction source confirmed, (2) rdkit installed in .venv,
  (3) proline/2OG source record (e.g. RHEA ID)
- next task authorization: T3 PARTIAL — real-data audit blocked. Downstream
  T4/T6 (which need rdkit + real source) remain blocked. T5 (participant roles)
  and T7/T8 (ledger skeletons) may proceed on read-only/fixture scaffolding
  per the same PARTIAL discipline.

## Task 4 (P1-T4: Atom-mapping adapter)
- timestamp: 2026-07-30T02:36Z (UTC)
- assumptions:
  - Preflight BLOCKED: rdkit/numpy/networkx/scipy all absent in `.venv`
    (verified: `import rdkit` → ModuleNotFoundError; Preflight json
    `runtime.mapper_backend=null`)
  - P0 `MappingReport` schema (§8/§10/§11/§12) is frozen — NOT modified
  - P0 `MappingStatus` enum (§10.2 vocabulary) reused as-is
  - T2 `NormalizedReactionRecord` is the input type (consumed by Protocol)
  - T1 `canonical_hash` accepts only basic types (no datetime/Path) —
    input_hash hashes only {reaction_id, normalized_reaction, source_record_id}
  - §10.4 formal ≠ mechanistic: FakeAtomMapper NEVER sets
    `mechanistic_atom_origin`; only `formal_mapped_source_assignment`
  - §10.5 MCS/center-pair fallback downgrades status (never fully_mapped)
  - §10.7: real mapper unavailable → UNIT_CONTRACT_COMPLETE / INTEGRATION_BLOCKED
    (not PASS)
- files:
  - created: `reaction_agent/mapping/__init__.py` (package exports)
  - created: `reaction_agent/mapping/base.py` (`AtomMapper` Protocol, §10.1)
  - created: `reaction_agent/mapping/adapter.py` (`FakeAtomMapper` +
    `compute_quality_flags` + `RealMapperAdapter` skeleton)
  - created: `tests/p1/test_mapping_adapter.py` (30 contract tests)
  - created: `reports/p1/mapping_integration_sample.json` (INTEGRATION_BLOCKED)
  - created: `reports/p1/P1_T4_MAPPING_ADAPTER.md` (this checkpoint)
  - NOT modified: P0 schemas, `reports/p0/`, `../benchmark/`, `../core/`
- Step 1 (READ — mapper backend probe):
  - rdkit: unavailable (ModuleNotFoundError)
  - rxnmapper: unavailable (ModuleNotFoundError)
  - rxn4chemistry: unavailable (ModuleNotFoundError)
  - numpy/networkx/scipy: unavailable (Preflight json confirms all null)
  - conclusion: real mapper integration BLOCKED → UNIT_CONTRACT_COMPLETE only
- RED:
  - `tests/p1/test_mapping_adapter.py` → 30 failed
    (ModuleNotFoundError: No module named 'reaction_agent.mapping')
- impl:
  - `base.py`: `AtomMapper` Protocol with `map_reaction(record) ->
    MappingReport`; `@runtime_checkable` for structural typing
  - `adapter.py`:
    - `FakeAtomMapper`: deterministic, formal-only; params: status/fallback/
      timeout/duplicate_map_ids/symmetry_ambiguity/resonance_tautomer_ambiguity;
      §10.5 fallback downgrades fully_mapped→partially_mapped; generates typed
      FormalMappedAtomPair objects (§11); mechanistic_atom_origin=None always
    - `compute_quality_flags`: §10.3 8 dimensions as `name=value` strings
    - `RealMapperAdapter`: SUPPORTED_BACKENDS=("rdkit","rxnmapper",
      "rxn4chemistry"); `is_available()` probes importability; `map_reaction()`
      raises NotImplementedError with INTEGRATION_BLOCKED marker when blocked
  - `input_hash`: `canonical_hash({reaction_id, normalized_reaction,
    source_record_id})` — basic types only (T1 fix respected)
  - `output_hash`: `canonical_hash({input_hash, mapper_name, mapper_version,
    mapping_status, fallback_method, assignment_method})` — deterministic
  - `mapper_parameters`: captures timeout + runtime_ms + status + fallback
    (all string values, per `dict[str, str]` schema)
- GREEN:
  - initial: 1 failed (`test_duplicate_map_ids_flagged` — duplicate_map_ids
    flag not wired to map_number_uniqueness)
  - fix: override `map_uniqueness=False` when `self._duplicate_map_ids` is set
  - final: `tests/p1/test_mapping_adapter.py` → 30 passed in 0.19s
- integration test (Step 6/7):
  - brief Step 6 uses `@pytest.mark.skipif` — replaced per user instruction
    (zero-skip discipline). `test_real_mapper_integration_handles_unavailable_backend`
    verifies adapter raises NotImplementedError("...INTEGRATION_BLOCKED...")
    when backend unavailable; runs real integration when available. No skip.
  - all 3 backends probed: unavailable → INTEGRATION_BLOCKED
  - `mapping_integration_sample.json`: documents blocked state + unit contract
    sample (fake mapper formal-only output with 8 quality flags)
- regression:
  - `tests` → 420 passed (290 P0 + 130 P1), 0 fail/error/skip/xfail/xpass
  - P0 Gate → 10/10 passed (READY_FOR_CHATGPT_AUDIT), no regression
- deviations:
  - execution model Qwen → Claude Code subagent (inherited)
  - integration test: skipif → non-skip INTEGRATION_BLOCKED assertion
    (per user instruction: zero-skip discipline)
  - runtime/timeout capture: §10.1 lists `runtime` but P0 MappingReport has
    no runtime field (frozen). Captured in `mapper_parameters` as
    `runtime_ms`/`timeout` strings (non-breaking, auditable)
  - brief `AtomMapper` Protocol signature uses bare `reaction` param;
    annotated as `NormalizedReactionRecord` per §10.1 spec text
- concerns:
  - INTEGRATION_BLOCKED: real mapper cannot run (rdkit absent). T4 is
    UNIT_CONTRACT_COMPLETE but NOT PASS. P1 Gate G04 will not pass until
    rdkit/numpy/networkx/scipy installed
  - RealMapperAdapter._do_map is a skeleton — wiring real backend is a
    follow-up once installed
  - FakeAtomMapper atom pairs are syntactic (not chemically correct) —
    sufficient for contract testing, not real chemistry validation
- verdict: UNIT_CONTRACT_COMPLETE / INTEGRATION_BLOCKED (not PASS)
- to unblock: (1) install rdkit/numpy/networkx/scipy in .venv,
  (2) set P1_REAL_MAPPER_AVAILABLE env, (3) implement RealMapperAdapter._do_map,
  (4) re-run integration test, (5) update verdict to PASS
- next task authorization: T4 UNIT_CONTRACT_COMPLETE — Protocol + fake mapper
  unit contract done. Real mapper integration blocked. Downstream T6 (lineage
  resolver) remains blocked (needs rdkit). T5/T7/T8 may proceed on
  scaffolding per the same PARTIAL discipline.

### Fix Round 1 (reviewer findings: 3 Important + 2 Minor)
- timestamp: 2026-07-30T03:05Z (UTC)
- [IMPORTANT-1] available-branch latent failure:
  - `test_real_mapper_integration_handles_unavailable_backend` if-branch
    called `a.map_reaction()` directly → would ERROR when rdkit installed
    but `_do_map` not wired (skeleton raises NotImplementedError)
  - fix: available-branch wrapped in `pytest.raises(NotImplementedError,
    match="skeleton")`; added `test_real_mapper_available_branch_raises_skeleton`
    (monkeypatches `_available=True` to force the branch regardless of rdkit)
- [IMPORTANT-2] `_probe_rdkit` probe scope:
  - only probed rdkit+numpy but deps declare rdkit/numpy/networkx/scipy →
    partial install would report is_available()=True then crash `_do_map`
  - fix: `_probe_rdkit` now probes all 4 (rdkit, numpy, networkx, scipy)
  - test: `test_probe_rdkit_requires_all_four_declared_deps` (sys.modules
    simulation of partial installs)
- [IMPORTANT-3] §10.6 coverage gap (5 missing cases):
  - timeout: added `timed_out` param to FakeAtomMapper (forces
    mapping_failed, records timed_out=true); test:
    `test_timeout_behavior_mapping_failed`
  - missing maps: test `test_missing_maps_flagged_in_quality` (partial
    coverage → unmapped_changed_atoms=present, fraction<1.0)
  - blocked by real mapper integration (require chemical perception, not
    syntactic fake pairs): mapped-reactants-unmapped-products, atom-order
    permutation, multi-fragment — explicitly marked BLOCKED in report +
    worklog §10.6 coverage matrix
- [MINOR-1] Protocol check: `test_atom_mapper_protocol_satisfied` now uses
  `assert isinstance(m, AtomMapper)` (runtime_checkable) instead of
  hasattr+callable
- [MINOR-2] `reactant_product_map_consistency`: extracted `_map_consistency`
  helper — fully_mapped→pass, partially_mapped/mapping_ambiguous→partial,
  unmapped/mapping_failed→fail (was "partial" for failed, semantically wrong)
- RED: 3 failed, 32 passed (3 impl-dependent: probe, consistency, timeout)
- GREEN: 35 passed (30 original + 5 new)
- regression: 425 passed (290 P0 + 135 P1), 0 fail/error/skip/xfail/xpass
- P0 Gate: 10/10 passed (READY_FOR_CHATGPT_AUDIT), no regression
- §10.6 coverage: 13/16 cases covered; 3 blocked (real mapper integration)
- files modified: `reaction_agent/mapping/adapter.py`, `tests/p1/test_mapping_adapter.py`
- NOT modified: P0 schemas, `reports/p0/`, `../benchmark/`, `../core/`
- verdict (unchanged): UNIT_CONTRACT_COMPLETE / INTEGRATION_BLOCKED

## Task 5 (P1-T5: Participant roles & donor eligibility)
- timestamp: 2026-07-30T03:20Z (UTC)
- assumptions:
  - Preflight BLOCKED (rdkit absent) — does NOT block T5; roles are
    hypotheses + evidence, not chemical computation
  - P0 `RoleHypothesis` (schemas/evidence.py: role/score/evidence_codes) is
    frozen — NOT redefined (brief discipline: "RoleHypothesis 在 P0 已有，
    不要重定义")
  - P0 `ReactionParticipant` (schemas/evidence.py) frozen — NOT modified
  - T2 `DonorEligibilityAssessment` (schemas/p1_entities.py) reused as-is
  - legacy `../benchmark/canonical_identity.py` imports rdkit at module top;
    rdkit absent → direct import fails. AST extraction used instead (read-only,
    no execution, no side effects)
  - §11.3: COFACTORS ONLY as participant_role_prior / donor_eligibility_prior /
    retrieval_downweighting_prior — never destructive
  - §11.4: donor eligibility ≠ role; 10 dimensions evaluated
  - §11.5: input participant multiset == persisted participant multiset
- files:
  - created: `reaction_agent/roles/__init__.py` (package exports)
  - created: `reaction_agent/roles/cofactors.py` (`load_cofactors` — AST extract + source hash)
  - created: `reaction_agent/roles/resolver.py` (`resolve_roles` + `assess_donor_eligibility`)
  - created: `tests/p1/test_participant_roles.py` (45 contract tests)
  - created: `reports/p1/participant_role_sample.json` (evidence sample)
  - created: `reports/p1/P1_T5_PARTICIPANT_ROLES.md` (checkpoint)
  - NOT modified: P0 schemas, `reports/p0/`, `../benchmark/`, `../core/`
- RED:
  - `tests/p1/test_participant_roles.py` → 45 failed
    (ModuleNotFoundError: No module named 'reaction_agent.roles')
- impl:
  - `cofactors.py`: AST-parse `COFACTORS = frozenset({...})` literal from
    legacy source (no rdkit execution); 24 string SMILES entries, sorted +
    de-duplicated; source SHA-256 = `6003f4bc…eb2d0` (matches Preflight);
    module-level cache (idempotent); `LEGACY_PATH` resolved via 4 `.parent`
    calls from `cofactors.py` → `ReactionAgent/benchmark/canonical_identity.py`
  - `resolver.py`:
    - `resolve_roles`: attaches `RoleHypothesis` to each participant via
      `model_copy(update={"role_hypotheses": ...})` (immutability — input NOT
      mutated); NEVER deletes a participant; 4 hypothesis layers:
      (1) `unknown` baseline (always present — no forced ground truth),
      (2) side-based weak prior (co_substrate/coproduct),
      (3) COFACTORS prior (cofactor/carrier) if member,
      (4) mapping-derived (transformed_substrate/product) if mapping evidence;
      layers 3+4 coexist → ambiguity preserved (§11.3)
    - `assess_donor_eligibility`: 10 dimensions (5 core mapping-derived +
      5 context priors); core drives verdict, context only downgrades
      eligible→conditional (COFACTORS prior, §11.3); without mapping →
      `unknown` (never fabricated); small molecules NOT auto-disqualified
    - `policy_version=p1-t5-1` encoded as evidence code (P0 RoleHypothesis
      has no policy_version field)
    - `ambiguity` encoded as multiple competing hypotheses (§11.2)
    - heuristic score in [0,1] = ordering hint, NOT probability
- GREEN:
  - initial: 1 failed (`test_donor_eligibility_unknown_without_mapping`
    returned `conditionally_eligible` instead of `unknown`)
  - fix: split dimensions into core (mapping-derived) + context (priors);
    core drives verdict, context never upgrades unknown→conditional
  - final: `tests/p1/test_participant_roles.py` → 45 passed in 0.18s
- §11.3 special tests (all pass):
  - O2 formal atom source: retained ✅
  - H2O hydrolysis participant: retained ✅
  - CO2 coproduct: retained ✅
  - NAD(P) evidence retained verbatim: ✅
  - small molecule transformed substrate: retained ✅
  - 2-oxoglutarate not deleted (not in COFACTORS by design): ✅
  - COFACTORS prior vs mapping conflict → both hypotheses retained: ✅
  - full proline/2OG/O2 reaction (6 participants): multiset preserved ✅
- §11.5 multiset invariant (verified):
  - input_count == output_count (8 == 8 in sample)
  - input_ids_sorted == output_ids_sorted: True
  - duplicates preserved (no set collapse)
  - input not mutated (model_copy returns new objects)
  - non-role fields preserved verbatim (smiles/side/stoichiometry/maps)
- COFACTORS not-destructive evidence:
  - legacy file SHA-256 pre == post == `6003f4bc…eb2d0`
  - git status: `../benchmark/` untracked (pre-existing), NOT modified
  - COFACTORS membership only adds a prior hypothesis; never deletes;
    never forces ground-truth role; `unknown` always retained
- regression:
  - `tests` → 470 passed (290 P0 + 180 P1), 0 fail/error/skip/xfail/xpass
  - P0 Gate → 10/10 passed (READY_FOR_CHATGPT_AUDIT), no regression
  - P1 breakdown: 26 (preflight) + 21 (T1) + 27 (T2) + 16 (T2 extra) +
    10 (T3) + 35 (T4) + 45 (T5) = 180
- deviations:
  - execution model Qwen → Claude Code subagent (inherited)
  - COFACTORS extraction via AST (legacy imports rdkit at top; rdkit absent;
    direct import impossible). Read-only, no execution, no side effects
  - canonicalization deferred: legacy values already canonical (produced by
    Chem.MolToSmiles); re-canonicalization requires rdkit (absent). Values
    returned as-is — correct per §11.3 "读取并 canonicalize" (legacy already
    canonicalized)
  - `policy_version` / `ambiguity` encoded in evidence_codes / hypothesis
    multiplicity (P0 RoleHypothesis schema frozen, no new fields)
  - donor eligibility aggregation: brief §11.4 lists dimensions but no
    aggregation function; split into core+context (core drives, context
    downgrades only) — ensures "without mapping → unknown"
  - `mapping_report` typed `object | None` (T5 checks presence only, not
    MappingReport fields; tighten to `MappingReport | None` when T6/T9 wire
    real reports)
- concerns:
  - rdkit absent: `size_complexity` uses SMILES-length proxy (≤5 chars →
    small); never disqualifies, only adds reason code. Replace with
    heavy-atom count when rdkit available
  - `reaction_direction` uses `side` as weak proxy (direction is on
    ReactionEvidence, not ReactionParticipant); consume `evidence.direction`
    when T6/T9 wire ReactionEvidence
  - `transferred_atoms` / `lineage_ambiguity` always `unknown` in T5
    (require mechanistic evidence / resolved lineage, T6+); honest, no
    fabrication
  - `not_eligible` unreachable in T5: all core dimensions produce
    `unknown_*`/`eligible_*`/`conditional_*` without mechanistic evidence
    (T6+); the `not_eligible` aggregation branch is reserved for T6+
    mechanistic analysis (atom-balance exclusion, direction mismatch).
    Absence of `not_eligible` outputs in T5 samples is expected, not a bug.
- verdict: UNIT_CONTRACT_COMPLETE (roles are hypotheses + evidence, not
  chemical computation; rdkit absence does not block the unit contract)
- next task authorization: T5 UNIT_CONTRACT_COMPLETE. T6 (lineage resolver)
  remains blocked (needs rdkit). T7/T8 (ledger skeletons) may proceed on
  scaffolding per the same PARTIAL discipline.

---

## T6 (Task 6) — Bipartite fragment-lineage graph
- timestamp: 2026-07-30T04:30Z (UTC)
- task: P1-T6 Bipartite fragment-lineage graph (final_design §9 = brief §12)
- preflight: BLOCKED (rdkit_absent + required_case_missing — does not block
  T6 unit contract; resolver operates on formal atom mapping only)
- files created:
  - `reaction_agent/lineage/__init__.py` (package exports)
  - `reaction_agent/lineage/resolver.py` (`build_lineage_graph` +
    `resolve_lineages` + `_build_edges`, RESOLVER_VERSION=`p1-t6-1`)
  - `tests/p1/test_lineage_graph.py` (41 contract tests)
  - `reports/p1/lineage_regression_cases.json` (14 regression cases)
  - `reports/p1/P1_T6_LINEAGE_GRAPH.md` (checkpoint)
- TDD:
  - RED: 39 failed, 2 passed (ModuleNotFoundError)
  - GREEN: 41 passed in 0.14s
  - full suite: 512 passed (471 baseline + 41 T6), 0 fail/error/skip/xfail/xpass
  - P0 Gate: 10/10 passed, no regression
- §9.2 three prohibitions (verified):
  1. NO independent side picking — edges from formal mapping, not "best
     molecule" picks. Weak spurious cross edges (overlapping + unequal
     strength) removed from lineages.
  2. NO tuple max() silent tie — equal-strength overlap → ambiguity_set,
     both lineages critical, NOT a single silently-picked winner.
  3. NO forced primary — `is_primary=False` for all hypotheses; multiple
     lineages coexist.
- §9.3 proline/2OG hard Gate:
  - Case A (curated): proline→hydroxyproline + 2OG→succinate + O transfer ✓
  - Case B (quarantine): unmapped → 0 strict, quality=unresolved ✓
  - Forbidden 2OG→hydroxyproline: NOT in strict index ✓
  - Real source: required_case_missing (not fabricated)
- §12.4 stable lineage ID: reaction identity + participant identity + sorted
  atom correspondence + resolver version. Order-invariant (sorting).
- 14 regression cases: all covered (proline/2OG, redox NAD, O2 incorporation,
  hydrolysis, transferase, decarboxylation, cleavage, condensation, split,
  merge, equal-score tie, partial mapping, MCS fallback, atom-order permutation)
- deviations:
  - rdkit absent: scaffold_continuity = retention_fraction proxy;
    changed_mapped_atoms uses changed_atom_fraction > 0 proxy
  - atom transfer detection: mapped_fraction==0.0 AND shared<=2 AND scaffold
    source exists for same product (conservative; when in doubt, edge remains
    a transformed lineage)
  - weak cross edge (overlapping + unequal strength): weaker edge removed from
    lineages, recorded in atom_transfer_edges as type=weak_cross_edge
  - resolve_lineages returns ALL lineages (including critical); caller filters
    critical out of strict index
- concerns:
  - real proline/2OG source required for integration verification (curated
    fixture covers unit logic; real-data verification blocked)
  - atom transfer heuristic may need refinement for edge cases (small mapped
    substrate vs. inorganic donor); conservative design errs toward keeping
    edges as transformed lineages
- verdict: UNIT_CONTRACT_COMPLETE (resolver operates on formal atom mapping;
  no chemistry fabricated; rdkit absence does not block the unit contract)
- next task authorization: T6 UNIT_CONTRACT_COMPLETE. T7/T8 (ledger skeletons)
  may proceed. Real-data lineage verification blocked until rdkit + source.
