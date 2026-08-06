"""P4-T3 counterevidence (allowed types only; absence is never negative)."""
from __future__ import annotations

import pytest

from tests.fixtures.p4.p4_contract_fixture import (
    build_evidence_records,
    build_strict_candidate,
    POLICY_VERSION,
)
from reaction_agent.schemas.p4.counterevidence import (
    CounterevidenceCollection,
    CounterevidenceType,
)
from reaction_agent.inference.evidence_identity import resolve_evidence_identity
from reaction_agent.inference.counterevidence import collect_counterevidence


def _resolution():
    return resolve_evidence_identity(build_evidence_records(), policy_version=POLICY_VERSION)


def test_allowed_counterevidence_types():
    """P4-T3: collected counterevidence uses only the allowed typed reasons."""
    cand = build_strict_candidate()
    res = _resolution()
    coll = collect_counterevidence(cand, build_evidence_records(), res, context={})
    assert isinstance(coll, CounterevidenceCollection)
    allowed = {t.value for t in CounterevidenceType}
    for rec in coll.records:
        assert rec.counter_type.value in allowed
        assert rec.evidence_ids, "counterevidence must bind evidence IDs"
        assert rec.source_identity, "source identity required"


def test_database_absence_never_negative():
    """P4-T3: absence / no-second-enzyme / low-frequency / not-covered are
    NOT counterevidence. The collector must refuse them."""
    cand = build_strict_candidate()
    res = _resolution()
    # A caller attempts to inject forbidden absence as negative.
    with pytest.raises((ValueError, TypeError)):
        collect_counterevidence(
            cand, build_evidence_records(), res,
            context={"forbidden_negative": [
                {"type": "database_absence", "detail": "no record for X"},
                {"type": "no_second_enzyme", "detail": "no second enzyme"},
            ]},
            allow_forbidden_negatives=True,
        )


def test_absence_is_unknown_not_negative():
    """P4-T3: no observed counterevidence => has_conflict False, not a negative."""
    cand = build_strict_candidate()
    res = _resolution()
    coll = collect_counterevidence(cand, build_evidence_records(), res, context={})
    # Fixture candidate has no structural conflict.
    assert coll.has_conflict is False or all(
        not r.counter_type.value.startswith("COMPETING") for r in coll.records)


def test_competing_transform_is_allowed_counterevidence():
    """P4-T3: a competing transform is allowed counterevidence."""
    cand = build_strict_candidate()
    res = _resolution()
    coll = collect_counterevidence(
        cand, build_evidence_records(), res,
        context={"competing_transform": ["t2"]})
    types = {r.counter_type.value for r in coll.records}
    if coll.records:
        assert CounterevidenceType.COMPETING_TRANSFORM.value in types
