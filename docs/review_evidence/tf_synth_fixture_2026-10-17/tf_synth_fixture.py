#!/usr/bin/env python
"""T-F 专项合成验证夹具（2026-10-17，主会话自干版）。

三夹具 + fx1b（cap=1 变体）：
- fx1  风险形态：模型首位 novel 折叠进【无声明位次】的池条目 B（同净反应签名）
- fx1b 同 fx1 但 max_frontier_width=1（观察 deferred 后果）
- fx2  良性对照：幸存池条目 B 有模型声明位次（rank 2）
- fx3  基线：novel 签名互异（不折叠），模型首位直接生效

零模型（scripted 协议）、零金标零题面；产物全落本目录 runs/ 下。
"""
import json, sys, sqlite3, traceback
from pathlib import Path

REPO = Path("/Volumes/CC/Enzyme_Agent/dependingv43")
sys.path.insert(0, str(REPO / "src"))

from pathway_v43.config import resolve_config
from pathway_v43.workflow.runner import start_run
from pathway_v43.storage.run_identity import PROFILE_POLLUTANT_PATHWAY_V1
from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.production import prepare_hypothesis
from pathway_v43.pollutant.s5b_compiler import net_reaction_signature
from pathway_v43.domain.models import stable_id

OUT = Path(__file__).resolve().parent

# ---- 池条目（纯构造，零题面零金标）----
SPEC_A = {  # 产物 CC=O（s3b_r2 spec 模板，已在既有测试证明可用）
    "key": "A", "product_smiles": "CC=O", "coefficient": 1,
    "transformation_ref": "donor-A", "origin_group_key": "donor-A",
    "edits": [{"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1",
               "from_order": "single", "to_order": "double"}],
    "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
    "alignment": {"status": "resolved",
                  "donor_to_current": {"S_C_2": "S_C_2", "S_O_1": "S_O_1"},
                  "ref": "align-A"},
    "expectation": {"target_smiles": "CC=O"}}
SPEC_B = {  # 产物 CCOO（add_atom O 模板，s3b05 novel 同款形状）
    "key": "B", "product_smiles": "CCOO", "coefficient": 1,
    "transformation_ref": "donor-B", "origin_group_key": "donor-B",
    "edits": [{"op": "add_atom", "element": "O",
               "new_atom_id": "SN_O_1", "atom1": "S_O_1"}],
    "donor": {"center_atom_ids": ["S_O_1", "SN_O_1"]},
    "alignment": {"status": "resolved",
                  "donor_to_current": {"S_O_1": "S_O_1", "SN_O_1": "SN_O_1"},
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
                      "donor_to_current": {anchor: anchor, new_atom: new_atom},
                      "ref": "align-N"},
        "expectation": {"target_smiles": product}}

NOVEL_O = _novel("CCOO", "O", "SN_O_1", "S_O_1", "donor-novel:1")  # 同 B 签名
NOVEL_C = _novel("CCCO", "C", "SN_C_1", "S_C_1", "donor-novel:2")  # 互异签名

def pool_prepared_id(run_id, spec):
    """镜像 _run_decide 装配口径（chain14 测试 _driver_inputs 同法）。"""
    root_path = stable_id("spath", run_id, "root")
    substrate = build_chemical_state(
        "CCO", "raw_input", [{"record": f"ppv1-substrate:{run_id}"}])
    prepared = prepare_hypothesis(
        dict(spec), parent_path_id=root_path,
        substrate_state=substrate,
        transformation_ref=str(spec.get("transformation_ref") or ""))
    return prepared["hypothesis"].hypothesis_id

def build_response(pool_ref_ids, novel_spec, ranked_ids):
    proposals = [{"hypothesis_id": pid} for pid in pool_ref_ids]
    proposals.append({
        "hypothesis_id": "novel:1",
        "proposal_context": {"reference_hypothesis_ids": [],
                              "output_origin": "novel_outside_pool"},
        "reaction_spec": novel_spec})
    return json.dumps({"proposals": proposals,
                       "rank_hypotheses": ranked_ids})

def run_fixture(run_id, response, width):
    plan = {"pools": {"CCO": [dict(SPEC_A), dict(SPEC_B)]},
            "model": {"provider_kind": "scripted",
                      "responses": [response]}}
    return start_run(config=resolve_config(), runs_root=OUT / "runs",
                     run_id=run_id, smiles="CCO", max_depth=3,
                     max_expansions=10, max_frontier_width=width,
                     finder=object(), scripted=True,
                     profile=PROFILE_POLLUTANT_PATHWAY_V1,
                     ppv1_plan=plan)

def read_entries(run_id):
    db = OUT / "runs" / run_id / "pollutant.sqlite"
    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT action_id, action_kind, status, payload "
        "FROM search_actions").fetchall()
    entries, actions = [], []
    for aid, kind, status, payload in rows:
        actions.append({"action_id": aid, "kind": kind, "status": status})
        try:
            p = json.loads(payload)
        except Exception:
            continue
        if isinstance(p, dict) and "logical_proposal_id" in p:
            entries.append({
                "action_id": aid, "action_kind": kind, "status": status,
                "logical_proposal_id": p.get("logical_proposal_id"),
                "model_rank": p.get("model_rank"),
                "effective_rank": p.get("effective_rank"),
                "rank_basis": p.get("rank_basis")})
    ev = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.close()
    return {"entries": sorted(entries, key=lambda e: e.get("effective_rank") or 99),
            "n_actions": len(actions), "n_events": ev}

def main():
    result = {"domain": "纯构造合成输入（零金标零题面）",
              "code_head": "(登记见 README)",
              "fixtures": {}}
    # 前置签名核验（折叠前提的代码级证明）
    result["signature_precheck"] = {
        "A": [str(x) for x in net_reaction_signature(SPEC_A)],
        "B_eq_novelO": net_reaction_signature(SPEC_B)
                       == net_reaction_signature(NOVEL_O),
        "C_distinct": net_reaction_signature(NOVEL_C)
                      != net_reaction_signature(SPEC_B)
                      and net_reaction_signature(NOVEL_C)
                      != net_reaction_signature(SPEC_A)}

    fx = {}
    for name, run_id, novel, ranked_pool_key, width in [
            ("fx1", "tf-fx1", NOVEL_O, "A", 2),
            ("fx1b", "tf-fx1b", NOVEL_O, "A", 1),
            ("fx2", "tf-fx2", NOVEL_O, "B", 2),
            ("fx3", "tf-fx3", NOVEL_C, "A", 2)]:
        a_id = pool_prepared_id(run_id, SPEC_A)
        b_id = pool_prepared_id(run_id, SPEC_B)
        pool_refs = {"A": [a_id], "B": [b_id]}[ranked_pool_key]
        ranked = ["novel:1"] + list(pool_refs)
        response = build_response(pool_refs, novel, ranked)
        try:
            out = run_fixture(run_id, response, width)
            summary = {"events": out.get("counts", {}).get("events")}
        except Exception:
            summary = {"error": traceback.format_exc(limit=6)}
        fx[name] = {"run_id": run_id, "width": width,
                    "ranked_ids": ranked,
                    "pool_prepared_ids": {"A": a_id, "B": b_id},
                    "summary": summary,
                    **read_entries(run_id)}
    result["fixtures"] = fx
    out_path = OUT / "tf_fixture_output.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False,
                                   indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
