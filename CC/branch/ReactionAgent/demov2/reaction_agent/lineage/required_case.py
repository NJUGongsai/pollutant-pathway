"""Fail-closed disposition for the real P1 proline/2OG required cases.

The G03 legacy audit proves that the historical selected pair crossed two
dominant scaffold lineages.  A generic formal mapper (and especially an MCS
fallback) cannot repair that scientific defect by itself.  This module owns a
narrow, explicit production boundary: a known unresolved G03 required row is
quarantined until a separately validated lineage resolver produces an audited
multi-lineage result.

This module deliberately does *not* infer the expected proline→hydroxyproline
or 2-oxoglutarate→succinate edges.  Quarantine is evidence-preserving; it is
not a disguised resolution.
"""
from __future__ import annotations

from typing import Literal

from reaction_agent.hashing import stable_id
from reaction_agent.schemas.common import (
    MappingStatus,
    NonEmptyStr,
    QuarantineBehavior,
    StrictModel,
)
from reaction_agent.schemas.mapping import MappingReport
from reaction_agent.schemas.p1_entities import QuarantineRecord


REQUIRED_CASE_POLICY_VERSION = "p1-required-case-quarantine-1"
_REQUIRED_CASE = "proline_2og"
_LEGACY_DEFECT_CATEGORY = "cross_lineage_pair"


class RequiredCaseDisposition(StrictModel):
    """Auditable outcome for one known real required-case source row."""

    disposition_id: NonEmptyStr
    source_id: NonEmptyStr
    reaction_id: NonEmptyStr
    required_case: Literal["proline_2og"]
    legacy_category: Literal["cross_lineage_pair"]
    mapping_status: MappingStatus
    fallback_method: str | None
    disposition: Literal["quarantined"]
    production_eligible: Literal[False]
    resolved_lineages: list[dict] = []
    forbidden_lineage_present: Literal[False]
    quarantine_record: QuarantineRecord
    evidence_ids: list[NonEmptyStr]
    policy_version: NonEmptyStr = REQUIRED_CASE_POLICY_VERSION


def _required_non_empty_string(row: dict, field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"required_case_quarantine_input_invalid: {field} must be a "
            "non-empty string"
        )
    return value


def quarantine_unresolved_required_case(
    legacy_audit_row: dict,
    mapping_report: MappingReport,
) -> RequiredCaseDisposition:
    """Quarantine one authoritative G03 proline/2OG cross-lineage row.

    The function has no promotion branch.  Even a complete formal map is not
    equivalent to a validated multi-participant lineage resolution, so callers
    cannot use this narrow safety path to place the row in production.

    Raises:
        ValueError: the input is not the authoritative required-case shape or
            contains an unexpected mechanistic-origin claim.
    """
    if not isinstance(legacy_audit_row, dict):
        raise ValueError(
            "required_case_quarantine_input_invalid: legacy audit row must be an object"
        )

    source_id = _required_non_empty_string(legacy_audit_row, "source_id")
    reaction_id = _required_non_empty_string(legacy_audit_row, "reaction_id")
    reaction_smiles = _required_non_empty_string(legacy_audit_row, "reaction_smiles")
    required_case = legacy_audit_row.get("required_case")
    category = legacy_audit_row.get("category")
    if required_case != _REQUIRED_CASE:
        raise ValueError(
            "required_case_quarantine_input_invalid: required_case must be "
            f"{_REQUIRED_CASE!r}"
        )
    if category != _LEGACY_DEFECT_CATEGORY:
        raise ValueError(
            "required_case_quarantine_input_invalid: category must be "
            f"{_LEGACY_DEFECT_CATEGORY!r}"
        )
    if source_id != reaction_id:
        raise ValueError(
            "required_case_quarantine_input_invalid: source_id and reaction_id "
            "must identify the same audited source row"
        )
    if mapping_report.mechanistic_atom_origin is not None:
        raise ValueError(
            "required_case_quarantine_input_invalid: this formal safety path "
            "cannot accept mechanistic atom-origin claims"
        )

    row_evidence_id = stable_id("ev_g03_required_case", {
        "source_id": source_id,
        "reaction_smiles": reaction_smiles,
        "legacy_category": category,
    })
    mapping_evidence_id = stable_id("ev_formal_mapping", {
        "source_id": source_id,
        "mapping_output_hash": mapping_report.output_hash,
        "mapping_status": mapping_report.mapping_status.value,
        "fallback_method": mapping_report.fallback_method,
    })
    evidence_ids = [row_evidence_id, mapping_evidence_id]

    disposition_id = stable_id("rcd", {
        "source_id": source_id,
        "required_case": required_case,
        "mapping_output_hash": mapping_report.output_hash,
        "policy_version": REQUIRED_CASE_POLICY_VERSION,
        "disposition": "quarantined",
    })
    quarantine_id = stable_id("qr", {
        "disposition_id": disposition_id,
        "source_id": source_id,
        "policy_version": REQUIRED_CASE_POLICY_VERSION,
    })
    reason = (
        "known_legacy_cross_lineage_pair_has_no_independently_validated_"
        "multi_lineage_resolution"
    )
    quarantine = QuarantineRecord(
        record_id=quarantine_id,
        reason=reason,
        category="required_case_lineage_unresolved",
        evidence_ids=evidence_ids,
        source_record_id=source_id,
        quarantine_behavior=QuarantineBehavior.quarantined,
        notes=(
            "Fail-closed P1 required-case policy. Formal mapping status="
            f"{mapping_report.mapping_status.value}; fallback="
            f"{mapping_report.fallback_method or 'none'}. No lineage was "
            "synthesized and this row is excluded from production."
        ),
    )

    return RequiredCaseDisposition(
        disposition_id=disposition_id,
        source_id=source_id,
        reaction_id=reaction_id,
        required_case="proline_2og",
        legacy_category="cross_lineage_pair",
        mapping_status=mapping_report.mapping_status,
        fallback_method=mapping_report.fallback_method,
        disposition="quarantined",
        production_eligible=False,
        resolved_lineages=[],
        forbidden_lineage_present=False,
        quarantine_record=quarantine,
        evidence_ids=evidence_ids,
        policy_version=REQUIRED_CASE_POLICY_VERSION,
    )

