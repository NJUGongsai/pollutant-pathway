"""P3 Gate (final_plan §6.11, CHATGPT_P3 prompt §7, R2-I, R3-A, R3-F).

Gate principles:
- PASS / FAIL / BLOCKED are distinct.
- Synthetic fixtures can verify MACHINERY only; they cannot satisfy a
  real-evidence Gate item.
- An implementation invariant failure is FAIL, never masked by a BLOCKED.
- The verdict is DERIVED from executed artifacts / schema hashes / capability
  probes / mutation results — never trusted from a stored status string.
- A mutation that escapes (or errors, or has an invalid baseline, or a
  mismatched observed code) blocks PASS — it is a machinery FAIL (R3-F).
- The runner exits with different codes: PASS=0, FAIL=1, BLOCKED=2.

R3-A: ``evaluate_gate_from_artifacts`` validates TYPED artifacts, recomputes
the interface schema hash from the live schemas, requires the complete
G01-G10 item set, rejects missing/duplicate/unknown/invalid items, binds
every item to verified evidence, validates the run namespace and
evidence-kind semantics, and never treats a stored status string (or a
truthy key) as authority.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import ValidationError

from reaction_agent.hashing import canonical_hash
from reaction_agent.p3.kernel import run_kernel
from reaction_agent.p3.schemas import (
    EvidenceKind,
    EvidenceReference,
    NonEmptyStr,
    StrictModel,
    field_validator,
)


class GateItemResult(StrictModel):
    item_id: NonEmptyStr
    title: NonEmptyStr
    status: Literal["PASS", "BLOCKED", "FAIL"]
    # R4-A: evidence is a list of TYPED, versioned evidence references bound
    # to executed artifacts — never arbitrary strings.
    evidence: list[EvidenceReference] = []
    evidence_kind: EvidenceKind = EvidenceKind.diagnostic

    @field_validator("evidence")
    @classmethod
    def _evidence_not_empty(cls, v: list) -> list:
        # R3-A/R4-A: every Gate item is bound to verified evidence; an item
        # without evidence is an invalid artifact.
        if not v:
            raise ValueError("gate item carries no evidence")
        return v


class MutationCaseRun(StrictModel):
    """One real subprocess execution of a mutation case variant (R3-F).

    R5-B: the receipt carries the REAL raw output (``raw_output``) so the
    verifier can RECOMPUTE the stdout hash from it, the typed structured
    artifact (``artifact``) so the artifact hash is RECOMPUTABLE, the real
    parsed status + failure code + exit code, and the run/component identity
    so a cached receipt from another run/component version is rejected.
    ``cwd`` / ``python_executable`` / ``command`` strings are recorded but
    are NEVER execution proof by themselves.

    R6-B: the receipt is a UNIQUE, STRICT, VERSIONED JSON payload embedded in
    the raw output (marker-delimited).  The verifier PARSES the receipt from
    the raw output and requires the typed fields to EXACTLY match the parsed
    payload — the raw output and the typed artifact are cryptographically and
    execution-semantically bound, never two independently modifiable copies.
    ``run_id`` / ``component`` / ``schema_version`` / ``case`` / ``variant`` /
    ``session_nonce`` are REQUIRED non-empty fields bound to the same trusted
    execution — a cached receipt from another run/component/session is
    rejected (no conditional "non-empty then compare").
    """
    command: list[NonEmptyStr]
    cwd: NonEmptyStr
    python_executable: NonEmptyStr
    started_at: float
    finished_at: float
    duration_seconds: float
    exit_code: int
    status: Literal["PASS", "FAIL", "ERROR"]
    failure_code: str = ""
    artifact_hash: str = ""
    stdout_stderr_hash: NonEmptyStr
    raw_output: str = ""
    raw_tail: str = ""
    artifact: dict = {}
    timed_out: bool = False
    run_id: NonEmptyStr
    component: NonEmptyStr
    schema_version: NonEmptyStr
    case: NonEmptyStr
    variant: NonEmptyStr
    session_nonce: NonEmptyStr


class MutationResult(StrictModel):
    """Baseline-vs-mutated evidence for ONE mutation (R3-F).

    ``observed_failure_code`` is the code the production machinery actually
    emitted during the mutated run — it is never copied from the expected
    code.

    R5-B: the record is bound to the FROZEN REGISTRY contract — the Gate
    compares mutation_id / target_gate_item / expected_failure_code /
    baseline_case / mutated_case / component / schema_version against the
    registry, not just the ID set.
    """
    mutation_id: NonEmptyStr
    target_gate_item: NonEmptyStr
    expected_failure_code: NonEmptyStr
    baseline_status: Literal["PASS", "INVALID_BASELINE"]
    mutated_status: Literal["FAIL", "ERROR", "PASS"]  # PASS == escaped
    baseline: MutationCaseRun
    mutated: MutationCaseRun
    observed_failure_code: str = ""
    caught: bool
    valid: bool
    invalid_reason: str = ""
    baseline_case: str = ""
    mutated_case: str = ""
    component: str = ""
    schema_version: str = ""
    registry_hash: str = ""
    run_id: str = ""
    # R6-B: the execution/session nonce that binds every baseline/mutated
    # receipt to the SAME trusted execution.  A receipt from a previous
    # execution (different nonce) is rejected.
    session_nonce: str = ""


class GateReport(StrictModel):
    gate_id: NonEmptyStr
    schema_version: NonEmptyStr = "p3-gate-3"
    verdict: Literal["PASS", "BLOCKED", "FAIL"]
    items: list[GateItemResult] = []
    mutations: list[MutationResult] = []
    interface_manifest_schema_hash: str = ""
    derived_from_artifacts: bool = False
    notes: str = ""
    # R4-A: the gate binds its own run namespace so every evidence reference
    # can be verified against the CURRENT snapshot/fold.
    run_id: str = ""
    fold_id: str = ""
    snapshot_id: str = ""
    snapshot_hash: str = ""
    # R5-B: the canonical frozen mutation-registry hash bound to this gate
    # execution.
    mutation_registry_hash: str = ""
    # R6-B: the session nonce of the trusted execution that produced every
    # mutation receipt in this report.
    session_nonce: str = ""


class GateEvaluation(StrictModel):
    """Typed outcome of verifying an artifact dict (R3-A).

    R5-A: ``verified`` is ONLY True when the artifact was verified against a
    TRUSTED EXECUTION CONTEXT (the typed item objects produced by the actual
    Gate runner).  A serialized dict alone can at most be
    ``structurally_valid`` — it can never become ``verified=True``.
    """
    verdict: Literal["PASS", "FAIL", "BLOCKED"]
    verified: bool = False
    structurally_valid: bool = False
    machinery_failures: list[NonEmptyStr] = []
    item_statuses: dict[str, str] = {}


# Gate items that REQUIRE real evidence (never satisfiable by fixtures).
REAL_EVIDENCE_ITEMS = frozenset({"G01", "G03", "G07"})
REQUIRED_GATE_ITEMS = tuple(f"G{i:02d}" for i in range(1, 11))

# R5-A: artifact types are a FROZEN enum/union — unknown types fail closed.
KNOWN_ARTIFACT_TYPES = frozenset({"kernel_run", "capability_probe", "mutation_case"})
# R5-A: schema versions supported by the CURRENT verifier — unknown versions
# fail closed.
SUPPORTED_SCHEMA_VERSIONS = frozenset({"p3-1"})

# R6-A: every artifact type has a STRICT TYPED CONTENT MODEL — not a string
# allowlist.  A content dict is only valid for an artifact type when its
# ``gate_check`` belongs to the declared check set for that type AND the
# required fields are present.  Relabeling a kernel_run payload as
# capability_probe (or vice versa) is therefore rejected by the verifier.
ARTIFACT_TYPE_CONTENT_SCHEMAS = {
    "kernel_run": {
        "gate_checks": frozenset({
            "equivalent_smiles_invariant",
            "no_llm_structure_creation",
            "system_failure_abstention_separate",
            "octanol_carbon_regression",
            "candidate_donor_context_labeled_assumptions",
            "strict_candidate_replayable",
        }),
        "required": ("gate_check",),
    },
    "capability_probe": {
        "gate_checks": frozenset({
            "x_only_automatic_end_to_end",
            "donor_reaction_lineage_transform_site_dual_ledger_complete",
            "pilot_funnel_operational",
            "formal_mapping_not_mechanism",
        }),
        "required": ("gate_check",),
    },
    "mutation_case": {
        "required": ("case", "variant", "status", "artifact"),
    },
}


class _ExecutionProof:
    """Module-private token that gates construction of ``GateExecutionAuthority``.

    The token is created once at import time and is never exported.  A public
    caller cannot obtain it, so it cannot construct an execution authority.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "<p3-execution-proof>"


