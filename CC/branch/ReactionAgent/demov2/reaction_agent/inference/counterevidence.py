"""P4-T3 counterevidence collection (final_design §16.2, §16.3).

Only the allowed typed counterevidence reasons may be collected. database
absence, "no second enzyme", similar molecule not covered, source not
reporting negative, low frequency, and inaccessible test fold are NEVER
negative evidence — they are only "not observed / unknown". The collector
fails closed on any forbidden-negative input.
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash, stable_id
from reaction_agent.policies.p4_decision_policy import (
    P4_POLICY_VERSION,
    ALLOWED_COUNTEREVIDENCE,
)
from reaction_agent.schemas.p4.counterevidence import (
    CounterevidenceType,
    CounterevidenceRecord,
    CounterevidenceCollection,
)

# Forbidden-negative context keys (never negative evidence).
_FORBIDDEN_NEGATIVE_KEYS = (
    "forbidden_negative",
    "database_absence",
    "no_second_enzyme",
    "low_frequency",
    "not_covered",
    "source_no_negative",
    "test_fold_inaccessible",
    "similar_molecule_not_covered",
)

# Counterevidence types that constitute a scientific EVIDENCE_CONFLICT.
CONFLICT_TYPES = frozenset({
    CounterevidenceType.LEDGER_CONTRADICTION,
    CounterevidenceType.PROVENANCE_DIRECTION_ROLE_CONFLICT,
    CounterevidenceType.COMPETING_TRANSFORM,
})

# context key -> allowed counterevidence type.
_CONTEXT_TYPE_MAP = {
    "competing_transform": CounterevidenceType.COMPETING_TRANSFORM,
    "failed_preconditions": CounterevidenceType.FAILED_TRANSFORM_PRECONDITIONS,
    "site_incompatibility": CounterevidenceType.SITE_INCOMPATIBILITY,
    "invalid_generation": CounterevidenceType.INVALID_GENERATION,
    "ledger_contradiction": CounterevidenceType.LEDGER_CONTRADICTION,
    "provenance_direction_role_conflict": (
        CounterevidenceType.PROVENANCE_DIRECTION_ROLE_CONFLICT),
    "strict_failure_only_relaxation": (
        CounterevidenceType.STRICT_FAILURE_ONLY_RELAXATION),
    "all_support_low_quality": (
        CounterevidenceType.ALL_SUPPORT_LOW_QUALITY_OR_SAME_SOURCE),
}


def _evidence_ids_for_transform(evidence_records, transform_id: str) -> list[str]:
    matched: list[str] = []
    for rec in evidence_records:
        transforms = rec.transformation_hypotheses if not isinstance(rec, dict) \
            else rec.get("transformation_hypotheses", [])
        if transform_id in (transforms or []):
            rid = rec.reaction_id if not isinstance(rec, dict) else rec.get("reaction_id", "")
            matched.append(rid)
    # Never fabricate an unresolved id; unmatched targets surface in detail.
    return matched


def _source_identity(evidence_records, evidence_ids: list[str]) -> str:
    for rec in evidence_records:
        rid = rec.reaction_id if not isinstance(rec, dict) else rec.get("reaction_id", "")
        if rid in evidence_ids:
            name = rec.source_name if not isinstance(rec, dict) else rec.get("source_name", "")
            ver = rec.source_version if not isinstance(rec, dict) else rec.get("source_version", "")
            return f"{name}/{ver}"
    return "unknown"


def _reject_forbidden(context: dict, allow_forbidden_negatives: bool) -> None:
    """Fail closed on any forbidden-negative presence in the context."""
    for key in _FORBIDDEN_NEGATIVE_KEYS:
        if key in context:
            raise ValueError(
                f"forbidden negative counterevidence refused: {key!r} "
                f"(absence is never negative)")


def collect_counterevidence(
    candidate,
    evidence_records,
    resolution,
    context: dict | None = None,
    allow_forbidden_negatives: bool = False,
) -> CounterevidenceCollection:
    """Collect only ALLOWED typed counterevidence for a candidate."""
    context = context or {}
    _reject_forbidden(context, allow_forbidden_negatives)

    cand_id = candidate.candidate_id
    records: list[CounterevidenceRecord] = []

    for key, ctype in _CONTEXT_TYPE_MAP.items():
        entries = context.get(key)
        if not entries:
            continue
        if isinstance(entries, str):
            entries = [entries]
        for entry in entries:
            if isinstance(entry, dict):
                target = entry.get("transform_id") or entry.get("target") or str(entry)
                detail = entry.get("detail", "")
            else:
                target = str(entry)
                detail = ""
            if ctype == CounterevidenceType.COMPETING_TRANSFORM:
                evidence_ids = _evidence_ids_for_transform(evidence_records, target)
            else:
                evidence_ids = _all_ids(evidence_records)
            # P4-R1-G: never fabricate unresolved:* ids; without source
            # evidence the record is skipped (absence is not counterevidence).
            if not evidence_ids:
                continue
            source_identity = _source_identity(evidence_records, evidence_ids)
            if source_identity == "unknown":
                continue  # no verifiable source -> no record
            record_id = stable_id("ce", {
                "type": ctype.value, "target": target,
                "evidence_ids": sorted(evidence_ids),
                "source_identity": source_identity,
            })
            records.append(CounterevidenceRecord(
                record_id=record_id,
                evidence_ids=evidence_ids,
                source_identity=source_identity,
                scope="strict_lane",
                counter_type=ctype,
                policy_version=P4_POLICY_VERSION,
                detail=detail,
            ))

    # Dedup identical records.
    seen: set[str] = set()
    deduped: list[CounterevidenceRecord] = []
    for r in records:
        if r.record_id in seen:
            continue
        seen.add(r.record_id)
        deduped.append(r)

    has_conflict = any(r.counter_type in CONFLICT_TYPES for r in deduped)

    return CounterevidenceCollection(
        candidate_id=cand_id,
        records=deduped,
        has_conflict=has_conflict,
        policy_version=P4_POLICY_VERSION,
    )


def _all_ids(evidence_records) -> list[str]:
    out: list[str] = []
    for rec in evidence_records:
        rid = rec.reaction_id if not isinstance(rec, dict) else rec.get("reaction_id", "")
        if rid and rid not in out:
            out.append(rid)
    return out
