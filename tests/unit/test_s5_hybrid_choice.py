# -*- coding: utf-8 -*-
"""Unit tests for s5_hybrid_choice.py (Phase 1 of TASK_S1D_S5_HYBRID_CHOICE_2026-11-09)."""

from __future__ import annotations

from pathway_v43.pollutant.s5b_builder import (
    S1D_POOL_MAX,
    S1D_POOL_PROFILE_VERSION,
    S1D_POOL_THRESHOLD,
    s1d_pool_provider,
)
from pathway_v43.services.s5_hybrid_choice import (
    CONTROLLED_12_REACTION_CLASSES,
    HybridCandidate,
    classify_reaction_12class,
    compute_chemical_prior_score,
    compute_formula_delta_str,
    k_strict,
    merge_dual_track_predictions,
    predict_top_reaction_classes_from_substrate,
    rank_and_select_hybrid_pool,
    render_dual_track_supplement_card,
    render_hybrid_choice_card,
    select_gated_s5_supplements,
)


def test_12_reaction_classes_classification() -> None:
    assert len(CONTROLLED_12_REACTION_CLASSES) == 12

    # 1. Monooxygenation / Hydroxylation (+1O)
    c6, f12 = classify_reaction_12class("c1ccccc1", "Oc1ccccc1")
    assert f12 == "monooxygenation_hydroxylation"
    assert compute_formula_delta_str("c1ccccc1", "Oc1ccccc1") == "+O"

    # 2. Dehalogenation (chlorobenzene -> phenol)
    _, f12_dehal = classify_reaction_12class("Clc1ccccc1", "Oc1ccccc1")
    assert f12_dehal == "dehalogenation_or_halogenation"

    # 3. Decarboxylation (benzoic acid -> benzene)
    _, f12_decarb = classify_reaction_12class("O=C(O)c1ccccc1", "c1ccccc1")
    assert f12_decarb == "decarboxylation_or_c1_cleavage"

    # 4. Dehydrogenation / Oxidation (ethanol -> acetaldehyde)
    _, f12_ox = classify_reaction_12class("CCO", "CC=O")
    assert f12_ox == "dehydrogenation_oxidation"


def test_chemical_prior_multi_source_consensus_and_class_balance() -> None:
    sub = "Clc1ccccc1"
    # Candidate A: multi-source consensus (analog + envipath + rr_rhea)
    cand_a = HybridCandidate(
        cand_strict=k_strict("Oc1ccccc1") or "A",
        cand_smiles="Oc1ccccc1",
        sub_smiles=sub,
        source_families={"analog", "envipath", "rr_rhea"},
        s1d_best_rank=2,
        s1d_best_sim=0.45,
        s1d_channels={"analog"},
        env_rule_ids={"bt0001"},
        env_freq_sum=10,
        rr_rule_ids={"RR01"},
        rr_max_radius=4,
        rr_freq_sum=20,
        fine_cat="dehalogenation_or_halogenation",
        formula_delta="+H +O -Cl",
        heavy_atom_ratio=1.0,
    )
    # Candidate B: single low-radius r=2 rule only
    cand_b = HybridCandidate(
        cand_strict=k_strict("Oc1ccc(Cl)cc1") or "B",
        cand_smiles="Oc1ccc(Cl)cc1",
        sub_smiles=sub,
        source_families={"rr_mnx"},
        rr_rule_ids={"RR02"},
        rr_max_radius=2,
        rr_freq_sum=5,
        fine_cat="monooxygenation_hydroxylation",
        formula_delta="+O",
        heavy_atom_ratio=1.14,
    )

    sa = compute_chemical_prior_score(cand_a, domain="biosysmodb121")
    sb = compute_chemical_prior_score(cand_b, domain="biosysmodb121")
    assert sa > sb
    assert cand_a.prior_tier == "HIGH_CONSENSUS"

    ranked = rank_and_select_hybrid_pool([cand_b, cand_a], max_pool=8, class_balanced=True)
    assert ranked[0].cand_smiles == "Oc1ccccc1"

    top_classes = predict_top_reaction_classes_from_substrate(sub, ranked, top_m=2)
    assert "dehalogenation_or_halogenation" in top_classes

    card_text = render_hybrid_choice_card(sub, ranked)
    assert "[OPT-01]" in card_text
    assert "Oc1ccccc1" in card_text
    assert "dehalogenation_or_halogenation" in card_text


