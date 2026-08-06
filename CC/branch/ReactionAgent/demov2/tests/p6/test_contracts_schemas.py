"""T1+T2 RED tests — 4 MCP tool contracts + strict JSON schemas.

These tests define the P6 kernel contract BEFORE implementation exists.
They must FAIL (RED) until the kernel is built, then PASS (GREEN).

Scope:
- T1: high-level tool contracts (names, input/output shapes).
- T2: strict JSON schemas (additionalProperties:false, enums, required,
  limits, typed errors, cross-field, golden schemas).
"""
from __future__ import annotations

import json

import pytest

from reaction_agent.schemas.common import StrictModel

# Modules under test (will not import until implemented → RED)
from reaction_agent.mcp.schemas import (
    GOLDEN_SCHEMAS,
    MCP_TOOL_SCHEMAS,
    P6_SCHEMA_VERSION,
    SchemaError,
    validate_input,
)


# =====================================================================
# T1 — High-level contracts
# =====================================================================

EXPECTED_TOOL_NAMES = {
    "reaction.predict_analogical_products_v1",
    "reaction.get_run_v1",
    "reaction.get_candidate_evidence_v1",
    "reaction.expand_evidence_v1",
}


class TestToolContracts:
    """T1: the 4 MCP tools exist and are exposed with schemas."""

    def test_all_four_tools_defined(self):
        # Every required tool must have a schema entry.
        missing = EXPECTED_TOOL_NAMES - set(GOLDEN_SCHEMAS.keys())
        assert not missing, f"missing tool schemas: {missing}"
        assert len(GOLDEN_SCHEMAS) == 4

    def test_tool_names_are_fully_qualified(self):
        for name in GOLDEN_SCHEMAS:
            assert name.startswith("reaction."), f"tool {name} not namespaced"
            assert name.endswith("_v1"), f"tool {name} lacks version suffix"

    def test_each_schema_has_stable_version(self):
        # Every golden schema is versioned.
        for name, schema in GOLDEN_SCHEMAS.items():
            assert schema.get("schema_version") == P6_SCHEMA_VERSION, name

    def test_side_effects_contract_matches_f3_matrix(self):
        # F3 matrix: predict=append_write_immutable_run, get=read-only,
        # local expand=append_immutable_child_run, network=False.
        # The golden schema must declare side_effect + network per tool.
        side_effects = {n: GOLDEN_SCHEMAS[n].get("side_effect") for n in GOLDEN_SCHEMAS}
        assert side_effects["reaction.predict_analogical_products_v1"] == "append_write_immutable_run"
        assert side_effects["reaction.get_run_v1"] == "read-only"
        assert side_effects["reaction.get_candidate_evidence_v1"] == "read-only"
        assert side_effects["reaction.expand_evidence_v1"] == "append_immutable_child_run"
        for n in GOLDEN_SCHEMAS:
            assert GOLDEN_SCHEMAS[n].get("network") is False, f"{n} must be network=False (MVP)"


# =====================================================================
# T2 — Strict JSON schemas
# =====================================================================


class TestStrictSchemas:
    """T2: strict JSON schema enforcement."""

    def test_predict_schema_required_fields(self):
        schema = MCP_TOOL_SCHEMAS["reaction.predict_analogical_products_v1"]
        props = schema["properties"]
        required = schema["required"]
        # substrate identity + idempotency + snapshot are mandatory.
        assert "substrate_smiles" in required
        assert "idempotency_key" in required
        assert "snapshot_id" in required
        assert "substrate_smiles" in props

    def test_predict_additional_properties_false(self):
        schema = MCP_TOOL_SCHEMAS["reaction.predict_analogical_products_v1"]
        assert schema["additionalProperties"] is False
        # nested objects also forbid extras
        assert schema["properties"]["budgets"]["additionalProperties"] is False

    def test_unknown_field_rejected(self):
        payload = {
            "substrate_smiles": "CCO",
            "idempotency_key": "k1",
            "snapshot_id": "snap-1",
            "bogus_field": 1,
        }
        with pytest.raises(SchemaError):
            validate_input("reaction.predict_analogical_products_v1", payload)

    def test_bad_type_rejected_typed(self):
        payload = {
            "substrate_smiles": "CCO",
            "idempotency_key": "k1",
            "snapshot_id": "snap-1",
            "budgets": {"max_candidates": "many"},  # string, not int
        }
        with pytest.raises(SchemaError):
            validate_input("reaction.predict_analogical_products_v1", payload)

    def test_missing_required_rejected(self):
        with pytest.raises(SchemaError):
            validate_input("reaction.predict_analogical_products_v1", {"substrate_smiles": "CCO"})

    def test_schema_error_has_code_and_message(self):
        try:
            validate_input("reaction.predict_analogical_products_v1", {"nope": 1})
        except SchemaError as e:
            assert e.code  # machine-readable typed code
            assert str(e.message)
        else:
            pytest.fail("expected SchemaError")

    def test_limits_enforced(self):
        # max_candidates capped at 200
        payload = {
            "substrate_smiles": "CCO",
            "idempotency_key": "k1",
            "snapshot_id": "snap-1",
            "budgets": {"max_candidates": 9999},
        }
        with pytest.raises(SchemaError):
            validate_input("reaction.predict_analogical_products_v1", payload)

    def test_get_run_schema_required(self):
        schema = MCP_TOOL_SCHEMAS["reaction.get_run_v1"]
        assert "run_id" in schema["required"]
        assert schema["additionalProperties"] is False

    def test_get_candidate_evidence_required(self):
        schema = MCP_TOOL_SCHEMAS["reaction.get_candidate_evidence_v1"]
        assert "run_id" in schema["required"]
        assert "evidence_id" in schema["required"]
        assert schema["additionalProperties"] is False

    def test_expand_evidence_required_and_cross_field(self):
        schema = MCP_TOOL_SCHEMAS["reaction.expand_evidence_v1"]
        assert "run_id" in schema["required"]
        assert "idempotency_key" in schema["required"]
        assert schema["additionalProperties"] is False

    def test_cross_field_parent_and_expansion_not_both(self):
        # Cross-field: expand requires max_depth >= 1 and budgets.max_expansions >= 1.
        payload = {
            "run_id": "run-1",
            "evidence_id": "ev-1",
            "idempotency_key": "k1",
            "snapshot_id": "snap-1",
            "budgets": {"max_expansions": 0},  # must be >= 1
        }
        with pytest.raises(SchemaError):
            validate_input("reaction.expand_evidence_v1", payload)

    def test_golden_schemas_are_stable_documents(self):
        # Golden schemas: every MCP schema has a matching golden JSON doc.
        for name in EXPECTED_TOOL_NAMES:
            assert name in GOLDEN_SCHEMAS
            assert "input_schema" in GOLDEN_SCHEMAS[name]
            # golden input schema is a JSON-serializeable dict
            json.dumps(GOLDEN_SCHEMAS[name]["input_schema"])

    def test_golden_and_mcp_schemas_consistent(self):
        # The MCP tool schemas must match the golden schema versions.
        for name in EXPECTED_TOOL_NAMES:
            assert MCP_TOOL_SCHEMAS[name]["schema_version"] == GOLDEN_SCHEMAS[name]["schema_version"]