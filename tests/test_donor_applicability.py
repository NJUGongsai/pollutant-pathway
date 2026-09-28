"""供体适用性门禁(Phase C 任务书 §3/C1,验收 §6.1)。

夹具(tests/fixtures/applicability/)为人工审过的正例/负例/歧义例,
不从 298 金标反推;每条预期由本测试在真实代码上核对。核心断言:
- 变换提取确定性且不信任 qc_flags 声明(映射号重复/元素漂移留拒因);
- 全部对齐枚举(不取首个),对称等价合并、竞争位点弃权;
- 全供体优先于中心子图;多供体只选有资格者,竞争变换 ambiguous;
- 键级/氢/价态/电荷冲突均留具体拒因;真实资产模板作集成夹具并核对 SHA。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pathway_v43.domain.identity import cn_identity
from pathway_v43.services.donor_applicability import (
    APPLICABILITY_AMBIGUOUS,
    APPLICABILITY_APPLICABLE,
    APPLICABILITY_INAPPLICABLE,
    APPLICABILITY_UNAVAILABLE,
    ApplicabilityPolicy,
    assess_alignment,
    assess_donor,
    build_eligibility,
    extract_donor_transform,
    enumerate_alignments,
    evaluate_card,
    _aromatic_form,
    _kekulized,
)

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "applicability"
     / "donor_applicability_fixtures.json").read_text(encoding="utf-8"))

REPO_ROOT = Path(__file__).resolve().parents[1]


def _donor(d: dict) -> dict:
    return dict(d)


def _h_charge(mol):
    return ({a.GetIdx(): a.GetTotalNumHs() for a in mol.GetAtoms()},
            {a.GetIdx(): a.GetFormalCharge() for a in mol.GetAtoms()})


# ------------------------------------------------------------ 变换提取


def test_extract_bond_order_change_and_h_delta():
    t, reason = extract_donor_transform(
        "[CH3:1][CH2:2][OH:3]", "[CH3:1][CH:2]=[O:3]")
    assert reason == ""
    assert t["bond_changes"] == [
        {"map1": 2, "map2": 3, "order_lhs": "single", "order_rhs": "double"}]
    assert t["h_loss_maps"] == ["2", "3"] and t["h_gain_maps"] == []
    assert t["charge_changed_maps"] == []


def test_extract_rejects_duplicate_map_and_element_drift():
    # 映射号重复:不信任 qc_flags.bijection 声明,提取即拒
    t, reason = extract_donor_transform(
        "[CH3:1][CH2:1][OH:3]", "[CH3:1][CH:2]=[O:3]")
    assert t is None and reason.startswith("duplicate_map_no")
    # 同映射号元素漂移 = 映射损坏
    t, reason = extract_donor_transform(
        "[CH3:1][CH2:2][Cl:3]", "[CH3:1][CH2:2][OH:3]")
    assert t is None and reason == "map_element_changed:3"
    # 无变化模板无用
    t, reason = extract_donor_transform("[CH4:1]", "[CH4:1]")
    assert t is None and reason == "transform_no_change"


def test_extract_added_atom_and_leaving_group():
    # SN2 取代:Cl 为离去原子(removed),O 为新增原子(added+added_bonds)
    t, reason = extract_donor_transform(
        "[CH3:1][CH2:2][Cl:3]", "[CH3:1][CH2:2][O:4]")
    assert reason == ""
    assert t["removed_atoms"] == {"3": {"element": "Cl"}}
    assert t["added_atoms"] == {"4": {"element": "O", "charge": 0}}
    assert any(b["map1"] == 2 and b["map2"] == 4
               for b in t["added_bonds"])


# ------------------------------------------------------------ 夹具全量


@pytest.mark.parametrize("fx", [f for f in FIXTURES["synthetic_fixtures"]
                                if "donor" in f],
                         ids=lambda f: f["fixture_id"])
def test_synthetic_fixture_expectations(fx):
    """C0 夹具逐条:预期适用性、拒因子串与目标结构全部核对。"""
    substrate = fx["substrate_smiles"]
    res = assess_donor(_donor(fx["donor"]), substrate)
    assert res["status"] == fx["expected"], (fx["fixture_id"], res)
    for needle in fx.get("expected_reasons", []):
        assert any(needle in r for r in res["reject_reasons"]), \
            (fx["fixture_id"], res["reject_reasons"])
    if fx.get("target_expectation"):
        assert res["target_smiles"] == fx["target_expectation"]


@pytest.mark.parametrize("fx", [f for f in FIXTURES["synthetic_fixtures"]
                                if "card" in f],
                         ids=lambda f: f["fixture_id"])
def test_card_fixture_expectations(fx):
    """卡级夹具:多供体竞争/无映射卡的资格与 fallback 拒因。"""
    entry = evaluate_card(fx["card"], fx["substrate_smiles"],
                          fx.get("max_donors", 3))
    assert entry["status"] == fx["expected"], (fx["fixture_id"], entry)
    if fx.get("expected_fallback"):
        assert entry["fallback_reason"] == fx["expected_fallback"]


def test_real_asset_integration_fixture_with_sha():
    """真实资产可复核模板:记录行存在、SHA 与本仓清单一致、门禁可判。"""
    r1 = FIXTURES["real_asset_integration"][0]
    asset_path = REPO_ROOT / "assets" / r1["asset_rel"]
    import hashlib

    actual_sha = hashlib.sha256(asset_path.read_bytes()).hexdigest()
    manifest = {}
    for line in (REPO_ROOT / "assets" / "MANIFEST.sha256").read_text(
            encoding="utf-8").splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            manifest[parts[1].strip().lstrip("*")] = parts[0]
    assert manifest.get(r1["asset_rel"]) == actual_sha
    # 记录行按 record_id 找回(行内 line_no 是来源语料行号,非本文件行号)
    record = next(
        json.loads(line)
        for line in asset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        and json.loads(line).get("record_id") == r1["record_id"])
    assert record["line_no"] == r1["line_no"]
    assert record["qc_flags"]["bijection"] is True
    # 门禁判定与冻结预期一致(不重建 donor 引用之外的内容)
    donor = dict(record)
    donor.update({"index": "analog_corpus_templates",
                  "asset_file": r1["asset_rel"],
                  "asset_sha256": actual_sha,
                  "line_no": r1["line_no"],
                  "mapping_quality": "mapped_bijection"})
    donor.pop("template_id", None)
    donor.pop("provenance_sha256", None)
    donor.pop("qc_flags", None)
    donor.pop("confidence", None)
    donor.pop("source", None)
    donor.pop("env_shell", None)
    res = assess_donor(donor, r1["substrate_smiles"])
    assert res["status"] == r1["expected"], res
    assert res["target_smiles"] == r1["target_expectation"]
    assert res["selected_result"]["strategy"] == "reaction_center_substructure"


# ------------------------------------------------------------ 对齐与选择


def test_full_donor_preferred_over_weak_center():
    """全供体可对齐时不落中心子图;两者都可行时全供体优先。"""
    donor = {"record_id": "r", "index": "synthetic", "asset_file": "s",
             "asset_sha256": "0" * 64, "line_no": 1,
             "mapping_quality": "mapped_bijection",
             "mapped_lhs": "[CH3:1][CH2:2][CH2:3][OH:4]",
             "mapped_rhs": "[CH3:1][CH2:2][CH:3]=[O:4]",
             "center_atoms": [3, 4]}
    res = assess_donor(donor, cn_identity("CCCCCO"))
    assert res["status"] == APPLICABILITY_APPLICABLE
    assert res["selected_result"]["strategy"] == "full_donor_substructure"
    assert res["n_alignments_full"] >= 1 and res["n_alignments_center"] == 0


def test_all_matches_enumerated_not_first_only():
    """对齐枚举取全部匹配(uniquify=False),不取 RDKit 首个。"""
    donor = _aromatic_form("[CH3:1][CH2:2][OH:3]")
    current = _aromatic_form("OCCCO")
    aligns = enumerate_alignments(donor, current, [2, 3])
    assert aligns["_n_full"] == 2  # 两个末端 CH2-OH 都是对齐
    assert len(aligns["full_donor_substructure"]) == 2


def test_symmetric_merge_keeps_all_references():
    donor = {"record_id": "r", "index": "synthetic", "asset_file": "s",
             "asset_sha256": "0" * 64, "line_no": 1,
             "mapping_quality": "mapped_bijection",
             "mapped_lhs": "[CH3:1][CH2:2][OH:3]",
             "mapped_rhs": "[CH3:1][CH:2]=[O:3]", "center_atoms": [2, 3]}
    res = assess_donor(donor, cn_identity("OCCCO"))
    assert res["status"] == APPLICABILITY_APPLICABLE
    assert res["selected_result"]["n_equivalent_alignments"] == 2


def test_competing_alignments_ambiguous_with_targets():
    donor = {"record_id": "r", "index": "synthetic", "asset_file": "s",
             "asset_sha256": "0" * 64, "line_no": 1,
             "mapping_quality": "mapped_bijection",
             "mapped_lhs": "[CH3:1][CH2:2][OH:3]",
             "mapped_rhs": "[CH3:1][CH:2]=[O:3]", "center_atoms": [2, 3]}
    res = assess_donor(donor, cn_identity("OCC(C)CCO"))
    assert res["status"] == APPLICABILITY_AMBIGUOUS
    assert len(res["competing_targets"]) == 2


def test_two_donors_different_applicability_select_eligible():
    """两供体一适用一失配:只选有资格者,失配者留拒因摘要。"""
    card = {
        "evidence_id": "E1", "retrieval_rank": 1,
        "mapping_status": "resolved",
        "donor_refs": [
            {"record_id": "bad", "index": "synthetic",
             "asset_file": "s", "asset_sha256": "0" * 64, "line_no": 1,
             "mapping_quality": "mapped_bijection",
             "mapped_lhs": "[CH3:1][C:2](=[O:3])[CH3:4]",
             "mapped_rhs": "[CH3:1][CH:2]([OH:3])[CH3:4]",
             "center_atoms": [2, 3]},  # 酮还原:戊醇上无对齐
            {"record_id": "good", "index": "synthetic",
             "asset_file": "s", "asset_sha256": "0" * 64, "line_no": 2,
             "mapping_quality": "mapped_bijection",
             "mapped_lhs": "[CH3:1][CH2:2][OH:3]",
             "mapped_rhs": "[CH3:1][CH:2]=[O:3]",
             "center_atoms": [2, 3]},  # 醇氧化:可执行
        ],
    }
    entry = evaluate_card(card, cn_identity("CCCCCO"), 3)
    assert entry["status"] == APPLICABILITY_APPLICABLE
    assert entry["selected"]["record_id"] == "good"
    statuses = {e["record_id"]: e["status"] for e in entry["donor_evals"]}
    assert statuses == {"bad": APPLICABILITY_INAPPLICABLE,
                        "good": APPLICABILITY_APPLICABLE}


def test_donor_budget_is_frozen_cap():
    """供体预算 N 跨卡共享,超出部分不评估(数量如实记录)。"""
    card = {"evidence_id": "E1", "retrieval_rank": 1,
            "mapping_status": "resolved",
            "donor_refs": [
                {"record_id": f"d{i}", "index": "synthetic",
                 "asset_file": "s", "asset_sha256": "0" * 64,
                 "line_no": i, "mapping_quality": "mapped_bijection",
                 "mapped_lhs": "[CH3:1][C:2](=[O:3])[CH3:4]",
                 "mapped_rhs": "[CH3:1][CH:2]([OH:3])[CH3:4]",
                 "center_atoms": [2, 3]} for i in range(6)]}
    entry = evaluate_card(card, cn_identity("CCCCCO"), 3)
    assert entry["n_donor_refs"] == 6
    assert entry["n_donor_refs_evaluated"] == 3


def test_parent_eligibility_selection_and_fallbacks():
    """父级资格:单卡适用 → selected;无任何供体 → no_mapping。"""
    good = {"evidence_id": "E-good", "retrieval_rank": 2,
            "kind": "analog_reaction", "mapping_status": "resolved",
            "donor_refs": [
                {"record_id": "r1", "index": "synthetic",
                 "asset_file": "s", "asset_sha256": "0" * 64,
                 "line_no": 1, "mapping_quality": "mapped_bijection",
                 "mapped_lhs": "[CH3:1][CH2:2][OH:3]",
                 "mapped_rhs": "[CH3:1][CH:2]=[O:3]",
                 "center_atoms": [2, 3]}]}
    block = build_eligibility([good], cn_identity("CCCCCO"),
                              ApplicabilityPolicy())
    assert block["status"] == APPLICABILITY_APPLICABLE
    assert block["selected"]["evidence_id"] == "E-good"
    assert block["selected"]["target_smiles"] == "CCCCC=O"
    assert block["fallback_reason"] == ""
    empty = {"evidence_id": "E-none", "retrieval_rank": 1,
             "kind": "analog_reaction", "mapping_status": "unavailable",
             "donor_refs": []}
    block2 = build_eligibility([empty], cn_identity("CCCCCO"),
                               ApplicabilityPolicy())
    assert block2["status"] == APPLICABILITY_UNAVAILABLE
    assert block2["fallback_reason"] == "no_mapping"


# ------------------------------------------------------------ 直接核验


def test_bond_order_guard_fires_on_aligned_pair():
    """键级上下文守卫:对齐给定时,当前键级与供体 lhs 不符即拒
    (枚举查询携带键级,故该守卫覆盖中心外的键与芳香路径)。"""
    t, _ = extract_donor_transform("[CH3:1][O:2][CH3:3]",
                                   "[CH3:1][O:2].[CH3:3]")
    cur = _aromatic_form("COC=O")  # 甲酸甲酯:O1-C2 醚单键,O3=C2 酯双键
    h, ch = _h_charge(cur)
    # 对齐:供体 O(map2)→羰基 O(idx3),供体 C(map3)→酯碳(idx2)
    res = assess_alignment(
        t, {0: 0, 1: 3, 2: 2}, "reaction_center_substructure",
        donor_mol=_aromatic_form("[CH3:1][O:2][CH3:3]"),
        current_mol=cur, current_kek=_kekulized("COC=O"),
        current_h=h, current_charge=ch)
    assert not res["ok"]
    assert any("bond_order_mismatch" in r for r in res["reasons"])


def test_empty_center_atoms_falls_back_to_mapped_atoms():
    """模板缺 center_atoms 元数据 → 中心查询回退到全部带映射原子
    (与 align_donor_mapping 既定语义一致;封存首跑 56 个引用属此类)。
    注:此类模板多因"真实反应在未映射区"在变换提取阶段即 unavailable
    (assess_donor 先提取后对齐),故本测试直接钉枚举层语义。"""
    donor_mol = _aromatic_form(
        "N=C(N)N[c:4]1[cH:3][cH:2][cH:1][cH:6][cH:5]1")
    cur = _aromatic_form("Oc1ccc(I)cc1")
    aligns = enumerate_alignments(donor_mol, cur, [])
    assert aligns.get("_n_center", 0) >= 1
    from pathway_v43.services.atom_tool import align_donor_mapping

    m, _ = align_donor_mapping(donor_mol, cur, center_map_nums=[],
                               center_only=True)
    assert m is not None


def test_hydrogen_outcome_mismatch_catches_shell_divergence():
    """氢结算守卫:邻域上下文分歧(当前多出供体没有的取代基)→ 拒。"""
    # 供体:乙醛氧化的逆过程不构造;直接用醇氧化模板但底物中心多一个取代基
    t, _ = extract_donor_transform("[CH3:1][CH2:2][OH:3]",
                                   "[CH3:1][CH:2]=[O:3]")
    cur = _aromatic_form("CC(C)(C)O")
    h, ch = _h_charge(cur)
    res = assess_alignment(
        t, {0: 0, 1: 1, 2: 4}, "reaction_center_substructure",
        donor_mol=_aromatic_form("[CH3:1][CH2:2][OH:3]"),
        current_mol=cur, current_kek=_kekulized("CC(C)(C)O"),
        current_h=h, current_charge=ch)
    assert not res["ok"]


# ---------------------------------------------------- Phase C R3 补钉


def test_all_alignments_assessed_beyond_storage_sample():
    """全对齐评估与落盘样本分离:18 个枚举对齐**全部参与判定**
    (n_alignments_assessed=18,旧截断实现只能评估到 16);产物明细
    只落 16 条样本,总数由 n_alignments_* 如实留痕。"""
    donor = {"record_id": "r", "index": "synthetic", "asset_file": "s",
             "asset_sha256": "0" * 64, "line_no": 1,
             "mapping_quality": "mapped_bijection",
             "mapped_lhs": "[CH3:1][CH2:2][OH:3]",
             "mapped_rhs": "[CH3:1][CH:2]=[O:3]", "center_atoms": [2, 3]}
    substrate = "O" + "CCO" * 9  # 18 个 C–C–O 枚举位点(>旧存储上限 16)
    aligns = enumerate_alignments(_aromatic_form(donor["mapped_lhs"]),
                                  _aromatic_form(substrate), [2, 3])
    assert aligns["_n_full"] == 18
    assert len(aligns["full_donor_substructure"]) == 18  # 枚举不截断
    res = assess_donor(donor, substrate)
    assert res["status"] == APPLICABILITY_APPLICABLE
    assert res["n_alignments_assessed"] == 18  # 判定覆盖全部对齐
    assert res["n_alignments_full"] == 18
    # 18 个枚举位点中仅 1 个通过结构必要条件(其余留具体拒因),
    # 该位点两个朝向产生同一产物 → 对称等价合并 = 2
    assert res["selected_result"]["n_equivalent_alignments"] == 2
    assert len(res["results"]) == 16  # 落盘明细只留样本


def test_alignment_enum_limit_explicit_and_truncation_flagged():
    """R2 复核 P2:枚举上限显式给出(RDKit 缺省 1000 也会静默截断),
    触顶返回 ``_truncated=True``;未触顶为 False。"""
    from pathway_v43.services.donor_applicability import (
        _ALIGNMENT_ENUM_LIMIT, ALIGN_FULL)

    donor_mol = _aromatic_form("C")  # 单碳查询:每个独立碳都是一个匹配
    big = _aromatic_form(".".join(["C"] * 2502))
    aligns = enumerate_alignments(donor_mol, big, [])
    assert aligns["_n_full"] == _ALIGNMENT_ENUM_LIMIT
    assert len(aligns[ALIGN_FULL]) == _ALIGNMENT_ENUM_LIMIT
    assert aligns["_truncated"] is True
    small = _aromatic_form("CCO")
    aligns2 = enumerate_alignments(donor_mol, small, [])
    assert aligns2["_n_full"] == 2 and aligns2["_truncated"] is False


def test_truncated_enum_never_claims_unique_target(monkeypatch):
    """截断集合不得当作唯一适用目标:触顶时 applicable 一律降为
    ambiguous 并带 alignment_limit_exceeded(上限之外仍可能有竞争对齐);
    已评估全败 + 触顶也不得声称 inapplicable(假阴性)→ unavailable。"""
    import pathway_v43.services.donor_applicability as da

    donor = {"record_id": "r", "index": "synthetic", "asset_file": "s",
             "asset_sha256": "0" * 64, "line_no": 1,
             "mapping_quality": "mapped_bijection",
             "mapped_lhs": "[CH3:1][CH2:2][OH:3]",
             "mapped_rhs": "[CH3:1][CH:2]=[O:3]", "center_atoms": [2, 3]}
    substrate = "OCCCO"  # 未触顶时:applicable、n_equivalent=2

    real = da.enumerate_alignments

    def truncated_enum(donor_mol, current_mol, center_map_nums):
        out = real(donor_mol, current_mol, center_map_nums)
        out["_truncated"] = True
        return out

    def failing_alignment(*_a, **_k):
        return {"ok": False, "strategy": "", "alignment": {},
                "reasons": ["insufficient_hydrogen"],
                "unverified_conditions": [], "product_smiles": ""}

    monkeypatch.setattr(da, "enumerate_alignments", truncated_enum)
    res = assess_donor(donor, substrate)
    assert res["status"] == APPLICABILITY_AMBIGUOUS
    assert "alignment_limit_exceeded" in res["reject_reasons"]
    assert res["alignment_enum_truncated"] is True
    assert res.get("selected_result") is None

    monkeypatch.setattr(da, "assess_alignment", failing_alignment)
    res2 = assess_donor(donor, substrate)  # 真实对齐但全部评估失败 + 触顶
    assert res2["status"] == APPLICABILITY_UNAVAILABLE
    assert "alignment_limit_exceeded" in res2["reject_reasons"]
