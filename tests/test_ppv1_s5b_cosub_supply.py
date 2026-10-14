"""PPV1 S5b C 线共底物伴生供给 + 声明链发射测试族(s5b-analog-cosub-
supply-1 / s5b-pool-policy-7,2026-10-14)。

权威链:设计书 C_COSUB_SUPPLY_DESIGN_PREREG_2026-10-14.md(冻结)+
实施任务书 TASK_C_COSUB_IMPL_2026-10-14.md;pred1 消费契约 =
criteria-v2 预注册(POLLUTANT_PATHWAY_CRITERIA_V2_PREREGISTRATION_
2026-10-13.md §二.1);探针锚 = reports/ppv1_s5b/c_probe_cosubgate_
2026-10-14/(45 行/35 题;11 题纯 H₂O 袋;裸通配 3 行拦截)。

控件矩阵:
- PC-S1 伴生供给装配:水袋模板 + 酯底物 ⇒ 池 spec 带完整声明面
  (participants 显式/co_substrate_states/declared_copy_components(空)/
  cosubstrate_event_contract/record_equation+ref/execution_input_smiles);
- PC-S2 份数多重集:2 H₂O 袋 ⇒ 供给两条目(2 H₂O ≠ 1 H₂O;
  record_equation 逐份在案);
- PC-S3 spectator 披露:未被模板变换消费的供给组分逐条
  spectator=True + consumption_status=spectator_pass_through(不得
  静默);
- PC-S4 裸通配袋(*)不供给(维持现状拦截;wildcard_blocked 计数);
  含通配原子的具体小分子([H]*[H])不属裸通配袋(探针 §4 口径);
- PC-S5 版本承载:policy-7 + analog_cosub_supply_* 诊断键;
- PC-S6 声明链发射(run 期,worker 事件提交路径):事件提交前
  provenance_records 行落库(record_id == hypothesis.provenance_refs[0];
  行 payload.record_equation = 模板记录方程);native export payload
  内链路可解析(_criteria_declaration_sides = resolved);
- PC-S7 v2 豁免正控(端到端):水袋 extra 经 v2 三谓词全过 ⇒
  v1_exempt tier + 事件升 exact;v1 口径同载荷维持 partial
  (豁免关 = 基线零漂移);
- NC-S1 发射面 fail-closed:record_equation_ref/equation 不成对、
  条目不可解析、execution_input_smiles 多重集篡改 ⇒ 结构化拒;
- NC-S2 NC-10 事件级:供给 spec participants 删减 ⇒ prepare 结构化拒
  (复用 corpus 消费面,零新发明);
- NC-S3 无声明 spec 零变化:hypothesis provenance_refs 保持 []、
  prepared 不带发射载荷(既有路径行为字节等价)。

本文件零网络、零真实模型(scripted 桩);合成分子/合成 qid 与真实
298 题面零重叠(qid 前缀 c-supply-;小分子夹具,同 D2 W2 纪律)。
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.evaluation import (  # noqa: E402
    _criteria_declaration_sides,
    match_reference_edges,
    match_reference_nodes,
)
from pathway_v43.pollutant.production import (  # noqa: E402
    ProductionContractError,
    prepare_hypothesis,
)
from pathway_v43.pollutant.real_model import (  # noqa: E402
    ScriptedRealModelAdapter,
)
from pathway_v43.pollutant.runflow import start_ppv1_run  # noqa: E402
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    S5B_ANALOG_COSUB_SUPPLY_VERSION,
    S5B_POOL_POLICY_VERSION,
    analog_cosub_supply,
    build_question_batch,
    default_pool_provider,
)
from pathway_v43.services.analog_source import DonorRef  # noqa: E402

# 合成模板(零真实模板 id 重叠;酯水解语义:主=乙酸酯骨架 + 供给水;
# 全原子显式 map,无电荷/手性变化,无新增/移除 map —— 仅断键/成键)
_SUBSTRATE = "CC(C)C(=O)OCC"          # 合成酯底物(非真实 298 题面)
_GOLD = ["CC(C)C(=O)O", "CCO"]        # 酸 + 醇(全事件产物即金标)
_TPL_LHS_1W = ("[CH3:1][C:2](=[O:3])[O:4][CH2:5][CH3:6]"
               ".[O:7]([H:8])[H:9]")
_TPL_RHS_1W = ("[CH3:1][C:2](=[O:3])[O:4][H:8]"
               ".[CH3:6][CH2:5][O:7][H:9]")
# 2 水袋:第 1 份被变换消费,第 2 份原样过路(spectator)
_TPL_LHS_2W = _TPL_LHS_1W + ".[O:10]([H:11])[H:12]"
_TPL_RHS_2W = _TPL_RHS_1W + ".[O:10]([H:11])[H:12]"
_CENTER = [2, 4, 7]
_RECORD_1W = "synthetic:rhea-x1"
_RECORD_2W = "synthetic:rhea-x2"


def _donor_ref(record_id: str, mapped_lhs: str, mapped_rhs: str) -> DonorRef:
    return DonorRef(
        record_id=record_id, index="analog_corpus_templates",
        asset_file="synthetic", asset_sha256="0" * 64, line_no=1,
        mapping_quality="mapped_bijection",
        reactant_smiles=".".join(c for c in
                                 (mapped_lhs.split("."))),
        product_smiles=".".join(mapped_rhs.split(".")),
        mapped_lhs=mapped_lhs, mapped_rhs=mapped_rhs,
        center_atoms=list(_CENTER))


def _stub_resolver(monkeypatch, refs: list[DonorRef]) -> None:
    """替换 AnalogSourceResolver(不触真实资产索引;零网络)。"""

    class _Stub:
        def __init__(self, config) -> None:
            self.config = config

        def templates_similar_to(self, substrate_smiles: str, *,
                                 threshold: float, top_k: int):
            return list(refs)

    import pathway_v43.services.analog_source as analog_module

    monkeypatch.setattr(analog_module, "AnalogSourceResolver", _Stub)


_PROFILE = {
    "search_limits": {
        "max_alternative_hypotheses_per_parent": 8,
        "max_attempts_per_hypothesis": 1,
        "max_product_expansion_width": 2,
        "max_search_depth": 1,
        "max_total_search_actions": 48,
        "max_scenario_transitions": 0,
        "max_reopens_per_hypothesis": 0,
        "max_real_model_requests": 4,
        "max_retrievals_per_parent": 1,
        "max_retrievals_total": 8,
    },
    "format_feedback_policy": {"max_format_feedback_rounds": 0},
}


def _supply_spec(monkeypatch, mapped_lhs: str, mapped_rhs: str) -> dict:
    """水袋模板 + 合成酯底物 ⇒ 池内供给 spec(经 default_pool_provider
    真实装配路径)。"""
    _stub_resolver(monkeypatch, [_donor_ref(
        _RECORD_1W, mapped_lhs, mapped_rhs)])
    # config 注入 ⇒ analog 通道开启(engine 不注入:recorded/corpus 关);
    # resolver 已被 stub 替换,不触真实资产索引
    provider = default_pool_provider(resolve_config(), engine=None)
    specs = provider(_SUBSTRATE)
    assert specs, "水袋模板应经伴生供给入池"
    supply = [s for s in specs
              if s.get("cosubstrate_event_contract") is not None]
    assert supply, "入池 spec 应携带共底物声明面"
    return supply[0]


# ================================================================ PC-S1


def test_supply_assembly_declaration_surface(monkeypatch) -> None:
    """水袋模板 + 酯底物 ⇒ 供给 spec 声明面全字段在位(语义 a 装配)。"""
    spec = _supply_spec(monkeypatch, _TPL_LHS_1W, _TPL_RHS_1W)
    assert spec["key"] == f"tpl-{_RECORD_1W}"
    b_entries = spec["co_substrate_states"]
    assert [e["smiles"] for e in b_entries] == ["O"]
    assert all(e["state_ref"] and e["source_ref"] == spec["key"]
               and e["strict_identity"] for e in b_entries)
    assert spec["declared_copy_components"] == []
    contract = spec["cosubstrate_event_contract"]
    assert contract["record_key"] == spec["key"]
    assert [c["smiles"] for c in contract["co_substrates"]] == ["O"]
    # record_products 轴 = 执行净产物全量(analog:执行派生,W1 #2)
    assert contract["record_products"] == [spec["product_smiles"]] \
        + list(spec["coproducts"])
    assert contract["copy_state_refs"] == []
    # 记录方程 = 模板记录原样两侧(去 map;精确多重集)
    eq = spec["record_equation"]
    # 模板记录原样两侧去 map(canonical;模板主=乙酸酯,非底物衍生)
    assert [e["smiles"] for e in eq["reactants"]] == ["CCOC(C)=O", "O"]
    assert [e["smiles"] for e in eq["products"]] == ["CC(=O)O", "CCO"]
    assert spec["record_equation_ref"] == \
        f"analog-supply:tpl-{_RECORD_1W}"
    # 执行输入显式声明(底物 ⊕ 供给)
    assert spec["execution_input_smiles"] == _SUBSTRATE + ".O"
    # 参与物显式(primary_substrate + cosubstrate + principal + coproduct)
    roles = [(p["side"], p["role"]) for p in spec["participants"]]
    assert roles == [("reactant", "primary_substrate"),
                     ("reactant", "cosubstrate"),
                     ("product", "principal_product"),
                     ("product", "coproduct")]
    assert spec["participant_list_status"] == "declared_complete"


def test_supply_prepared_event_invariant(monkeypatch) -> None:
    """供给 spec 经 prepare_hypothesis(NC-10 复用消费面)⇒ 假设/状态
    装配成功;执行输入随 tool_inputs 下传。"""
    spec = _supply_spec(monkeypatch, _TPL_LHS_1W, _TPL_RHS_1W)
    from pathway_v43.pollutant.chemstate import build_chemical_state

    substrate_state = build_chemical_state(
        _SUBSTRATE, "raw_input", [{"record": "ppv1-substrate:test"}])
    prepared = prepare_hypothesis(
        spec, parent_path_id="path-test", substrate_state=substrate_state,
        transformation_ref="synthetic:rhea-x1")
    hyp = prepared["hypothesis"].to_dict()
    assert hyp["provenance_refs"] == [spec["record_equation_ref"]]
    assert prepared["tool_inputs"]["execution_input_smiles"] == \
        _SUBSTRATE + ".O"
    # 供给状态进入状态集(参与物可解析)
    for e in spec["co_substrate_states"]:
        assert e["state_ref"] in prepared["states"]


# ================================================================ PC-S2


def test_supply_multiset_exact_two_water(monkeypatch) -> None:
    """2 H₂O ≠ 1 H₂O:两份水袋 ⇒ 供给两条目 + 记录方程逐份在案 +
    spectator 逐条披露(第 2 份原样过路)。"""
    spec = _supply_spec(monkeypatch, _TPL_LHS_2W, _TPL_RHS_2W)
    b_entries = spec["co_substrate_states"]
    assert [e["smiles"] for e in b_entries] == ["O", "O"]
    eq = spec["record_equation"]
    assert [e["smiles"] for e in eq["reactants"]].count("O") == 2
    assert spec["execution_input_smiles"] == _SUBSTRATE + ".O.O"
    # 多余主份数之外:precise multiset —— contract refs 两条
    assert len(spec["cosubstrate_event_contract"][
        "co_substrate_state_refs"]) == 2
    # spectator 披露:第 1 份被消费,第 2 份两侧净零 ⇒ 逐条标记
    flags = [(e["smiles"], e["spectator"], e["consumption_status"])
             for e in b_entries]
    assert flags == [("O", False, "unknown"),
                     ("O", True, "spectator_pass_through")]
    # 1 水袋对照:单条目(份数不同 ⇒ 不同供给/不同净反应)
    spec1 = _supply_spec(monkeypatch, _TPL_LHS_1W, _TPL_RHS_1W)
    assert len(spec1["co_substrate_states"]) == 1
    assert spec1["cosubstrate_event_contract"]["co_substrate_state_refs"] \
        != spec["cosubstrate_event_contract"]["co_substrate_state_refs"]


# ================================================================ PC-S4


def test_bare_wildcard_bag_not_supplied(monkeypatch) -> None:
    """裸通配袋(*)不供给:维持现状拦截(wildcard_blocked;不入池);
    [H]*[H] 等含通配原子具体小分子不属裸通配袋(按自身身份供给)。"""
    _stub_resolver(monkeypatch, [_donor_ref(
        "synthetic:rhea-wc", _TPL_LHS_1W + ".*", _TPL_RHS_1W + ".*")])
    provider = default_pool_provider(resolve_config(), engine=None)
    specs = provider(_SUBSTRATE)
    assert not [s for s in specs
                if s.get("cosubstrate_event_contract") is not None]
    diag = provider.last_diagnostics
    assert diag["analog_cosub_supply_wildcard_blocked"] == 1
    assert diag["analog_cosub_supply_rescued"] == 0
    # 单元口径(真实形状袋:酯主+水+通配;主判定无 0 分并列歧义):
    # 裸通配组分在供给内 ⇒ wildcard_blocked;含通配原子的具体小分子
    # ([H]*[H])不属裸通配袋 ⇒ 按自身身份供给
    wc = analog_cosub_supply(mapped_lhs=_TPL_LHS_1W + ".*",
                             mapped_rhs=_TPL_RHS_1W,
                             substrate_smiles=_SUBSTRATE)
    assert wc["status"] == "wildcard_blocked"
    concrete = analog_cosub_supply(mapped_lhs=_TPL_LHS_1W + ".[H]*[H]",
                                   mapped_rhs=_TPL_RHS_1W,
                                   substrate_smiles=_SUBSTRATE)
    assert concrete["status"] == "supply"


# ================================================================ PC-S5


def test_pool_policy_version_carrier(monkeypatch) -> None:
    """版本承载:policy-7 + 供给登记面 + 诊断键在位。"""
    assert S5B_POOL_POLICY_VERSION == "s5b-pool-policy-7"
    assert S5B_ANALOG_COSUB_SUPPLY_VERSION == "s5b-analog-cosub-supply-1"
    _supply_spec(monkeypatch, _TPL_LHS_1W, _TPL_RHS_1W)


# ================================================================ PC-S6/S7


def _run_e2e(monkeypatch, tmp_path: Path) -> tuple[dict, dict, Path]:
    """全链:build(policy-7 池)→ run(scripted 桩)→ native export。"""
    _stub_resolver(monkeypatch, [_donor_ref(
        _RECORD_1W, _TPL_LHS_1W, _TPL_RHS_1W)])
    questions = tmp_path / "questions.jsonl"
    questions.write_text(json.dumps({
        "qid": "c-supply-e2e-1", "substrate_smiles": _SUBSTRATE,
        "products_smiles": list(_GOLD)}) + "\n", encoding="utf-8")
    manifest = build_question_batch(
        questions, tmp_path / "batch", batch_tag="c-supply-e2e",
        pool_provider=default_pool_provider(resolve_config(),
                                            engine=None),
        provider_kind="scripted", synthetic_review=True)
    entry = manifest["entries"][0]
    run_input = json.loads(
        (tmp_path / "batch" / "run_inputs" /
         "c-supply-e2e-1.json").read_text(encoding="utf-8"))
    model = ScriptedRealModelAdapter(
        strategy="first_pool", model_id="c-supply-e2e-model")
    summary = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_input["run_id"], smiles=_SUBSTRATE,
        plan=run_input["plan"], model=model, profile_policy=_PROFILE)
    assert summary["counts"]["events"] >= 1, summary.get("stop")
    graph = json.loads((tmp_path / "batch" / entry["graph_rel"]).read_text(
        encoding="utf-8"))
    payload = json.loads(sorted(
        (tmp_path / "runs" / run_input["run_id"] / "native_export").glob(
            "*/payload.json"))[0].read_text(encoding="utf-8"))
    return summary, {"payload": payload, "graph": graph}, tmp_path


def test_declaration_chain_emission_end_to_end(monkeypatch,
                                               tmp_path) -> None:
    """PC-S6:事件提交前 provenance_records 行落库;链
    event→hypothesis.provenance_refs→行(record_id 匹配)→
    record_equation 可解析(pred1 消费契约;native export 内闭合)。"""
    _summary, bag, _tmp = _run_e2e(monkeypatch, tmp_path)
    payload = bag["payload"]
    rows = payload.get("provenance_records") or []
    assert rows, "声明链发射:provenance_records 行应随导出在案"
    bodies = {}
    for row in rows:
        body = row.get("payload")
        if isinstance(body, str):
            body = json.loads(body)
        bodies[str(row.get("record_id"))] = body
    hyp_refs = []
    for h in payload.get("hypotheses") or []:
        body = h.get("payload")
        if isinstance(body, str):
            body = json.loads(body)
        hyp_refs.extend(str(x) for x in body.get("provenance_refs") or [])
    assert hyp_refs, "假设应携带 provenance_refs"
    assert set(hyp_refs) <= set(bodies), "引用不得悬空"
    equation = bodies[hyp_refs[0]].get("record_equation")
    assert equation and equation["reactants"] and equation["products"]
    assert [e["smiles"] for e in equation["reactants"]] == \
        ["CCOC(C)=O", "O"]
    # 判分侧消费契约同源解析 ⇒ resolved
    event = (payload.get("events") or [])[0]
    hyp_id = str(event.get("hypothesis_id"))
    react_declared, prod_declared, status = \
        _criteria_declaration_sides(payload, hyp_id)
    assert status == "resolved"
    from pathway_v43.domain.identity import cn_identity

    assert cn_identity("O") in react_declared


def test_v2_exemption_positive_control_end_to_end(monkeypatch,
                                                  tmp_path) -> None:
    """PC-S7:水袋 extra 经 v2 三谓词全过 ⇒ v1_exempt + 事件升 exact;
    v1 口径同载荷维持 partial(豁免关=基线零漂移)。"""
    _summary, bag, _tmp = _run_e2e(monkeypatch, tmp_path)
    payload, graph = bag["payload"], bag["graph"]
    nodes = match_reference_nodes(graph, payload)
    edges_v1 = match_reference_edges(
        graph, payload, nodes, criteria_version="ppv1-criteria-v1")
    edges_v2 = match_reference_edges(
        graph, payload, nodes, criteria_version="ppv1-criteria-v2")

    def _exact(items):
        return sum(1 for e in items for bucket in
                   ("matched_events", "coverage_mismatch_events")
                   for item in (e.get(bucket) or [])
                   if item.get("participant_coverage") == "exact")

    assert _exact(edges_v1) == 0, "v1 口径(豁免关)应维持 partial"
    assert _exact(edges_v2) >= 1, "v2 口径水袋 extra 应获豁免升 exact"
    exempted = [
        occ for e in edges_v2
        for bucket in ("matched_events", "coverage_mismatch_events")
        for item in (e.get(bucket) or [])
        for occ in (item.get("exempted_participants") or [])]
    assert exempted, "v1_exempt 披露条目应在案"
    for occ in exempted:
        assert occ["tier"] == "v1_exempt"
        assert occ["pred1_record_declared"] == "true"
        assert occ["pred2_element_traceable"] in ("pass",
                                                  "not_applicable")
        assert occ["pred3_cn_identity_member"] is True


# ================================================================ NC-S1


def _base_supply_spec() -> dict:
    """最小合法供给 spec(供负控变形;形状 = PC-S1 装配输出)。"""
    from pathway_v43.pollutant.chemstate import build_chemical_state

    def _state(smiles: str) -> str:
        return build_chemical_state(
            smiles, "source_product", [{"record": "synthetic:rhea-x1"}]
        ).state_id

    return {
        "key": "tpl-synthetic:rhea-x1",
        "product_smiles": "CC(C)C(=O)O",
        "coproducts": ["CCO"],
        "coefficient": 1,
        "transformation_ref": "synthetic:rhea-x1",
        "origin_group_key": "analog-template:synthetic:rhea-x1",
        "edits": [],
        "donor": {"center_atom_ids": ["D_2"]},
        "alignment": {"status": "resolved", "donor_to_current": {},
                      "equivalence_classes": [],
                      "ref": "corpus-template:x"},
        "expectation": {"target_smiles": "CC(C)C(=O)O.CCO"},
        "participants": [
            {"state_ref": _state(_SUBSTRATE), "side": "reactant",
             "role": "primary_substrate", "coefficient": None,
             "coefficient_status": "unknown"},
            {"state_ref": _state("O"), "side": "reactant",
             "role": "cosubstrate", "coefficient": None,
             "coefficient_status": "unknown"},
            {"state_ref": _state("CC(C)C(=O)O"), "side": "product",
             "role": "principal_product", "coefficient": None,
             "coefficient_status": "unknown"},
            {"state_ref": _state("CCO"), "side": "product",
             "role": "coproduct", "coefficient": None,
             "coefficient_status": "unknown"},
        ],
        "participant_list_status": "declared_complete",
        "co_substrate_states": [
            {"smiles": "O", "state_ref": _state("O"),
             "source_ref": "tpl-synthetic:rhea-x1",
             "strict_identity": _state("O"), "spectator": False,
             "consumption_status": "unknown"}],
        "declared_copy_components": [],
        "cosubstrate_event_contract": {
            "record_key": "tpl-synthetic:rhea-x1",
            "co_substrates": [{"smiles": "O"}],
            "record_products": ["CC(C)C(=O)O", "CCO"],
            "copy_state_refs": [],
            "co_substrate_state_refs": [_state("O")],
        },
        "execution_input_smiles": _SUBSTRATE + ".O",
        "record_equation": {"reactants": [{"smiles": _SUBSTRATE},
                                          {"smiles": "O"}],
                            "products": [{"smiles": "CC(C)C(=O)O"},
                                         {"smiles": "CCO"}]},
        "record_equation_ref": "analog-supply:tpl-synthetic:rhea-x1",
    }


def test_declaration_fail_closed_shapes() -> None:
    """NC-S1:发射面声明不成对/条目不可解析/执行输入篡改 ⇒ 结构化拒。"""
    from pathway_v43.pollutant.chemstate import build_chemical_state

    substrate_state = build_chemical_state(
        _SUBSTRATE, "raw_input", [{"record": "ppv1-substrate:test"}])
    spec = _base_supply_spec()
    spec.pop("record_equation")
    with pytest.raises(ProductionContractError) as exc:
        prepare_hypothesis(spec, parent_path_id="p",
                           substrate_state=substrate_state)
    assert exc.value.detail["kind"] == "record_equation_missing"

    spec = _base_supply_spec()
    spec["record_equation"] = {"reactants": [{"smiles": _SUBSTRATE}],
                               "products": [{"smiles": "not-a-molecule"}]}
    with pytest.raises(ProductionContractError) as exc:
        prepare_hypothesis(spec, parent_path_id="p",
                           substrate_state=substrate_state)
    assert exc.value.detail["kind"] == "record_equation_entry_unparseable"

    spec = _base_supply_spec()
    spec["execution_input_smiles"] = _SUBSTRATE + ".N"  # 冒充执行输入
    with pytest.raises(ProductionContractError) as exc:
        prepare_hypothesis(spec, parent_path_id="p",
                           substrate_state=substrate_state)
    assert exc.value.detail["kind"] == "execution_input_multiset_mismatch"


def test_nc10_participants_shrink_rejected(monkeypatch) -> None:
    """NC-S2(复用 corpus 消费面):供给 spec 删 participants ⇒ 结构化拒
    (缺省装配不得覆盖共底物语义)。"""
    from pathway_v43.pollutant.chemstate import build_chemical_state

    substrate_state = build_chemical_state(
        _SUBSTRATE, "raw_input", [{"record": "ppv1-substrate:test"}])
    spec = _base_supply_spec()
    spec.pop("participants")
    with pytest.raises(ProductionContractError) as exc:
        prepare_hypothesis(spec, parent_path_id="p",
                           substrate_state=substrate_state)
    assert exc.value.detail["kind"] == "cosubstrate_participants_required"


def test_no_declaration_spec_zero_change() -> None:
    """NC-S3:无声明 spec ⇒ hypothesis provenance_refs 保持 []、prepared
    不带发射载荷(既有路径行为字节等价)。"""
    from pathway_v43.pollutant.chemstate import build_chemical_state

    substrate_state = build_chemical_state(
        "CCO", "raw_input", [{"record": "ppv1-substrate:test"}])
    spec = {
        "product_smiles": "CC=O",
        "coproducts": [],
        "edits": [],
        "donor": {"center_atom_ids": ["D_1"]},
        "alignment": {"status": "resolved", "donor_to_current": {},
                      "equivalence_classes": [], "ref": "x"},
        "expectation": {"target_smiles": "CC=O"},
    }
    prepared = prepare_hypothesis(spec, parent_path_id="p",
                                  substrate_state=substrate_state)
    assert prepared["hypothesis"].to_dict()["provenance_refs"] == []
    assert "record_equation_provenance" not in prepared or \
        prepared["record_equation_provenance"] is None
    assert "execution_input_smiles" not in prepared["tool_inputs"]
