"""P1-G10 hard-condition H2: real proline/2OG cases fail closed.

The legacy audit located three real source rows whose old donor/product pair
crossed scaffold lineages.  Until the new pipeline has a validated complete
mapping plus an independently checked lineage resolution, those rows must be
explicitly quarantined and must never enter production.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from reaction_agent.lineage.required_case import (
    REQUIRED_CASE_POLICY_VERSION,
    quarantine_unresolved_required_case,
)
from reaction_agent.mapping.adapter import RealMapperAdapter
from reaction_agent.schemas.common import MappingStatus, QuarantineBehavior
from reaction_agent.schemas.p1_entities import NormalizedReactionRecord


ROOT = Path(__file__).resolve().parents[2]
LEGACY_AUDIT = ROOT / "reports" / "data_audit" / "legacy_lineage_audit.json"


def _required_rows() -> list[dict]:
    audit = json.loads(LEGACY_AUDIT.read_text(encoding="utf-8"))
    return [
        row for row in audit["examples"]
        if row.get("required_case") == "proline_2og"
    ]


def _map(row: dict):
    mapper = RealMapperAdapter(backend="rdkit")
    assert mapper.is_available(), "P1 preflight must provide the RDKit diagnostic mapper"
    return mapper.map_reaction(NormalizedReactionRecord(
        reaction_id=row["reaction_id"],
        source_record_id=row["source_id"],
        normalized_reaction=row["reaction_smiles"],
        raw_reaction=row["reaction_smiles"],
        direction="forward",
    ))


def test_all_three_real_required_rows_are_explicitly_quarantined():
    rows = _required_rows()
    assert len(rows) == 3

    dispositions = [
        quarantine_unresolved_required_case(row, _map(row)) for row in rows
    ]

    assert {item.source_id for item in dispositions} == {
        row["source_id"] for row in rows
    }
    for disposition in dispositions:
        assert disposition.disposition == "quarantined"
        assert disposition.production_eligible is False
        assert disposition.resolved_lineages == []
        assert disposition.forbidden_lineage_present is False
        assert disposition.mapping_status in {
            MappingStatus.partially_mapped,
            MappingStatus.mapping_ambiguous,
            MappingStatus.unmapped,
            MappingStatus.mapping_failed,
        }
        assert disposition.fallback_method == "mcs"
        assert disposition.quarantine_record.source_record_id == disposition.source_id
        assert disposition.quarantine_record.quarantine_behavior == QuarantineBehavior.quarantined
        assert disposition.quarantine_record.category == "required_case_lineage_unresolved"
        assert disposition.policy_version == REQUIRED_CASE_POLICY_VERSION


def test_required_case_quarantine_is_deterministic():
    row = _required_rows()[0]
    report = _map(row)
    first = quarantine_unresolved_required_case(row, report)
    second = quarantine_unresolved_required_case(dict(row), report.model_copy(deep=True))
    assert first == second
    assert first.disposition_id == second.disposition_id
    assert first.quarantine_record.record_id == second.quarantine_record.record_id


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("required_case", "some_other_case"),
        ("category", "supported_pair"),
        ("source_id", ""),
        ("reaction_id", ""),
        ("reaction_smiles", ""),
    ],
)
def test_non_authoritative_or_malformed_row_cannot_receive_required_case_disposition(
    field: str, value: str,
):
    row = dict(_required_rows()[0])
    report = _map(row)
    row[field] = value
    with pytest.raises(ValueError, match="required_case_quarantine_input_invalid"):
        quarantine_unresolved_required_case(row, report)


def test_complete_map_still_does_not_silently_resolve_legacy_cross_lineage_case():
    """A map is not itself a validated multi-lineage resolution.

    Mutating the report to look complete must not promote the known legacy
    cross-lineage row.  This helper's only authorized outcome is quarantine;
    a future resolver needs its own separately audited promotion path.
    """
    row = _required_rows()[0]
    report = _map(row).model_copy(update={
        "mapping_status": MappingStatus.fully_mapped,
        "fallback_method": None,
    })
    disposition = quarantine_unresolved_required_case(row, report)
    assert disposition.production_eligible is False
    assert disposition.disposition == "quarantined"
    assert disposition.resolved_lineages == []


def test_mechanistic_claim_is_rejected_by_this_formal_quarantine_path():
    row = _required_rows()[0]
    report = _map(row)
    # A bare mapping adapter must never provide mechanistic evidence; the
    # quarantine policy refuses any unexpected mechanistic upgrade so it
    # cannot legitimize such a claim.
    assert report.mechanistic_atom_origin is None

