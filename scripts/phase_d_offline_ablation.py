"""Phase D D3.1:dev 20 四配置零 API 资格消融(任务书 §4.1)。

输入 = 冻结 dev 20 输入清单(``reports/export_dev/input_manifest.json``,
``gold_fields_excluded=true``,只含 root_smiles/route_id,**不读金标**)。
不跑模型、不进网络:审计对象是每条路线从根出发、沿**唯一 recorded
确定性直通**可达的全部父节点(无模型时类比/novel 停留,树不再展开 ——
这是零 API 的诚实边界,完整展开树由 D3.2 真实臂产生)。

四配置:
- C0     :v1 语料 + reactant_similar 关闭 + 预算 3(= Phase B/C 现状)
- D1-only:v1 + similar(0.45/16,参数卡) + 预算 3
- D2-only:v2 + similar 关闭 + 预算 3
- D1+D2  :v2 + similar + 预算 3

逐题输出:父节点数、检索 refs、实际评估数、资格分布
(applicable/ambiguous/inapplicable/unavailable)、拒因计数、通道分布、
displaced、budget_not_assessed。产物 ``reports/phase_d/ablation/``。

用法:
  OMP_NUM_THREADS=1 PYTHONPATH=src python scripts/phase_d_offline_ablation.py
"""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "reports" / "export_dev" / "input_manifest.json"
OUT_DIR = REPO / "reports" / "phase_d" / "ablation"

SIM_THRESHOLD = 0.45   # 参数卡冻结值(docs/PHASE_D_D1_PARAM_CARD.md)
SIM_TOP_K = 16
BUDGET = 3

ARMS = {
    "C0": {"corpus": "v1", "sim": False},
    "D1-only": {"corpus": "v1", "sim": True},
    "D2-only": {"corpus": "v2", "sim": False},
    "D1+D2": {"corpus": "v2", "sim": True},
}


def _config(corpus: str):
    from pathway_v43.config import V43Config, repo_root

    root = repo_root()
    return V43Config(
        v3_code_root=(root.parent / "dependingv3").resolve(),
        assets_root=(root / "assets").resolve(),
        analog_corpus=corpus,
    )


