"""P7 T0② P3→P4 bridge adapter pin tests (RED first).

The bridge (``reaction_agent/adapters/p3_p4_bridge.py``) derives the three P4
pipeline inputs from a P3 ``KernelResult`` by BACK-SOURCING donor evidence
through the P3 loaders. These pins assert the CC-Option-A acceptance criteria:

- evidence_records are loaded (not synthesized) from the candidate's evidence
  paths via the P3 train-view loaders;
- each of the 7 structural_context ordinals is deterministically derived from
  a named real field, with traceable derivation provenance;
- feature_evidence_ids only reference evidence IDs that exist in the run;
- missing data (unresolvable evidence path / absent source field) raises a
  typed ``BridgeBackSourceError`` — never a silent default.

RED until ``p3_p4_bridge.py`` is implemented (ImportError); GREEN after.
"""
from __future__ import annotations

import pytest

from reaction_agent.p3.kernel import run_kernel
from reaction_agent.p3.schemas import KernelResult


@pytest.fixture(scope="module")
def fixture_kernel() -> KernelResult:
    """A real P3 fixture KernelResult (octanol oxidation, 2 candidates)."""
    return run_kernel(
        input_smiles="CCCCCCCCO",
        case_id="c_pin",
        fold_id="fold_fx_p3",
        mode="fixture",
        seed=0,
    )


def _candidate_evidence_reaction_ids(k: KernelResult) -> set[str]:
    out: set[str] = set()
    for c in k.candidates:
        for p in c.candidate_evidence_paths:
            out.add(p.reaction_id)
    return out


class TestBridgeBackSourceEvidence:
    def test_evidence_records_loaded_not_synthesized(self, fixture_kernel, tmp_path):
        from reaction_agent.adapters.p3_p4_bridge import build_p4_inputs_from_kernel

        inputs = build_p4_inputs_from_kernel(
            fixture_kernel, current_run_path=str(tmp_path / "current_run.json")
        )
        valid_rids = _candidate_evidence_reaction_ids(fixture_kernel)
        assert inputs.evidence_records, "bridge must surface >=1 evidence record"
        for rec in inputs.evidence_records:
            assert rec.reaction_id in valid_rids, (
                f"evidence {rec.reaction_id!r} not in candidate evidence paths; "
                f"possible synthesis"
            )
            # Real loaded evidence carries participants + mapping_report
            # (not a hand-built shell).
            assert rec.participants
            assert rec.mapping_report is not None

    def test_unknown_evidence_path_raises_typed_error(self, fixture_kernel, tmp_path):
        """A candidate whose evidence-path reaction is absent from the train
        view must raise BridgeBackSourceError, not synthesize a record."""
        from reaction_agent.adapters.p3_p4_bridge import (
            BridgeBackSourceError,
            build_p4_inputs_from_kernel,
        )
        from reaction_agent.p3.fixtures import (
            FixtureReaction,
            TrainView,
            build_train_view,
            load_fixture_reactions,
        )

        # An empty train view: every candidate evidence path is unresolvable.
        empty_tv = build_train_view(load_fixture_reactions())
        # Sabotage: clear donors so find_donor_ref raises KeyError for every path.
        object.__setattr__(empty_tv, "donors", [])
        with pytest.raises(BridgeBackSourceError):
            build_p4_inputs_from_kernel(
                fixture_kernel,
                train_view=empty_tv,
                current_run_path=str(tmp_path / "current_run.json"),
            )


class TestBridgeStructuralContexts:
    EXPECTED_FEATURES = {
        "donor_similarity",
        "transform_support",
        "site_compatibility",
        "mapping_lineage_quality",
        "source_quality",
        "ledger_completeness",
        "retrieval_stability",
    }

    def test_seven_ordinals_per_candidate_in_range(self, fixture_kernel, tmp_path):
        from reaction_agent.adapters.p3_p4_bridge import build_p4_inputs_from_kernel

        inputs = build_p4_inputs_from_kernel(
            fixture_kernel, current_run_path=str(tmp_path / "current_run.json")
        )
        assert inputs.structural_contexts
        for cand_id, ctx in inputs.structural_contexts.items():
            assert set(ctx.keys()) == self.EXPECTED_FEATURES, (
                f"{cand_id}: missing/extra features {set(ctx) ^ self.EXPECTED_FEATURES}"
            )
            for feature, ordinal in ctx.items():
                assert isinstance(ordinal, int), f"{feature} not int"
                assert 0 <= ordinal <= 3, f"{feature}={ordinal} out of 0..3"

    def test_ordinal_derivation_traceable(self, fixture_kernel, tmp_path):
        """Each ordinal must expose its derivation source field + value (audit)."""
        from reaction_agent.adapters.p3_p4_bridge import build_p4_inputs_from_kernel

        inputs = build_p4_inputs_from_kernel(
            fixture_kernel, current_run_path=str(tmp_path / "current_run.json")
        )
        assert inputs.derivations
        for cand_id, derivs in inputs.derivations.items():
            assert set(d.feature for d in derivs) == self.EXPECTED_FEATURES
            for d in derivs:
                assert d.source_field, f"{cand_id}/{d.feature}: no source_field"
                assert d.source_value != "", f"{cand_id}/{d.feature}: empty source_value"


class TestBridgeFeatureEvidenceIds:
    def test_bindings_only_reference_existing_evidence(self, fixture_kernel, tmp_path):
        from reaction_agent.adapters.p3_p4_bridge import build_p4_inputs_from_kernel

        inputs = build_p4_inputs_from_kernel(
            fixture_kernel, current_run_path=str(tmp_path / "current_run.json")
        )
        valid_rids = {rec.reaction_id for rec in inputs.evidence_records}
        for cand_id, feats in inputs.feature_evidence_ids.items():
            for feature, eids in feats.items():
                for eid in eids:
                    assert eid in valid_rids, (
                        f"{cand_id}/{feature}: evidence id {eid!r} not in run"
                    )


class TestBridgeAuthority:
    def test_authority_resolved_from_consumer(self, fixture_kernel, tmp_path):
        """The P3AuthorityHandle comes from the verified P3 consumer
        (P4-R1-B), not caller-constructed."""
        from reaction_agent.adapters.p3_p4_bridge import build_p4_inputs_from_kernel
        from reaction_agent.schemas.p4.authority import AuthoritySource

        inputs = build_p4_inputs_from_kernel(
            fixture_kernel, current_run_path=str(tmp_path / "current_run.json")
        )
        assert inputs.authority.source == AuthoritySource.p3_current_run
        assert inputs.authority.capability_available is True


class TestBridgeCandidateConversion:
    def test_p3_candidates_converted_to_p4(self, fixture_kernel, tmp_path):
        from reaction_agent.adapters.p3_p4_bridge import build_p4_inputs_from_kernel
        from reaction_agent.schemas.candidate import Candidate

        inputs = build_p4_inputs_from_kernel(
            fixture_kernel, current_run_path=str(tmp_path / "current_run.json")
        )
        assert len(inputs.candidates) == len(fixture_kernel.candidates)
        for c in inputs.candidates:
            assert isinstance(c, Candidate)
            assert c.candidate_id
            assert c.canonical_product