def test_s1d_frozen_profile_and_provider_registration() -> None:
    assert S1D_POOL_PROFILE_VERSION == "s5b-pool-profile-s1d-1"
    assert S1D_POOL_MAX == 16
    assert S1D_POOL_THRESHOLD == 0.25

    prov = s1d_pool_provider(None)
    assert callable(prov)
    assert prov("CCO") == []


def test_dual_track_gated_s5_supplements_and_slot_reserved_merge() -> None:
    # 1. When S1d already has >= 3 candidates, gate stays closed (protects S1 precision)
    s1d_rich = [
        {"cand_smiles": "CC=O", "cand_strict": "CC=O", "prior_score": 90.0},
        {"cand_smiles": "CC(=O)O", "cand_strict": "CC(=O)O", "prior_score": 85.0},
        {"cand_smiles": "OCCO", "cand_strict": "OCCO", "prior_score": 80.0},
    ]
    hybrid_cands = [
        {"cand_smiles": "CC=O", "cand_strict": "CC=O", "prior_score": 90.0},
        {"cand_smiles": "CCOC=O", "cand_strict": "CCOC=O", "prior_score": 140.0, "fine_cat": "transfer_or_conjugation"},
        {"cand_smiles": "CCCO", "cand_strict": "CCCO", "prior_score": 60.0, "fine_cat": "other_transformation"},
    ]
    assert select_gated_s5_supplements(s1d_rich, hybrid_cands) == []

    # 2. When S1d has <= 2 candidates, only non-S1d S5 candidates with prior_score >= 70.0 pass
    s1d_sparse = [{"cand_smiles": "CC=O", "cand_strict": "CC=O", "prior_score": 90.0}]
    supps = select_gated_s5_supplements(s1d_sparse, hybrid_cands, min_s5_prior_score=70.0)
    assert len(supps) == 1
    assert supps[0]["cand_smiles"] == "CCOC=O"

    # 3. Slot-reserved merge: 2 supplements -> Track-1 keeps Slots 1..3, Track-2 fills Slots 4..5
    t1_preds = ["CC=O", "CC(=O)O", "OCCO", "CCCC", "CCCCC"]
    s5_two = [
        {"cand_smiles": "c1ccccc1O", "cand_strict": "Oc1ccccc1", "prior_score": 145.0},
        {"cand_smiles": "c1ccc(O)cc1O", "cand_strict": "Oc1ccc(O)cc1", "prior_score": 110.0},
    ]
    merged_3p2 = merge_dual_track_predictions(t1_preds, s5_two, total_slots=5, max_supplements=2)
    assert len(merged_3p2) == 5
    assert merged_3p2[:3] == ["CC=O", "CC(=O)O", "OCCO"]
    assert merged_3p2[3:] == ["c1ccccc1O", "c1ccc(O)cc1O"]

    # 4. If one S5 supplement is already in Track-1 Top-3, Slot 4 is returned to Track-1's 4th prediction!
    s5_overlap = [
        {"cand_smiles": "CC(=O)O", "cand_strict": "CC(=O)O", "prior_score": 145.0},
        {"cand_smiles": "c1ccccc1O", "cand_strict": "Oc1ccccc1", "prior_score": 110.0},
    ]
    merged_overlap = merge_dual_track_predictions(t1_preds, s5_overlap, total_slots=5, max_supplements=2)
    assert len(merged_overlap) == 5
    assert merged_overlap[:4] == ["CC=O", "CC(=O)O", "OCCO", "CCCC"]
    assert merged_overlap[4] == "c1ccccc1O"

    # 5. Render dual-track card
    card = render_dual_track_supplement_card("CCO", s1d_sparse, supps)
    assert "[TRACK-1:" in card
    assert "[TRACK-2:" in card
    assert "[S5-SUPP-01]" in card
