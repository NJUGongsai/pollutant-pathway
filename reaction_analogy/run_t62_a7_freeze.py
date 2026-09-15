#!/usr/bin/env python3
"""T6-2 A7/gold 冻结驱动 — parent-only 预测 + 归一化 + 冻结清单。

冻结纪律（老师 2026-09-15 指示）：
  1. 只用 parent-only 包（BLIND_PARENT_INPUTS.csv）完成预测并冻结原始输出；
  2. 冻结（本脚本产出的 manifest + git commit）之后才允许打开 gold 评分；
  3. 预测进程绝不接触 gold —— 本脚本与其子进程只读引擎数据与 parent CSV，
     从不引用 gold_standard/ 下任何文件（gold 仅由评分脚本读取，冻结后调用）。

三个口径（与 BioTransformer ENVMICRO 同 scope：depth-1 产物预测）：
  v32pred    single_smiles_v32.py  --scoring v32  （v3.2 基线，纯预测）
  v33pred    single_smiles_v32.py  --scoring v33  （v3.3 融合层，纯预测）
  v33hybrid  single_smiles_hybrid.py --scoring v33（v3.3 + EAWAG lookup 混合）

输出（T62_DIR = reports/T62_A7_GOLD_2026-09-15/）：
  inputs/BLIND_PARENT_INPUTS.csv     parent-only 输入副本（公共安全）
  runs/<caliber>/<case>*.{csv,json}  每口径每 case 的原始输出（frozen-chain 兼容）
  normalized/<tool>_predictions.jsonl 三工具归一化 schema（THREE_TOOL_PREDICTION_
                                     NORMALIZED_SCHEMA.md，flat 一行一产物）
  FREEZE_MANIFEST.json               全部产物 sha256 + git commit + 命令行审计

用法：
  python3 reaction_analogy/run_t62_a7_freeze.py --parent-csv <path> [--limit N]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
T62_DIR = os.path.join(_HERE, "reports", "T62_A7_GOLD_2026-09-15")
RUN_ID = "t62-a7-freeze-r1"

CALIBERS = {
    "v32pred": {
        "script": "single_smiles_v32.py",
        "tool_name": "depending-v32",
        "extra": ["--scoring", "v32"],
    },
    "v33pred": {
        "script": "single_smiles_v32.py",
        "tool_name": "depending-v33",
        "extra": ["--scoring", "v33"],
    },
    "v33hybrid": {
        "script": "single_smiles_hybrid.py",
        "tool_name": "depending-v33-hybrid",
        "extra": ["--scoring", "v33"],
    },
}

TOP_K = 50          # 头部留量：支持 Hit@10 及更宽诊断口径
MAX_DEPTH = 1       # BioTransformer ENVMICRO 同 scope：一步产物预测


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_parents(path: str):
    parents = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            parents.append((row["case_id"].strip(), row["parent_smiles"].strip()))
    return parents


def run_all(parents):
    runs_meta = {}
    for caliber, cfg in CALIBERS.items():
        out_dir = os.path.join(T62_DIR, "runs", caliber)
        os.makedirs(out_dir, exist_ok=True)
        for case_id, smi in parents:
            prefix = os.path.join(out_dir, case_id)
            if os.path.exists(prefix + "_RUN_META.json"):
                print(f"[skip] {caliber}/{case_id} (already run)", flush=True)
                continue
            cmd = [
                sys.executable, os.path.join(_HERE, cfg["script"]),
                "--smiles", smi,
                "--top-k", str(TOP_K),
                "--max-depth", str(MAX_DEPTH),
                "--case-id", case_id,
                "--out-prefix", prefix,
            ] + cfg["extra"]
            t0 = time.time()
            res = subprocess.run(cmd, cwd=_HERE, capture_output=True, text=True)
            dt = round(time.time() - t0, 1)
            ok = res.returncode == 0
            runs_meta[f"{caliber}/{case_id}"] = {
                "cmd": cmd, "returncode": res.returncode, "time_s": dt,
            }
            print(f"[{'ok' if ok else 'FAIL'}] {caliber}/{case_id} {dt}s "
                  f"rc={res.returncode}", flush=True)
            if not ok:
                print(res.stderr[-1500:], flush=True)
    return runs_meta


def normalize(parents):
    """runs/<caliber>/<case>_ALL_NORMALIZED_PREDICTIONS.csv → flat schema jsonl."""
    from rdkit import Chem

    out_files = {}
    for caliber, cfg in CALIBERS.items():
        out_path = os.path.join(T62_DIR, "normalized",
                                f"{cfg['tool_name']}_predictions.jsonl")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        n_rows = 0
        with open(out_path, "w") as out:
            for case_id, parent_smi in parents:
                csv_path = os.path.join(T62_DIR, "runs", caliber,
                                        f"{case_id}_ALL_NORMALIZED_PREDICTIONS.csv")
                if not os.path.exists(csv_path):
                    continue
                with open(csv_path, newline="") as f:
                    for i, row in enumerate(csv.DictReader(f), start=2):
                        smi = (row.get("product_smiles") or "").strip()
                        if not smi:
                            continue
                        mol = Chem.MolFromSmiles(smi)
                        if mol is None:
                            canon, ik, status = "", "", "invalid_smiles"
                        else:
                            canon = Chem.MolToSmiles(mol, canonical=True)
                            ik = Chem.MolToInchiKey(mol)
                            status = "ok"
                        eawag = (row.get("eawag_reactions") or "").strip()
                        prov = f"layer={row.get('layer', '')};source={row.get('source', '')}"
                        if eawag and eawag != "[]":
                            prov += f";eawag_reactions={eawag}"
                        rec = {
                            "tool_name": cfg["tool_name"],
                            "tool_version": "3.2" if caliber == "v32pred" else "3.3",
                            "run_id": RUN_ID,
                            "case_id": case_id,
                            "parent_smiles": parent_smi,
                            "prediction_rank": int(row["rank"]),
                            "predicted_product_smiles_original": smi,
                            "predicted_product_smiles_canonical": canon,
                            "predicted_product_inchikey": ik,
                            "raw_score": row.get("score", ""),
                            "raw_confidence": "",
                            "provenance": prov,
                            "raw_output_ref": f"runs/{caliber}/{case_id}_ALL_NORMALIZED_PREDICTIONS.csv:{i}",
                            "normalization_status": status,
                            "normalization_note": (
                                (row.get("score_semantics") or "")
                                + ";is_calibrated_probability=false"),
                        }
                        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        n_rows += 1
        out_files[cfg["tool_name"]] = out_path
        print(f"[norm] {cfg['tool_name']}: {n_rows} rows", flush=True)
    return out_files


def build_manifest(parents, runs_meta, out_files, parent_csv_src):
    files = {}
    for dirpath, _, names in os.walk(T62_DIR):
        for name in sorted(names):
            p = os.path.join(dirpath, name)
            rel = os.path.relpath(p, T62_DIR)
            if name == "FREEZE_MANIFEST.json":
                continue
            files[rel] = {"sha256": sha256(p), "bytes": os.path.getsize(p)}
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    manifest = {
        "run_id": RUN_ID,
        "frozen_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "git_commit_at_freeze": commit,
        "discipline": [
            "predictions ran on parent-only inputs BEFORE any gold access",
            "gold_standard/* opened only after this manifest is committed",
            "the only gold reader is scripts/score_three_tool_predictions.py "
            "(their frozen scorer), invoked post-freeze",
        ],
        "parent_csv_source": os.path.abspath(parent_csv_src),
        "parent_csv_sha256": sha256(parent_csv_src),
        "n_cases": len(parents),
        "case_ids": [c for c, _ in parents],
        "calibers": {k: {
            "script": v["script"], "tool_name": v["tool_name"],
            "scoring": v["extra"][-1], "top_k": TOP_K, "max_depth": MAX_DEPTH,
        } for k, v in CALIBERS.items()},
        "runs": runs_meta,
        "files": files,
    }
    path = os.path.join(T62_DIR, "FREEZE_MANIFEST.json")
    with open(path, "w") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False, sort_keys=True)
    print(f"[freeze] manifest -> {path} ({len(files)} files hashed)", flush=True)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent-csv", required=True)
    ap.add_argument("--limit", type=int, default=0, help="debug: first N cases")
    args = ap.parse_args()

    os.makedirs(T62_DIR, exist_ok=True)
    inputs_dir = os.path.join(T62_DIR, "inputs")
    os.makedirs(inputs_dir, exist_ok=True)
    dst = os.path.join(inputs_dir, "BLIND_PARENT_INPUTS.csv")
    shutil.copyfile(args.parent_csv, dst)

    parents = load_parents(dst)
    if args.limit:
        parents = parents[: args.limit]
    print(f"[plan] {len(parents)} cases x {len(CALIBERS)} calibers, "
          f"top_k={TOP_K}, max_depth={MAX_DEPTH}", flush=True)

    runs_meta = run_all(parents)
    failed = [k for k, v in runs_meta.items() if v["returncode"] != 0]
    if failed:
        print(f"FATAL: {len(failed)} failed runs: {failed}", file=sys.stderr)
        return 2

    out_files = normalize(parents)
    build_manifest(parents, runs_meta, out_files, args.parent_csv)
    print("[done] freeze artifacts ready — commit before opening gold",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
