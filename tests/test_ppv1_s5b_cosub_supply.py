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
- PC-S4 wildcard 袋整袋不供给(冻结边界:P2-WILDCARD-01 回修后裸
  ``*`` 与 [H]*[H] 等含未定义 dummy 原子组分走同一判据,status=
  wildcard_blocked);
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
  prepared 不带发射载荷(既有路径行为字节等价);

REAUDIT 回修控件(2026-10-19,P1-BUILD-01/P1-RUN-01/P2/P3):
- P1-BUILD-01 反例:同 CN 相反手性双份 + 底物对后位 ⇒ 扣除**选定
  main_idx 位置**那一份(位置扣除,不是第一份同 CN),供给袋按原序
  保真保留另一手性份;正确袋编译 = ambiguous_alignment(歧义不被
  错误供给消除),旧错袋反事实可 compiled(误救形态,负控);
  合法正控:两份完全同结构仍恰供一份;
- P1-RUN-01 B3 四控(全链 crash 注入):正常提交 / B3 未写(恢复
  幂等补发射后提交)/ 记录方程写异常(恢复补发射)/ 既定内容冲突
  (拒绝提交、零事件/零提交、旧行保全)+ 合法同源来源已在位正控
  (恢复幂等 no-op 后提交);
- P1-RUN-01 追修(2026-10-19 修订轮)**载荷内容校验兜底**:经公开
  writer **首写缺方程载荷**(合法事件+合法 refs、写入侧兼容不强制)
  ⇒ 恢复结构化拒(emission_missing,H07 同形:零事件/零提交/零消费、
  bundle 保全、无悬空声明链);首写坏载荷同形拒(内容不可解析
  payload_unparseable / record_id 不属 refs ref_unbound / refs 有
  未覆盖悬空项 refs_uncovered);四种拒后零翻转(存量四控/正控全绿);
- P2-WILDCARD-01:含 dummy 原子组分的袋整袋 wildcard_blocked(池级
  + 单元级);
- P3-INPUT-01:execution_input_smiles 键在位含 null ⇒ 首次消费
  结构化拒(fail-closed,不回落裸底物);键不在位 = 无声明兼容边界。

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


def _donor_ref(record_id: str, mapped_lhs: str, mapped_rhs: str,
               center_atoms: list[int] | None = None) -> DonorRef:
    return DonorRef(
        record_id=record_id, index="analog_corpus_templates",
        asset_file="synthetic", asset_sha256="0" * 64, line_no=1,
        mapping_quality="mapped_bijection",
        reactant_smiles=".".join(c for c in
                                 (mapped_lhs.split("."))),
        product_smiles=".".join(mapped_rhs.split(".")),
        mapped_lhs=mapped_lhs, mapped_rhs=mapped_rhs,
        center_atoms=list(center_atoms if center_atoms is not None
                          else _CENTER))


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
    """PC-S4:wildcard 袋(裸 * 与 [H]*[H] 等含未定义 dummy 原子组分)
    **整袋不供给**(P2-WILDCARD-01 回修:恢复冻结设计边界,两形态走
    同一判据;此前只拦裸 * 的"具体小分子组分照供"是未授权收窄)。"""
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
    # 裸 * 与含 dummy 原子的具体小分子([H]*[H])同属 wildcard 袋 ⇒
    # wildcard_blocked(整袋不供给)
    wc = analog_cosub_supply(mapped_lhs=_TPL_LHS_1W + ".*",
                             mapped_rhs=_TPL_RHS_1W,
                             substrate_smiles=_SUBSTRATE)
    assert wc["status"] == "wildcard_blocked"
    concrete = analog_cosub_supply(mapped_lhs=_TPL_LHS_1W + ".[H]*[H]",
                                   mapped_rhs=_TPL_RHS_1W,
                                   substrate_smiles=_SUBSTRATE)
    assert concrete["status"] == "wildcard_blocked"
    # 无 dummy 的对照袋照常供给(不是全拒替代正确多重集)
    clean = analog_cosub_supply(mapped_lhs=_TPL_LHS_1W,
                                mapped_rhs=_TPL_RHS_1W,
                                substrate_smiles=_SUBSTRATE)
    assert clean["status"] == "supply"


def test_concrete_wildcard_bag_not_supplied_pool_level(monkeypatch) -> None:
    """PC-S4b(P2 池级):[H]*[H] 具体 dummy 组分的袋不入池 —— 修复前
    该袋经供给编译入池(未授权收窄);修复后整袋拦截、诊断计数、
    拒因维持 no_alignment 口径。"""
    _stub_resolver(monkeypatch, [_donor_ref(
        "synthetic:rhea-wc2",
        _TPL_LHS_1W + ".[H]*[H]", _TPL_RHS_1W + ".[H]*[H]")])
    provider = default_pool_provider(resolve_config(), engine=None)
    specs = provider(_SUBSTRATE)
    assert not [s for s in specs
                if s.get("cosubstrate_event_contract") is not None], \
        "含 dummy 原子组分的袋不得经供给入池(冻结边界)"
    diag = provider.last_diagnostics
    assert diag["analog_cosub_supply_wildcard_blocked"] == 1
    assert diag["analog_cosub_supply_rescued"] == 0
    assert int(diag.get("analog_cosub_supply_compile_attempted", 0)) == 0
    assert diag["analog_pregate_skipped"] == 1