_EXECUTION_PROOF = _ExecutionProof()


def _model_snapshot_json(model) -> str:
    """R8: independent canonical JSON snapshot of a strict model.

    The snapshot is a plain IMMUTABLE string generated at registration time
    (value-copied, never a shared reference).  The returned ``GateReport``
    therefore shares NO mutable object with the execution authority — mutating
    a returned report's mutation/item (or any nested dict/list inside it) can
    never change the authority's audit basis.
    """
    return json.dumps(
        model.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
    )


class GateExecutionAuthority:
    """R6-A / R7-A: the ONLY object that can make ``evaluate_gate_artifact``
    return ``verified=True``.

    The constructor requires the module-private proof token ``_EXECUTION_PROOF``
    which is never exported; a public caller passing a plain dict, an empty
    dict or any other object as ``trusted_context`` is rejected fail-closed
    (``UNTRUSTED_CONTEXT``).  Only the Gate runner (via the private factory
    ``_register_execution_authority``) can create an authority.

    The authority holds the TYPED items AND the TYPED mutation results the
    runner ACTUALLY executed.  The verifier derives the verdict from these
    objects (never from submitted statuses) and requires every submitted item
    AND every submitted mutation to EXACTLY match the executed ones
    (complete-match contract): status, title, evidence_kind and the full
    evidence list (type / id / content / content hash / schema / run / fold /
    snapshot namespace) for items; the FULL mutation record (baseline + mutated
    receipts, every hash, status, failure code, case, variant, session nonce,
    adjudication) for mutations.  A missing, extra, reordered or changed item /
    mutation is a verification failure — FAIL, never a masked PASS.

    R7-A: binding the executed mutations closes the "self-consistent rewrite of
    BOTH the raw receipt and the typed fields" attack — the calling submitter
    also controls the marker receipt and every hash in the submitted report, so
    a fully-resynchronized rewrite is internally consistent.  Only the
    in-process authority (which holds the mutations the runner ACTUALLY
    executed, registered AFTER the mutation suite completes) can prove a
    mutation outcome came from THIS execution.

    R8: the authority does NOT keep the raw mutable model references it was
    registered with.  At registration time every executed item and mutation is
    converted into an INDEPENDENT canonical JSON snapshot (a plain immutable
    string, see ``_model_snapshot_json``).  The returned ``GateReport`` shares
    no mutable object with the authority, so mutating a returned report's
    mutation/item (or any nested dict inside it) can never change the
    authority's audit basis.  ``items`` / ``mutations`` / ``executed`` expose
    parsed COPIES of the snapshots (never the original references), so even a
    caller that reaches the authority cannot mutate its internal audit basis.
    """

    __slots__ = ("_item_snapshots", "_mutation_snapshots", "_by_id", "_proof")

    def __init__(
        self,
        items: list["GateItemResult"],
        mutations: list["MutationResult"],
        proof: "_ExecutionProof",
    ) -> None:
        if proof is not _EXECUTION_PROOF:
            raise TypeError("GateExecutionAuthority is not constructible by callers")
        # R8: immediately convert the executed items/mutations into independent
        # canonical JSON snapshots.  Strings are immutable and value-copied, so
        # the authority is fully isolated from the returned GateReport — a
        # later mutation of the report (or any nested dict/list) cannot change
        # the authority's audit basis.
        item_snapshots = tuple(_model_snapshot_json(item) for item in items)
        mutation_snapshots = tuple(_model_snapshot_json(m) for m in mutations)
        object.__setattr__(self, "_item_snapshots", item_snapshots)
        object.__setattr__(self, "_mutation_snapshots", mutation_snapshots)
        object.__setattr__(
            self, "_by_id",
            {item.item_id: snap for item, snap in zip(items, item_snapshots)},
        )
        object.__setattr__(self, "_proof", proof)

    @property
    def items(self) -> tuple[dict, ...]:
        """Parsed COPIES of the executed item snapshots (never the original
        mutable model references — R8)."""
        return tuple(json.loads(s) for s in self._item_snapshots)

    @property
    def mutations(self) -> tuple[dict, ...]:
        """Parsed COPIES of the executed mutation snapshots (never the
        original mutable model references — R8)."""
        return tuple(json.loads(s) for s in self._mutation_snapshots)

    def executed(self, item_id: str) -> dict | None:
        """Parsed COPY of the executed item snapshot for ``item_id`` (never
        the original mutable model reference — R8)."""
        snap = self._by_id.get(item_id)
        return None if snap is None else json.loads(snap)


# R6-A: in-process execution authorities keyed by run_id.  ONLY the Gate
# runner registers here through the private factory — a public caller cannot
# create an authority.  The registry is keyed by run identity so a submitted
# artifact can only resolve the authority of the run that produced it.
_EXECUTION_AUTHORITIES: dict[str, GateExecutionAuthority] = {}


def _register_execution_authority(
    run_id: str,
    items: list["GateItemResult"],
    mutations: list["MutationResult"] | None = None,
) -> GateExecutionAuthority:
    """Private factory: the Gate runner registers the typed items AND the
    typed mutation results it EXECUTED.

    This is the ONLY way an execution authority can be created.  Subsequent
    offline evaluations of the same run's artifact resolve this authority and
    are verified against the EXECUTED items and EXECUTED mutations
    (complete-match contract).

    R7-A: the authority must be registered AFTER the mutation suite completes,
    so the executed MutationResult objects (real receipts, real nonce, real
    adjudication) are bound to the trusted execution.
    """
    authority = GateExecutionAuthority(items, mutations or [], _EXECUTION_PROOF)
    _EXECUTION_AUTHORITIES[run_id] = authority
    return authority


def _resolve_execution_authority(run_id: str) -> GateExecutionAuthority | None:
    return _EXECUTION_AUTHORITIES.get(run_id)


def _live_interface_schema_hash() -> str:
    from reaction_agent.p3.manifest import build_interface_manifest, manifest_schema_hash
    return manifest_schema_hash(build_interface_manifest())


def make_evidence_reference(
    *,
    artifact_type: str,
    artifact_id: str,
    content: dict,
    run_id: str,
    fold_id: str = "",
    snapshot_id: str = "",
    snapshot_hash: str = "",
) -> EvidenceReference:
    """Build a typed evidence reference whose content hash is recomputed from
    the embedded canonical content (R4-A)."""
    return EvidenceReference(
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        content_hash=canonical_hash(content),
        schema_version="p3-1",
        run_id=run_id,
        fold_id=fold_id,
        snapshot_id=snapshot_id,
        snapshot_hash=snapshot_hash,
        content=content,
    )


