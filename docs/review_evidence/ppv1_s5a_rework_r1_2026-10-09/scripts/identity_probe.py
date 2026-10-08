"""S5A-01/03 反例复现探针(复制自评审 identity/scripts/identity_probe.py 与
required_node_probe.py,仅改 ROOT/sys.path 指向当前仓;fresh tmp 执行)。

观察面(不改变任何产品行为):
- 六 scope 分案:reference_intermediates_{cn_only,partial,unknown} 与
  reference_all_{cn_only,partial,unknown}(内容严格相等的参考节点声明
  有限 scope 时是否仍授 strict_structure / matched_strict 边 / 聚合);
- strict_mismatch_isotope/charge 与 stereo 单元控制(应保持 cn_only);
- 必要节点两核心案(reactant/product + unmatched_structure)与
  limited_duplicate 变体、participants-only 变体(P2 观察)。
"""
from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path("/Volumes/CC/Enzyme_Agent/dependingv43")
ROOT = Path(__file__).resolve().parents[1]          # .../before 或 .../after
OUT = ROOT / "probe" / "outputs"
OUT.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(REPO / "tests"), str(REPO / "src")]

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.workflow.runner import start_run  # noqa: E402
from pathway_v43.storage.run_identity import (  # noqa: E402
    PROFILE_POLLUTANT_PATHWAY_V1,
)
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    evaluate_scientific,
    match_reference_nodes,
    native_export_reader_from_ledger,
)
from pathway_v43.pollutant.reference_graph import (  # noqa: E402
    validate_reference_graph,
)
from pathway_v43.pollutant import preregistration  # noqa: E402
from pathway_v43.pollutant.search import SearchLedger  # noqa: E402
from pathway_v43.pollutant.store import PollutantPathwayStore  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402
from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.pollutant.chemstate import strict_identity_of  # noqa: E402
from test_ppv1_s5a_schema import (  # noqa: E402
    synth_evaluation_input,
    synth_reference_graph,
)
from test_ppv1_s4a_endpoint import spec  # noqa: E402


def save(name: str, obj) -> None:
    (OUT / name).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def snapshot(db: Path) -> dict:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    schema = [dict(row) for row in conn.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "ORDER BY type,name")]
    tables = {}
    for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "ORDER BY name"):
        name = row["name"]
        q = 'SELECT * FROM "' + name.replace('"', '""') + '"'
        rows = [dict(r) for r in conn.execute(q)]
        tables[name] = sorted(
            rows, key=lambda r: json.dumps(r, sort_keys=True))
    conn.close()
    return {"schema": schema, "tables": tables,
            "sha256": hashlib.sha256(db.read_bytes()).hexdigest()}


def create(name: str, scope: str = "net_reaction"):
    runid = "review-identity-" + name
    runs = ROOT / "runs" / name
    plan = {
        "condition_facts": [{
            "key": "oxygen_regime", "value": "aerobic",
            "status": "known_present", "source_ref": "src:synthetic"}],
        "pools": {"CCO": [
            spec("B", "CC=O", "donor-B", coproducts=["[H][H]"],
                 step_scope=scope),
            spec("C", "CC=O", "donor-C", step_scope=scope)]},
        "schedule_budget": {"max_select": 2},
        "endpoint_evidence": [],
    }
    out = start_run(
        config=resolve_config(), runs_root=runs, run_id=runid,
        smiles="CCO", max_depth=3, max_expansions=10,
        max_frontier_width=2, finder=object(), scripted=True,
        profile=PROFILE_POLLUTANT_PATHWAY_V1, ppv1_plan=plan)
    store = PollutantPathwayStore(runs / runid / "pollutant.sqlite")
    artifacts = ArtifactStore(runs, runid)
    ledger = SearchLedger(store, artifacts, runid)
    reader = native_export_reader_from_ledger(ledger, runs / runid)
    entry = {"run_id": runid,
             "export_digest": out["native_export"]["export_digest"]}
    before = snapshot(runs / runid / "pollutant.sqlite")
    native = reader(entry)
    save(name + "_public_run.json", {
        "plan": plan, "start_output": out, "native_export": native,
        "database_after_start": before})
    return runid, runs, entry, reader, before


runs = {"known": create("known"), "unknown": create("unknown", "unknown")}


def evaluate(case: str, graph: dict, run: str = "known"):
    runid, runsroot, entry, reader, before = runs[run]
    validate_reference_graph(graph)
    inp = synth_evaluation_input(graphs=[graph], exports=[entry])
    inp["run_identity"]["run_id"] = runid
    output = evaluate_scientific(
        inp, reference_graphs={graph["reference_graph_id"]: graph},
        native_export_reader=reader,
        preregistration=preregistration.build_preregistration_template())
    after = snapshot(runsroot / runid / "pollutant.sqlite")
    assert before == after
    sample = output["sample_results"][0]
    record = {
        "case": case, "run": run, "reference_graph": graph,
        "evaluation_input": inp, "evaluation_output": output,
        "tables_unchanged": before == after,
    }
    save(case + ".json", record)
    return {
        "case": case, "run": run,
        "nodes": {n["node_id"]: {
            "scope": n["reference_identity_scope"],
            "status": n["match_status"],
            "matched_state_ids": n["matched_state_ids"],
            "cn_only_state_ids": n["cn_only_state_ids"]}
            for n in sample["predicted_node_matches"]},
        "edges": {e["edge_id"]: {
            "status": e["match_status"],
            "matched_events": [x["event_id"]
                               for x in e["matched_events"]],
            "structure_only": [x["event_id"]
                               for x in e["structure_only_events"]]}
            for e in sample["predicted_edge_matches"]},
        "aggregate_metrics": output["aggregate_metrics"],
        "unknown_partial": sample["unknown_or_partial_summary"],
        "outside_reference": sample["false_or_unverified_edges"],
        "status": output["status"],
        "tables_unchanged": before == after,
    }


