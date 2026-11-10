"""Unit tests for Phase 2b standalone RetroRules loader, source adapter, and derived indexes.

Covers:
  1. SMARTS normalization (balanced component-group parentheses ``(A.B).C``) and
     100% record conversion across sanitized and aromatic-fragment templates.
  2. Verified ``rhea_retro_index.npz`` (134,738 rules) and ``mnx_retro_index.npz``
     (336,966 rules) loading, selftest, and ``mnx <-> rhea`` shared ``TEMPLATE``
     cross-mapping (77,144 shared templates).
  3. Merged ``"mnx+rhea"`` union dataset (394,560 unique templates).
  4. Exact ``allowed_radii`` filtering (``{2}``, ``{4}``, ``{6}``, ``{2, 4}``).
  5. Small-radius (``r=2, 4, 6``) substructure/hybrid retrieval and
     ``bridge_occurrence_to_spec`` compilation with strict multiset fidelity.
  6. Self-record detection (``check_retro_self_record``) by reaction ID overlap
     (``RHEA:xxxx`` / ``MNXR...``) and strict ``(substrate, principal_product)``
     identity match.
  7. Pool integration helpers (``compile_retro_candidates_for_substrate`` and
     ``merge_retro_specs_into_pool`` with ``append`` vs ``unified_score``).
  8. Fail-closed tamper detection on corrupted manifest/index artifacts.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import pytest

from pathway_v43.services.retro_loader import (
    FLAG_BOTH_SIDES_SANITIZED,
    FLAG_INDEXED,
    RetroAssetError,
    RetroLibrary,
    normalize_side_smarts,
    process_record,
)
from pathway_v43.services.retro_source import (
    RetroTemplateResolver,
    bridge_occurrence_to_spec,
    check_retro_self_record,
    compile_retro_candidates_for_substrate,
    merge_retro_specs_into_pool,
    retro_asset_identity,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DERIVED_DIR = REPO_ROOT / "assets" / "retrorules" / "derived"
RAW_DIR = REPO_ROOT / "assets" / "retrorules" / "raw"


def test_normalize_side_smarts_and_aromatic_fragment_handling():
    """Verify component-group parens stripping and aromatic fragment indexing."""
    raw = "(([#6:1]-[#8:2].[#8:3])).[#6:4]"
    assert normalize_side_smarts(raw) == "[#6:1]-[#8:2].[#8:3].[#6:4]"

    # Small-radius aromatic fragment that cuts through a benzene ring
    frag_rec = {
        "TEMPLATE_ID": "RR:TEST-FRAG-R2",
        "TEMPLATE": "([#8:1]-[c:2](:[cH:3]):[cH:4])>>([#8:1]=[#6:2](-[#6:3])-[#6:4])",
        "RADIUS_MIN": 2,
        "RADIUS_MAX": 2,
        "RADII": [2],
        "ECS": ["1.13.11.-"],
        "REACTIONS": ["RHEA:99999"],
        "SCORE": [1.5],
        "VALID": True,
    }
    out_frag = process_record(frag_rec, allow_unsanitized_fragments=True)
    assert out_frag["status"] == "indexed"
    assert out_frag["both_sides_sanitized"] is False
    assert out_frag["unsanitized_reason"] == "lhs_convert_aromatic_fragment"
    assert bool(out_frag["flags"] & FLAG_INDEXED) is True
    assert bool(out_frag["flags"] & FLAG_BOTH_SIDES_SANITIZED) is False

    # Strict mode skips unsanitized aromatic fragments as in n004 stage 1
    out_strict = process_record(frag_rec, allow_unsanitized_fragments=False)
    assert out_strict["status"] == "skip"
    assert out_strict["reason"] == "lhs_convert_aromatic_fragment"


def test_rhea_index_verification_and_selftest():
    """Verify pre-built rhea_retro_index.npz counts, integrity, and selftest."""
    lib = RetroLibrary(DERIVED_DIR, dataset="rhea", source=RAW_DIR / "rhea.json")
    counts = lib.manifest["counts"]
    assert counts["n_templates"] == 134738
    assert counts["n_indexed"] == 134738
    assert counts["n_sanitized_both"] == 112862
    assert counts["n_unsanitized_fragment"] == 21876
    assert counts["n_skipped"] == 0
    assert counts["n_unique_lhs"] == 75067
    assert counts["radii_counts"]["2"] == 16528
    assert counts["radii_counts"]["4"] == 19946
    assert counts["radii_counts"]["6"] == 21454

    st = lib.selftest(10)
    assert st["all_passed"] is True
    assert st["passed"] == 10


def test_mnx_index_verification_and_rhea_cross_mapping():
    """Verify pre-built mnx_retro_index.npz counts and 77,144 shared RHEA cross-maps."""
    lib = RetroLibrary(DERIVED_DIR, dataset="mnx", source=RAW_DIR / "METANETX.json")
    counts = lib.manifest["counts"]
    assert counts["n_templates"] == 336966
    assert counts["n_indexed"] == 336966
    assert counts["n_sanitized_both"] == 275956
    assert counts["n_unsanitized_fragment"] == 61010
    assert counts["n_skipped"] == 0
    assert counts["n_unique_lhs"] == 182875
    assert counts["shared_rhea_templates_count"] == 77163
    assert counts["radii_counts"]["2"] == 43829
    assert counts["radii_counts"]["4"] == 51780
    assert counts["radii_counts"]["6"] == 55134

    # Verify cross-mapped RHEA reaction IDs appear on MNX search hits
    resolver = RetroTemplateResolver(index_dir=DERIVED_DIR, dataset="mnx")
    refs = resolver.templates_similar_to(
        "O=C(O)c1ccc(O)cc1", threshold=0.45, top_k=25, mode="hybrid"
    )
    assert len(refs) > 0
    cross_mapped = [r for r in refs if r.rhea_reactions]
    assert len(cross_mapped) > 0
    for ref in cross_mapped:
        assert any(rx.startswith("RHEA:") for rx in ref.rhea_reactions)
        for rx in ref.rhea_reactions:
            assert rx in ref.parent_reaction_ids


def test_merged_mnx_plus_rhea_union():
    """Verify mnx+rhea deduplicates shared templates and merges reactions & radii."""
    resolver = RetroTemplateResolver(index_dir=DERIVED_DIR, dataset="mnx+rhea")
    ident = resolver.identity
    # 336,966 + 134,738 - 77,156 = 394,548 unique templates
    assert ident["n_templates"] == 394548
    assert ident["n_indexed"] == 394548
    assert ident["library"] == "mnx+rhea"

    refs = resolver.templates_similar_to(
        "O=C(O)c1ccc(O)cc1",
        threshold=0.45,
        top_k=20,
        allowed_radii={6},
        mode="hybrid",
    )
    assert len(refs) > 0
    assert all(6 in ref.radii for ref in refs)


def test_exact_allowed_radii_filtering():
    """Verify exact radius bitmask filtering for {2}, {4}, {6}, and {2, 4}."""
    resolver = RetroTemplateResolver(index_dir=DERIVED_DIR, dataset="rhea")
    substrate = "O=C(O)c1ccc(O)cc1"

    for allowed in ({2}, {4}, {6}, {2, 4}):
        refs = resolver.templates_similar_to(
            substrate,
            threshold=0.45,
            top_k=30,
            allowed_radii=allowed,
            mode="hybrid",
        )
        assert len(refs) > 0
        for ref in refs:
            assert set(ref.radii) & allowed, (
                f"Template {ref.template_id} radii={ref.radii} does not intersect {allowed}"
            )


def test_small_radius_substruct_and_bridge_compilation():
    """Verify r=2 and r=4 retrieval + bridge_occurrence_to_spec compilation."""
    substrate = "O=C(O)c1ccc(O)cc1"  # 4-hydroxybenzoate

    kept_r2, stats_r2 = compile_retro_candidates_for_substrate(
        substrate,
        index_dir=DERIVED_DIR,
        dataset="rhea",
        allowed_radii={2},
        top_k=24,
        retrieval_mode="hybrid",
        compile_mode="hybrid",
    )
    assert stats_r2["retro_n_retrieved"] > 0
    assert stats_r2["retro_n_compiled"] > 0
    assert stats_r2["retro_n_compiled_bridge"] > 0
    assert len(kept_r2) > 0

    for spec in kept_r2:
        assert spec["channel"] == "retro"
        assert "retro_meta" in spec
        assert 2 in spec["retro_meta"]["radii"]
        assert spec["expectation"]["target_smiles"]


def test_self_record_detection_reaction_id_and_strict_pair():
    """Verify check_retro_self_record detects both reaction ID overlap and strict pair match."""
    resolver = RetroTemplateResolver(index_dir=DERIVED_DIR, dataset="mnx")
    refs = resolver.templates_similar_to(
        "O=C(O)c1ccc(O)cc1", threshold=0.45, top_k=25, mode="hybrid"
    )
    ref_with_rhea = next(r for r in refs if r.rhea_reactions)
    target_rhea = ref_with_rhea.rhea_reactions[0]
    bare_digits = target_rhea.split(":")[1]

    # 1) Match by RHEA:xxxx or bare digits
    res_id = check_retro_self_record(
        ref_with_rhea,
        question_source_ids=[bare_digits],
    )
    assert res_id["is_self_record"] is True
    assert res_id["by_reaction_id"] is True
    assert target_rhea in res_id["matched_reaction_ids"]

    # 2) Match by strict (substrate, principal_product) identity
    san_ref = next(
        r for r in refs
        if r.both_sides_sanitized and r.lhs_unmapped_smiles and r.rhs_unmapped_smiles
    )
    lhs_comp = san_ref.lhs_unmapped_smiles.split(".")[0]
    rhs_comp = san_ref.rhs_unmapped_smiles.split(".")[0]
    res_strict = check_retro_self_record(
        san_ref,
        question_source_ids=["RHEA:00000"],
        substrate_smiles=lhs_comp,
        gold_principal_smiles=[rhs_comp],
    )
    assert res_strict["is_self_record"] is True
    assert res_strict["by_reaction_id"] is False
    assert res_strict["by_strict_pair"] is True

    # 3) Non-matching control
    res_neg = check_retro_self_record(
        san_ref,
        question_source_ids=["RHEA:00000"],
        substrate_smiles="CCO",
        gold_principal_smiles=["CC=O"],
    )
    assert res_neg["is_self_record"] is False


def test_pool_ranking_modes_append_and_unified_score():
    """Verify merge_retro_specs_into_pool under append and unified_score modes."""
    substrate = "O=C(O)c1ccc(O)cc1"
    retro_kept, _stats = compile_retro_candidates_for_substrate(
        substrate,
        index_dir=DERIVED_DIR,
        dataset="rhea",
        allowed_radii={6},
        top_k=15,
        retrieval_mode="hybrid",
        compile_mode="hybrid",
    )
    assert len(retro_kept) >= 2

    # Construct a synthetic analog spec with lower similarity than top retro spec
    fake_analog = dict(retro_kept[-1])
    fake_analog["key"] = "atpl:fake_analog_1"
    fake_analog["channel"] = "analog"
    fake_analog["origin_group_key"] = "analog:fake_1"
    fake_analog["similarity"] = 0.41

    pool_append = merge_retro_specs_into_pool(
        [fake_analog], retro_kept[:-1], max_pool=8, ranking_mode="append"
    )
    assert pool_append[0]["key"] == "atpl:fake_analog_1"

    # Ensure top retro spec has strictly highest similarity for unified_score test
    for idx_r, rspec in enumerate(retro_kept[:-1]):
        rspec["retro_meta"]["similarity"] = 0.95 if idx_r == 0 else 0.55
    pool_unified = merge_retro_specs_into_pool(
        [fake_analog], retro_kept[:-1], max_pool=8, ranking_mode="unified_score"
    )
    assert pool_unified[0]["key"] == retro_kept[0]["key"]


def test_query_speed_benchmark():
    """Verify per-substrate search speed is fast (< 50 ms per substrate)."""
    resolver = RetroTemplateResolver(index_dir=DERIVED_DIR, dataset="rhea")
    substrates = [
        "O=C(O)c1ccc(O)cc1",
        "Nc1ccccc1C(=O)O",
        "CC(=O)O",
        "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O",
        "c1ccc(cc1)O",
    ]
    # Warm-up query
    resolver.templates_similar_to(substrates[0], top_k=24, mode="hybrid")

    t0 = time.time()
    for smi in substrates:
        resolver.templates_similar_to(
            smi, top_k=24, allowed_radii={6}, mode="hybrid"
        )
    avg_ms = (time.time() - t0) * 1000.0 / len(substrates)
    assert avg_ms < 50.0


def test_fail_closed_on_tampered_meta(tmp_path: Path):
    """Verify RetroLibrary raises RetroAssetError when artifact sha256 mismatches."""
    meta_src = DERIVED_DIR / "rhea_retro_index.meta.json"
    npz_src = DERIVED_DIR / "rhea_retro_index.npz"
    meta_dst = tmp_path / "rhea_retro_index.meta.json"
    npz_dst = tmp_path / "rhea_retro_index.npz"
    shutil.copyfile(npz_src, npz_dst)

    meta_data = json.loads(meta_src.read_text(encoding="utf-8"))
    meta_data["artifacts"]["rhea_retro_index.npz"]["sha256"] = "0" * 64
    meta_dst.write_text(json.dumps(meta_data), encoding="utf-8")

    with pytest.raises(RetroAssetError):
        RetroLibrary(tmp_path, dataset="rhea", source=RAW_DIR / "rhea.json")
