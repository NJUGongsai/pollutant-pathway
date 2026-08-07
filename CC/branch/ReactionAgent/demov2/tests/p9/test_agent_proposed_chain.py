"""P9-T1 RED tests — AgentProposedHypothesis validation chain (final_plan §12.1,
final_design §19.2, ADR-0002).

The agent-proposed lane is a physically isolated, exploratory, NON-production
lane. An AgentProposedHypothesis must pass the full eight-step validation chain:

    support validation
    -> registered vocabulary
    -> compiler
    -> site validation
    -> graph edit
    -> molecule validation
    -> dual-ledger validation
    -> grounding validation

On pass it receives an ``agent_proposed`` lane candidate (exploratory, NOT a
strict ``Candidate`` / NOT production rank). The independent report carries six
metric groups: new valid/correct/incorrect, reject reasons, incremental recall,
risk, cost, reproducibility.

ADR-0002 regressions: lane mixing rejected, unknown IDs rejected, free-text
relaxation rejected (relaxation IDs must be registered).
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from reaction_agent.schemas.common import Lane
from reaction_agent.schemas.candidate import Candidate
from reaction_agent.schemas.errors import UnknownReferenceError
from reaction_agent.schemas.hypothesis import (
    AgentProposedHypothesis,
    AtomTarget,
    BondTarget,
    HypothesisReferenceRegistry,
)
from reaction_agent.schemas.ledger import (
    CandidateAnalogyLedger,
    LedgerBalanceStatus,
    LedgerReferenceRegistry,
    SourceReactionLedger,
)

from reaction_agent.p9.agent_proposed import (
    DEFAULT_AGENT_PROPOSED_CHAIN_POLICY,
    CHAIN_STEPS,
    AgentProposedCandidate,
    AgentProposedChainPolicy,
    AgentProposedCostReport,
    AgentProposedReproducibility,
    AgentProposedReport,
    AgentProposedRejectReasonCode,
    AgentProposedValidationError,
    AgentProposedValidation,
    AgentProposedValidationContext,
    CompiledGraphEdit,
    EditedMolecule,
    LaneScopedCandidateLedger,
    QueryMoleculeContext,
    apply_graph_edit,
    build_agent_proposed_candidate,
    build_agent_proposed_report,
    compile_typed_targets,
    revalidate_agent_proposed_candidate,
    validate_agent_proposed_hypothesis,
    validate_dual_ledger,
    validate_grounding,
    validate_molecule,
)


# ---------------------------------------------------------------------------
# Fixtures — a valid agent-proposed hypothesis + a fully grounded context
# ---------------------------------------------------------------------------


def _registry() -> HypothesisReferenceRegistry:
    return HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn_a", "rxn_b"}),
        lineage_ids=frozenset({"lin_a1", "lin_a2", "lin_b1"}),
        transformation_ids=frozenset({"tx_a"}),
        site_ids=frozenset({"site_a"}),
        transformation_family_ids=frozenset({"fam_oh_to_c", "fam_cc_bond"}),
        relaxation_policy_ids=frozenset({"relax_pol_1"}),
        relaxation_ids=frozenset({"relax_donor_site", "relax_precond"}),
        source_ledger_ids=frozenset({"src_ledger_a"}),
        lineage_to_reaction_id={
            "lin_a1": "rxn_a",
            "lin_a2": "rxn_a",
            "lin_b1": "rxn_b",
        },
        transformation_to_lineage_ids={"tx_a": ["lin_a1", "lin_a2"]},
        site_to_transformation_id={"site_a": "tx_a"},
        relaxation_policy_to_allowed_ids={
            "relax_pol_1": ["relax_donor_site", "relax_precond"]
        },
        source_ledger_to_reaction_id={"src_ledger_a": "rxn_a"},
    )


def _query_molecule() -> QueryMoleculeContext:
    # ethanol with atom maps: [CH3:1][CH2:2][OH:3] -> atom maps {1,2,3},
    # bonds {(1,2),(2,3)}
    return QueryMoleculeContext(
        smiles="[CH3:1][CH2:2][OH:3]",
        query_atom_ids=frozenset({1, 2, 3}),
        query_bond_pairs=frozenset({(1, 2), (2, 3)}),
    )


def _valid_hypothesis() -> AgentProposedHypothesis:
    return AgentProposedHypothesis(
        hypothesis_id="h_ap_1",
        hypothesis_origin="agent_proposed",
        support_reaction_ids=["rxn_a"],
        support_lineage_ids=["lin_a1"],
        transformation_family_id="fam_cc_bond",
        typed_target_atom_or_bond_set=[BondTarget(begin_atom_id=1, end_atom_id=2)],
        relaxation_policy_id="relax_pol_1",
        allowed_relaxation_ids=["relax_donor_site"],
        rationale_summary="propose C-C bond cleavage at the mapped site",
        policy_version="1.0.0",
    )


def _valid_context(
    *,
    with_query: bool = True,
    with_grounding: bool = True,
) -> AgentProposedValidationContext:
    return AgentProposedValidationContext(
        registry=_registry(),
        chain_policy=DEFAULT_AGENT_PROPOSED_CHAIN_POLICY,
        query_molecule=_query_molecule() if with_query else None,
        source_ledgers={
            "src_ledger_a": SourceReactionLedger(
                ledger_id="src_ledger_a",
                reaction_evidence_id="rxn_a",
                balance_status=LedgerBalanceStatus.balanced,
            )
        },
        agent_candidate_ledgers={},
        strict_candidate_ids=frozenset({"strict_cand_1"}),
        family_grounding=(
            {"fam_cc_bond": ["rxn_a"], "fam_oh_to_c": ["rxn_b"]}
            if with_grounding
            else {}
        ),
    )


# ---------------------------------------------------------------------------
# Step 0: frozen validation-chain policy
# ---------------------------------------------------------------------------


def test_chain_policy_default_has_eight_steps_and_semver():
    pol = DEFAULT_AGENT_PROPOSED_CHAIN_POLICY
    assert len(CHAIN_STEPS) == 8
    assert pol.chain_steps == CHAIN_STEPS
    assert pol.version == "1.0.0"
    assert pol.content_hash  # non-empty


def test_chain_policy_content_hash_is_verified():
    pol = DEFAULT_AGENT_PROPOSED_CHAIN_POLICY
    # reconstructing with the same fields must reproduce the same content hash
    rebuilt = AgentProposedChainPolicy.create(version="1.0.0")
    assert rebuilt.content_hash == pol.content_hash
    # tampering with the content_hash must raise
    with pytest.raises(ValidationError):
        AgentProposedChainPolicy(
            policy_id=pol.policy_id,
            version=pol.version,
            chain_steps=pol.chain_steps,
            content_hash="tampered",
        )


# ---------------------------------------------------------------------------
# Step 3: compiler — typed targets -> deterministic CompiledGraphEdit
# ---------------------------------------------------------------------------


def test_compile_targets_deterministic_and_order_invariant():
    a = compile_typed_targets(
        [BondTarget(begin_atom_id=1, end_atom_id=2), AtomTarget(atom_id=3)]
    )
    b = compile_typed_targets(
        [AtomTarget(atom_id=3), BondTarget(begin_atom_id=1, end_atom_id=2)]
    )
    assert a.compile_hash == b.compile_hash
    assert a.target_count == 2
    assert a.atom_target_ids == [3]
    assert a.bond_target_pairs == [(1, 2)]


def test_compile_targets_rejects_empty_set():
    with pytest.raises(AgentProposedValidationError):
        compile_typed_targets([])


# ---------------------------------------------------------------------------
# Step 1: support validation (registry existence + relation integrity)
# ---------------------------------------------------------------------------


def test_step1_rejects_unknown_support_reaction_id():
    h = _valid_hypothesis().model_copy(update={"support_reaction_ids": ["rxn_unknown"]})
    with pytest.raises(UnknownReferenceError):
        validate_agent_proposed_hypothesis(h, _valid_context())


def test_step1_rejects_unknown_support_lineage_id():
    h = _valid_hypothesis().model_copy(update={"support_lineage_ids": ["lin_unknown"]})
    with pytest.raises(UnknownReferenceError):
        validate_agent_proposed_hypothesis(h, _valid_context())


# ---------------------------------------------------------------------------
# Step 2: registered vocabulary (family + relaxation IDs — ADR-0002)
# ---------------------------------------------------------------------------


def test_step2_rejects_unknown_transformation_family_id():
    h = _valid_hypothesis().model_copy(
        update={"transformation_family_id": "fam_unknown"}
    )
    with pytest.raises(UnknownReferenceError):
        validate_agent_proposed_hypothesis(h, _valid_context())


def test_step2_rejects_unregistered_relaxation_id():
    # free-text relaxation: an ID not in the registered vocabulary -> ADR-0002
    h = _valid_hypothesis().model_copy(
        update={"allowed_relaxation_ids": ["relax_freestyle_invented"]}
    )
    with pytest.raises(UnknownReferenceError):
        validate_agent_proposed_hypothesis(h, _valid_context())


# ---------------------------------------------------------------------------
# Step 4: site validation — typed targets belong to the current query
# ---------------------------------------------------------------------------


def test_step4_rejects_atom_target_not_in_query():
    h = _valid_hypothesis().model_copy(
        update={
            "typed_target_atom_or_bond_set": [AtomTarget(atom_id=999)],
        }
    )
    with pytest.raises(UnknownReferenceError):
        validate_agent_proposed_hypothesis(h, _valid_context())


def test_step4_rejects_bond_target_not_in_query():
    h = _valid_hypothesis().model_copy(
        update={
            "typed_target_atom_or_bond_set": [
                BondTarget(begin_atom_id=1, end_atom_id=999)
            ],
        }
    )
    with pytest.raises(UnknownReferenceError):
        validate_agent_proposed_hypothesis(h, _valid_context())


# ---------------------------------------------------------------------------
# Step 5: graph edit — apply compiled delta to the query molecule
# ---------------------------------------------------------------------------


def test_step5_rejects_missing_query_molecule_context():
    h = _valid_hypothesis()
    ctx = _valid_context(with_query=False)
    with pytest.raises(AgentProposedValidationError):
        validate_agent_proposed_hypothesis(h, ctx)


def test_step5_applies_bond_deletion_and_produces_fragments():
    compiled = compile_typed_targets([BondTarget(begin_atom_id=1, end_atom_id=2)])
    edited = apply_graph_edit(compiled, _query_molecule())
    assert isinstance(edited, EditedMolecule)
    assert edited.sanitized is True
    assert edited.heavy_atom_count_before == edited.heavy_atom_count_after
    assert edited.edited_smiles  # non-empty
    assert edited.edited_smiles != edited.query_smiles  # the edit changed something


# ---------------------------------------------------------------------------
# Step 6: molecule validation — sanitization + heavy-atom conservation
# ---------------------------------------------------------------------------


def test_step6_rejects_broken_valence():
    # pentavalent carbon — RDKit sanitization must fail
    bad = EditedMolecule(
        query_smiles="CCO",
        edited_smiles="C(C)(C)(C)(C)C",
        heavy_atom_count_before=3,
        heavy_atom_count_after=3,
        sanitized=False,
    )
    with pytest.raises(AgentProposedValidationError):
        validate_molecule(bad)


def test_step6_rejects_heavy_atom_gain():
    bad = EditedMolecule(
        query_smiles="CCO",
        edited_smiles="CCCO",
        heavy_atom_count_before=3,
        heavy_atom_count_after=4,
        sanitized=True,
    )
    with pytest.raises(AgentProposedValidationError):
        validate_molecule(bad)


# ---------------------------------------------------------------------------
# Step 7: dual-ledger validation — lane non-contamination + existence
# ---------------------------------------------------------------------------


def _scoped_ledger(candidate_id: str, source_ledger_id: str = "src_ledger_a") -> LaneScopedCandidateLedger:
    return LaneScopedCandidateLedger(
        lane="agent_proposed",
        underlying=CandidateAnalogyLedger(
            ledger_id="cand_ledger_1",
            source_ledger_id=source_ledger_id,
            candidate_id=candidate_id,
            candidate_balance_status=LedgerBalanceStatus.partial_or_unbalanced_source,
        ),
    )


def test_step7_rejects_lane_contamination_with_strict_candidate_id():
    h = _valid_hypothesis()
    ctx = _valid_context().model_copy(
        update={
            "agent_candidate_ledgers": {
                h.hypothesis_id: _scoped_ledger(candidate_id="strict_cand_1"),
            }
        }
    )
    with pytest.raises(AgentProposedValidationError):
        validate_dual_ledger(h.hypothesis_id, ctx.agent_candidate_ledgers[h.hypothesis_id], ctx)


def test_step7_rejects_unknown_source_ledger_id():
    h = _valid_hypothesis()
    ctx = _valid_context()
    ledger = _scoped_ledger(candidate_id="agent_cand_1", source_ledger_id="src_unknown")
    with pytest.raises(UnknownReferenceError):
        validate_dual_ledger(h.hypothesis_id, ledger, ctx)


def test_step7_accepts_clean_agent_scoped_ledger():
    h = _valid_hypothesis()
    ctx = _valid_context().model_copy(
        update={
            "agent_candidate_ledgers": {
                h.hypothesis_id: _scoped_ledger(candidate_id="agent_cand_1"),
            }
        }
    )
    # no raise
    validate_dual_ledger(h.hypothesis_id, ctx.agent_candidate_ledgers[h.hypothesis_id], ctx)


# ---------------------------------------------------------------------------
# Step 8: grounding validation — family grounded by a cited support reaction
# ---------------------------------------------------------------------------


def test_step8_rejects_ungrounded_family():
    h = _valid_hypothesis()  # family fam_cc_bond grounded by rxn_a (cited)
    ctx = _valid_context(with_grounding=False)  # no grounding evidence at all
    with pytest.raises(AgentProposedValidationError):
        validate_grounding(h, ctx)


def test_step8_rejects_family_not_grounded_by_cited_support():
    # family is grounded, but only by a reaction the hypothesis did NOT cite
    h = _valid_hypothesis().model_copy(update={"support_reaction_ids": ["rxn_b"]})
    # fam_cc_bond is grounded only by rxn_a in the default context
    ctx = _valid_context()
    with pytest.raises(AgentProposedValidationError):
        validate_grounding(h, ctx)


# ---------------------------------------------------------------------------
# Full chain happy path + lane-pinned candidate emission
# ---------------------------------------------------------------------------


def test_full_chain_happy_path_emits_lane_pinned_candidate():
    cand = build_agent_proposed_candidate(_valid_hypothesis(), _valid_context())
    assert isinstance(cand, AgentProposedCandidate)
    assert cand.lane == "agent_proposed"
    assert cand.exploratory is True
    assert cand.output_semantics == "exploratory_non_production"
    assert cand.validation.status == "validated"
    assert cand.validation.lane == "agent_proposed"
    # the 8 checks are burned in AFTER the chain passes
    assert len(cand.validation.checks) == 8
    assert cand.compiled_graph_edit.compile_hash
    assert cand.edited_product_smiles  # non-empty


def test_candidate_is_structurally_distinct_from_strict_candidate():
    cand = build_agent_proposed_candidate(_valid_hypothesis(), _valid_context())
    # an AgentProposedCandidate must NOT be assignable to a strict Candidate:
    # it has no canonical_product / ranking_score / run_id fields and a pinned
    # lane Literal — a structurally incompatible type.
    with pytest.raises(ValidationError):
        Candidate.model_validate(cand.model_dump())


def test_builder_burns_checks_only_after_chain_passes():
    # a hypothesis with an empty target set cannot pass the compiler step.
    # the builder must NOT emit a candidate whose validation.checks claim pass.
    h = _valid_hypothesis().model_copy(
        update={"typed_target_atom_or_bond_set": []}
    )
    with pytest.raises(ValidationError):
        # schema itself rejects the empty target set before the chain runs
        build_agent_proposed_candidate(h, _valid_context())


# ---------------------------------------------------------------------------
# Consumption gate (re-run, never trust embedded record)
# ---------------------------------------------------------------------------


def test_consumption_gate_reruns_chain_and_catches_lying_candidate():
    cand = build_agent_proposed_candidate(_valid_hypothesis(), _valid_context())
    # tamper: claim 8 checks passed, but corrupt the edited product so the
    # re-run chain raises at molecule validation
    lying = cand.model_copy(
        update={
            "edited_product_smiles": "C(C)(C)(C)(C)C",  # broken valence
        }
    )
    # the embedded validation.checks still claim "validated" — the re-run must
    # catch the lie and raise, never trust the embedded record.
    with pytest.raises((AgentProposedValidationError, UnknownReferenceError)):
        revalidate_agent_proposed_candidate(lying, _valid_context())


def test_consumption_gate_accepts_honest_candidate():
    cand = build_agent_proposed_candidate(_valid_hypothesis(), _valid_context())
    revalidate_agent_proposed_candidate(cand, _valid_context())  # no raise


# ---------------------------------------------------------------------------
# Lane mixing — strict input rejected by the agent-proposed consumer
# ---------------------------------------------------------------------------


def test_lane_mixing_strict_candidate_rejected_by_agent_proposed_consumer():
    strict_cand = Candidate(
        candidate_id="strict_cand_1",
        canonical_product="CCO",
        lane=Lane.strict,
        origin="agent_selected_from_evidence_space",
    )
    # the consumption gate must reject a strict-lane input outright (no
    # cross-lane raw-score mixing, no strict masquerade)
    with pytest.raises(AgentProposedValidationError):
        revalidate_agent_proposed_candidate(strict_cand, _valid_context())


# ---------------------------------------------------------------------------
# Independent report — six metric groups
# ---------------------------------------------------------------------------


def test_report_six_metric_groups_complete():
    cand = build_agent_proposed_candidate(_valid_hypothesis(), _valid_context())
    report = build_agent_proposed_report(
        candidates=[cand],
        rejected=[],
        production_valid_count=2,
        ground_truth_smiles={"h_ap_1": cand.edited_product_smiles},  # correct
        cost=AgentProposedCostReport(llm_calls=1, tool_calls=0, latency_ms=120),
        reproducibility=AgentProposedReproducibility(
            repeated_run_agreement=1.0, seed=42, chain_policy_version="1.0.0"
        ),
    )
    assert isinstance(report, AgentProposedReport)
    assert report.lane == "agent_proposed"
    assert report.exploratory is True
    # six metric groups
    assert report.new_valid == 1
    assert report.new_correct == 1
    assert report.new_incorrect == 0
    assert isinstance(report.reject_reasons, dict)
    assert report.incremental_recall >= 0.0
    assert report.risk >= 0.0
    assert report.cost.llm_calls == 1
    assert report.reproducibility.repeated_run_agreement == 1.0


def test_report_reject_reasons_tallied_by_code():
    cand = build_agent_proposed_candidate(_valid_hypothesis(), _valid_context())
    report = build_agent_proposed_report(
        candidates=[cand],
        rejected=[
            ("h_bad_1", AgentProposedRejectReasonCode.molecule_validation_failed),
            ("h_bad_2", AgentProposedRejectReasonCode.molecule_validation_failed),
            ("h_bad_3", AgentProposedRejectReasonCode.grounding_failed),
        ],
        production_valid_count=0,
    )
    assert report.reject_reasons["molecule_validation_failed"] == 2
    assert report.reject_reasons["grounding_failed"] == 1


def test_report_incremental_recall_and_risk_computed():
    # 2 production-only valid; +2 agent-proposed valid (1 correct, 1 incorrect)
    cand = build_agent_proposed_candidate(_valid_hypothesis(), _valid_context())
    report = build_agent_proposed_report(
        candidates=[cand, cand],
        rejected=[],
        production_valid_count=2,
        ground_truth_smiles={"h_ap_1": "WRONG"},  # both marked incorrect
    )
    # incremental recall = (production + new_correct) / total_relevant
    # new_valid=2, new_correct=0, new_incorrect=2
    assert report.new_valid == 2
    assert report.new_correct == 0
    assert report.new_incorrect == 2
    # risk = new_incorrect / (new_correct + new_incorrect) at fixed coverage
    assert report.risk == pytest.approx(1.0)
    assert report.incremental_recall >= 0.0


# ---------------------------------------------------------------------------
# Reproducibility — same input -> same compile_hash + same edited SMILES
# ---------------------------------------------------------------------------


def test_reproducibility_same_input_same_compile_hash_and_smiles():
    h = _valid_hypothesis()
    ctx = _valid_context()
    c1 = build_agent_proposed_candidate(h, ctx)
    c2 = build_agent_proposed_candidate(h, ctx)
    assert c1.compiled_graph_edit.compile_hash == c2.compiled_graph_edit.compile_hash
    assert c1.edited_product_smiles == c2.edited_product_smiles
    assert c1.validation.chain_policy_content_hash == c2.validation.chain_policy_content_hash
