"""RA-RREF — Reaction-class *relevance* reranker for the enviPath track.

Purpose (Route A "replace alphabetical" task): the [H]-fix pool
(`data/hfix/candidates_hfix.json`) floods the candidate set with enviPath-rule
products, but it stores plain SMILES with **no tier / reaction-class
provenance**, so the old M4 ranker degrades to SMILES alphabetical order and
collapses (Hit@1=0/83). This module rebuilds, from frozen read-only artifacts,
the two signals the old pool carried implicitly and one new, chemistry-meaningful
one:

  1. **tier**        — a candidate produced by >=1 enviPath SMARTS rule is
                       `envipath` and always ranks above the legacy RHEA
                       donor-similarity residue (`rhea`).  (Restores the M4
                       tier-first contract that the flat hfix pool dropped.)
  2. **specificity** — inverse-frequency of the producing rule's reactant SMARTS
                       across the 83 blind parents (the public query set, NOT the
                       answer key).  A rule that matches only this compound is a
                       *characteristic* transformation; a rule that matches 45
                       compounds (aromatic C-H hydroxylation, methyl->alcohol,
                       alcohol->aldehyde) is generic noise.  This replaces the
                       alphabetical key inside the enviPath tier.
  3. **relevance**   — hand-curated chemistry prior (the "人工级 prior table"):
                       which reaction family is most likely to be X's first
                       degradation step, keyed by the EAWAG-BBD rule description
                       (dehalogenation / ring cleavage / hydrolysis / aromatic
                       mono-oxygenation / decarboxylation / S,N-oxidation /
                       deamination / aliphatic hydroxylation / alcohol-aldehyde
                       oxidation / reduction).
  4. **site**        — M3 site-compatibility penalty carried from the frozen
                       `sitecompat_v1` per-rule verdicts (ambiguous multi-site or
                       incompatible transforms are nudged down; fail-closed —
                       incompatible products were already dropped at pool build).

Score (enviPath tier only):
    score(rule)  = w_rel*relevance(rule) + w_spec*specificity(rule) + w_site*site(rule)
    score(y)     = max over producing rules r of score(r)     (y = candidate)
    order        = tier desc -> score desc -> candidate_smiles asc
    TOP_K        = 10 strict.

Answer isolation: this module NEVER references the restricted accepted-products
file.  Its only "label-adjacent" artefact-free inputs are the public blind-parent
CSV, the enviPath template library (read-only reaction_v3), the hfix pool, the
BBD rule-description table (bbd_expand), lineage fragments, and the frozen
sitecompat_v1 verdicts.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import re
from typing import Dict, List, Optional, Tuple

from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

# ---------------------------------------------------------------------------
# pre-registered constants (see reports/RA_RREF_RANKING_KEY.md)
# ---------------------------------------------------------------------------

RANKING_KEY = (
    "RREF_V1: order = (tier desc) -> (score desc) -> (candidate_smiles asc); "
    "tier = 'envipath' iff candidate produced by >=1 enviPath SMARTS rule else "
    "'rhea'; score = max over producing rules r of "
    "(w_rel*relevance(r) + w_spec*specificity(r) + w_site*site(r)); "
    "relevance = hand chemistry-prior family priority; "
    "specificity = log2(83 / n_parents_matching(r)); "
    "site = sitecompat_v1 per-rule penalty (0/-0.25/-1.0); "
    "TOP_K = 10 strict."
)

TOP_K = 10
TIER_ENVIPATH = "envipath"
TIER_RHEA = "rhea"
STATUS_RANKED = "ranked"
ABSTAIN_NO_CANDIDATE = "no_candidate"

W_REL = 0.20
W_SPEC = 1.00
W_SITE = 0.10

N_PARENTS = 83  # fixed; blind-parent set is the public frozen CSV

# ---------------------------------------------------------------------------
# frozen read-only input paths (never written)
# ---------------------------------------------------------------------------

ROOT = "/Volumes/CC/Enzyme_Agent/depending"
HFIX_POOL = os.path.join(ROOT, "data/hfix/candidates_hfix.json")
HFIX_TEMPLATES = os.path.join(ROOT, "data/hfix/templates_implicitH.jsonl")
ENVIPATH_TSV = os.path.join(ROOT, "reaction_v3/data/lib_envipath/templates.tsv.gz")
ENVIPATH_SUBS = os.path.join(ROOT, "reaction_v3/data/lib_envipath/source_substrates.json")
PARENTS_CSV = os.path.join(
    ROOT, "demov3/data/bbd83_blind_inputs/KNOWN_PATHWAY_POLLUTANT_BLIND_PARENT_INPUTS_V0_2.csv"
)
BBDRULES_JSON = os.path.join(ROOT, "reaction_analogy/data/bbd_expand/parsed/rules.json")
SITECOMPAT_REPORT = os.path.join(ROOT, "reaction_analogy/data/sitecompat_v1/site_report.json")

TEMPLATES_REF = "data/hfix/templates_implicitH.jsonl"
BBDRULES_REF = "data/bbd_expand/parsed/rules.json"
SITECOMPAT_REF = "data/sitecompat_v1/site_report.json"

# ---------------------------------------------------------------------------
# chemistry prior (人工级 prior table) — BT rule -> (family, priority)
# ---------------------------------------------------------------------------
# Prior encodes "given the trigger is present, how likely is this family to be
# the FIRST degradation step" for aerobic biodegradation (EAWAG-BBD ontology).
# Higher = more likely canonical first step.  Rules not listed default to
# ("other", 0.0).
# ---------------------------------------------------------------------------

FAMILY_PRIORITY = {
    "dehalogenation": 2.0,
    "ring_cleavage": 1.5,
    "hydrolysis": 1.5,
    "monooxygen_aromatic": 1.0,
    "deamination": 1.0,
    "decarboxylation": 0.5,
    "s_n_oxidation": 0.5,
    "dealkylation": 0.5,
    "epoxidation": 0.5,
    "aliphatic_hydroxylation": 0.0,
    "alcohol_aldehyde_oxidation": 0.0,
    "other": 0.0,
    "reduction": -1.0,
}

# keyed by the BBD rule id `btXXXX` (pattern-insensitive: the class)
RULE_FAMILY: Dict[str, str] = {
    "bt0001": "alcohol_aldehyde_oxidation",
    "bt0002": "alcohol_aldehyde_oxidation",
    "bt0003": "alcohol_aldehyde_oxidation",
    "bt0005": "monooxygen_aromatic",
    "bt0011": "monooxygen_aromatic",
    "bt0012": "monooxygen_aromatic",
    "bt0013": "monooxygen_aromatic",
    "bt0014": "monooxygen_aromatic",
    "bt0020": "other",
    "bt0021": "epoxidation",
    "bt0022": "dehalogenation",
    "bt0023": "hydrolysis",
    "bt0024": "hydrolysis",
    "bt0027": "hydrolysis",
    "bt0028": "hydrolysis",
    "bt0029": "dehalogenation",
    "bt0030": "hydrolysis",
    "bt0031": "hydrolysis",
    "bt0033": "reduction",
    "bt0034": "reduction",
    "bt0035": "reduction",
    "bt0036": "aliphatic_hydroxylation",
    "bt0037": "reduction",
    "bt0042": "reduction",
    "bt0049": "epoxidation",
    "bt0050": "hydrolysis",
    "bt0051": "decarboxylation",
    "bt0055": "decarboxylation",
    "bt0060": "decarboxylation",
    "bt0061": "dealkylation",
    "bt0063": "deamination",
    "bt0064": "monooxygen_aromatic",
    "bt0065": "deamination",
    "bt0066": "dehalogenation",
    "bt0067": "hydrolysis",
    "bt0069": "dehalogenation",
    "bt0070": "reduction",
    "bt0071": "other",
    "bt0072": "dehalogenation",
    "bt0073": "aliphatic_hydroxylation",
    "bt0078": "reduction",
    "bt0079": "reduction",
    "bt0080": "reduction",
    "bt0103": "hydrolysis",
    "bt0104": "hydrolysis",
    "bt0128": "hydrolysis",
    "bt0143": "hydrolysis",
    "bt0144": "hydrolysis",
    "bt0147": "hydrolysis",
    "bt0156": "ring_cleavage",
    "bt0158": "hydrolysis",
    "bt0162": "s_n_oxidation",
    "bt0192": "reduction",
    "bt0193": "s_n_oxidation",
    "bt0199": "deamination",
    "bt0202": "other",
    "bt0208": "other",
    "bt0209": "other",
    "bt0212": "other",
    "bt0216": "other",
    "bt0218": "other",
    "bt0230": "other",
    "bt0241": "aliphatic_hydroxylation",
    "bt0242": "aliphatic_hydroxylation",
    "bt0243": "dealkylation",
    "bt0254": "ring_cleavage",
    "bt0259": "hydrolysis",
    "bt0260": "reduction",
    "bt0268": "other",
    "bt0269": "other",
    "bt0270": "other",
    "bt0275": "dehalogenation",
    "bt0291": "reduction",
    "bt0298": "hydrolysis",
    "bt0306": "other",
    "bt0318": "hydrolysis",
    "bt0330": "dehalogenation",
    "bt0332": "aliphatic_hydroxylation",
    "bt0333": "aliphatic_hydroxylation",
    "bt0334": "aliphatic_hydroxylation",
    "bt0339": "dealkylation",
    "bt0340": "ring_cleavage",
    "bt0342": "ring_cleavage",
    "bt0344": "ring_cleavage",
    "bt0349": "decarboxylation",
    "bt0351": "ring_cleavage",
    "bt0353": "monooxygen_aromatic",
    "bt0357": "ring_cleavage",
    "bt0358": "ring_cleavage",
    "bt0359": "dehalogenation",
    "bt0361": "hydrolysis",
    "bt0364": "ring_cleavage",
    "bt0366": "monooxygen_aromatic",
    "bt0367": "monooxygen_aromatic",
    "bt0374": "ring_cleavage",
    "bt0375": "monooxygen_aromatic",
    "bt0379": "dehalogenation",
    "bt0383": "ring_cleavage",
    "bt0389": "hydrolysis",
    "bt0391": "hydrolysis",
    "bt0397": "reduction",
    "bt0399": "epoxidation",
    "bt0404": "ring_cleavage",
    "bt0407": "s_n_oxidation",
    "bt0416": "monooxygen_aromatic",
    "bt0421": "hydrolysis",
    "bt0425": "ring_cleavage",
    "bt0430": "hydrolysis",
    "bt0432": "hydrolysis",
    "bt0436": "dealkylation",
    "bt0438": "monooxygen_aromatic",
    "bt0439": "other",
    "bt0440": "hydrolysis",
}


def family_of(bt_id: Optional[str]) -> str:
    if bt_id is None:
        return "other"
    return RULE_FAMILY.get(bt_id, "other")


def relevance_priority(bt_id: Optional[str]) -> float:
    return FAMILY_PRIORITY.get(family_of(bt_id), 0.0)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_BT_RE = re.compile(r"^bt\d+")


def bt_of(template_id: str) -> Optional[str]:
    """'envipath:bt0330-3929' -> 'bt0330'."""
    if not template_id:
        return None
    core = template_id.split(":")[-1]
    m = _BT_RE.match(core)
    return m.group(0) if m else None


def canon(smiles: str) -> Optional[str]:
    m = Chem.MolFromSmiles(smiles)
    return Chem.MolToSmiles(m) if m is not None else None


def load_parents(path: str = PARENTS_CSV) -> Dict[str, str]:
    import csv
    out = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["benchmark_case_id"]] = row["parent_smiles"]
    return out


def load_hfix_templates(path: str = HFIX_TEMPLATES) -> Dict[str, str]:
    """template_id -> reencoded_smirks (implicit-H, from the [H]-fix)."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out[d["template_id"]] = d["reencoded_smirks"]
    return out


