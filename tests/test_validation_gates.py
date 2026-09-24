"""确定性门禁:可解析/价态、兄弟去重、路径内循环、方向/来源、深度预算。"""

from __future__ import annotations

from pathway_v43.domain.identity import cn_identity
from pathway_v43.validation.gates import (
    gate_budget,
    gate_depth,
    gate_direction_source,
    gate_smiles,
    validate_event_products,
)

from wf_helpers import evidence

CN = cn_identity("Oc1ccccc1O")


def test_gate_smiles_parse_and_valence():
    ok, _ = gate_smiles("Oc1ccccc1O")
    assert ok
    # 价态非法:五价碳(RDKit sanitize 拒绝)
    ok, reason = gate_smiles("C(C)(C)(C)(C)C")
    assert not ok and "unparseable" in reason
    ok, _ = gate_smiles("")
    assert not ok


def test_gate_direction_source_requires_exact_match_for_recorded():
    ev = evidence("bt0#r0", "recorded_reaction", CN, ["CC(O)=O"])
    ok, _ = gate_direction_source(ev)
    assert ok
    ev_bad = dict(ev, match_type="retrieval_similarity")
    ok, reason = gate_direction_source(ev_bad)
    assert not ok and "direction_or_source" in reason
    ev_nosrc = dict(ev, source_id="")
    ok, reason = gate_direction_source(ev_nosrc)
    assert not ok


def test_event_products_duplicate_in_event_keeps_first():
    ev = evidence("bt0#r0", "recorded_reaction", CN,
                  ["CC(O)=O", "CC(O)=O"])  # 对称位点重复产物
    verdicts = validate_event_products(evidence=ev, ancestry_cns=[CN])
    assert verdicts[0].accepted is True
    assert verdicts[1].accepted is False
    assert any("sibling_dedup" in r for r in verdicts[1].reasons)


def test_event_products_sibling_from_existing_path_rejected():
    ev = evidence("bt0#r0", "recorded_reaction", CN, ["CC(O)=O"])
    verdicts = validate_event_products(
        evidence=ev, ancestry_cns=[CN],
        existing_sibling_cns={cn_identity("CC(O)=O")},
    )
    assert verdicts[0].accepted is False
    assert any("sibling_dedup" in r for r in verdicts[0].reasons)


def test_event_products_in_path_cycle_rejected():
    """产物回到本路径祖先(含当前底物)→ cycle;不同路线汇合不是循环。"""
    ev = evidence("bt0#r0", "recorded_reaction", CN, ["Oc1ccccc1O"])
    verdicts = validate_event_products(evidence=ev, ancestry_cns=[CN])
    assert verdicts[0].accepted is False
    assert any("in_path_cycle" in r for r in verdicts[0].reasons)
    # 同一分子在另一条无祖先关系的路径上不是循环
    verdicts2 = validate_event_products(
        evidence=ev, ancestry_cns=[cn_identity("CCO")])
    assert verdicts2[0].accepted is True


def test_event_products_unparseable_rejected():
    ev = evidence("bt0#r0", "recorded_reaction", CN, ["C(C)(C)(C)(C)(C)C"])
    verdicts = validate_event_products(evidence=ev, ancestry_cns=[CN])
    assert verdicts[0].accepted is False
    assert any("unparseable" in r for r in verdicts[0].reasons)


def test_order_preserved_and_mapping_declared():
    prods = ["O=CCC=CO", "CC(O)=O"]
    ev = evidence("bt0#r0", "recorded_reaction", CN, prods)
    verdicts = validate_event_products(evidence=ev, ancestry_cns=[CN])
    assert [v.position for v in verdicts] == [0, 1]
    assert all(v.accepted for v in verdicts)
    assert ev["atom_mapping"] == "unavailable"  # 明确声明,不是含糊缺席


def test_depth_and_budget_gates():
    ok, _ = gate_depth(0, 3)
    assert ok
    ok, reason = gate_depth(3, 3)
    assert not ok and "depth_limit" in reason
    ok, reason = gate_budget(3, 3)
    assert not ok and "budget_exhausted" in reason
    ok, _ = gate_budget(2, 3)
    assert ok
