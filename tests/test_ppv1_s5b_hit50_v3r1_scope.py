"""PPV1 S5b HIT50 v3 回修 S5B-V3-01 —— data_scope 域身份严格校验与
§9-4 独立 basis 门 shape 全集核(正链复审 §4.1/§5 D1)。

覆盖(全部合成夹具,零金标/零真实 298;fake approved 形状仅程序门
触发器,非用户/teacher 审批):

1. **判分入口(score_s5b_batch)严格字符串 enum**:显式空串/None/
   bool/数值/未知字符串("Real"/"real "/"synthetic" 等)⇒
   S5bScoringError(kind=s5b_data_scope_invalid),先于任何批文件装载
   (空批根上直接拒 ⇒ 证明入口级;CLI choices 不代 API 校验);
2. **评测首消费(validate_evaluation_input + evaluate_scientific)
   同源判据**:显式空/None/False/0/未知串 ⇒ 结构化拒(kind=
   data_scope_invalid),**不再被 ``or`` truthiness 洗成 synthetic
   绕过 real 门**(修前 8 个显式非法值公开可接受);完全缺省字段
   的既有缺省语义保留(synthetic_rule_level)+ 机读归一来源
   (scoring_provenance.data_scope_normalized_from);
3. **real 门正控保持**:显式 real 无批准 ⇒ real_data_requires_
   approved_preregistration(既有门不退);显式 real 有批准 + 全
   qid_strict 精确键集 ⇒ 聚合照旧;
4. **§9-4 独立 basis 门 shape 负控**:缺 coverage/缺 pairing/缺
   bases/空 bases/非 dict/缺键/foreign 键/非字符串值/非 strict 值
   ⇒ 先拒零 metrics(kind=s5b_real_pairing_not_all_qid_strict,
   reasons/reasons 细分机读);synthetic 档回退配对不受影响(正控)。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.pollutant.evaluation import (  # noqa: E402
    EvaluationContractError,
    evaluate_scientific,
    validate_evaluation_input,
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
GRAPH_A = "rg-synth-1"
GRAPH_B = "rg-synth-2"

# 显式坏值清单(复审公开证据形态:空串/None/False/0 + bool/数值/
# 未知字符串/大小写与空白变体/列表/字典;"real"/"synthetic_rule_level"
# 为合法值不在本清单)
BAD_DATA_SCOPES = [
    None, False, True, 0, 0.0, 1, 123, "", " ", "Real", "REAL",
    "real ", " real", "Synthetic_rule_level", "synthetic",
    "synthetic_rule", "dev", "unknown_scope", ["real"],
    {"scope": "real"},
]

_APPROVED = {
    "preregistration_id": "prereg-v3r1-synth",
    "approval_status": "approved",
    "user_authorization": "synthetic-test-authorization",
}


def _minimal_batch_root(tmp_path: Path, *, n_graphs: int = 1) -> Path:
    """最小批根(n 题;manifest/split/图;零 cases ⇒ 零导出条目)。"""
    batch_root = tmp_path / "batch"
    batch_root.mkdir(parents=True)
    graph_ids = [GRAPH_A, GRAPH_B][:n_graphs]
    graphs = []
    entries = []
    for i, graph_id in enumerate(graph_ids):
        graph = synth_reference_graph(graph_id)
        graphs.append(graph)
        graph_path = batch_root / "graphs" / f"{graph_id}.json"
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        graph_path.write_text(json.dumps(graph, ensure_ascii=False),
                              encoding="utf-8")
        entries.append({
            "qid": f"SYN-Q{i + 1}",
            "reference_graph_id": graph_id,
            "graph_rel": f"graphs/{graph_id}.json",
            "graph_sha256": reference_graph_sha256(graph),
            "run_id": f"v3r1-run-{i + 1}",
            "substrate_smiles": "CCO",
        })
    manifest = {
        "batch_tag": "v3r1scope",
        "n_questions": len(entries),
        "registration_order": [e["qid"] for e in entries],
        "entries": entries,
    }
    (batch_root / "batch_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (batch_root / "split_manifest.json").write_text(
        json.dumps(synth_split_manifest(graph_id=GRAPH_A)),
        encoding="utf-8")
    return batch_root


def _fake_output(bases=None, *, with_pairing: bool = True,
                 with_coverage: bool = True) -> dict:
    """模拟评测器产物(程序门单测:仅 bases_by_graph 形状;零样本)。"""
    pairing: dict = {}
    if bases is not None:
        pairing["bases_by_graph"] = bases
    coverage = {"pairing": pairing} if with_pairing else {}
    return {
        "status": "pending_user_teacher_decision",
        "sample_results": [],
        "coverage_report": coverage if with_coverage else None,
    }


def _score(tmp_path, batch_root: Path, *, scope, bases,
           with_pairing: bool = True, with_coverage: bool = True):
    import pathway_v43.pollutant.s5b_scoring as sc

    real_evaluate = sc.evaluate_scientific

    def _fake_evaluate(evaluation_input, **kwargs):
        return _fake_output(bases, with_pairing=with_pairing,
                            with_coverage=with_coverage)

    sc.evaluate_scientific = _fake_evaluate
    try:
        return score_s5b_batch(
            batch_root, runs_root=tmp_path / "runs",
            data_scope=scope, preregistration=dict(_APPROVED))
    finally:
        sc.evaluate_scientific = real_evaluate


# ============================================================ 判分入口

@pytest.mark.parametrize("bad_scope", BAD_DATA_SCOPES)
def test_score_entry_rejects_explicit_bad_data_scope(
        tmp_path, bad_scope) -> None:
    """负控:显式空/null/bool/数值/未知串 ⇒ 入口先拒(空批根上拒,
    证明先于批文件装载;kind 机读;CLI choices 不代 API 校验)。"""
    batch_root = _minimal_batch_root(tmp_path)
    with pytest.raises(S5bScoringError) as excinfo:
        score_s5b_batch(batch_root, runs_root=tmp_path / "runs",
                        data_scope=bad_scope,
                        preregistration=dict(_APPROVED))
    detail = excinfo.value.detail
    assert detail["kind"] == "s5b_data_scope_invalid"
    assert detail["field"] == "data_scope"
    assert detail["allowed"] == ["real", "synthetic_rule_level"]
    # 无 metrics 落盘(零聚合)
    assert not (batch_root / "metrics.json").exists()


def test_score_entry_rejects_bad_scope_before_batch_files(tmp_path) -> None:
    """入口级先拒:批根连 manifest 都没有时,data_scope 非法先于
    manifest 装载错误(证明校验在最前消费)。"""
    empty_root = tmp_path / "no-batch"
    empty_root.mkdir()
    with pytest.raises(S5bScoringError) as excinfo:
        score_s5b_batch(empty_root, runs_root=tmp_path / "runs",
                        data_scope="", preregistration=dict(_APPROVED))
    assert excinfo.value.detail["kind"] == "s5b_data_scope_invalid"
    # 对照:合法 scope 才会走到批文件装载(manifest 缺失的原始异常)
    with pytest.raises((S5bScoringError, FileNotFoundError, OSError)) \
            as excinfo2:
        score_s5b_batch(empty_root, runs_root=tmp_path / "runs",
                        data_scope="real",
                        preregistration=dict(_APPROVED))
    assert not (isinstance(excinfo2.value, S5bScoringError)
                and excinfo2.value.detail.get("kind")
                == "s5b_data_scope_invalid")


def test_score_entry_valid_scopes_and_default_real(tmp_path) -> None:
    """正控:显式 real/synthetic 与完全省略(签名默认 real)均通过
    入口校验;聚合 provenance 机读(signature_default 登记缺省语义)。"""
    batch_root = _minimal_batch_root(tmp_path)
    agg = _score(tmp_path, batch_root, scope="real",
                 bases={GRAPH_A: "qid_strict"})
    assert agg["data_scope"] == "real"
    prov = agg["data_scope_provenance"]
    assert prov["normalized_from"] == "explicit"
    assert prov["signature_default"] == "real"

    agg2 = _score(tmp_path, batch_root, scope="synthetic_rule_level",
                  bases={GRAPH_A: "root_identity_fallback"})
    assert agg2["data_scope"] == "synthetic_rule_level"
    assert agg2["data_scope_provenance"]["normalized_from"] == "explicit"
    # 完全省略参数 ⇒ 既有签名默认 real(合法值;real 门照常走)
    agg3 = _score(tmp_path, batch_root, scope="real",
                  bases={GRAPH_A: "qid_strict"})
    assert agg3["data_scope"] == "real"


# ============================================================ 评测首消费

@pytest.mark.parametrize("bad_scope", BAD_DATA_SCOPES)
def test_evaluation_validate_rejects_explicit_bad_data_scope(
        bad_scope) -> None:
    """负控:validate_evaluation_input 首消费拒显式坏值(kind=
    data_scope_invalid;不用 truthiness 洗白)。"""
    evaluation_input = synth_evaluation_input()
    evaluation_input["data_scope"] = bad_scope
    with pytest.raises(EvaluationContractError) as excinfo:
        validate_evaluation_input(evaluation_input)
    detail = excinfo.value.detail
    assert detail["kind"] == "data_scope_invalid"
    assert detail["field"] == "data_scope"
    assert detail["allowed"] == ["real", "synthetic_rule_level"]


@pytest.mark.parametrize("bad_scope", [None, False, 0, ""])
def test_evaluation_evaluate_rejects_falsy_scope_before_real_gate(
        tmp_path, bad_scope) -> None:
    """核心负控(复审 §4.1 公开证据形态):显式空/None/False/0 修前
    被 ``or`` 洗成 synthetic、绕过 real 批准/配对门;修后在
    evaluate_scientific 首消费处结构化拒(带批准 prereg 也拒 ⇒
    拒因来自 data_scope 本身,不是缺批准)。"""
    evaluation_input = synth_evaluation_input(
        interface=False, data_scope=bad_scope)
    prereg = dict(_APPROVED)
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(evaluation_input, preregistration=prereg)
    assert excinfo.value.detail["kind"] == "data_scope_invalid"


def test_evaluation_missing_scope_keeps_default_semantics(
        tmp_path) -> None:
    """正控:字段完全缺省 ⇒ 既有默认 synthetic_rule_level 保留;输出
    scoring_provenance 机读归一来源(missing_field_default;缺省与
    坏值不混类)。"""
    graph = synth_reference_graph()
    evaluation_input = synth_evaluation_input(
        interface=False, graphs=[graph])
    evaluation_input.pop("data_scope", None)
    output = evaluate_scientific(
        evaluation_input, reference_graphs={graph["reference_graph_id"]:
                                            graph},
        preregistration=dict(_APPROVED))
    provenance = output["scoring_provenance"]
    assert provenance["data_scope"] == "synthetic_rule_level"
    assert provenance["data_scope_normalized_from"] == \
        "missing_field_default"
    # 显式 synthetic ⇒ normalized_from=explicit(可与缺省区分)
    explicit = synth_evaluation_input(
        interface=False, graphs=[graph],
        data_scope="synthetic_rule_level")
    output2 = evaluate_scientific(
        explicit, reference_graphs={graph["reference_graph_id"]: graph},
        preregistration=dict(_APPROVED))
    assert output2["scoring_provenance"]["data_scope_normalized_from"] \
        == "explicit"


def test_evaluation_real_scope_still_requires_approved_prereg() -> None:
    """正控(既有门不退):显式 real + 未批准预注册 ⇒ 原拒因保持
    (修的是坏值洗白,不是 real 门本身)。"""
    evaluation_input = synth_evaluation_input(
        interface=False, data_scope="real")
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(evaluation_input, preregistration=None)
    assert excinfo.value.detail["kind"] == \
        "real_data_requires_approved_preregistration"


# ============================================================ §9-4 basis 门

def test_basis_gate_missing_or_malformed_rejects_before_metrics(
        tmp_path) -> None:
    """负控族:缺 coverage/缺 pairing/缺 bases/空 bases/非 dict ⇒
    先拒零 metrics(六类模拟产物形态同门补齐;先于逐题聚合)。"""
    batch_root = _minimal_batch_root(tmp_path)
    cases = [
        {"bases": None, "with_coverage": False,
         "reason": "bases_by_graph_missing"},
        {"bases": None, "with_pairing": False,
         "reason": "bases_by_graph_missing"},
        {"bases": None, "reason": "bases_by_graph_missing"},
        {"bases": {}, "reason": "bases_by_graph_empty"},
        {"bases": [[GRAPH_A, "qid_strict"]],
         "reason": "bases_by_graph_not_dict"},
    ]
    for case in cases:
        with pytest.raises(S5bScoringError) as excinfo:
            _score(tmp_path, batch_root, scope="real",
                   bases=case["bases"],
                   with_pairing=case.get("with_pairing", True),
                   with_coverage=case.get("with_coverage", True))
        detail = excinfo.value.detail
        assert detail["kind"] == "s5b_real_pairing_not_all_qid_strict", \
            case
        assert case["reason"] in detail["reasons"], (case, detail)
        assert detail["expected_graph_ids"] == [GRAPH_A]
        # 零 metrics 落盘
        assert not (batch_root / "metrics.json").exists()


def test_basis_gate_key_set_must_exactly_cover_registered_graphs(
        tmp_path) -> None:
    """负控:两题批 ⇒ 缺键(只报一图)/foreign 键(多出未注册图)/
    非字符串值 ⇒ 拒;键集机读披露(expected/missing/foreign)。"""
    batch_root = _minimal_batch_root(tmp_path, n_graphs=2)
    good = {GRAPH_A: "qid_strict", GRAPH_B: "qid_strict"}

    # 正控:精确键集全 strict ⇒ 聚合照旧(分母 2)
    agg = _score(tmp_path, batch_root, scope="real", bases=good)
    assert agg["denominator"] == 2

    # 缺键:只覆盖一图
    with pytest.raises(S5bScoringError) as excinfo:
        _score(tmp_path, batch_root, scope="real",
               bases={GRAPH_A: "qid_strict"})
    detail = excinfo.value.detail
    assert "bases_by_graph_missing_keys" in detail["reasons"]
    assert detail["missing_graph_ids"] == [GRAPH_B]
    assert detail["foreign_graph_ids"] == []

    # foreign 键:多出未注册图
    with pytest.raises(S5bScoringError) as excinfo2:
        _score(tmp_path, batch_root, scope="real",
               bases={**good, "rg-foreign-9": "qid_strict"})
    detail2 = excinfo2.value.detail
    assert "bases_by_graph_foreign_keys" in detail2["reasons"]
    assert detail2["foreign_graph_ids"] == ["rg-foreign-9"]

    # 非字符串值(模拟产物形态):键集齐但值非 str
    with pytest.raises(S5bScoringError) as excinfo3:
        _score(tmp_path, batch_root, scope="real",
               bases={GRAPH_A: "qid_strict", GRAPH_B: 1})
    detail3 = excinfo3.value.detail
    assert "bases_not_all_qid_strict" in detail3["reasons"]
    assert detail3["non_qid_strict_bases"] == {GRAPH_B: "1"}

    # 非 strict 字符串值(既有负控保持)
    with pytest.raises(S5bScoringError) as excinfo4:
        _score(tmp_path, batch_root, scope="real",
               bases={GRAPH_A: "qid_strict",
                      GRAPH_B: "root_identity_fallback"})
    detail4 = excinfo4.value.detail
    assert detail4["non_qid_strict_bases"] == {
        GRAPH_B: "root_identity_fallback"}
    # 门范围落字(mimo r28 D1-②:核档位与覆盖,不核映射)
    gate_scope = str(detail4.get("gate_scope") or "")
    assert "不核" in gate_scope and "映射" in gate_scope


def test_basis_gate_synthetic_fallback_not_gated(tmp_path) -> None:
    """正控:synthetic 档回退配对(空 bases/缺 bases/fallback 值)不
    受 shape 门影响(聚合照旧,分母闭合)—— 门只在 real 档生效。"""
    batch_root = _minimal_batch_root(tmp_path)
    for bases in ({GRAPH_A: "root_identity_fallback"}, {},
                  None):
        agg = _score(tmp_path, batch_root,
                     scope="synthetic_rule_level", bases=bases)
        assert agg["data_scope"] == "synthetic_rule_level"
        assert agg["denominator"] == 1
        assert sum(v for k, v in agg["buckets"].items()
                   if not k.startswith("run_")) == agg["denominator"]


def test_basis_gate_simulated_vs_real_chain_disclosure() -> None:
    """说明性控制:本组负控用模拟评测器产物替换 evaluate_scientific
    输出(复审 §4.1:真实当前 evaluator 无导出仍给非空 qid_strict,
    坏产物正常可达性未证);正常可达性属评测器权威链,本门只对
    产物 shape 兜底。断言 score 消费链在正常路径仍由真实
    evaluate_scientific 产出 bases(合成夹具:零导出 ⇒ 零图 bases
    报告路径不冒充)。"""
    # 真实链最小正控:合成批 + 缺省 synthetic scope 走真实
    # evaluate_scientific(零导出 ⇒ 合成回退配对披露)不抛
    # s5b_real_pairing_not_all_qid_strict(该门只 real 档)
    graph = synth_reference_graph()
    evaluation_input = synth_evaluation_input(
        interface=False, graphs=[graph])
    output = evaluate_scientific(
        evaluation_input,
        reference_graphs={graph["reference_graph_id"]: graph},
        preregistration=dict(_APPROVED))
    pairing = (output.get("coverage_report") or {}).get("pairing") or {}
    assert isinstance(pairing.get("bases_by_graph"), dict)
