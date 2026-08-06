"""P6 MCP Service — strict JSON schemas and golden schema registry.

Defines the 4 MCP tool contracts:
- reaction.predict_analogical_products_v1
- reaction.get_run_v1
- reaction.get_candidate_evidence_v1
- reaction.expand_evidence_v1

Every tool has:
- ``MCP_TOOL_SCHEMAS``: the input JSON Schema used by the MCP server
  (additionalProperties:false, enums, required, limits, cross-field).
- ``GOLDEN_SCHEMAS``: a stable, versioned golden document (includes the
  input schema, side-effect contract, and network flag) used as the
  single source of truth for audits and tests.

Side-effect contract (F3 matrix / ADR-0006), one line each:
- predict                     → append_write_immutable_run,  network=False
- get_run                     → read-only,                   network=False
- get_candidate_evidence      → read-only,                   network=False
- expand_evidence_v1          → append_immutable_child_run,  network=False
"""
from __future__ import annotations

import json
import re
from typing import Any

from reaction_agent.mcp.errors import SchemaError

P6_SCHEMA_VERSION = "p6-1"

# Identifier pattern (GATE-P6-07): client-controlled identifiers reach the
# filesystem (run_id / idempotency_key / evidence_id / snapshot_id /
# client_request_id / tenant_id all become file names or path components),
# so they must be path-safe — reject '/', '\\', leading '.', whitespace, and
# any char that could traverse or escape the store root. Anchored full-match.
IDENT_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"

# -- shared budget sub-schema (additionalProperties:false, limits) --

_BUDGET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "max_candidates": {"type": "integer", "minimum": 1, "maximum": 200},
        "max_expansions": {"type": "integer", "minimum": 0, "maximum": 50},
    },
}

_IDEM_FIELDS: dict[str, Any] = {
    "client_request_id": {
        "type": "string", "minLength": 1, "maxLength": 128, "pattern": IDENT_PATTERN,
    },
    "idempotency_key": {
        "type": "string", "minLength": 1, "maxLength": 128, "pattern": IDENT_PATTERN,
    },
    "snapshot_id": {
        "type": "string", "minLength": 1, "maxLength": 128, "pattern": IDENT_PATTERN,
    },
}

# =====================================================================
# MCP tool input schemas (strict)
# =====================================================================

MCP_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "reaction.predict_analogical_products_v1": {
        "schema_version": P6_SCHEMA_VERSION,
        "type": "object",
        "additionalProperties": False,
        "required": ["substrate_smiles", "idempotency_key", "snapshot_id"],
        "properties": {
            "substrate_smiles": {"type": "string", "minLength": 1, "maxLength": 4096},
            **_IDEM_FIELDS,
            "budgets": _BUDGET_SCHEMA,
        },
    },
    "reaction.get_run_v1": {
        "schema_version": P6_SCHEMA_VERSION,
        "type": "object",
        "additionalProperties": False,
        "required": ["run_id"],
        "properties": {
            "run_id": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": IDENT_PATTERN},
        },
    },
    "reaction.get_candidate_evidence_v1": {
        "schema_version": P6_SCHEMA_VERSION,
        "type": "object",
        "additionalProperties": False,
        "required": ["run_id", "evidence_id"],
        "properties": {
            "run_id": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": IDENT_PATTERN},
            "evidence_id": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": IDENT_PATTERN},
        },
    },
    "reaction.expand_evidence_v1": {
        "schema_version": P6_SCHEMA_VERSION,
        "type": "object",
        "additionalProperties": False,
        "required": ["run_id", "evidence_id", "idempotency_key", "snapshot_id"],
        "properties": {
            "run_id": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": IDENT_PATTERN},
            "evidence_id": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": IDENT_PATTERN},
            **_IDEM_FIELDS,
            "budgets": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "max_expansions": {"type": "integer", "minimum": 1, "maximum": 50},
                },
            },
        },
    },
}

# =====================================================================
# Golden schema registry (stable, versioned, includes side effects)
# =====================================================================

GOLDEN_SCHEMAS: dict[str, dict[str, Any]] = {
    "reaction.predict_analogical_products_v1": {
        "schema_version": P6_SCHEMA_VERSION,
        "side_effect": "append_write_immutable_run",
        "network": False,
        "input_schema": MCP_TOOL_SCHEMAS["reaction.predict_analogical_products_v1"],
    },
    "reaction.get_run_v1": {
        "schema_version": P6_SCHEMA_VERSION,
        "side_effect": "read-only",
        "network": False,
        "input_schema": MCP_TOOL_SCHEMAS["reaction.get_run_v1"],
    },
    "reaction.get_candidate_evidence_v1": {
        "schema_version": P6_SCHEMA_VERSION,
        "side_effect": "read-only",
        "network": False,
        "input_schema": MCP_TOOL_SCHEMAS["reaction.get_candidate_evidence_v1"],
    },
    "reaction.expand_evidence_v1": {
        "schema_version": P6_SCHEMA_VERSION,
        "side_effect": "append_immutable_child_run",
        "network": False,
        "input_schema": MCP_TOOL_SCHEMAS["reaction.expand_evidence_v1"],
    },
}

