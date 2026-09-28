"""v2 导出 / 研究报告 / 旧版兼容验收测试(TASK_V43_EC298_PHASE_B §4/§5.5)。

- v2 裁决投影:未提交的可报告候选进入父步骤但不产生子步骤;父节点无
  ReactionEvent 但有占位候选仍生成父步骤;已提交 deferred 产物进答卷。
- 账本交叉核对:只核对 committed_event_ref 指向产物及其 position/raw/cn;
  位次集合/身份/raw 不一致 → fail-closed。
- 旧版兼容:v1 裁决按旧投影逐字节保持原结果;新旧 schema 混用拒绝;
  草稿产物永不进入导出。
- 新鲜度:``export --verify`` 核对答卷文件 SHA 与裁决集合指纹 ——
  新增/删减/篡改裁决、答卷篡改均报过期。
- 研究报告:top5_reportable_products 与导出前五逐位一致;报告/提交/
  仅报告/展开计数分列。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.domain.identity import cn_identity  # noqa: E402
from pathway_v43.domain.models import stable_id  # noqa: E402
from pathway_v43.output.export_v3 import (  # noqa: E402
    ExportStale,
    LedgerCorrupt,
    adjudication_fingerprint,
    export_run_v3,
)
from pathway_v43.output.report import build_report  # noqa: E402
from pathway_v43.storage.artifact_store import ArtifactStore  # noqa: E402
from pathway_v43.storage.pathway_store import (  # noqa: E402
    PathwayStore,
    event_id_for,
    product_path_id,
    root_path_id,
)

from wf_helpers import evidence, run_scripted  # noqa: E402

A = "CCO"
B1 = "CC=O"
B2 = "C=CO"
B3 = "CC(O)C"
S_A = cn_identity(A)


def _make_run(runs_root: Path, run_id: str, root_smiles: str, *,
              adj_schema: str | None = "v43-report-adjudication-2"
              ) -> PathwayStore:
    """合成账本 + run_identity(adj_schema 模拟身份声明的裁决 schema;
    None = 旧 v1 run 的身份无 adjudication 块)。真实工作流的身份由
    build_run_identity 写入 adjudication 块 —— verify 以它为预期 schema。"""
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    store = PathwayStore(run_dir / "pathway.sqlite")
    root_cn = cn_identity(root_smiles) or root_smiles
    store.ensure_run(run_id, root_smiles, root_cn)
    identity = {"schema_version": "v43-identity-1", "run_id": run_id,
                "inputs": {"root_smiles": root_smiles,
                           "root_identity": root_cn}}
    if adj_schema:
        identity["adjudication"] = {"schema_version": adj_schema,
                                    "policy_version": "v43-repadj-1"}
    (runs_root / run_id / "run_identity.json").write_text(
        json.dumps(identity, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return store


def _submit(store: PathwayStore, runs_root: Path, run_id: str,
            parent_path_id: str, parent_identity: str, ev_rid: str,
            products: list[tuple[int, str]], *, expandable: list[int],
            deferred: list[int]) -> str:
    card = evidence(ev_rid, "recorded_reaction", parent_identity,
                    [s for _, s in sorted(products)])
    card["products"] = [
        {"position": p, "product_smiles": s, "product_smiles_full": s,
         "product_identity": cn_identity(s) or s, "score": 0.9,
         "score_semantics": "fixture"}
        for p, s in sorted(products)]
    card["evidence_id"] = f"E-{ev_rid}"
    eid = event_id_for(run_id, parent_path_id, parent_identity,
                       card["evidence_id"])
    result = store.submit_event(
        run_id=run_id, parent_path_id=parent_path_id,
        substrate_identity=parent_identity, evidence=card,
        products=card["products"],
        expandable_path_ids=[product_path_id(run_id, eid, p)
                             for p in expandable],
        deferred_path_ids=[product_path_id(run_id, eid, p)
                           for p in deferred])
    store.refresh_depths(run_id)
    return result["event_id"]


def _entry(path_id, eid, kind, pos, smiles, *, rank=None, accepted=True,
           committed=None, expand=False, deferred=False, raw_full="",
           ref_task="T-val", ref_artifact=None):
    # 缺省每卡一份验证产物(与工作流 cardval.<hash> 语义一致)
    ref_artifact = ref_artifact or f"cardval.{eid}"
    raw = raw_full or smiles
    return {
        "path_id": path_id, "evidence_id": eid, "card_kind": kind,
        "entry_layer": "retrieval", "retrieval_rank": 1,
        "task_candidate_position": None, "model_order_position": None,
        "position": pos, "product_smiles_full": raw_full,
        "product_smiles": smiles,
        "raw_source": "product_smiles_full" if raw_full else "product_smiles",
        "cn_identity": cn_identity(raw) or "", "stored_product_identity":
            cn_identity(raw),
        "identity_match": True,
        "validation_ref": {"task_id": ref_task, "artifact": ref_artifact,
                           "payload_sha256": "0" * 64},
        "validation_verdict_hash": "", "accepted": accepted, "reasons": [],
        "reportable": rank is not None, "report_rank": rank,
        "dedup_reason": "", "committed_event_ref": committed,
        "expand_selected": expand, "deferred": deferred,
        "expand_status": ("frontier" if expand
                          else ("deferred" if deferred
                                else ("accepted" if accepted else "rejected"))),
        "endorsed": True,
    }


def _v2_payload(run_id, path_id, substrate, products, *, event_id=None,
                no_event_reason=""):
    ranked = [e for e in products if e["reportable"]]
    ranks = sorted(e["report_rank"] for e in ranked)
    selected = products[0]["evidence_id"] if products else ""
    return {
        "schema_version": "v43-report-adjudication-2",
        "task_kind": "report_adjudication", "stage": "final",
        "run_id": run_id, "path_id": path_id, "substrate_identity": substrate,
        "policy": {"policy_version": "v43-repadj-1",
                   "max_reportable_products": 5},
        "rank_basis": "deterministic_fallback",
        "selection": {"selected_evidence_id": selected,
                      "selected_card_kind": "recorded_reaction",
                      "model_order": [], "order_missing": False,
                      "mode": "deterministic", "model_decision_ref": ""},
        "cards": [], "products": products,
        "event": {"event_id": event_id, "no_event": event_id is None,
                  "no_event_reason": no_event_reason},
        "n_reportable": len(ranked),
        "n_committed": sum(1 for e in products
                           if e["committed_event_ref"] is not None),
        "n_expand_selected": sum(1 for e in products if e["expand_selected"]),
        "n_deferred": sum(1 for e in products if e["deferred"]),
    }


def _write_v2(runs_root: Path, run_id: str, payload: dict) -> None:
    """写最终裁决 + 其引用的全部验证产物(R1 P1-2:导出读取端会按
    validation_ref 回查并逐项核对 verdict)。"""
    from pathway_v43.domain.models import content_hash

    artifacts = ArtifactStore(runs_root, run_id)
    task_id = stable_id("T", run_id, payload["path_id"], "adjudication-v2")
    # 组装每个 (task_id, artifact) 的验证产物 payload,verdict 与裁决条目
    # 逐项一致(evidence_id/position/raw/cn/accepted)
    val_payloads: dict[tuple[str, str], dict] = {}
    for e in payload["products"]:
        ref = e["validation_ref"]
        key = (ref["task_id"], ref["artifact"])
        vp = val_payloads.setdefault(key, {
            "schema_version": "v43-validation-1",
            "evidence_id": e["evidence_id"], "verdicts": []})
        raw = e["product_smiles_full"] or e["product_smiles"]
        vp["verdicts"].append({
            "position": e["position"], "product_smiles": raw,
            "product_identity": e["cn_identity"],
            "accepted": bool(e["accepted"]), "reasons": []})
    for (ref_task, ref_artifact), vp in val_payloads.items():
        env = artifacts.write(ref_task, ref_artifact, vp)
        for e in payload["products"]:
            r = e["validation_ref"]
            if (r["task_id"], r["artifact"]) == (ref_task, ref_artifact):
                e["validation_ref"] = {**r, "payload_sha256":
                                       env["payload_hash"]}
    artifacts.write(task_id, "report_adjudication", payload)


# ---------------------------------------------------------------- v2 投影


def test_v2_uncommitted_reportable_enters_step_without_child(tmp_path):
    """可报告集合大于事件产物:未提交候选进父步骤,但不产生子步骤。"""
    store = _make_run(tmp_path, "v2a", A)
    root_pid = root_path_id("v2a", S_A)
    eid = _submit(store, tmp_path, "v2a", root_pid, S_A, "ev1",
                  [(0, B1), (1, B2)], expandable=[0], deferred=[1])
    payload = _v2_payload("v2a", root_pid, S_A, [
        _entry(root_pid, "E-ev1", "recorded_reaction", 0, B1, rank=1,
               committed=eid, expand=True),
        _entry(root_pid, "E-ev1", "recorded_reaction", 1, B2, rank=2,
               committed=eid, deferred=True),
        _entry(root_pid, "E-alt", "recorded_reaction", 0, B3, rank=3),
    ], event_id=eid)
    _write_v2(tmp_path, "v2a", payload)
    result = export_run_v3(tmp_path, "v2a")
    line = json.loads((tmp_path / "v2a" / "predictions.jsonl").read_text())
    assert line["steps"] == [
        {"parent_smiles": A,
         "predicted_products": [B1, B2, B3]}]
    counts = result["metadata"]["counts"]
    assert counts["n_committed_products"] == 2
    assert counts["n_reportable_products"] == 3
    assert counts["n_report_only_products"] == 1
    # B3 无产物路径(未提交):不产生子步骤
    steps = line["steps"]
    assert len(steps) == 1


def test_v2_no_event_parent_with_reportable_gets_step(tmp_path):
    """父节点无 ReactionEvent 但有最终可报告候选:仍生成一个父步骤。"""
    store = _make_run(tmp_path, "v2b", A)
    root_pid = root_path_id("v2b", S_A)
    store.set_path_status(root_pid, "dead_end", "fixture")
    payload = _v2_payload(
        "v2b", root_pid, S_A,
        [_entry(root_pid, "E-alt", "recorded_reaction", 0, B3, rank=1)],
        no_event_reason="selected_card_all_products_rejected")
    _write_v2(tmp_path, "v2b", payload)
    export_run_v3(tmp_path, "v2b")
    line = json.loads((tmp_path / "v2b" / "predictions.jsonl").read_text())
    assert line["steps"] == [{"parent_smiles": A,
                              "predicted_products": [B3]}]


def test_v2_no_event_without_reportable_yields_no_step(tmp_path):
    """no_event 空裁决(无可报告候选):不产生步骤(冻结策略明示)。"""
    store = _make_run(tmp_path, "v2c", A)
    root_pid = root_path_id("v2c", S_A)
    payload = _v2_payload(
        "v2c", root_pid, S_A,
        [_entry(root_pid, "E-a", "recorded_reaction", 0, "C(C(",
                accepted=False, rank=None)],
        no_event_reason="selected_card_all_products_rejected")
    _write_v2(tmp_path, "v2c", payload)
    export_run_v3(tmp_path, "v2c")
    line = json.loads((tmp_path / "v2c" / "predictions.jsonl").read_text())
    assert line["steps"] == []


def test_v2_ledger_adjudication_mismatch_fail_closed(tmp_path):
    """committed 条目与账本事件产物位次/身份/raw 不一致 → 结构化失败。"""
    def build(name, entries):
        store = _make_run(tmp_path, name, A)
        root_pid = root_path_id(name, S_A)
        eid = _submit(store, tmp_path, name, root_pid, S_A, "ev1",
                      [(0, B1)], expandable=[0], deferred=[])
        payload = _v2_payload(name, root_pid, S_A, entries(
            root_pid, eid), event_id=eid)
        _write_v2(tmp_path, name, payload)
        export_run_v3(tmp_path, name)

    # 位次集合不一致:账本有 pos0,裁决 committed 条目却标 pos1
    def wrong_positions(root_pid, eid):
        return [_entry(root_pid, "E-ev1", "recorded_reaction", 1, B2,
                       rank=1, committed=eid, expand=True)]
    with pytest.raises(LedgerCorrupt):
        build("v2x1", wrong_positions)

    # 身份不一致:committed 条目 cn_identity 与账本产物身份不同
    def wrong_identity(root_pid, eid):
        e = _entry(root_pid, "E-ev1", "recorded_reaction", 0, B1, rank=1,
                   committed=eid, expand=True)
        e["cn_identity"] = cn_identity(B2)
        return [e]
    with pytest.raises(LedgerCorrupt):
        build("v2x2", wrong_identity)

    # raw 不一致:裁决条目 raw 与账本 raw 不同(同身份不同电荷形)
    def wrong_raw(root_pid, eid):
        return [_entry(root_pid, "E-ev1", "recorded_reaction", 0, B2,
                       rank=1, committed=eid, expand=True)]
    with pytest.raises(LedgerCorrupt):
        build("v2x3", wrong_raw)


def test_mixed_schemas_rejected(tmp_path):
    """同一 run 混用 v1/v2 裁决 schema → 拒绝(不静默重解释)。"""
    store = _make_run(tmp_path, "mix", A)
    root_pid = root_path_id("mix", S_A)
    eid = _submit(store, tmp_path, "mix", root_pid, S_A, "ev1",
                  [(0, B1)], expandable=[0], deferred=[])
    # v1 形态裁决(另一 task 目录)
    artifacts = ArtifactStore(tmp_path, "mix")
    v1 = {
        "schema_version": "v43-report-adjudication-1",
        "task_kind": "report_adjudication", "run_id": "mix",
        "path_id": root_pid, "substrate_identity": S_A,
        "evidence_id": "E-ev1", "event_id": eid,
        "entries": [_entry(root_pid, "E-ev1", "recorded_reaction", 0, B1,
                           rank=1, committed=eid, expand=True)],
        "n_reportable": 1,
    }
    artifacts.write(stable_id("T", "mix", "v1"), "report_adjudication", v1)
    v2 = _v2_payload("mix", root_pid, S_A, [
        _entry(root_pid, "E-ev1", "recorded_reaction", 0, B1, rank=1,
               committed=eid, expand=True)], event_id=eid)
    artifacts.write(stable_id("T", "mix", "v2"), "report_adjudication", v2)
    with pytest.raises(LedgerCorrupt):
        export_run_v3(tmp_path, "mix")


def test_draft_artifacts_never_exported(tmp_path):
    """草稿产物(另一文件名)既不产生步骤,也不破坏导出。"""
    store = _make_run(tmp_path, "dr", A)
    root_pid = root_path_id("dr", S_A)
    artifacts = ArtifactStore(tmp_path, "dr")
    artifacts.write(stable_id("T", "dr", "draft"),
                    "report_adjudication_draft",
                    _v2_payload("dr", root_pid, S_A, [
                        _entry(root_pid, "E-a", "recorded_reaction", 0, B1,
                               rank=1)]))
    export_run_v3(tmp_path, "dr")
    line = json.loads((tmp_path / "dr" / "predictions.jsonl").read_text())
    assert line["steps"] == []
    # 同一 run 的事件提交后:草稿仍被忽略,最终裁决进入答卷
    eid = _submit(store, tmp_path, "dr", root_pid, S_A, "ev1",
                  [(0, B1)], expandable=[0], deferred=[])
    _write_v2(tmp_path, "dr", _v2_payload("dr", root_pid, S_A, [
        _entry(root_pid, "E-ev1", "recorded_reaction", 0, B1, rank=1,
               committed=eid, expand=True)], event_id=eid))
    export_run_v3(tmp_path, "dr")
    line = json.loads((tmp_path / "dr" / "predictions.jsonl").read_text())
    assert line["steps"] == [{"parent_smiles": A,
                              "predicted_products": [B1]}]


# ---------------------------------------------------------------- 新鲜度


def _fresh_v2_run(tmp_path: Path) -> Path:
    store = _make_run(tmp_path, "fresh", A)
    root_pid = root_path_id("fresh", S_A)
    eid = _submit(store, tmp_path, "fresh", root_pid, S_A, "ev1",
                  [(0, B1), (1, B2)], expandable=[0], deferred=[1])
    _write_v2(tmp_path, "fresh", _v2_payload("fresh", root_pid, S_A, [
        _entry(root_pid, "E-ev1", "recorded_reaction", 0, B1, rank=1,
               committed=eid, expand=True),
        _entry(root_pid, "E-ev1", "recorded_reaction", 1, B2, rank=2,
               committed=eid, deferred=True),
        _entry(root_pid, "E-alt", "recorded_reaction", 0, B3, rank=3)],
        event_id=eid))
    export_run_v3(tmp_path, "fresh")
    return tmp_path / "fresh"


def test_verify_fresh_and_detects_answer_tamper(tmp_path):
    run_dir = _fresh_v2_run(tmp_path / "r1")
    export_run_v3(tmp_path / "r1", "fresh", verify_only=True)
    pred = run_dir / "predictions.jsonl"
    pred.write_text(pred.read_text().replace(B1, "CCCCCCO"),
                    encoding="utf-8")
    with pytest.raises(ExportStale):
        export_run_v3(tmp_path / "r1", "fresh", verify_only=True)


def test_verify_detects_adjudication_add_remove_tamper(tmp_path):
    run_dir = _fresh_v2_run(tmp_path / "r2")
    results = run_dir / "results"
    adj_path = next(p for p in results.glob("*/report_adjudication.json"))
    export_run_v3(tmp_path / "r2", "fresh", verify_only=True)

    # 篡改裁决 payload(同键重写哈希)= 内容篡改 → 过期
    envelope = json.loads(adj_path.read_text())
    envelope["payload"]["products"][2]["reportable"] = False
    envelope["payload"]["products"][2]["report_rank"] = None
    from pathway_v43.domain.models import content_hash

    envelope["payload_hash"] = content_hash(envelope["payload"])
    adj_path.write_text(json.dumps(envelope, ensure_ascii=False) + "\n")
    with pytest.raises(ExportStale):
        export_run_v3(tmp_path / "r2", "fresh", verify_only=True)

    # 删减:去掉整份裁决 → 聚合指纹变化 → 过期(且事件缺裁决会先损坏)
    adj_path.unlink()
    with pytest.raises((ExportStale, LedgerCorrupt)):
        export_run_v3(tmp_path / "r2", "fresh", verify_only=True)

    # 新增:另一份裁决 → 聚合指纹变化 → 过期
    store = PathwayStore(run_dir / "pathway.sqlite")
    root_pid = root_path_id("fresh", S_A)
    extra = _v2_payload("fresh", root_pid, S_A, [
        _entry(root_pid, "E-extra", "recorded_reaction", 0, "CCCCCCO",
               rank=1)],
        no_event_reason="fixture_extra_adjudication")
    _write_v2(tmp_path / "r2", "fresh", extra)
    with pytest.raises(ExportStale):
        export_run_v3(tmp_path / "r2", "fresh", verify_only=True)


def test_fingerprint_is_stable_and_covers_set(tmp_path):
    run_dir = _fresh_v2_run(tmp_path / "r3")
    fp1 = adjudication_fingerprint(run_dir)
    fp2 = adjudication_fingerprint(run_dir)
    assert fp1 == fp2
    assert fp1["n_adjudications"] == 1
    assert fp1["schema_version"] == "v43-report-adjudication-2"
    assert fp1["committed_event_ids"]


# ---------------------------------------------------------------- 报告一致性


def test_report_top5_matches_export_bitwise(tmp_path):
    """报告 top5_reportable_products 与导出前五逐位一致(任务书 §5.5)。"""
    a = evidence("btA", "recorded_reaction", cn_identity(A), [B1, B2, B3])
    summary, runs_root = run_scripted(
        "rc1", {S_A: [a]}, smiles=A, max_depth=1, max_expansions=4,
        max_frontier_width=2, runs_root=tmp_path)
    assert summary["counts"]["reaction_events"] == 1
    export_run_v3(runs_root, "rc1")
    line = json.loads((runs_root / "rc1" / "predictions.jsonl").read_text())
    exported = line["steps"][0]["predicted_products"][:5]
    report = build_report(
        __import__("pathway_v43.storage.pathway_store",
                   fromlist=["PathwayStore"]).PathwayStore(
                       runs_root / "rc1" / "pathway.sqlite"),
        runs_root / "rc1", "rc1",
        {"budget": {}, "root_smiles": A}, "completed")
    path_record = next(p for p in report["path_instances"]
                       if p["parent_path_id"] is None)
    reported = [e["product_smiles"]
                for e in path_record["top5_reportable_products"]]
    assert reported == exported
    rc = path_record["report"]
    assert rc["n_reported"] == len(exported)
    assert rc["n_committed"] == len(exported)
    assert rc["n_expand_selected"] == 2  # frontier 宽度 2,与报告宽度分离


# ------------------------------------------------- R1 P2: v2 verify 门禁


def test_verify_rejects_missing_or_incomplete_adjudication_block(tmp_path):
    """R1 P2:v2 裁决的新鲜度门禁不可选 —— 元数据删整个裁决指纹块、删块内
    字段、伪造纸架版本都判过期;完整块比对一致才通过。"""
    run_dir = _fresh_v2_run(tmp_path / "rv")
    meta_path = run_dir / "export_metadata.json"

    def _restore(text):
        meta_path.write_text(text, encoding="utf-8")

    original = meta_path.read_text(encoding="utf-8")
    meta = json.loads(original)

    # 基线:完整块 → verify 通过
    export_run_v3(tmp_path / "rv", "fresh", verify_only=True)

    # 删整个块 → ExportStale
    _restore(json.dumps({k: v for k, v in meta.items()
                         if k != "adjudication"},
                        ensure_ascii=False, sort_keys=True))
    with pytest.raises(ExportStale):
        export_run_v3(tmp_path / "rv", "fresh", verify_only=True)

    # 删块内字段(payload_hashes_sha256)→ ExportStale
    broken = dict(meta)
    broken["adjudication"] = {k: v for k, v in meta["adjudication"].items()
                              if k != "payload_hashes_sha256"}
    _restore(json.dumps(broken, ensure_ascii=False, sort_keys=True))
    with pytest.raises(ExportStale):
        export_run_v3(tmp_path / "rv", "fresh", verify_only=True)

    # 伪造块内 schema 版本 → 与当前指纹不一致 → ExportStale
    forged = dict(meta)
    forged["adjudication"] = {**meta["adjudication"],
                              "schema_version": "v43-report-adjudication-9"}
    _restore(json.dumps(forged, ensure_ascii=False, sort_keys=True))
    with pytest.raises(ExportStale):
        export_run_v3(tmp_path / "rv", "fresh", verify_only=True)

    # 篡改聚合哈希 → ExportStale
    forged2 = dict(meta)
    forged2["adjudication"] = {**meta["adjudication"],
                               "payload_hashes_sha256": "0" * 64}
    _restore(json.dumps(forged2, ensure_ascii=False, sort_keys=True))
    with pytest.raises(ExportStale):
        export_run_v3(tmp_path / "rv", "fresh", verify_only=True)

    # 恢复原块 → 通过
    _restore(original)
    export_run_v3(tmp_path / "rv", "fresh", verify_only=True)


def test_v1_legacy_metadata_without_block_still_verifiable(tmp_path):
    """v1 旧 run 元数据无裁决指纹块:保留兼容(revision/策略/身份仍核对)。"""
    # 直接构造 v1 场景:旧导出器产物没有 adjudication 块
    runs_root = tmp_path / "leg"
    store = _make_run(runs_root, "leg1", A, adj_schema=None)
    root_pid = root_path_id("leg1", S_A)
    eid = _submit(store, runs_root, "leg1", root_pid, S_A, "ev1",
                  [(0, B1)], expandable=[0], deferred=[])
    # 用 v1 形态裁决(旧 run)
    artifacts = ArtifactStore(runs_root, "leg1")
    v1 = {
        "schema_version": "v43-report-adjudication-1",
        "task_kind": "report_adjudication", "run_id": "leg1",
        "path_id": root_pid, "substrate_identity": S_A,
        "evidence_id": "E-ev1", "event_id": eid,
        "evidence_kind": "recorded_reaction",
        "report_rank_basis": "event_product_position_accepted_order",
        "policy": {"max_reportable_products": 5},
        "entries": [{
            "position": 0, "product_identity": cn_identity(B1),
            "product_smiles": B1, "product_smiles_full": B1,
            "evidence_id": "E-ev1", "validation_ref": "T-fixture-validation",
            "accepted": True, "reportable": True, "report_rank": 1,
            "expand_selected": True, "expand_status": "frontier",
            "verdict_reasons": [],
        }],
        "n_reportable": 1,
    }
    artifacts.write(stable_id("T", "leg1", "v1"), "report_adjudication", v1)
    export_run_v3(runs_root, "leg1")
    _line = json.loads((runs_root / "leg1" / "predictions.jsonl").read_text())
    assert _line["steps"] == [{"parent_smiles": A,
                               "predicted_products": [B1]}]
    meta_path = runs_root / "leg1" / "export_metadata.json"
    meta = json.loads(meta_path.read_text())
    # 模拟历史 v1 元数据:去掉 adjudication 块
    meta_path.write_text(json.dumps(
        {k: v for k, v in meta.items() if k != "adjudication"},
        ensure_ascii=False, sort_keys=True), encoding="utf-8")
    result = export_run_v3(runs_root, "leg1", verify_only=True)
    assert result["verified"] is True


# ------------------------------------- R2 P1-2: verify 组合删除 + 空集合


def test_verify_combined_deletion_of_adjudications_and_block(tmp_path):
    """R2 P1-2 review 复现:删光两份最终裁决文件 + 删元数据指纹块 ——
    verify 以 run identity 声明的预期 schema 为准,不得因现存文件消失
    而把 v2 run 伪装成 v1;组合删除必须判过期。"""
    import shutil

    src = _fresh_v2_run(tmp_path / "src")
    work = tmp_path / "work" / "fresh"
    shutil.copytree(src, work)
    meta_path = work / "export_metadata.json"
    original = meta_path.read_text(encoding="utf-8")
    meta = json.loads(original)

    # 基线:完整 run verify 通过
    export_run_v3(tmp_path / "work", "fresh", verify_only=True)

    # 组合删除:删光裁决文件 + 删指纹块 → 必须过期(不得伪装 v1)
    for p in (work / "results").glob("*/report_adjudication.json"):
        p.unlink()
    meta_path.write_text(json.dumps(
        {k: v for k, v in meta.items() if k != "adjudication"},
        ensure_ascii=False, sort_keys=True), encoding="utf-8")
    with pytest.raises(ExportStale):
        export_run_v3(tmp_path / "work", "fresh", verify_only=True)

    # 只删裁决文件、留指纹块:指纹失配(空集合 ≠ 两份裁决)→ 过期
    meta_path.write_text(original, encoding="utf-8")
    with pytest.raises(ExportStale):
        export_run_v3(tmp_path / "work", "fresh", verify_only=True)

    # 对照:身份无 adjudication 声明的真旧 v1 run —— R1 起明确保留的
    # 历史兼容:元数据无块则 verify 无裁决门禁(verify 语义 = 核对导出
    # 时点快照的新鲜度);其"事件缺裁决"损坏由重导出投影兜底
    # LedgerCorrupt —— 不静默重导,但不像 v2 那样在 verify 强制。
    runs_root = tmp_path / "leg"
    store = _make_run(runs_root, "leg1", A, adj_schema=None)
    root_pid = root_path_id("leg1", S_A)
    eid = _submit(store, runs_root, "leg1", root_pid, S_A, "ev1",
                  [(0, B1)], expandable=[0], deferred=[])
    artifacts = ArtifactStore(runs_root, "leg1")
    artifacts.write(stable_id("T", "leg1", "v1"), "report_adjudication", {
        "schema_version": "v43-report-adjudication-1",
        "task_kind": "report_adjudication", "run_id": "leg1",
        "path_id": root_pid, "substrate_identity": S_A,
        "evidence_id": "E-ev1", "event_id": eid,
        "evidence_kind": "recorded_reaction",
        "report_rank_basis": "event_product_position_accepted_order",
        "policy": {"max_reportable_products": 5},
        "entries": [{
            "position": 0, "product_identity": cn_identity(B1),
            "product_smiles": B1, "product_smiles_full": B1,
            "evidence_id": "E-ev1", "validation_ref": "T-fixture-validation",
            "accepted": True, "reportable": True, "report_rank": 1,
            "expand_selected": True, "expand_status": "frontier",
            "verdict_reasons": [],
        }],
        "n_reportable": 1,
    })
    export_run_v3(runs_root, "leg1")
    for p in (runs_root / "leg1" / "results").glob(
            "*/report_adjudication.json"):
        p.unlink()
    (runs_root / "leg1" / "export_metadata.json").write_text(json.dumps(
        {k: v for k, v in json.loads(
            (runs_root / "leg1" / "export_metadata.json").read_text()).items()
         if k != "adjudication"}, ensure_ascii=False, sort_keys=True),
        encoding="utf-8")
    result = export_run_v3(runs_root, "leg1", verify_only=True)
    assert result["verified"] is True  # v1 历史兼容语义(如上说明)
    with pytest.raises(LedgerCorrupt):
        export_run_v3(runs_root, "leg1")  # 重导出投影兜底:fail-closed


def test_verify_legitimate_empty_adjudication_set_v2(tmp_path):
    """R2 P1-2:v2 run 的合法空裁决集合(全部路径停待预测)—— 导出显式
    空答卷,指纹块按 identity 预期 schema 记 v2 空集合;verify 通过;
    事后补一份裁决 → 指纹失配 → 过期。"""
    a = evidence("btA", "recorded_reaction", S_A, [B1])
    b = evidence("btB", "recorded_reaction", S_A, [B2], rank=2)
    summary, runs_root = run_scripted(
        "emptyv2", {S_A: [a, b]}, smiles=A, max_depth=1,
        max_expansions=4, max_frontier_width=3, runs_root=tmp_path)
    assert summary["stop_reason"] == "awaiting_prediction"
    assert summary["counts"]["reaction_events"] == 0
    result = export_run_v3(runs_root, "emptyv2")
    meta = result["metadata"]
    assert meta["adjudication"]["schema_version"] \
        == "v43-report-adjudication-2"
    assert meta["adjudication"]["n_adjudications"] == 0
    line = json.loads((runs_root / "emptyv2" / "predictions.jsonl")
                      .read_text())
    assert line["steps"] == []
    export_run_v3(runs_root, "emptyv2", verify_only=True)

    # 事后追加一份裁决(如手工补写)→ 指纹失配 → 过期
    root_pid = root_path_id("emptyv2", S_A)
    _write_v2(runs_root, "emptyv2", _v2_payload(
        "emptyv2", root_pid, S_A,
        [_entry(root_pid, "E-x", "recorded_reaction", 0, B1, rank=1)],
        no_event_reason="fixture"))
    with pytest.raises(ExportStale):
        export_run_v3(runs_root, "emptyv2", verify_only=True)


# --------------------------------- R3 P2: schema ⇄ 身份声明一致性


def test_v2_identity_with_v1_adjudications_rejected(tmp_path):
    """R3 P2 review 复现:身份声明 v2、账本有已提交事件、最终裁决却是
    完整 v1 → 导出与 verify 都拒绝(不得按文件中的 v1 静默走旧投影)。"""
    store = _make_run(tmp_path, "mixid", A, adj_schema=None)  # 先造旧式身份
    run_dir = tmp_path / "mixid"
    # 手工把身份升为 v2 声明(模拟"身份 v2 + 裁决 v1"的拼装 run)
    ipath = run_dir / "run_identity.json"
    identity = json.loads(ipath.read_text())
    identity["adjudication"] = {"schema_version":
                                "v43-report-adjudication-2",
                                "policy_version": "v43-repadj-1"}
    ipath.write_text(json.dumps(identity, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    root_pid = root_path_id("mixid", S_A)
    eid = _submit(store, tmp_path, "mixid", root_pid, S_A, "ev1",
                  [(0, B1)], expandable=[0], deferred=[])
    # 写完整 v1 形态裁决(非空集合)
    artifacts = ArtifactStore(tmp_path, "mixid")
    artifacts.write(stable_id("T", "mixid", "v1"), "report_adjudication", {
        "schema_version": "v43-report-adjudication-1",
        "task_kind": "report_adjudication", "run_id": "mixid",
        "path_id": root_pid, "substrate_identity": S_A,
        "evidence_id": "E-ev1", "event_id": eid,
        "evidence_kind": "recorded_reaction",
        "report_rank_basis": "event_product_position_accepted_order",
        "policy": {"max_reportable_products": 5},
        "entries": [{
            "position": 0, "product_identity": cn_identity(B1),
            "product_smiles": B1, "product_smiles_full": B1,
            "evidence_id": "E-ev1", "validation_ref": "T-fx",
            "accepted": True, "reportable": True, "report_rank": 1,
            "expand_selected": True, "expand_status": "frontier",
            "verdict_reasons": [],
        }],
        "n_reportable": 1,
    })
    with pytest.raises(LedgerCorrupt):
        export_run_v3(tmp_path, "mixid")
    # verify 腿:翻转身份到 v2 声明后,历史导出物的身份指纹必须同步更新,
    # 才能走到 schema 一致性核对(否则先被身份指纹变化拦下,测不到目标门禁)
    ipath.write_text(json.dumps(
        {k: v for k, v in identity.items() if k != "adjudication"},
        ensure_ascii=False, indent=2), encoding="utf-8")
    export_run_v3(tmp_path, "mixid")  # 无声明 + v1 = 历史兼容,可导出
    ipath.write_text(json.dumps(identity, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    from pathway_v43.storage.run_identity import identity_fingerprint

    meta_path = run_dir / "export_metadata.json"
    meta = json.loads(meta_path.read_text())
    meta["run_identity_fingerprint"] = identity_fingerprint(
        json.loads(ipath.read_text()))
    meta["adjudication"]["schema_version"] = "v43-report-adjudication-1"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, sort_keys=True),
                         encoding="utf-8")
    with pytest.raises(LedgerCorrupt):
        export_run_v3(tmp_path, "mixid", verify_only=True)


def test_v2_adjudications_without_identity_declaration_rejected(tmp_path):
    """R3 P2 反向组合:v2 裁决文件 + 无身份声明的旧式身份 → 拒绝
    (v2 只由写入 identity 块的新代码产生;无声明 + v2 = 拼装 run)。"""
    store = _make_run(tmp_path, "rev", A, adj_schema=None)
    root_pid = root_path_id("rev", S_A)
    eid = _submit(store, tmp_path, "rev", root_pid, S_A, "ev1",
                  [(0, B1)], expandable=[0], deferred=[])
    _write_v2(tmp_path, "rev", _v2_payload("rev", root_pid, S_A, [
        _entry(root_pid, "E-ev1", "recorded_reaction", 0, B1, rank=1,
               committed=eid, expand=True)], event_id=eid))
    with pytest.raises(LedgerCorrupt):
        export_run_v3(tmp_path, "rev")
    # 导出从未成功(无导出物),verify 入口同样先经一致性核对拒绝
    from pathway_v43.output.export_v3 import check_adjudication_schema_identity

    identity = json.loads((tmp_path / "rev" / "run_identity.json").read_text())
    with pytest.raises(LedgerCorrupt):
        check_adjudication_schema_identity(tmp_path / "rev", identity)


def test_v1_declared_identity_with_v1_adjudications_still_legacy(tmp_path):
    """一致性核对不破坏历史兼容:无声明身份 + v1 裁决照常导出与 verify。"""
    runs_root = tmp_path / "leg"
    store = _make_run(runs_root, "leg2", A, adj_schema=None)
    root_pid = root_path_id("leg2", S_A)
    eid = _submit(store, runs_root, "leg2", root_pid, S_A, "ev1",
                  [(0, B1)], expandable=[0], deferred=[])
    artifacts = ArtifactStore(runs_root, "leg2")
    artifacts.write(stable_id("T", "leg2", "v1"), "report_adjudication", {
        "schema_version": "v43-report-adjudication-1",
        "task_kind": "report_adjudication", "run_id": "leg2",
        "path_id": root_pid, "substrate_identity": S_A,
        "evidence_id": "E-ev1", "event_id": eid,
        "evidence_kind": "recorded_reaction",
        "report_rank_basis": "event_product_position_accepted_order",
        "policy": {"max_reportable_products": 5},
        "entries": [{
            "position": 0, "product_identity": cn_identity(B1),
            "product_smiles": B1, "product_smiles_full": B1,
            "evidence_id": "E-ev1", "validation_ref": "T-fx",
            "accepted": True, "reportable": True, "report_rank": 1,
            "expand_selected": True, "expand_status": "frontier",
            "verdict_reasons": [],
        }],
        "n_reportable": 1,
    })
    export_run_v3(runs_root, "leg2")
    export_run_v3(runs_root, "leg2", verify_only=True)
