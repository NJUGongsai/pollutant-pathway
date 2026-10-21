#!/usr/bin/env python3
"""T-H Top3 levers: read-only per-qid metadata extractor (HPC side).

Reads the sealed batch + run exports (read-only) and re-runs the frozen
evaluator in-process to recover matched event IDs. Emits metadata only:
no gold structures, no candidate/substrate SMILES, no reaction specs.
Writes only to the analysis directory given by --out.
"""
import argparse
import json
import os
import sys
from pathlib import Path

CODE_SRC = os.environ.get(
    "V43_SRC", "/work/home/aclhl3hbth/EnzymeAgent/v43cTH/src")
sys.path.insert(0, CODE_SRC)
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from pathway_v43.pollutant.evaluation import (  # noqa: E402
    _CRITERIA_V2_IDENTITIES, PPV1_CRITERIA_V2, PPV1_EVALUATION_VERSION,
    _event_payload_body, _export_states, evaluate_participant_exemption,
    evaluate_scientific)
from pathway_v43.pollutant.profile import (  # noqa: E402
    PPV1_NATIVE_EXPORT_VERSION, PPV1_PROFILE_SCHEMA_VERSION)
from pathway_v43.pollutant.reference_graph import (  # noqa: E402
    load_reference_graph)
from pathway_v43.pollutant.s5b_scoring import (  # noqa: E402
    _batch_export_reader, _candidate_events, _paired_payload, _read_case,
    _root_strict_states, normalize_preregistration)


def _event_participants(event):
    body = event.get("payload")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except (ValueError, TypeError):
            body = {}
    return list((body or {}).get("participants") or [])


def _role_counts(participants, sides=None):
    out = {}
    for p in participants:
        if not isinstance(p, dict):
            continue
        side = str(p.get("side") or "")
        if sides and side not in sides:
            continue
        key = f"{side}:{p.get('role') or ''}"
        out[key] = out.get(key, 0) + 1
    return out