def _verify_artifact_content_schema(artifact_type: str, content: dict) -> list[str]:
    """R6-A: validate a content dict against the STRICT typed content model for
    its artifact type.

    Returns a list of failures (empty = valid).  This is a real typed content
    schema: the artifact type declares which check names are valid AND which
    fields are required.  A content dict relabeled under a different artifact
    type (whose check set it does not belong to) is rejected.
    """
    schema = ARTIFACT_TYPE_CONTENT_SCHEMAS.get(artifact_type)
    if schema is None:
        return [f"EVIDENCE_ARTIFACT_SCHEMA_UNKNOWN:{artifact_type}"]
    failures: list[str] = []
    if not isinstance(content, dict):
        return [f"EVIDENCE_ARTIFACT_SCHEMA_NOT_DICT:{artifact_type}"]
    for field in schema["required"]:
        if field not in content or not content[field]:
            failures.append(
                f"EVIDENCE_ARTIFACT_SCHEMA_MISSING:{artifact_type}:{field}"
            )
    gate_checks = schema.get("gate_checks")
    if gate_checks is not None:
        check = content.get("gate_check")
        if not isinstance(check, str) or check not in gate_checks:
            failures.append(
                f"EVIDENCE_ARTIFACT_SCHEMA_CHECK:{artifact_type}:{check}"
            )
    return failures


def _evidence_lists_exact_match(
    submitted: list["EvidenceReference"], executed: list[dict]
) -> bool:
    """R6-A: complete-match contract — two evidence lists must be EXACTLY
    equal (same length, same type / id / content / content hash / schema /
    run / fold / snapshot namespace).

    R8: ``submitted`` carries the typed EvidenceReference models (from the
    submitted report); ``executed`` is the authority's independent snapshot
    (plain dicts).  Both are compared BY VALUE (canonical JSON dump), never
    by identity — mutating the returned report can never change the
    authority's snapshot."""
    if len(submitted) != len(executed):
        return False
    for a, b in zip(submitted, executed):
        if isinstance(a, EvidenceReference):
            a = a.model_dump(mode="json")
        if not isinstance(a, dict) or not isinstance(b, dict):
            return False
        if a != b:
            return False
    return True


def _verify_evidence_references(
    item: GateItemResult, artifact: dict
) -> list[str]:
    """Recompute every evidence reference's content hash and verify the
    fold/snapshot namespace binding against the CURRENT run (R4-A).

    R5-A: additionally verifies the artifact type is a KNOWN type, the
    schema version is SUPPORTED, the run_id matches the evidence's run_id,
    and the artifact ID/path actually EXISTS in the trusted execution
    context.  A reference whose content was tampered without updating its
    hash, whose content is empty, whose type/schema/run is unknown, or whose
    artifact ID does not exist is an invalid artifact.
    """
    failures: list[str] = []
    for ref in item.evidence:
        if not ref.content:
            failures.append(f"EVIDENCE_EMPTY_CONTENT:{item.item_id}")
            continue
        if ref.artifact_type not in KNOWN_ARTIFACT_TYPES:
            failures.append(f"EVIDENCE_UNKNOWN_ARTIFACT_TYPE:{item.item_id}:{ref.artifact_type}")
            continue
        if ref.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            failures.append(f"EVIDENCE_UNKNOWN_SCHEMA_VERSION:{item.item_id}:{ref.schema_version}")
            continue
        # R6-A: the content must satisfy the STRICT typed content model of the
        # declared artifact type (not just a string allowlist).
        failures.extend(_verify_artifact_content_schema(ref.artifact_type, ref.content))
        if canonical_hash(ref.content) != ref.content_hash:
            failures.append(f"EVIDENCE_HASH_MISMATCH:{item.item_id}")
        # R5-A: the evidence run_id must match the artifact's run_id.
        if artifact.get("run_id") and ref.run_id != artifact["run_id"]:
            failures.append(f"EVIDENCE_RUN_MISMATCH:{item.item_id}")
        # R4-A: when the artifact declares a namespace, every evidence
        # reference MUST carry a non-empty, matching fold/snapshot binding —
        # a reference that omits or mismatches the namespace is fail-closed.
        if artifact.get("fold_id"):
            if not ref.fold_id or ref.fold_id != artifact["fold_id"]:
                failures.append(f"EVIDENCE_FOLD_MISMATCH:{item.item_id}")
        if artifact.get("snapshot_id"):
            if not ref.snapshot_id or ref.snapshot_id != artifact["snapshot_id"]:
                failures.append(f"EVIDENCE_SNAPSHOT_MISMATCH:{item.item_id}")
        if artifact.get("snapshot_hash"):
            if not ref.snapshot_hash or ref.snapshot_hash != artifact["snapshot_hash"]:
                failures.append(f"EVIDENCE_SNAPSHOT_HASH_MISMATCH:{item.item_id}")
    return failures


def _frozen_mutation_ids() -> frozenset[str]:
    """The FROZEN mutation registry IDs (R4-A): an artifact's mutation ID set
    must EXACTLY equal this set — missing/extra/duplicate/unknown mutations
    are machinery failures."""
    from reaction_agent.p3.mutations_round3 import MUTATION_REGISTRY
    return frozenset(m["mutation_id"] for m in MUTATION_REGISTRY)


def _frozen_mutation_contracts() -> dict[str, dict]:
    """R5-B: the FULL frozen mutation contract by mutation_id.

    Each entry binds mutation_id / target_gate_item / expected_failure_code /
    baseline_case / mutated_case / component / schema_version.  The Gate
    compares the complete metadata, not just the ID set.
    """
    from reaction_agent.p3.mutations_round3 import MUTATION_REGISTRY
    return {
        m["mutation_id"]: {
            "target_gate_item": m["target_gate_item"],
            "expected_failure_code": m["expected_failure_code"],
            "baseline_case": m["baseline_case"],
            "mutated_case": m["mutated_case"],
            "component": m["component"],
            "schema_version": m["schema_version"],
        }
        for m in MUTATION_REGISTRY
    }


