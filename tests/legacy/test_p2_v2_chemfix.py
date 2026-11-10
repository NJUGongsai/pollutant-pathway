"""P2 证据卡 v2 化学修复测试（2026-10-21）。

任务：`docs/T_P2_V2_CHEMFIX_IMPL_2026-10-21.md`（主窗口任务书）。
验收标准：`docs/T_P2_V2_CHEM_REVIEW_2026-10-21.md` §2 七项 must-fix +
§1 的 19 条逐条判定（9 条「对」不得回归，10 条「错」必须翻成预期结果）。

本文件显式保存 before/after 观测表：
- before = `impl.patch`（SHA cd8c03e0…ebbd6）在基线 11aeeaf 上的实测；
- after  = 本修复后的实测；
- 9 条「对」：before == after（不回归）；
- 10 条「错」：before != after（翻成预期）。

零金标零题面零模型；全部为合成 SMILES。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
from rdkit import Chem, RDLogger

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pathway_v43.pollutant import candidate_evidence as ce  # noqa: E402
from pathway_v43.pollutant.chemstate import build_chemical_state  # noqa: E402
from pathway_v43.pollutant.production import prepare_hypothesis  # noqa: E402
from pathway_v43.pollutant.real_model import (  # noqa: E402
    PROPOSALS_PROMPT_VERSION,
    PROPOSALS_PROMPT_VERSION_V2,
    build_proposals_user_payload,
    proposals_system_prompt,
)

RDLogger.DisableLog("rdApp.*")

V1_PROMPT_SHA256 = (
    "fe9eaf770deb19f8c6eec9aee14febe83f6b2d47f53e1c60002bb808eb3b0f4e")
# 复审记录的旧 v2 prompt（impl.patch r2）
OLD_V2_PROMPT_SHA256 = (
    "89311fdb5a85e6699f558d7b0ab64e7cc7972cad616d3c8972101f80a6b50f37")
# 本修复后的 v2 prompt（两臂共用；改一字即改版本哈希）
NEW_V2_PROMPT_SHA256 = (
    "c24bee42f651c783c9bdcee6e8f547bff63f1f5fee6a4a87f4816e4d15e57598")


# ---------------------------------------------------------------- helpers


def _prompt() -> str:
    return proposals_system_prompt("v2")


def _hits(smiles: str) -> dict[str, int]:
    return dict(ce.substrate_facts_v2(smiles)["class_hits"])


def _c_ox(smiles: str):
    return ce.substrate_facts_v2(smiles)["carbon_oxidation_state"]


def _detail(smiles: str):
    mol = Chem.MolFromSmiles(smiles)
    counts = ce._element_counts_v2(mol)
    charge = ce._formal_charge_v2(mol)
    return ce._carbon_oxidation_state_detail_v2(mol, counts, charge)


def _delta(substrate: str, product: str) -> tuple[dict, dict]:
    evidence = ce.candidate_evidence_payload_v2(
        spec={"product_smiles": product}, prepared=None,
        substrate_facts=ce.substrate_facts_v2(substrate))
    return evidence["product_delta"], evidence["functional_group_delta"]


def _amine_total(smiles: str) -> int:
    hit_map = _hits(smiles)
    return sum(hit_map.get(name, 0) for name in
               ("amine_primary", "amine_secondary", "amine_tertiary"))


def _participant_rows() -> list[dict]:
    spec = {
        "key": "rec-CHEMFIX-0002@L3", "product_smiles": "CC=O",
        "coefficient": 1,
        "transformation_ref": "CHEMFIX-0002@L3",
        "origin_group_key": "rec-source:CHEMFIX-0002@L3",
        "edits": [{"op": "change_bond_order", "atom1": "S_C_2",
                   "atom2": "S_O_1", "from_order": "single",
                   "to_order": "double"}],
        "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]},
        "alignment": {"status": "resolved",
                      "donor_to_current": {"S_C_2": "S_C_2",
                                           "S_O_1": "S_O_1"},
                      "equivalence_classes": [],
                      "ref": "recorded-inferred:CHEMFIX-0002@L3"},
        "expectation": {"target_smiles": "CC=O"},
        "coproducts": ["CO"],
    }
    substrate = build_chemical_state(
        "CCO", "raw_input", [{"record": "chemfix-synthetic"}])
    prepared = prepare_hypothesis(
        spec, parent_path_id="chemfix-test", substrate_state=substrate,
        transformation_ref=str(spec["transformation_ref"]))
    evidence = ce.candidate_evidence_payload_v2(
        spec=spec, prepared=prepared,
        substrate_facts=ce.substrate_facts_v2("CCO"))
    return evidence["participants"]


def _payload_shape() -> dict:
    spec = {"key": "rec-CHEMFIX-0001@L3", "product_smiles": "CC=O",
            "transformation_ref": "CHEMFIX-0001@L3",
            "edits": [], "alignment": {"status": "resolved"}}
    evidence = ce.candidate_evidence_payload_v2(
        spec=spec, prepared=None,
        substrate_facts=ce.substrate_facts_v2("CCO"))
    raw = build_proposals_user_payload(
        substrate_smiles="CCO",
        atom_id_map={"S_C_1": "C", "S_C_2": "C", "S_O_1": "O"},
        pool_entries=[{"hypothesis_id": "H", "product_smiles": "CC=O",
                       "transformation_ref": "CHEMFIX-0001@L3",
                       "coproducts": [], "evidence": evidence}],
        execution_graph={"atoms": [{"id": "S_C_1", "element": "C"}],
                         "bonds": []},
        substrate_evidence=ce.substrate_evidence_payload_v2("CCO"),
        schema_version=ce.CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2)
    return json.loads(raw)


# ---------------------------------------------------------------- 19-item matrix


def _observe(item: str):
    """当前树的逐条观测（before/after 同一口径）。"""
    if item == "A1":
        payload = _payload_shape()
        entry = payload["pool_hypotheses"][0]["evidence"]
        return {
            "has_substrate_smiles": "substrate_smiles" in payload,
            "has_atom_id_map": "substrate_atom_id_map" in payload,
            "has_execution_graph": "execution_graph" in payload,
            "substrate_fg_classes": [
                row["class"]
                for row in payload["substrate_evidence"][
                    "functional_groups"]],
            "product_delta": entry["product_delta"],
        }
    if item == "A2":
        return {
            "prompt_defines_n_hits": (
                "n_hits is the number of distinct matched atom tuples"
                in _prompt()),
            "prompt_says_may_exceed_groups": (
                "may exceed the number of functional groups" in _prompt()),
            "prompt_distinguishes_class_delta": (
                "The substrate n_hits and the functional-group class delta"
                in _prompt()),
        }
    if item == "A3":
        delta = _delta("CCO", "OCCO")[1]
        return {
            "gained": delta["gained"], "lost": delta["lost"],
            "prompt_not_hit_counts": (
                "not hit-count changes" in _prompt()),
        }
    if item == "A4":
        product_delta = _delta("CC(=O)OCC", "CC(=O)O")[0]
        return {
            "formula": product_delta["formula"],
            "c_ox": product_delta["carbon_oxidation_state"],
            "prompt_principal_minus_substrate": (
                "designated principal product minus the substrate"
                in _prompt()),
            "prompt_excludes_water_and_coproducts": (
                "It excludes co-substrates, water, and coproducts"
                in _prompt()),
            "prompt_not_balanced_net_reaction": (
                "not a balanced net reaction" in _prompt()),
        }
    if item == "A5":
        return {
            "cannizzaro_delta": _delta("C=O", "CO")[0][
                "carbon_oxidation_state"],
            "prompt_scope_principal": (
                "designated principal product" in _prompt()),
            "prompt_not_redox_balance_proof": (
                "not a per-atom, mechanism, or redox-balance proof"
                in _prompt()),
        }
    if item == "A6":
        absent = ce.candidate_evidence_payload_v2(
            spec={"product_smiles": "CCO"}, prepared=None,
            substrate_facts=ce.substrate_facts_v2("CCO"))
        empty = ce.candidate_evidence_payload_v2(
            spec={"product_smiles": "CCO", "requirements": []},
            prepared=None, substrate_facts=ce.substrate_facts_v2("CCO"))
        return {
            "absent": absent["conditions_and_scope"]["requirements"],
            "empty": empty["conditions_and_scope"]["requirements"],
            "prompt_unknown_not_negative": (
                "an unknown field is not negative evidence" in _prompt()),
        }
    if item == "A7":
        rows = _participant_rows()
        return {
            "n_rows": len(rows),
            "coefficients": [row["coefficient"] for row in rows],
            "keys": sorted(rows[0]),
        }
    if item == "B1":
        return {
            "bad": {name: _hits(smiles).get("carboxylic_acid", 0)
                    for name, smiles in {
                        "carbonate": "[O-]C(=O)[O-]",
                        "bicarbonate": "OC(=O)[O-]",
                        "carbamate": "NC(=O)[O-]",
                        "carbonic_acid": "OC(=O)O",
                        "carbamic_acid": "NC(=O)O",
                        "methyl_carbonate": "COC(=O)O",
                    }.items()},
            "good": {name: _hits(smiles).get("carboxylic_acid", 0)
                     for name, smiles in {
                         "acetic_acid": "CC(=O)O",
                         "acetate": "CC(=O)[O-]",
                         "formic_acid": "C(=O)O",
                         "formate": "C(=O)[O-]",
                     }.items()},
        }
    if item == "B2":
        return {
            "bad": {name: _amine_total(smiles)
                    for name, smiles in {
                        "thioacetamide": "CC(N)=S",
                        "amidine": "CC(=N)N",
                        "guanidine": "NC(=N)N",
                        "thiourea": "NC(=S)N",
                        "n_methylthioacetamide": "CC(=S)NC",
                        "creatine": "CN(CC(=O)O)C(=N)N",
                    }.items()},
            "good": {name: _amine_total(smiles)
                     for name, smiles in {
                         "ethylamine": "CCN",
                         "ethylammonium": "CC[NH3+]",
                         "trimethylamine": "CN(C)C",
                         "n_methylpyrrolidine": "CN1CCCC1",
                     }.items()},
        }
    if item == "B3":
        pairs = {
            "primary_neutral": ("CCN", "amine_primary"),
            "primary_charged": ("CC[NH3+]", "amine_primary"),
            "secondary_charged": ("CC[NH2+]C", "amine_secondary"),
            "tertiary_neutral": ("CN(C)C", "amine_tertiary"),
            "tertiary_charged": ("C[NH+](C)C", "amine_tertiary"),
        }
        negatives = {
            "pyridine": "c1ccncc1",
            "pyrrole": "c1cc[nH]c1",
            "indole": "c1ccc2[nH]ccc2c1",
            "imidazole": "c1c[nH]cn1",
            "hydroxylamine": "NO",
            "hydrazine": "NN",
            "trimethylamine_n_oxide": "C[N+](C)(C)[O-]",
            "pyridine_n_oxide": "[O-][n+]1ccccc1",
        }
        return {
            "pairs": {name: _hits(smiles).get(cls, 0)
                      for name, (smiles, cls) in pairs.items()},
            "negatives": {name: _amine_total(smiles)
                          for name, smiles in negatives.items()},
        }
    if item == "B4":
        return {
            "amine_hits": _amine_total("C[N+](C)(C)C"),
            "class_hits": _hits("C[N+](C)(C)C"),
        }
    if item == "B5":
        return {
            "chloronium_halide_cl": _hits(
                "C[Cl+](C)C").get("halide_cl", 0),
            "iodonium_halide_i": _hits("C[I+]C").get("halide_i", 0),
            "glycerol_hydroxyl_oh": _hits(
                "OCC(O)CO").get("hydroxyl_oh", 0),
            "prompt_defines_n_hits": (
                "n_hits is the number of distinct matched atom tuples"
                in _prompt()),
            "prompt_distinguishes_class_delta": (
                "The substrate n_hits and the functional-group class delta"
                in _prompt()),
        }
    if item == "B6":
        return {
            "phosphocholine": _hits("C[N+](C)(C)CCOP(=O)(O)O"),
            "choline_amine_hits": _amine_total("C[N+](C)(C)CCO"),
            "heteroarene_arene_ring": {
                "pyridine": _hits("c1ccncc1").get("arene_ring", 0),
                "imidazole": _hits("c1c[nH]cn1").get("arene_ring", 0),
                "furan": _hits("c1ccoc1").get("arene_ring", 0),
                "thiophene": _hits("c1ccsc1").get("arene_ring", 0),
            },
            "prompt_table_not_exhaustive": (
                "the functional-group class table is not exhaustive"
                in _prompt()),
            "prompt_unlisted_not_absent": (
                "not evidence that the group is absent" in _prompt()),
            "prompt_names_quaternary_ammonium": (
                "quaternary ammonium" in _prompt()),
            "prompt_names_heteroarene": "heteroarene" in _prompt(),
        }
    if item == "C1":
        return {
            "methane": _c_ox("C"),
            "methanol": _c_ox("CO"),
            "ethanol": _c_ox("CCO"),
            "acetaldehyde": _c_ox("CC=O"),
            "acetic_acid": _c_ox("CC(=O)O"),
            "acetate": _c_ox("CC(=O)[O-]"),
            "carbon_dioxide": _c_ox("O=C=O"),
            "formic_acid": _c_ox("C(=O)O"),
            "formate": _c_ox("C(=O)[O-]"),
        }
    if item == "C2":
        return {
            "dimethyl_peroxide": _c_ox("COOC"),
            "methyl_hydroperoxide": _c_ox("COO"),
            "diethyl_peroxide": _c_ox("CCOOCC"),
            "peroxyacetic_acid": _c_ox("CC(=O)OO"),
            "methyl_perchlorate": _c_ox("COCl(=O)(=O)=O"),
            "hydrogen_peroxide": _c_ox("OO"),
            "methylamine_domain": _c_ox("CN"),
            "closed_shell_ethanol": _c_ox("CCO"),
        }
    if item == "C3":
        return {
            "oxonium_zwitterion": _c_ox("C[O+](C)CC(=O)[O-]"),
            "methoxide": _c_ox("C[O-]"),
            "iodonium": _c_ox("C[I+]C"),
            "trimethylchloronium": _c_ox("C[Cl+](C)C"),
            "glycine_zwitterion": _c_ox("[NH3+]CC(=O)[O-]"),
        }
    if item == "C4":
        return {
            "methyl_radical": _c_ox("[CH3]"),
            "carbene": _c_ox("[CH2]"),
            "phenoxyl_radical": _c_ox("[O]c1ccccc1"),
        }
    if item == "C5":
        return {
            "ethanol_to_glycerol": _delta(
                "CCO", "OCC(O)CO")[0]["carbon_oxidation_state"],
            "ethyl_acetate_hydrolysis": _delta(
                "CC(=O)OCC", "CC(=O)O")[0]["carbon_oxidation_state"],
            "cannizzaro": _delta("C=O", "CO")[0][
                "carbon_oxidation_state"],
            "prompt_different_carbon_set": (
                "different carbon set" in _prompt()),
            "prompt_nonzero_not_oxidation_event": (
                "does not by itself show an oxidation or reduction event"
                in _prompt()),
            "prompt_redox_equivalents_coproducts": (
                "redox equivalents may be carried by coproducts"
                in _prompt()),
        }
    if item == "C6":
        same = _delta("CCO", "CCO")[0]
        unknowns = [_delta("CCO", product)[0]
                    for product in ("CCO.CC", "", "not_a_smiles")]
        return {
            "same_formula": same["formula"],
            "same_c_ox": same["carbon_oxidation_state"],
            "unknowns": unknowns,
        }
    raise AssertionError(f"unknown item {item}")


# before = impl.patch r2（未修）实测；after = chemfix 实测。
# 每条只列判定所需观测；9 条「对」要求 before == after，
# 10 条「错」要求 before != after 且 after 为复审预期。
BEFORE_AFTER: dict[str, dict] = {
    "A1": {
        "judgment": "对",
        "before": {
            "has_substrate_smiles": True, "has_atom_id_map": True,
            "has_execution_graph": True,
            "substrate_fg_classes": ["hydroxyl_oh"],
            "product_delta": {
                "scope": "principal_product",
                "formula": {"H": -2},
                "carbon_oxidation_state": 1.0},
        },
        "after": {
            "has_substrate_smiles": True, "has_atom_id_map": True,
            "has_execution_graph": True,
            "substrate_fg_classes": ["hydroxyl_oh"],
            "product_delta": {
                "scope": "principal_product",
                "formula": {"H": -2},
                "carbon_oxidation_state": 1.0},
        },
    },
    "A2": {
        "judgment": "错",
        "before": {
            "prompt_defines_n_hits": False,
            "prompt_says_may_exceed_groups": False,
            "prompt_distinguishes_class_delta": False},
        "after": {
            "prompt_defines_n_hits": True,
            "prompt_says_may_exceed_groups": True,
            "prompt_distinguishes_class_delta": True},
    },
    "A3": {
        "judgment": "对",
        "before": {"gained": [], "lost": [],
                   "prompt_not_hit_counts": True},
        "after": {"gained": [], "lost": [],
                  "prompt_not_hit_counts": True},
    },
    "A4": {
        "judgment": "错",
        "before": {
            "formula": {"C": -2, "H": -4}, "c_ox": 1.0,
            "prompt_principal_minus_substrate": False,
            "prompt_excludes_water_and_coproducts": False,
            "prompt_not_balanced_net_reaction": False},
        "after": {
            "formula": {"C": -2, "H": -4}, "c_ox": 1.0,
            "prompt_principal_minus_substrate": True,
            "prompt_excludes_water_and_coproducts": True,
            "prompt_not_balanced_net_reaction": True},
    },
    "A5": {
        "judgment": "对",
        "before": {"cannizzaro_delta": -2.0,
                   "prompt_scope_principal": True,
                   "prompt_not_redox_balance_proof": True},
        "after": {"cannizzaro_delta": -2.0,
                  "prompt_scope_principal": True,
                  "prompt_not_redox_balance_proof": True},
    },
    "A6": {
        "judgment": "对",
        "before": {"absent": "unknown", "empty": [],
                   "prompt_unknown_not_negative": True},
        "after": {"absent": "unknown", "empty": [],
                  "prompt_unknown_not_negative": True},
    },
    "A7": {
        "judgment": "对",
        "before": {"n_rows": 3, "coefficients": ["1", "1", "unknown"],
                   "keys": ["coefficient", "role", "side", "smiles"]},
        "after": {"n_rows": 3, "coefficients": ["1", "1", "unknown"],
                  "keys": ["coefficient", "role", "side", "smiles"]},
    },
    "B1": {
        "judgment": "错",
        "before": {
            "bad": {"carbonate": 2, "bicarbonate": 2, "carbamate": 1,
                    "carbonic_acid": 2, "carbamic_acid": 1,
                    "methyl_carbonate": 1},
            "good": {"acetic_acid": 1, "acetate": 1,
                     "formic_acid": 1, "formate": 1}},
        "after": {
            "bad": {"carbonate": 0, "bicarbonate": 0, "carbamate": 0,
                    "carbonic_acid": 0, "carbamic_acid": 0,
                    "methyl_carbonate": 0},
            "good": {"acetic_acid": 1, "acetate": 1,
                     "formic_acid": 1, "formate": 1}},
    },
    "B2": {
        "judgment": "错",
        "before": {
            "bad": {"thioacetamide": 1, "amidine": 1, "guanidine": 2,
                    "thiourea": 2, "n_methylthioacetamide": 1,
                    "creatine": 2},
            "good": {"ethylamine": 1, "ethylammonium": 1,
                     "trimethylamine": 1, "n_methylpyrrolidine": 1}},
        "after": {
            "bad": {"thioacetamide": 0, "amidine": 0, "guanidine": 0,
                    "thiourea": 0, "n_methylthioacetamide": 0,
                    "creatine": 0},
            "good": {"ethylamine": 1, "ethylammonium": 1,
                     "trimethylamine": 1, "n_methylpyrrolidine": 1}},
    },
    "B3": {
        "judgment": "对",
        "before": {
            "pairs": {"primary_neutral": 1, "primary_charged": 1,
                      "secondary_charged": 1, "tertiary_neutral": 1,
                      "tertiary_charged": 1},
            "negatives": {"pyridine": 0, "pyrrole": 0, "indole": 0,
                          "imidazole": 0, "hydroxylamine": 0,
                          "hydrazine": 0, "trimethylamine_n_oxide": 0,
                          "pyridine_n_oxide": 0}},
        "after": {
            "pairs": {"primary_neutral": 1, "primary_charged": 1,
                      "secondary_charged": 1, "tertiary_neutral": 1,
                      "tertiary_charged": 1},
            "negatives": {"pyridine": 0, "pyrrole": 0, "indole": 0,
                          "imidazole": 0, "hydroxylamine": 0,
                          "hydrazine": 0, "trimethylamine_n_oxide": 0,
                          "pyridine_n_oxide": 0}},
    },
    "B4": {
        "judgment": "对",
        "before": {"amine_hits": 0, "class_hits": {}},
        "after": {"amine_hits": 0, "class_hits": {}},
    },
    "B5": {
        "judgment": "错",
        "before": {
            "chloronium_halide_cl": 3, "iodonium_halide_i": 2,
            "glycerol_hydroxyl_oh": 3,
            "prompt_defines_n_hits": False,
            "prompt_distinguishes_class_delta": False},
        "after": {
            "chloronium_halide_cl": 3, "iodonium_halide_i": 2,
            "glycerol_hydroxyl_oh": 3,
            "prompt_defines_n_hits": True,
            "prompt_distinguishes_class_delta": True},
    },
    "B6": {
        "judgment": "错",
        "before": {
            "phosphocholine": {},
            "choline_amine_hits": 0,
            "heteroarene_arene_ring": {"pyridine": 0, "imidazole": 0,
                                       "furan": 0, "thiophene": 0},
            "prompt_table_not_exhaustive": False,
            "prompt_unlisted_not_absent": False,
            "prompt_names_quaternary_ammonium": False,
            "prompt_names_heteroarene": False},
        "after": {
            "phosphocholine": {},
            "choline_amine_hits": 0,
            "heteroarene_arene_ring": {"pyridine": 0, "imidazole": 0,
                                       "furan": 0, "thiophene": 0},
            "prompt_table_not_exhaustive": True,
            "prompt_unlisted_not_absent": True,
            "prompt_names_quaternary_ammonium": True,
            "prompt_names_heteroarene": True},
    },
    "C1": {
        "judgment": "对",
        "before": {"methane": -4.0, "methanol": -2.0, "ethanol": -2.0,
                   "acetaldehyde": -1.0, "acetic_acid": 0.0,
                   "acetate": 0.0, "carbon_dioxide": 4.0,
                   "formic_acid": 2.0, "formate": 2.0},
        "after": {"methane": -4.0, "methanol": -2.0, "ethanol": -2.0,
                  "acetaldehyde": -1.0, "acetic_acid": 0.0,
                  "acetate": 0.0, "carbon_dioxide": 4.0,
                  "formic_acid": 2.0, "formate": 2.0},
    },
    "C2": {
        "judgment": "错",
        "before": {"dimethyl_peroxide": -1.0, "methyl_hydroperoxide": 0.0,
                   "diethyl_peroxide": -1.5,
                   "peroxyacetic_acid": 1.0,
                   "methyl_perchlorate": 6.0,
                   "hydrogen_peroxide": None, "methylamine_domain": None,
                   "closed_shell_ethanol": -2.0},
        "after": {"dimethyl_peroxide": None, "methyl_hydroperoxide": None,
                  "diethyl_peroxide": None, "peroxyacetic_acid": None,
                  "methyl_perchlorate": None,
                  "hydrogen_peroxide": None, "methylamine_domain": None,
                  "closed_shell_ethanol": -2.0},
    },
    "C3": {
        "judgment": "错",
        "before": {"oxonium_zwitterion": -0.5, "methoxide": -2.0,
                   "iodonium": -2.0, "trimethylchloronium": -2.3333,
                   "glycine_zwitterion": None},
        "after": {"oxonium_zwitterion": -0.5, "methoxide": -2.0,
                  "iodonium": -2.0, "trimethylchloronium": None,
                  "glycine_zwitterion": None},
    },
    "C4": {
        "judgment": "错",
        "before": {"methyl_radical": -3.0, "carbene": -2.0,
                   "phenoxyl_radical": -0.5},
        "after": {"methyl_radical": None, "carbene": None,
                  "phenoxyl_radical": None},
    },
    "C5": {
        "judgment": "错",
        "before": {"ethanol_to_glycerol": 1.3333,
                   "ethyl_acetate_hydrolysis": 1.0,
                   "cannizzaro": -2.0,
                   "prompt_different_carbon_set": False,
                   "prompt_nonzero_not_oxidation_event": False,
                   "prompt_redox_equivalents_coproducts": False},
        "after": {"ethanol_to_glycerol": 1.3333,
                  "ethyl_acetate_hydrolysis": 1.0,
                  "cannizzaro": -2.0,
                  "prompt_different_carbon_set": True,
                  "prompt_nonzero_not_oxidation_event": True,
                  "prompt_redox_equivalents_coproducts": True},
    },
    "C6": {
        "judgment": "对",
        "before": {"same_formula": {}, "same_c_ox": 0.0,
                   "unknowns": ["unknown", "unknown", "unknown"]},
        "after": {"same_formula": {}, "same_c_ox": 0.0,
                  "unknowns": ["unknown", "unknown", "unknown"]},
    },
}

JUDGMENT_ORDER = ["A1", "A2", "A3", "A4", "A5", "A6", "A7",
                  "B1", "B2", "B3", "B4", "B5", "B6",
                  "C1", "C2", "C3", "C4", "C5", "C6"]


def test_review_matrix_has_19_items_with_9_ok_10_fixed() -> None:
    assert list(BEFORE_AFTER) == JUDGMENT_ORDER
    ok = [key for key, row in BEFORE_AFTER.items()
          if row["judgment"] == "对"]
    fixed = [key for key, row in BEFORE_AFTER.items()
             if row["judgment"] == "错"]
    assert len(ok) == 9 and len(fixed) == 10
    # 9 条「对」before == after（不回归）；10 条「错」before != after
    for key in ok:
        assert BEFORE_AFTER[key]["before"] == BEFORE_AFTER[key]["after"]
    for key in fixed:
        assert BEFORE_AFTER[key]["before"] != BEFORE_AFTER[key]["after"]


@pytest.mark.parametrize("item", JUDGMENT_ORDER)
def test_review_item_after_matches_expected(item: str) -> None:
    expected = BEFORE_AFTER[item]["after"]
    assert _observe(item) == expected


# ---------------------------------------------------------------- P1/P2 negatives


def test_legal_carboxylic_acids_are_not_regressed() -> None:
    """合法羧酸/羧酸根正控（P1 不得把真羧酸也排掉）。"""
    expected = {
        "acetic_acid": "CC(=O)O",
        "acetate": "CC(=O)[O-]",
        "benzoic_acid": "O=C(O)c1ccccc1",
        "formic_acid": "C(=O)O",
        "formate": "C(=O)[O-]",
        "oxalic_acid": "O=C(O)C(=O)O",
        "acetoacetic_acid": "CC(=O)CC(=O)O",
        "glycine_zwitterion": "[NH3+]CC(=O)[O-]",
        "explicit_h_formic_acid": "[H]C(=O)O",
    }
    hits = {name: _hits(smiles).get("carboxylic_acid", 0)
            for name, smiles in expected.items()}
    assert hits == {
        "acetic_acid": 1, "acetate": 1, "benzoic_acid": 1,
        "formic_acid": 1, "formate": 1, "oxalic_acid": 2,
        "acetoacetic_acid": 1, "glycine_zwitterion": 1,
        "explicit_h_formic_acid": 1,
    }


def test_legal_amines_are_not_regressed() -> None:
    """合法伯/仲/叔胺（含质子化）正控；酰胺/磺酰胺/磷酰胺仍排除。"""
    positives = {
        "ethylamine": ("CCN", "amine_primary", 1),
        "ethylammonium": ("CC[NH3+]", "amine_primary", 1),
        "diethylamine": ("CCNCC", "amine_secondary", 1),
        "diethylammonium": ("CC[NH2+]CC", "amine_secondary", 1),
        "trimethylamine": ("CN(C)C", "amine_tertiary", 1),
        "trimethylammonium": ("C[NH+](C)C", "amine_tertiary", 1),
        "n_methylpyrrolidine": ("CN1CCCC1", "amine_tertiary", 1),
        "aniline": ("Nc1ccccc1", "amine_primary", 1),
    }
    for name, (smiles, cls, count) in positives.items():
        assert _hits(smiles).get(cls, 0) == count, name
    for name, smiles in {
            "acetamide": "CC(=O)N",
            "n_ethylacetamide": "CC(=O)NCC",
            "urea": "NC(=O)N",
            "methanesulfonamide": "CS(=O)(=O)NC",
            "phosphoramide": "CP(=O)(N)N",
            "quaternary_ammonium": "C[N+](C)(C)C",
    }.items():
        assert _amine_total(smiles) == 0, name


def test_carboxylic_acid_and_amine_fixes_do_not_cross_talk() -> None:
    """P1/P2 组合：creatine 只保留真羧基，胍基 N 不再计胺。"""
    hits = _hits("CN(CC(=O)O)C(=N)N")
    assert hits.get("carboxylic_acid", 0) == 1
    assert hits.get("amine_primary", 0) == 0
    assert hits.get("amine_secondary", 0) == 0
    assert hits.get("amine_tertiary", 0) == 0


# ---------------------------------------------------------------- P6/P7 guards


def test_c_ox_unknown_reasons_are_precise() -> None:
    """P6/P7：unknown 只落在具体不可靠结构上，且原因码可区分。"""
    expected = {
        "COOC": "peroxide_oo_bond",
        "COO": "peroxide_oo_bond",
        "CCOOCC": "peroxide_oo_bond",
        "CC(=O)OO": "peroxide_oo_bond",
        "COCl(=O)(=O)=O": "hypervalent_halogen",
        "C[Cl+](C)C": "hypervalent_halogen",
        "COCl": "hypervalent_halogen",
        "[CH3]": "open_shell",
        "[CH2]": "open_shell",
        "[O]c1ccccc1": "open_shell",
        "OO": "no_carbon",
        "CN": "element_out_of_domain",
        "CS": "element_out_of_domain",
        "[NH3+]CC(=O)[O-]": "element_out_of_domain",
    }
    for smiles, reason in expected.items():
        value, actual_reason = _detail(smiles)
        assert value is None, smiles
        assert actual_reason == reason, smiles


def test_c_ox_unknown_does_not_spill_to_closed_shell_domain() -> None:
    """闭壳层正常分子 C_ox 仍正确；守卫不外溢。"""
    expected = {
        "C": -4.0, "CO": -2.0, "CCO": -2.0, "CC=O": -1.0,
        "CC(=O)O": 0.0, "CC(=O)[O-]": 0.0, "O=C=O": 4.0,
        "C(=O)O": 2.0, "C(=O)[O-]": 2.0,
        "CCl": -2.0, "CBr": -2.0, "CI": -2.0, "CF": -2.0,
        "ClC(Cl)Cl": 2.0, "ClC(Cl)(Cl)Cl": 4.0, "FC(F)(F)F": 4.0,
        "CC(=O)OCC": -1.0, "OCC(O)CO": -0.6667,
        "c1ccccc1": -1.0,
        # 带电但卤素仍为 -1 / 总电荷公式成立的正控
        "C[I+]C": -2.0, "C[O-]": -2.0,
        "C[O+](C)CC(=O)[O-]": -0.5,
    }
    for smiles, value in expected.items():
        actual, reason = _detail(smiles)
        assert actual == value, smiles
        assert reason == "computed", smiles


def test_iodonium_not_over_rejected_but_chloronium_is() -> None:
    """二配位碘鎓 I 仍为 -1 ⇒ 数字正确；三配位氯鎓不是 -1 ⇒ unknown。"""
    iodonium, reason = _detail("C[I+]C")
    assert iodonium == -2.0 and reason == "computed"
    chloronium, reason = _detail("C[Cl+](C)C")
    assert chloronium is None and reason == "hypervalent_halogen"


# ---------------------------------------------------------------- prompt/contract


def test_prompt_identities_and_shared_v2_prompt() -> None:
    """v1 不变；v2 旧→新 SHA；两臂共用同一 v2 prompt。"""
    assert PROPOSALS_PROMPT_VERSION == V1_PROMPT_SHA256
    assert hashlib.sha256(_prompt().encode("utf-8")).hexdigest() == \
        PROPOSALS_PROMPT_VERSION_V2
    assert PROPOSALS_PROMPT_VERSION_V2 == NEW_V2_PROMPT_SHA256
    assert PROPOSALS_PROMPT_VERSION_V2 != OLD_V2_PROMPT_SHA256
    assert PROPOSALS_PROMPT_VERSION_V2 != PROPOSALS_PROMPT_VERSION
    # v2 仍只替换证据段：v1 的规则/示例段没有进入 v2 的字节变化
    assert "functional-group class delta" in _prompt()
    assert "partial charges" not in _prompt()


def test_p3_n_hits_definition_in_prompt() -> None:
    prompt = _prompt()
    assert "n_hits is the number of distinct matched atom tuples" in prompt
    assert "may exceed the number of functional groups" in prompt
    assert "The substrate n_hits and the functional-group class delta" \
        in prompt
    assert "not hit-count changes" in prompt


def test_p4_unlisted_class_disclosure_in_prompt() -> None:
    prompt = _prompt()
    assert "the functional-group class table is not exhaustive" in prompt
    assert "not evidence that the group is absent" in prompt
    assert "quaternary ammonium" in prompt
    assert "heteroarene" in prompt
    assert "Treat missing classes as unmodeled" in prompt


def test_p5_delta_semantics_disclosure_in_prompt() -> None:
    prompt = _prompt()
    assert "designated principal product minus the substrate" in prompt
    assert "It excludes co-substrates, water, and coproducts" in prompt
    assert "not a balanced net reaction" in prompt
    assert "different carbon set" in prompt
    assert "does not by itself show an oxidation or reduction event" \
        in prompt
    assert "redox equivalents may be carried by coproducts" in prompt


def test_unknown_reason_taxonomy_in_prompt() -> None:
    prompt = _prompt()
    assert "an O-O bond" in prompt
    assert "a hypervalent halogen" in prompt
    assert "an open-shell or radical species" in prompt
    assert "unknown is not zero" in prompt


def test_n1_n2_n5_prompt_wording() -> None:
    """二轮复审 N1/N2/N5：质子化容忍、n_hits 不反向低估、render_ok 语义。"""
    prompt = _prompt()
    assert "may exceed the number of functional groups" in prompt
    assert "protonation-tolerant" in prompt
    assert "a protonation change alone is not a class gain or loss" in prompt
    assert ("computed on the substrate and on the entry's designated "
            "principal product") in prompt
    assert "substrate_render_ok" in prompt
    assert "render failure rather than a true zero-hit structure" in prompt


def test_optional_disclosures_adopted() -> None:
    """复审 §3 的非阻断建议：空 dict 语义 / requirements 非权威 / delta 方向。"""
    prompt = _prompt()
    assert "An empty formula object means no net element-count change" \
        in prompt
    assert "requirement_missing is not evaluated" in prompt
    assert "designated principal product minus the substrate" in prompt


def test_no_schema_or_field_structure_change() -> None:
    """硬约束：不新增 schema/descriptor 版本号，不新增字段。"""
    assert ce.CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2 == "candidate-evidence-3"
    assert ce.CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION_V2 == \
        "candidate-evidence-descr-3"
    evidence = ce.candidate_evidence_payload_v2(
        spec={"product_smiles": "CC=O"}, prepared=None,
        substrate_facts=ce.substrate_facts_v2("CCO"))
    assert set(evidence) == {
        "edit_summary", "participants", "alignment_quality",
        "conditions_and_scope", "functional_group_delta", "product_delta"}
    assert set(evidence["product_delta"]) == {
        "scope", "formula", "carbon_oxidation_state"}
    substrate = ce.substrate_evidence_payload_v2("CCO")
    assert set(substrate) == {
        "descriptor_version", "substrate_render_ok", "functional_groups",
        "representation_fidelity", "condition_keys_known"}


def test_v1_zero_drift_smoke() -> None:
    """v1 行为不变：v1 羧酸仍不认羧酸根；v1 表未改。"""
    v1_classes = {row["class"] for row in ce.substrate_evidence_payload(
        "CC(=O)[O-]")["functional_groups"]}
    assert "carboxylic_acid" not in v1_classes
    assert dict(ce._FUNCTIONAL_GROUP_TABLE)["carboxylic_acid"] == \
        "[CX3](=O)[OX2H1]"
    assert dict(ce._FUNCTIONAL_GROUP_TABLE)["amine_primary"] == \
        "[NX3;H2;!$(NC=[OX1])][#6]"
    # v2 表仍是 21 类，顺序/类名未增删
    assert [name for name, _ in ce._FUNCTIONAL_GROUP_TABLE_V2] == [
        name for name, _ in ce._FUNCTIONAL_GROUP_TABLE]


def test_only_the_four_protonation_smarts_differ_from_v1() -> None:
    """复审前提：v2 只改 4 条；其余 17 条与 v1 逐字相同。"""
    changed = {"carboxylic_acid", "amine_primary", "amine_secondary",
               "amine_tertiary"}
    v1 = dict(ce._FUNCTIONAL_GROUP_TABLE)
    v2 = dict(ce._FUNCTIONAL_GROUP_TABLE_V2)
    assert set(v1) == set(v2)
    assert {name for name in v2 if v2[name] != v1[name]} == changed
    for name in set(v2) - changed:
        assert v2[name] == v1[name], name
