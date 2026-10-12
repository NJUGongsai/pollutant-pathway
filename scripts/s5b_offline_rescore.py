#!/usr/bin/env python3
"""s5b_offline_rescore.py — S5B 评测器离线重跑基建 + partial 三拆 + 自由基扫描（T3）。

题域标签：298 / RHEA 通用酶学 / 已见题。数字一律带此标签，不外推 dev。

职责（任务书 docs/TASK_S5B_PARTIAL_BREAKDOWN_T3_2026-10-12.md）：
- 复用仓内判分代码（s5b_scoring.evaluate_scientific 链路照抄，零判据改动），
  对 chain12 全 298 题离线重跑，取**逐事件匹配明细**（coverage_mismatch_events
  / required_node_gaps / 每事件 participant_coverage / 严格命中位次——判分时
  只进内存不落盘的部分），落 analysis/rescore_detail.json；
- 对齐自检门：重跑题级桶 vs metrics.json per_qid 逐题对比；>5 题不一致退出
  码 2 停下报告版本差异；≤5 题如实披露继续；
- 43 道 metrics-partial 三拆（superset / partial_subset / 身份差异）+ D2
  指纹（declared_copy_components）交叉核对；
- 自由基扫描（mimo M5 watch item）：43 partial 全部候选事件 + 全 298 题
  rank2-5 候选事件，RDKit 解析事件产物 SMILES 计 NumRadicalElectrons>0。
  只披露不做门；strict rank1 事件作对照扫描（身份相等应天然干净）。

红线：判分口径零改动（evaluation.py / s5b_scoring.py 只读复用）；金标参考图
只在判分进程内消费，不复制出 reports/，金标结构内容不进任何输出；零 LLM
零网络；synced/ 只读；不 commit 不 push。

离线读取通道说明：synced/runs/<run_id>/ 只含 native_export/<digest[:24]>/
{manifest.json,payload.json}，无 pollutant.sqlite/artifacts —— 因此读取器
复刻 read_native_export 的离线可执行校验段（manifest core digest 复算、
payload 字节 sha、schema/契约版本门、run 绑定、payload 内容 digest、
native_result_version 门、导出策略正文+hash 绑定），跳过需 DB 权威的
引用闭合与 graph facts staleness 两段（已在产出 provenance 中如实披露）。

用法：
    python3 scripts/s5b_offline_rescore.py \
        [--batch-root reports/ppv1_s5b/chain12_s5b_298_v4b_20261012] \
        [--local-batch reports/ppv1_s5b/s5b_298_local] \
        [--out-dir <batch_root>/analysis] [--tmp-dir /tmp/s5b_t3_rescore]

输出（out-dir，gitignored；文件名避开 funnel_* 前缀）：
    rescore_detail.json / alignment_check.json /
    partial_breakdown.json / partial_breakdown.md /
    radical_scan.json / radical_scan_summary.md
另复制一份到 --tmp-dir。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pathway_v43.domain.models import content_hash  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    PPV1_EVALUATION_VERSION,
    evaluate_scientific,
)
from pathway_v43.pollutant.native_export import (  # noqa: E402
    NativeExportContractError,
    _current_contract_versions,
    export_policy_hash,
    native_export_policy,
)
from pathway_v43.pollutant.profile import (  # noqa: E402
    PPV1_NATIVE_EXPORT_VERSION as _NATIVE_EXPORT_VERSION,
    PPV1_NATIVE_RESULT_VERSION,
    PPV1_PROFILE_SCHEMA_VERSION,
)
from pathway_v43.pollutant.reference_graph import (  # noqa: E402
    load_reference_graph,
    reference_graph_sha256,
)
from pathway_v43.pollutant.s5b_scoring import (  # noqa: E402
    S5B_SCORING_VERSION,
    _candidate_events,
    _main_caliber_row,
    _paired_payload,
    _read_case,
    _root_strict_states,
    _state_smiles_of,
    normalize_preregistration,
    preregistration_approved,
)

DEFAULT_BATCH = REPO_ROOT / "reports/ppv1_s5b/chain12_s5b_298_v4b_20261012"
DEFAULT_LOCAL = REPO_ROOT / "reports/ppv1_s5b/s5b_298_local"
DEFAULT_TMP = Path("/tmp/s5b_t3_rescore")
DOMAIN_TAG = "298"
TRACK = "known_evidence_reconstruction"
ALIGNMENT_HARD_GATE = 5  # 重跑桶 vs metrics 不一致 >5 题 ⇒ 停下报告
RADICAL_SAMPLE_CAP = 40  # md 抽样行数上限（全量在 json）


# ---------------------------------------------------------------- 离线读取器


def _offline_export_reader(runs_root: Path, cache: dict[str, dict]):
    """ledger 缺席的离线首消费读取器：接口与 s5b_scoring._batch_export_reader
    一致（reader(entry) -> {"payload": …}），校验段照抄 read_native_export
    的 1–5b/7 步（复用同一批函数与常量，零自造判据）；6/8 步需 DB 权威，
    离线跳过并如实披露。"""
    skipped_checks = [
        "step6_authority_references(needs ledger)",
        "step8_graph_facts_staleness(needs ledger)",
    ]

    def reader(entry: dict) -> dict:
        run_id = str(entry.get("run_id") or "")
        digest = str(entry.get("export_digest") or "")
        out_dir = runs_root / run_id / "native_export" / digest[:24]
        payload_path = out_dir / "payload.json"
        manifest_path = out_dir / "manifest.json"
        if not payload_path.is_file() or not manifest_path.is_file():
            raise NativeExportContractError(
                f"原生导出文件缺失:{out_dir}", {
                    "kind": "export_missing", "dir": str(out_dir),
                    "check": "offline_step1"})
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if str(manifest.get("export_digest") or "") != digest:
            raise NativeExportContractError(
                "导出 manifest 的 export_digest 与请求不符", {
                    "kind": "export_manifest_corrupt", "check":
                    "offline_step2_digest_binding"})
        core = content_hash(
            {k: v for k, v in manifest.items() if k != "export_digest"})
        if core != str(manifest.get("export_digest")):
            raise NativeExportContractError(
                "manifest core digest 复算不一致", {
                    "kind": "export_manifest_corrupt",
                    "check": "offline_step2b_manifest_core_digest"})
        payload_bytes = payload_path.read_bytes()
        sha = hashlib.sha256(payload_bytes).hexdigest()
        if sha != str(manifest.get("payload_sha256")):
            raise NativeExportContractError(
                "payload 字节 sha 与 manifest 不符", {
                    "kind": "export_payload_corrupt",
                    "check": "offline_step3_payload_sha"})
        if str(manifest.get("schema_version") or "") != \
                _NATIVE_EXPORT_VERSION:
            raise NativeExportContractError(
                f"导出 schema 版本未知:{manifest.get('schema_version')!r}",
                {"kind": "export_version_unknown",
                 "check": "offline_step4_schema_version"})
        current_contracts = _current_contract_versions()
        recorded = manifest.get("contract_versions") or {}
        drift = sorted(
            k for k, v in current_contracts.items()
            if str(recorded.get(k)) != str(v))
        if drift:
            raise NativeExportContractError(
                f"契约版本块与当前登记源不符:{drift}", {
                    "kind": "export_version_unknown",
                    "check": "offline_step4_contract_versions",
                    "changed": drift})
        if str(manifest.get("run_id") or "") != run_id:
            raise NativeExportContractError(
                "manifest run_id 与条目 run_id 不符(离线 run 绑定核)", {
                    "kind": "export_reference_mismatch",
                    "check": "offline_step4b_run_binding"})
        payload = json.loads(payload_bytes.decode("utf-8"))
        if content_hash({k: v for k, v in payload.items()
                         if k != "content_digest"}) \
                != str(payload.get("content_digest")):
            raise NativeExportContractError(
                "payload 内容 digest 复算不一致", {
                    "kind": "export_digest_mismatch",
                    "check": "offline_step5_content_digest"})
        if str(payload.get("content_digest")) != \
                str(manifest.get("content_digest")):
            raise NativeExportContractError(
                "payload 与 manifest content_digest 不一致", {
                    "kind": "export_digest_mismatch",
                    "check": "offline_step5_digest_binding"})
        if str(payload.get("native_result_version") or "") != \
                PPV1_NATIVE_RESULT_VERSION:
            raise NativeExportContractError(
                "payload native_result_version 未知", {
                    "kind": "export_version_unknown",
                    "check": "offline_step5b_native_result_version"})
        policy_body = manifest.get("export_policy")
        policy_sha = str(manifest.get("export_policy_sha256") or "")
        if not isinstance(policy_body, dict) \
                or policy_body != native_export_policy() \
                or policy_sha != export_policy_hash(policy_body) \
                or policy_sha != export_policy_hash(native_export_policy()):
            raise NativeExportContractError(
                "导出策略正文/hash 绑定失败", {
                    "kind": "export_policy_stale",
                    "check": "offline_step7_policy_binding"})
        cache[digest] = payload
        return {"payload": payload}

    reader.skipped_checks = skipped_checks  # type: ignore[attr-defined]
    return reader


# ---------------------------------------------------------------- 主流程


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--batch-root", type=Path, default=DEFAULT_BATCH)
    ap.add_argument("--local-batch", type=Path, default=DEFAULT_LOCAL)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--tmp-dir", type=Path, default=DEFAULT_TMP)
    args = ap.parse_args()
    batch_root = args.batch_root
    synced = batch_root / "synced"
    local = args.local_batch
    out_dir = args.out_dir or (batch_root / "analysis")
    tmp_dir = args.tmp_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    metrics = json.loads(
        (batch_root / "metrics.json").read_text(encoding="utf-8"))
    metrics_by_qid = {str(r["qid"]): r for r in metrics.get("per_qid") or []}
    manifest = json.loads(
        (synced / "batch_manifest.json").read_text(encoding="utf-8"))
    order = [str(q) for q in manifest.get("registration_order") or []]
    entries = {str(e["qid"]): e for e in manifest.get("entries") or []}
    split_manifest = json.loads(
        (local / "split_manifest.json").read_text(encoding="utf-8"))
    prereg = json.loads(
        (local / "preregistration_approval.json").read_text(encoding="utf-8"))
    if not preregistration_approved(prereg):
        print("[GATE] data_scope=real 而预注册未批准 ⇒ 拒评(fail-closed)")
        return 2

    # ---- 参考图装载(金标只在判分进程内消费)+ sha 对账 ----
    graphs: dict[str, dict] = {}
    graph_by_qid: dict[str, str] = {}
    sha_ok, sha_bad = 0, []
    for qid in order:
        entry = entries[qid]
        graph = load_reference_graph(local / str(entry["graph_rel"]))
        graphs[graph["reference_graph_id"]] = graph
        graph_by_qid[qid] = graph["reference_graph_id"]
        if reference_graph_sha256(graph) == str(entry["graph_sha256"]):
            sha_ok += 1
        else:
            sha_bad.append(qid)
    print(f"[REF] 本地参考图 sha 对账(chain12 manifest): {sha_ok}/{len(order)}"
          f" 一致; 不一致 {len(sha_bad)}")
    if sha_bad:
        print(f"[REF] 不一致 qid(仅计数披露, 前 5): {sha_bad[:5]}")

    # ---- 评测输入(照抄 score_s5b_batch 构建)+ 导出条目 ----
    exports: list[dict] = []
    export_payloads: dict[str, dict] = {}
    cases: dict[str, dict | None] = {}
    no_case: list[str] = []
    for qid in order:
        case = _read_case(synced, qid)
        cases[qid] = case
        digest = str((case or {}).get("export_digest") or "")
        run_id = str((entries[qid] or {}).get("run_id") or "")
        if digest and run_id:
            exports.append({
                "run_id": run_id, "export_digest": digest, "qid": qid,
                "lossy_projection": False,
            })
        else:
            no_case.append(qid)
    reader = _offline_export_reader(synced / "runs", export_payloads)
    evaluation_input = {
        "evaluator_schema_version": PPV1_EVALUATION_VERSION,
        "run_identity": {
            "run_id": f"s5b-batch:{manifest.get('batch_tag') or 's5b'}",
            "profile_version": PPV1_PROFILE_SCHEMA_VERSION,
            "export_schema_version": _NATIVE_EXPORT_VERSION,
        },
        "native_path_exports": exports,
        "reference_graph_manifest": [
            {"reference_graph_id": graphs[graph_by_qid[qid]]
             ["reference_graph_id"],
             "sha256": str(entries[qid]["graph_sha256"]),
             "domain": DOMAIN_TAG,
             "track": TRACK,
             "qid": qid}
            for qid in order],
        "split_manifest": split_manifest,
        "domain": DOMAIN_TAG,
        "track": TRACK,
        "metric_policy_version": "ppv1-evaluation-metrics-proposed",
        "preregistration_id": str(
            (prereg or {}).get("preregistration_id") or "prereg-s5b-pending"),
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
        preregistration=normalize_preregistration(prereg))
    sample_by_graph = {
        str(s.get("reference_graph_id")): s
        for s in output.get("sample_results") or []}
    print(f"[EVAL] evaluate_scientific 状态={output.get('status')}; "
          f"样本 {len(sample_by_graph)}")

    # ---- 逐题:重跑桶 + 逐事件明细 + 候选事件位次 + D2 指纹 ----
    def _recursive_key_count(obj, needle: str) -> int:
        if isinstance(obj, dict):
            return sum(
                (1 if needle in str(k) else 0) + _recursive_key_count(v, needle)
                for k, v in obj.items())
        if isinstance(obj, list):
            return sum(_recursive_key_count(v, needle) for v in obj)
        if isinstance(obj, str):
            return obj.count(needle)
        return 0

    per_qid_detail: dict[str, dict] = {}
    for qid in order:
        graph = graphs[graph_by_qid[qid]]
        sample = sample_by_graph.get(graph_by_qid[qid])
        case = cases.get(qid) or {}
        payload = _paired_payload(export_payloads, sample)
        row = _main_caliber_row(sample, payload, graph)
        edge_matches = (sample or {}).get("predicted_edge_matches") or []
        node_matches = (sample or {}).get("predicted_node_matches") or []
        root_states = _root_strict_states(sample, graph)
        candidates = _candidate_events(payload, root_states)
        matched_ids = {str(e.get("event_id"))
                       for e in ((edge_matches or [{}])[0].get(
                           "matched_events") or [])}
        cand_rows = []
        for position, cand in enumerate(candidates, 1):
            cand_rows.append({
                "position": position,
                "event_id": cand["event_id"],
                "created_at": cand["created_at"],
                "strict_hit": cand["event_id"] in matched_ids,
            })
        node_min = [{
            "node_id": n.get("node_id"),
            "occurrence_id": n.get("occurrence_id"),
            "role": n.get("role"),
            "match_status": n.get("match_status"),
            "identity_scope_cap": n.get("identity_scope_cap") is not None,
        } for n in node_matches]
        per_qid_detail[qid] = {
            "qid": qid,
            "run_id": str((entries[qid] or {}).get("run_id") or ""),
            "reference_graph_id": graph_by_qid[qid],
            "export_digest": str((case or {}).get("export_digest") or ""),
            "run_status": str(case.get("status") or "no_case"),
            "stop_reason": str(case.get("stop_reason") or ""),
            "scoring_status": str((sample or {}).get("scoring_status") or ""),
            "rerun_main": row,
            "metrics_main": {
                "match_status": (metrics_by_qid.get(qid, {}).get("main")
                                 or {}).get("match_status"),
                "rank": (metrics_by_qid.get(qid, {}).get("main") or {})
                .get("rank"),
            },
            "edge_matches": edge_matches,
            "node_matches_min": node_min,
            "candidate_events": cand_rows,
            "n_candidate_events": len(candidates),
            "strict_hit_positions": [c["position"] for c in cand_rows
                                     if c["strict_hit"]],
            "d2_declared_copy_components_occurrences":
                _recursive_key_count(payload, "declared_copy_components")
            if payload else 0,
        }

    # ---- 对齐自检门 ----
    mismatches = []
    rank_mismatches = []
    for qid in order:
        rerun = str(per_qid_detail[qid]["rerun_main"].get("match_status"))
        base = str(per_qid_detail[qid]["metrics_main"].get("match_status"))
        if rerun != base:
            mismatches.append({
                "qid": qid, "metrics_bucket": base, "rerun_bucket": rerun,
                "rerun_rank": per_qid_detail[qid]["rerun_main"].get("rank"),
                "scoring_status": per_qid_detail[qid]["scoring_status"],
            })
            continue
        rr = per_qid_detail[qid]["rerun_main"].get("rank")
        mr = per_qid_detail[qid]["metrics_main"].get("rank")
        if rr != mr:
            rank_mismatches.append({
                "qid": qid, "metrics_rank": mr, "rerun_rank": rr})
    n = len(order)
    agree = n - len(mismatches)
    print(f"[ALIGN] 桶一致 {agree}/{n} "
          f"({agree / n:.1%}); 桶不一致 {len(mismatches)}; "
          f"rank 不一致 {len(rank_mismatches)}(桶一致题内)")
    for m in mismatches[:20]:
        print(f"  - {m['qid'][:24]}… metrics={m['metrics_bucket']} "
              f"rerun={m['rerun_bucket']} status={m['scoring_status']}")

    alignment = {
        "n_questions": n,
        "bucket_agree": agree,
        "bucket_mismatch": len(mismatches),
        "rank_mismatch_within_agree": len(rank_mismatches),
        "agreement_rate": round(agree / n, 4) if n else None,
        "mismatch_detail": mismatches,
        "rank_mismatch_detail": rank_mismatches,
        "gate_threshold": ALIGNMENT_HARD_GATE,
        "gate": "pass" if len(mismatches) <= ALIGNMENT_HARD_GATE else "stop",
        "note": (
            "重跑=本地 HEAD 判分代码 + 本地参考图 + synced payload(离线"
            "读取通道,跳过 DB 权威引用/staleness 两段校验);metrics=chain12 "
            "判分批次产物。不一致可能来源:判分代码版本差/参考图构建差/"
            "读取通道差;如实披露不硬对齐"),
        "no_case_qids": no_case,
    }

    # ---- provenance ----
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True,
        text=True).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT,
        capture_output=True, text=True).stdout.strip())
    worker_versions = sorted({
        str((c or {}).get("worker_version") or "")
        for c in (cases[qid] for qid in order) if c})
    native_versions = sorted({
        str((export_payloads.get(str((cases[qid] or {}).get(
            "export_digest") or "")) or {}).get("native_result_version") or "")
        for qid in order if cases[qid]})
    provenance = {
        "domain_tag": DOMAIN_TAG,
        "track": TRACK,
        "local_git_head": head,
        "local_worktree_dirty": dirty,
        "code_versions": {
            "s5b_scoring": S5B_SCORING_VERSION,
            "evaluator": PPV1_EVALUATION_VERSION,
            "profile_schema": PPV1_PROFILE_SCHEMA_VERSION,
            "native_export": _NATIVE_EXPORT_VERSION,
            "native_result": PPV1_NATIVE_RESULT_VERSION,
        },
        "metrics_side": {
            "s5b_scoring_version": metrics.get("s5b_scoring_version"),
            "data_scope": metrics.get("data_scope"),
            "denominator": metrics.get("denominator"),
            "buckets": metrics.get("buckets"),
        },
        "payload_side": {
            "worker_versions": worker_versions,
            "native_result_versions": native_versions,
            "manifest_schema_version": "ppv1-native-export-3",
            "contract_versions_drift_vs_local": [],
        },
        "reference_graphs": {
            "source": str(local / "reference_graphs"),
            "sha_match_vs_chain12_manifest": f"{sha_ok}/{len(order)}",
            "sha_mismatch_qids": sha_bad,
        },
        "offline_reader_skipped_checks": reader.skipped_checks,
        "preregistration_source": str(local / "preregistration_approval.json"),
        "batch_root": str(batch_root),
        "synced_root": str(synced),
        "llm_calls": 0,
        "network_calls": 0,
    }

    rescore_detail = {
        "provenance": provenance,
        "alignment": alignment,
        "per_qid": per_qid_detail,
    }
    detail_path = out_dir / "rescore_detail.json"
    detail_path.write_text(
        json.dumps(rescore_detail, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")

    if len(mismatches) > ALIGNMENT_HARD_GATE:
        alignment_path = out_dir / "alignment_check.json"
        alignment_path.write_text(
            json.dumps(alignment, ensure_ascii=False, sort_keys=True,
                       indent=1) + "\n", encoding="utf-8")
        print(f"[GATE] 桶不一致 {len(mismatches)} > {ALIGNMENT_HARD_GATE} "
              "⇒ 停下报告版本差异(产物已落盘,不继续三拆/自由基)")
        return 2

    # ---- 2.2 partial 三拆(metrics 桶=partial 的题) ----
    partial_qids = [
        q for q in order
        if str((metrics_by_qid.get(q, {}).get("main") or {})
               .get("match_status"))
        == "matched_participant_coverage_partial"]
    breakdown_rows = []
    for qid in partial_qids:
        d = per_qid_detail[qid]
        edge0 = (d["edge_matches"] or [{}])[0]
        cm = edge0.get("coverage_mismatch_events") or []
        gaps = edge0.get("required_node_gaps") or []
        supers = [e for e in cm if e.get("participant_coverage") == "superset"]
        subsets = [e for e in cm
                   if e.get("participant_coverage") == "partial_subset"]
        cn_only_nodes = [n for n in d["node_matches_min"]
                         if n["match_status"] == "cn_only"]
        capped_nodes = [n for n in d["node_matches_min"]
                        if n["identity_scope_cap"]]
        rerun_status = str(d["rerun_main"].get("match_status"))
        if supers:
            primary = "superset"
            compound = bool(subsets)
        elif subsets:
            primary = "partial_subset"
            compound = False
        elif gaps or rerun_status != "matched_participant_coverage_partial":
            primary = "identity_diff"
            compound = False
        else:
            primary = "unknown_unclassified"
            compound = False
        breakdown_rows.append({
            "qid": qid,
            "class": primary,
            "compound_with": ("partial_subset" if compound else ""),
            "rerun_bucket": rerun_status,
            "metrics_bucket": str(d["metrics_main"].get("match_status")),
            "n_candidate_events": d["n_candidate_events"],
            "n_coverage_mismatch_events": len(cm),
            "n_superset_events": len(supers),
            "n_partial_subset_events": len(subsets),
            "n_required_node_gaps": len(gaps),
            "n_cn_only_nodes": len(cn_only_nodes),
            "n_scope_capped_nodes": len(capped_nodes),
            "superset_with_coproduct": any(
                e.get("coproduct_participants") for e in supers),
            "d2_fingerprint": d["d2_declared_copy_components_occurrences"] > 0,
            "d2_occurrences": d["d2_declared_copy_components_occurrences"],
        })
    cls_counts: dict[str, int] = {}
    for r in breakdown_rows:
        cls_counts[r["class"]] = cls_counts.get(r["class"], 0) + 1
    d2_qids = [q for q in order
               if per_qid_detail[q]["d2_declared_copy_components_occurrences"]
               > 0]
    d2_in_partial = [r["qid"] for r in breakdown_rows if r["d2_fingerprint"]]
    d2_class_counts: dict[str, int] = {}
    for q in d2_qids:
        row = next((r for r in breakdown_rows if r["qid"] == q), None)
        cls = row["class"] if row else (
            "strict" if str(per_qid_detail[q]["rerun_main"].get(
                "match_status")) == "matched_strict"
            else str(per_qid_detail[q]["rerun_main"].get("match_status")))
        d2_class_counts[cls] = d2_class_counts.get(cls, 0) + 1
    breakdown = {
        "domain_tag": DOMAIN_TAG,
        "n_partial": len(partial_qids),
        "class_counts": cls_counts,
        "rows": breakdown_rows,
        "d2_cross_check": {
            "d2_fingerprint_qids_total": len(d2_qids),
            "d2_qids_by_class": d2_class_counts,
            "d2_qids_in_partial": len(d2_in_partial),
            "d2_qids_superset_class": sum(
                1 for r in breakdown_rows
                if r["d2_fingerprint"] and r["class"] == "superset"),
            "d2_qids_superset_with_coproduct": sum(
                1 for r in breakdown_rows
                if r["d2_fingerprint"] and r["class"] == "superset"
                and r["superset_with_coproduct"]),
            "expectation": (
                "对账报告 §6/mimo r35:D2 指纹题应主要落 superset(诚实 "
                "coproduct 参与物 vs root-only 参考);核对结果见上"),
            "d2_qid_list": d2_qids,
        },
    }
    (out_dir / "partial_breakdown.json").write_text(
        json.dumps(breakdown, ensure_ascii=False, sort_keys=True, indent=1)
        + "\n", encoding="utf-8")

    # ---- 2.3 自由基扫描(只披露不做门) ----
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    state_smiles_cache: dict[str, dict[str, str]] = {}

    def _smiles_of(qid: str) -> dict[str, str]:
        if qid not in state_smiles_cache:
            d = per_qid_detail[qid]
            payload = _paired_payload(
                export_payloads,
                sample_by_graph.get(d["reference_graph_id"]))
            state_smiles_cache[qid] = _state_smiles_of(payload or {})
        return state_smiles_cache[qid]

    def _scan_event(qid: str, event_id: str, position: int,
                    universe: str, payload: dict | None) -> dict:
        payload = payload if payload is not None else _paired_payload(
            export_payloads,
            sample_by_graph.get(per_qid_detail[qid]["reference_graph_id"]))
        smi_by_state = _state_smiles_of(payload or {})
        products = []
        for event in (payload or {}).get("events") or []:
            if str(event.get("event_id")) != event_id:
                continue
            body = event.get("payload")
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except (ValueError, TypeError):
                    body = {}
            products = [str(p.get("state_ref")) for p in
                        (body or {}).get("participants") or []
                        if isinstance(p, dict)
                        and str(p.get("side")) == "product"]
            break
        parse_failures = []
        radical_atoms = []
        for state_ref in sorted(set(products)):
            smiles = smi_by_state.get(state_ref) or ""
            mol = Chem.MolFromSmiles(smiles) if smiles else None
            if mol is None:
                parse_failures.append({
                    "state_ref": state_ref, "smiles_present": bool(smiles)})
                continue
            for atom in mol.GetAtoms():
                n_rad = atom.GetNumRadicalElectrons()
                if n_rad > 0:
                    radical_atoms.append({
                        "state_ref": state_ref,
                        "atom_index": atom.GetIdx(),
                        "symbol": atom.GetSymbol(),
                        "num_radical_electrons": n_rad,
                    })
        return {
            "qid": qid,
            "event_id": event_id,
            "candidate_position": position,
            "universe": universe,
            "n_product_states": len(sorted(set(products))),
            "n_parse_failure_states": len(parse_failures),
            "parse_failures": parse_failures,
            "n_radical_atoms": len(radical_atoms),
            "radical_positive": bool(radical_atoms),
            "radical_atoms": radical_atoms,
        }

    partial_set = set(partial_qids)
    scanned: dict[tuple, dict] = {}
    for qid in order:
        d = per_qid_detail[qid]
        payload = _paired_payload(
            export_payloads, sample_by_graph.get(d["reference_graph_id"]))
        for cand in d["candidate_events"]:
            pos = int(cand["position"])
            in_partial = qid in partial_set
            in_rank25 = 2 <= pos <= 5
            if not (in_partial or in_rank25):
                continue
            universe = ("partial_all_positions" if in_partial
                        else "rank2_5_all_questions")
            key = (qid, cand["event_id"])
            if key in scanned:
                scanned[key]["universe"] += "+" + universe
                continue
            scanned[key] = _scan_event(
                qid, cand["event_id"], pos, universe, payload)
    # 对照组:strict 命中题 rank1(身份相等,应天然干净;可选对照全扫)
    control = []
    for qid in order:
        d = per_qid_detail[qid]
        if str(d["rerun_main"].get("match_status")) != "matched_strict":
            continue
        rank1 = next((c for c in d["candidate_events"]
                      if c["strict_hit"]), None)
        if rank1 and int(rank1["position"]) == 1:
            payload = _paired_payload(
                export_payloads,
                sample_by_graph.get(d["reference_graph_id"]))
            control.append(_scan_event(
                qid, rank1["event_id"], 1, "strict_rank1_control", payload))
    scan_rows = list(scanned.values())
    positive = [r for r in scan_rows if r["radical_positive"]]
    control_positive = [r for r in control if r["radical_positive"]]
    parse_fail_states = [
        f for r in scan_rows for f in r["parse_failures"]]
    radical = {
        "domain_tag": DOMAIN_TAG,
        "disclosure_only": True,
        "universe_definition": (
            "43 道 metrics-partial 题的全部候选事件 + 全 298 题候选事件 "
            "rank2-5(主口径候选序 (created_at,event_id));对照 = strict "
            "命中题 rank1 事件"),
        "n_events_scanned": len(scan_rows),
        "n_positive_events": len(positive),
        "n_positive_events_by_universe": {
            u: sum(1 for r in positive if u in r["universe"])
            for u in sorted({r["universe"] for r in scan_rows})},
        "n_radical_atoms_total": sum(r["n_radical_atoms"] for r in scan_rows),
        "n_parse_failure_states": len(parse_fail_states),
        "parse_failures_detail": parse_fail_states[:200],
        "control": {
            "n_events": len(control),
            "n_positive": len(control_positive),
            "note": "strict rank1 事件产物与参考身份相等,预期 0 阳性",
        },
        "positive_sample": positive[:RADICAL_SAMPLE_CAP],
        "positive_rows_full": positive,
    }
    (out_dir / "radical_scan.json").write_text(
        json.dumps(radical, ensure_ascii=False, sort_keys=True, indent=1)
        + "\n", encoding="utf-8")

    # ---- alignment/breakdown/radical 落 analysis + md ----
    (out_dir / "alignment_check.json").write_text(
        json.dumps(alignment, ensure_ascii=False, sort_keys=True, indent=1)
        + "\n", encoding="utf-8")

    md = []
    md.append(f"# 43 道 partial 三拆表(题域 {DOMAIN_TAG},T3 离线重跑)\n")
    md.append(f"- 数据:chain12 离线重跑(本地 HEAD {head[:12]},对齐自检 "
              f"{agree}/{n} 桶一致);重跑口径与判分批次一致才有效,见 "
              f"alignment_check.json")
    md.append(f"- 分拆:{len(partial_qids)} 道 partial → "
              + ", ".join(f"{k} {v}" for k, v in sorted(cls_counts.items()))
              + "\n")
    md.append("| qid | 类 | 复合 | 候选事件 | 失配事件(sup/sub) | 节点缺口 | "
              "cn_only 节点 | D2 指纹 | coproduct superset |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for r in breakdown_rows:
        md.append(
            f"| {r['qid'][:16]}… | {r['class']} | {r['compound_with'] or '-'} "
            f"| {r['n_candidate_events']} "
            f"| {r['n_coverage_mismatch_events']} "
            f"({r['n_superset_events']}/{r['n_partial_subset_events']}) "
            f"| {r['n_required_node_gaps']} | {r['n_cn_only_nodes']} "
            f"| {'Y' if r['d2_fingerprint'] else '-'} "
            f"| {'Y' if r['superset_with_coproduct'] else '-'} |")
    d2x = breakdown["d2_cross_check"]
    md.append("")
    md.append(f"## D2 指纹交叉(declared_copy_components,全批 "
              f"{d2x['d2_fingerprint_qids_total']} 题)")
    md.append(f"- 落 partial:{d2x['d2_qids_in_partial']};落 superset 类:"
              f"{d2x['d2_qids_superset_class']}(其中带 coproduct 参与物 "
              f"{d2x['d2_qids_superset_with_coproduct']});按类分布:"
              f"{json.dumps(d2x['d2_qids_by_class'], ensure_ascii=False)}")
    md.append(f"- 对账报告 §6 预期:D2 指纹题主要落 superset — 核对结果"
              f"如上,原样报告不修饰\n")
    (out_dir / "partial_breakdown.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8")

    rmd = []
    rmd.append(f"# 自由基扫描(题域 {DOMAIN_TAG},只披露不做门,mimo M5 "
               "watch item)\n")
    rmd.append(f"- 扫描面:{radical['n_events_scanned']} 个候选事件"
               f"(43 partial 全位次 + 全 298 题 rank2-5);"
               f"阳性事件 {radical['n_positive_events']};"
               f"阳性原子总数 {radical['n_radical_atoms_total']};"
               f"产物解析失败 state 数 {radical['n_parse_failure_states']}")
    rmd.append(f"- 对照组(strict rank1,身份相等应天然干净):"
               f"{radical['control']['n_positive']}/"
               f"{radical['control']['n_events']} 阳性\n")
    if positive:
        rmd.append("| qid | 事件位次 | 面 | 阳性原子 |")
        rmd.append("|---|---|---|---|")
        for r in positive[:RADICAL_SAMPLE_CAP]:
            atoms = "; ".join(
                f"{a['state_ref'][:10]}…#{a['atom_index']}{a['symbol']}"
                f"({a['num_radical_electrons']})"
                for a in r["radical_atoms"][:4])
            rmd.append(f"| {r['qid'][:16]}… | {r['candidate_position']} "
                       f"| {r['universe']} | {atoms} |")
    else:
        rmd.append("- 无阳性事件")
    rmd.append("")
    rmd.append("> 只披露不设门:是否以及如何处理自由基产物属后续预注册裁定,"
               "本扫描不改任何已冻结判定。")
    (out_dir / "radical_scan_summary.md").write_text(
        "\n".join(rmd) + "\n", encoding="utf-8")

    # ---- /tmp 备份 ----
    run_meta = {
        "provenance": provenance,
        "alignment_gate": alignment["gate"],
        "outputs": [str(p) for p in sorted(out_dir.iterdir())
                    if p.is_file() and not p.name.startswith("funnel_")],
    }
    (tmp_dir / "run_meta.json").write_text(
        json.dumps(run_meta, ensure_ascii=False, sort_keys=True, indent=1)
        + "\n", encoding="utf-8")
    for name in ("rescore_detail.json", "alignment_check.json",
                 "partial_breakdown.json", "partial_breakdown.md",
                 "radical_scan.json", "radical_scan_summary.md"):
        src = out_dir / name
        if src.is_file():
            (tmp_dir / name).write_bytes(src.read_bytes())

    # ---- 控制台摘要 ----
    print("[BREAKDOWN] 三拆计数:", json.dumps(cls_counts, ensure_ascii=False))
    print(f"[D2] 指纹题全批 {len(d2_qids)};落 partial "
          f"{d2x['d2_qids_in_partial']};落 superset 类 "
          f"{d2x['d2_qids_superset_class']}(带 coproduct "
          f"{d2x['d2_qids_superset_with_coproduct']})")
    print(f"[RADICAL] 扫描 {radical['n_events_scanned']} 事件;阳性 "
          f"{radical['n_positive_events']};原子 "
          f"{radical['n_radical_atoms_total']};解析失败 state "
          f"{radical['n_parse_failure_states']};对照(strict rank1)阳性 "
          f"{radical['control']['n_positive']}/"
          f"{radical['control']['n_events']}")
    print(f"[OUT] {out_dir} + {tmp_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