def _verify_mutation_contract(
    mutation: MutationResult,
    contracts: dict[str, dict],
    registry_hash: str,
    report_session_nonce: str,
) -> list[str]:
    """R5-B / R6-B: verify one mutation against the frozen registry + strict
    execution receipts.

    R6-B: the mutation outcome is DERIVED FROM THE TRUSTED EXECUTION RECEIPT
    (the unique, strict, versioned JSON payload parsed from the raw output),
    never from the submission's stored fields.  The stored typed artifact,
    artifact hash, status, failure code, case, variant, run id, component,
    schema version and session nonce must EXACTLY match the parsed receipt —
    a receipt whose raw output and typed artifact were independently
    rewritten (and re-hashed) is rejected.  ``run_id`` / ``component`` /
    ``schema_version`` / ``case`` / ``variant`` / ``session_nonce`` are
    REQUIRED non-empty fields: there is no conditional "non-empty then
    compare" path.

    Returns a list of machinery failures (empty = the mutation is valid).
    """
    failures: list[str] = []
    mid = mutation.mutation_id
    contract = contracts.get(mid)
    if contract is None:
        failures.append(f"MUTATION_NOT_IN_REGISTRY:{mid}")
        return failures
    if mutation.target_gate_item != contract["target_gate_item"]:
        failures.append(f"MUTATION_TARGET_MISMATCH:{mid}")
    if mutation.expected_failure_code != contract["expected_failure_code"]:
        failures.append(f"MUTATION_EXPECTED_CODE_MISMATCH:{mid}")
    if mutation.baseline_case != contract["baseline_case"]:
        failures.append(f"MUTATION_BASELINE_CASE_MISMATCH:{mid}")
    if mutation.mutated_case != contract["mutated_case"]:
        failures.append(f"MUTATION_MUTATED_CASE_MISMATCH:{mid}")
    if mutation.component != contract["component"]:
        failures.append(f"MUTATION_COMPONENT_MISMATCH:{mid}")
    if mutation.schema_version != contract["schema_version"]:
        failures.append(f"MUTATION_SCHEMA_VERSION_MISMATCH:{mid}")
    if mutation.registry_hash != registry_hash:
        failures.append(f"MUTATION_REGISTRY_HASH_MISMATCH:{mid}")

    # -- R6-B: session nonce binding (the report's trusted execution) ------
    if not report_session_nonce:
        failures.append(f"MUTATION_REPORT_NO_SESSION_NONCE:{mid}")
    if mutation.session_nonce != report_session_nonce:
        failures.append(f"MUTATION_SESSION_NONCE_MISMATCH:{mid}")

    # -- real strict execution receipts (R5-B / R6-B) ----------------------
    from reaction_agent.p3.mutation_harness import (
        CASE_RUNNER,
        parse_strict_receipt,
    )
    import hashlib
    import json as _json

    for side in ("baseline", "mutated"):
        run = getattr(mutation, side)
        if not run.raw_output:
            failures.append(f"MUTATION_NO_RAW_OUTPUT:{mid}:{side}")
            continue
        recomputed_stdout = hashlib.sha256(run.raw_output.encode("utf-8")).hexdigest()
        if recomputed_stdout != run.stdout_stderr_hash:
            failures.append(f"MUTATION_STDOUT_HASH_MISMATCH:{mid}:{side}")

        # R6-B: the raw output MUST contain the unique strict receipt; the
        # typed artifact is derived FROM the receipt and must EXACTLY match
        # it.  A raw output and typed artifact that were independently
        # rewritten are rejected.
        receipt = parse_strict_receipt(run.raw_output)
        if receipt is None:
            failures.append(f"MUTATION_NO_STRICT_RECEIPT:{mid}:{side}")
            continue
        parsed_artifact = receipt.get("artifact")
        if not isinstance(parsed_artifact, dict) or parsed_artifact != run.artifact:
            failures.append(f"MUTATION_RAW_ARTIFACT_MISMATCH:{mid}:{side}")
        artifact_json = _json.dumps(
            parsed_artifact, ensure_ascii=False, sort_keys=True, default=str
        )
        recomputed_artifact = hashlib.sha256(artifact_json.encode("utf-8")).hexdigest()
        if recomputed_artifact != run.artifact_hash:
            failures.append(f"MUTATION_ARTIFACT_HASH_MISMATCH:{mid}:{side}")
        if not run.artifact_hash:
            failures.append(f"MUTATION_EMPTY_ARTIFACT_HASH:{mid}:{side}")

        # R6-B: parsed receipt fields must exactly equal the typed fields.
        if receipt.get("status") != run.status:
            failures.append(f"MUTATION_RAW_STATUS_MISMATCH:{mid}:{side}")
        if receipt.get("failure_code", "") != run.failure_code:
            failures.append(f"MUTATION_RAW_FAILURE_CODE_MISMATCH:{mid}:{side}")
        if receipt.get("case") != run.case:
            failures.append(f"MUTATION_RAW_CASE_MISMATCH:{mid}:{side}")
        if receipt.get("variant") != run.variant:
            failures.append(f"MUTATION_RAW_VARIANT_MISMATCH:{mid}:{side}")
        if receipt.get("run_id") != run.run_id:
            failures.append(f"MUTATION_RAW_RUN_ID_MISMATCH:{mid}:{side}")
        if receipt.get("component") != run.component:
            failures.append(f"MUTATION_RAW_COMPONENT_MISMATCH:{mid}:{side}")
        if receipt.get("schema_version") != run.schema_version:
            failures.append(f"MUTATION_RAW_SCHEMA_MISMATCH:{mid}:{side}")
        if receipt.get("session_nonce") != run.session_nonce:
            failures.append(f"MUTATION_RAW_NONCE_MISMATCH:{mid}:{side}")

        # R6-B: REQUIRED non-empty identity fields — no conditional bypass.
        if not run.run_id:
            failures.append(f"MUTATION_EMPTY_RUN_ID:{mid}:{side}")
        if not run.component:
            failures.append(f"MUTATION_EMPTY_COMPONENT:{mid}:{side}")
        if not run.schema_version:
            failures.append(f"MUTATION_EMPTY_SCHEMA_VERSION:{mid}:{side}")
        if not run.session_nonce:
            failures.append(f"MUTATION_EMPTY_SESSION_NONCE:{mid}:{side}")
        if not run.case:
            failures.append(f"MUTATION_EMPTY_CASE:{mid}:{side}")
        if not run.variant:
            failures.append(f"MUTATION_EMPTY_VARIANT:{mid}:{side}")

        # R6-B: identity binding to the SAME trusted execution.
        if run.run_id != mutation.run_id:
            failures.append(f"MUTATION_RECEIPT_RUN_MISMATCH:{mid}:{side}")
        if run.component != contract["component"]:
            failures.append(f"MUTATION_RECEIPT_COMPONENT_MISMATCH:{mid}:{side}")
        if run.schema_version != contract["schema_version"]:
            failures.append(f"MUTATION_RECEIPT_SCHEMA_MISMATCH:{mid}:{side}")
        if run.session_nonce != mutation.session_nonce:
            failures.append(f"MUTATION_RECEIPT_NONCE_MISMATCH:{mid}:{side}")
        expected_case = (
            contract["baseline_case"] if side == "baseline"
            else contract["mutated_case"]
        )
        if run.case != expected_case:
            failures.append(f"MUTATION_RECEIPT_CASE_MISMATCH:{mid}:{side}")
        if run.variant != side:
            failures.append(f"MUTATION_RECEIPT_VARIANT_MISMATCH:{mid}:{side}")

        # status/exit-code contract: PASS->0, FAIL->1, ERROR->2
        expected_exit = {"PASS": 0, "FAIL": 1, "ERROR": 2}.get(run.status)
        if expected_exit is not None and run.exit_code != expected_exit:
            failures.append(f"MUTATION_STATUS_EXIT_MISMATCH:{mid}:{side}")

        # command/case identity: the recorded command must reference the
        # registry-mandated case runner for THIS mutation (never a
        # nonexistent program, never a different case).
        cmd = run.command
        if cmd and CASE_RUNNER not in cmd:
            failures.append(f"MUTATION_COMMAND_NOT_CASE_RUNNER:{mid}:{side}")
        if cmd and f"--case {mid}" not in " ".join(cmd) and mid not in " ".join(cmd):
            failures.append(f"MUTATION_COMMAND_CASE_MISMATCH:{mid}:{side}")

    # baseline/mutated status must match the run status.
    if mutation.baseline_status == "PASS" and mutation.baseline.status != "PASS":
        failures.append(f"MUTATION_BASELINE_STATUS_CONFLICT:{mid}")
    if mutation.baseline_status == "INVALID_BASELINE" and mutation.baseline.status == "PASS":
        failures.append(f"MUTATION_BASELINE_STATUS_CONFLICT:{mid}")
    if mutation.mutated_status != mutation.mutated.status:
        failures.append(f"MUTATION_MUTATED_STATUS_CONFLICT:{mid}")
    # observed code must match the mutated run's real failure code.
    if mutation.observed_failure_code != mutation.mutated.failure_code:
        failures.append(f"MUTATION_OBSERVED_SOURCE_MISMATCH:{mid}")
    return failures


def _typed_validate(model_cls, payload: dict):
    """Validate a plain dict against a strict model using JSON semantics.

    JSON-mode validation is used because the frozen schemas are strict:
    enum values round-trip as strings through JSON, while python-mode
    validation would reject them.  Returns the model or raises.
    """
    return model_cls.model_validate_json(json.dumps(payload))


