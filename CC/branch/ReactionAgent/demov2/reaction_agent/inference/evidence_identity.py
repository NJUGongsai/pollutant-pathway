"""P4-T1 independent evidence identity + dedup (final_design §4.9, §7.1).

Two evidence rows represent the SAME independent evidence if ANY dedup
dimension ties them together:
- database mirror      : same (source_name, source_version, source_record_id)
- same publication     : same publication AND same normalized reaction
- same normalized rxn  : same source lineage AND same normalized reaction
- mapper duplicate     : same source lineage AND same raw reaction
- same donor transform : same source lineage AND same donor-transform key

Mirror rows, same-publication rows, mapper duplicates and same donor-transform
evidence from the same source lineage are merged into ONE independent group.
The same transform observed from a DIFFERENT source lineage is INDEPENDENT.
Merging never loses provenance (``duplicate_of`` preserves every merged id).

All identity strings are content-addressed (canonical_hash) and recomputable.
"""
from __future__ import annotations

from reaction_agent.hashing import canonical_hash
from reaction_agent.schemas.common import NonEmptyStr
from reaction_agent.schemas.p4.evidence import (
    DedupDimension,
    EvidenceIdentity,
    IndependentGroup,
    EvidenceIdentityResolution,
)


class EvidenceIdentityValidationError(ValueError):
    """P4-R1-G: an evidence record is missing required schema fields or uses
    an id that cannot be resolved (orphan) — fail closed, never partial dedup."""


def _field(record, name: str, default=""):
    """Read a field from a schema object or a dict."""
    if isinstance(record, dict):
        return record.get(name, default)
    return getattr(record, name, default)


def _norm_publication(pub: str) -> str:
    return (pub or "").strip().lower()


def _donor_transform_key(record) -> str:
    lineages = sorted(_field(record, "resolved_transformed_lineages", []) or [])
    transforms = sorted(_field(record, "transformation_hypotheses", []) or [])
    return canonical_hash({"lineages": lineages, "transforms": transforms})


def _row_components(record) -> dict:
    """Extract deterministic identity components from one evidence row."""
    pub = _norm_publication(_field(record, "source_uri_or_citation"))
    source_name = _field(record, "source_name")
    source_version = _field(record, "source_version", "unknown")
    source_record_id = _field(record, "source_record_id")
    raw = _field(record, "raw_reaction")
    norm = _field(record, "normalized_reaction")
    lineages = sorted(_field(record, "resolved_transformed_lineages", []) or [])
    transforms = sorted(_field(record, "transformation_hypotheses", []) or [])
    return {
        "evidence_id": _field(record, "reaction_id"),
        "db_mirror_key": (source_name, source_version, source_record_id),
        "source_lineage_key": (source_name, source_version),
        "publication_key": pub,
        "reaction_key": norm,
        "raw_key": raw,
        "donor_transform_key": canonical_hash(
            {"lineages": lineages, "transforms": transforms}),
        "has_donor_transform": bool(lineages or transforms),
    }


def _same_dimension(a: dict, b: dict) -> DedupDimension | None:
    """Return the first dedup dimension tying two rows together, or None."""
    # D1 database mirror
    if a["db_mirror_key"] == b["db_mirror_key"] and a["db_mirror_key"][0]:
        return DedupDimension.database_mirror
    # D2 same publication + same reaction
    if (a["publication_key"] and a["publication_key"] == b["publication_key"]
            and a["reaction_key"] == b["reaction_key"]):
        return DedupDimension.same_publication
    # D3 same source lineage + same normalized reaction
    if (a["source_lineage_key"] == b["source_lineage_key"]
            and a["reaction_key"] == b["reaction_key"] and a["reaction_key"]):
        return DedupDimension.same_normalized_reaction
    # D4 same source lineage + same raw reaction (mapper duplicate)
    if (a["source_lineage_key"] == b["source_lineage_key"]
            and a["raw_key"] == b["raw_key"] and a["raw_key"]):
        return DedupDimension.mapper_duplicate
    # D5 same source lineage + same donor-transform evidence (only when a
    # non-trivial donor-transform observation exists — empty data must not
    # merge two distinct reactions).
    if (a["has_donor_transform"] and b["has_donor_transform"]
            and a["source_lineage_key"] == b["source_lineage_key"]
            and a["donor_transform_key"] == b["donor_transform_key"]):
        return DedupDimension.same_donor_transform
    return None


def _union_find(n: int):
    parent = list(range(n))
    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx
    return find, union


def _row_canonical_identity(comp: dict) -> str:
    return canonical_hash({
        "publication": comp["publication_key"],
        "source_lineage": list(comp["source_lineage_key"]),
        "normalized_reaction": comp["reaction_key"],
        "donor_transform": comp["donor_transform_key"],
        "raw_reaction": comp["raw_key"],
    })


