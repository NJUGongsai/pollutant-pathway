"""R5-D: manifest_schema_hash MUST cover every nested unknown semantic field.

Round 4 defect: the manifest hash hand-projected each interface into a fixed
subset of fields.  Adding a NEW semantic field to the manifest (e.g.
``interfaces.StrictCandidate.unknown_semantic_contract``) did NOT change the
hash:

    nested_unknown_manifest_field_keeps_hash=True

R5-D contract: the hash is computed over the COMPLETE canonical manifest
dump.  Only the explicitly declared, versioned non-semantic display fields
(producer/consumer/generated_from/hash_algorithm) are excluded via a JSON
path allowlist.  Any other field — top-level, interface-level, nested dict,
nested list element — is semantic by default and MUST change the hash
(fail-closed).  Equivalent dict ordering must NOT change the hash.

These tests are RED on the R4 code (nested unknown fields keep the hash) and
GREEN after R5-D.
"""
from __future__ import annotations

import pytest

from reaction_agent.p3.manifest import (
    NON_SEMANTIC_MANIFEST_FIELDS,
    build_interface_manifest,
    manifest_schema_hash,
)


def _base_hash() -> str:
    return manifest_schema_hash(build_interface_manifest())


# -- 1. unknown top-level semantic field -------------------------------------


def test_unknown_top_level_semantic_field_changes_hash():
    base = _base_hash()
    manifest = build_interface_manifest()
    manifest["unknown_top_level_semantic"] = {"forged": True}
    assert manifest_schema_hash(manifest) != base


# -- 2. unknown interface-level field -----------------------------------------


def test_unknown_interface_level_field_changes_hash():
    base = _base_hash()
    manifest = build_interface_manifest()
    manifest["interfaces"]["StrictCandidate"]["unknown_semantic_contract"] = {
        "requirement": "hash must cover this",
    }
    assert manifest_schema_hash(manifest) != base


# -- 3. unknown nested dict field ---------------------------------------------


def test_unknown_nested_dict_field_changes_hash():
    base = _base_hash()
    manifest = build_interface_manifest()
    manifest["nested_record_contract"]["unknown_nested_dict_field"] = {"x": 1}
    assert manifest_schema_hash(manifest) != base


# -- 4. unknown nested list element field -------------------------------------


def test_unknown_nested_list_element_field_changes_hash():
    base = _base_hash()
    manifest = build_interface_manifest()
    manifest["p4_must_not"] = manifest["p4_must_not"] + ["unknown_element"]
    assert manifest_schema_hash(manifest) != base


# -- 5. known semantic field mutation -----------------------------------------


def test_known_semantic_field_mutation_changes_hash():
    base = _base_hash()
    manifest = build_interface_manifest()
    manifest["manifest_version"] = "forged"
    assert manifest_schema_hash(manifest) != base
    manifest2 = build_interface_manifest()
    manifest2["interfaces"]["StrictCandidate"]["fields"] = ["forged"]
    assert manifest_schema_hash(manifest2) != base


# -- 6. explicit non-semantic field mutation does NOT change hash -------------


def test_explicit_non_semantic_field_mutation_keeps_hash():
    base = _base_hash()
    manifest = build_interface_manifest()
    for field in NON_SEMANTIC_MANIFEST_FIELDS:
        manifest[field] = "FORGED_DISPLAY"
    assert manifest_schema_hash(manifest) == base


# -- 7. dict ordering invariance ----------------------------------------------


def test_equivalent_dict_ordering_keeps_hash():
    base = _base_hash()
    manifest = build_interface_manifest()
    manifest["interfaces"] = dict(
        sorted(manifest["interfaces"].items(), reverse=True)
    )
    assert manifest_schema_hash(manifest) == base


# -- 8. manifest schema/version drift -----------------------------------------


def test_manifest_schema_version_drift_changes_hash():
    base = _base_hash()
    manifest = build_interface_manifest()
    manifest["interfaces"]["StrictCandidate"]["schema_version"] = "p3-999"
    assert manifest_schema_hash(manifest) != base


# -- R4-D regression: the previously covered semantic contract fields ---------


_SEMANTIC_TAMPERS = [
    ("nested_record_contract.mode", lambda m: m["nested_record_contract"].update({"mode": "forged_mode"})),
    ("nested_record_contract.binding_fields", lambda m: m["nested_record_contract"].update({"binding_fields": ["forged"]})),
    ("nested_record_contract.binding_version", lambda m: m["nested_record_contract"].update({"binding_version": "forged"})),
    ("nested_record_contract.preimage_includes", lambda m: m["nested_record_contract"].update({"preimage_includes": ["forged"]})),
    ("nested_record_contract.enforced_by", lambda m: m["nested_record_contract"].update({"enforced_by": ["forged"]})),
    ("id_preimage_contract", lambda m: m.update({"id_preimage_contract": "FORGED_PREIMAGE"})),
    ("evidence_kind_semantics", lambda m: m.update({"evidence_kind_semantics": {"forged": "x"}})),
    ("blocker_semantics", lambda m: m.update({"blocker_semantics": "FORGED_BLOCKER"})),
    ("p4_must_not", lambda m: m.update({"p4_must_not": ["FORGED_NOT"]})),
    ("run_namespace_required", lambda m: m.update({"run_namespace_required": ["forged"]})),
    ("manifest_version", lambda m: m.update({"manifest_version": "forged"})),
    ("interfaces.fields", lambda m: m["interfaces"]["StrictCandidate"].update({"fields": ["forged"]})),
    ("interfaces.required_fields", lambda m: m["interfaces"]["StrictCandidate"].update({"required_fields": ["forged"]})),
    ("interfaces.schema_hash", lambda m: m["interfaces"]["StrictCandidate"].update({"schema_hash": "forged"})),
    ("interfaces.run_namespace_fields", lambda m: m["interfaces"]["StrictCandidate"].update({"run_namespace_fields": ["forged"]})),
    ("interfaces.namespace_binding", lambda m: m["interfaces"]["StrictCandidate"].update({"namespace_binding": "forged"})),
    ("interfaces.schema_version", lambda m: m["interfaces"]["StrictCandidate"].update({"schema_version": "p3-999"})),
]


@pytest.mark.parametrize("label,tamper", _SEMANTIC_TAMPERS)
def test_r4d_semantic_contract_tamper_changes_hash(label, tamper):
    base = _base_hash()
    manifest = build_interface_manifest()
    tamper(manifest)
    assert manifest_schema_hash(manifest) != base, (
        f"semantic contract tamper {label!r} did NOT change manifest_schema_hash"
    )