def evaluate_gate_artifact(
    candidate_report: dict,
    *,
    trusted_context: "GateExecutionAuthority | None" = None,
) -> GateEvaluation:
    """Verify a gate artifact and derive the verdict from VERIFIED evidence.

    R6-A: ``trusted_context`` — when provided, it MUST be a
    ``GateExecutionAuthority`` (the opaque object the Gate runner created for
    the typed items it ACTUALLY executed).  A plain dict, an empty dict or any
    other object is rejected fail-closed with ``UNTRUSTED_CONTEXT``.  When
    omitted, the authority of the run that produced the artifact is resolved
    from the in-process registry (keyed by run_id); an offline artifact
    (fresh process — no registry) can at most be structurally_valid and can
    NEVER be verified=True.

    When a trusted authority is present, the verifier applies the R6-A
    COMPLETE-MATCH contract: every submitted item must EXACTLY match the
    executed item (status, title, evidence_kind and the full evidence list),
    the item set must be exactly equal (no missing / no extra), and the
    verdict is DERIVED FROM THE EXECUTED ITEMS — never from submitted statuses.

    Fail-closed machinery semantics (any of these makes the verdict FAIL,
    even when other items are BLOCKED):
    - forged / missing interface schema hash (recomputed from live schemas);
    - untyped items (status strings are never authority);
    - incomplete / duplicate / unknown / evidence-less items;
    - truthy fake trace / capability probes that fail typed parsing;
    - run-namespace inconsistency;
    - synthetic evidence presented for a real-evidence item;
    - escaped / invalid mutations;
    - empty / untrusted / missing / wrong execution authority.
    """
    ctx = trusted_context
    if not isinstance(candidate_report, dict):
        return GateEvaluation(
            verdict="FAIL", machinery_failures=["ARTIFACT_NOT_A_MAPPING"],
        )
    failures: list[str] = []
    # R6-A: a provided trusted_context MUST be a GateExecutionAuthority.  A
    # plain dict / empty dict / any other object is rejected fail-closed.
    if ctx is not None and not isinstance(ctx, GateExecutionAuthority):
        failures.append("UNTRUSTED_CONTEXT")
        ctx = None
    if ctx is None:
        # No explicit authority: resolve the authority of the run that
        # produced this artifact (if any).  An offline artifact (fresh
        # process) resolves nothing and can never be verified=True.
        run_id = candidate_report.get("run_id")
        if isinstance(run_id, str) and run_id:
            ctx = _resolve_execution_authority(run_id)

    # -- 1. Interface schema hash: recomputed from the LIVE schemas ---------
    live_schema_hash = _live_interface_schema_hash()
    provided_schema_hash = (
        candidate_report.get("interface_manifest_schema_hash")
        or candidate_report.get("schema_hash")
    )
    if not isinstance(provided_schema_hash, str) or not provided_schema_hash:
        failures.append("MISSING_SCHEMA_HASH")
    elif provided_schema_hash != live_schema_hash:
        failures.append("FORGED_SCHEMA_HASH")

    # -- 2. Typed items: a status-string dict is never authority ------------
    items_raw = candidate_report.get("items")
    items: list[GateItemResult] | None = None
    if isinstance(items_raw, list) and items_raw:
        try:
            items = [
                _typed_validate(GateItemResult, i)
                for i in items_raw
            ]
        except (ValidationError, TypeError):
            items = None
            failures.append("ITEMS_NOT_TYPED")
    else:
        # dict of status strings / empty / missing: an artifactless PASS
        # attempt — stored status strings are never authority.
        failures.append("ARTIFACTLESS_PASS")

    if items is not None:
        ids = [i.item_id for i in items]
        if len(ids) != len(set(ids)):
            failures.append("DUPLICATE_GATE_ITEM")
        unknown = sorted(set(ids) - set(REQUIRED_GATE_ITEMS))
        if unknown:
            failures.append("UNKNOWN_GATE_ITEM")
        missing = sorted(set(REQUIRED_GATE_ITEMS) - set(ids))
        if missing:
            failures.append("MISSING_GATE_ITEMS")
        for item in items:
            if not item.evidence:
                failures.append(f"GATE_ITEM_NO_EVIDENCE:{item.item_id}")
            # R4-A: every evidence reference must be a typed, content-hash-
            # verifiable, namespace-bound reference — never a bare string.
            failures.extend(_verify_evidence_references(item, candidate_report))
            if (
                item.item_id in REAL_EVIDENCE_ITEMS
                and item.status == "PASS"
                and item.evidence_kind is not EvidenceKind.real
            ):
                failures.append("SYNTHETIC_AS_REAL_EVIDENCE")

    # -- 3. Typed trace / capability probes (truthy fakes fail parsing) -----
    from reaction_agent.p3.schemas import CandidateTrace, CapabilityStatus
    trace = candidate_report.get("candidate_trace")
    if trace is not None:
        try:
            parsed_trace = _typed_validate(CandidateTrace, trace)
        except (ValidationError, TypeError):
            parsed_trace = None
            failures.append("INVALID_CANDIDATE_TRACE")
        if parsed_trace is not None:
            if (
                "run_id" in candidate_report
                and candidate_report["run_id"] != parsed_trace.run_id
            ):
                failures.append("TRACE_NAMESPACE_MISMATCH")
    probes = candidate_report.get("capability_probes")
    if probes is not None:
        try:
            parsed_probes = _typed_validate(CapabilityStatus, probes)
        except (ValidationError, TypeError):
            parsed_probes = None
            failures.append("INVALID_CAPABILITY_PROBES")
        if parsed_probes is not None:
            if (
                "run_id" in candidate_report
                and candidate_report["run_id"] != parsed_probes.run_id
            ):
                failures.append("CAPABILITY_NAMESPACE_MISMATCH")

    # -- 4. Run namespace consistency ----------------------------------------
    if "run_id" in candidate_report and "candidate_run_id" in candidate_report:
        if candidate_report["run_id"] != candidate_report["candidate_run_id"]:
            failures.append("NAMESPACE_MISMATCH")

    # -- 5. Mutations: REQUIRED, typed, exact frozen-registry match --------
    # R4-A: an artifact WITHOUT real mutation evidence is an artifactless
    # PASS attempt.  The mutation set is mandatory: missing or empty must
    # fail, and the mutation ID set must EXACTLY equal the frozen registry.
    # R5-B: the FULL metadata (target/expected/cases/component/schema) and
    # the canonical registry hash are compared against the frozen contract,
    # and every execution receipt is recomputed from real raw output.
    # R7-A: when a trusted execution authority is present, the submitted
    # mutations are additionally EXACT-MATCHED against the EXECUTED mutations
    # (below) — a missing/extra/reordered/full-field-rewritten mutation is a
    # verification failure.
    mutations: list[MutationResult] = []
    mutations_raw = candidate_report.get("mutations")
    if "mutations" not in candidate_report:
        failures.append("MISSING_MUTATIONS")
    elif mutations_raw is None or mutations_raw == []:
        failures.append("EMPTY_MUTATIONS")
    elif not isinstance(mutations_raw, list):
        failures.append("INVALID_MUTATION_RECORDS")
    else:
        try:
            mutations = [
                _typed_validate(MutationResult, m)
                for m in mutations_raw
            ]
        except (ValidationError, TypeError):
            failures.append("INVALID_MUTATION_RECORDS")
        if mutations:
            ids = [m.mutation_id for m in mutations]
            if len(ids) != len(set(ids)):
                failures.append("MUTATION_ID_DUPLICATE")
            frozen = _frozen_mutation_ids()
            if set(ids) != frozen:
                failures.append(
                    "MUTATION_ID_MISMATCH"
                    f":{sorted(set(ids) ^ frozen)}"
                )
            contracts = _frozen_mutation_contracts()
            from reaction_agent.p3.mutations_round3 import mutation_registry_hash
            registry_hash = mutation_registry_hash()
            # R5-B: the artifact must carry the registry hash and it must
            # equal the live frozen registry hash.
            provided_registry_hash = candidate_report.get("mutation_registry_hash", "")
            if provided_registry_hash != registry_hash:
                failures.append("MUTATION_REGISTRY_HASH_MISMATCH")
            for mutation in mutations:
                # R4-A: every mutation must carry REAL baseline/mutated
                # execution artifacts and be internally consistent; the
                # observed code must be the one the machinery actually
                # emitted against the expected code.
                if not mutation.baseline.artifact_hash or not mutation.baseline.stdout_stderr_hash:
                    failures.append(f"MUTATION_NO_BASELINE_ARTIFACT:{mutation.mutation_id}")
                if not mutation.mutated.artifact_hash or not mutation.mutated.stdout_stderr_hash:
                    failures.append(f"MUTATION_NO_MUTATED_ARTIFACT:{mutation.mutation_id}")
                if mutation.mutated_status == "PASS":
                    failures.append(f"MUTATION_ESCAPED:{mutation.mutation_id}")
                if mutation.mutated_status == "ERROR":
                    failures.append(f"MUTATED_RUN_ERROR:{mutation.mutation_id}")
                if mutation.baseline_status != "PASS":
                    failures.append(f"MUTATION_INVALID_BASELINE:{mutation.mutation_id}")
                if mutation.observed_failure_code != mutation.expected_failure_code:
                    failures.append(
                        f"MUTATION_OBSERVED_CODE_MISMATCH:{mutation.mutation_id}"
                    )
                if not mutation.caught or not mutation.valid:
                    failures.append(f"MUTATION_ESCAPED:{mutation.mutation_id}")
                # R5-B / R6-B: full-metadata contract + strict receipt
                # verification against the report's trusted execution.
                report_session_nonce = candidate_report.get("session_nonce", "")
                failures.extend(
                    _verify_mutation_contract(
                        mutation, contracts, registry_hash, report_session_nonce,
                    )
                )

    # -- Verdict --------------------------------------------------------------
    # R6-A: verified requires a trusted GateExecutionAuthority (never a plain
    # dict, never an empty dict).  Without it the artifact is at most
    # structurally_valid; it can never be verified=True.  When an authority
    # IS present, the verifier applies the COMPLETE-MATCH contract:
    #
    #   every submitted item must EXACTLY match the executed item — status,
    #   title, evidence_kind and the full evidence list (type / id / content /
    #   content hash / schema / run / fold / snapshot namespace);
    #   the submitted item set must EXACTLY equal the executed item set —
    #   a missing OR extra item is a verification failure;
    #   the verdict is DERIVED FROM THE EXECUTED ITEMS, never from submitted
    #   statuses.
    has_trusted_context = isinstance(ctx, GateExecutionAuthority) and bool(ctx.items)
    verification_failures: list[str] = []
    if isinstance(ctx, GateExecutionAuthority) and not ctx.items:
        # R6-A: an empty execution authority is not an authority — fail-closed.
        verification_failures.append("EMPTY_EXECUTION_AUTHORITY")
    if has_trusted_context and items is not None:
        assert ctx is not None
        # R8: the authority exposes parsed COPIES of its independent canonical
        # snapshots — comparing against them is an exact-match against the
        # executed audit basis, never against the submitted (mutable) objects.
        executed_ids = {item["item_id"] for item in ctx.items}
        submitted_ids = {i.item_id for i in items}
        missing_executed = sorted(executed_ids - submitted_ids)
        extra_submitted = sorted(submitted_ids - executed_ids)
        if missing_executed:
            verification_failures.append(
                f"EXECUTED_ITEM_MISSING:{missing_executed}"
            )
        if extra_submitted:
            verification_failures.append(
                f"SUBMITTED_ITEM_EXTRA:{extra_submitted}"
            )
        for item in items:
            executed = ctx.executed(item.item_id)
            if executed is None:
                verification_failures.append(
                    f"EXECUTED_ITEM_MISSING:{item.item_id}"
                )
                continue
            if item.status != executed["status"]:
                verification_failures.append(
                    f"EXECUTED_STATUS_MISMATCH:{item.item_id}"
                )
            if item.title != executed["title"]:
                verification_failures.append(
                    f"EXECUTED_TITLE_MISMATCH:{item.item_id}"
                )
            if item.evidence_kind.value != executed["evidence_kind"]:
                verification_failures.append(
                    f"EXECUTED_EVIDENCE_KIND_MISMATCH:{item.item_id}"
                )
            if not _evidence_lists_exact_match(item.evidence, executed["evidence"]):
                verification_failures.append(
                    f"EXECUTED_EVIDENCE_MISMATCH:{item.item_id}"
                )
    # R7-A: with a trusted authority the submitted mutations must EXACTLY
    # match the EXECUTED mutations (same count, same order, same full record —
    # baseline + mutated receipts, every hash, status, failure code, case,
    # variant, session nonce, adjudication).  A missing / extra / duplicate /
    # reordered / fully-synchronized-rewritten mutation is a verification
    # failure — FAIL, never a masked PASS.  The mutation verdict, caught/valid
    # and observed code are therefore derived from the EXECUTED mutations (the
    # submitted copies are forced to be identical), never from an internally
    # consistent but forged submission.
    if has_trusted_context:
        assert ctx is not None
        # R8: the executed mutations are the authority's independent canonical
        # snapshots (parsed dict copies) — the submitted mutation is compared
        # BY VALUE against the executed audit basis, never by identity.
        executed_mutations = list(ctx.mutations)
        submitted_mutations = list(mutations)
        if len(executed_mutations) != len(submitted_mutations):
            verification_failures.append(
                "EXECUTED_MUTATION_COUNT_MISMATCH"
                f":executed={len(executed_mutations)}:submitted={len(submitted_mutations)}"
            )
        else:
            executed_ids = [m["mutation_id"] for m in executed_mutations]
            submitted_ids = [m.mutation_id for m in submitted_mutations]
            for i, (sub, exe) in enumerate(
                zip(submitted_mutations, executed_mutations)
            ):
                if sub.mutation_id != exe["mutation_id"]:
                    verification_failures.append(
                        "EXECUTED_MUTATION_ORDER_MISMATCH"
                        f":{sub.mutation_id}:executed_position={i}:{exe['mutation_id']}"
                    )
                if sub.model_dump(mode="json") != exe:
                    verification_failures.append(
                        f"EXECUTED_MUTATION_MISMATCH:{sub.mutation_id}"
                    )
    if failures or verification_failures:
        # A machinery invariant failure is FAIL — never masked by BLOCKED.
        return GateEvaluation(
            verdict="FAIL", machinery_failures=failures + verification_failures,
            structurally_valid=bool(items),
            item_statuses=(
                {i.item_id: i.status for i in items} if items else {}
            ),
        )
    assert items is not None  # ARTIFACTLESS_PASS otherwise
    # R6-A: with a trusted authority the verdict comes from the EXECUTED
    # items (the live typed objects), never from submitted statuses.
    # R8: the authority's item snapshots are parsed copies — the verdict is
    # derived from the independent audit basis, never from submitted objects.
    if has_trusted_context:
        assert ctx is not None
        statuses = {i["item_id"]: i["status"] for i in ctx.items}
    else:
        statuses = {i.item_id: i.status for i in items}
    if any(s == "FAIL" for s in statuses.values()):
        verdict = "FAIL"
    elif any(s == "BLOCKED" for s in statuses.values()):
        verdict = "BLOCKED"
    else:
        verdict = "PASS"
    return GateEvaluation(
        verdict=verdict,
        verified=has_trusted_context,
        structurally_valid=True,
        item_statuses=statuses,
    )


