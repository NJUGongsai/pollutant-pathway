# -*- coding: utf-8 -*-
"""v1.4 成对裁决排序层（adjudication_v14）与共识融合（consensus_v13）纯净单测。"""

from __future__ import annotations

from types import SimpleNamespace

from pathway_v43.services.adjudication_v14 import (
    ADJUDICATION_EXTERNAL_FIELDS,
    ROLE_PRINCIPAL_PRODUCT,
    VERDICT_PROMOTE_CHALLENGER,
    VERDICT_REORDER_PREFIX,
    apply_pairwise_adjudication,
    candidate_display_from_prepared,
    candidate_display_sha256,
    sanitize_adjudication_external,
)
from pathway_v43.services.consensus_v13 import (
    CONSENSUS_DEFAULT_PARAMS,
    consensus_params,
    consensus_params_from_plan,
    fuse_multi_sample_top5,
)


def _mock_prepared(*product_specs: tuple[str, str]) -> dict:
    """构造最小 prepared 字典：product_specs 为 (smiles, role) 列表。"""
    participants = []
    states = {}
    for idx, (smiles, role) in enumerate(product_specs):
        ref = f"st_{idx}"
        participants.append(SimpleNamespace(side="product", state_ref=ref, role=role))
        states[ref] = SimpleNamespace(smiles_isomeric=smiles)
    participants.append(
        SimpleNamespace(side="reactant", state_ref="reactant_0", role="primary_substrate")
    )
    states["reactant_0"] = SimpleNamespace(smiles_isomeric="c1ccccc1")
    return {"hypothesis": SimpleNamespace(participants=participants), "states": states}


def test_sanitize_adjudication_external_whitelist_and_types():
    assert sanitize_adjudication_external(None) is None
    assert sanitize_adjudication_external(["bad"]) is None

    raw = {
        "verdict": VERDICT_PROMOTE_CHALLENGER,
        "defender_sha256": "aaa",
        "challenger_sha256": "bbb",
        "order_sha256s": ["bbb", 123],
        "gate_tag": "trace_protected",
        "extra_leak": "must_be_dropped",
    }
    cleaned = sanitize_adjudication_external(raw)
    assert cleaned is not None
    assert tuple(sorted(cleaned)) == tuple(sorted(ADJUDICATION_EXTERNAL_FIELDS))
    assert cleaned["order_sha256s"] == ["bbb", "123"]
    assert "extra_leak" not in cleaned

    malformed_order = sanitize_adjudication_external({"order_sha256s": "not_a_list"})
    assert malformed_order == {"order_sha256s": []}


def test_candidate_display_and_sha256_deterministic():
    prep_a = _mock_prepared(("O", "coproduct"), ("Oc1ccccc1", ROLE_PRINCIPAL_PRODUCT), ("O", "coproduct"))
    prep_b = _mock_prepared(("Oc1ccccc1", ROLE_PRINCIPAL_PRODUCT), ("O", "coproduct"))

    disp_a = candidate_display_from_prepared(prep_a)
    disp_b = candidate_display_from_prepared(prep_b)
    assert disp_a == "Oc1ccccc1 + O"
    assert disp_a == disp_b
    assert len(candidate_display_sha256(disp_a)) == 64
    assert candidate_display_sha256(disp_a) == candidate_display_sha256(disp_b)