def load_bbd_rules(path: str = BBDRULES_JSON) -> Dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_hfix_pool(path: str = HFIX_POOL) -> Dict[str, List[str]]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_reactions(templates: Dict[str, str]) -> Dict[str, object]:
    """template_id -> parsed single-reactant ReactionFromSmarts (or None)."""
    out = {}
    for tid in sorted(templates):
        r = AllChem.ReactionFromSmarts(templates[tid])
        if r is not None and r.GetNumReactantTemplates() == 1:
            out[tid] = r
    return out


def build_rule_support(reactions: Dict[str, object],
                       parents: Dict[str, str]) -> Dict[str, int]:
    """support[tid] = number of the 83 blind parents whose SMILES the rule's
    reactant SMARTS matches (>=1 for any rule that generates a candidate)."""
    support: Dict[str, int] = {}
    parent_mols = {}
    for cid, smi in parents.items():
        m = Chem.MolFromSmiles(smi)
        if m is not None:
            parent_mols[cid] = m
    for tid in sorted(reactions):
        r = reactions[tid]
        pat = r.GetReactants()[0]
        n = 0
        for m in parent_mols.values():
            if m.HasSubstructMatch(pat):
                n += 1
        support[tid] = n
    return support


def specificity(support: int) -> float:
    """log2(83/support); support>=1 guaranteed for generating rules."""
    s = max(1, int(support))
    return math.log2(N_PARENTS / s)