def evaluate_gate_from_artifacts(candidate_report: dict) -> str:
    """Derive the verdict from VERIFIED ARTIFACTS, never a stored status
    string (R3-A). Backward-compatible verdict-only entry point."""
    return evaluate_gate_artifact(candidate_report).verdict


# -- Mutation registry: REAL baseline/mutated executions (R3-F) --------------


def _mutation_outcomes() -> list[MutationResult]:
    """Run the R3-F mutation harness: every mutation is executed as two
    separate subprocess runs (baseline + mutated) with real recorded
    evidence.

    R5-B: the records carry the frozen registry metadata (baseline/mutated
    case, component, schema version, registry hash) and the REAL raw output
    + typed artifact so the Gate can recompute every hash.

    R6-B: every receipt is bound to the SAME trusted execution session (the
    process session nonce) and the SAME run identity as the Gate report.
    """
    from reaction_agent.p3.mutation_harness import (
        run_mutation_suite,
        session_nonce,
    )
    from reaction_agent.p3.mutations_round3 import (
        MUTATION_REGISTRY,
        mutation_registry_hash,
    )
    records = run_mutation_suite()
    registry_hash = mutation_registry_hash()
    meta_by_id = {
        c["mutation_id"]: c for c in MUTATION_REGISTRY
    }
    nonce = session_nonce()
    mutations: list[MutationResult] = []
    for record in records:
        meta = meta_by_id.get(record["mutation_id"], {})
        mutations.append(MutationResult(
            mutation_id=record["mutation_id"],
            target_gate_item=record["target_gate_item"],
            expected_failure_code=record["expected_failure_code"],
            baseline_status=record["baseline_status"],
            mutated_status=record["mutated_status"],
            baseline=MutationCaseRun(**record["baseline"]),
            mutated=MutationCaseRun(**record["mutated"]),
            observed_failure_code=record["observed_failure_code"],
            caught=record["caught"],
            valid=record["valid"],
            invalid_reason=record["invalid_reason"],
            baseline_case=meta.get("baseline_case", ""),
            mutated_case=meta.get("mutated_case", ""),
            component=meta.get("component", ""),
            schema_version=meta.get("schema_version", ""),
            registry_hash=registry_hash,
            run_id="p3_gate",
            session_nonce=nonce,
        ))
    return mutations