def _origin_channel(origin_group_key, logical_key):
    og = str(origin_group_key or "")
    lk = str(logical_key or "")
    if lk.startswith("novel") or (not og and lk):
        return "novel"
    if og.startswith("rec-source:"):
        return "recorded"
    if og.startswith("analog-template:"):
        return "analog"
    if og:
        return og.split(":", 1)[0]
    return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-root", required=True)
    ap.add_argument("--runs-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--qids", default="")
    args = ap.parse_args()

    batch_root = Path(args.batch_root)
    runs_root = Path(args.runs_root)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(
        (batch_root / "batch_manifest.json").read_text(encoding="utf-8"))
    split_manifest = json.loads(
        (batch_root / "split_manifest.json").read_text(encoding="utf-8"))
    order = [str(q) for q in manifest.get("registration_order") or []]
    if args.qids:
        keep = {q.strip() for q in args.qids.split(",") if q.strip()}
        order = [q for q in order if q in keep]
    entries = {str(e["qid"]): e for e in manifest.get("entries") or []}

    graphs = {}
    graph_by_qid = {}
    for qid in order:
        entry = entries[qid]
        graph = load_reference_graph(batch_root / str(entry["graph_rel"]))
        graphs[graph["reference_graph_id"]] = graph
        graph_by_qid[qid] = graph["reference_graph_id"]

    exports = []
    cases = {}
    for qid in order:
        case = _read_case(batch_root, qid)
        cases[qid] = case
        digest = str((case or {}).get("export_digest") or "")
        run_id = str((entries[qid] or {}).get("run_id") or "")
        if digest and run_id:
            exports.append({
                "run_id": run_id, "export_digest": digest, "qid": qid,
                "lossy_projection": False,
            })

    prereg_path = batch_root / "preregistration_approval.json"
    prereg = json.loads(prereg_path.read_text(encoding="utf-8")) \
        if prereg_path.is_file() else None

    export_payloads = {}
    reader = _batch_export_reader(runs_root, export_payloads)
    evaluation_input = {
        "evaluator_schema_version": PPV1_EVALUATION_VERSION,
        "run_identity": {
            "run_id": f"s5b-batch:{manifest.get('batch_tag') or 's5b'}",
            "profile_version": PPV1_PROFILE_SCHEMA_VERSION,
            "export_schema_version": PPV1_NATIVE_EXPORT_VERSION,
        },
        "native_path_exports": exports,
        "reference_graph_manifest": [
            {"reference_graph_id": graphs[graph_by_qid[qid]]
             ["reference_graph_id"],
             "sha256": str(entries[qid]["graph_sha256"]),
             "domain": "298",
             "track": "known_evidence_reconstruction",
             "qid": qid}
            for qid in order],
        "split_manifest": split_manifest,
        "domain": "298",
        "track": "known_evidence_reconstruction",
        "metric_policy_version": "ppv1-evaluation-metrics-proposed",
        "preregistration_id": str(
            (prereg or {}).get("preregistration_id")
            or "prereg-s5b-pending"),
        "scoring_policy_version": "ppv1-evaluation-scoring-proposed",
        "missingness_policy_version":
            "ppv1-evaluation-missingness-proposed",
        "data_scope": "real",
        "interface_verification": False,
        "model_provider_policy": {
            "provider_kind": "real",
            "authorization": str(
                (prereg or {}).get("user_authorization")
                or "s5b-launch-authorized-by-user-2026-10-09"),
        },
    }
    output = evaluate_scientific(
        evaluation_input, reference_graphs=graphs,
        native_export_reader=reader,
        preregistration=normalize_preregistration(prereg),
        criteria_version=PPV1_CRITERIA_V2)
    sample_by_graph = {
        str(s.get("reference_graph_id")): s
        for s in output.get("sample_results") or []}

    per_qid = []
    for qid in order:
        graph = graphs[graph_by_qid[qid]]
        sample = sample_by_graph.get(graph_by_qid[qid]) or {}
        payload = _paired_payload(export_payloads, sample)
        root_states = _root_strict_states(sample, graph) if sample else set()
        candidates = _candidate_events(payload, root_states)
        edge_matches = sample.get("predicted_edge_matches") or []
        edge = edge_matches[0] if edge_matches else {}
        matched_ids = [str(e.get("event_id"))
                       for e in (edge.get("matched_events") or [])]
        rank = None
        for pos, cand in enumerate(candidates, 1):
            if cand["event_id"] in matched_ids:
                rank = pos
                break

        events = {str(e.get("event_id")): e
                  for e in payload.get("events") or []}
        hyps = {str(h.get("hypothesis_id")): (h.get("payload") or {})
                for h in payload.get("hypotheses") or []}
        expand_by_hyp = {}
        for action in payload.get("search_actions") or []:
            if str(action.get("action_kind")) != "expand_hypothesis":
                continue
            body = action.get("payload") or {}
            prepared = str(body.get("prepared_hypothesis_id") or "")
            if prepared:
                expand_by_hyp[prepared] = {
                    "action_status": str(action.get("status") or ""),
                    "logical_proposal_id": str(
                        body.get("logical_proposal_id") or ""),
                    "hypothesis_key": str(body.get("hypothesis_key") or ""),
                    "model_rank": body.get("model_rank"),
                    "effective_rank": body.get("effective_rank"),
                    "rank_basis": str(body.get("rank_basis") or ""),
                    "model_rank_inherited_from": body.get(
                        "model_rank_inherited_from"),
                    "rank_policy_version": str(
                        body.get("rank_policy_version") or ""),
                    "action_created_at": str(
                        action.get("created_at") or ""),
                }
        decide_models = []
        dedup_rejections = []
        for outcome in payload.get("expansion_outcomes") or []:
            detail = ((outcome.get("outcome_payload") or {}).get(
                "outcome") or {}).get("detail") or {}
            model = detail.get("model")
            if isinstance(model, dict):
                decide_models.append({
                    "network_request_count": model.get(
                        "network_request_count"),
                    "abstained": model.get("abstained"),
                    "model_rank_by_id": model.get("model_rank_by_id") or {},
                })
                dedup_rejections.extend(
                    model.get("dedup_rejections") or [])

        event_rows = []
        for cand in candidates:
            event = events.get(cand["event_id"]) or {}
            hyp_id = str(event.get("hypothesis_id") or "")
            exp = expand_by_hyp.get(hyp_id) or {}
            hyp = hyps.get(hyp_id) or {}
            logical = str(exp.get("logical_proposal_id") or "")
            origin = str(hyp.get("origin_group_key") or "")
            event_rows.append({
                "event_id": cand["event_id"],
                "created_at": cand["created_at"],
                "hypothesis_id": hyp_id,
                "logical_proposal_id": logical,
                "channel": _origin_channel(origin, logical),
                "origin_prefix": origin.split(":", 1)[0] if origin else "",
                "model_rank": exp.get("model_rank"),
                "effective_rank": exp.get("effective_rank"),
                "rank_basis": exp.get("rank_basis"),
                "inherited_from": exp.get("model_rank_inherited_from"),
                "step_scope": hyp.get("step_scope"),
                "participant_list_status": hyp.get(
                    "participant_list_status"),
                "participant_roles": _role_counts(
                    event.get("payload", {}).get("participants")
                    if isinstance(event.get("payload"), dict) else []),
                "is_matched": cand["event_id"] in matched_ids,
            })

        node_rows = []
        for node in sample.get("predicted_node_matches") or []:
            node_rows.append({
                "node_id": str(node.get("node_id")),
                "role": str(node.get("role") or ""),
                "reference_identity_scope": str(
                    node.get("reference_identity_scope") or ""),
                "match_status": str(node.get("match_status") or ""),
                "n_matched_state_ids": len(
                    node.get("matched_state_ids") or []),
                "n_cn_only_state_ids": len(
                    node.get("cn_only_state_ids") or []),
                "identity_scope_cap": bool(node.get("identity_scope_cap")),
            })
        states = _export_states(payload)
        family_by_cn = _CRITERIA_V2_IDENTITIES.get("family_by_cn") or {}
        node_by_id = {str(n.get("node_id")): n
                      for n in graph.get("nodes") or []}
        graph_edge = {}
        for ge in graph.get("edges") or []:
            if str(ge.get("edge_id")) == str(edge.get("edge_id")):
                graph_edge = ge
                break
        edge_node_ids = {str(x) for x in
                         list(graph_edge.get("from_node_ids") or [])
                         + list(graph_edge.get("to_node_ids") or [])}
        required_by_node = {}
        for node in sample.get("predicted_node_matches") or []:
            nid = str(node.get("node_id"))
            if nid in edge_node_ids:
                required_by_node[nid] = set(
                    node.get("matched_state_ids") or [])
        required_states = set().union(*required_by_node.values()) \
            if required_by_node else set()
        coverage_events = []
        for item in edge.get("coverage_mismatch_events") or []:
            event = events.get(str(item.get("event_id"))) or {}
            body = event.get("payload") if isinstance(
                event.get("payload"), dict) else {}
            participants = body.get("participants") or []
            role_by_ref = {str(p.get("state_ref") or ""): {
                "role": str(p.get("role") or ""),
                "side": str(p.get("side") or ""),
            } for p in participants if isinstance(p, dict)}
            refs = {str(x) for x in
                    (item.get("participant_state_refs") or [])}
            extras = sorted(refs - required_states)
            missing = sorted(required_states - refs)
            extra_rows = []
            for ref in extras:
                role = role_by_ref.get(ref, {})
                cn = str((states.get(ref) or {}).get("cn_identity") or "")
                extra_rows.append({
                    "role": role.get("role", ""),
                    "side": role.get("side", ""),
                    "exempt_family": family_by_cn.get(cn, ""),
                })
            missing_roles = []
            for nid, stateset in required_by_node.items():
                if stateset and not (stateset & refs):
                    missing_roles.append(str(
                        (node_by_id.get(nid) or {}).get("role") or ""))
            from_states = set()
            to_states = set()
            for nid in graph_edge.get("from_node_ids") or []:
                from_states.update(required_by_node.get(str(nid), set()))
            for nid in graph_edge.get("to_node_ids") or []:
                to_states.update(required_by_node.get(str(nid), set()))
            exempt = evaluate_participant_exemption(
                payload, _event_payload_body(event), states,
                hypothesis_id=str(event.get("hypothesis_id") or ""),
                from_states=from_states, to_states=to_states)
            coverage_events.append({
                "event_id": str(item.get("event_id")),
                "participant_coverage": str(
                    item.get("participant_coverage") or ""),
                "n_participants": len(refs),
                "n_extra": len(extras),
                "n_missing": len(missing),
                "extras": extra_rows,
                "missing_roles": missing_roles,
                "participant_roles": _role_counts(participants),
                "exempted_participants": len(
                    item.get("exempted_participants") or []),
                "t1_review": {
                    "eligible": bool(exempt.get("eligible")),
                    "all_exempt": bool(exempt.get("all_exempt")),
                    "declaration_status": exempt.get(
                        "declaration_status"),
                    "element_accounts": exempt.get("element_accounts"),
                    "occurrences": [{
                        "side": str(o.get("side") or ""),
                        "role": str(o.get("role") or ""),
                        "exempt_family": o.get("exempt_family"),
                        "tier": str(o.get("tier") or ""),
                        "pred1": o.get("pred1_record_declared"),
                        "pred2": o.get("pred2_element_traceable"),
                        "pred3": o.get("pred3_cn_identity_member"),
                    } for o in exempt.get("occurrences") or []],
                },
            })

        per_qid.append({
            "qid": qid,
            "run_id": str(entries[qid].get("run_id") or ""),
            "pool_size": entries[qid].get("pool_size"),
            "scoring_status": str(sample.get("scoring_status") or ""),
            "scoring_error_kinds": [
                str(e.get("kind")) for e in
                (sample.get("scoring_errors") or [])][:4],
            "edge_status": str(edge.get("match_status") or ""),
            "rank": rank,
            "n_candidate_events": len(candidates),
            "n_matched_events": len(matched_ids),
            "matched_event_not_in_candidates": bool(
                matched_ids and rank is None),
            "matched_event_ids": matched_ids,
            "candidate_events": event_rows,
            "decide_model_rank_by_id": (
                decide_models[0]["model_rank_by_id"] if decide_models else {}),
            "dedup_rejections": dedup_rejections,
            "node_matches": node_rows,
            "required_node_gaps": [
                {"node_id": str(g.get("node_id")),
                 "side": str(g.get("side")),
                 "node_match_status": str(
                     g.get("node_match_status") or "")}
                for g in edge.get("required_node_gaps") or []],
            "coverage_mismatch_events": coverage_events,
            "endpoint_stop_reason": str(
                ((payload.get("endpoint_record") or {}).get(
                    "search_stop_reason") or {}).get("primary") or ""),
        })

    result = {
        "note": ("T-H Top3 levers read-only metadata; no SMILES/gold "
                 "structures emitted; evaluator re-run in-process with "
                 "frozen code + criteria v2"),
        "n_qids": len(per_qid),
        "evaluator_status": str(output.get("status") or ""),
        "per_qid": per_qid,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    print(f"WROTE {out_path} n={len(per_qid)}")


if __name__ == "__main__":
    main()
