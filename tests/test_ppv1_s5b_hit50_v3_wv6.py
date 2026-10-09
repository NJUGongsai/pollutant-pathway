"""PPV1 S5b HIT50 v3 W-V6 —— mimo r27 判断面一附条件工程落地(三件)。

1. **§9-④ 程序门**(``s5b_scoring.score_s5b_batch``):评分聚合前落
   程序检查 —— data_scope=real ∧ 任一 pairing basis 非 qid_strict ⇒
   S5bScoringError(结构化;与 evaluation-5 首消费守卫双保险,判分
   入口独立复核,覆盖守卫未及的任何非 strict 值;synthetic 档不受
   影响)。正控:合成档 fallback basis 聚合照旧;负控:real + 非
   qid_strict ⇒ 拒。
2. **配对唯一消费入口锁**:`_pair_exports_to_samples`` 全仓唯一活动
   调用 = ``evaluate_scientific``(入口矩阵登记见 evaluation.py 模块
   docstring W-V6.2 节);本测试源码扫描断言唯一活动调用点(新增第
   二调用 ⇒ 红,须显式扩登记)。
3. **触发条件等价性写死**:L01 守卫 detail 携带机读
   ``trigger_equivalence``("触发 ⇔ 两个 qid 映射皆空;整批二档;
   改逐图混合须同步改逐图判")。

全部合成夹具(零金标/零真实 298;fake approved 形状仅程序门触发器,
非用户/teacher 审批)。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.pollutant import preregistration  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    EvaluationContractError,
    evaluate_scientific,
)
from pathway_v43.pollutant.s5b_scoring import (  # noqa: E402
    S5bScoringError,
    score_s5b_batch,
)

from test_ppv1_s5a_schema import (  # noqa: E402
    reference_graph_sha256,
    synth_evaluation_input,
    synth_reference_graph,
    synth_split_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH_ID = "rg-synth-1"


def _fake_output(bases: dict[str, str]) -> dict:
    """模拟评测器产物(程序门单测:仅 bases_by_graph 形状;零样本)。

    real 档下 evaluation-5 首消费守卫拦截 root_identity_fallback;
    本夹具模拟**守卫未及的非 strict 值**(未来逐图混合档/新档),
    验证判分入口双保险独立生效。
    """
    return {
        "status": "pending_user_teacher_decision",
        "sample_results": [],
        "coverage_report": {
            "pairing": {"bases_by_graph": dict(bases)}},
    }


def _minimal_batch_root(tmp_path: Path) -> Path:
    """最小批根(1 题;manifest/split/图;零 cases ⇒ 零导出条目)。"""
    batch_root = tmp_path / "batch"
    batch_root.mkdir(parents=True)
    graph = synth_reference_graph(GRAPH_ID)
    graph_path = batch_root / "graphs" / f"{GRAPH_ID}.json"
    graph_path.parent.mkdir(parents=True)
    graph_path.write_text(json.dumps(graph, ensure_ascii=False),
                          encoding="utf-8")
    manifest = {
        "batch_tag": "wv6gate",
        "n_questions": 1,
        "registration_order": ["SYN-Q1"],
        "entries": [{
            "qid": "SYN-Q1",
            "reference_graph_id": GRAPH_ID,
            "graph_rel": f"graphs/{GRAPH_ID}.json",
            "graph_sha256": reference_graph_sha256(graph),
            "run_id": "wv6-run-1",
            "substrate_smiles": "CCO",
        }],
    }
    (batch_root / "batch_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (batch_root / "split_manifest.json").write_text(
        json.dumps(synth_split_manifest(graph_id=GRAPH_ID)),
        encoding="utf-8")
    return batch_root


_APPROVED = {
    "preregistration_id": "prereg-wv6-synth",
    "approval_status": "approved",
    "user_authorization": "synthetic-test-authorization",
}


def _score(tmp_path, batch_root: Path, *, scope: str, bases):
    import pathway_v43.pollutant.s5b_scoring as sc

    real_evaluate = sc.evaluate_scientific

    def _fake_evaluate(evaluation_input, **kwargs):
        return _fake_output(bases)

    sc.evaluate_scientific = _fake_evaluate
    try:
        return score_s5b_batch(
            batch_root, runs_root=tmp_path / "runs",
            data_scope=scope, preregistration=dict(_APPROVED))
    finally:
        sc.evaluate_scientific = real_evaluate


# ================================================================ 程序门

def test_wv6_program_gate_real_non_strict_rejects(tmp_path) -> None:
    """负控:real ∧ 任一 pairing basis 非 qid_strict ⇒ S5bScoringError
    (kind 机读;先于聚合/落盘)。守卫未及的"未来混合档"值同样拒
    (双保险 = 判分入口不依赖评测器内部异常路径)。"""
    batch_root = _minimal_batch_root(tmp_path)
    with pytest.raises(S5bScoringError) as excinfo:
        _score(tmp_path, batch_root, scope="real",
               bases={GRAPH_ID: "root_identity_fallback"})
    detail = excinfo.value.detail
    assert detail["kind"] == "s5b_real_pairing_not_all_qid_strict"
    assert detail["data_scope"] == "real"
    assert detail["non_qid_strict_bases"] == {
        GRAPH_ID: "root_identity_fallback"}
    # 非 fallback 的非 strict 值(未来混合档形状)同样拒
    with pytest.raises(S5bScoringError) as excinfo2:
        _score(tmp_path, batch_root, scope="real",
               bases={GRAPH_ID: "per_graph_mixed_hypothetical"})
    assert excinfo2.value.detail["kind"] == \
        "s5b_real_pairing_not_all_qid_strict"
    # real + 全 qid_strict ⇒ 程序门不触发(聚合照常;零样本留分母)
    agg = _score(tmp_path, batch_root, scope="real",
                 bases={GRAPH_ID: "qid_strict"})
    assert agg["denominator"] == 1


def test_wv6_program_gate_synthetic_fallback_aggregates(tmp_path) -> None:
    """正控:synthetic 档 fallback basis 聚合照旧(程序门零影响;
    合成回退配对披露不变)。"""
    batch_root = _minimal_batch_root(tmp_path)
    agg = _score(tmp_path, batch_root, scope="synthetic_rule_level",
                 bases={GRAPH_ID: "root_identity_fallback"})
    assert agg["data_scope"] == "synthetic_rule_level"
    assert agg["denominator"] == 1
    # 零样本 ⇒ 命中 0;分母闭合照旧(判分互斥桶总 = 分母)
    assert agg["main_caliber"]["hit@1"] == 0
    assert sum(v for k, v in agg["buckets"].items()
               if not k.startswith("run_")) == agg["denominator"]


# ================================================================ 入口锁

def test_wv6_pairing_single_active_call_site_locked() -> None:
    """W-V6.2:``_pair_exports_to_samples`` 全仓唯一活动调用 =
    evaluate_scientific(def 行/注释/文档行除外;新增第二调用点 ⇒ 红,
    须显式扩展 evaluation.py 的 W-V6.2 入口矩阵登记)。"""
    pattern = re.compile(r"_pair_exports_to_samples\(")
    active: list[tuple[str, int, str]] = []
    for py in sorted((REPO_ROOT / "src").rglob("*.py")):
        for lineno, line in enumerate(
                py.read_text(encoding="utf-8").splitlines(), 1):
            if not pattern.search(line):
                continue
            stripped = line.strip()
            if stripped.startswith("def _pair_exports_to_samples"):
                continue  # 定义行
            if stripped.startswith("#"):
                continue  # 注释行
            if py.name == "evaluation.py" and \
                    "pairing = _pair_exports_to_samples(" in line:
                continue  # 已登记的唯一活动调用(evaluate_scientific 内)
            active.append((str(py), lineno, stripped[:80]))
    assert active == [], (
        f"发现未登记的 _pair_exports_to_samples 活动调用(唯一消费入口"
        f"= evaluate_scientific;新增调用须先扩展 evaluation.py W-V6.2 "
        f"入口矩阵登记):{active}")
    # 定义存在且唯一(防重定义绕过)
    defs = [
        (str(py), lineno) for py in (REPO_ROOT / "src").rglob("*.py")
        for lineno, line in enumerate(
            py.read_text(encoding="utf-8").splitlines(), 1)
        if line.strip().startswith("def _pair_exports_to_samples")]
    assert len(defs) == 1, defs


def test_wv6_l01_trigger_equivalence_written_down(tmp_path) -> None:
    """W-V6.3:L01 守卫 detail 写死触发等价性(机读 trigger_equivalence
    字段:触发 ⇔ 两个 qid 映射皆空;整批二档;改逐图混合须同步改
    逐图判),守卫行为保持(合成反例轴照旧拒)。"""
    from test_ppv1_s5b_pairing import (  # noqa: F401
        QID_A,
        _multi_run_reader,
        _plan_coproduct,
        _plan_no_coproduct,
        _qid_graph,
        _run,
        _two_graph_split,
    )

    GRAPH_A = "rg-wv6-a"
    run_a = _run(tmp_path, "s5b-wv6-a", _plan_coproduct())
    run_b = _run(tmp_path, "s5b-wv6-b", _plan_no_coproduct())
    graphs = [_qid_graph(GRAPH_A, QID_A),
              _qid_graph("rg-wv6-b", "RXNG-SYNTH-B")]
    exports = [
        {"run_id": "s5b-wv6-a",
         "export_digest": run_a["native_export"]["export_digest"]},
        {"run_id": "s5b-wv6-b",
         "export_digest": run_b["native_export"]["export_digest"]},
    ]
    evaluation_input = synth_evaluation_input(
        graphs=graphs, split_manifest=_two_graph_split(
            [GRAPH_A, "rg-wv6-b"]), exports=exports, data_scope="real")
    reader = _multi_run_reader(
        tmp_path / "runs", ["s5b-wv6-a", "s5b-wv6-b"])
    fake = preregistration.build_preregistration_template(
        note="SYNTHETIC: wv6 trigger equivalence control")
    fake["approval_status"] = "approved"
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(
            evaluation_input,
            reference_graphs={g["reference_graph_id"]: g for g in graphs},
            native_export_reader=reader,
            preregistration=fake)
    detail = excinfo.value.detail
    assert detail["kind"] == "real_data_root_identity_fallback_forbidden"
    assert "trigger_equivalence" in detail
    # 等价性内容:两个 qid 映射皆空 + 逐图混合前瞻声明
    text = str(detail["trigger_equivalence"])
    assert "manifest_qids empty" in text and "export_qids empty" in text
    assert "逐图" in text
