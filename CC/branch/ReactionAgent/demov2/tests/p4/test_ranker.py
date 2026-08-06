"""P4-T4 strict-only deterministic ranker (ordinal, not probability)."""
from __future__ import annotations

import pytest

from tests.fixtures.p4.p4_contract_fixture import (
    build_evidence_records,
    build_strict_candidate,
    build_structural_context,
    POLICY_VERSION,
)
from reaction_agent.schemas.common import Lane
from reaction_agent.schemas.candidate import Candidate
from reaction_agent.schemas.p4.ranking import RankingResult, RankedStrictCandidate
from reaction_agent.inference.features import build_feature_vector
from reaction_agent.inference.ranker import rank_strict_candidates
from reaction_agent.inference.support import aggregate_support
from reaction_agent.inference.evidence_identity import resolve_evidence_identity


def _cand2():
    """Second strict candidate with weaker structural support."""
    return Candidate(
        candidate_id="cand_ox_002",
        canonical_product="CCC=O",
        lane=Lane.strict,
        origin="agent_selected_from_evidence_space",
        transformation_ids=["t1"],
        site_ids=["site_c2"],
        support_lineage_ids=["lin_d2"],
        validation={"valid_molecule": True, "no_relaxation": True},
        provenance=["fixture:candidate"],
    )


def test_strict_lane_only():
    """P4-T4: generalized / agent_proposed candidates must NOT enter strict ranking."""
    gen = Candidate(candidate_id="cand_gen_1", canonical_product="CC=O",
                    lane=Lane.generalized, origin="agent_proposed",
                    provenance=["fixture"])
    agent = Candidate(candidate_id="cand_ag_1", canonical_product="CC=O",
                      lane=Lane.agent_proposed, origin="agent_proposed",
                      provenance=["fixture"])
    strict = build_strict_candidate()
    with pytest.raises(ValueError):
        rank_strict_candidates([gen, agent, strict],
                               feature_vectors={},
                               policy_version=POLICY_VERSION)


def test_rank_is_ordinal_and_deterministic():
    """P4-T4: deterministic ranking; rank is ordinal selection, not probability."""
    c1 = build_strict_candidate()
    c2 = _cand2()
    ctx1 = build_structural_context()
    ctx2 = dict(ctx1, donor_similarity=1, transform_support=1,
                site_compatibility=1, mapping_lineage_quality=1,
                ledger_completeness=1, evidence_independence=0,
                retrieval_stability=1)
    recs = build_evidence_records()
    res = resolve_evidence_identity(recs, policy_version=POLICY_VERSION)
    fv = {
        c1.candidate_id: build_feature_vector(c1, res, ctx1),
        c2.candidate_id: build_feature_vector(c2, res, ctx2),
    }
    r1 = rank_strict_candidates([c1, c2], feature_vectors=fv,
                                policy_version=POLICY_VERSION)
    r2 = rank_strict_candidates([c1, c2], feature_vectors=fv,
                                policy_version=POLICY_VERSION)
    assert isinstance(r1, RankingResult)
    assert len(r1.candidates) == 2
    # c1 should outrank c2 (stronger support).
    assert r1.candidates[0].candidate_id == "cand_ox_001"
    assert r1.candidates[0].rank == 1
    assert r1.candidates[1].rank == 2
    # Deterministic.
    assert r1.ranking_hash == r2.ranking_hash
    assert [c.candidate_id for c in r1.candidates] == [c.candidate_id for c in r2.candidates]
    # Ordinal: no probability semantics allowed in the output schema.
    for c in r1.candidates:
        assert isinstance(c, RankedStrictCandidate)
        assert c.lane == Lane.strict
        assert c.tie_break_key


def test_tie_break_is_deterministic():
    """P4-T4: equal scores break ties deterministically (by tie_break_key)."""
    c1 = build_strict_candidate()
    c2 = _cand2()
    # Force equal scores.
    ctx = build_structural_context()
    recs = build_evidence_records()
    res = resolve_evidence_identity(recs, policy_version=POLICY_VERSION)
    fv = {
        c1.candidate_id: build_feature_vector(c1, res, ctx),
        c2.candidate_id: build_feature_vector(c2, res, ctx),
    }
    r = rank_strict_candidates([c1, c2], feature_vectors=fv,
                               policy_version=POLICY_VERSION)
    keys = [c.tie_break_key for c in r.candidates]
    assert keys == sorted(keys), "tie-break must be deterministic ascending"
    # Recompute is identical.
    r2 = rank_strict_candidates([c1, c2], feature_vectors=fv,
                                policy_version=POLICY_VERSION)
    assert [c.candidate_id for c in r.candidates] == [c.candidate_id for c in r2.candidates]


def test_ranking_score_is_weighted_and_not_probability():
    """P4-T4: ranking_score is a weighted ordinal aggregate in [0,1]."""
    c1 = build_strict_candidate()
    recs = build_evidence_records()
    res = resolve_evidence_identity(recs, policy_version=POLICY_VERSION)
    fv = {c1.candidate_id: build_feature_vector(c1, res, build_structural_context())}
    r = rank_strict_candidates([c1], feature_vectors=fv, policy_version=POLICY_VERSION)
    assert 0.0 <= r.candidates[0].ranking_score <= 1.0
    assert r.ranker_version
    assert r.policy_version == POLICY_VERSION