def load_site_verdicts(path: str = SITECOMPAT_REPORT) -> Dict[str, str]:
    """source_id -> 'incompatible' | 'ambiguous' | 'compatible' (worst verdict)."""
    with open(path, encoding="utf-8") as f:
        rep = json.load(f)
    verdicts: Dict[str, str] = {}
    for sid, v in (rep.get("per_rule_verdicts") or {}).items():
        if v.get("incompatible", 0) > 0:
            verdicts[sid] = "incompatible"
        elif v.get("ambiguous", 0) > 0:
            verdicts[sid] = "ambiguous"
        else:
            verdicts[sid] = "compatible"
    return verdicts


def site_penalty(template_id: str, verdicts: Dict[str, str]) -> float:
    v = verdicts.get(template_id, "compatible")
    if v == "incompatible":
        return -1.0
    if v == "ambiguous":
        return -0.25
    return 0.0


# ---------------------------------------------------------------------------
# provenance reconstruction (deterministic; cached by the CLI to an artefact)
# ---------------------------------------------------------------------------

def apply_rule(rxn, smiles: str, wanted: Optional[set] = None) -> set:
    """Return canonical products of one rule on one substrate.

    `wanted` (optional) restricts output to a caller-provided candidate set —
    used to reconstruct WHICH pool candidates a rule produced.
    """
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return set()
    if not m.HasSubstructMatch(rxn.GetReactants()[0]):
        return set()
    out: set = set()
    for ps in rxn.RunReactants((m,)):
        for p in ps:
            try:
                Chem.SanitizeMol(p)
                cp = Chem.MolToSmiles(p)
            except Exception:
                continue
            if wanted is None or cp in wanted:
                out.add(cp)
    return out