def _validate_record(record, idx: int) -> None:
    """P4-R1-G: every evidence record must carry a resolvable identity and a
    snapshot binding (fail closed on orphan/missing fields)."""
    rid = _field(record, "reaction_id", "")
    if not rid:
        raise EvidenceIdentityValidationError(
            f"evidence[{idx}] missing reaction_id")
    if not _field(record, "source_name", ""):
        raise EvidenceIdentityValidationError(
            f"evidence[{idx}] missing source_name")
    if not _field(record, "snapshot_id", ""):
        raise EvidenceIdentityValidationError(
            f"evidence[{idx}] missing snapshot_id (namespace binding)")


def resolve_evidence_identity(
    evidence_records: list,
    policy_version: str,
) -> EvidenceIdentityResolution:
    """Resolve evidence identity + dedup over ``evidence_records``.

    Returns an ``EvidenceIdentityResolution`` with per-row identities and
    independent groups. ``independent_count`` is the number of groups.
    P4-R1-G: records are schema-validated first (orphan/missing fields are
    rejected) and the dedup/group ids are order-invariant.
    """
    for idx, rec in enumerate(evidence_records):
        _validate_record(rec, idx)
    comps = [_row_components(r) for r in evidence_records]
    n = len(comps)

    find, union = _union_find(n)
    # Record the dedup dimension that first ties each pair.
    pair_dim: dict[tuple[int, int], DedupDimension] = {}
    for i in range(n):
        for j in range(i + 1, n):
            dim = _same_dimension(comps[i], comps[j])
            if dim is not None:
                union(i, j)
                pair_dim[(i, j)] = dim

    # Assemble groups (roots -> member indices).
    root_members: dict[int, list[int]] = {}
    for idx in range(n):
        root_members.setdefault(find(idx), []).append(idx)

    groups: list[IndependentGroup] = []
    for root in sorted(root_members):
        members = sorted(root_members[root])
        # Order-invariant member ids (P4-R1-G input-order invariance).
        member_ids = sorted(comps[m]["evidence_id"] for m in members)
        dims_seen: list[DedupDimension] = []
        for i in members:
            for j in members:
                if i == j:
                    continue
                d = pair_dim.get((min(i, j), max(i, j)))
                if d is not None and d not in dims_seen:
                    dims_seen.append(d)
        sorted_member_ids = sorted(member_ids)
        group_id = f"evg_{canonical_hash({'members': sorted_member_ids})[:12]}"
        groups.append(IndependentGroup(
            group_id=group_id,
            canonical_identity=canonical_hash({"members": sorted_member_ids}),
            member_evidence_ids=member_ids,
            dedup_dimensions=sorted(dims_seen, key=lambda d: d.value),
            is_independent=True,
        ))

    # Per-row identities.
    member_by_root = {root: g for root, g in zip(sorted(root_members), groups)}
    identities: list[EvidenceIdentity] = []
    for idx in range(n):
        root = find(idx)
        group = member_by_root[root]
        siblings = [m for m in group.member_evidence_ids if m != comps[idx]["evidence_id"]]
        row_dims: list[DedupDimension] = []
        for j in range(n):
            if j == idx:
                continue
            d = pair_dim.get((min(idx, j), max(idx, j)))
            if d is not None and d not in row_dims:
                row_dims.append(d)
        identities.append(EvidenceIdentity(
            evidence_id=comps[idx]["evidence_id"],
            canonical_identity=_row_canonical_identity(comps[idx]),
            independent_group_id=group.group_id,
            dedup_dimensions=sorted(row_dims, key=lambda d: d.value),
            duplicate_of=siblings,
            source_lineage={
                "source_name": comps[idx]["source_lineage_key"][0],
                "source_version": comps[idx]["source_lineage_key"][1],
            },
            publication=comps[idx]["publication_key"],
            normalized_reaction=comps[idx]["reaction_key"],
            donor_transform={
                "lineages": _lineages_of(evidence_records[idx]),
                "transforms": sorted(
                    _field(evidence_records[idx], "transformation_hypotheses", []) or []),
            },
        ))

    resolution_hash = canonical_hash({
        "policy_version": policy_version,
        "groups": [
            {"group_id": g.group_id, "members": g.member_evidence_ids,
             "canonical_identity": g.canonical_identity,
             "dedup_dimensions": [d.value for d in g.dedup_dimensions]}
            for g in sorted(groups, key=lambda g: g.group_id)
        ],
    })

    return EvidenceIdentityResolution(
        identities=identities,
        groups=groups,
        independent_count=len(groups),
        total_rows=n,
        policy_version=policy_version,
        resolution_hash=resolution_hash,
    )


def _lineages_of(record) -> list[str]:
    return sorted(_field(record, "resolved_transformed_lineages", []) or [])