# ================================================================ PC-S5


def test_pool_policy_version_carrier(monkeypatch) -> None:
    """版本承载:policy-7 + 供给登记面 + 诊断键在位。"""
    # T-G C2(2026-10-19):重刀 R2' 路由/准入解耦接线 + s5b-compiler-4 中心锚定对齐(池成员变化)⇒ 8
    assert S5B_POOL_POLICY_VERSION == "s5b-pool-policy-9"
    assert S5B_ANALOG_COSUB_SUPPLY_VERSION == "s5b-analog-cosub-supply-1"
    _supply_spec(monkeypatch, _TPL_LHS_1W, _TPL_RHS_1W)


# ================================================================ P1-BUILD-01
# (REAUDIT 回修 2026-10-19:主份扣除按选定 main_idx 位置,不是第一份同 CN)

# 合成手性模板:两份相反手性的 α-氯代醇 + 乙酰供体;底物 = **后位**
# 那一份的手性(立体盲指纹 ⇒ 两份 Tanimoto 并列 1.0 ⇒ main_idx=1)
_CHIR_A = "[CH2:1]([OH:2])[C@H:3]([F:4])[Cl:5]"
_CHIR_B = "[CH2:6]([OH:7])[C@@H:8]([F:9])[Cl:10]"
_CHIR_C = "[CH3:11][C:12](=[O:13])[OH:14]"
_CHIR_LHS = _CHIR_A + "." + _CHIR_B + "." + _CHIR_C
_CHIR_RHS = ("[CH2:1]([O:2][C:12](=[O:13])[CH3:11])[C@H:3]([F:4])"
             "[Cl:5]." + _CHIR_B + ".[OH2:14]")
_CHIR_SUB = "OC[C@@H](F)Cl"          # = 后位份(B)的手性
_CHIR_OTHER = "OC[C@H](F)Cl"         # = 前位份(A)的手性(应被保真供给)
_RECORD_CHIR = "synthetic:rhea-chir"


def test_supply_deducts_selected_main_idx_position() -> None:
    """P1-BUILD-01 反例(单元):同 CN 相反手性双份、底物对后位 ⇒ 扣除
    **选定位置(index1)**那一份,供给袋按原序保真保留 index0 那份
    (旧实现删"第一份同 CN"⇒ 把底物自身手性份当供给,消除严格结构
    歧义);合法正控:两份完全同结构仍恰供一份。"""
    from rdkit import Chem

    def _canon(s: str) -> str:
        return Chem.MolToSmiles(Chem.MolFromSmiles(s))

    out = analog_cosub_supply(mapped_lhs=_CHIR_LHS, mapped_rhs=_CHIR_RHS,
                              substrate_smiles=_CHIR_SUB)
    assert out["status"] == "supply"
    assert out["main_idx"] == 1          # 并列取后位(与底物对应)
    assert out["main_copies"] == 2
    bag = [sc for _mc, sc in out["supply"]]
    # 供给袋保真:保留 index0 的**另一手性**份(不是底物自身手性),
    # 其余组分按原序(乙酰供体在 index2)—— 旧实现此处为底物手性份
    assert bag == [_canon(_CHIR_OTHER), "CC(=O)O"]
    assert bag[0] != _canon(_CHIR_SUB)
    # 合法正控:两份**完全同结构**仍恰供一份(照常供给,不整袋拒)
    dup = analog_cosub_supply(
        mapped_lhs=_SUBSTRATE + "." + _SUBSTRATE,
        mapped_rhs="CC=O", substrate_smiles=_SUBSTRATE)
    assert dup["status"] == "supply"
    assert dup["main_copies"] == 2
    assert [sc for _mc, sc in dup["supply"]] == [_canon(_SUBSTRATE)]


def test_supply_main_idx_bag_fidelity_compile_level() -> None:
    """P1-BUILD-01 反例(编译级):保真袋(另一手性份在供给)⇒ 编译
    如实拒 ambiguous_alignment(严格结构歧义不被错误供给消除);
    旧错袋(底物自身手性份冒充供给)反事实 compiled —— 误救形态
    负控,证明本修真的关掉了它。"""
    from rdkit import Chem

    from pathway_v43.pollutant.s5b_compiler import (
        compile_donor_template,
        template_elements_fit,
    )

    def _canon(s: str) -> str:
        return Chem.MolToSmiles(Chem.MolFromSmiles(s))

    out = analog_cosub_supply(mapped_lhs=_CHIR_LHS, mapped_rhs=_CHIR_RHS,
                              substrate_smiles=_CHIR_SUB)
    bag = [sc for _mc, sc in out["supply"]]
    # 前置门拒(模板袋 ⊄ 底物)⇒ 供给救援;供给袋过门
    assert not template_elements_fit(_CHIR_LHS, _CHIR_SUB)
    sub_new = _CHIR_SUB + "." + ".".join(bag)
    assert template_elements_fit(_CHIR_LHS, sub_new)
    out_new = compile_donor_template(
        mapped_lhs=_CHIR_LHS, mapped_rhs=_CHIR_RHS,
        center_atoms=[2, 3, 12], substrate_smiles=sub_new,
        record_id="synthetic:rhea-chir")
    assert out_new.get("status") == "unsupported"
    assert out_new.get("reason") == "ambiguous_alignment"
    assert out_new["detail"]["n_alignments"] >= 2
    # 负控(旧错袋反事实):供 index1(与底物同手性)⇒ 编译通过,
    # 即 REAUDIT 复现的具体误救;修复后供给袋不再产出该形态
    sub_old = _CHIR_SUB + "." + _canon(_CHIR_B) + ".CC(=O)O"
    out_old = compile_donor_template(
        mapped_lhs=_CHIR_LHS, mapped_rhs=_CHIR_RHS,
        center_atoms=[2, 3, 12], substrate_smiles=sub_old,
        record_id="synthetic:rhea-chir")
    assert out_old.get("status") == "compiled"
    assert bag != [_canon(_CHIR_SUB), "CC(=O)O"]


