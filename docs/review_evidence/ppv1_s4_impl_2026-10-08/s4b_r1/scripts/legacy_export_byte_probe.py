#!/usr/bin/env python3
"""S4b 专项:冻结 legacy/export_v3 字节不变探针(任务书 §7 S4b 第
7 项;S4a 交付书 §20.7 遗留)。

目的:证明 S4b 改动(PPV1 native_export/v3_projection/runflow/profile)
对**冻结的 legacy v3 导出路径**零字节影响 —— 同一合成 legacy run 在
「当前树」与「直接父 fc40605 树」分别构建并导出,predictions.jsonl
与 export_metadata.json 逐字节一致(export_v3.py / pathway_store /
report_adjudication / identity / artifact_store 均为冻结依赖,任何
非预期触碰都会使字节分叉)。

夹具(与 tests/test_export_v3.py 同构,自包含复制;不依赖 tests/
helpers):
- run A:单事件多产物(CCO → CC=O + O);
- run B:两事件竞争同父分子(首现合并语义)+ deferred 位次。
两 run 覆盖 v1 投影主路径(合并/首现/位次/上限)。

用法(每树一次,--out 拒绝已存在目录):
    python -B legacy_export_byte_probe.py --src <tree>/src \
        --out <fresh_tmp_out> [--runs-root <fresh_tmp_runs>]

输出:predictions_sha256/metadata_sha256(两树对比由调用方执行)+
 载荷文件副本(证据落盘)。零网络、零 LLM、零真实资产读取。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--src", required=True, type=Path)
parser.add_argument("--out", required=True, type=Path)
parser.add_argument("--runs-root", required=True, type=Path)
args = parser.parse_args()

SRC = args.src.expanduser().resolve()
OUT = args.out.expanduser().resolve()
RUNS_ROOT = args.runs_root.expanduser().resolve()
if OUT.exists():
    raise SystemExit(f"输出目录已存在,须用新 tmp:{OUT}")
if RUNS_ROOT.exists():
    raise SystemExit(f"runs 根已存在,须用新 tmp:{RUNS_ROOT}")
OUT.mkdir(parents=True)
sys.path.insert(0, str(SRC))

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.domain.models import STRATEGY_VERSION, stable_id  # noqa: E402
from pathway_v43.output.export_v3 import export_run_v3  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402
from pathway_v43.storage.pathway_store import (  # noqa: E402
    PathwayStore,
    event_id_for,
    product_path_id,
)

REPORT_ADJUDICATION_SCHEMA = "v43-report-adjudication-1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_run(runs_root: Path, run_id: str, root_smiles: str) -> PathwayStore:
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    store = PathwayStore(run_dir / "pathway.sqlite")
    root_cn = cn_identity(root_smiles) or root_smiles
    store.ensure_run(run_id, root_smiles, root_cn)
    identity = {
        "schema_version": "v43-identity-1",
        "run_id": run_id,
        "inputs": {"root_smiles": root_smiles, "root_identity": root_cn},
    }
    (run_dir / "run_identity.json").write_text(
        json.dumps(identity, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return store


def evidence_card(rid: str, kind: str, reactant_identity: str,
                  products: list[str]) -> dict:
    card = {
        "evidence_id": f"E-{rid}",
        "source_id": rid,
        "kind": kind,
        "query_identity": reactant_identity,
        "match_type": "exact_donor_cn_match",
        "reactant_smiles": reactant_identity,
        "reactant_identity": reactant_identity,
        "products": [
            {"position": i, "product_smiles": s,
             "product_smiles_full": s,
             "product_identity": cn_identity(s) or s, "score": 0.9,
             "score_semantics": "fixture"}
            for i, s in enumerate(products)
        ],
        "atom_mapping": "unavailable",
        "condition_fit": "unknown",
        "retrieval_rank": 1,
        "score": 0.9,
        "score_semantics": "fixture",
        "source_record": {"fixture": rid},
        "asset_file": "fixture/v3_reactions.jsonl",
        "asset_sha256": "0" * 64,
        "run_id": "",
        "path_id": "",
    }
    return card


def write_adjudication(runs_root: Path, run_id: str, parent_path_id: str,
                       parent_identity: str, card: dict,
                       products: list[dict], expandable_pos: set[int],
                       deferred_pos: set[int], event_id: str) -> None:
    entries = []
    rank = 0
    for p in sorted(products, key=lambda q: q["position"]):
        pos = p["position"]
        accepted = cn_identity(p["product_smiles"]) is not None
        entry = {
            "position": pos,
            "product_identity": p["product_identity"],
            "product_smiles": p["product_smiles"],
            "product_smiles_full": p.get("product_smiles_full", ""),
            "evidence_id": card["evidence_id"],
            "validation_ref": "T-fixture-validation",
            "accepted": accepted,
            "reportable": accepted,
            "report_rank": None,
            "expand_selected": pos in expandable_pos,
            "expand_status": ("frontier" if pos in expandable_pos
                              else ("deferred" if pos in deferred_pos
                                    else "rejected")),
            "verdict_reasons": [],
        }
        if accepted:
            rank += 1
            entry["report_rank"] = rank
        entries.append(entry)
    payload = {
        "schema_version": REPORT_ADJUDICATION_SCHEMA,
        "task_kind": "report_adjudication",
        "run_id": run_id,
        "path_id": parent_path_id,
        "substrate_identity": parent_identity,
        "evidence_id": card["evidence_id"],
        "evidence_kind": card.get("kind"),
        "event_id": event_id,
        "report_rank_basis": "event_product_position_accepted_order",
        "policy": {"max_reportable_products": 5},
        "entries": entries,
        "n_reportable": rank,
        "n_expand_selected": sum(1 for e in entries if e["expand_selected"]),
    }
    task_id = stable_id("T", run_id, parent_path_id, "adjudication",
                        f"{parent_identity}|{event_id}",
                        STRATEGY_VERSION, "", "")
    artifacts = ArtifactStore(runs_root, run_id)
    artifacts.write(task_id, "report_adjudication", payload)


def submit(store: PathwayStore, run_id: str, parent_path_id: str,
           parent_identity: str, ev_rid: str,
           products: list[tuple[int, str]], *, expandable: list[int],
           deferred: list[int], kind: str = "recorded_reaction",
           runs_root: Path | None = None) -> str:
    card = evidence_card(
        ev_rid, kind, parent_identity,
        [s for _, s in sorted(products, key=lambda t: t[0])])
    eid = event_id_for(run_id, parent_path_id, parent_identity,
                       card["evidence_id"])
    expandable_ids = [product_path_id(run_id, eid, p) for p in expandable]
    deferred_ids = [product_path_id(run_id, eid, p) for p in deferred]
    accepted_products = [
        prod for prod in card["products"]
        if cn_identity(prod["product_smiles"]) is not None]
    result = store.submit_event(
        run_id=run_id, parent_path_id=parent_path_id,
        substrate_identity=parent_identity, evidence=card,
        products=accepted_products, expandable_path_ids=expandable_ids,
        deferred_path_ids=deferred_ids)
    store.refresh_depths(run_id)
    if runs_root is not None:
        write_adjudication(runs_root, run_id, parent_path_id,
                           parent_identity, card, card["products"],
                           set(expandable), set(deferred),
                           result["event_id"])
    return result["event_id"]


root_smiles = "CCO"
root_cn = cn_identity(root_smiles)

# ---- run A:单事件多产物(CCO → CC=O + O) ----
runs_root = RUNS_ROOT
run_a = "legA"
store_a = make_run(runs_root, run_a, root_smiles)
root_path_a = store_a.ensure_run(run_a, root_smiles, root_cn)
submit(store_a, run_a, root_path_a, root_cn, "rA",
       [(0, "CC=O"), (1, "O")], expandable=[0], deferred=[],
       runs_root=runs_root)
result_a = export_run_v3(runs_root, run_a, route_id=run_a)

# ---- run B:两事件竞争同父(首现合并)+ deferred 位次 ----
run_b = "legB"
store_b = make_run(runs_root, run_b, root_smiles)
root_path_b = store_b.ensure_run(run_b, root_smiles, root_cn)
submit(store_b, run_b, root_path_b, root_cn, "rB1",
       [(0, "CC=O")], expandable=[0], deferred=[],
       runs_root=runs_root)
submit(store_b, run_b, root_path_b, root_cn, "rB2",
       [(0, "CC=O"), (1, "O"), (2, "CC")], expandable=[],
       deferred=[2], runs_root=runs_root)
result_b = export_run_v3(runs_root, run_b, route_id=run_b)

# ---- 重导出(树内字节幂等)与证据落盘 ----
export_run_v3(runs_root, run_a, route_id=run_a)
export_run_v3(runs_root, run_b, route_id=run_b)
out = {"src": str(SRC), "runs_root": str(RUNS_ROOT), "runs": {}}
for run_id, result in ((run_a, result_a), (run_b, result_b)):
    pred = runs_root / run_id / "predictions.jsonl"
    meta = runs_root / run_id / "export_metadata.json"
    shutil.copy2(pred, OUT / f"{run_id}_predictions.jsonl")
    shutil.copy2(meta, OUT / f"{run_id}_export_metadata.json")
    out["runs"][run_id] = {
        "predictions_sha256": result["predictions_sha256"],
        "predictions_sha256_recheck": sha(pred),
        "export_metadata_sha256": sha(meta),
        "metadata_counts": result["metadata"].get("counts"),
    }
assert out["runs"][run_a]["predictions_sha256"] == \
    out["runs"][run_a]["predictions_sha256_recheck"]
(OUT / "probe_result.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    run_id: {"predictions": r["predictions_sha256"][:16],
             "metadata": r["export_metadata_sha256"][:16]}
    for run_id, r in out["runs"].items()}, ensure_ascii=False))