# =====================================================================
# Validation
# =====================================================================


def _type_violation(path: str, expected: str, got: Any) -> str:
    return f"field '{path}': expected {expected}, got {type(got).__name__}"


def _check_object(value: Any, schema: dict, path: str) -> list[str]:
    """Recursively validate ``value`` against a strict JSON schema grammar.

    Supports: type object/string/integer/boolean, additionalProperties:false,
    required list, minLength/maxLength, minimum/maximum, enum.
    Returns a list of human+machine readable violations (empty = valid).
    """
    errors: list[str] = []

    if not isinstance(value, dict):
        return [_type_violation(path or "payload", "object", value)]

    # required
    for req in schema.get("required", []):
        if req not in value:
            errors.append(f"field '{path}.{req}' is required")

    # additionalProperties:false
    if schema.get("additionalProperties") is False:
        allowed = set(schema.get("properties", {}).keys())
        for key in value:
            if key not in allowed:
                errors.append(f"unknown field '{path}.{key}'")

    # property constraints
    properties = schema.get("properties", {})
    for key, spec in properties.items():
        if key not in value:
            continue
        val = value[key]
        sub = f"{path}.{key}" if path else key
        etype = spec.get("type")
        if etype == "object":
            errors.extend(_check_object(val, spec, sub))
            continue
        if etype == "string":
            if not isinstance(val, str):
                errors.append(_type_violation(sub, "string", val))
                continue
            if val.strip() == "":
                errors.append(f"field '{sub}' must not be empty")
            if "minLength" in spec and len(val) < spec["minLength"]:
                errors.append(f"field '{sub}' too short (min {spec['minLength']})")
            if "maxLength" in spec and len(val) > spec["maxLength"]:
                errors.append(f"field '{sub}' too long (max {spec['maxLength']})")
            if "pattern" in spec and not re.fullmatch(spec["pattern"], val):
                errors.append(f"field '{sub}': invalid format (pattern mismatch)")
            if "enum" in spec and val not in spec["enum"]:
                errors.append(f"field '{sub}': invalid enum value '{val}'")
        elif etype == "integer":
            if not isinstance(val, int) or isinstance(val, bool):
                errors.append(_type_violation(sub, "integer", val))
                continue
            if "minimum" in spec and val < spec["minimum"]:
                errors.append(f"field '{sub}' below minimum {spec['minimum']}")
            if "maximum" in spec and val > spec["maximum"]:
                errors.append(f"field '{sub}' above maximum {spec['maximum']}")
        elif etype == "boolean":
            if not isinstance(val, bool):
                errors.append(_type_violation(sub, "boolean", val))
    return errors


def _cross_field_violations(tool_name: str, value: dict) -> list[str]:
    """Cross-field invariants per tool (in addition to the JSON schema)."""
    errors: list[str] = []
    if tool_name == "reaction.expand_evidence_v1":
        budgets = value.get("budgets")
        if budgets is not None and isinstance(budgets, dict):
            max_exp = budgets.get("max_expansions")
            if isinstance(max_exp, int) and not isinstance(max_exp, bool) and max_exp < 1:
                errors.append(
                    "field 'budgets.max_expansions' must be >= 1 for expansion"
                )
    # predict: budgets.max_candidates must be >= 1 (already in minimum; kept explicit)
    if tool_name == "reaction.predict_analogical_products_v1":
        budgets = value.get("budgets")
        if budgets is not None and isinstance(budgets, dict):
            max_cand = budgets.get("max_candidates")
            if isinstance(max_cand, int) and not isinstance(max_cand, bool) and max_cand < 1:
                errors.append("field 'budgets.max_candidates' must be >= 1")
    return errors


def validate_input(tool_name: str, payload: dict) -> dict:
    """Validate a request payload against the tool's strict schema.

    Returns the validated payload (unchanged, immutable) or raises
    :class:`SchemaError` with a typed machine-readable code and message.
    """
    if tool_name not in MCP_TOOL_SCHEMAS:
        raise SchemaError(f"unknown tool '{tool_name}'")

    schema = MCP_TOOL_SCHEMAS[tool_name]
    errors = _check_object(payload, schema, "")
    # Cross-field invariants only apply to dict payloads — a non-dict
    # already produced a typed type-violation above and must not crash the
    # validator with an AttributeError (T6: no uncaught exception leak).
    if isinstance(payload, dict):
        errors.extend(_cross_field_violations(tool_name, payload))
    if errors:
        raise SchemaError("; ".join(errors))
    return payload


def golden_document(tool_name: str) -> dict:
    """Return a deep-copied golden schema document (JSON-serializable)."""
    import copy
    return copy.deepcopy(GOLDEN_SCHEMAS[tool_name])


def golden_json(tool_name: str) -> str:
    """Serialized golden document (stable, for audit evidence)."""
    return json.dumps(GOLDEN_SCHEMAS[tool_name], sort_keys=True, ensure_ascii=False)