"""S5b 启动批回修 L01 回归(evaluation-5:S5B-L01 real 首消费禁
双无 qid / root_identity_fallback)。

复审 ``docs/POLLUTANT_PATHWAY_S5B_CODEX_REVIEW_2026-10-09.md`` §4.1
P1:``evaluate_scientific`` 对 ``data_scope=real`` 且评测输入两侧
全部未声明 qid(manifest 条目与 native_path_exports 条目均无
qid,配对档 ``root_identity_fallback``)不拒——公开合成反例
(real 标签 + fake approved 形状 + 双无 qid)修前 codex-a 一图
``scored`` 进聚合、codex-b ``not_evaluated_export_missing``。
evaluation-5 在配对计算后、样本评分/聚合/结果写入**前**结构化拒
(``real_data_root_identity_fallback_forbidden``)。

夹具纪律与 ``test_ppv1_s5b_pairing.py`` 相同:公共 ``start_run``
真实生成的合成 run(两题同底物 CCO、可区分计划)、合成规则级
参考图、合成 qid(与真实 RXNG_* 题面零重叠);本文件中
``data_scope='real'`` 与 ``approval_status='approved'`` 只是触发
程序门形状的**合成接口标签**(复审反例同款),不代表真实数据/
金标/封存 run/用户或 teacher 审批;判分零 LLM、零网络、零费用。

父基线预期(a399d6e,evaluation-4):反例案 red(未发生指定守卫
异常——evaluate 返回错误评分输出,sample_results/aggregate 非空);
三个正控案(synthetic 回退/real 严格 qid/real+pending prereg 拒)
在父上同为绿——是**保持控制**,不是行为翻转。
"""

from __future__ import annotations

import copy
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
from pathway_v43.pollutant.profile import (  # noqa: E402
    PPV1_EVALUATION_VERSION,
    PPV1_PROFILE_SCHEMA_VERSION,
    contract_versions,
)

from test_ppv1_s5a_schema import synth_evaluation_input  # noqa: E402
from test_ppv1_s5b_pairing import (  # noqa: E402
    QID_A,
    QID_B,
    _multi_run_reader,
    _plan_coproduct,
    _plan_no_coproduct,
    _qid_graph,
    _run,
    _two_graph_split,
)


GRAPH_A = "rg-l01-a"
GRAPH_B = "rg-l01-b"


def _fake_approved_prereg() -> dict:
    """合成 approved 形状(程序门触发器;非用户/teacher 审批)。"""
    prereg = preregistration.build_preregistration_template(
        note="SYNTHETIC_APPROVAL_TAG_ONLY: adversarial interface "
             "fixture, not user/teacher approval")
    prereg["approval_status"] = "approved"
    prereg["preregistration_id"] = \
        "synthetic-prereg-interface-approved-shape"
    return prereg


def _noqid_two_graph_input(tmp_path: Path, *, scope: str,
                           interface: bool = False) -> dict:
    """评审反例形状:两同根图 + 两导出,两侧条目全部不声明 qid。

    图的 root_entity.source_refs 仍携带合成 qid(复审口径:图里
    有 qid 不能推断为已严格配对——消费档只看条目级声明)。
    """
    run_a = _run(tmp_path, "s5b-l01-a", _plan_coproduct())
    digest_a = run_a["native_export"]["export_digest"]
    run_b = _run(tmp_path, "s5b-l01-b", _plan_no_coproduct())
    digest_b = run_b["native_export"]["export_digest"]
    graphs = [_qid_graph(GRAPH_A, QID_A), _qid_graph(GRAPH_B, QID_B)]
    exports = [
        {"run_id": "s5b-l01-a", "export_digest": digest_a},
        {"run_id": "s5b-l01-b", "export_digest": digest_b},
    ]
    evaluation_input = synth_evaluation_input(
        graphs=graphs,
        split_manifest=_two_graph_split([GRAPH_A, GRAPH_B]),
        exports=exports, data_scope=scope, interface=interface)
    reader = _multi_run_reader(
        tmp_path / "runs", ["s5b-l01-a", "s5b-l01-b"])
    return {
        "evaluation_input": evaluation_input,
        "reference_graphs": {g["reference_graph_id"]: g for g in graphs},
        "reader": reader,
        "digest_a": digest_a,
        "digest_b": digest_b,
    }