def main() -> None:
    from pathway_v43.adapters.v3_engine import get_engine
    from pathway_v43.domain.identity import cn_identity
    from pathway_v43.services.analog_source import (
        AnalogSourceResolver,
        similar_donor_refs,
    )
    from pathway_v43.services.donor_applicability import (
        ApplicabilityPolicy,
        build_eligibility,
    )
    from pathway_v43.services.reaction_finder import (
        EngineReactionFinder,
        ReactionContext,
    )
    from pathway_v43.services.donor_applicability import (
        APPLICABILITY_AMBIGUOUS, APPLICABILITY_APPLICABLE,
        APPLICABILITY_INAPPLICABLE, APPLICABILITY_UNAVAILABLE,
        APPLICABILITY_BUDGET_NOT_ASSESSED,
    )
    from pathway_v43.domain.policy import (
        PREDICTION_POLICY_DEFAULTS, _usable_recorded,
    )

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest.get("gold_fields_excluded") is True
    routes = manifest["routes"]

    t0 = time.time()
    engine = get_engine(_config("v1"))     # 引擎只读 v3_reactions(四臂同源)
    resolvers = {}
    finders = {}
    for arm, spec in ARMS.items():
        cfg = _config(spec["corpus"])
        resolver = AnalogSourceResolver(cfg)
        resolvers[arm] = resolver
        finders[arm] = EngineReactionFinder(engine, cfg,
                                            analog_resolver=resolver)
    print("engine + 2 resolvers loaded", round(time.time() - t0, 1), "s",
          flush=True)

    arm_results: dict[str, list] = {}
    for arm, spec in ARMS.items():
        t_arm = time.time()
        rows = []
        for route in routes:
            rid, smiles = route["route_id"], route["root_smiles"]
            # 沿唯一 recorded 直通收集父节点(确定性;无模型不展开预测分支);
            # envelope 随发现缓存,审计阶段不重复检索
            parents: list[tuple[str, str, list]] = []
            seen: set[str] = set()
            queue = [(rid, smiles, 0)]
            while queue:
                tag, smi, depth = queue.pop(0)
                ident = cn_identity(smi) or smi
                if ident in seen or depth > 6:
                    continue
                seen.add(ident)
                ctx = ReactionContext(
                    run_id=f"pd-ablation-{arm}", path_id=f"{tag}-d{depth}",
                    substrate_smiles=smi, substrate_identity=ident,
                    ancestry=[],
                )
                envelope = finders[arm].find(ctx)
                cards = envelope["evidences"]
                parents.append((f"{tag}-d{depth}", smi, cards))
                usable = [c for c in cards
                          if _usable_recorded(c, ident)]
                if len(usable) == 1:
                    # 唯一 recorded:确定性直通,其产物为下一父节点
                    prods = usable[0].get("products") or []
                    if prods:
                        queue.append(
                            (tag, prods[0]["product_smiles_full"], depth + 1))
            per_parents = []
            for tag, smi, cards in parents:
                ident = cn_identity(smi) or smi
                pol = ApplicabilityPolicy(
                    max_donor_candidates=BUDGET,
                    similarity_threshold=(
                        SIM_THRESHOLD if spec["sim"] else 0.0),
                    similarity_top_k=SIM_TOP_K if spec["sim"] else 0,
                )
                sim_refs = []
                if spec["sim"]:
                    sim_refs = similar_donor_refs(
                        resolvers[arm], smi,
                        threshold=SIM_THRESHOLD, top_k=SIM_TOP_K)
                block = build_eligibility(cards, smi, pol,
                                          similar_refs=sim_refs)
                cards_b = block.get("cards") or []
                per_parents.append({
                    "parent": tag,
                    "substrate": smi,
                    "n_similar_refs": block.get("n_similar_channel_refs", 0),
                    "n_cards_evaluated": block.get("n_cards_evaluated", 0),
                    "status": block["status"],
                    "fallback_reason": block["fallback_reason"],
                    "reject_reasons": block.get("reject_reasons", []),
                    "n_evaluated_refs": sum(
                        c.get("n_donor_refs_evaluated", 0) for c in cards_b),
                    "n_budget_not_assessed": sum(
                        c.get("n_budget_not_assessed", 0) for c in cards_b),
                    "displaced": block.get("displaced_by_similar_channel",
                                           []),
                    "channels": dict(Counter(
                        ch for c in cards_b
                        for e in c.get("donor_evals", [])
                        for ch in (e.get("find_channels") or []))),
                    "donor_statuses": dict(Counter(
                        e.get("status", "") for c in cards_b
                        for e in c.get("donor_evals", []))),
                    "selected_record": (
                        block.get("selected") or {}).get("record_id", ""),
                })
            rows.append({"route_id": rid, "parents": per_parents})
        arm_results[arm] = rows
        print(f"arm {arm} done in {round(time.time()-t_arm,1)}s",
              flush=True)

    # ---- 汇总(逐臂 + 逐题配对差异) ----
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {}
    for arm, rows in arm_results.items():
        parents = [p for r in rows for p in r["parents"]]
        ch = Counter()
        st = Counter()
        for p in parents:
            for k, v in p["channels"].items():
                ch[k] += v
            for k, v in p["donor_statuses"].items():
                st[k] += v
        summary[arm] = {
            "n_routes": len(rows),
            "n_parents_audited": len(parents),
            "eligibility": dict(Counter(p["status"] for p in parents)),
            "fallback_reasons": dict(Counter(
                p["fallback_reason"] for p in parents
                if p["fallback_reason"])),
            "n_evaluated_refs": sum(p["n_evaluated_refs"] for p in parents),
            "n_budget_not_assessed": sum(
                p["n_budget_not_assessed"] for p in parents),
            "n_displaced": sum(len(p["displaced"]) for p in parents),
            "n_similar_refs_recalled": sum(
                p["n_similar_refs"] for p in parents),
            "channels": dict(ch),
            "donor_statuses": dict(st),
        }

    # 逐题配对:C0 → 各臂的状态迁移
    transitions = {}
    base = {r["route_id"]: [p["status"] for p in r["parents"]]
            for r in arm_results["C0"]}
    for arm in ("D1-only", "D2-only", "D1+D2"):
        rows = []
        for r in arm_results[arm]:
            rid = r["route_id"]
            new = [p["status"] for p in r["parents"]]
            old = base.get(rid, [])
            same = len(old) == len(new) and all(
                a == b for a, b in zip(old, new))
            rows.append({
                "route_id": rid,
                "c0_statuses": old, "arm_statuses": new,
                "n_parents": len(new),
                "changed": (not same),
                "n_applicable_c0": old.count("applicable"),
                "n_applicable_arm": new.count("applicable"),
                "n_similar_refs": sum(p["n_similar_refs"] for p in r["parents"]),
                "first_selected_record": next(
                    (p["selected_record"] for p in r["parents"]
                     if p["selected_record"]), ""),
            })
        transitions[arm] = rows

    out = {
        "schema_version": "pd-ablation-1",
        "inputs": {
            "manifest": str(MANIFEST.relative_to(REPO)),
            "manifest_sha256": __import__("hashlib").sha256(
                MANIFEST.read_bytes()).hexdigest(),
            "gold_fields_excluded": True,
            "sim_threshold": SIM_THRESHOLD, "sim_top_k": SIM_TOP_K,
            "budget": BUDGET,
        },
        "arms": {arm: {"corpus": s["corpus"], "sim": s["sim"]}
                 for arm, s in ARMS.items()},
        "summary": summary,
        "transitions_vs_c0": transitions,
        "elapsed_s": round(time.time() - t0, 1),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (OUT_DIR / "ablation_summary.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    for arm, rows in arm_results.items():
        (OUT_DIR / f"per_route_{arm.replace('+', '_')}.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
            + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2)[:3000])
    print("elapsed", out["elapsed_s"], "s")


if __name__ == "__main__":
    main()
