"""T-F 位次继承回归测试（s5b-rank-policy-2，2026-10-17）。

背景：`docs/TF_RANK_TRANSFER_VERIFICATION_2026-10-16.md` +
`docs/TF_SYNTHETIC_VALIDATION_2026-10-17.md`（证实）——模型首位 novel
折叠进**无声明位次**的池条目时，v1 丢弃被折叠者位次，该反应劣化到
deterministic_fallback 殿后。v2 修复：被折叠者声明位次优于幸存者
（或幸存者无声明位次）⇒ 幸存者继承该位次；继承事实逐条落
dedup_rejections（folded_model_rank / rank_inherited）与展开载荷
（model_rank_inherited_from），不静默。

四夹具=合成验证报告的 fx1/fx2/fx3 与"幸存者位次更优不继承"变体；
纯构造输入（零金标零题面），scripted 协议零模型。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.domain.models import stable_id  # noqa: E402
from pathway_v43.pollutant.chemstate import build_chemical_state  # noqa: E402
from pathway_v43.pollutant.production import prepare_hypothesis  # noqa: E402
from pathway_v43.storage.run_identity import (  # noqa: E402
    PROFILE_POLLUTANT_PATHWAY_V1,
)
from pathway_v43.workflow.runner import start_run  # noqa: E402

# ---- 纯构造池（与合成验证夹具同源）----
SPEC_A = {  # 产物 CC=O（s3b_r2 spec 模板）
    "key": "A", "product_smiles": "CC=O", "coefficient": 1,
    "transformation_ref": "donor-A", "origin_group_key": "donor-A",
    "edits": [{"op": "change_bond_order", "atom1": "S_C_2",
               "atom2": "S_O_1", "from_order": "single",
               "to_order": "double"}],
    "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
    "alignment": {"status": "resolved",
                  "donor_to_current": {"S_C_2": "S_C_2",
                                       "S_O_1": "S_O_1"},
                  "ref": "align-A"},
    "expectation": {"target_smiles": "CC=O"}}
SPEC_B = {  # 产物 CCOO（add_atom O 模板，与 novel 同签名）
    "key": "B", "product_smiles": "CCOO", "coefficient": 1,
    "transformation_ref": "donor-B", "origin_group_key": "donor-B",
    "edits": [{"op": "add_atom", "element": "O",
               "new_atom_id": "SN_O_1", "atom1": "S_O_1"}],
    "donor": {"center_atom_ids": ["S_O_1", "SN_O_1"]},
    "alignment": {"status": "resolved",
                  "donor_to_current": {"S_O_1": "S_O_1",
                                       "SN_O_1": "SN_O_1"},
                  "ref": "align-B"},
    "expectation": {"target_smiles": "CCOO"}}


def _novel(product, element, new_atom, anchor, tref):
    return {
        "key": "Novel", "product_smiles": product, "coefficient": 1,
        "transformation_ref": tref, "origin_group_key": tref,
        "edits": [{"op": "add_atom", "element": element,
                   "new_atom_id": new_atom, "atom1": anchor}],
        "donor": {"center_atom_ids": [anchor, new_atom]},
        "alignment": {"status": "resolved",
                      "donor_to_current": {anchor: anchor,
                                           new_atom: new_atom},
                      "ref": "align-N"},
        "expectation": {"target_smiles": product}}


NOVEL_O = _novel("CCOO", "O", "SN_O_1", "S_O_1", "donor-novel:1")
NOVEL_C = _novel("CCCO", "C", "SN_C_1", "S_C_1", "donor-novel:2")


def _pool_prepared_id(run_id, spec):
    """镜像 _run_decide 装配口径（chain14 测试 _driver_inputs 同法）。"""
    root_path = stable_id("spath", run_id, "root")
    substrate = build_chemical_state(
        "CCO", "raw_input", [{"record": f"ppv1-substrate:{run_id}"}])
    prepared = prepare_hypothesis(
        dict(spec), parent_path_id=root_path,
        substrate_state=substrate,
        transformation_ref=str(spec.get("transformation_ref") or ""))
    return prepared["hypothesis"].hypothesis_id


def _response(novel_spec, pool_ref_ids, ranked_ids):
    proposals = [{"hypothesis_id": pid} for pid in pool_ref_ids]
    proposals.append({
        "hypothesis_id": "novel:1",
        "proposal_context": {"reference_hypothesis_ids": [],
                              "output_origin": "novel_outside_pool"},
        "reaction_spec": novel_spec})
    return json.dumps({"proposals": proposals,
                       "rank_hypotheses": ranked_ids})


def _run(tmp_path, run_id, response, width=2):
    plan = {"pools": {"CCO": [dict(SPEC_A), dict(SPEC_B)]},
            "model": {"provider_kind": "scripted",
                      "responses": [response]}}
    return start_run(config=resolve_config(),
                     runs_root=tmp_path / "runs", run_id=run_id,
                     smiles="CCO", max_depth=3, max_expansions=10,
                     max_frontier_width=width, finder=object(),
                     scripted=True,
                     profile=PROFILE_POLLUTANT_PATHWAY_V1,
                     ppv1_plan=plan)


def _entries(tmp_path, run_id):
    db = tmp_path / "runs" / run_id / "pollutant.sqlite"
    conn = sqlite3.connect(str(db))
    out = {}
    for aid, kind, status, payload in conn.execute(
            "SELECT action_id, action_kind, status, payload "
            "FROM search_actions"):
        try:
            p = json.loads(payload)
        except Exception:
            continue
        if isinstance(p, dict) and "logical_proposal_id" in p:
            out[p["logical_proposal_id"]] = p
    conn.close()
    return out


def _decide_dedup(tmp_path, run_id):
    for f in (tmp_path / "runs" / run_id / "results").glob(
            "soutc_*/expansion_outcome.json"):
        d = json.loads(f.read_text())
        payload = d.get("payload") or {}
        o = payload.get("outcome") or {}
        if not isinstance(o, dict):
            continue
        model = (o.get("detail") or {}).get("model") or {}
        if "dedup_rejections" in model:
            return model["dedup_rejections"]
    return []


def test_fx1_unranked_survivor_inherits_rank(tmp_path) -> None:
    """fx1（风险形态）：首位 novel 折叠进无位次池条目 B ⇒ B 继承
    位次 1 并第一执行（v1 该反应殿后——回归目标）。"""
    run_id = "tf-fix-fx1"
    a_id = _pool_prepared_id(run_id, SPEC_A)
    resp = _response(NOVEL_O, [a_id], ["novel:1", a_id])  # B 不排名
    _run(tmp_path, run_id, resp)
    e = _entries(tmp_path, run_id)
    assert set(e) == {"A", "B"}                       # novel:1 被折叠
    assert e["B"]["model_rank"] == 1                  # 继承 novel 位次
    assert e["B"]["model_rank_inherited_from"] == "novel:1"
    assert e["B"]["rank_basis"] == "model_selection"
    assert e["B"]["effective_rank"] == 1              # 模型首位先执行
    assert e["A"]["model_rank"] == 2
    assert e["A"]["effective_rank"] == 2
    dd = _decide_dedup(tmp_path, run_id)
    assert len(dd) == 1
    assert dd[0]["logical_proposal_id"] == "novel:1"
    assert dd[0]["merged_into"] == "B"
    assert dd[0]["folded_model_rank"] == 1
    assert dd[0]["rank_inherited"] is True


def test_fold_survivor_better_rank_not_inherited(tmp_path) -> None:
    """幸存者 B 自身位次 2 优于被折叠 novel 的 3 ⇒ 不继承、保留 2。"""
    run_id = "tf-fix-keep"
    a_id = _pool_prepared_id(run_id, SPEC_A)
    b_id = _pool_prepared_id(run_id, SPEC_B)
    resp = _response(NOVEL_O, [a_id, b_id],
                     [a_id, b_id, "novel:1"])      # novel 排第 3
    _run(tmp_path, run_id, resp)
    e = _entries(tmp_path, run_id)
    assert set(e) == {"A", "B"}
    assert e["B"]["model_rank"] == 2                # 保留自己的更优位次
    assert e["B"]["model_rank_inherited_from"] is None
    assert e["B"]["rank_basis"] == "model_selection"
    dd = _decide_dedup(tmp_path, run_id)
    assert dd[0]["folded_model_rank"] == 3
    assert dd[0]["rank_inherited"] is False


def test_fx2_folded_better_rank_inherits(tmp_path) -> None:
    """fx2 变体：B 声明位次 2、被折叠 novel 位次 1 ⇒ B 继承 1。"""
    run_id = "tf-fix-fx2"
    b_id = _pool_prepared_id(run_id, SPEC_B)
    resp = _response(NOVEL_O, [b_id], ["novel:1", b_id])
    _run(tmp_path, run_id, resp)
    e = _entries(tmp_path, run_id)
    assert e["B"]["model_rank"] == 1
    assert e["B"]["model_rank_inherited_from"] == "novel:1"
    assert e["A"]["rank_basis"] == "deterministic_fallback"


def test_fx3_no_fold_baseline_unchanged(tmp_path) -> None:
    """fx3 基线：novel 签名互异不折叠 ⇒ 位次直达、无继承字段。"""
    run_id = "tf-fix-fx3"
    a_id = _pool_prepared_id(run_id, SPEC_A)
    resp = _response(NOVEL_C, [a_id], ["novel:1", a_id])
    _run(tmp_path, run_id, resp)
    e = _entries(tmp_path, run_id)
    assert set(e) == {"A", "B", "novel:1"}
    assert e["novel:1"]["model_rank"] == 1
    assert e["novel:1"]["effective_rank"] == 1
    assert e["novel:1"]["model_rank_inherited_from"] is None
    assert e["A"]["model_rank"] == 2
    assert e["B"]["rank_basis"] == "deterministic_fallback"
    assert _decide_dedup(tmp_path, run_id) == []
