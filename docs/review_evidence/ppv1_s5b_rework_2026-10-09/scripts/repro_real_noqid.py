"""S5B-L01 公开反例复现脚本(修前/修后两用)。

复制评审公开 real 标签双无 qid 反例(复审证据
ppv1_s5b_codex_2026-10-09/pairing/outputs/real_label_noqid_public_*)
到 fresh /private/tmp:两题同 CCO 根合成 run(公共 start_run 真实
生成)、两侧条目全部不声明 qid、data_scope='real' +
approval_status='approved'(合成 approved 形状——只触发程序门,
不代表真实数据/金标/用户或 teacher 审批)。

--expect prefault:修前基线(a399d6e/evaluation-4)——期望复现缺口
(evaluate_scientific 返回输出:codex-a scored 进聚合、codex-b
not_evaluated、两图 root_identity_fallback);
--expect guarded:修后(当前工作树/evaluation-5)——期望结构化拒
(EvaluationContractError kind=real_data_root_identity_fallback_
forbidden,零样本评分/聚合/结果写入:异常先于输出构造)。

正控(两树都须保持):synthetic 双无 qid 回退 scored;real 严格
qid 全 scored;real+未批准预注册先拒。全部数据为合成夹具,零
网络零 LLM 零费用,不外推 dev/298。
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

tree = Path(sys.argv[1]).resolve()
case_work = Path(sys.argv[2]).resolve()
outdir = Path(sys.argv[3]).resolve()
expect = sys.argv[4]
assert expect in ("prefault", "guarded")
sys.path[:0] = [str(tree / "src"), str(tree / "tests")]

from test_ppv1_s5b_pairing import (  # noqa: E402
    _multi_run_reader,
    _plan_coproduct,
    _plan_no_coproduct,
    _qid_graph,
    _run,
    _two_graph_split,
)
from test_ppv1_s5a_schema import synth_evaluation_input  # noqa: E402
from pathway_v43.pollutant import preregistration  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    EvaluationContractError,
    evaluate_scientific,
)

outdir.mkdir(parents=True, exist_ok=True)
records = []


def save(name: str, obj) -> str:
    path = outdir / (name + ".json")
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    return str(path)


GRAPH_A, GRAPH_B = "codex-a", "codex-b"
QID_A, QID_B = "SYNTH-CODEX-QID-A", "SYNTH-CODEX-QID-B"
run_a = _run(case_work, "codex-pair-a", _plan_coproduct())
run_b = _run(case_work, "codex-pair-b", _plan_no_coproduct())
digest_a = run_a["native_export"]["export_digest"]
digest_b = run_b["native_export"]["export_digest"]
graphs = [_qid_graph(GRAPH_A, QID_A), _qid_graph(GRAPH_B, QID_B)]
graphs_map = {g["reference_graph_id"]: g for g in graphs}
reader = _multi_run_reader(case_work / "runs", ["codex-pair-a",
                                                "codex-pair-b"])
exports_noqid = [
    {"run_id": "codex-pair-a", "export_digest": digest_a},
    {"run_id": "codex-pair-b", "export_digest": digest_b},
]
exports_qid = [
    {"run_id": "codex-pair-a", "export_digest": digest_a, "qid": QID_A},
    {"run_id": "codex-pair-b", "export_digest": digest_b, "qid": QID_B},
]


def two_input(exports, *, scope, interface=True):
    inp = synth_evaluation_input(
        graphs=graphs, split_manifest=_two_graph_split(list(graphs_map)),
        exports=json.loads(json.dumps(exports)), data_scope=scope,
        interface=interface)
    return inp


def evaluate(name, inp, prereg):
    save(name + "_input", {
        "evaluation_input": inp, "reference_graphs": graphs_map,
        "preregistration": prereg, "synthetic_only": True})
    try:
        out = evaluate_scientific(
            inp, reference_graphs=graphs_map,
            native_export_reader=reader, preregistration=prereg)
    except Exception as exc:  # noqa: BLE001 —— 结构化记录
        err = {
            "exception": type(exc).__name__,
            "kind": (getattr(exc, "detail", {}) or {}).get("kind"),
            "detail": getattr(exc, "detail", None),
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "output_object": None,
            "sample_results": None,
            "aggregate_metrics": None,
        }
        save(name + "_error", err)
        return {"raised": err}
    save(name + "_output", out)
    return {"output": out}


fake_approved = preregistration.build_preregistration_template(
    note="SYNTHETIC_APPROVAL_TAG_ONLY: adversarial interface fixture, "
         "not user/teacher approval")
fake_approved["approval_status"] = "approved"
fake_approved["preregistration_id"] = \
    "synthetic-prereg-interface-approved-shape"
pending_prereg = preregistration.build_preregistration_template()

# ---- ①核心:real 标签 + 双无 qid + fake approved 形状(评审反例) ----
real_in = two_input(exports_noqid, scope="real", interface=False)
result = evaluate("real_label_noqid_public", real_in, fake_approved)
if expect == "prefault":
    out = result["output"]
    assert out is not None, "修前基线应返回输出(缺口复现),而非异常"
    statuses = {s["reference_graph_id"]: s["scoring_status"]
                for s in out["sample_results"]}
    bases = out["coverage_report"]["pairing"]["bases_by_graph"]
    assert statuses == {GRAPH_A: "scored",
                        GRAPH_B: "not_evaluated_export_missing"}, statuses
    assert set(bases.values()) == {"root_identity_fallback"}, bases
    assert len(out["aggregate_metrics"]) > 0, "修前错误评分已进入聚合"
    records.append({
        "case": "real_label_noqid_public",
        "verdict": "PREFAULT_REPRODUCED",
        "statuses": statuses, "bases": bases,
        "n_aggregate_metrics": len(out["aggregate_metrics"]),
        "output_sha256": out["output_sha256"]})
else:
    raised = result["raised"]
    assert raised is not None, "修后应结构化拒(evaluation-5 守卫)"
    assert raised["exception"] == "EvaluationContractError"
    assert raised["kind"] == "real_data_root_identity_fallback_forbidden"
    assert raised["output_object"] is None
    assert raised["sample_results"] is None
    assert raised["aggregate_metrics"] is None
    assert raised["detail"]["data_scope"] == "real"
    assert raised["detail"]["pairing_basis"] == \
        "root_identity_fallback"
    assert raised["detail"]["graphs_without_declared_qid"] == \
        [GRAPH_A, GRAPH_B]
    assert raised["detail"]["export_entries_without_declared_qid"] == \
        sorted([digest_a, digest_b])
    records.append({
        "case": "real_label_noqid_public",
        "verdict": "GUARDED_STRUCTURED_REJECT",
        "kind": raised["kind"],
        "zero_sample_scoring": True, "zero_aggregation": True,
        "zero_persisted_output": True})

# ---- ②正控:synthetic 双无 qid 回退保持(两树同绿) ----
syn_out = evaluate(
    "synthetic_noqid_control",
    two_input(exports_noqid, scope="synthetic_rule_level"),
    pending_prereg)["output"]
assert syn_out is not None
syn_a = next(s for s in syn_out["sample_results"]
             if s["reference_graph_id"] == GRAPH_A)
assert syn_a["scoring_status"] == "scored"
assert syn_a["pairing"]["basis"] == "root_identity_fallback"
records.append({"case": "synthetic_noqid_control", "verdict": "KEPT",
                "status": syn_a["scoring_status"],
                "basis": syn_a["pairing"]["basis"]})

# ---- ③正控:real 严格 qid 合法(两树同绿) ----
strict_in = two_input(exports_qid, scope="real", interface=False)
for entry, qid in zip(strict_in["reference_graph_manifest"],
                      (QID_A, QID_B)):
    entry["qid"] = qid
rs = evaluate("real_label_strict_control", strict_in, fake_approved)
rs_out = rs["output"]
assert rs_out is not None, "real 严格 qid 正控必须保持合法"
for s in rs_out["sample_results"]:
    assert s["scoring_status"] == "scored"
    assert s["pairing"]["basis"] == "qid_strict"
records.append({"case": "real_label_strict_control", "verdict": "KEPT",
                "bases": rs_out["coverage_report"]["pairing"][
                    "bases_by_graph"]})

# ---- ④正控:real + 未批准预注册先拒(两树同绿) ----
pend = evaluate("real_pending_prereg_control", real_in, pending_prereg)
assert pend["raised"] is not None
assert pend["raised"]["kind"] == \
    "real_data_requires_approved_preregistration"
records.append({"case": "real_pending_prereg_control",
                "verdict": "KEPT",
                "kind": pend["raised"]["kind"]})

summary = {
    "expect": expect,
    "tree": str(tree),
    "case_work": str(case_work),
    "run_ids": ["codex-pair-a", "codex-pair-b"],
    "export_digests": {"codex-pair-a": digest_a,
                       "codex-pair-b": digest_b},
    "all_data_synthetic": True,
    "no_network": True,
    "records": records,
}
save("summary", summary)
print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
