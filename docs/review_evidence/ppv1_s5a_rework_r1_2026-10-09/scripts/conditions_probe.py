"""S5A-02 反例复现探针(复制自评审 conditions/scripts/probe.py 的
conditions() 段,仅改 ROOT/sys.path 指向当前仓;fresh tmp 执行)。

20 案逐案走真实 public 链:start_run(plan 带 fact)→ ledger 导出首读
→ evaluate_scientific;另按评审对照口径构造冻结同源 Requirement/
事实(build_requirement/build_condition_fact/assess_candidate_
conditions),记录公开评测桶 vs 冻结同源评估,不修改产品行为。
"""
from __future__ import annotations

import copy
import json
import sys
import traceback
from pathlib import Path

REPO = Path("/Volumes/CC/Enzyme_Agent/dependingv43")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "probe" / "outputs"
WORK = ROOT / "work"
OUT.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(REPO / "tests"), str(REPO / "src")]

import test_ppv1_s5a_evaluator as e  # noqa: E402
import test_ppv1_s5a_schema as s  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    classify_condition_requirement,
    evaluate_scientific,
)
from pathway_v43.pollutant.path_context import (  # noqa: E402
    assess_candidate_conditions,
    build_condition_fact,
    build_path_context,
    build_requirement,
)
from pathway_v43.pollutant.preregistration import (  # noqa: E402
    build_preregistration_template,
)
from pathway_v43.domain.models import canonical_json  # noqa: E402


def save(name: str, obj) -> None:
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2,
                   default=str) + "\n")


def req(key, value, **kwargs):
    return {**s.condition_scope(key, value),
            "subject_scenario_ref": "", **kwargs}


def fact(key, value, status="known_present", unit=""):
    return {"key": key, "value": value, "status": status,
            "unit": unit, "source_ref": "src:synthetic-observation"}


CASES = [
    ("missing_fact", req("oxygen_regime", "aerobic"), [],
     "aerobic", "entity"),
    ("same_known_present", req("oxygen_regime", "aerobic"),
     [fact("oxygen_regime", "aerobic")], "aerobic", "entity"),
    ("opposite_known_present", req("oxygen_regime", "aerobic"),
     [fact("oxygen_regime", "anaerobic")], "aerobic", "entity"),
    ("same_known_absent", req("oxygen_regime", "aerobic"),
     [fact("oxygen_regime", "aerobic", "known_absent")], "aerobic",
     "entity"),
    ("other_known_absent", req("oxygen_regime", "aerobic"),
     [fact("oxygen_regime", "anaerobic", "known_absent")], "aerobic",
     "entity"),
    ("numeric_known_absent", req("temperature_C", "20-30", unit="C"),
     [fact("temperature_C", 25, "known_absent", "C")],
     {"lo": 20, "hi": 30}, "range"),
    ("entity_other_known_absent", req("electron_acceptor", "O2"),
     [fact("electron_acceptor", "NO3", "known_absent")], "O2", "entity"),
    ("canonical_unit_positive", req("temperature_C", "20-30", unit="C"),
     [fact("temperature_C", 25, unit="C")], {"lo": 20, "hi": 30},
     "range"),
    ("unit_unknown", req("temperature_C", "20-30", unit="C"),
     [fact("temperature_C", 25)], {"lo": 20, "hi": 30}, "range"),
    ("unit_mismatch_K", req("temperature_C", "20-30", unit="C"),
     [fact("temperature_C", 30, unit="K")], {"lo": 20, "hi": 30},
     "range"),
    ("unit_noncanonical_F", req("temperature_C", "20-30", unit="C"),
     [fact("temperature_C", 25, unit="F")], {"lo": 20, "hi": 30},
     "range"),
    ("conflicting_facts_conflict_first",
     req("oxygen_regime", "aerobic"),
     [fact("oxygen_regime", "anaerobic"),
      fact("oxygen_regime", "aerobic")], "aerobic", "entity"),
    ("conflicting_facts_satisfied_first",
     req("oxygen_regime", "aerobic"),
     [fact("oxygen_regime", "aerobic"),
      fact("oxygen_regime", "anaerobic")], "aerobic", "entity"),
    ("necessity_no_source",
     req("oxygen_regime", "aerobic", source_refs=[]),
     [fact("oxygen_regime", "anaerobic")], "aerobic", "entity"),
    ("zero_point_present", req("temperature_C", "0", unit="C"),
     [fact("temperature_C", 0, unit="C")], 0, "point"),
    ("negative_interval_present", req("temperature_C", "-5-10", unit="C"),
     [fact("temperature_C", 0, unit="C")], {"lo": -5, "hi": 10},
     "range"),
    ("dict_interval_present", req("temperature_C", "20-30", unit="C"),
     [fact("temperature_C", {"lo": 22, "hi": 26}, unit="C")],
     {"lo": 20, "hi": 30}, "range"),
    ("matrix_label_unresolved", req("matrix", "soil"),
     [fact("matrix", "activated_sludge")], "soil", "entity"),
    ("required_absent_fact_absent",
     req("oxygen_regime", "aerobic", status="known_absent"),
     [fact("oxygen_regime", "aerobic", "known_absent")], None, None),
    ("required_absent_fact_present",
     req("oxygen_regime", "aerobic", status="known_absent"),
     [fact("oxygen_regime", "aerobic")], None, None),
]

