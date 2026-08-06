"""R4-D: manifest_schema_hash MUST protect the full semantic contract.

ChatGPT P3 Round 3 audit independently showed that tampering
``nested_record_contract.mode`` / ``id_preimage_contract`` (and other
semantic contract fields) does NOT change ``manifest_schema_hash``.

This test asserts the OPPOSITE: any semantic contract tamper MUST change
the hash (fail-closed), while semantically irrelevant input ordering must
NOT change it.
"""
from __future__ import annotations

import pytest

from reaction_agent.p3.manifest import build_interface_manifest, manifest_schema_hash


def _base_hash() -> str:
    return manifest_schema_hash(build_interface_manifest())


# -- semantic contract fields that MUST be covered by the hash -------------

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
def test_semantic_contract_tamper_changes_hash(label, tamper):
    base = _base_hash()
    manifest = build_interface_manifest()
    tamper(manifest)
    changed = manifest_schema_hash(manifest)
    assert changed != base, (
        f"semantic contract tamper {label!r} did NOT change manifest_schema_hash"
    )


# -- explicit non-semantic display fields MAY be excluded ------------------


def test_non_semantic_display_fields_may_not_change_hash():
    base = _base_hash()
    manifest = build_interface_manifest()
    # producer/consumer/generated_from/hash_algorithm are documentation-only
    # display fields; they are explicitly declared non-semantic.
    manifest["producer"] = "FORGED_PRODUCER"
    manifest["consumer"] = "FORGED_CONSUMER"
    manifest["generated_from"] = "FORGED_GEN"
    manifest["hash_algorithm"] = "FORGED_ALG"
    assert manifest_schema_hash(manifest) == base


# -- semantically irrelevant ordering must not change the hash -------------


def test_equivalent_ordering_does_not_change_hash():
    base = _base_hash()
    manifest = build_interface_manifest()
    # Reorder interfaces dict (semantically irrelevant) — hash must be stable.
    manifest["interfaces"] = dict(
        sorted(manifest["interfaces"].items(), reverse=True)
    )
    assert manifest_schema_hash(manifest) == base
    # Reorder p4_must_not list semantically irrelevant? NO — order of a list
    # of independent prohibitions is semantic.  Only dict ordering is tested.