def _kernel_machinery_items(ns: dict) -> list[GateItemResult]:
    """Machinery items verified by running the deterministic kernel on
    explicit synthetic fixtures (never satisfy real-evidence items).  Every
    item's evidence is a typed reference to the ACTUAL executed kernel run
    (content hash recomputable by the verifier) (R4-A)."""
    items: list[GateItemResult] = []

    r1 = run_kernel(input_smiles="CCCCCCCCO", case_id="g04a", fold_id="fold_fx_p3", mode="fixture")
    r2 = run_kernel(input_smiles="OCCCCCCCC", case_id="g04b", fold_id="fold_fx_p3", mode="fixture")
    ok_equiv = (
        r1.candidates
        and r2.candidates
        and {c.canonical_product_identity for c in r1.candidates}
        == {c.canonical_product_identity for c in r2.candidates}
    )
    items.append(GateItemResult(
        item_id="G04", title="equivalent SMILES invariant",
        status="PASS" if ok_equiv else "FAIL",
        evidence=[make_evidence_reference(
            artifact_type="kernel_run", artifact_id=r1.run_id,
            content={
                "gate_check": "equivalent_smiles_invariant",
                "octanol_candidates": sorted(
                    c.canonical_product_identity for c in r1.candidates
                ),
                "permuted_candidates": sorted(
                    c.canonical_product_identity for c in r2.candidates
                ),
                "same_candidate_set": ok_equiv,
            },
            # R5-A: the evidence reference belongs to the GATE run namespace;
            # the actual kernel run id is recorded as artifact_id.
            run_id="p3_gate", **ns,
        )],
        evidence_kind=EvidenceKind.synthetic_fixture,
    ))

    ok_no_llm = bool(r1.candidates) and all(
        c.origin == "deterministic_kernel" for c in r1.candidates
    )
    items.append(GateItemResult(
        item_id="G05", title="no LLM structure creation",
        status="PASS" if ok_no_llm else "FAIL",
        evidence=[make_evidence_reference(
            artifact_type="kernel_run", artifact_id=r1.run_id,
            content={
                "gate_check": "no_llm_structure_creation",
                "candidate_origins": sorted(
                    {c.origin for c in r1.candidates}
                ),
                "all_deterministic_kernel": ok_no_llm,
            },
            run_id="p3_gate", **ns,
        )],
        evidence_kind=EvidenceKind.synthetic_fixture,
    ))

    real = run_kernel(input_smiles="CCCCCCCCO", case_id="g06", fold_id="fold_real", mode="real")
    ok_sep = real.status.value == "blocked" and all(f.category == "system" for f in real.failures)
    items.append(GateItemResult(
        item_id="G06", title="system failure / abstention separate",
        status="PASS" if ok_sep else "FAIL",
        evidence=[make_evidence_reference(
            artifact_type="kernel_run", artifact_id=real.run_id,
            content={
                "gate_check": "system_failure_abstention_separate",
                "real_mode_status": real.status.value,
                "failure_categories": sorted({f.category for f in real.failures}),
                "separated": ok_sep,
            },
            run_id="p3_gate", **ns,
        )],
        evidence_kind=EvidenceKind.diagnostic,
    ))

    ok_oct = bool(r1.candidates) and r1.candidates[0].canonical_product_identity == "CCCCCCCC=O"
    items.append(GateItemResult(
        item_id="G08", title="octanol carbon regression (CCCCCCCCO -> CCCCCCCC=O)",
        status="PASS" if ok_oct else "FAIL",
        evidence=[make_evidence_reference(
            artifact_type="kernel_run", artifact_id=r1.run_id,
            content={
                "gate_check": "octanol_carbon_regression",
                "product_identity": (
                    r1.candidates[0].canonical_product_identity
                    if r1.candidates else None
                ),
                "regression_ok": ok_oct,
            },
            run_id="p3_gate", **ns,
        )],
        evidence_kind=EvidenceKind.synthetic_fixture,
    ))

    from reaction_agent.p3.fixtures import build_train_view, load_fixture_reactions, find_donor_ref
    from reaction_agent.p3.load import load_reaction_evidence
    tv = build_train_view(load_fixture_reactions())
    donor, ref = find_donor_ref(tv, "fx_oct")
    dev = load_reaction_evidence(tv, donor.donor_id, ref)
    mapping = dev.context.mapping_report
    ok_formal = mapping.mechanistic_atom_origin is None
    items.append(GateItemResult(
        item_id="G09", title="formal mapping not mechanism",
        status="PASS" if ok_formal else "FAIL",
        evidence=[make_evidence_reference(
            artifact_type="capability_probe", artifact_id=dev.donor_id,
            content={
                "gate_check": "formal_mapping_not_mechanism",
                "mechanistic_atom_origin": (
                    None if mapping.mechanistic_atom_origin is None
                    else mapping.mechanistic_atom_origin
                ),
                "ok": ok_formal,
            },
            run_id="p3_gate", **ns,
        )],
        evidence_kind=EvidenceKind.synthetic_fixture,
    ))

    ok_assumptions = bool(r1.candidates) and all(
        "donor_context_is_assumption_not_x_y_fact"
        in c.candidate_analogy_ledger.inherited_assumptions
        for c in r1.candidates
    )
    items.append(GateItemResult(
        item_id="G10", title="candidate donor context labeled assumptions",
        status="PASS" if ok_assumptions else "FAIL",
        evidence=[make_evidence_reference(
            artifact_type="kernel_run", artifact_id=r1.run_id,
            content={
                "gate_check": "candidate_donor_context_labeled_assumptions",
                "candidate_ledgers": [
                    c.candidate_analogy_ledger.inherited_assumptions
                    for c in r1.candidates
                ],
                "ok": ok_assumptions,
            },
            run_id="p3_gate", **ns,
        )],
        evidence_kind=EvidenceKind.synthetic_fixture,
    ))

    return items


