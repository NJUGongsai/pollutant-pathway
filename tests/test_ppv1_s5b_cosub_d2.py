"""PPV1 S5b 共底物参与物语义 D2 编译实现轮测试族
(S5b-corpus-retrieval-3 / s5b-recorded-source-3 / s5b-pool-policy-5)。

权威链:设计书 S5B_COSUBSTRATE_PARTICIPANT_SEMANTICS_DESIGN_2026-10-10.md
(方案 a + §五 原子三分类守门 + §五.3 union gate 扩展 + §12 T-1~T-5
主会话默认档)+ mimo r32 回应 16 条修改建议(NC-8..12/PC-4/5 控件
矩阵、R32-CS3-3 事件级不变量、R32-CS3-2 键空间同源)+ r31 措辞护栏。

控件矩阵(设计 §五.4 + r32 增补):
- NC-1 键合融合 LR/RL(CCO.CC→CCOCC):保守拒 + 拒因标签迁移;
- NC-2 键合融合配平增强(CCO.C=C=O→CCOC(C)=O):同根拒(配平
  不可自救);
- NC-3 add_atom 伪装机器断言(规格注入 add_atom ⇒ 守门拒);
- NC-4 拷贝身份 ≠ 记录产物组分(篡改 SMILES)⇒ declared_copy_mismatch;
- NC-5 不可归属原子形态 ⇒ 保守拒 + mapping_fallback 分列;
- NC-6 共底物 SMILES 不可解析 ⇒ cosubstrate_unparseable(声明保留);
- NC-7 从被拒条目 detail 重建 spec ⇒ 许可边界句在(R31-8);
- NC-8 可执行子集为空 ⇒ 结构化拒(防御分支;公共枚举下不可达,
  映射注入验证拒因名——A 的像必落于 A-可溯组分);
- NC-9 拷贝注入 expectation ⇒ 拒;
- NC-10 事件级端到端不变量(B 与拷贝同丢的退化 spec ⇒ prepare 拒);
- NC-11 拷贝身份 cn 派生(立体异构)⇒ declared_copy_mismatch(拷贝
  只认 strict);
- NC-12 批级熔断:本通道事件 matched_strict 恒 == 0(结构性不变量,
  出数即红;e2e 合成批断言);
- PC-1 辅因子对型(CCO.c1ccncc1→CC=O+C1CCNCC1):编译成功 + 参与
  物形态 + 事件 partial(断言具体桶);元素账 unknown 非已配平
  (该例按氢计不配平:乙醇→乙醛释 2H、吡啶→哌啶需 6H,差 4H;
  R32-CS1 风险 3 披露);
- PC-2 整串氧化/whole 多组分/EAWAG 水解:零回退(判分面与 EAWAG
  gate 行为等价;PC-2 全量行为由 wv41 既有族保持);
- PC-3 池侧同签名合并(拷贝入净反应签名;不双占槽);
- PC-4 旁观已声明共底物(零拷贝形态;r31 R31-2 登记形态正解落点);
- PC-5 多共底物记录(A+B1+B2→P+copy1+copy2,两个 B 全声明)。

本文件零网络、零真实模型(scripted 桩);合成分子与真实 298 金标
零重叠(乙醇级小分子;W2 夹具纪律)。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pathway_v43.config import resolve_config  # noqa: E402
from pathway_v43.pollutant.production import (  # noqa: E402
    ProductionContractError,
    prepare_hypothesis,
)
from pathway_v43.pollutant.real_model import (  # noqa: E402
    ScriptedRealModelAdapter,
)
from pathway_v43.pollutant.recorded_source import (  # noqa: E402
    CORPUS_RETRIEVAL_VERSION,
    RECORDED_SOURCE_VERSION,
    compile_recorded_reaction,
    find_corpus_recorded_exact,
    reset_corpus_cache,
    reset_library_cache,
)
from pathway_v43.pollutant.runflow import start_ppv1_run  # noqa: E402
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    S5B_POOL_POLICY_VERSION,
    build_question_batch,
    default_pool_provider,
)
from pathway_v43.pollutant.s5b_compiler import (  # noqa: E402
    net_reaction_signature,
)


def _rhea_row(rid, mid, direction, donor_a, comps, product_b, pcomps,
              *, ec=None, prov="f" * 64, extra=None) -> dict:
    row = {
        "atom_mapping": None, "direction": direction,
        "donor_A_smiles": donor_a, "donor_components": comps,
        "ec": ec, "mapping_status": "absent", "master_id": mid,
        "parse_note": "rxn-parsed", "product_B_smiles": product_b,
        "product_components": pcomps, "provenance_sha256": prov,
        "reaction_smiles": f"{donor_a}>>{product_b}",
        "record_id": rid, "source_id": rid, "source_type": "rhea",
    }
    row.update(extra or {})
    return row


class _CorpusEngine:
    """D2 测试桩:identity_block + 空 lookup(corpus 直通独立驱动)。

    合成 corpus 行与真实 298 金标零重叠(W2 纪律)。"""

    def __init__(self, tmp: Path, corpus_rows: list[dict]):
        import tempfile

        self._tmpdir = Path(tempfile.mkdtemp(
            prefix="d2-synth-", dir=str(tmp)))
        corpus = self._tmpdir / "corpus_v1.jsonl"
        corpus.write_text(
            "\n".join(json.dumps(r) for r in corpus_rows) + "\n",
            encoding="utf-8")
        lib = self._tmpdir / "library_full.jsonl"
        lib.write_text("\n", encoding="utf-8")
        self.identity_block = {
            "library_path": str(lib),
            "library_sha256": hashlib.sha256(
                lib.read_bytes()).hexdigest(),
            "corpus_v1_path": str(corpus),
            "corpus_v1_sha256": hashlib.sha256(
                corpus.read_bytes()).hexdigest(),
        }

    def expand_raw(self, smiles: str, case_id: str = "c") -> dict:
        return {"lookup": [], "pred_edges": [], "merged_edges": [],
                "n_pred_candidates": 0, "n_lookup": 0,
                "budget_cut": False, "pool_capped": False,
                "canonical_smiles": smiles}


@pytest.fixture(autouse=True)
def _clean_caches():
    reset_library_cache()
    reset_corpus_cache()
    yield
    reset_library_cache()
    reset_corpus_cache()


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

_SUB = "CCO"                       # 乙醇(组分级底物)
_SUB_PENTANAMIDE = "CCOC(C)=O"     # 乙酸乙酯(水解 component 面)


# ================================================================ 版本与登记

def test_d2_versions_registered() -> None:
    """D2 版本登记(既有身份规则:许可/池成员/gate 扩展三处升版;
    EAWAG/整串语义键保持)。"""
    assert CORPUS_RETRIEVAL_VERSION == "s5b-corpus-retrieval-3"
    assert RECORDED_SOURCE_VERSION == "s5b-recorded-source-3"
    assert S5B_POOL_POLICY_VERSION == "s5b-pool-policy-5"


# ================================================================ 负控族(NC)

def _find_component(tmp_path, rows, substrate=_SUB):
    engine = _CorpusEngine(tmp_path, rows)
    out = find_corpus_recorded_exact(
        substrate_smiles=substrate, engine=engine)
    comp = [c for c in out["candidates"]
            if c["donor_match_kind"] == "component"]
    return engine, out, comp


def test_d2_nc1_bonded_fusion_lr_rl_rejected(tmp_path) -> None:
    """NC-1:键合融合同根 LR/RL 两方向 —— 保守拒(零 spec/零 event),
    拒因 = cosubstrate_bonded_contribution_unsupported(从 corpus-
    retrieval-2 许可拒迁移;拒因标签变化如实分类);四轴子标签在
    (R32-CS2-3);理由两层分写(物理层:执行图不含 B;规则层:R2-2
    无条件禁令,'伪装'仅指未声明形态——r31 R31-1 护栏)。"""
    rows = [
        _rhea_row("rhea:91001", "91000", "LR", "CCO.CC",
                  ["CCO", "CC"], "CCOCC", ["CCOCC"]),
        _rhea_row("rhea:91002", "91000", "RL", "CCO.CC",
                  ["CCO", "CC"], "CCOCC", ["CCOCC"]),
    ]
    engine, out, comp = _find_component(tmp_path, rows)
    assert {c["record_id"] for c in comp} == {"rhea:91001",
                                              "rhea:91002"}
    for c in comp:
        assert c["compile"] is None
        assert c["compile_status"] == "unsupported"
        assert c["compile_reason"] == \
            "cosubstrate_bonded_contribution_unsupported"
        d = c["compile_detail"]
        # 拒因可追溯:源行/方向/共底物声明/记录产物全保留(NC-7 句)
        assert d["record_key"].startswith(c["record_id"] + "@L")
        assert d["donor_A_smiles"] == "CCO.CC"
        assert [x["smiles"] for x in d["co_substrates"]] == ["CC"]
        assert d["products"] == ["CCOCC"]
        assert "REBUILDING a usable pool spec" in d["permission_note"]
        # 四轴子标签(R32-CS2-3):bonded_kind/balance/b_class/
        # b_identity_in_products
        axes = d["bonded_kind_axes"]
        assert axes["per_component"], axes
        for entry in axes["per_component"]:
            assert entry["bonded_kind"] in (
                "single_atom_insertion", "group_transfer",
                "skeleton_merge")
        assert axes["record_balance_status"]
        assert axes["b_class"] == "organic_like"
        assert isinstance(axes["b_identity_in_products"], bool)
        # 理由两层分写(R32-CS2-1)
        assert "execution graph = render(substrate)" in d["note"]
        assert "unconditionally" in d["note"]
    # 池层:守门拒 ⇒ 零池槽
    provider = default_pool_provider(None, engine=engine)
    assert provider(_SUB) == []
    diag = provider.last_diagnostics
    assert diag["compile_failure_histogram"][
        "cosubstrate_bonded_contribution_unsupported"] == 2


def test_d2_nc2_bonded_fusion_balanced_rejected(tmp_path) -> None:
    """NC-2:键合融合配平增强(CCO.C=C=O→CCOC(C)=O;Codex §4.2 原
    案)——配平不可自救,同根保守拒。"""
    rows = [
        _rhea_row("rhea:91006", "91004", "LR", "CCO.C=C=O",
                  ["CCO", "C=C=O"], "CCOC(C)=O", ["CCOC(C)=O"]),
    ]
    engine, out, comp = _find_component(tmp_path, rows)
    assert len(comp) == 1
    assert comp[0]["compile"] is None
    assert comp[0]["compile_reason"] == \
        "cosubstrate_bonded_contribution_unsupported"
    axes = comp[0]["compile_detail"]["bonded_kind_axes"]
    assert axes["record_balance_status"].startswith("balanced")


def test_d2_nc3_add_atom_regression_guard(tmp_path, monkeypatch) -> None:
    """NC-3(设计 §五.2.5):component 候选产出的 spec 其 edits 不得含
    add_atom——规则 2/3 已结构性排除,该断言防未来实现漂移。注入
    add_atom(公共编译结果被篡改)⇒ 结构化守门拒,零 spec。"""
    from pathway_v43.pollutant import recorded_source as rs

    rows = [
        _rhea_row("rhea:91003", "91001", "LR", "CCO.c1ccncc1",
                  ["CCO", "c1ccncc1"], "CC=O.C1CCNCC1",
                  ["CC=O", "C1CCNCC1"]),
    ]
    real_compile = rs.compile_recorded_reaction

    def _injected(**kwargs):
        out = real_compile(**kwargs)
        if out.get("status") == "compiled":
            spec = dict(out["spec"])
            spec["edits"] = list(spec["edits"]) + [{
                "op": "add_atom", "element": "C",
                "new_atom_id": "SN_C_9", "atom1": "S_C_1"}]
            out = dict(out)
            out["spec"] = spec
        return out

    monkeypatch.setattr(rs, "compile_recorded_reaction", _injected)
    engine, out, comp = _find_component(tmp_path, rows)
    assert len(comp) == 1
    assert comp[0]["compile"] is None
    assert comp[0]["compile_reason"] == \
        "cosubstrate_executable_add_atom_regression_guard"
    assert "add_atom" in comp[0]["compile_detail"]["note"]


def test_d2_nc4_declared_copy_mismatch_tampered() -> None:
    """NC-4:拷贝组分身份 ≠ 记录产物组分(篡改 SMILES)⇒
    declared_copy_mismatch(拷贝只认 strict identity;多重集包含
    核对)。"""
    out = compile_recorded_reaction(
        substrate_smiles="CCO", donor_smiles="CCO",
        products=["CC=O"], record_id="d2-nc4",
        declared_copies=["CCOCC"],
        record_products=["CC=O", "CCC"])
    assert out["status"] == "unsupported"
    assert out["reason"] == "declared_copy_mismatch"
    assert out["detail"]["record_id"] == "d2-nc4"


def test_d2_nc5_unattributable_rejected(tmp_path) -> None:
    """NC-5:不可归属原子形态(产物含 A∪B 不存在的元素)⇒ 保守拒
    (T-3 主会话默认档子选项 i;mimo r32 R32-CS3-1 已裁);拒因子类
    mapping_fallback 分列键在(两类计数分列)。"""
    rows = [
        # 产物 CS:硫既不在 A(CCO)也不在 B(CC)⇒ 不可归属强形态
        _rhea_row("rhea:91005", "91003", "LR", "CCO.CC",
                  ["CCO", "CC"], "CC=O.CS", ["CC=O", "CS"]),
    ]
    engine, out, comp = _find_component(tmp_path, rows)
    assert len(comp) == 1
    assert comp[0]["compile"] is None
    assert comp[0]["compile_reason"] == \
        "cosubstrate_atom_source_unattributable"
    d = comp[0]["compile_detail"]
    assert d["unattributable_products"] == ["CS"]
    assert d["mapping_fallback"] is False
    hist = out["diagnostics"]["compile_failure_histogram"]
    assert hist["cosubstrate_atom_source_unattributable"] == 1
    # R32-CS3-1:分列键(bond-diff 回退伪影 vs 源记录真缺)
    assert hist["cosubstrate_unattributable_mapping_fallback_false"] \
        == 1


def test_d2_nc6_cosubstrate_unparseable(tmp_path) -> None:
    """NC-6:共底物 SMILES 不可解析 ⇒ cosubstrate_unparseable 结构化
    拒,detail 保留声明(不猜不清洗)。"""
    rows = [
        _rhea_row("rhea:91007", "91005", "LR", "CCO.not-a-smiles",
                  ["CCO", "not-a-smiles"], "CC=O.CCO",
                  ["CC=O", "CCO"]),
    ]
    engine, out, comp = _find_component(tmp_path, rows)
    assert len(comp) == 1
    assert comp[0]["compile"] is None
    assert comp[0]["compile_reason"] == "cosubstrate_unparseable"
    assert comp[0]["compile_detail"]["co_substrate_smiles"] == \
        "not-a-smiles"
    # 候选级共底物声明保留(不静默丢弃)
    assert [x["smiles"] for x in comp[0]["co_substrates"]] == \
        ["not-a-smiles"]


def test_d2_nc8_no_executable_subset_defensive(tmp_path,
                                               monkeypatch) -> None:
    """NC-8(R32-CS2-4):可执行子集为空 ⇒ 结构化拒
    cosubstrate_no_executable_product_subset(不得产空 expectation
    事件、不得把整产物集降级为拷贝绕行)。

    公共枚举下该分支不可达(A 的像必落于某产物组分,而干净二分要求
    该组分为纯 A-可溯 ⇒ executable 非空)——本用例以映射注入钉死
    拒因名与机器分支存在(防未来实现漂移)。"""
    from pathway_v43.pollutant import recorded_source as rs

    rows = [
        _rhea_row("rhea:91008", "91006", "LR", "CCO.CC",
                  ["CCO", "CC"], "CC", ["CC"]),
    ]
    monkeypatch.setattr(
        rs, "infer_reaction_mapping",
        lambda donor, products: [{
            # 全部 donor 原子离去、产物全为 new 原子的自洽映射
            # (公共枚举不可达形态;防漂移注入)
            "donor_to_union": {},
            "new_union": [0, 1],
            "removed_donor": list(range(
                rs.Chem.MolFromSmiles(donor).GetNumAtoms())),
            "truncated": False}])
    engine, out, comp = _find_component(tmp_path, rows)
    assert len(comp) == 1
    assert comp[0]["compile"] is None
    assert comp[0]["compile_reason"] == \
        "cosubstrate_no_executable_product_subset"


def test_d2_nc9_copy_injected_into_expectation(tmp_path) -> None:
    """NC-9:拷贝组分串塞进 expectation.target_smiles ⇒ 契约拒
    (拷贝组分不经执行通道;设计 §四.3.4 禁止事项;NC-3 只覆盖
    add_atom 通道,本控件覆盖 expectation 通道)。"""
    rows = [
        _rhea_row("rhea:91003", "91001", "LR", "CCO.c1ccncc1",
                  ["CCO", "c1ccncc1"], "CC=O.C1CCNCC1",
                  ["CC=O", "C1CCNCC1"]),
    ]
    engine, out, comp = _find_component(tmp_path, rows)
    spec = comp[0]["compile"]
    assert spec is not None
    tampered = json.loads(json.dumps(spec))
    copy_smiles = tampered["declared_copy_components"][0]["smiles"]
    tampered["expectation"]["target_smiles"] = \
        f"{tampered['expectation']['target_smiles']}.{copy_smiles}"
    substrate_state = None
    from pathway_v43.pollutant.production import (
        build_product_state,
    )
    substrate_state = build_product_state(
        "CCO", source_refs=[{"record": "d2-nc9"}])
    with pytest.raises(ProductionContractError) as exc_info:
        prepare_hypothesis(
            tampered, parent_path_id="pp-d2-nc9",
            substrate_state=substrate_state)
    assert exc_info.value.detail["kind"] == \
        "cosubstrate_copy_in_expectation"


def test_d2_nc10_event_invariant_degenerate_spec_rejected(tmp_path) -> None:
    """NC-10(r32 R32-CS3-3 必加):B 与拷贝同丢的退化 spec(事件退
    化为 A→P 可 exact 的 R2-2 禁形态)⇒ prepare 拒(spec 层 gate
    通过不替代事件层核对;add_atom 负控对零产物贡献 B 空转,本不
    变量是唯一事件层闸)。"""
    rows = [
        _rhea_row("rhea:91003", "91001", "LR", "CCO.c1ccncc1",
                  ["CCO", "c1ccncc1"], "CC=O.C1CCNCC1",
                  ["CC=O", "C1CCNCC1"]),
    ]
    engine, out, comp = _find_component(tmp_path, rows)
    spec = comp[0]["compile"]
    assert spec is not None
    from pathway_v43.pollutant.production import build_product_state

    # 退化形态 1:participants 丢掉 B(reactant cosubstrate)
    degenerate = json.loads(json.dumps(spec))
    degenerate["participants"] = [
        p for p in degenerate["participants"]
        if p["role"] != "cosubstrate"]
    substrate_state = build_product_state(
        "CCO", source_refs=[{"record": "d2-nc10"}])
    with pytest.raises(ProductionContractError) as exc_info:
        prepare_hypothesis(
            degenerate, parent_path_id="pp-d2-nc10",
            substrate_state=substrate_state)
    assert exc_info.value.detail["kind"] == \
        "cosubstrate_event_invariant_violation"
    assert exc_info.value.detail["axis"] == "declared_cosubstrates_subset"

    # 退化形态 2:participants 丢掉拷贝组分(产物多重集不齐)
    degenerate2 = json.loads(json.dumps(spec))
    degenerate2["participants"] = [
        p for p in degenerate2["participants"]
        if p["state_ref"] not in
        {e["state_ref"] for e in spec["declared_copy_components"]}]
    degenerate2["declared_copy_components"] = []
    degenerate2["cosubstrate_event_contract"]["copy_state_refs"] = []
    with pytest.raises(ProductionContractError) as exc_info2:
        prepare_hypothesis(
            degenerate2, parent_path_id="pp-d2-nc10b",
            substrate_state=substrate_state)
    assert exc_info2.value.detail["kind"] == \
        "cosubstrate_event_invariant_violation"


def test_d2_nc11_copy_identity_cn_derived_rejected() -> None:
    """NC-11:拷贝身份用 cn 派生(电荷归一/立体盲)⇒ 必须
    declared_copy_mismatch 拒——拷贝只认 strict。立体异构拷贝(CN 同
    而 strict 异)对记录产物组分。"""
    record_product = "C[C@H](N)O"
    copy_claim = "C[C@@H](N)O"
    out = compile_recorded_reaction(
        substrate_smiles="CCO", donor_smiles="CCO",
        products=["CC=O"], record_id="d2-nc11",
        declared_copies=[copy_claim],
        record_products=["CC=O", record_product])
    assert out["status"] == "unsupported"
    assert out["reason"] == "declared_copy_mismatch"


def test_d2_nc12_union_gate_missing_copy_rejected() -> None:
    """union gate 负控:拷贝缺失(执行 ∪ 拷贝 ≠ 记录全量)⇒
    product_set_mismatch(fail-closed;忘传拷贝的方向是安全拒)。"""
    out = compile_recorded_reaction(
        substrate_smiles="CCO", donor_smiles="CCO",
        products=["CC=O"], record_id="d2-nc12",
        declared_copies=[],
        record_products=["CC=O", "C1CCNCC1"])
    assert out["status"] == "unsupported"
    assert out["reason"] == "product_set_mismatch"
    assert out["detail"]["recorded_components"]


def test_d2_completion_license_unchanged_machine_guard() -> None:
    """R32-CS4-3 机器锚(D-T1′-2 补全许可不延伸):COMPLETION_
    LICENSED_IDENTITIES 只允许 H₂/[H] 氢当量——任何含碳/辅因子身份
    入列 = 判据三许可边界变更(本轮零实施零扩列,机器断言钉死)。"""
    from pathway_v43.pollutant.audit import COMPLETION_LICENSED_IDENTITIES

    licensed = [str(x) for x in COMPLETION_LICENSED_IDENTITIES]
    assert licensed, "许可集意外为空(应含 H2/[H] 氢当量)"
    from rdkit import Chem

    for smiles in licensed:
        mol = Chem.MolFromSmiles(smiles)
        assert mol is not None, smiles
        assert not any(a.GetSymbol() == "C" for a in mol.GetAtoms()), \
            f"含碳身份进入补全许可集(判据三边界变更):{smiles}"


# ================================================================ 正控族(PC)

def test_d2_pc1_cofactor_pair_compiles_partial_supply(tmp_path) -> None:
    """PC-1(本设计最重要正控):辅因子对型(底物 CCO,共底物吡啶,
    产物乙醛+哌啶)——编译成功 + 事件参与物 = {CCO(底物), 吡啶
    (cosubstrate,reactant)} / {乙醛(principal), 哌啶(copy,coproduct)}
    + 中心 unknown + 冻结匹配 ⇒ matched_participant_coverage_partial
    (断言具体桶,不断言 strict)。**解锁的是诚实 partial,不是
    strict**;该例按氢计不配平(乙醇→乙醛释 2H、吡啶→哌啶需 6H,
    差 4H)——元素账 unknown 非已配平(R32-CS1 风险 3 注记)。"""
    rows = [
        _rhea_row("rhea:91003", "91001", "LR", "CCO.c1ccncc1",
                  ["CCO", "c1ccncc1"], "CC=O.C1CCNCC1",
                  ["CC=O", "C1CCNCC1"]),
    ]
    engine, out, comp = _find_component(tmp_path, rows)
    assert len(comp) == 1
    cand = comp[0]
    assert cand["compile"] is not None, cand["compile_reason"]
    spec = cand["compile"]
    # 可执行子集 = 乙醛;拷贝 = 哌啶(不进执行期望)
    assert spec["product_smiles"] == "CC=O"
    assert spec["coproducts"] == []
    assert spec["expectation"]["target_smiles"] == "CC=O"
    # add_atom 伪装负控:可执行子集原子全部 A-可溯 ⇒ 零 add_atom
    assert not any(e.get("op") == "add_atom" for e in spec["edits"])
    # 参与物形态(协议层零新发明:role 复用既有枚举,系数全 unknown)
    sides = [(p["side"], p["role"], p["coefficient"],
              p["coefficient_status"])
             for p in spec["participants"]]
    assert sides == [
        ("reactant", "primary_substrate", None, "unknown"),
        ("reactant", "cosubstrate", None, "unknown"),
        ("product", "principal_product", None, "unknown"),
        ("product", "coproduct", None, "unknown")]
    assert spec["participant_list_status"] == "declared_complete"
    # 拷贝组分机读披露(R32-CS1-1:身份轴可核/生成轴未执行)
    copy = spec["declared_copy_components"][0]
    assert copy["smiles"] == "C1CCNCC1"
    assert copy["component_source"] == "record_declared_copy"
    assert copy["record_key"] == cand["record_key"]
    assert copy["execution_status"] == "declared_not_executed"
    assert copy["provenance_sha256"] == "f" * 64
    # B 状态装配
    b = spec["co_substrate_states"][0]
    assert b["smiles"] == "c1ccncc1"
    assert b["source_ref"] == cand["record_key"]
    # 事件契约(NC-10 记录侧输入)
    contract = spec["cosubstrate_event_contract"]
    assert contract["record_products"] == ["CC=O", "C1CCNCC1"]
    assert [x["smiles"] for x in contract["co_substrates"]] == \
        ["c1ccncc1"]
    # union gate 机读信息(R32-CS3-2 键空间一致性披露在)
    info = spec["compile"]["declared_copies"]
    assert info["n_declared_copies"] == 1
    assert info["execution_status"] == "declared_not_executed"
    assert info["key_space_consistency"]["n_components"] == 1
    assert info["key_space_consistency"]["n_divergent"] == 0
    assert "NOT an element/charge balance" in \
        info["verified_product_set_scope"] or "非元素" in \
        info["verified_product_set_scope"]
    # EAWAG 面(引擎 lookup 空)不受影响;池层供给成立
    provider = default_pool_provider(None, engine=engine)
    pool = provider(_SUB)
    assert [s["key"] for s in pool] == [spec["key"]]
    diag = provider.last_diagnostics
    assert diag["n_cosubstrate_declared_specs"] == 1
    assert diag["cosubstrate_pool_labels"]["count_unit"].startswith(
        "pool_specs")


def test_d2_pc4_bystander_cosubstrate_zero_copy(tmp_path) -> None:
    """PC-4:旁观已声明共底物(B 在反应物侧声明、产物集不含任何 B
    原子、全部产物 A-可溯)⇒ 编译成功、零拷贝、事件含 B、partial
    (r31 R31-2 登记形态在本设计下的正解落点)。"""
    rows = [
        # A + 乙烷 → 乙醛(乙烷旁观:声明但对产物零贡献)
        _rhea_row("rhea:91004", "91002", "LR", "CCO.CC",
                  ["CCO", "CC"], "CC=O", ["CC=O"]),
    ]
    engine, out, comp = _find_component(tmp_path, rows)
    assert len(comp) == 1
    spec = comp[0]["compile"]
    assert spec is not None, comp[0]["compile_reason"]
    assert spec["declared_copy_components"] == []
    roles = [(p["side"], p["role"]) for p in spec["participants"]]
    assert roles == [
        ("reactant", "primary_substrate"),
        ("reactant", "cosubstrate"),
        ("product", "principal_product")]
    # 零拷贝形态:union gate = 执行 == 记录(B 未出现在产物侧)
    assert spec["compile"]["declared_copies"]["n_declared_copies"] == 0
    # 池层供给 + 事件级断言(e2e)
    provider = default_pool_provider(None, engine=engine)
    pool = provider(_SUB)
    assert pool and pool[0]["key"] == spec["key"]


def test_d2_pc5_multiple_cosubstrates_all_declared(tmp_path) -> None:
    """PC-5:多共底物记录(A+B1+B2 → P+copy1+copy2):两个 B 全声明、
    两个拷贝全带来源字段——防实现只装配首个 co_substrate。"""
    rows = [
        _rhea_row("rhea:91009", "91007", "LR",
                  "CCO.c1ccncc1.O",
                  ["CCO", "c1ccncc1", "O"],
                  "CC=O.C1CCNCC1.O",
                  ["CC=O", "C1CCNCC1", "O"]),
    ]
    engine, out, comp = _find_component(tmp_path, rows)
    assert len(comp) == 1
    spec = comp[0]["compile"]
    assert spec is not None, comp[0]["compile_reason"]
    # 两个 B 全部进 reactant 侧 cosubstrate 参与物
    b_smiles = [e["smiles"] for e in spec["co_substrate_states"]]
    assert b_smiles == ["c1ccncc1", "O"]
    cosub_roles = [p["role"] for p in spec["participants"]
                   if p["side"] == "reactant" and p["role"] ==
                   "cosubstrate"]
    assert len(cosub_roles) == 2
    # 两个拷贝全带来源字段
    copies = spec["declared_copy_components"]
    assert [e["smiles"] for e in copies] == ["C1CCNCC1", "O"]
    assert all(e["component_source"] == "record_declared_copy"
               and e["execution_status"] == "declared_not_executed"
               for e in copies)
    assert spec["compile"]["declared_copies"]["n_declared_copies"] == 2


def test_d2_pc3_pool_signature_merges_copy_channel(tmp_path) -> None:
    """PC-3:池侧同签名合并(拷贝型 spec 净反应签名含共底物贡献 ⇒
    与同净反应记录合并留痕不双占槽;含拷贝签名使"乙醛+副产物"与
    "乙醛"两条净反应**不**误并)。"""
    rows = [
        # 同净反应的两条独立记录(不同 master):拷贝型 component
        _rhea_row("rhea:91011", "91008", "LR", "CCO.c1ccncc1",
                  ["CCO", "c1ccncc1"], "CC=O.C1CCNCC1",
                  ["CC=O", "C1CCNCC1"]),
        _rhea_row("rhea:91012", "91009", "LR", "CCO.c1ccncc1",
                  ["CCO", "c1ccncc1"], "CC=O.C1CCNCC1",
                  ["CC=O", "C1CCNCC1"]),
        # 副产物不同(甲烷 vs 无):净反应签名须不同(不误并)
        _rhea_row("rhea:91013", "91010", "LR", "CCO.C",
                  ["CCO", "C"], "CC=O.C", ["CC=O", "C"]),
    ]
    engine = _CorpusEngine(tmp_path, rows)
    provider = default_pool_provider(None, engine=engine)
    pool = provider(_SUB)
    keys = [s["key"] for s in pool]
    # 91011/91012 同净反应(乙醛+哌啶)⇒ 合并单槽 + provenance 留痕;
    # 91013(乙醛+甲烷)不同净反应 ⇒ 独立槽
    assert len(pool) == 2, keys
    merged_spec = next(s for s in pool
                       if s["key"] == "rec-rhea:91011@L1")
    assert "rec-rhea:91012@L2" in merged_spec["compile"].get(
        "merged_source_keys", [])
    # 签名扩展:拷贝组分进净反应签名(无拷贝字段 spec 逐字节不变)
    sig_with = net_reaction_signature(merged_spec)
    assert len(sig_with) == 2  # (CC=O, piperidine)
    plain = {"product_smiles": "CC=O", "coproducts": []}
    assert net_reaction_signature(plain) == ("CC=O",)


def test_d2_pc2_whole_and_eawag_zero_regression(tmp_path) -> None:
    """PC-2(零回退面):整串氧化/whole 多组分照旧编译;compile_
    recorded_reaction 缺省路径(declared_copies=None)行为字节等价
    ——spec["compile"] 无 declared_copies/record_products_full 新键,
    gate 输出形状与历史一致(EAWAG 水解 add_atom 能力由 wv41 既有
    正控保持,此处钉缺省键空间)。"""
    rows = [
        _rhea_row("rhea:91021", "91020", "LR", "CCO",
                  ["CCO"], "CC=O", ["CC=O"]),
        _rhea_row("rhea:91022", "91021", "LR", "CCO.CC",
                  ["CCO", "CC"], "CCOCC", ["CCOCC"]),
    ]
    engine = _CorpusEngine(tmp_path, rows)
    out = find_corpus_recorded_exact(
        substrate_smiles="CCO", engine=engine)
    whole = [c for c in out["candidates"]
             if c["record_id"] == "rhea:91021"]
    assert whole and whole[0]["compile"] is not None
    spec = whole[0]["compile"]
    assert "declared_copies" not in spec["compile"]
    assert "record_products_full" not in spec["compile"]
    assert spec["compile"]["verified_product_set"] is True
    # whole 多组分(底物=donor 全串)照旧
    out_multi = find_corpus_recorded_exact(
        substrate_smiles="CCO.CC", engine=engine)
    multi = {c["record_id"]: c for c in out_multi["candidates"]}
    assert multi["rhea:91022"]["compile"] is not None
    assert multi["rhea:91022"]["donor_match_kind"] == "whole"
    # 缺省路径直调(无 declared_copies)与历史行为一致:无新键
    out_direct = compile_recorded_reaction(
        substrate_smiles="CCO", donor_smiles="CCO",
        products=["CC=O"], record_id="d2-pc2")
    assert out_direct["status"] == "compiled"
    assert "declared_copies" not in out_direct["spec"]["compile"]


# ================================================================ e2e(NC-10/NC-12)

def test_d2_e2e_cosubstrate_event_partial_and_batch_fuse(tmp_path) -> None:
    """端到端(零真实模型):builder(corpus 拷贝型接线池)→ runflow
    decide(scripted first_pool)→ 公共链执行 → 事件提交 → 判分。

    断言(设计 §一.4 + NC-12 批级熔断):
    - 事件参与物(原生 sqlite):反应物 = {底物, 共底物},产物 =
      {可执行主产物, 声明拷贝组分}(拷贝组分 = 声明参与物,来源在
      provenance 层);
    - NC-10 不变量通过(事件提交本身即证明;production_report 携带
      共底物披露);
    - **NC-12 批级熔断:本通道 matched_strict 恒 == 0**;边匹配落
      matched_participant_coverage_partial(具体桶),非 strict、非
      unmatched;
    - 生产报告携带 cosubstrate_disclosure(拷贝组分机读披露 +
      expectation 覆盖 refs + coproduct_participants 字段说明)。"""
    rows = [
        _rhea_row("rhea:91003", "91001", "LR", "CCO.c1ccncc1",
                  ["CCO", "c1ccncc1"], "CC=O.C1CCNCC1",
                  ["CC=O", "C1CCNCC1"]),
    ]
    engine = _CorpusEngine(tmp_path, rows)
    provider = default_pool_provider(None, engine=engine)
    questions = tmp_path / "questions.jsonl"
    questions.write_text(json.dumps({
        "qid": "d2-syn-1", "substrate_smiles": "CCO",
        "products_smiles": ["CC=O"],
    }) + "\n", encoding="utf-8")
    manifest = build_question_batch(
        questions, tmp_path / "batch", batch_tag="d2-synth",
        pool_provider=provider, provider_kind="scripted",
        synthetic_review=True)
    entry = manifest["entries"][0]
    assert entry["pool_size"] == 1
    run_input = json.loads(
        (tmp_path / "batch" / "run_inputs" / "d2-syn-1.json"
         ).read_text(encoding="utf-8"))
    spec = run_input["plan"]["pools"]["CCO"][0]
    assert spec["cosubstrate_event_contract"]["record_products"] == \
        ["CC=O", "C1CCNCC1"]
    model = ScriptedRealModelAdapter(
        strategy="first_pool", model_id="d2-model")
    summary = start_ppv1_run(
        config=resolve_config(), runs_root=tmp_path / "runs",
        run_id=run_input["run_id"], smiles="CCO",
        plan=run_input["plan"], model=model,
        profile_policy=dict(
            _PROFILE, search_limits=dict(
                _PROFILE["search_limits"],
                max_real_model_requests=4)))
    assert summary["counts"]["events"] == 1
    run_id = run_input["run_id"]
    # ---- 事件参与物(原生事件表;不只断言 metadata) ----
    import sqlite3

    conn = sqlite3.connect(
        str(tmp_path / "runs" / run_id / "pollutant.sqlite"))
    conn.row_factory = sqlite3.Row
    events = [json.loads(r["payload"]) for r in conn.execute(
        "SELECT payload FROM events")]
    states = {str(r["state_id"]): json.loads(r["payload"])
              for r in conn.execute(
                  "SELECT state_id, payload FROM states")}
    conn.close()
    reactants: set = set()
    products: set = set()
    roles: set = set()
    for payload in events:
        for p in payload.get("participants") or []:
            state = states.get(str(p.get("state_ref") or "")) or {}
            roles.add((str(p.get("side")), str(p.get("role"))))
            if p.get("side") == "reactant":
                reactants.add(str(state.get("smiles_isomeric") or ""))
            else:
                products.add(str(state.get("smiles_isomeric") or ""))
    assert reactants == {"CCO", "c1ccncc1"}, reactants
    assert products == {"CC=O", "C1CCNCC1"}, products
    assert ("reactant", "cosubstrate") in roles
    assert ("product", "coproduct") in roles
    # ---- 判分:具体桶 partial + NC-12 批级熔断 ----
    from pathway_v43.pollutant import preregistration
    from pathway_v43.pollutant.evaluation import (
        evaluate_scientific,
        match_reference_edges,
        match_reference_nodes,
        native_export_reader_from_ledger,
    )
    from pathway_v43.pollutant.native_export import read_native_export
    from pathway_v43.pollutant.search import SearchLedger
    from pathway_v43.pollutant.store import PollutantPathwayStore
    from pathway_v43.storage.artifact_store import ArtifactStore

    runs_root = tmp_path / "runs"
    store = PollutantPathwayStore(
        runs_root / run_id / "pollutant.sqlite")
    ledger = SearchLedger(
        store, ArtifactStore(runs_root, run_id), run_id)
    digest = summary["native_export"]["export_digest"]
    payload = read_native_export(
        ledger, runs_root / run_id, digest)["payload"]
    graph = json.loads(
        (tmp_path / "batch" / "reference_graphs" /
         (entry["reference_graph_id"] + ".json")).read_text(
             encoding="utf-8"))
    node_matches = match_reference_nodes(graph, payload)
    edge_matches = match_reference_edges(graph, payload, node_matches)
    statuses = {e["match_status"] for e in edge_matches}
    # NC-12:本通道 matched_strict 恒 == 0(出数即红)
    assert "matched_strict" not in statuses, statuses
    # 具体桶:partial(不是 unmatched/structure_only)
    assert statuses == {"matched_participant_coverage_partial"}, statuses
    for r in edge_matches:
        for e in r["coverage_mismatch_events"]:
            assert e["participant_coverage"] == "superset"
    # ---- 生产报告披露(R32-CS1-1/CS5-2) ----
    report_paths = list(
        (runs_root / run_id).rglob("production_report*"))
    assert report_paths, "production_report artifact 缺席"
    disclosed = False
    for p in report_paths:
        text = p.read_text(encoding="utf-8")
        if "cosubstrate_disclosure" in text:
            disclosed = True
            assert "declared_not_executed" in text
            assert "expectation_covered_state_refs" in text
    assert disclosed, "共底物披露未随生产报告落盘"
    # 零 LLM 判分面(evaluate_scientific 走读)——sample 主口径行
    # 不在本断言范围(partial 不进 hit;NC-12 已在边级断言)
    _ = (evaluate_scientific, preregistration,
         native_export_reader_from_ledger)