def _evaluate(case: dict, *, prereg=None) -> dict:
    return evaluate_scientific(
        case["evaluation_input"],
        reference_graphs=case["reference_graphs"],
        native_export_reader=case["reader"],
        preregistration=prereg if prereg is not None else
        preregistration.build_preregistration_template())


# ------------------------------------------- L01 反例:real 双无 qid 结构化拒


def test_real_label_noqid_structured_reject_before_scoring(
        tmp_path: Path) -> None:
    """反例翻转:S5B-L01——real 标签 + 两侧全无 qid 声明 ⇒ 配对首
    次消费处结构化拒(``real_data_root_identity_fallback_forbidden``),
    先于任何样本评分/聚合/结果写入(修前 a399d6e:codex-a scored
    进聚合、codex-b not_evaluated,复现见回修证据包)。

    ``data_scope='real'`` + fake approved 形状沿复审公开反例轴;
    全部数据是合成夹具(dev/known/development),不冒称真实 298/
    金标/用户科学授权。
    """
    case = _noqid_two_graph_input(tmp_path, scope="real")
    with pytest.raises(EvaluationContractError) as excinfo:
        _evaluate(case, prereg=_fake_approved_prereg())
    detail = excinfo.value.detail
    assert detail["kind"] == "real_data_root_identity_fallback_forbidden"
    # 机读保留:data_scope / pairing_basis / 缺 qid 范围
    assert detail["data_scope"] == "real"
    assert detail["pairing_basis"] == "root_identity_fallback"
    assert detail["graphs_without_declared_qid"] == [GRAPH_A, GRAPH_B]
    assert detail["export_entries_without_declared_qid"] == sorted(
        [case["digest_a"], case["digest_b"]])
    # 守卫语义:样本身份边界 fail-closed,不是 criteria-v2 化学门
    assert "样本身份边界" in excinfo.value.args[0]
    assert "先于任何样本评分" in excinfo.value.args[0]


def test_real_noqid_prereg_gate_precedes_pairing_guard(
        tmp_path: Path) -> None:
    """门次序:real + 双无 qid + 预注册未批准 ⇒ 预注册门先拒
    (real_data_requires_approved_preregistration;新守卫不取消
    既有授权前置)。"""
    case = _noqid_two_graph_input(tmp_path, scope="real")
    with pytest.raises(EvaluationContractError) as excinfo:
        _evaluate(case)  # 模板 approval_status 为 pending 族
    assert excinfo.value.detail["kind"] == \
        "real_data_requires_approved_preregistration"


def test_real_noqid_input_guard_precedes_pairing_guard(
        tmp_path: Path) -> None:
    """门次序:real 标签下既有输入守卫仍先于配对守卫(以 manifest
    声明 qid 不在 source_refs 为例——守卫顺序不因 real 档改写)。"""
    case = _noqid_two_graph_input(tmp_path, scope="real")
    bad = copy.deepcopy(case["evaluation_input"])
    bad["reference_graph_manifest"][0]["qid"] = "SYNTH-NOT-IN-SOURCE"
    with pytest.raises(EvaluationContractError) as excinfo:
        evaluate_scientific(
            bad, reference_graphs=case["reference_graphs"],
            native_export_reader=case["reader"],
            preregistration=_fake_approved_prereg())
    assert excinfo.value.detail["kind"] == \
        "reference_graph_qid_not_in_source_refs"


# ------------------------------------------- 正控:合法行为保持(父上亦绿)


def test_synthetic_noqid_fallback_positive_control_kept(
        tmp_path: Path) -> None:
    """正控保持:synthetic_rule_level + 双无 qid ⇒ 回退根身份配对
    照常 scored 并机读披露(evaluation-5 不取消合成夹具回退)。"""
    case = _noqid_two_graph_input(tmp_path, scope="synthetic_rule_level")
    output = _evaluate(case)
    sample_a = next(s for s in output["sample_results"]
                    if s["reference_graph_id"] == GRAPH_A)
    assert sample_a["scoring_status"] == "scored"
    assert sample_a["pairing"]["basis"] == "root_identity_fallback"
    assert sample_a["pairing"]["consumed_export_digest"] is not None
    assert set(output["coverage_report"]["pairing"][
        "bases_by_graph"].values()) == {"root_identity_fallback"}


