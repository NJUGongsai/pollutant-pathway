"""MCP side-effect policy — single machine-readable source of truth.

This is the ONLY authoritative definition of MCP tool contracts.
ADR-0006 must be consistent with this file. Tests import from here.
"""

from reaction_agent.schemas.common import StrictModel, NonEmptyStr


class ToolSideEffect(StrictModel):
    """Side-effect contract for one MCP tool."""
    tool_name: NonEmptyStr
    evidence_corpus: NonEmptyStr
    run_store: NonEmptyStr
    network: bool
    idempotency: NonEmptyStr


class IdempotencyRule(StrictModel):
    """Idempotency semantics for MCP tools."""
    scenario: NonEmptyStr
    expected_behavior: NonEmptyStr


class RunInvariant(StrictModel):
    """Immutability invariant for runs."""
    invariant_name: NonEmptyStr
    description: NonEmptyStr


# -- Tool side-effect matrix --

MCP_TOOL_CONTRACTS: list[ToolSideEffect] = [
    ToolSideEffect(
        tool_name="predict",
        evidence_corpus="read-only",
        run_store="append_write_immutable_run",
        network=False,
        idempotency="request_hash_snapshot_version_idempotency_key_reuse",
    ),
    ToolSideEffect(
        tool_name="get_run",
        evidence_corpus="read-only",
        run_store="read-only",
        network=False,
        idempotency="read_only_idempotent",
    ),
    ToolSideEffect(
        tool_name="get_candidate_evidence",
        evidence_corpus="read-only",
        run_store="read-only",
        network=False,
        idempotency="read_only_idempotent",
    ),
    ToolSideEffect(
        tool_name="expand_evidence_local",
        evidence_corpus="read-only",
        run_store="append_immutable_child_run",
        network=False,
        idempotency="child_request_reuse",
    ),
    ToolSideEffect(
        tool_name="expand_evidence_external",
        evidence_corpus="append_augmentation_provenance",
        run_store="append_child_augmentation",
        network=True,
        idempotency="independent_retrieval_request_hash",
    ),
]


# -- Idempotency rules --

IDEMPOTENCY_RULES: list[IdempotencyRule] = [
    IdempotencyRule(
        scenario="same_key_same_request",
        expected_behavior="reuse_run",
    ),
    IdempotencyRule(
        scenario="same_key_different_request",
        expected_behavior="typed_conflict",
    ),
    IdempotencyRule(
        scenario="concurrent_identical",
        expected_behavior="atomic_dedup",
    ),
]


# -- Run immutability invariants --

RUN_INVARIANTS: list[RunInvariant] = [
    RunInvariant(
        invariant_name="completed_run_immutable",
        description="Completed/frozen runs cannot be modified in place",
    ),
    RunInvariant(
        invariant_name="frozen_run_immutable",
        description="Frozen runs are immutable; evidence expansion creates child run",
    ),
    RunInvariant(
        invariant_name="child_run_preserves_parent",
        description="Child run does not modify parent run",
    ),
    RunInvariant(
        invariant_name="resource_uris_opaque",
        description="Resource URIs are opaque; agents must not derive them",
    ),
]


# -- Validation helpers --

def get_tool_contract(tool_name: str) -> ToolSideEffect | None:
    """Get tool contract by name."""
    for tc in MCP_TOOL_CONTRACTS:
        if tc.tool_name == tool_name:
            return tc
    return None


def validate_policy_integrity() -> list[str]:
    """Validate policy integrity. Returns list of issues (empty = valid)."""
    issues = []
    tool_names = [tc.tool_name for tc in MCP_TOOL_CONTRACTS]

    if len(tool_names) != len(set(tool_names)):
        issues.append("Duplicate tool names in MCP_TOOL_CONTRACTS")

    required_tools = {"predict", "get_run", "get_candidate_evidence",
                      "expand_evidence_local", "expand_evidence_external"}
    missing = required_tools - set(tool_names)
    if missing:
        issues.append(f"Missing required tools: {missing}")

    for tc in MCP_TOOL_CONTRACTS:
        if tc.tool_name == "predict" and "immutable" not in tc.run_store:
            issues.append(f"predict run_store should mention immutability")

    if len(IDEMPOTENCY_RULES) != 3:
        issues.append(f"Expected 3 idempotency rules, got {len(IDEMPOTENCY_RULES)}")

    if len(RUN_INVARIANTS) != 4:
        issues.append(f"Expected 4 run invariants, got {len(RUN_INVARIANTS)}")

    return issues
