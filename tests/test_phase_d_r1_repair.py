"""Phase D R1 修复回归(pb_0117 TypeError + prepare 失败路由)。

事故重放(任务书 §3):D-3/D-10 的 pb_0117 在第 k 轮 classify 落盘
``mode=analogy_edit``(selected 来自 reactant_similar 通道,载体卡不在
检索 evidences 中)后:

1. prepare_prediction → build_prediction_task 抛 PredictionTaskError
   (selected_donor_card_missing)→ ``_hold_or_dead`` 只改 state;
2. 旧图 prepare_prediction→call_model 是**固定边**,控制流仍进
   call_model,以空 task_id 读产物 → ``read(...)["payload"]`` 对 None
   下标 → 裸 ``TypeError`` 崩溃 worker。

修复 = 三层:资格块 selected 携带 donor_ref(v43-applicability-3)、
prediction 任务组装兜底合成载体卡、prepare 失败路由回主循环 +
call_model/_read_decision 结构化守卫(v43-policy-5)。全部无凭证无网络。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.wf_helpers import evidence, fake_model, load_report, run_scripted

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "phase_d_r1"
     / "pb0117_d3_similarity_selected.json").read_text(encoding="utf-8"))


# ------------------------------------------------ R1-b 生产端:donor_ref 随行


def test_selected_carries_full_donor_ref():
    """applicable 的 selected 必须自带完整供体引用(含映射模板)。"""
    from tests.test_reactant_similar import _fx, _similar_ref
    from pathway_v43.services.donor_applicability import (
        ApplicabilityPolicy, build_eligibility,
    )

    fx = _fx("F1_full_donor_exact")
    similar = _similar_ref(fx["donor"])
    block = build_eligibility(
        [], fx["substrate_smiles"],
        ApplicabilityPolicy(max_donor_candidates=3),
        similar_refs=[similar])
    assert block["status"] == "applicable"
    sel = block["selected"]
    ref = sel["donor_ref"]
    assert ref["record_id"] == sel["record_id"]
    assert ref["mapped_lhs"] and ref["mapped_rhs"]
    # 资格块整体仍满足 canonical round-trip 稳定(int 键事故回归钉同源)
    from pathway_v43.domain.models import canonical_json
    assert canonical_json(block) == canonical_json(
        json.loads(canonical_json(block)))
    # donor_ref 同样进入 JSON 往返稳定
    assert canonical_json(ref) == canonical_json(json.loads(
        canonical_json(ref)))


def test_similar_channel_donor_ref_json_roundtrip_stable():
    """真实 r1 供体形状(rhea:54370 氰醇加成)的 donor_ref 往返稳定。"""
    from tests.test_reactant_similar import _fx, _similar_ref
    from pathway_v43.services.donor_applicability import (
        ApplicabilityPolicy, build_eligibility,
    )
    from pathway_v43.domain.models import canonical_json

    fx = _fx("F2_center_match_first_shell_conflict")
    similar = _similar_ref(fx["donor"])
    block = build_eligibility(
        [], fx["substrate_smiles"],
        ApplicabilityPolicy(max_donor_candidates=3),
        similar_refs=[similar])
    if block["status"] == "applicable":
        sel = block["selected"]
        assert canonical_json(sel) == canonical_json(
            json.loads(canonical_json(sel)))


# --------------------------------------------- R1-b 消费端:任务组装兜底


def _eligibility_with_similar_selected(substrate_smiles: str) -> dict:
    """最小相似通道 applicable 资格块(selected=reactant_similar_channel)。"""
    from tests.test_reactant_similar import _fx, _similar_ref
    from pathway_v43.services.donor_applicability import (
        ApplicabilityPolicy, build_eligibility,
    )

    fx = _fx("F1_full_donor_exact")
    similar = _similar_ref(fx["donor"])
    block = build_eligibility(
        [], substrate_smiles,
        ApplicabilityPolicy(max_donor_candidates=3),
        similar_refs=[similar])
    assert block["status"] == "applicable", block.get("fallback_reason")
    assert block["selected"]["evidence_id"] == "reactant_similar_channel"
    return block


def test_prediction_task_synthesizes_carrier_for_similar_channel(tmp_path):
    """selected 供体不在 evidences 时,凭 selected.donor_ref 合成载体卡。"""
    from pathway_v43.domain.identity import cn_identity
    from pathway_v43.services.prediction import (
        PREDICTION_MODE_ANALOGY, build_prediction_task,
    )
    from pathway_v43.storage.pathway_store import PathwayStore
    from pathway_v43.services.atom_tool import roundtrip

    substrate = "CCO"
    ident = cn_identity(substrate)
    store = PathwayStore(tmp_path / "t.sqlite")
    root = store.ensure_run("r1b-unit", substrate, ident)
    elig = _eligibility_with_similar_selected(substrate)
    render = roundtrip(substrate, name="S")
    task = build_prediction_task(
        store=store, run_id="r1b-unit", path_id=root,
        substrate_identity=ident, substrate_smiles=substrate,
        root_smiles=substrate, mode=PREDICTION_MODE_ANALOGY,
        retrieval_payload={"evidences": []},  # 检索产物不含相似通道载体卡
        retrieval_payload_hash="h", conditions=[],
        model_block={}, policy={"max_candidates_for_ranking": 8},
        budget={"active_depth": 0, "max_depth": 2, "max_expansions": 40, "max_frontier_width": 3, "max_llm_calls": 42, "max_proposals": 40, "used_expansions": 1, "used_llm_calls": 0, "used_proposals": 0},
        molecule_render={"molecode": render.molecode,
                         "atom_ids": render.atom_ids,
                         "canonical_smiles": render.canonical_smiles},
        siblings=[], analogy_eligibility=elig,
    )
    donor = task["donor"]["donor"]
    assert task["donor"]["evidence_id"] == "reactant_similar_channel"
    assert donor["record_id"] == elig["selected"]["record_id"]
    assert donor["mapped_lhs"] and donor["mapped_rhs"]
    assert task["donor"]["transform"], "变换表必须随任务携带"
    assert task["donor"]["applicability"]["status"] == "applicable"


def test_legacy_selected_without_donor_ref_still_fails_explicitly(tmp_path):
    """旧形状资格块(v43-applicability-2,无 donor_ref)不得静默换供体。"""
    from pathway_v43.domain.identity import cn_identity
    from pathway_v43.services.prediction import (
        PREDICTION_MODE_ANALOGY, PredictionTaskError, build_prediction_task,
    )
    from pathway_v43.storage.pathway_store import PathwayStore

    substrate = "CCO"
    ident = cn_identity(substrate)
    store = PathwayStore(tmp_path / "t.sqlite")
    root = store.ensure_run("r1b-unit", substrate, ident)
    elig = _eligibility_with_similar_selected(substrate)
    elig["selected"] = {k: v for k, v in elig["selected"].items()
                        if k != "donor_ref"}  # 还原 r1 事故现场形状
    with pytest.raises(PredictionTaskError) as ei:
        build_prediction_task(
            store=store, run_id="r1b-unit", path_id=root,
            substrate_identity=ident, substrate_smiles=substrate,
            root_smiles=substrate, mode=PREDICTION_MODE_ANALOGY,
            retrieval_payload={"evidences": []},
            retrieval_payload_hash="h", conditions=[],
            model_block={}, policy={}, budget={"active_depth": 0, "max_depth": 2, "max_expansions": 40, "max_frontier_width": 3, "max_llm_calls": 42, "max_proposals": 40, "used_expansions": 1, "used_llm_calls": 0, "used_proposals": 0},
            molecule_render={"molecode": "graph TB", "atom_ids": [],
                             "canonical_smiles": substrate},
            siblings=[], analogy_eligibility=elig,
        )
    assert ei.value.reason == "selected_donor_card_missing"


def test_real_pb0117_slice_r1_shape_fails_new_shape_succeeds(tmp_path):
    """Chenyu r1 事故现场切片:旧形状显式失败;补 donor_ref 后可组装。

    证明链:同一现场输入,修复前的失败模式(卡片缺失)保持显式结构化,
    修复后(资格块 v3 形状)任务组装成功 —— 不再经过 call_model 崩溃。
    """
    from pathway_v43.domain.identity import cn_identity
    from pathway_v43.services.prediction import (
        PREDICTION_MODE_ANALOGY, PredictionTaskError, build_prediction_task,
    )
    from pathway_v43.storage.pathway_store import PathwayStore

    substrate = FIXTURE["substrate_smiles"]
    elig = json.loads(json.dumps(FIXTURE["eligibility"]))  # r1 旧形状
    assert elig["selected"]["evidence_id"] == "reactant_similar_channel"
    assert "donor_ref" not in elig["selected"]
    digest = FIXTURE["evidences_digest"]
    assert not any(e["evidence_id"] == "reactant_similar_channel"
                   for e in digest)
    ident = cn_identity(substrate)
    store = PathwayStore(tmp_path / "t.sqlite")
    root = store.ensure_run("r1b-real", substrate, ident)

    def _build(eligibility):
        return build_prediction_task(
            store=store, run_id="r1b-real", path_id=root,
            substrate_identity=ident, substrate_smiles=substrate,
            root_smiles=substrate, mode=PREDICTION_MODE_ANALOGY,
            retrieval_payload={"evidences": []},
            retrieval_payload_hash="h", conditions=[],
            model_block={}, policy={}, budget={"active_depth": 0, "max_depth": 2, "max_expansions": 40, "max_frontier_width": 3, "max_llm_calls": 42, "max_proposals": 40, "used_expansions": 1, "used_llm_calls": 0, "used_proposals": 0},
            molecule_render={"molecode": "graph TB", "atom_ids": [],
                             "canonical_smiles": substrate},
            siblings=[], analogy_eligibility=eligibility,
        )

    with pytest.raises(PredictionTaskError) as ei:
        _build(elig)
    assert ei.value.reason == "selected_donor_card_missing"
    # v3 形状:selected 补 donor_ref(取自所选供体的映射模板)
    sel = elig["selected"]
    sel["donor_ref"] = {
        "record_id": sel["record_id"],
        "donor_index": sel.get("donor_index", ""),
        "asset_file": sel.get("asset_file", ""),
        "asset_sha256": sel.get("asset_sha256", ""),
        "line_no": sel.get("line_no"),
        "mapping_quality": sel.get("mapping_quality", ""),
        # rhea:54370 供体模板(氰醇加成 → 羧酸α-羟基化形状),从资格块
        # alignment/transform 不可反推模板本身,夹具用同反应家族最小模板
        "mapped_lhs": "CC(=O)C(O)C(=O)O",
        "mapped_rhs": "CC(=O)C(O)C(=O)O",
        "find_channels": [],
    }
    task = _build(elig)
    assert task["donor"]["evidence_id"] == "reactant_similar_channel"
    assert task["donor"]["donor"]["record_id"] == sel["record_id"]


# --------------------------------------------- R1-b 路由与结构化守卫


def test_route_after_prepare_holds_on_prepare_failure():
    """prepare 显式停留(phase≠call_model)必须回主循环,不进 call_model。"""
    from pathway_v43.workflow.routing import route_after_prepare

    ok = {"phase": "call_model", "prediction_task_id": "T_x",
          "prediction_mode": "analogy_edit"}
    assert route_after_prepare(ok) == "call_model"
    # _hold_or_dead 的事故现场:phase=select、无任务 id(裸 TypeError 源)
    held = {"phase": "select", "prediction_task_id": "",
            "prediction_mode": "", "prediction_failed": True}
    assert route_after_prepare(held) == "select_frontier"


def test_call_model_missing_task_structured_error_not_typeerror(tmp_path):
    """空 task_id 进 call_model:结构化 NodeStateError(带身份),非裸 TypeError。"""
    from pathway_v43.workflow.nodes import NodeStateError, call_model

    class _Svc:
        pass

    svc = _Svc()

    class _Artifacts:
        def read(self, *a, **k):
            return None

    svc.artifacts = _Artifacts()
    node = call_model(svc)
    # 事故机制复现:旧表达式对 read() 结果直接下标必 TypeError
    with pytest.raises(TypeError):
        _Artifacts().read("", "prediction_task")["payload"]
    # 新守卫:结构化报错,detail 含可定位身份
    with pytest.raises(NodeStateError) as ei:
        node({"run_id": "r", "prediction_task_id": "", "prediction_mode": "",
              "phase": "select"})
    assert ei.value.detail["prediction_task_id"] == ""
    with pytest.raises(NodeStateError) as ei2:
        node({"run_id": "r", "prediction_task_id": "T_missing",
              "prediction_mode": "analogy_edit", "phase": "call_model"})
    assert ei2.value.detail["task_id"] == "T_missing"


def test_prepare_failure_end_to_end_stops_cleanly(tmp_path):
    """端到端:相似通道 selected 的类比轮次存活,run 合法终态不崩溃。

    旧图下该局面 = selected_donor_card_missing → _hold_or_dead → 固定边
    误入 call_model → worker 裸 TypeError 崩溃;新图 = 任务组装成功或
    显式停留,run 正常终态。旧形状的显式失败已由上方单元测试钉住。
    """
    from pathway_v43.config import resolve_config
    from tests.test_reactant_similar import _fx
    from pathway_v43.services.analog_source import AnalogSourceResolver
    from pathway_v43.services.reaction_finder import ScriptedReactionFinder
    from pathway_v43.workflow import start_run

    fx = _fx("F1_full_donor_exact")
    substrate = fx["substrate_smiles"]

    class _ResolverFinder(ScriptedReactionFinder):
        def __init__(self):
            super().__init__({})
            self.analog_resolver = AnalogSourceResolver(resolve_config())

    model = fake_model(default_by_mode={
        "analogy_edit": json.dumps({"decision": "abstain",
                                    "reason": "供体对不上,弃权"}),
        "novel_proposal": json.dumps(
            {"decision": "abstain", "reason": "无据可说"})})
    summary = start_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id="r1b-e2e", smiles=substrate, max_depth=1,
        max_expansions=2, max_frontier_width=3,
        finder=_ResolverFinder(), scripted=True,
        model=model, max_llm_calls=3, max_proposals=3)
    assert summary["stop_reason"] in ("awaiting_prediction", "completed",
                                      "budget_exhausted"), summary
    # run 存活到导出:report 可读、无未捕获异常
    report = load_report(tmp_path / "runs", "r1b-e2e")
    assert report["run_id"] == "r1b-e2e"