def test_real_label_strict_qid_positive_control_kept(
        tmp_path: Path) -> None:
    """正控保持:real 标签 + 双侧 qid 声明 ⇒ 严格 qid 档正常评分
    (S5B-L01 只拦双无 qid 回退,不全面拒绝 real 合法严格档)。"""
    case = _noqid_two_graph_input(tmp_path, scope="real")
    evaluation_input = case["evaluation_input"]
    qids = {GRAPH_A: QID_A, GRAPH_B: QID_B}
    for entry in evaluation_input["reference_graph_manifest"]:
        entry["qid"] = qids[str(entry["reference_graph_id"])]
    exports = [
        {"run_id": "s5b-l01-a", "export_digest": case["digest_a"],
         "qid": QID_A},
        {"run_id": "s5b-l01-b", "export_digest": case["digest_b"],
         "qid": QID_B},
    ]
    evaluation_input["native_path_exports"] = exports
    output = _evaluate(case, prereg=_fake_approved_prereg())
    for sample in output["sample_results"]:
        assert sample["scoring_status"] == "scored"
        assert sample["pairing"]["basis"] == "qid_strict"
    assert output["coverage_report"]["pairing"][
        "bases_by_graph"] == {GRAPH_A: "qid_strict",
                              GRAPH_B: "qid_strict"}


def test_real_qid_unpaired_not_evaluated_kept(tmp_path: Path) -> None:
    """正控保持:real 标签 + qid 声明缺配导出 ⇒ not_evaluated +
    ``sample_qid_unpaired``(fail-closed 留分母,不张冠李戴;不因
    real 档回退根身份)。"""
    case = _noqid_two_graph_input(tmp_path, scope="real")
    evaluation_input = case["evaluation_input"]
    evaluation_input["native_path_exports"] = [
        {"run_id": "s5b-l01-a", "export_digest": case["digest_a"],
         "qid": QID_A}]
    for entry in evaluation_input["reference_graph_manifest"]:
        entry["qid"] = {GRAPH_A: QID_A, GRAPH_B: QID_B}[
            str(entry["reference_graph_id"])]
    output = _evaluate(case, prereg=_fake_approved_prereg())
    sample_b = next(s for s in output["sample_results"]
                    if s["reference_graph_id"] == GRAPH_B)
    assert sample_b["scoring_status"] == "not_evaluated_export_missing"
    assert sample_b["scoring_errors"][0]["kind"] == "sample_qid_unpaired"
    assert sample_b["scoring_errors"][0]["qid"] == QID_B
    assert output["coverage_report"]["unmatched_exports"] == []


# ------------------------------------------- 契约登记(evaluation-5/profile-25)


def test_l01_contract_version_registration() -> None:
    """evaluation-5 / profile-25 契约登记(S5B-L01 real 档配对守卫
    升版,不偷换已登记契约;reference-graph-1/split-manifest-1/
    preregistration-template-3 不变;qid 不进化学结构判据)。"""
    from pathway_v43.pollutant.profile import (
        PPV1_PREREGISTRATION_TEMPLATE_VERSION,
        PPV1_REFERENCE_GRAPH_VERSION,
        PPV1_SPLIT_MANIFEST_VERSION,
    )
    assert PPV1_EVALUATION_VERSION == "ppv1-evaluation-5"
    assert PPV1_PROFILE_SCHEMA_VERSION == "ppv1-profile-25"
    assert contract_versions()["evaluation"] == "ppv1-evaluation-5"
    assert contract_versions()["profile"] == "ppv1-profile-25"
    assert PPV1_REFERENCE_GRAPH_VERSION == "ppv1-reference-graph-1"
    assert PPV1_SPLIT_MANIFEST_VERSION == "ppv1-split-manifest-1"
    assert PPV1_PREREGISTRATION_TEMPLATE_VERSION == \
        "ppv1-preregistration-template-3"