def test_supply_main_idx_bag_fidelity_pool_level(monkeypatch) -> None:
    """P1-BUILD-01 反例(池级):手性模板经真实池装配 ⇒ 供给尝试后
    编译如实拒(不入池、不登记 rescued);拒因 = ambiguous_alignment
    (诊断谱系行在案),无误救 spec。"""
    _stub_resolver(monkeypatch, [_donor_ref(
        _RECORD_CHIR, _CHIR_LHS, _CHIR_RHS, center_atoms=[2, 3, 12])])
    provider = default_pool_provider(resolve_config(), engine=None)
    specs = provider(_CHIR_SUB)
    assert not [s for s in specs
                if s.get("cosubstrate_event_contract") is not None]
    diag = provider.last_diagnostics
    assert diag["analog_cosub_supply_compile_attempted"] == 1
    assert diag["analog_cosub_supply_rescued"] == 0
    assert (diag.get("compile_failure_histogram") or {}).get(
        "ambiguous_alignment") == 1
    rows = [r for r in (diag.get("candidates") or [])
            if r.get("outcome") == "compile_rejected"]
    assert rows and rows[0]["reason"] == "ambiguous_alignment"


# ================================================================ P3-INPUT-01


def test_execution_input_key_present_null_rejected() -> None:
    """P3-INPUT-01:execution_input_smiles 键在位含 null ⇒ 首次消费
    结构化拒(不回落裸底物执行);键不在位 = 无声明兼容边界(既有
    路径零变化)。"""
    from pathway_v43.pollutant.chemstate import build_chemical_state

    substrate_state = build_chemical_state(
        _SUBSTRATE, "raw_input", [{"record": "ppv1-substrate:test"}])
    spec = _base_supply_spec()
    spec["execution_input_smiles"] = None
    with pytest.raises(ProductionContractError) as exc:
        prepare_hypothesis(spec, parent_path_id="p",
                           substrate_state=substrate_state)
    assert exc.value.detail["kind"] == "execution_input_invalid"
    assert exc.value.detail["value_type"] == "NoneType"
    # 形状披露:空串同样结构化拒(非静默)
    spec = _base_supply_spec()
    spec["execution_input_smiles"] = "   "
    with pytest.raises(ProductionContractError) as exc:
        prepare_hypothesis(spec, parent_path_id="p",
                           substrate_state=substrate_state)
    assert exc.value.detail["kind"] == "execution_input_invalid"
    # 兼容边界:键不在位 ⇒ 无声明,prepare 照常(既有路径零变化)
    spec = _base_supply_spec()
    spec.pop("execution_input_smiles")
    prepared = prepare_hypothesis(spec, parent_path_id="p",
                                  substrate_state=substrate_state)
    assert "execution_input_smiles" not in prepared["tool_inputs"]


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


# ================================================================ P1-RUN-01
# (REAUDIT 回修 2026-10-19:B3 恢复先幂等发射/核验记录方程 provenance
# (含内容冲突门)再提交;验收 = 正常/B3 未写/写异常/既定冲突四控 +
# 合法同源来源已在位恢复正控)

_EXPAND_TASK_BUNDLE = "search_commit_bundle.json"


def _b3_build(monkeypatch, tmp_path: Path):
    """B3 控件全链前置:build(policy-7 池)+ run_input(scripted 桩)。"""
    _stub_resolver(monkeypatch, [_donor_ref(
        _RECORD_1W, _TPL_LHS_1W, _TPL_RHS_1W)])
    questions = tmp_path / "questions.jsonl"
    questions.write_text(json.dumps({
        "qid": "c-supply-b3-1", "substrate_smiles": _SUBSTRATE,
        "products_smiles": list(_GOLD)}) + "\n", encoding="utf-8")
    build_question_batch(
        questions, tmp_path / "batch", batch_tag="c-supply-b3",
        pool_provider=default_pool_provider(resolve_config(), engine=None),
        provider_kind="scripted", synthetic_review=True)
    run_input = json.loads(
        (tmp_path / "batch" / "run_inputs" /
         "c-supply-b3-1.json").read_text(encoding="utf-8"))
    model = ScriptedRealModelAdapter(
        strategy="first_pool", model_id="c-supply-b3-model")
    return run_input, model


def _b3_start(run_input: dict, model, tmp_path: Path, *,
              crash_after: str | None = None) -> dict:
    return start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_input["run_id"], smiles=_SUBSTRATE,
        plan=run_input["plan"], model=model, profile_policy=_PROFILE,
        crash_after=crash_after)


