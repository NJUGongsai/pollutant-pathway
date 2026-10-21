#!/usr/bin/env python3
"""Read-only per-qid candidate/compile metadata extract for lever 2.

Reads batch_manifest entries for the requested qids only and emits metadata:
counters, candidate outcome/reason/channel/f5/route aggregates, and compact
candidate records. It never reads reference_graphs, gold, questions, or emits
any SMILES / structure text (candidate rows in this schema carry no SMILES).
"""
from __future__ import annotations

import argparse
import collections
import json


def agg_candidates(cands):
    keys = ("channel", "f5", "outcome", "reason", "route", "pool_rank", "merged_into")
    out = {k: collections.Counter() for k in keys}
    rows = []
    for c in cands:
        rec = {k: c.get(k) for k in keys}
        rows.append(rec)
        for k in keys:
            out[k][str(rec[k])] += 1
    f5_reason = collections.Counter(
        "%s|%s" % (c.get("f5"), c.get("reason")) for c in cands
    )
    channel_reason = collections.Counter(
        "%s|%s" % (c.get("channel"), c.get("reason")) for c in cands
    )
    return {
        "n_candidates": len(cands),
        "by": {k: dict(v) for k, v in out.items()},
        "by_f5_reason": dict(f5_reason),
        "by_channel_reason": dict(channel_reason),
        "rows": rows,
    }


def entry_meta(e):
    pd = e.get("pool_diagnostics") or {}
    keep = (
        "n_pool_returned", "n_analog_compiled", "n_unique_net_reactions",
        "n_corpus_strict_exact", "n_corpus_cn_candidate",
        "n_recorded_strict_exact", "n_recorded_cn_candidate",
        "n_cosubstrate_declared_specs",
        "analog_cosub_supply_compile_attempted",
        "analog_cosub_supply_rescued",
        "analog_cosub_supply_wildcard_blocked",
        "analog_center_admission_checked",
        "analog_center_admission_deferred",
        "analog_center_admission_skipped",
        "analog_pregate_skipped",
        "analog_threshold",
        "analog_threshold_dropped",
        "compiler_version",
        "pool_policy_version",
    )
    out = {"pool_size": e.get("pool_size")}
    for k in keep:
        out[k] = pd.get(k)
    out["compile_failure_histogram"] = pd.get("compile_failure_histogram") or {}
    rd = pd.get("recorded_diagnostics") or {}
    out["recorded_diagnostics"] = {
        k: rd.get(k) for k in (
            "n_lookup_rows", "n_reactions", "n_strict_exact", "n_cn_candidate",
            "compile_failure_histogram", "recorded_source_version",
        )
    }
    cd = pd.get("corpus_diagnostics") or {}
    out["corpus_diagnostics"] = {
        k: cd.get(k) for k in (
            "corpus_n_rows", "n_matched_rows", "n_strict_exact", "n_cn_candidate",
            "n_failure_events", "compile_failure_histogram",
            "n_cosubstrate_component_candidates",
            "n_cosubstrate_component_compiled",
            "n_cosubstrate_component_rejected",
            "corpus_retrieval_semantics", "corpus_retrieval_version",
        )
    }
    out["candidates"] = agg_candidates(pd.get("candidates") or [])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("qids")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    qids = set(json.load(open(args.qids))["union"])
    man = json.load(open(args.manifest))
    out = {}
    for e in man.get("entries") or []:
        q = e.get("qid")
        if q in qids:
            out[q] = entry_meta(e)
    json.dump(
        {
            "manifest": args.manifest,
            "manifest_batch_tag": man.get("batch_tag"),
            "manifest_n_questions": man.get("n_questions"),
            "requested_qids": len(qids),
            "found_qids": len(out),
            "by_qid": out,
            "note": "metadata only; no reference_graphs/gold/questions/SMILES read or emitted",
        },
        open(args.out, "w"), ensure_ascii=False, indent=1,
    )
    print("wrote", args.out, "found", len(out), "/", len(qids))


if __name__ == "__main__":
    main()