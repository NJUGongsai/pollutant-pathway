"""EC298 Phase D retest — paired scoring of the C0 / D-3 arms (zero LLM).

Runs AFTER both arms are sealed. Steps (retest task book §5):

1. Pairing-integrity gate first (`v43-pairing-gate-1`): independently re-read
   worker terminal states, merged metadata, per-route answer SHAs for BOTH
   arms. Any violation -> verdict=diagnostic_incomplete (paired numbers are
   then diagnostic only, and the report must say so).
2. Score each arm with the formal `v43-ec298-scorer-2` (exam_v2): both arms
   recompute cn_identity from raw candidate SMILES; the SAME engine-results
   file (SHA-verified) is passed for both scorings (engine background only,
   NOT part of the main pairing).
3. Explicit-qid pairing table, 298 rows: per question both ranks, @1/@3/@5
   hits, first reported product + source, answer kind/stop reason, call /
   retry / orphan counts, usage presence. For each K: both / C0_only /
   D3_only / neither (four cells MUST sum to 298), D-3 win/lose/tie, hit
   counts and percentage-point deltas.

Usage (Chenyu, zero LLM):
  OMP_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
      scripts/ec298_pd_retest_pairing.py \
      --c0-root runs/ec298_pd_retest_C0 --d3-root runs/ec298_pd_retest_D3 \
      --engine-results runs/ec298_pd_retest_engine/engine_results.jsonl \
      --gold <readonly gold questions.jsonl> \
      --out-dir reports/phase_d/retest/scoring
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def _sha256_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _call_stats_for_run(run_dir: Path) -> dict:
    """Per-run call/retry/orphan/usage facts from persisted artifacts."""
    stats = {"issued": 0, "responses": 0, "ok": 0, "failed": 0,
             "orphans": 0, "usage_present": 0, "usage_missing": 0,
             "http429": 0}
    results = run_dir / "results"
    if not results.is_dir():
        return stats
    for task_dir in sorted(results.iterdir()):
        if not task_dir.is_dir():
            continue
        stats["issued"] += len(list(task_dir.glob("prediction_call.*.json")))
        stats["orphans"] += len(list(task_dir.glob("prediction_orphan.*.json")))
        for rp in sorted(task_dir.glob("prediction_response.*.json")):
            stats["responses"] += 1
            try:
                payload = json.loads(
                    rp.read_text(encoding="utf-8")).get("payload", {})
            except Exception:
                stats["failed"] += 1
                continue
            transport = payload.get("transport") or {}
            if payload.get("status") == "ok" and transport.get("ok"):
                stats["ok"] += 1
            else:
                stats["failed"] += 1
            if transport.get("usage"):
                stats["usage_present"] += 1
            else:
                stats["usage_missing"] += 1
            for att in transport.get("http_attempts") or []:
                if att.get("status") == 429:
                    stats["http429"] += 1
    return stats


def _first_reportable_source(run_dir: Path) -> dict | None:
    """First reportable product source from the sealed adjudication artifact.

    The merged export step carries only parent_smiles/predicted_products (no
    source block), so per-question source references are rebuilt from
    results/T_*/report_adjudication.json: products[] filtered by
    reportable=true, ordered by report_rank. Read-only; zero LLM.
    """
    results = run_dir / "results"
    if not results.is_dir():
        return None
    for t in sorted(results.iterdir()):
        rp = t / "report_adjudication.json"
        if not rp.is_file():
            continue
        try:
            payload = json.loads(
                rp.read_text(encoding="utf-8")).get("payload") or {}
        except Exception:
            return None
        rep = [x for x in payload.get("products") or []
               if x.get("reportable")]
        rep.sort(key=lambda x: (x.get("report_rank") is None,
                                x.get("report_rank") or 0))
        if not rep:
            return None
        first = rep[0]
        return {
            "evidence_id": first.get("evidence_id"),
            "kind": first.get("card_kind"),
            "report_rank": first.get("report_rank"),
            "product_smiles_full": first.get("product_smiles_full"),
        }
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--c0-root", required=True)
    ap.add_argument("--d3-root", required=True)
    ap.add_argument("--engine-results", required=True)
    ap.add_argument("--gold", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    from pathway_v43.exam_v2 import score_exam_v2, multicomponent_sensitivity
    from pathway_v43.output.pairing_gate import (
        paired_release_verdict, validate_arm,
    )

    c0_root = Path(a.c0_root).resolve()
    d3_root = Path(a.d3_root).resolve()
    out_dir = Path(a.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    engine_path = Path(a.engine_results).resolve()
    gold_path = Path(a.gold).resolve()

    # ---- 1. integrity gate before reading answers ----
    expected_ids = list(json.loads(
        (c0_root / "input_manifest.json").read_text(
            encoding="utf-8")).get("route_order") or [])
    gate = paired_release_verdict({
        "C0": validate_arm(c0_root, expected_route_ids=expected_ids),
        "D3": validate_arm(d3_root, expected_route_ids=expected_ids),
    })
    (out_dir / "pairing_gate.json").write_text(
        json.dumps(gate, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    print("[gate] verdict:", gate["verdict"],
          "release_eligible:", gate["release_eligible"])
    for label, res in gate["per_arm"].items():
        if not res["ok"]:
            print(f"[gate][{label}] {res['n_violations']} violation(s)")
            for v in res["violations"][:10]:
                print("   -", json.dumps(v, ensure_ascii=False)[:200])

    engine_sha = _sha256_file(engine_path)
    gold_sha = _sha256_file(gold_path)

    # ---- 2. score both arms with scorer-2, same engine file ----
    scores = {}
    for label, root in (("C0", c0_root), ("D3", d3_root)):
        pred_path = root / "merged" / "predictions.jsonl"
        inputs_sha = {
            "agent_predictions": _sha256_file(pred_path),
            "engine_results": engine_sha,
            "gold_questions": gold_sha,
        }
        v2 = score_exam_v2(
            agent_predictions_path=str(pred_path),
            engine_results_path=str(engine_path),
            gold_questions_path=str(gold_path),
            out_path=out_dir / f"score_v2_{label}.json",
            inputs_sha=inputs_sha)
        multicomponent_sensitivity(
            agent_predictions_path=str(pred_path),
            engine_results_path=str(engine_path),
            gold_questions_path=str(gold_path),
            out_path=out_dir / f"multicomponent_sensitivity_{label}.json")
        scores[label] = v2
        s = v2["summary"]
        print(f"[{label}] agent hit@1/3/5:",
              [s["agent"]["hit@1"], s["agent"]["hit@3"], s["agent"]["hit@5"]])

    # ---- 3. explicit-qid pairing (298 rows) ----
    rank_c0 = {q["qid"]: q for q in scores["C0"]["per_question"]}
    rank_d3 = {q["qid"]: q for q in scores["D3"]["per_question"]}
    merged = {
        label: {r["route_id"]: r for r in _load_jsonl(
            root / "merged" / "predictions.jsonl")}
        for label, root in (("C0", c0_root), ("D3", d3_root))}
    meta = {
        label: {pr["route_id"]: pr for pr in json.loads(
            (root / "merged" / "export_metadata.json").read_text(
                encoding="utf-8")).get("per_route") or []}
        for label, root in (("C0", c0_root), ("D3", d3_root))}
    runs_roots = {"C0": c0_root / "runs", "D3": d3_root / "runs"}

    def _qid_set(merged_rows):
        return list(merged_rows)

    qids = expected_ids or _qid_set(merged["C0"])
    if len(qids) != 298:
        raise SystemExit(f"expected 298 qids, got {len(qids)}")

    def _hit(rec, k):
        return rec is not None and rec["agent_rank"] is not None \
            and rec["agent_rank"] <= k

    rows = []
    quadrant = {k: {"both": 0, "C0_only": 0, "D3_only": 0, "neither": 0}
                for k in (1, 3, 5)}
    win_lose = {k: {"win": 0, "lose": 0, "tie": 0} for k in (1, 3, 5)}
    source_filled = {"C0": 0, "D3": 0}
    source_mismatch = {"C0": 0, "D3": 0}
    for qid in qids:
        rc0, rd3 = rank_c0.get(qid), rank_d3.get(qid)
        row = {"qid": qid}
        for label, rec in (("C0", rc0), ("D3", rd3)):
            row[f"{label}_rank"] = rec["agent_rank"] if rec else None
            row[f"{label}_n_predicted"] = rec["n_predicted"] if rec else None
            for k in (1, 3, 5):
                row[f"{label}_hit@{k}"] = _hit(rec, k)
            pr = meta[label].get(qid) or {}
            row[f"{label}_answer_kind"] = pr.get("answer_kind")
            row[f"{label}_stop_reason"] = pr.get("stop_reason")
            row[f"{label}_route_state"] = pr.get("route_state")
            row[f"{label}_failure_reason"] = pr.get("failure_reason")
            mrow = merged[label].get(qid) or {}
            steps = mrow.get("steps") or []
            prods = (steps[0].get("predicted_products")
                     if steps else None) or []
            row[f"{label}_first_product"] = prods[0] if prods else ""
            run_id = pr.get("run_id") or ""
            # First-product source: merged steps carry no source field —
            # rebuild from the sealed adjudication artifact (reportable,
            # report_rank ordering) and cross-check against the merged
            # first product so the reference is provably about the same
            # product.
            src = _first_reportable_source(
                runs_roots[label] / run_id) if run_id else None
            row[f"{label}_first_source_evidence_id"] = (
                src or {}).get("evidence_id")
            row[f"{label}_first_source_kind"] = (src or {}).get("kind")
            row[f"{label}_first_source_report_rank"] = (
                src or {}).get("report_rank")
            if src is not None and prods:
                if str(src.get("product_smiles_full") or "") != str(
                        prods[0] if prods else ""):
                    source_mismatch[label] += 1
            elif src is not None and not prods:
                source_mismatch[label] += 1
            if src is not None:
                source_filled[label] += 1
            row[f"{label}_run_id"] = run_id
            row[f"{label}_calls"] = _call_stats_for_run(
                runs_roots[label] / run_id) if run_id else {}
        for k in (1, 3, 5):
            h0, h3 = row["C0_hit@%d" % k], row["D3_hit@%d" % k]
            cell = ("both" if h0 and h3 else "C0_only" if h0
                    else "D3_only" if h3 else "neither")
            quadrant[k][cell] += 1
            if h3 and not h0:
                win_lose[k]["win"] += 1
            elif h0 and not h3:
                win_lose[k]["lose"] += 1
            else:
                win_lose[k]["tie"] += 1
        rows.append(row)

    def _hits(label, k):
        return sum(1 for r in rows if r[f"{label}_hit@{k}"])

    summary = {
        "schema_version": "ec298-pd-retest-paired-1",
        "experiment_label": "seen298_post_hoc_repair_check",
        "scorer_version": "v43-ec298-scorer-2",
        "identity_caliber": "cn from raw candidate SMILES, whole-candidate string",
        "n_questions": len(rows),
        "pairing_gate_verdict": gate["verdict"],
        "release_eligible": gate["release_eligible"],
        "engine_results_sha256": engine_sha,
        "gold_questions_sha256": gold_sha,
        "c0_predictions_sha256": _sha256_file(
            c0_root / "merged" / "predictions.jsonl"),
        "d3_predictions_sha256": _sha256_file(
            d3_root / "merged" / "predictions.jsonl"),
        "hits": {
            k: {"C0": _hits("C0", k), "D3": _hits("D3", k),
                "delta": _hits("D3", k) - _hits("C0", k),
                "delta_pp": round(
                    (_hits("D3", k) - _hits("C0", k)) / 298 * 100, 2)}
            for k in (1, 3, 5)},
        "quadrants": {f"hit@{k}": quadrant[k] for k in (1, 3, 5)},
        "quadrant_sums_ok": {f"hit@{k}": sum(quadrant[k].values()) == 298
                             for k in (1, 3, 5)},
        "d3_win_lose_tie": {f"hit@{k}": win_lose[k] for k in (1, 3, 5)},
        "first_product_source": {
            label: {
                "n_filled": source_filled[label],
                "n_first_product_mismatch": source_mismatch[label],
                "source": "results/T_*/report_adjudication.json "
                          "products[reportable=true] ordered by report_rank; "
                          "cross-checked product_smiles_full == merged "
                          "predicted_products[0]",
            }
            for label in ("C0", "D3")},
        "note_hit10": "hit@10 equals hit@5 for a five-per-step agent "
                      "(output width ceiling), width statement only",
        "engine_background_note": "engine ranks are background reference "
                                  "only; NOT part of the C0/D-3 pairing",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    result = {"summary": summary, "per_question": rows}
    (out_dir / "paired_scoring_298.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")

    # flat TSV for humans
    cols = ["qid"]
    for label in ("C0", "D3"):
        cols += [f"{label}_rank", f"{label}_hit@1", f"{label}_hit@3",
                 f"{label}_hit@5", f"{label}_n_predicted",
                 f"{label}_answer_kind", f"{label}_stop_reason",
                 f"{label}_route_state", f"{label}_first_product",
                 f"{label}_first_source_evidence_id",
                 f"{label}_first_source_kind",
                 f"{label}_first_source_report_rank"]
    lines = ["\t".join(cols)]
    for r in rows:
        lines.append("\t".join(
            "" if r.get(c) is None else
            (str(r[c]).replace("\t", " ").replace("\n", " "))
            for c in cols))
    (out_dir / "paired_scoring_298.tsv").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items()
                      if k in ("hits", "quadrants", "quadrant_sums_ok",
                               "d3_win_lose_tie", "pairing_gate_verdict")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