def _b3_store(tmp_path: Path, run_id: str):
    from pathway_v43.pollutant.store import PollutantPathwayStore
    return PollutantPathwayStore(
        tmp_path / "runs" / run_id / "pollutant.sqlite")


def _b3_ledger(tmp_path: Path, run_id: str):
    from pathway_v43.pollutant.search import SearchLedger
    from pathway_v43.storage.artifact_store import ArtifactStore
    return SearchLedger(_b3_store(tmp_path, run_id),
                        ArtifactStore(tmp_path / "runs", run_id), run_id)


def _b3_counts(store, run_id: str,
               action_id: str | None = None) -> dict:
    """run 事件数 + expand action(或全 run)提交记录数。"""
    if action_id is None:
        sql = ("SELECT COUNT(*) FROM search_commit_records"
               " WHERE run_id = ?")
        args: tuple = (run_id,)
    else:
        sql = ("SELECT COUNT(*) FROM search_commit_records"
               " WHERE run_id = ? AND action_id = ?")
        args = (run_id, action_id)
    return {
        "events": store.counts()["events"],
        "commits": store.conn.execute(sql, args).fetchone()[0],
    }


def _b3_claimed_expand_action(store, run_id: str) -> str:
    """crash 断点在案的 expand action(claimed;全链 e2e 用)。"""
    rows = store.conn.execute(
        "SELECT action_id FROM search_actions WHERE run_id = ?"
        " AND action_kind = 'expand_hypothesis' AND status = 'claimed'",
        (run_id,)).fetchall()
    assert len(rows) == 1, "B3 断点应有恰一个已认领 expand action"
    return str(rows[0]["action_id"])


def _b3_bundle_emission(tmp_path: Path, run_id: str) -> dict:
    """读 crash 后落盘的 commit bundle(公共读取入口)内发射载荷。"""
    from pathway_v43.pollutant.search import read_search_artifact
    from pathway_v43.storage.artifact_store import ArtifactStore

    art = ArtifactStore(tmp_path / "runs", run_id)
    bundles = sorted(
        (tmp_path / "runs" / run_id / "results").glob(
            f"*/{_EXPAND_TASK_BUNDLE}"))
    assert bundles, "B3 断点应有可恢复 bundle"
    return read_search_artifact(
        art, bundles[0].parent.name,
        "search_commit_bundle")["payload"]["record_equation_provenance"]


def _b3_recover(tmp_path: Path, run_id: str) -> tuple[dict, dict]:
    ledger = _b3_ledger(tmp_path, run_id)
    report = ledger.recover_run(run_id)
    entry = [a for a in report["actions"]
             if a["action_kind"] == "expand_hypothesis"][0]
    return ledger, entry


def _b3_conflict_payload(payload: dict) -> dict:
    """同 ref **不同内容**的冲突旧方程(内容冲突门触发件)。"""
    conflicting = json.loads(json.dumps(payload))
    conflicting["record_equation"]["products"] = list(
        conflicting["record_equation"]["products"]) + [{"smiles": "C"}]
    return conflicting


_B3_REF = f"analog-supply:tpl-{_RECORD_1W}"


def _b3_direct_drive(monkeypatch, tmp_path: Path, run_name: str, *,
                     inject=None) -> dict:
    """生产段直驱夹具(P1-RUN-01 写异常/既定冲突控:不注入 crash;
    池 spec → prepare → ledger/action/context →(可选 inject)→
    expand_hypothesis_production(write_bundle=True)⇒ bundle 落盘而
    记录方程写入失败/冲突的真实形态;正常路径同一夹具)。"""
    from pathway_v43.pollutant.chemstate import build_chemical_state
    from pathway_v43.pollutant.path_context import build_path_context
    from pathway_v43.pollutant.production import persist_context
    from pathway_v43.pollutant.profile import (
        build_profile_identity_block,
    )
    from pathway_v43.pollutant.search import (
        SearchLedger,
        search_policy_version,
    )
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.storage.artifact_store import ArtifactStore

    spec = _supply_spec(monkeypatch, _TPL_LHS_1W, _TPL_RHS_1W)
    store = PollutantPathwayStore(tmp_path / f"{run_name}.sqlite")
    artifacts = ArtifactStore(tmp_path / "runs", run_name)
    ledger = SearchLedger(store, artifacts, run_name)
    ledger.register_search_run(run_name, build_profile_identity_block())
    substrate_state = build_chemical_state(
        _SUBSTRATE, "raw_input",
        [{"record": f"ppv1-substrate:{run_name}"}])
    prepared = prepare_hypothesis(
        spec, parent_path_id="p1", substrate_state=substrate_state,
        transformation_ref=str(spec.get("transformation_ref") or ""))
    context = build_path_context(
        condition_facts=[], scenario_ref="", dependencies=[])
    context_ref = persist_context(artifacts, context)
    out = ledger.enqueue_action(
        run_id=run_name, parent_path_id="p1", context_ref=context_ref,
        subject_ref=prepared["hypothesis"].hypothesis_id,
        action_kind="expand_hypothesis", parent_search_revision=0,
        policy_version=search_policy_version(),
        payload={"task_key": "tk1"}, depth=1)
    action_id = out["action_id"]
    receipt = ledger.claim_action(action_id, worker_id="w1")
    attempt_id = (receipt.get("attempt_refs") or [""])[0]
    if inject is not None:
        inject(store)
    return {"ledger": ledger, "prepared": prepared, "context": context,
            "substrate_state": substrate_state, "action_id": action_id,
            "attempt_id": attempt_id, "task_key": "tk1",
            "run_id": run_name}