def _replay_item(ns: dict) -> GateItemResult:
    r1 = run_kernel(input_smiles="CCCCCCCCO", case_id="g02a", fold_id="fold_fx_p3", mode="fixture", seed=7)
    r2 = run_kernel(input_smiles="CCCCCCCCO", case_id="g02b", fold_id="fold_fx_p3", mode="fixture", seed=7)
    ok = (
        [c.candidate_id for c in r1.candidates] == [c.candidate_id for c in r2.candidates]
        and [c.canonical_product_identity for c in r1.candidates]
        == [c.canonical_product_identity for c in r2.candidates]
    )
    return GateItemResult(
        item_id="G02", title="strict candidate replayable",
        status="PASS" if ok else "FAIL",
        evidence=[make_evidence_reference(
            artifact_type="kernel_run", artifact_id=r1.run_id,
            content={
                "gate_check": "strict_candidate_replayable",
                "first_candidate_ids": [c.candidate_id for c in r1.candidates],
                "second_candidate_ids": [c.candidate_id for c in r2.candidates],
                "replay_identical": ok,
            },
            run_id="p3_gate", **ns,
        )],
        evidence_kind=EvidenceKind.synthetic_fixture,
    )


def _real_evidence_items(ns: dict) -> list[GateItemResult]:
    """Items that REQUIRE real evidence; honestly BLOCKED when absent."""
    from reaction_agent.p3.capability import build_capability_status

    status, _ = build_capability_status("gate_real", "q", "fold_real", "case_gate", snapshot_path=None)
    snapshot_ok = status.real_snapshot_available
    donor_ok = status.automatic_donor_available
    return [
        GateItemResult(
            item_id="G01", title="X-only automatic end-to-end (real evidence)",
            status="BLOCKED" if not (snapshot_ok and donor_ok) else "PASS",
            evidence=[make_evidence_reference(
                artifact_type="capability_probe", artifact_id="cap_real",
                content={
                    "gate_check": "x_only_automatic_end_to_end",
                    "real_snapshot_available": snapshot_ok,
                    "automatic_donor_available": donor_ok,
                },
                run_id="p3_gate", **ns,
            )],
            evidence_kind=EvidenceKind.blocked,
        ),
        GateItemResult(
            item_id="G03", title="donor/reaction/lineage/transform/site/dual-ledger complete (real)",
            status="BLOCKED" if not snapshot_ok else "PASS",
            evidence=[make_evidence_reference(
                artifact_type="capability_probe", artifact_id="cap_real",
                content={
                    "gate_check": "donor_reaction_lineage_transform_site_dual_ledger_complete",
                    "real_snapshot_available": snapshot_ok,
                },
                run_id="p3_gate", **ns,
            )],
            evidence_kind=EvidenceKind.blocked,
        ),
        GateItemResult(
            item_id="G07", title="pilot funnel operational",
            status="BLOCKED",
            evidence=[make_evidence_reference(
                artifact_type="capability_probe", artifact_id="cap_real",
                content={
                    "gate_check": "pilot_funnel_operational",
                    "blocker": "P2 formal Gate BLOCKED; pilot funnel not available",
                },
                run_id="p3_gate", **ns,
            )],
            evidence_kind=EvidenceKind.blocked,
        ),
    ]


def run_p3_gate(*, run_mutations: bool = True) -> GateReport:
    """Run the full P3 Gate.

    Verdict derivation:
    - any item FAIL OR any invalid/escaped mutation -> FAIL (a machinery
      invariant failure dominates blockers and can never be masked);
    - else any BLOCKED (real evidence missing) -> BLOCKED;
    - else PASS (requires ALL items to pass with verified evidence).

    The finished report is re-verified through ``evaluate_gate_artifact``:
    the gate never trusts its own construction path either.  R4-A: the
    report ALWAYS carries the full frozen mutation set (mandatory evidence)
    and binds its own run/snapshot/fold namespace so every evidence
    reference is verifiable against the CURRENT execution.
    """
    from reaction_agent.p3.manifest import build_interface_manifest, manifest_schema_hash

    from reaction_agent.p3.fixtures import build_train_view, load_fixture_reactions
    gate_tv = build_train_view(load_fixture_reactions())
    ns = {
        "fold_id": "fold_fx_p3",
        "snapshot_id": gate_tv.snapshot_id,
        "snapshot_hash": gate_tv.snapshot_hash,
    }

    items: list[GateItemResult] = [_replay_item(ns)]
    items += _kernel_machinery_items(ns)
    items += _real_evidence_items(ns)

    # R4-A: the gate report ALWAYS carries the full frozen mutation set
    # (mandatory evidence).  run_mutations only controls whether the suite is
    # forcibly re-run; cached real executions are used otherwise.
    mutations = _mutation_outcomes()

    # R6-A / R7-A: the ACTUAL executed typed items AND the ACTUAL executed
    # mutation results are bound to an opaque GateExecutionAuthority (only the
    # runner can create it) and registered under the run identity.  The
    # authority is registered AFTER the mutation suite completes so the
    # executed MutationResult objects (real receipts, real nonce, real
    # adjudication) are bound to the trusted execution.  The self-verification
    # below passes it EXPLICITLY; a later offline evaluation of the same run's
    # artifact resolves it by run_id and is verified against the EXECUTED
    # items and EXECUTED mutations.
    _register_execution_authority("p3_gate", items, mutations)
    mutation_invalid = any(not m.valid for m in mutations)

    has_fail = any(item.status == "FAIL" for item in items)
    has_blocked = any(item.status == "BLOCKED" for item in items)

    if has_fail or mutation_invalid:
        verdict = "FAIL"
    elif has_blocked:
        verdict = "BLOCKED"
    else:
        verdict = "PASS"

    interface_hash = manifest_schema_hash(build_interface_manifest())
    from reaction_agent.p3.mutations_round3 import mutation_registry_hash
    from reaction_agent.p3.mutation_harness import session_nonce
    registry_hash = mutation_registry_hash()
    report = GateReport(
        gate_id="p3_gate",
        schema_version="p3-gate-3",
        verdict=verdict,
        items=items,
        mutations=mutations,
        interface_manifest_schema_hash=interface_hash,
        derived_from_artifacts=False,
        run_id="p3_gate",
        **ns,
        mutation_registry_hash=registry_hash,
        # R6-B: every mutation receipt is bound to the SAME trusted execution
        # session as this report.
        session_nonce=session_nonce(),
        notes=(
            "Verdict derived from executed kernel runs + capability probes + "
            "real baseline/mutated mutation executions; never from a stored "
            "status string. Synthetic fixtures verify machinery only and "
            "cannot satisfy real-evidence Gate items. Any machinery invariant "
            "failure (including escaped/invalid mutations) is FAIL, never "
            "masked by a BLOCKED. R6-A: verified requires the in-process "
            "GateExecutionAuthority (complete-match contract); R6-B: mutation "
            "receipts are strict, versioned JSON payloads parsed from the raw "
            "output and bound to the current run/session/component/schema; "
            "R7-A: the authority binds the EXECUTED mutation results too — "
            "submitted mutations must exactly match the executed mutations "
            "(count/order/full record), so a fully-synchronized raw+typed "
            "receipt rewrite is rejected."
        ),
    )

    # Self-verification through the same typed artifact evaluation a
    # reviewer would apply (R3-A): if our own artifact fails verification,
    # the verdict is FAIL regardless of items.  The execution authority is
    # passed EXPLICITLY (R6-A).
    evaluation = evaluate_gate_artifact(
        report.model_dump(mode="json"),
        trusted_context=_resolve_execution_authority("p3_gate"),
    )
    if evaluation.machinery_failures:
        report = report.model_copy(update={
            "verdict": "FAIL",
            "derived_from_artifacts": False,
            "notes": report.notes
            + f" SELF-VERIFICATION FAILED: {evaluation.machinery_failures}",
        })
    else:
        report = report.model_copy(update={
            "derived_from_artifacts": bool(items),
        })
    return report


def exit_code_for(verdict: str) -> int:
    """PASS=0, FAIL=1, BLOCKED=2 (distinct exit codes for the runner)."""
    if verdict == "PASS":
        return 0
    if verdict == "FAIL":
        return 1
    return 2
