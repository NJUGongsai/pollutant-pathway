"""冻结评测器接线与诊断测试(TASK_V43_EXPORT_DEV §5.6 / §4)。

- v3 冻结评测器 CLI 对 v4.3 导出**真正执行** ``--split dev``(子进程),
  产出 cn/raw_sb、S/M/D 分层与逐路线结果;报告 split 字段核对。
- 误用拒绝:split=eval / 缺行 / 路线数不符 → EvaluatorRefusal(不过账)。
- 失分归因:命中不归因;父未到达/检索池外/池内未提交等分桶;检索池
  命中率是**诊断指标**,与正式分数分离命名。
全部测试无模型凭证可运行。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.output.score_report import (  # noqa: E402
    EvaluatorRefusal,
    diagnose_route,
    run_frozen_evaluator,
)

REPO = Path(__file__).resolve().parents[1]
V3_ROOT = REPO.parent / "dependingv3"
BENCH = V3_ROOT / "evaluation" / "pathway_benchmark"

pytestmark = pytest.mark.skipif(
    not (BENCH / "eval_pathway_benchmark.py").is_file(),
    reason="v3 冻结基准不可用")


def _dev_manifest(tmp_path: Path) -> dict:
    """真实冻结 dev 清单的白名单提取(运行侧输入;不含金标内容)。"""
    from pathway_v43.batch import build_input_manifest

    return build_input_manifest(V3_ROOT, "dev", tmp_path / "input_manifest.json")


def _make_export_run(runs_root: Path, run_id: str, root_smiles: str,
                     product: str) -> Path:
    """合成一个最小 v4.3 run(账本 + 裁决产物)→ 导出。"""
    from pathway_v43.storage.pathway_store import (
        PathwayStore,
        event_id_for,
        product_path_id,
        root_path_id,
    )
    from pathway_v43.storage.artifact_store import ArtifactStore
    from pathway_v43.domain.models import STRATEGY_VERSION, stable_id

    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True)
    store = PathwayStore(run_dir / "pathway.sqlite")
    root_cn = cn_identity(root_smiles) or root_smiles
    store.ensure_run(run_id, root_smiles, root_cn)
    (run_dir / "run_identity.json").write_text(json.dumps({
        "schema_version": "v43-identity-1", "run_id": run_id,
        "inputs": {"root_smiles": root_smiles, "root_identity": root_cn},
    }), encoding="utf-8")
    card = {
        "evidence_id": "E-fixture", "kind": "recorded_reaction",
        "products": [{"position": 0, "product_smiles": product,
                      "product_smiles_full": product,
                      "product_identity": cn_identity(product) or product,
                      "score": 0.9, "score_semantics": "fixture"}],
    }
    eid = event_id_for(run_id, root_path_id(run_id, root_cn), root_cn,
                       "E-fixture")
    store.submit_event(
        run_id=run_id, parent_path_id=root_path_id(run_id, root_cn),
        substrate_identity=root_cn, evidence=card, products=card["products"],
        expandable_path_ids=[product_path_id(run_id, eid, 0)],
        deferred_path_ids=[])
    store.refresh_depths(run_id)
    payload = {
        "schema_version": "v43-report-adjudication-1",
        "task_kind": "report_adjudication", "run_id": run_id,
        "path_id": root_path_id(run_id, root_cn),
        "substrate_identity": root_cn, "evidence_id": "E-fixture",
        "evidence_kind": "recorded_reaction", "event_id": eid,
        "report_rank_basis": "event_product_position_accepted_order",
        "policy": {"max_reportable_products": 5},
        "entries": [{
            "position": 0, "product_identity": card["products"][0][
                "product_identity"],
            "product_smiles": product, "product_smiles_full": product,
            "evidence_id": "E-fixture", "validation_ref": "T-v",
            "accepted": True, "reportable": True, "report_rank": 1,
            "expand_selected": True, "expand_status": "frontier",
            "verdict_reasons": [],
        }],
        "n_reportable": 1, "n_expand_selected": 1,
    }
    task_id = stable_id("T", run_id, root_path_id(run_id, root_cn),
                        "adjudication", root_cn, STRATEGY_VERSION, "", "")
    ArtifactStore(runs_root, run_id).write(
        task_id, "report_adjudication", payload)
    from pathway_v43.output.export_v3 import export_run_v3

    export_run_v3(runs_root, run_id)
    return run_dir


def test_frozen_evaluator_cli_really_runs_dev(tmp_path):
    """v3 冻结评测器 CLI 对 v4.3 导出真正执行 --split dev(子进程)。"""
    manifest = _dev_manifest(tmp_path)
    first = manifest["routes"][0]
    gold_lines = {}
    for line in (BENCH / "gold_routes.jsonl").read_text(
            encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["route_id"] in set(manifest["route_order"]):
            gold_lines[rec["route_id"]] = rec
    gold_first = gold_lines[first["route_id"]]
    # 用 gold 的第一条边产物作为预测(测试金标读取仅用于判分断言,
    # 不进入任何运行侧输入)
    product = gold_first["edges"][0]["product_smiles"]
    runs_root = tmp_path / "runs"
    run_id = "dev_test_pb"
    _make_export_run(runs_root, run_id, first["root_smiles"], product)
    line = json.loads(
        (runs_root / run_id / "predictions.jsonl").read_text())
    line["route_id"] = first["route_id"]
    # 20 行完整答卷:目标路线 + 其余显式空行(归并层语义)
    out_lines = []
    for r in manifest["routes"]:
        if r["route_id"] == first["route_id"]:
            out_lines.append(json.dumps(line, ensure_ascii=False,
                                        sort_keys=True, separators=(",", ":")))
        else:
            out_lines.append(json.dumps(
                {"route_id": r["route_id"], "root_smiles": r["root_smiles"],
                 "steps": []}, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")))
    merged = tmp_path / "merged" / "predictions.jsonl"
    merged.parent.mkdir(parents=True)
    merged.write_text("".join(l + "\n" for l in out_lines), encoding="utf-8")

    report = run_frozen_evaluator(V3_ROOT, merged, tmp_path / "eval_dev.json",
                                  split="dev")
    assert report["split"] == "dev"
    assert report["n_routes"] == 20
    assert report["missing_predictions"] == []
    assert report["extra_predictions"] == []
    cn = report["calibers"]["cn"]
    assert "overall" in cn and "by_stratum" in cn
    assert cn["overall"]["n_gold_edges"] == 207
    raw = report["calibers"]["raw_sb"]
    assert "overall" in raw
    if "per_route" in cn:
        target = next(r for r in cn["per_route"]
                      if r["route_id"] == first["route_id"])
        # CLI JSON 往返后 step_hits 键为字符串
        assert target["step_hits"]["1"] >= 1, "cn 主口径:首边产物应命中"


def test_evaluator_refusal_on_wrong_split(tmp_path):
    """split=eval 被拒绝(本阶段仅 dev;eval 为 run-once 冻结切片)。"""
    preds = tmp_path / "p.jsonl"
    preds.write_text('{"route_id":"pb_0001","root_smiles":"CCO","steps":[]}\n')
    with pytest.raises(EvaluatorRefusal):
        run_frozen_evaluator(V3_ROOT, preds, tmp_path / "e.json",
                             split="eval")


def test_evaluator_refusal_on_missing_lines(tmp_path):
    """归并层漏行 → 评测器报告 missing → 拒绝过账。"""
    manifest = _dev_manifest(tmp_path)
    one = manifest["routes"][0]
    preds = tmp_path / "p.jsonl"
    preds.write_text(json.dumps(
        {"route_id": one["route_id"], "root_smiles": one["root_smiles"],
         "steps": []}) + "\n")
    with pytest.raises(EvaluatorRefusal):
        run_frozen_evaluator(V3_ROOT, preds, tmp_path / "e.json", split="dev")


def test_diagnose_route_buckets(tmp_path):
    """失分归因分桶:命中不归因;父未到达/候选未生成分桶正确;
    检索池诊断指标单独命名。"""
    manifest = _dev_manifest(tmp_path)
    gold_lines = {}
    for line in (BENCH / "gold_routes.jsonl").read_text(
            encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["route_id"] in set(manifest["route_order"]):
            gold_lines[rec["route_id"]] = rec
    route_id = manifest["route_order"][0]
    gold = gold_lines[route_id]
    root = next(r["root_smiles"] for r in manifest["routes"]
                if r["route_id"] == route_id)

    # 场景一:空答卷 → 所有 gold 边漏失,父身份基本不在预测树
    empty_run = tmp_path / "runs" / "empty"
    empty_run.mkdir(parents=True)
    diag = diagnose_route(gold, {"route_id": route_id, "root_smiles": root,
                                 "steps": []}, empty_run)
    missed = diag["missed_gold_edges"]
    assert missed["n_missed"] == missed["n_total"] == len(gold["edges"])
    assert missed["buckets"].get("parent_never_reached",
                                 0) + missed["buckets"].get(
        "candidate_not_generated", 0) + missed["buckets"].get(
        "unclassified", 0) == missed["n_missed"]
    assert diag["retrieval_pool_diagnostic_hit"]["top5_of_any_path"][
               "hits"] == 0
    assert "diagnostic only" in diag["retrieval_pool_diagnostic_hit"]["note"]
    assert diag["diagnostic_kind"] == \
        "v43_ledger_descriptive_not_frozen_evaluator_slice"

    # 场景二:命中首边 → 该边不进失分列表
    product0 = gold["edges"][0]["product_smiles"]
    run_id = "hit-route"
    _make_export_run(tmp_path / "runs", run_id, root, product0)
    pred = json.loads((tmp_path / "runs" / run_id /
                       "predictions.jsonl").read_text())
    diag2 = diagnose_route(gold, pred, tmp_path / "runs" / run_id)
    missed2 = diag2["missed_gold_edges"]
    missed_pairs = {(l["parent_cn"], l["product_cn"]) for l in missed2["losses"]}
    e0 = gold["edges"][0]
    assert (e0["parent_cn"], e0["product_cn"]) not in missed_pairs
    assert missed2["n_missed"] == missed2["n_total"] - 1