def reconstruct_provenance(pool: Dict[str, List[str]],
                           reactions: Dict[str, object],
                           parents: Dict[str, str]) -> Dict[str, Dict[str, List[str]]]:
    """{case_id: {candidate_smiles: [template_id, ...]}} for pool candidates
    produced by >=1 enviPath rule.  RunReactants result -> canonicalised, and
    only kept when the product is exactly present in the frozen hfix pool."""
    prov: Dict[str, Dict[str, List[str]]] = {}
    for cid in sorted(pool):
        smi = parents.get(cid)
        x = canon(smi) if smi else None
        cands = set(pool[cid])
        prod2tid: Dict[str, List[str]] = {}
        if x:
            for tid in sorted(reactions):
                try:
                    for p in apply_rule(reactions[tid], smi, wanted=cands):
                        prod2tid.setdefault(p, []).append(tid)
                except Exception:
                    continue
        prov[cid] = prod2tid
    return prov


def provenance_sha256(prov: Dict[str, Dict[str, List[str]]]) -> str:
    """Deterministic fingerprint of the provenance map (for the ranked lineage)."""
    import hashlib
    canon_form = {}
    for cid in sorted(prov):
        inner = {c: sorted(prov[cid][c]) for c in sorted(prov[cid])}
        canon_form[cid] = inner
    return hashlib.sha256(
        json.dumps(canon_form, sort_keys=True, ensure_ascii=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------------------------
# ranking
# ---------------------------------------------------------------------------

def _rule_score(tid: str, support: Dict[str, int], verdicts: Dict[str, str],
                bbd: Dict[str, dict]) -> Tuple[float, dict]:
    bt = bt_of(tid)
    fam = family_of(bt)
    rel = relevance_priority(bt)
    spec = specificity(support.get(tid, 1))
    site = site_penalty(tid, verdicts)
    score = round(W_REL * rel + W_SPEC * spec + W_SITE * site, 8)
    meta = {
        "source_id": tid,
        "bt_rule": bt,
        "family": fam,
        "relevance": rel,
        "specificity": round(spec, 6),
        "support": support.get(tid, 1),
        "site_penalty": site,
    }
    if bbd and bt and bt in bbd:
        meta["description"] = bbd[bt].get("description")
    return score, meta


def rank_case(case_id: str, pool: List[str],
              prov: Dict[str, List[str]],
              support: Dict[str, int], verdicts: Dict[str, str],
              bbd: Dict[str, dict], k: int = TOP_K) -> dict:
    """Rank one case's pool (plain SMILES) -> {'case_id','status','ranked',...}."""
    if not pool:
        return {
            "case_id": case_id,
            "status": ABSTAIN_NO_CANDIDATE,
            "n_pool": 0,
            "ranked": [],
            "abstention": {"type": ABSTAIN_NO_CANDIDATE,
                           "reason": "empty candidate pool"},
        }

    prov_map = prov.get(case_id, {})
    scored: List[Tuple[float, str, str, Optional[dict]]] = []
    for smi in pool:
        tids = prov_map.get(smi, [])
        if tids:
            tier = TIER_ENVIPATH
            best = None
            best_score = None
            for tid in tids:
                sc, meta = _rule_score(tid, support, verdicts, bbd)
                if best_score is None or sc > best_score:
                    best_score = sc
                    best = meta
            scored.append((best_score, smi, tier, best))
        else:
            # legacy RHEA donor-similarity residue: no rule provenance
            scored.append((float("-inf"), smi, TIER_RHEA, None))

    def key(t):
        sc, smi, tier, _ = t
        tier_num = 0 if tier == TIER_ENVIPATH else 1
        return (tier_num, -sc, smi)

    scored.sort(key=key)

    ranked = []
    for i, (sc, smi, tier, meta) in enumerate(scored[:k], start=1):
        rec = {
            "rank": i,
            "candidate_smiles": smi,
            "tier": tier,
        }
        if tier == TIER_ENVIPATH:
            rec["score"] = sc
            rec["reaction_class"] = meta
        ranked.append(rec)

    return {
        "case_id": case_id,
        "status": STATUS_RANKED,
        "n_pool": len(pool),
        "n_envipath": len(prov_map),
        "ranked": ranked,
    }


def rank_all(pool: Dict[str, List[str]], prov: Dict[str, Dict[str, List[str]]],
             support: Dict[str, int], verdicts: Dict[str, str],
             bbd: Dict[str, dict], k: int = TOP_K) -> list:
    out = []
    for cid in sorted(pool):
        out.append(rank_case(cid, pool[cid], prov, support, verdicts, bbd, k=k))
    return out


def coverage(case_results: list, k: int = TOP_K) -> dict:
    total = len(case_results)
    ranked = [r for r in case_results if r["status"] == STATUS_RANKED]
    abstained = [r for r in case_results if r["status"] != STATUS_RANKED]
    counts: Dict[str, int] = {}
    for r in abstained:
        counts[r["abstention"]["type"]] = counts.get(r["abstention"]["type"], 0) + 1
    return {
        "top_k": k,
        "cases_total": total,
        "cases_ranked": len(ranked),
        "cases_abstained": len(abstained),
        "abstention_by_type": counts,
        "non_abstained_coverage": round(len(ranked) / total, 6) if total else 0.0,
        "total_ranked_candidates": sum(len(r["ranked"]) for r in ranked),
        "ranking_key": RANKING_KEY,
    }