summary = []
for name, rq, fs, value, basis in CASES:
    plan = e._plan(select=1)
    plan["condition_facts"] = copy.deepcopy(fs)
    graph = s.synth_reference_graph(graph_id="rg-" + name)
    graph["edges"] = graph["edges"][:1]
    graph["edges"][0]["condition_requirements"] = [rq]
    for n in graph["nodes"]:
        n["condition_scope"] = []
    runid = "condition-" + name
    case = {"name": name, "reference_graph": graph,
            "ppv1_plan": plan,
            "literal_classifier": classify_condition_requirement(rq, fs)}
    try:
        runs, out = e._run(WORK / name, runid, plan)
        read = e._reader(runs, runid)
        request = s.synth_evaluation_input(
            graphs=[graph],
            split_manifest=s.synth_split_manifest(
                graph_id=graph["reference_graph_id"]),
            exports=[{"run_id": runid,
                      "export_digest":
                      out["native_export"]["export_digest"]}])
        request["run_identity"]["run_id"] = runid
        payload_read = read(request["native_path_exports"][0])
        result = evaluate_scientific(
            request,
            reference_graphs={graph["reference_graph_id"]: graph},
            native_export_reader=read,
            preregistration=build_preregistration_template())
        case.update(run_output=out, evaluation_input=request,
                    validated_reader_output=payload_read,
                    evaluation_output=result)
        env = result["sample_results"][0]["environment_conflicts"]
        if value is not None:
            frozen_facts = [build_condition_fact(**f) for f in fs]
            frozen_req = build_requirement(
                key=rq["key"], level=rq["required"], value=value,
                value_basis=basis, source_refs=rq["source_refs"])
            ctx = build_path_context(
                condition_facts=frozen_facts,
                assessment_scope=[rq["key"]])
            assessed = assess_candidate_conditions(
                ctx, {"hypothesis_id": "synthetic-condition-compare",
                      "requirements": [frozen_req.to_dict()]})
            case.update(frozen_context=ctx.to_dict(),
                        frozen_requirement=frozen_req.to_dict(),
                        frozen_assessment=assessed.to_dict())
            public = assessed.to_dict()["per_requirement"][0]
        else:
            public = {
                "status": "not_directly_representable",
                "reason": ("Requirement has no status=known_absent field; "
                           "this case is reference schema semantics "
                           "only")}
            case["frozen_not_compared"] = public
        row = {
            "name": name,
            "literal_classifier": case["literal_classifier"],
            "public_evaluation_buckets": env["buckets"],
            "public_evaluation_status": result["status"],
            "frozen_assessment": public,
            "scoring_status":
                result["sample_results"][0]["scoring_status"]}
        summary.append(row)
        case["summary"] = row
        print(name, canonical_json(row), flush=True)
    except BaseException as ex:  # noqa: BLE001 —— 结构化披露
        case["exception"] = {
            "type": type(ex).__name__, "message": str(ex),
            "detail": getattr(ex, "detail", None),
            "traceback": traceback.format_exc()}
        summary.append({"name": name, "exception": case["exception"]})
        print("CASE_ERROR", name, type(ex).__name__, str(ex),
              flush=True)
    save("conditions/" + name + ".json", case)

save("conditions_summary.json", summary)
if any("exception" in x for x in summary):
    raise RuntimeError(
        "One or more condition public cases failed before observation")
print("conditions probe complete:", len(summary), "cases")