def _b3_drive(handle: dict, *, crash_after: str | None = None) -> dict:
    from pathway_v43.pollutant.production import (
        expand_hypothesis_production,
    )

    return expand_hypothesis_production(
        handle["ledger"], handle["action_id"],
        prepared=handle["prepared"], context=handle["context"],
        worker_id="w1", attempt_id=handle["attempt_id"],
        task_key=handle["task_key"],
        substrate_state=handle["substrate_state"],
        limits=handle["ledger"]._limits(handle["run_id"]), depth=1,
        parent_search_revision=0, write_bundle=True,
        crash_after=crash_after)


def _b3_recover_direct(tmp_path: Path, run_name: str) -> tuple[dict, dict]:
    from pathway_v43.pollutant.search import SearchLedger
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.storage.artifact_store import ArtifactStore

    store = PollutantPathwayStore(tmp_path / f"{run_name}.sqlite")
    ledger = SearchLedger(store, ArtifactStore(tmp_path / "runs",
                                               run_name), run_name)
    report = ledger.recover_run(run_name)
    entry = [a for a in report["actions"]
             if a["action_kind"] == "expand_hypothesis"][0]
    return ledger, entry


def _b3_hypothesis_refs(store) -> set:
    refs = set()
    for r in store.conn.execute("SELECT payload FROM hypotheses").fetchall():
        refs.update(str(x) for x in
                    (json.loads(r["payload"]).get("provenance_refs") or []))
    return refs


def test_normal_submit_control_one_event_provenance_commit(
        monkeypatch, tmp_path) -> None:
    """正常提交正控(生产段直驱,无注入):事件提交前来源方程落库 ——
    1 event/1 provenance/1 commit;假设 provenance_refs 全可解析
    (B3 回修不改正常路径)。"""
    handle = _b3_direct_drive(monkeypatch, tmp_path,
                              "c-supply-b3-normal")
    result = _b3_drive(handle)
    assert result.get("status") == "submitted"
    store = handle["ledger"].store
    assert _b3_counts(store, handle["run_id"]) == {"events": 1,
                                                   "commits": 1}
    row = store.get_provenance(_B3_REF)
    assert row is not None
    assert row["record_equation"]["reactants"] and \
        row["record_equation"]["products"]
    refs = _b3_hypothesis_refs(store)
    assert refs == {_B3_REF}
    assert store.get_provenance(_B3_REF) is not None
    store.close()


def test_b3_not_written_recovery_emits_before_submit(monkeypatch,
                                                     tmp_path) -> None:
    """B3 未写控:P1-RUN-01 反例 —— bundle 已写、来源未写、事件未提交
    ⇒ 恢复**先幂等发射记录方程再提交**:1 event/1 provenance/1 commit,
    声明链不悬空(hypothesis.provenance_refs 行 payload 在案);
    bundle 载荷携带发射面(修复前恢复直接 submit ⇒ 1/0/1 unparseable)。"""
    from pathway_v43.pollutant.search import SearchCrashInjection

    run_input, model = _b3_build(monkeypatch, tmp_path)
    run_id = run_input["run_id"]
    with pytest.raises(SearchCrashInjection):
        _b3_start(run_input, model, tmp_path,
                  crash_after="after_bundle_written")
    # 断点事实:event 0、来源未写、bundle 在位且带完整发射载荷
    store0 = _b3_store(tmp_path, run_id)
    action_id = _b3_claimed_expand_action(store0, run_id)
    assert _b3_counts(store0, run_id, action_id) == {"events": 0,
                                                     "commits": 0}
    assert store0.get_provenance(f"analog-supply:tpl-{_RECORD_1W}") is None
    store0.close()
    emission = _b3_bundle_emission(tmp_path, run_id)
    ref = str(emission["record_id"])

    ledger, entry = _b3_recover(tmp_path, run_id)
    assert entry["boundary"] == "B3_artifact_written_event_uncommitted"
    assert str(entry["disposition"]).startswith(
        "consumed_same_output_attempt")
    assert _b3_counts(ledger.store, run_id, action_id) == {"events": 1,
                                                           "commits": 1}
    row = ledger.store.get_provenance(ref)
    assert row is not None, "恢复必须先发射来源方程再提交(不得悬空)"
    assert row["record_equation"] == emission["payload"]["record_equation"]
    # 声明链闭合:事件的假设 provenance_refs ⊆ 已在位 provenance 行
    hyp_rows = ledger.store.conn.execute(
        "SELECT payload FROM hypotheses").fetchall()
    refs = set()
    for r in hyp_rows:
        refs.update(str(x) for x in
                    (json.loads(r["payload"]).get("provenance_refs") or []))
    assert refs, "假设应携带 provenance_refs"
    assert all(ledger.store.get_provenance(x) is not None for x in refs)
    ledger.store.close()


