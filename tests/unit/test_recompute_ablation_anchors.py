# -*- coding: utf-8 -*-
"""v44 消融锚点独立零调用复算器（recompute_ablation_anchors）纯净单测。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "eval" / "recompute_ablation_anchors.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("recompute_ablation_anchors", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_verify_frozen_scorers_passes_on_repo_and_fails_on_tamper(tmp_path: Path):
    mod = _load_module()
    res = mod.verify_frozen_scorers(REPO_ROOT)
    assert res["all_ok"] is True
    assert set(res["files"]) == set(mod.FROZEN_SCORER_SHA256)

    # 伪造一份篡改后目录，断言 fail-closed 拒绝
    for rel in mod.FROZEN_SCORER_SHA256:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# tampered\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="SHA256"):
        mod.verify_frozen_scorers(tmp_path)


def test_clean_220_sha16_cardinality_and_hex_format():
    mod = _load_module()
    assert len(mod.CLEAN_220_SHA16) == 220
    assert all(len(h) == 16 and all(c in "0123456789abcdef" for c in h) for h in mod.CLEAN_220_SHA16)


def test_classify_key_prefix_and_provenance_from_payload():
    mod = _load_module()
    assert mod.classify_key_prefix("rec-123", "") == "rec"
    assert mod.classify_key_prefix("", "rec-source:abc") == "rec"
    assert mod.classify_key_prefix("tpl-rr_mnx-9", "") == "tpl-rr_mnx"
    assert mod.classify_key_prefix("tpl-eawag-2", "") == "tpl-eawag"
    assert mod.classify_key_prefix("novel-cand-1", "") == "novel"

    payload = {
        "events": [
            {"event_id": "ev_rec", "hypothesis_id": "hyp_1"},
            {"event_id": "ev_tpl", "hypothesis_id": "hyp_2"},
            {"event_id": "ev_nov", "hypothesis_id": "hyp_3"},
        ],
        "search_actions": [
            {
                "action_kind": "expand_hypothesis",
                "subject_ref": "hyp_1",
                "payload": {
                    "logical_proposal_id": "rec-cand-1",
                    "spec": {"transformation_ref": "rec-source:r1"},
                },
            },
            {
                "action_kind": "expand_hypothesis",
                "subject_ref": "hyp_2",
                "payload": '{"logical_proposal_id": "tpl-rr_mnx-2", "spec": {"transformation_ref": "rr_mnx:t2"}}',
            },
            {
                "action_kind": "expand_hypothesis",
                "subject_ref": "hyp_3",
                "payload": {
                    "logical_proposal_id": "novel-1",
                    "spec": {"transformation_ref": "novel:model"},
                },
            },
        ],
    }
    prov = mod.provenance_from_payload(payload)
    assert prov["hypothesis_key_by_event"] == {
        "ev_rec": "rec-cand-1",
        "ev_tpl": "tpl-rr_mnx-2",
        "ev_nov": "novel-1",
    }
    assert prov["transformation_ref_by_event"] == {
        "ev_rec": "rec-source:r1",
        "ev_tpl": "rr_mnx:t2",
        "ev_nov": "novel:model",
    }


def test_compute_ex_self_ranks_distinguishes_all_ex_rec_only_and_ex_self():
    mod = _load_module()
    candidates = [
        {"event_id": "ev_rec"},
        {"event_id": "ev_tpl"},
        {"event_id": "ev_nov"},
    ]
    trefs = {"ev_rec": "rec-source:r1", "ev_tpl": "rr_mnx:t2", "ev_nov": "novel:model"}
    keys = {"ev_rec": "rec-1", "ev_tpl": "tpl-rr_mnx-2", "ev_nov": "novel-3"}

    # Full pool (both rec and tpl hit gold): all=1 -> ex_rec_only=2 -> ex_self=3
    res_full = mod.compute_ex_self_ranks(
        candidates=candidates,
        hit_events={"ev_rec", "ev_tpl", "ev_nov"},
        tref_by_event=trefs,
        key_by_event=keys,
        rec_refs={"rec-source:r1"},
        tpl_refs={"rr_mnx:t2"},
        tpl_family={"rr_mnx:t2": "tpl-rr_mnx"},
    )
    assert res_full["ex_rec_rank"] == 2
    assert res_full["ex_self_rank"] == 3
    assert res_full["rank1_rec_flag"] is True
    assert res_full["rank1_prefix"] == "rec"

    # NoSelf pool (rec_refs empty): ex_rec_only == first hit (1), while ex_self skips ev_tpl -> 2
    res_noself = mod.compute_ex_self_ranks(
        candidates=[{"event_id": "ev_tpl"}, {"event_id": "ev_nov"}],
        hit_events={"ev_tpl", "ev_nov"},
        tref_by_event=trefs,
        key_by_event=keys,
        rec_refs=set(),
        tpl_refs={"rr_mnx:t2"},
        tpl_family={"rr_mnx:t2": "tpl-rr_mnx"},
    )
    assert res_noself["ex_rec_rank"] == 1
    assert res_noself["ex_self_rank"] == 2
    assert res_noself["rank1_rec_flag"] is False
    assert res_noself["rank1_tpl_flag"] is True
    assert res_noself["rank1_tpl_fam"] == "tpl-rr_mnx"