summary = []
base = synth_reference_graph()
summary.append(evaluate("strict_control", base))
for scope in ["cn_only", "partial", "unknown"]:
    g = copy.deepcopy(base)
    for n in g["nodes"]:
        if n["role"] == "intermediate":
            n["structure_identity_scope"] = scope
    summary.append(evaluate("reference_intermediates_" + scope, g))
    g = copy.deepcopy(base)
    for n in g["nodes"]:
        n["structure_identity_scope"] = scope
    summary.append(evaluate("reference_all_" + scope, g))
for name, smi in [("isotope", "[13CH3]C=O"), ("charge", "CC=[OH+]")]:
    g = copy.deepcopy(base)
    for n in g["nodes"]:
        if n["role"] == "intermediate":
            n["structure_smiles"] = smi
            n["state_identity"] = "strict:" + smi
    summary.append(evaluate("strict_mismatch_" + name, g))
for scope in ["elementary_step", "multistep_summary", "unknown"]:
    g = copy.deepcopy(base)
    for e in g["edges"]:
        e["step_scope"] = scope
    summary.append(evaluate("scope_known_vs_" + scope, g))
g = copy.deepcopy(base)
for e in g["edges"]:
    e["step_scope"] = "unknown"
summary.append(evaluate("scope_unknown_vs_unknown", g, run="unknown"))

# ---- S5A-03 必要节点(评审 required_node_probe.py 同案构造) ----
runid, runsroot, entry, reader, before = runs["known"]
for side in ["reactant", "product"]:
    for kind in ["unmatched_structure", "limited_duplicate",
                 "inconsistent_participant_nodes"]:
        g = synth_reference_graph()
        e = g["edges"][1]
        if kind == "inconsistent_participant_nodes":
            extra = copy.deepcopy(g["nodes"][3])
            extra.update(node_id="n-required-missing",
                         structure_smiles="C", state_identity="strict:C",
                         occurrence_id="occ-extra-required",
                         role="coproduct")
            g["nodes"].append(extra)
            e["participants"].append({
                "node_id": extra["node_id"], "side": side,
                "role": "cosubstrate" if side == "reactant"
                else "coproduct", "coefficient": 1,
                "coefficient_status": "known"})
        else:
            existing = g["nodes"][0] if side == "reactant" \
                else g["nodes"][2]
            extra = copy.deepcopy(existing)
            extra.update(node_id="n-required-missing",
                         occurrence_id="occ-extra-required")
            if kind == "unmatched_structure":
                extra.update(structure_smiles="C",
                             state_identity="strict:C")
            else:
                extra.update(structure_identity_scope="cn_only")
            g["nodes"].append(extra)
            e["from_node_ids" if side == "reactant"
              else "to_node_ids"].append(extra["node_id"])
            e["participants"].append({
                "node_id": extra["node_id"], "side": side,
                "role": "cosubstrate" if side == "reactant"
                else "coproduct", "coefficient": 1,
                "coefficient_status": "known"})
        validate_reference_graph(g)
        inp = synth_evaluation_input(graphs=[g], exports=[entry])
        inp["run_identity"]["run_id"] = runid
        out = evaluate_scientific(
            inp, reference_graphs={g["reference_graph_id"]: g},
            native_export_reader=reader,
            preregistration=preregistration
            .build_preregistration_template())
        case = side + "_" + kind
        save("required_node_" + case + ".json", {
            "case": case, "graph": g, "evaluation_input": inp,
            "output": out})
        sample = out["sample_results"][0]
        nodes = sample["predicted_node_matches"]
        edges = sample["predicted_edge_matches"]
        summary.append({
            "case": case,
            "added_node": next(n for n in nodes
                               if n["node_id"] == "n-required-missing"),
            "target_edge": next(
                x for x in edges if x["edge_id"] == "e-alt-2"),
            "aggregate_reference_edges": next(
                x for x in out["aggregate_metrics"]
                if x["metric_id"] == "reference_edge_recall"),
        })

# ---- 立体 CN 单元控制(复用公共 matcher,非 native 公共链) ----
sm = "F[C@@H](Cl)Br"
ref = "F[C@H](Cl)Br"
g = copy.deepcopy(base)
g["nodes"] = copy.deepcopy(base["nodes"][:1])
g["nodes"][0]["structure_smiles"] = ref
g["nodes"][0]["structure_identity_scope"] = "strict_structure"
unit = {"states": [{
    "state_id": "synthetic-stereo-control",
    "payload": {"smiles_isomeric": strict_identity_of(sm),
                "cn_identity": cn_identity(sm)}}]}
result = match_reference_nodes(g, unit)
save("stereo_cn_matcher_unit.json", {
    "classification": "unit-only, not native public chain",
    "reference": g, "payload": unit, "output": result})
assert result[0]["match_status"] == "cn_only"

save("summary.json", summary)
print(json.dumps({
    "case_count": len(summary),
    "scope_limited": [
        {k: r[k] for k in ("case", "nodes", "edges", "status")}
        for r in summary if "reference_" in r["case"]],
    "required_node": [
        {"case": r["case"],
         "added_node_status": r["added_node"]["match_status"],
         "target_edge_status": r["target_edge"]["match_status"]}
        for r in summary if r["case"].endswith((
            "unmatched_structure", "limited_duplicate",
            "inconsistent_participant_nodes"))],
    "unknown_scope": summary[-4],
    "stereo_unit": result,
}, ensure_ascii=False, indent=2))