def test_b3_same_source_in_place_positive_control(monkeypatch,
                                                  tmp_path) -> None:
    """B3 合法恢复正控:同源来源已在位(同内容)⇒ 恢复幂等发射 no-op
    后提交:1/1/1,行内容不被改写(既有合法恢复语义保持)。"""
    from pathway_v43.pollutant.search import SearchCrashInjection

    run_input, model = _b3_build(monkeypatch, tmp_path)
    run_id = run_input["run_id"]
    with pytest.raises(SearchCrashInjection):
        _b3_start(run_input, model, tmp_path,
                  crash_after="after_bundle_written")
    emission = _b3_bundle_emission(tmp_path, run_id)
    ref = str(emission["record_id"])
    store0 = _b3_store(tmp_path, run_id)
    action_id = _b3_claimed_expand_action(store0, run_id)
    store0.put_provenance(ref, run_id, dict(emission["payload"]))
    before = store0.get_provenance(ref)
    store0.close()

    ledger, entry = _b3_recover(tmp_path, run_id)
    assert str(entry["disposition"]).startswith(
        "consumed_same_output_attempt")
    assert _b3_counts(ledger.store, run_id, action_id) == {"events": 1,
                                                           "commits": 1}
    after = ledger.store.get_provenance(ref)
    assert after == before, "同内容幂等:行内容与确认时一致"
    ledger.store.close()


def test_b3_provenance_write_failure_recovery_refills(monkeypatch,
                                                      tmp_path) -> None:
    """B3 写异常控(生产段直驱):正常段记录方程写入失败(RuntimeError,
    0 event、bundle 已在位)⇒ 恢复按 bundle 载荷补发射后提交:1/1/1、
    行内容 = bundle 载荷(修复前恢复提交 ⇒ 1/0/1 悬空链)。"""
    from pathway_v43.pollutant.store import PollutantPathwayStore

    original = PollutantPathwayStore.put_provenance
    state = {"left": 1}

    def _flaky(self, record_id, run_id_arg, payload):
        if state["left"] > 0:
            state["left"] -= 1
            raise RuntimeError("injected provenance write failure")
        return original(self, record_id, run_id_arg, payload)

    monkeypatch.setattr(PollutantPathwayStore, "put_provenance", _flaky)
    handle = _b3_direct_drive(monkeypatch, tmp_path,
                              "c-supply-b3-werr")
    with pytest.raises(RuntimeError):
        _b3_drive(handle)
    assert state["left"] == 0, "注入应已命中记录方程写入"
    store0 = handle["ledger"].store
    assert _b3_counts(store0, handle["run_id"]) == {"events": 0,
                                                    "commits": 0}
    assert store0.get_provenance(_B3_REF) is None
    store0.close()
    emission = _b3_bundle_emission(tmp_path, handle["run_id"])
    assert str(emission["record_id"]) == _B3_REF

    ledger, entry = _b3_recover_direct(tmp_path, handle["run_id"])
    assert entry["boundary"] == "B3_artifact_written_event_uncommitted"
    assert str(entry["disposition"]).startswith(
        "consumed_same_output_attempt")
    assert _b3_counts(ledger.store, handle["run_id"]) == {"events": 1,
                                                          "commits": 1}
    row = ledger.store.get_provenance(_B3_REF)
    assert row is not None, "恢复必须先补发射来源方程再提交"
    assert row["record_equation"] == emission["payload"]["record_equation"]
    ledger.store.close()


def test_b3_existing_conflict_refuses_submit(monkeypatch, tmp_path) -> None:
    """B3 既定冲突控(生产段直驱):同 ref 已有**不同内容**方程 ⇒
    正常段冲突拒(0 event);恢复**拒绝提交**(不沿冲突旧方程):
    0 event/0 commit、旧行原样保全、bundle 保全在案(修复前恢复
    1/1/1 沿冲突旧方程)。"""
    from pathway_v43.pollutant.store import (
        Ppv1EventConflict,
        PollutantPathwayStore,
    )

    original = PollutantPathwayStore.put_provenance
    state = {"armed": True}

    def _preconflict(self, record_id, run_id_arg, payload):
        if state.pop("armed", False):
            # 模拟"同 ref 已有不同方程":先经公共 writer 落冲突旧行,
            # 再走真实写入 ⇒ 内容冲突门(Ppv1EventConflict)
            original(self, record_id, run_id_arg,
                     _b3_conflict_payload(dict(payload)))
        return original(self, record_id, run_id_arg, payload)

    monkeypatch.setattr(PollutantPathwayStore, "put_provenance",
                        _preconflict)
    handle = _b3_direct_drive(monkeypatch, tmp_path,
                              "c-supply-b3-conflict")
    with pytest.raises(Ppv1EventConflict):
        _b3_drive(handle)
    assert state == {}, "冲突注入应已命中正常段记录方程写入"
    store0 = handle["ledger"].store
    assert _b3_counts(store0, handle["run_id"]) == {"events": 0,
                                                    "commits": 0}
    conflicting_before = store0.get_provenance(_B3_REF)
    assert conflicting_before is not None
    store0.close()

    ledger, entry = _b3_recover_direct(tmp_path, handle["run_id"])
    assert entry["boundary"] == "B3_artifact_written_event_uncommitted"
    assert isinstance(entry["disposition"], dict)
    assert entry["disposition"]["error"] == "Ppv1EventConflict"
    assert entry["disposition"]["kind"] == "provenance_payload_mismatch"
    assert _b3_counts(ledger.store, handle["run_id"]) == {"events": 0,
                                                          "commits": 0}
    assert ledger.store.get_provenance(_B3_REF) == conflicting_before, \
        "冲突旧行原样保全(不覆盖、不洗白)"
    bundles = sorted(
        (tmp_path / "runs" / handle["run_id"] / "results").glob(
            f"*/{_EXPAND_TASK_BUNDLE}"))
    assert bundles, "bundle 保全(零消费,不删不覆盖)"
    ledger.store.close()


