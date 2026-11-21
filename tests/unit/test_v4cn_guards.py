"""T2-H v4-cn 护栏单测：不变量 / 身份同源 / 净电荷 / 盐 / 排除清单 / 留痕。

夹具全部为合成分子（非金标、非题面），只钉算子行为，不跑完整判分。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script(name: str):
    path = REPO_ROOT / "scripts" / "eval" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"v13_eval_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def guards():
    return _load_script("score_disclosure_v4cn")


EXPECTED_STATUS = {
    "quaternary_ammonium": "not_applicable",
    "quaternary_ammonium_chloride": "salt_not_normalized",
    "pyridinium": "applied",
    "glycine_zwitterion": "applied",
    "betaine_inner_salt": "not_applicable",
    "nitro_neutral": "not_applicable",
    "n_oxide_neutral": "not_applicable",
    "azoxylium": "not_applicable",
    "phosphate_dianion": "applied",
    "sulfate_monoanion": "applied",
    "sulfonate_aryl": "applied",
    "coa_thioester_like": "not_applicable",
    "sodium_salt": "salt_not_normalized",
    "chloride_ammonium_salt": "salt_not_normalized",
    "enolate": "applied",
    "carbonate_dianion": "excluded_family",
    "bicarbonate": "excluded_family",
    "carbon_dioxide": "excluded_family",
    "ammonium": "excluded_family",
    "cyanide": "excluded_family",
    "thiocyanate": "excluded_family",
    "hydronium": "excluded_family",
    "methyl_radical": "not_applicable",
    "enhanced_stereo": "not_applicable",
    "uncharged_acetate_acid": "not_applicable",
}


def test_fixture_status_table(guards):
    assert set(EXPECTED_STATUS) == {fid for fid, _ in guards.FIXTURES}
    for fixture_id, smiles in guards.FIXTURES:
        assert guards.neutralize_checked(smiles)["status"] == \
            EXPECTED_STATUS[fixture_id], fixture_id


def test_every_revert_has_machine_reason(guards):
    for fixture_id, smiles in guards.FIXTURES:
        record = guards.neutralize_checked(smiles)
        if record["status"] != "applied":
            assert record["reason"], fixture_id
            assert record["rewritten"] is False, fixture_id


def test_applied_outputs_use_strict_identity_machine(guards):
    from pathway_v43.pollutant.chemstate import strict_identity_of

    for fixture_id, smiles in guards.FIXTURES:
        record = guards.neutralize_checked(smiles)
        if record["status"] != "applied":
            continue
        assert strict_identity_of(record["output"]) == record["output"], \
            fixture_id


def test_neutralization_is_idempotent(guards):
    for fixture_id, smiles in guards.FIXTURES:
        record = guards.neutralize_checked(smiles)
        if record["status"] != "applied":
            continue
        again = guards.neutralize_checked(record["output"])
        assert again["output"] == record["output"], fixture_id


def test_salt_is_not_stripped_or_rewritten(guards):
    record = guards.neutralize_checked("[Cl-].C[NH3+]")
    assert record["status"] == "salt_not_normalized"
    assert record["output"] == "[Cl-].C[NH3+]"
    assert record["n_frags_before"] == 2


def test_enhanced_stereo_and_radical_preserved(guards):
    stereo = guards.neutralize_checked("F[C@H](Cl)Br |&1:1|")
    assert stereo["output"] == "F[C@H](Cl)Br |&1:1|"
    radical = guards.neutralize_checked("[CH3]")
    assert radical["output"] == "[CH3]"


def test_net_charge_guard_reverts_zero_to_nonzero(guards, monkeypatch):
    class FakeUncharger:
        def uncharge(self, mol):
            out = Chem.RWMol(mol)
            for atom in out.GetAtoms():
                if atom.GetFormalCharge() < 0:
                    atom.SetFormalCharge(0)
            return out.GetMol()

    monkeypatch.setattr(guards, "_uncharger", lambda: FakeUncharger())
    # 只隔离测电荷闸：不变量签名固定为空（该闸的行为由下一用例单独测）
    monkeypatch.setattr(guards, "_invariant_signature", lambda mol: {})
    # 两性离子净 0；去除阴离子电荷后变净 +1 ⇒ 0→非 0 必须回退
    record = guards.neutralize_checked("[NH3+]CC(=O)[O-]")
    assert record["status"] == "net_charge_changed"
    assert record["reason"] == "zero_to_nonzero"
    assert record["output"] == "[NH3+]CC(=O)[O-]"
    # 带电 → 反号也回退
    class SignFlipUncharger:
        def uncharge(self, mol):
            out = Chem.RWMol(mol)
            for atom in out.GetAtoms():
                if atom.GetFormalCharge() < 0:
                    atom.SetFormalCharge(1)
            return out.GetMol()

    monkeypatch.setattr(guards, "_uncharger", lambda: SignFlipUncharger())
    record = guards.neutralize_checked("CC(=O)[O-]")
    assert record["status"] == "net_charge_changed"
    assert record["reason"] == "sign_flip"


def test_invariant_guard_reverts_graph_change(guards, monkeypatch):
    class FakeUncharger:
        def uncharge(self, mol):
            out = Chem.RWMol(mol)
            for bond in out.GetBonds():
                if str(bond.GetBondType()) == "DOUBLE":
                    bond.SetBondType(Chem.BondType.SINGLE)
            return out.GetMol()

    monkeypatch.setattr(guards, "_uncharger", lambda: FakeUncharger())
    record = guards.neutralize_checked("CC(=O)[O-]")
    assert record["status"] == "invariant_broken"
    assert record["rewritten"] is False


def test_payload_derived_fields_and_policy(guards):
    payload = {"states": [
        {"state_id": "s1", "payload": json.dumps({
            "smiles_isomeric": "CC(=O)[O-]", "cn_identity": "old",
            "formal_charge": -1})},
        {"state_id": "s2", "payload": {"smiles_isomeric": ""}},
    ]}
    records: dict = {}
    out = guards._neutral_payload(payload, records)
    body = out["states"][0]["payload"]
    assert body["smiles_isomeric"] == "CC(=O)O"
    assert body["cn_identity"] == "CC(=O)O"
    assert body["formal_charge"] == 0
    assert body["v4cn_derived_fields_policy"] == "identity_axis_only"
    # state_id 保持原值（身份轴改写，不重排出现键）
    assert out["states"][0]["state_id"] == "s1"
    assert records["s1"]["status"] == "applied"
    assert out["states"][1]["payload"]["smiles_isomeric"] == ""


def test_graph_records_and_no_mutation(guards):
    graph = {"nodes": [{"node_id": "n1",
                        "structure_smiles": "CC(=O)[O-]"},
                       {"node_id": "n2",
                        "structure_smiles": "[Cl-].C[NH3+]"}],
             "edges": []}
    records: dict = {}
    out = guards._neutral_graph(graph, records)
    assert out["nodes"][0]["structure_smiles"] == "CC(=O)O"
    assert out["nodes"][1]["structure_smiles"] == "[Cl-].C[NH3+]"
    assert graph["nodes"][0]["structure_smiles"] == "CC(=O)[O-]"
    assert records["n1"]["status"] == "applied"
    assert records["n2"]["status"] == "salt_not_normalized"


def test_operator_table_has_no_smiles(guards):
    table = guards.probe_operator_table()
    assert table["fixture_count"] == len(guards.FIXTURES)
    fixture_smiles = {smiles for _, smiles in guards.FIXTURES}
    for row in table["fixtures"]:
        assert not (set(row.values()) & fixture_smiles)
        assert set(row) == {
            "fixture_id", "status", "reason", "rewritten",
            "net_charge_before", "net_charge_after", "n_frags_before",
            "permanent_charge_retained", "legacy_rewrite",
            "identity_roundtrip_ok",
        }


def test_record_summary_marks_suppressed_legacy_rewrites(guards):
    records = {
        "a": guards.neutralize_checked("[Cl-].C[NH3+]"),
        "b": guards.neutralize_checked("CC(=O)[O-]"),
    }
    summary = guards._record_summary(records)
    assert summary["n_structures"] == 2
    assert summary["n_rewritten"] == 1
    assert summary["n_legacy_rewrites_suppressed"] == 1
    assert summary["changed_state_ids"] == ["b"]