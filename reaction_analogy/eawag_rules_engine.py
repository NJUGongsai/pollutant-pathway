#!/usr/bin/env python3
"""Engine B (second batch): 49 EAWAG SMIRKS rules.

Task §4.2.  The 49 cleaned, rxnmapper-atom-mapped, roundtrip-verified SMIRKS
in ``rules_new_clean.jsonl`` are applied as a SECOND batch of engine B
alongside the 286 enviPath rules.  Crucially the rules are applied with
``RunReactants`` (NOT graph-edit) — they generate new atoms, and the v2
graph-edit engine could not materialise those (v2 lesson, task §8).

Candidates are emitted with ``source="envipath"`` so the existing
substring-routing logic (in ``compute_v31_case_features`` grouping,
``_belongs`` in the predictors, and the trainer's per-source mining) routes
them into the envipath per-source ranker UNCHANGED — zero matching-code
edits.  Provenance is preserved in the separate ``rule_family="eawag_rule"``
field (auditable, task §10.4).  This is the implementer choice allowed by
§4.2 ("fold into envipath ranker"), documented in the REPORT.

Cleaning mirrors engine B in ``train_bbd_v31_ranker._process_educt_raw``
(lines 124-185): substruct-match gate → ``RunReactants`` → strip atom maps
→ ``SanitizeMol`` → wildcard-atom reject → max-fragment → parent filter
(``stereo_blind == parent``) → dedup.  Ion/cofactor sink-marking is applied
later by the predictor's filter step (same as every other source).

Answer-key isolation: this file NEVER reads the answer key.
"""
from __future__ import annotations

import json
import os
import sys

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem

RDLogger.DisableLog("rdApp.*")

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

RULES_PATH = os.path.join(
    "/Volumes/CC/Enzyme_Agent/depending",
    "reaction_analogy/data/bbd_expand/rules_new_clean.jsonl",
)


def _sb(smi: str) -> str | None:
    """Stereo-blind canonical SMILES (isomericSmiles=False)."""
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def _strip_maps(mol: Chem.Mol) -> Chem.Mol:
    """Return an RWMol copy with all atom maps zeroed."""
    rw = Chem.RWMol(mol)
    for a in rw.GetAtoms():
        a.SetAtomMapNum(0)
    return rw.GetMol()


def load_eawag_rules(path: str = RULES_PATH) -> list[dict]:
    """Parse the 49 EAWAG SMIRKS rules into pre-parsed reaction objects.

    Returns a list of dicts with the SAME shape as enviPath rules
    (``{tid, rxn, rt, mapped_idx, reactions_count, n_mapped}``) plus
    ``smirks``, ``confidence`` and ``rule_family``.  Fail-closed:
    unparseable or multi-reactant rules are skipped and counted.
    """
    rules: list[dict] = []
    skip = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            smirks = d.get("smirks", "")
            tid = f"{d.get('btid', '')}#{d.get('reac_id', '')}"
            rxn = AllChem.ReactionFromSmarts(smirks)
            if rxn is None:
                skip += 1
                continue
            if rxn.GetNumReactantTemplates() != 1:
                skip += 1
                continue
            rt = rxn.GetReactantTemplate(0)
            mapped_idx = [a.GetIdx() for a in rt.GetAtoms()
                          if a.GetAtomMapNum() > 0]
            if not mapped_idx:
                skip += 1
                continue
            rules.append({
                "tid": tid,
                "rxn": rxn,
                "rt": rt,
                "mapped_idx": mapped_idx,
                "reactions_count": 1,  # each EAWAG rule is one observed rxn
                "n_mapped": len(mapped_idx),
                "smirks": smirks,
                "confidence": d.get("confidence"),
                "rule_family": "eawag_rule",
            })
    return rules