# ================================================================ P1-RUN-01
# 追修(2026-10-19 修订轮):恢复门**载荷内容校验兜底** —— 写入侧兼容
# 边界不动(公开 writer 不强制传发射载荷),恢复侧不得"先提交后留无法
# 解析的声明链"。


def _b3_bundle_dict(tmp_path: Path, run_name: str) -> tuple[Path, dict]:
    """读 crash 后落盘的 bundle(公共读取入口)。"""
    from pathway_v43.pollutant.search import read_search_artifact
    from pathway_v43.storage.artifact_store import ArtifactStore

    bundles = sorted((tmp_path / "runs" / run_name / "results").glob(
        f"*/{_EXPAND_TASK_BUNDLE}"))
    assert bundles, "应有可恢复 bundle"
    art = ArtifactStore(tmp_path / "runs", run_name)
    return bundles[0], read_search_artifact(
        art, bundles[0].parent.name, "search_commit_bundle")


def _b3_first_write(monkeypatch, tmp_path: Path, run_name: str,
                    mutate) -> dict:
    """生产段直驱 + 公开 writer 变形包装:**首写形态可控**的 bundle
    (bundle 已写、事件未提交、记录方程在途)⇒ 返回 handle。

    ``mutate(kwargs) -> kwargs`` 模拟不同公开调用方形态(缺参数/坏
    载荷/hypothesis 带多余 refs);写仍经公共 ``write_commit_bundle``。
    """
    from pathway_v43.pollutant.search import (
        SearchCrashInjection,
        SearchLedger,
    )

    handle = _b3_direct_drive(monkeypatch, tmp_path, run_name)
    original = SearchLedger.write_commit_bundle

    def _mutated(self, **kwargs):
        return original(self, **mutate(kwargs))

    monkeypatch.setattr(SearchLedger, "write_commit_bundle", _mutated)
    with pytest.raises(SearchCrashInjection):
        _b3_drive(handle, crash_after="bundle_written")
    # 立即还原真身:同测试内多次首写(不同 mutate)不得包装嵌套
    monkeypatch.setattr(SearchLedger, "write_commit_bundle", original)
    return handle


def _b3_assert_refused(ledger, entry, run_name: str,
                       tmp_path: Path) -> None:
    """H07 同形拒后态:零事件/零提交/零消费(无悬空链)+ bundle 保全。"""
    assert entry["boundary"] == "B3_artifact_written_event_uncommitted"
    assert isinstance(entry["disposition"], dict)
    assert entry["disposition"]["error"] == "SearchArtifactIntegrityError"
    store = ledger.store
    assert _b3_counts(store, run_name) == {"events": 0, "commits": 0}
    counts = store.counts()
    assert counts["events"] == 0 and counts["hypotheses"] == 0 and \
        counts["provenance_records"] == 0, \
        "零消费:不先提交/不先发射(无悬空声明链,可解析性不破坏)"
    bundles = sorted((tmp_path / "runs" / run_name / "results").glob(
        f"*/{_EXPAND_TASK_BUNDLE}"))
    assert bundles and bundles[0].is_file(), \
        "bundle 保全(零消费,不删不覆盖)"


def test_b3_missing_equation_payload_recovery_refuses_submit(
        monkeypatch, tmp_path) -> None:
    """P1-RUN-01 追修反例(Codex 复审 P1 最小复现):经公开接口首次
    写入一个**缺少记录方程**的载荷(合法事件 + 合法 refs;写入侧兼容
    —— 调用方不传发射参数也写得进),B3 恢复**拒绝提交**:
    结构化 disposition(emission_missing)、零事件/零提交/零消费、
    bundle 原样保全、声明链可解析性不破坏(零提交 ⇒ 无悬空行)。

    修复前事实(对拍):同形态恢复走 consumed_same_output_attempt ⇒
    1 event/1 commit,假设 provenance_refs 悬空、判分侧
    _criteria_declaration_sides = unparseable。
    """
    handle = _b3_first_write(
        monkeypatch, tmp_path, "c-supply-b3-nopayload",
        lambda kw: {k: v for k, v in kw.items()
                    if k != "record_equation_provenance"})
    run_id = handle["run_id"]
    # 断点事实:事件 0/提交 0/来源未写;bundle 在位而**无发射载荷键**
    store0 = handle["ledger"].store
    assert _b3_counts(store0, run_id) == {"events": 0, "commits": 0}
    assert store0.get_provenance(_B3_REF) is None
    store0.close()
    _path, bundle = _b3_bundle_dict(tmp_path, run_id)
    assert "record_equation_provenance" not in bundle["payload"], \
        "反例形态 = 首写缺方程载荷(写入侧兼容边界不动)"
    refs = bundle["payload"]["hypothesis_dict"]["provenance_refs"]
    assert refs == [_B3_REF], "合法来源引用在案(声明链要求记录方程)"
    before = _path.read_bytes()

    ledger, entry = _b3_recover_direct(tmp_path, run_id)
    assert entry["disposition"]["kind"] == \
        "bundle_record_equation_emission_missing"
    _b3_assert_refused(ledger, entry, run_id, tmp_path)
    assert _path.read_bytes() == before, "bundle 字节原样保全"
    ledger.store.close()


