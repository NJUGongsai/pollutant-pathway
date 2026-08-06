"""P4-T1 independent evidence identity + dedup (RED first, then GREEN)."""
from __future__ import annotations

import pytest

from tests.fixtures.p4.p4_contract_fixture import (
    build_evidence_records,
    POLICY_VERSION,
)
from reaction_agent.schemas.p4.evidence import (
    DedupDimension,
    EvidenceIdentityResolution,
)
from reaction_agent.inference.evidence_identity import resolve_evidence_identity


def test_mirror_publication_mapper_duplicates_do_not_add_support():
    """P4-T1: mirror rows, same-publication rows, and mapper duplicates
    must NOT be counted as multiple independent support."""
    records = build_evidence_records()
    res = resolve_evidence_identity(records, policy_version=POLICY_VERSION)

    assert isinstance(res, EvidenceIdentityResolution)
    assert res.total_rows == 5

    # ev_d1, ev_d1_mirror, ev_d4 all represent the same observation.
    ids = [i.evidence_id for i in res.identities]
    gid_d1 = next(i.independent_group_id for i in res.identities if i.evidence_id == "ev_d1")
    gid_mirror = next(i.independent_group_id for i in res.identities if i.evidence_id == "ev_d1_mirror")
    gid_d4 = next(i.independent_group_id for i in res.identities if i.evidence_id == "ev_d4")
    assert gid_d1 == gid_mirror == gid_d4, "mirror/publication/mapper rows must share one group"

    # ev_d2 (different source, same transform) is independent.
    gid_d2 = next(i.independent_group_id for i in res.identities if i.evidence_id == "ev_d2")
    assert gid_d2 != gid_d1, "same transform from different source must be independent"

    # ev_d3 (different transform) is independent.
    gid_d3 = next(i.independent_group_id for i in res.identities if i.evidence_id == "ev_d3")
    assert gid_d3 != gid_d1 and gid_d3 != gid_d2

    # independent_count: 3 groups from 5 rows.
    assert res.independent_count == 3


def test_support_count_uses_independent_groups_not_rows():
    """P4-T1: duplicates must not inflate the independent support count."""
    records = build_evidence_records()
    res = resolve_evidence_identity(records, policy_version=POLICY_VERSION)
    support_ids = ["ev_d1", "ev_d1_mirror", "ev_d4", "ev_d2"]
    group_ids = res.group_ids_for(support_ids)
    assert len(group_ids) == 2, "4 rows covering 2 independent groups"
    assert res.independent_count == 3


def test_provenance_preserved_on_merge():
    """P4-T1: merging duplicates must preserve provenance (duplicate_of)."""
    records = build_evidence_records()
    res = resolve_evidence_identity(records, policy_version=POLICY_VERSION)
    d1 = next(i for i in res.identities if i.evidence_id == "ev_d1")
    # ev_d1's group includes ev_d1_mirror and ev_d4.
    group_members = {
        g.group_id: set(g.member_evidence_ids)
        for g in res.groups
    }[d1.independent_group_id]
    assert {"ev_d1", "ev_d1_mirror", "ev_d4"} <= group_members
    # The resolution records the dedup dimensions that tied them together.
    assert d1.dedup_dimensions, "dedup dimensions must be recorded"


def test_dedup_dimension_recorded_for_mirror():
    """P4-T1: mirror/publication/mapper duplicates carry typed dedup reasons."""
    records = build_evidence_records()
    res = resolve_evidence_identity(records, policy_version=POLICY_VERSION)
    dims = set()
    for i in res.identities:
        dims.update(d.value for d in i.dedup_dimensions)
    assert DedupDimension.database_mirror.value in dims or \
        DedupDimension.same_publication.value in dims or \
        DedupDimension.mapper_duplicate.value in dims


def test_deterministic_recomputation():
    """P4-T1: same evidence + same policy => same resolution hash."""
    records = build_evidence_records()
    res1 = resolve_evidence_identity(records, policy_version=POLICY_VERSION)
    res2 = resolve_evidence_identity(records, policy_version=POLICY_VERSION)
    assert res1.resolution_hash == res2.resolution_hash
    assert res1.groups == res2.groups

    # Changing input changes the hash.
    res3 = resolve_evidence_identity(records[:-1], policy_version=POLICY_VERSION)
    assert res3.resolution_hash != res1.resolution_hash


def test_policy_version_recorded():
    res = resolve_evidence_identity(build_evidence_records(), policy_version=POLICY_VERSION)
    assert res.policy_version == POLICY_VERSION


def test_empty_evidence_has_zero_independent():
    res = resolve_evidence_identity([], policy_version=POLICY_VERSION)
    assert res.independent_count == 0
    assert res.total_rows == 0
    assert res.identities == []
    assert res.groups == []