def apply_eawag_rules(smi: str, rules: list[dict],
                      parent_sb: str | None = None) -> list[dict]:
    """Apply all EAWAG rules to *smi*; return cleaned candidate dicts.

    Each returned dict has the engine-B candidate shape (``source="envipath"``,
    ``rule_family="eawag_rule"``) plus the ranker feature inputs.  Cleaning
    mirrors ``train_bbd_v31_ranker._process_educt_raw`` engine-B block.
    """
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return []
    if parent_sb is None:
        parent_sb = _sb(smi)

    cands: dict[str, dict] = {}  # max_smi -> candidate dict

    for rule in rules:
        rt = rule["rt"]
        rxn = rule["rxn"]
        try:
            matches = mol.GetSubstructMatches(rt, maxMatches=1000)
        except Exception:
            continue
        if not matches:
            continue
        try:
            outs = rxn.RunReactants([mol])
        except Exception:
            continue
        if not outs:
            continue
        for prod_tuple in outs:
            clean_mols = []
            bad = False
            for p in prod_tuple:
                p2 = _strip_maps(p)
                try:
                    Chem.SanitizeMol(p2)
                except Exception:
                    bad = True
                    break
                # wildcard-atom reject (P4 / P4.1 病灶 — rules must not emit '*')
                if any(a.GetAtomicNum() == 0 for a in p2.GetAtoms()):
                    bad = True
                    break
                clean_mols.append(p2)
            if bad:
                continue
            all_frags = []
            for cm in clean_mols:
                all_frags.extend(Chem.GetMolFrags(cm, asMols=True))
            if not all_frags:
                continue
            frag_scored = [(f.GetNumAtoms(),
                            Chem.MolToSmiles(f, isomericSmiles=True), f)
                           for f in all_frags]
            frag_scored.sort(key=lambda x: (-x[0], x[1]))
            max_smi = frag_scored[0][1]
            # parent filter: product == parent (no transformation) → skip
            if _sb(max_smi) == parent_sb:
                continue
            full_smi = ".".join(sorted(s for _, s, _ in frag_scored))
            if max_smi not in cands:
                cands[max_smi] = {
                    "product_smiles": max_smi,
                    "product_smiles_full": full_smi,
                    "source": "envipath",
                    "rule_family": "eawag_rule",
                    "template_freq": 0,
                    "reactions_count": rule["reactions_count"],
                    "pattern_atom_count": rule["n_mapped"],
                    "n_evidence": 0,
                    "max_tanimoto": 0.0,
                    "mean_tanimoto": 0.0,
                    "donor_exact_match": False,
                    "confidence": rule.get("confidence"),
                    "smirks": rule["smirks"],
                }
            else:
                c = cands[max_smi]
                if rule["reactions_count"] > c["reactions_count"]:
                    c["reactions_count"] = rule["reactions_count"]
                if rule["n_mapped"] > c["pattern_atom_count"]:
                    c["pattern_atom_count"] = rule["n_mapped"]

    return list(cands.values())


def _selftest_c0946() -> int:
    """c0946 (branched dodecylbenzene sulfonate) desulfonation/hydroxylation.

    Rule must emit the hydroxylated product ``CCCCCCCCCCCCc1ccc(O)cc1``
    (Branched-chain dodecyl-4-hydroxy-benzene, EAWAG c0947 / r1079).
    """
    parent = "CCCCCCCCCCCCc1ccc(cc1)S([O-])(=O)=O"
    expected_sb = _sb("CCCCCCCCCCCCc1ccc(O)cc1")
    rules = load_eawag_rules()
    cands = apply_eawag_rules(parent, rules, _sb(parent))
    print(f"  loaded {len(rules)} rules; c0946 produced {len(cands)} candidates")
    for c in cands[:8]:
        print(f"    {c['product_smiles']}  (rule_family={c['rule_family']}, "
              f"pac={c['pattern_atom_count']})")
    hits = [c for c in cands if _sb(c["product_smiles"]) == expected_sb]
    assert hits, "FAIL: c0946 rule did not emit the hydroxylated product"
    # every candidate must be envipath-family, no wildcards, != parent
    for c in cands:
        assert c["source"] == "envipath"
        assert c["rule_family"] == "eawag_rule"
        assert "*" not in c["product_smiles"]
        assert _sb(c["product_smiles"]) != _sb(parent)
    print(f"  PASS: c0946 hydroxylation product present ({len(hits)} hit)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest_c0946())