def test_b3_bad_equation_payload_recovery_refuses_submit(
        monkeypatch, tmp_path) -> None:
    """P1-RUN-01 追修(损坏/不符形态,首写经公开 writer):载荷内容
    不可解析 ⇒ payload_unparseable;record_id 不属 refs ⇒ ref_unbound;
    refs 有未覆盖悬空项(载荷与 refs 不符)⇒ refs_uncovered;假设载荷
    形状非法 ⇒ hypothesis_dict_invalid —— 各形态同形拒(零事件/
    零提交/零消费、bundle 保全),不抛原始异常中断恢复。"""
    # (a) 损坏:发射载荷 record_equation 条目不可解析(cn 失败)
    def _corrupt(kw: dict) -> dict:
        em = dict(kw["record_equation_provenance"])
        payload = dict(em["payload"])
        payload["record_equation"] = {
            "reactants": [{"smiles": "not-a-molecule"}],
            "products": [{"smiles": "CCO"}]}
        em["payload"] = payload
        kw["record_equation_provenance"] = em
        return kw

    handle = _b3_first_write(monkeypatch, tmp_path,
                             "c-supply-b3-badp", _corrupt)
    ledger, entry = _b3_recover_direct(tmp_path, handle["run_id"])
    assert entry["disposition"]["kind"] == \
        "bundle_record_equation_payload_unparseable"
    _b3_assert_refused(ledger, entry, handle["run_id"], tmp_path)
    ledger.store.close()

    # (b) 不符:发射载荷 record_id 不属于 refs(悬空未引用载荷)
    def _unbound(kw: dict) -> dict:
        em = dict(kw["record_equation_provenance"])
        em["record_id"] = "analog-supply:tpl-elsewhere"
        kw["record_equation_provenance"] = em
        return kw

    handle = _b3_first_write(monkeypatch, tmp_path,
                             "c-supply-b3-unbound", _unbound)
    ledger, entry = _b3_recover_direct(tmp_path, handle["run_id"])
    assert entry["disposition"]["kind"] == \
        "bundle_record_equation_ref_unbound"
    _b3_assert_refused(ledger, entry, handle["run_id"], tmp_path)
    ledger.store.close()

    # (c) 不符:refs 多一条无覆盖悬空引用(载荷只覆盖本 ref)
    def _extra_ref(kw: dict) -> dict:
        hyp = json.loads(json.dumps(kw["hypothesis_dict"]))
        hyp["provenance_refs"] = [str(r) for r in hyp["provenance_refs"]] \
            + ["analog-supply:tpl-second-missing"]
        kw["hypothesis_dict"] = hyp
        return kw

    handle = _b3_first_write(monkeypatch, tmp_path,
                             "c-supply-b3-uncovered", _extra_ref)
    ledger, entry = _b3_recover_direct(tmp_path, handle["run_id"])
    assert entry["disposition"]["kind"] == \
        "bundle_record_equation_refs_uncovered"
    _b3_assert_refused(ledger, entry, handle["run_id"], tmp_path)
    ledger.store.close()

    # (d) 损坏:假设载荷形状非法(非 dict/null)⇒ 结构化拒(不抛原始
    # AttributeError 中断恢复;零事件/零提交)
    def _bad_hyp(kw: dict) -> dict:
        kw["hypothesis_dict"] = ["broken"]
        return kw

    handle = _b3_first_write(monkeypatch, tmp_path,
                             "c-supply-b3-badhyp", _bad_hyp)
    ledger, entry = _b3_recover_direct(tmp_path, handle["run_id"])
    assert entry["disposition"]["kind"] == \
        "bundle_hypothesis_dict_invalid"
    _b3_assert_refused(ledger, entry, handle["run_id"], tmp_path)
    ledger.store.close()


def test_b3_payload_backstop_keeps_legit_paths_green(monkeypatch,
                                                     tmp_path) -> None:
    """追修正控(不误拒):公开接口**首写带完整载荷**(内容可解析 +
    refs 全绑定 + 覆盖完整)⇒ 恢复核验发射后照常提交,链闭合 ——
    载荷内容兜底只拦坏形态(缺/坏/不符),不拦合法形态;无 refs 的
    非 C bundle 零调用零变化由 S3A 族既有 B3 恢复测与全量覆盖。"""
    handle = _b3_first_write(monkeypatch, tmp_path,
                             "c-supply-b3-legit", lambda kw: kw)
    _path, bundle = _b3_bundle_dict(tmp_path, handle["run_id"])
    emission = bundle["payload"]["record_equation_provenance"]
    assert emission["record_id"] == _B3_REF
    ledger, entry = _b3_recover_direct(tmp_path, handle["run_id"])
    assert str(entry["disposition"]).startswith(
        "consumed_same_output_attempt")
    assert _b3_counts(ledger.store, handle["run_id"]) == {"events": 1,
                                                          "commits": 1}
    row = ledger.store.get_provenance(_B3_REF)
    assert row is not None and row["record_equation"]["reactants"], \
        "合法载荷恢复照常发射,声明链闭合"
    ledger.store.close()
