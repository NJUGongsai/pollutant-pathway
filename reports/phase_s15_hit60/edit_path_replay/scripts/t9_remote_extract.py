#!/usr/bin/env python3
"""T9 远端只读取证:抽取 analogy_edit 任务的原始编辑输入(零写入、零 API)。

对象:
  A) ec298_pd_retest_C0 的 12 个 edit_blocked qid(boundary_pools 口径);
  B) dependingv43_s1 六个 dev 批次中 mode=analogy_edit 的全部任务。

输出:JSONL 到 stdout(由本地调用方捕获,落入 gitignored raw_inputs/)。
只读:不写远端任何文件,不调任何 API。
"""
import json
import sys
from pathlib import Path

QIDS = [
    "RXNG_0c352348a848d6e24b845830cb6babf521bf976fe5e1029b3140e1917eb0545a",
    "RXNG_0eda0ec3a41b2c3acfd65b9fb04c98769602f4e7fcc9d41e156cfa5d020f1d7a",
    "RXNG_21ed83a680e54ef6741935a58d8f25e9fbde2714dd60c0793d731d875750bfc0",
    "RXNG_31299a2c77ec97998ff6c2d057a92d5bf9e80d5ef08e71cdfb8fc473cf906fba",
    "RXNG_3d58685aebce44376b74102596b979baa8aeaac74e31da59b4b15a8c96277858",
    "RXNG_89b8bce798e20b8a265b94e1bead35a7fd06c5064466ab19fcfd334e53f4cd92",
    "RXNG_b139babc703701fc836ff00662f8a5010f90ac1138b2ca5ef264bdf4655acdec",
    "RXNG_b978fd0b540c4b52d0b90b504c8479c5fdb89291e40f9ab008f2639964bdd9b3",
    "RXNG_bd3bc48984cbae8677446ad46fcfc9d11aeadaa52fc743b20f62b8498147862a",
    "RXNG_d30a28d0eca9e1703f1939e734213afd2c1d733799080752e1ec908daefa69fc",
    "RXNG_e11a1cac66b6fca34aa0f0c2405a66e89bc3ae311d6cedd07c4cc7310d0e9d44",
    "RXNG_eabc2bf0bfa38d7017254413b48ab72b2f4f5e4d6c804ce36887f7885277649b",
]

C0_ROOT = Path("/usrdata/EnzymeCAGE_data/workspaces/dependingv43/runs/ec298_pd_retest_C0/runs")
S1_ROOT = Path("/usrdata/EnzymeCAGE_data/workspaces/dependingv43_s1/runs")
S1_BATCHES = [
    "s1_dev_C0_20260929T182619Z",
    "s1_dev_C0_20260929T190054Z",
    "s1_dev_E2_20260929T192739Z",
    "s1_dev_E2_20260929T201603Z",
    "s1_dev_E3_20260929T204506Z",
    "s1_dev_E1_20260930T023702Z",
]


def read_json(p):
    try:
        with open(p) as f:
            return json.load(f)["payload"]
    except Exception:
        return None


def extract(run_dir, batch, qid):
    """从一个题的 run 目录抽取全部 analogy_edit 任务(通常恰 1 个)。"""
    out = []
    results = run_dir / "results"
    if not results.is_dir():
        return out
    # 检索产物按 (path_id, substrate_identity) 索引(与 phase_c 审计同法)
    retrievals = {}
    for td in sorted(results.iterdir()):
        ret = read_json(td / "retrieval.json")
        if not ret:
            continue
        q = ret.get("query") or {}
        retrievals[(q.get("path_id"), q.get("substrate_identity"))] = {
            "n_evidence": len(ret.get("evidence") or ret.get("evidences") or []),
        }
    for td in sorted(results.iterdir()):
        pt = read_json(td / "prediction_task.json")
        if not pt or pt.get("mode") != "analogy_edit":
            continue
        cur = pt.get("current") or {}
        dec = read_json(td / "decision.json") or {}
        pred = read_json(td / "prediction.json") or {}
        parsed = pred.get("parsed") or {}
        donor = (pt.get("donor") or {})
        d = donor.get("donor") or {}
        checks = pred.get("atomtool_checks") or {}
        ret_info = retrievals.get((pt.get("path_id"), cur.get("identity"))) or {}
        out.append({
            "batch": batch,
            "qid": qid,
            "run_name": run_dir.name,
            "task_id": td.name,
            "task": {
                "mode": pt.get("mode"),
                "path_id": pt.get("path_id"),
                "current": {
                    "identity": cur.get("identity"),
                    "smiles_canonical": cur.get("smiles_canonical"),
                    "atom_ids": cur.get("atom_ids"),
                },
                "donor": {
                    "evidence_id": donor.get("evidence_id"),
                    "record_id": d.get("record_id"),
                    "alignment": d.get("alignment"),
                    "center_atoms": d.get("center_atoms"),
                },
                "n_candidates": len(pt.get("candidates") or []),
            },
            "decision": {
                "outcome": dec.get("outcome"),
                "mode": dec.get("mode"),
                "prediction_reason": dec.get("prediction_reason"),
            },
            "prediction": {
                "outcome": pred.get("outcome"),
                "fail_reason": pred.get("fail_reason"),
                "attempt": pred.get("attempt"),
                "parsed": parsed,
                "checks": checks,
            },
            "retrieval": ret_info,
        })
    return out


def main():
    rows = []
    # A) C0 臂 12 qid
    for qid in QIDS:
        found = False
        for run_dir in sorted(C0_ROOT.glob(f"*_{qid}")):
            found = True
            rows.extend(extract(run_dir, "ec298_pd_retest_C0", qid))
        if not found:
            rows.append({"batch": "ec298_pd_retest_C0", "qid": qid,
                         "error": "run_dir_not_found"})
    # B) dev 六批 analogy_edit 全扫
    n_dev = 0
    for b in S1_BATCHES:
        root = S1_ROOT / b / "runs"
        if not root.is_dir():
            rows.append({"batch": b, "qid": "", "error": "runs_dir_missing"})
            continue
        for run_dir in sorted(root.iterdir()):
            if not run_dir.is_dir():
                continue
            qid = run_dir.name.split("_", 2)[-1]
            got = extract(run_dir, b, qid)
            rows.extend(got)
            n_dev += len(got)
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))
    print(f"n_rows={len(rows)} n_dev_analogy_tasks={n_dev}", file=sys.stderr)


if __name__ == "__main__":
    main()
