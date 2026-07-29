"""ADR-0006: MCP side-effect — tests import from formal contract artifact."""

import pytest
from reaction_agent.contracts.mcp_side_effects import (
    MCP_TOOL_CONTRACTS,
    IDEMPOTENCY_RULES,
    RUN_INVARIANTS,
    get_tool_contract,
    validate_policy_integrity,
    ToolSideEffect,
    IdempotencyRule,
    RunInvariant,
)


@pytest.mark.contract
def test_policy_integrity():
    issues = validate_policy_integrity()
    assert issues == [], f"MCP policy integrity issues: {issues}"


@pytest.mark.contract
def test_five_tool_contracts():
    assert len(MCP_TOOL_CONTRACTS) == 5


@pytest.mark.contract
def test_predict_is_mutation():
    tc = get_tool_contract("predict")
    assert tc is not None
    assert "immutable" in tc.run_store
    assert tc.network is False


@pytest.mark.contract
def test_get_tools_are_read_only():
    for name in ["get_run", "get_candidate_evidence"]:
        tc = get_tool_contract(name)
        assert tc is not None
        assert tc.evidence_corpus == "read-only"
        assert tc.run_store == "read-only"


@pytest.mark.contract
def test_local_expand_creates_child_run():
    tc = get_tool_contract("expand_evidence_local")
    assert tc is not None
    assert "child" in tc.run_store
    assert tc.evidence_corpus == "read-only"


@pytest.mark.contract
def test_external_expand_has_network():
    tc = get_tool_contract("expand_evidence_external")
    assert tc is not None
    assert tc.network is True


@pytest.mark.contract
def test_three_idempotency_rules():
    assert len(IDEMPOTENCY_RULES) == 3
    scenarios = {r.scenario for r in IDEMPOTENCY_RULES}
    assert "same_key_same_request" in scenarios
    assert "same_key_different_request" in scenarios
    assert "concurrent_identical" in scenarios


@pytest.mark.contract
def test_same_key_same_request_reuses():
    for r in IDEMPOTENCY_RULES:
        if r.scenario == "same_key_same_request":
            assert r.expected_behavior == "reuse_run"


@pytest.mark.contract
def test_same_key_different_request_conflicts():
    for r in IDEMPOTENCY_RULES:
        if r.scenario == "same_key_different_request":
            assert r.expected_behavior == "typed_conflict"


@pytest.mark.contract
def test_concurrent_identical_dedup():
    for r in IDEMPOTENCY_RULES:
        if r.scenario == "concurrent_identical":
            assert r.expected_behavior == "atomic_dedup"


@pytest.mark.contract
def test_four_run_invariants():
    assert len(RUN_INVARIANTS) == 4
    names = {i.invariant_name for i in RUN_INVARIANTS}
    assert "completed_run_immutable" in names
    assert "frozen_run_immutable" in names
    assert "child_run_preserves_parent" in names
    assert "resource_uris_opaque" in names


@pytest.mark.contract
def test_all_tool_contracts_are_typed():
    for tc in MCP_TOOL_CONTRACTS:
        assert isinstance(tc, ToolSideEffect)


@pytest.mark.contract
def test_get_tool_contract_returns_none_for_unknown():
    assert get_tool_contract("nonexistent_tool") is None