def test_apply_pairwise_adjudication_promote_reorder_and_guards():
    sha = {"k1": "sha1", "k2": "sha2", "k3": "sha3"}

    # Fewer than two candidates -> skipped
    out, disc = apply_pairwise_adjudication(
        selected_top_keys=["k1"], sha_by_key=sha, external={"verdict": VERDICT_PROMOTE_CHALLENGER}
    )
    assert out == ["k1"]
    assert disc["applied"] is False and disc["skipped"] == "fewer_than_two_candidates"

    # Defender SHA mismatch -> fail-closed
    out, disc = apply_pairwise_adjudication(
        selected_top_keys=["k1", "k2", "k3"],
        sha_by_key=sha,
        external={
            "verdict": VERDICT_PROMOTE_CHALLENGER,
            "defender_sha256": "wrong_sha",
            "challenger_sha256": "sha2",
        },
    )
    assert out == ["k1", "k2", "k3"]
    assert disc["applied"] is False and disc["skipped"] == "defender_sha256_mismatch"

    # Valid promote_challenger
    out, disc = apply_pairwise_adjudication(
        selected_top_keys=["k1", "k2", "k3"],
        sha_by_key=sha,
        external={
            "verdict": VERDICT_PROMOTE_CHALLENGER,
            "defender_sha256": "sha1",
            "challenger_sha256": "sha3",
            "gate_tag": "trace_protected",
        },
    )
    assert out == ["k3", "k1", "k2"]
    assert disc["applied"] is True and disc["promoted_from_rank"] == 3 and disc["gate_tag"] == "trace_protected"

    # Unknown verdict -> fail-closed
    out, disc = apply_pairwise_adjudication(
        selected_top_keys=["k1", "k2"],
        sha_by_key=sha,
        external={"verdict": "unsupported", "defender_sha256": "sha1"},
    )
    assert out == ["k1", "k2"]
    assert disc["applied"] is False and disc["skipped"] == "verdict_unknown"

    # Valid reorder_prefix
    out, disc = apply_pairwise_adjudication(
        selected_top_keys=["k1", "k2", "k3"],
        sha_by_key=sha,
        external={
            "verdict": VERDICT_REORDER_PREFIX,
            "defender_sha256": "sha1",
            "order_sha256s": ["sha2", "sha1"],
        },
    )
    assert out == ["k2", "k1", "k3"]
    assert disc["applied"] is True and disc["skipped"] == ""


def test_consensus_params_and_fuse_multi_sample_top5_invariants():
    # Default params & disabled v14 gates produce None (zero drift)
    p = consensus_params()
    assert p["equiv_cluster_mode"] == "none"
    assert p["elig_norm_alpha"] == CONSENSUS_DEFAULT_PARAMS["elig_norm_alpha"]
    assert consensus_params_from_plan({}) is None

    # Disabled v14 switches strip research overrides of gated keys
    stripped = consensus_params_from_plan(
        {"enable_v14_equiv_product_consensus": False},
        base={"equiv_cluster_mode": "v6_neutral", "rrf_k": 5.0},
    )
    assert stripped == {"rrf_k": 5.0}

    row_a = {"src": "cand_a", "cls": "monooxygenation_hydroxylation", "is_rec": False, "is_novel": True, "raw_sim": 0.4, "prior": 100.0, "eff_rk": 1}
    row_b = {"src": "cand_b", "cls": "dehydrogenation_oxidation", "is_rec": True, "is_novel": False, "raw_sim": 0.99, "prior": 50.0, "eff_rk": 2}
    row_c = {"src": "cand_c", "cls": "monooxygenation_hydroxylation", "is_rec": False, "is_novel": True, "raw_sim": 0.5, "prior": 250.0, "eff_rk": 3}

    # Unanimous rank-0 lock vs deterministic fusion
    fused, note = fuse_multi_sample_top5(
        pass_top5_lists=[[row_a, row_b], [row_c, row_a]],
        submittable_by_key={"cand_a": row_a, "cand_b": row_b, "cand_c": row_c},
        stage1_routing={"primary_class": "monooxygenation_hydroxylation", "secondary_class": "invalid_class"},
        target_slots=3,
    )
    assert [r["src"] for r in fused] == note["fused_keys"]
    assert len(fused) == 3
    assert fused[0]["src"] == "cand_a"
    assert note["stage1_routing"]["primary_class"] == "monooxygenation_hydroxylation"
    assert note["stage1_routing"]["secondary_classes"] == []
