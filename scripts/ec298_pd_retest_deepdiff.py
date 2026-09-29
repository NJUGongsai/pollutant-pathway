"""EC298 Phase D retest — per-question layered difference analysis (zero LLM).

Mines the sealed run artifacts of both arms (decision / validation /
report_adjudication / prediction artifacts) and emits, per qid, the layered
trace the retest task §5.4 requires:

  L1 D1 new recall      : n_similar_channel_refs, similar-channel donor
                          evals (similarity/rank), displaced_by_similar_channel,
                          budget_not_assessed;
  L2 donor evaluation   : donor_evals statuses and reject reasons;
  L3 eligibility        : analogy_eligibility status / fallback / selected;
  L4 routing            : decision outcome + prediction_mode;
  L5 validation         : validation.json state / rejection reasons;
  L6 report             : report_adjudication.json products[reportable]:
                          evidence ids, first rank/card_kind/product,
                          n_reportable (must be <= 5 per step).

Read-only over run dirs; no gold, no network, no LLM.

Usage (Chenyu):
  OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
      scripts/ec298_pd_retest_deepdiff.py \
      --c0-root runs/ec298_pd_retest_C0 --d3-root runs/ec298_pd_retest_D3 \
      --out-dir reports/phase_d/retest/scoring
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _decisions(run_dir: Path) -> list[dict]:
    """All decision payloads of a run, ordered by created_at."""
    out = []
    results = run_dir / "results"
    if not results.is_dir():
        return out
    for t in sorted(results.iterdir()):
        dp = t / "decision.json"
        if not dp.is_file():
            continue
        env = _load_json(dp)
        if not env:
            continue
        p = env.get("payload") or {}
        p["_task_id"] = t.name
        out.append(p)
    out.sort(key=lambda p: str(p.get("created_at", "")))
    return out


def _mine_run(run_dir: Path) -> dict:
    """Compact per-run trace across the six layers (defensive to shape)."""
    trace = {
        "n_decision_tasks": 0,
        "outcome": "", "prediction_mode": "", "prediction_reason": "",
        "eligibility_status": "", "eligibility_fallback": "",
        "eligibility_selected_evidence_id": "",
        "eligibility_selected_record_id": "",
        "eligibility_selected_similarity": None,
        "n_similar_channel_refs": 0, "n_cards": 0, "n_donor_evals": 0,
        "n_donor_evals_ok": 0, "n_donor_evals_rejected": 0,
        "n_budget_not_assessed": 0, "n_displaced_by_similar": 0,
        "similar_donor_records": [],
        "donor_reject_reasons": [],
        "validation_state": "", "validation_reject_reasons": [],
        "report_evidence_ids": [], "report_first_rank": None,
        "report_first_card_kind": None, "report_first_product": None,
        "n_report_products": 0, "n_adjudication_products_total": 0,
        "prediction_outcome": "", "prediction_parsed": None,
    }
    decs = _decisions(run_dir)
    trace["n_decision_tasks"] = len(decs)
    last = decs[-1] if decs else {}
    trace["outcome"] = last.get("outcome", "")
    trace["prediction_mode"] = last.get("prediction_mode", "")
    trace["prediction_reason"] = str(last.get("prediction_reason", ""))[:300]
    elig = last.get("analogy_eligibility") or {}
    trace["eligibility_status"] = elig.get("status", "")
    trace["eligibility_fallback"] = elig.get("fallback_reason", "")
    sel = elig.get("selected") or {}
    trace["eligibility_selected_evidence_id"] = sel.get("evidence_id", "")
    trace["eligibility_selected_record_id"] = sel.get("record_id", "")
    trace["eligibility_selected_similarity"] = sel.get("similarity")
    trace["n_similar_channel_refs"] = elig.get("n_similar_channel_refs", 0) or 0
    cards = elig.get("cards") or []
    trace["n_cards"] = len(cards)
    for card in cards:
        trace["n_budget_not_assessed"] += int(
            card.get("n_budget_not_assessed") or 0)
        for de in card.get("donor_evals") or []:
            trace["n_donor_evals"] += 1
            if de.get("status") == "ok":
                trace["n_donor_evals_ok"] += 1
            else:
                trace["n_donor_evals_rejected"] += 1
                for r in de.get("reject_reasons") or []:
                    trace["donor_reject_reasons"].append(str(r))
            if de.get("similarity") is not None:
                trace["similar_donor_records"].append({
                    "record_id": de.get("record_id"),
                    "similarity": de.get("similarity"),
                    "similarity_rank": de.get("similarity_rank"),
                    "status": de.get("status"),
                })
    trace["n_displaced_by_similar"] = len(
        elig.get("displaced_by_similar_channel") or [])

    results = run_dir / "results"
    if results.is_dir():
        for t in sorted(results.iterdir()):
            vp = t / "validation.json"
            if vp.is_file():
                v = (_load_json(vp) or {}).get("payload") or {}
                trace["validation_state"] = v.get("state", "")
                for r in v.get("reject_reasons") or []:
                    trace["validation_reject_reasons"].append(str(r))
            rp = t / "report_adjudication.json"
            if rp.is_file():
                r = (_load_json(rp) or {}).get("payload") or {}
                # v2 adjudication schema: products[] with reportable flag;
                # reportable items carry report_rank/evidence_id/card_kind.
                # (report/entries does not exist — the old reading left the
                # report layer empty and counted all candidates, not the
                # reportable subset.)
                rep = [x for x in r.get("products") or []
                       if x.get("reportable")]
                rep.sort(key=lambda x: (x.get("report_rank") is None,
                                        x.get("report_rank") or 0))
                trace["report_evidence_ids"] = [
                    x.get("evidence_id") for x in rep]
                trace["n_report_products"] = len(rep)
                trace["n_adjudication_products_total"] = len(
                    r.get("products") or [])
                if rep:
                    trace["report_first_rank"] = rep[0].get("report_rank")
                    trace["report_first_card_kind"] = rep[0].get("card_kind")
                    trace["report_first_product"] = rep[0].get(
                        "product_smiles_full")
            pp = t / "prediction.json"
            if pp.is_file():
                pr = (_load_json(pp) or {}).get("payload") or {}
                trace["prediction_outcome"] = pr.get("outcome", "")
                trace["prediction_parsed"] = pr.get("parsed_present")
    return trace


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--c0-root", required=True)
    ap.add_argument("--d3-root", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    out_dir = Path(a.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    def _arm(root_s: str, label: str) -> dict:
        root = Path(root_s).resolve()
        meta = json.loads(
            (root / "merged" / "export_metadata.json").read_text(
                encoding="utf-8"))
        per_route = {pr["route_id"]: pr for pr in meta.get("per_route") or []}
        traces = {}
        for qid, pr in per_route.items():
            run_id = pr.get("run_id") or ""
            run_dir = root / "runs" / run_id
            traces[qid] = _mine_run(run_dir) if run_id and run_dir.is_dir() \
                else {"mined": False}
        return {"root": str(root), "per_route": per_route, "traces": traces,
                "label": label}

    c0 = _arm(a.c0_root, "C0")
    d3 = _arm(a.d3_root, "D3")
    qids = sorted(c0["traces"])
    rows = []
    for qid in qids:
        t0, t3 = c0["traces"].get(qid, {}), d3["traces"].get(qid, {})
        row = {"qid": qid}
        for label, t in (("c0", t0), ("d3", t3)):
            for k, v in t.items():
                if k in ("similar_donor_records", "donor_reject_reasons",
                         "validation_reject_reasons", "report_evidence_ids"):
                    row[f"{label}_{k}"] = v[:10]
                else:
                    row[f"{label}_{k}"] = v
        # layer deltas
        row["d1_new_recall_refs"] = int(
            row.get("d3_n_similar_channel_refs", 0) or 0) - int(
            row.get("c0_n_similar_channel_refs", 0) or 0)
        row["donor_evals_delta"] = int(
            row.get("d3_n_donor_evals", 0) or 0) - int(
            row.get("c0_n_donor_evals", 0) or 0)
        row["eligibility_changed"] = (
            row.get("c0_eligibility_status", "") !=
            row.get("d3_eligibility_status", "")
            or row.get("c0_eligibility_fallback", "") !=
            row.get("d3_eligibility_fallback", ""))
        row["route_changed"] = (
            row.get("c0_prediction_mode", "") !=
            row.get("d3_prediction_mode", "")
            or row.get("c0_outcome", "") != row.get("d3_outcome", ""))
        row["similar_selected_d3_only"] = bool(
            (row.get("d3_eligibility_selected_evidence_id") or "")
            == "reactant_similar_channel"
            and (row.get("c0_eligibility_selected_evidence_id") or "")
            != "reactant_similar_channel")
        rows.append(row)

    summary = {
        "schema_version": "ec298-pd-retest-deepdiff-2",
        "n_questions": len(rows),
        "n_c0_similar_channel_engaged": sum(
            1 for r in rows if (r.get("c0_n_similar_channel_refs") or 0) > 0),
        "n_d3_similar_channel_engaged": sum(
            1 for r in rows if (r.get("d3_n_similar_channel_refs") or 0) > 0),
        "n_d1_new_recall_questions": sum(
            1 for r in rows if (r.get("d1_new_recall_refs") or 0) > 0),
        "n_similar_selected_d3_only": sum(
            1 for r in rows if r.get("similar_selected_d3_only")),
        "n_eligibility_changed": sum(
            1 for r in rows if r.get("eligibility_changed")),
        "n_route_changed": sum(1 for r in rows if r.get("route_changed")),
        "report_layer": {
            label: {
                "n_questions_with_reportable": sum(
                    1 for r in rows
                    if (r.get(f"{label}_n_report_products") or 0) > 0),
                "max_n_report_products": max(
                    (r.get(f"{label}_n_report_products") or 0)
                    for r in rows),
                "n_report_products_over_5": sum(
                    1 for r in rows
                    if (r.get(f"{label}_n_report_products") or 0) > 5),
                "caliber": "report_adjudication.json "
                           "products[reportable=true]; report_rank ordered",
            }
            for label in ("c0", "d3")},
        "layer_note": ("layers are descriptive; similarity/applicable gains "
                       "are not hit evidence; single-model samples do not "
                       "prove deterministic causation"),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (out_dir / "deepdiff_298.json").write_text(
        json.dumps({"summary": summary, "per_question": rows},
                   ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
