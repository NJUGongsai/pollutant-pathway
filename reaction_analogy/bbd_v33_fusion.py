#!/usr/bin/env python3
"""BBD v3.3 fusion layer: charge normalization + source agreement + skeleton
plausibility, applied ON TOP of the existing v3.2 per-source ranker scores.

Motivation (DBP post-freeze diagnostic 2026-09-12):
  Rank 1 was an unexplained USPTO rearrangement (ester -> aryl-CH3) while the
  correct first hydrolysis product (MBP) sat at Rank 2 as its carboxylate form
  (USPTO+enviPath).  Three independent gaps caused it:
    1. charge variants (neutral / [O-]) were treated as distinct products, so
       the correct candidate's evidence was split across identities;
    2. ns_score = max(p_source)/3 ignores multi-source agreement — one
       overconfident synthetic template beats two consistent sources;
    3. no reaction-plausibility constraint — a candidate that loses a large
       skeleton piece not explainable by a clean leaving group ranked top-1.

Design constraints:
  - NO model retraining: consumes p_uspto / p_envipath / p_retrieval already
    produced by the v3.1 per-source rankers (features stay untouched, so the
    trained models remain valid).
  - Generic chemistry rules only — nothing is fitted to DBP or any compound.
  - Raw outputs preserved: charge_variants keep every raw member and score.
  - Deterministic: sorted keys, stable tie-breaks, cached canonicalization.

Score semantics (v3.3):
    ns33(c) = max_s p_s(c) / 3
              * (1 + AGREE_BONUS * (n_independent_sources - 1))
              * SKELETON_KEEP_FACTOR   if unexplained skeleton loss
              capped at 1/3.
  Not a calibrated probability: is_calibrated_probability stays False.
"""
from __future__ import annotations

from functools import lru_cache

from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

RDLogger.DisableLog("rdApp.*")

# --------------------------------------------------------------------------- #
# Tunable fusion constants (a-priori chemistry priors, NOT fitted to any
# benchmark; validated for non-regression on the BBD83 blind pool as a whole)
# --------------------------------------------------------------------------- #
AGREE_BONUS = 0.15          # per extra independent source (1 -> 1.0, 2 -> 1.15, 3 -> 1.30)
SKELETON_KEEP_FACTOR = 0.70 # multiplicative penalty when skeleton change unexplained
NS_CAP = 1.0 / 3.0          # keep v3.2 score ceiling semantics

_SOURCE_ORDER = ("uspto", "envipath", "retrieval")
_HALOGENS = {"F", "Cl", "Br", "I"}


# --------------------------------------------------------------------------- #
# 1. Charge / protonation normalization (auditable identity)
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=100_000)
def _uncharger() -> rdMolStandardize.Uncharger:
    return rdMolStandardize.Uncharger()


@lru_cache(maxsize=100_000)
def normalize_charge_smiles(smi: str) -> str | None:
    """Canonical charge-neutral form of *smi* (auditable product identity).

    Neutral + canonical + isomeric.  Returns None for unparseable input.
    MBP carboxylate ``CCCCOC(=O)c1ccccc1C(=O)[O-]`` -> neutral MBP.
    """
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    try:
        m2 = _uncharger().uncharge(m)
        Chem.SanitizeMol(m2)
    except Exception:
        m2 = m
    return Chem.MolToSmiles(m2)


@lru_cache(maxsize=100_000)
def stereo_blind(smi: str) -> str | None:
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m, isomericSmiles=False) if m is not None else None


def source_set(src: str) -> set[str]:
    """Independent sources behind a v3.x combined source label."""
    s = set()
    for sk in _SOURCE_ORDER:
        if sk in src:
            s.add(sk)
    if "both" in src:  # legacy v2 label
        s.add("uspto")
        s.add("envipath")
    return s


def combined_source_label(sources: set[str]) -> str:
    if not sources:
        return "uspto"
    return "+".join(sk for sk in _SOURCE_ORDER if sk in sources)


# --------------------------------------------------------------------------- #
# 2. Skeleton-change plausibility (generic, mechanism-aware)
# --------------------------------------------------------------------------- #
_SMALL_LOSS_TOL = 2  # heavy atoms — below this any change is plausible


def _relaxed_query(mol: Chem.Mol) -> Chem.Mol:
    """Query copy with generic bonds (bond-order changes at one center do not
    break substructure attribution of the lost fragment)."""
    p = Chem.AdjustQueryParameters.NoAdjustments()
    p.makeBondsGeneric = True
    return Chem.AdjustQueryProperties(Chem.Mol(mol), p)


def _connected_pieces(idxs: list[int], bond_pairs: list[tuple[int, int]]) -> list[set[int]]:
    idx_set = set(idxs)
    adj: dict[int, set[int]] = {i: set() for i in idxs}
    for a, b in bond_pairs:
        if a in idx_set and b in idx_set:
            adj[a].add(b)
            adj[b].add(a)
    seen: set[int] = set()
    pieces = []
    for i in idxs:
        if i in seen:
            continue
        comp, stack = set(), [i]
        while stack:
            j = stack.pop()
            if j in comp:
                continue
            comp.add(j)
            stack.extend(adj[j] - comp)
        seen |= comp
        pieces.append(comp)
    return pieces


def _classify_piece(piece_atoms: dict[int, str], attach_sym: str | None) -> str | None:
    """Return 'ok' | 'flag' classification reason for one lost fragment.

    Generic leaving-group / cleavage chemistry:
      pure C/H alkyl (any attachment)              -> dealkylation / chain pruning
      C(+<=2 O) attached via its own C             -> decarboxylation
      N(+2 O) attached via N                       -> denitration
      single halogen                                -> dehalogenation
      anything else (e.g. acyl-O or alkoxy loss
      from a carbonyl carbon, ring fragments)      -> unexplained
    """
    syms = sorted(piece_atoms.values())
    n_c = syms.count("C")
    n_o = syms.count("O")
    n_n = syms.count("N")
    if set(syms) <= {"C"}:
        return "ok:pure_alkyl_loss"
    if set(syms) <= {"C", "O"} and 1 <= n_c <= 1 and n_o <= 2 and len(syms) <= 3:
        return "ok:decarboxylation"
    if set(syms) == {"N", "O"} and n_n == 1 and n_o == 2:
        return "ok:denitration"
    if len(syms) == 1 and set(syms) <= _HALOGENS:
        return "ok:dehalogenation"
    return "flag:unexplained_fragment"


def assess_skeleton_change(parent_smi: str, prod_smi: str) -> dict:
    """Heavy-atom accounting of parent -> product (generic, no target chemistry).

    Returns dict:
      n_heavy_lost       net heavy atoms lost (<=0 when product grows)
      unexplained        True when loss cannot be attributed to clean event(s)
      reason             machine-readable explanation ('ok:...' / 'flag:...')
    Fail-open: unparseable input -> no flag (rankers keep authority).
    """
    out = {"n_heavy_lost": 0, "unexplained": False, "reason": "ok:no_loss"}
    parent = Chem.MolFromSmiles(parent_smi)
    prod = Chem.MolFromSmiles(prod_smi)
    if parent is None or prod is None:
        out["reason"] = "ok:unparseable_failopen"
        return out

    p_heavy = parent.GetNumHeavyAtoms()
    q_heavy = prod.GetNumHeavyAtoms()
    n_lost = p_heavy - q_heavy
    out["n_heavy_lost"] = n_lost
    if n_lost <= 0:
        out["reason"] = "ok:no_loss"
        return out
    if n_lost <= _SMALL_LOSS_TOL:
        out["reason"] = "ok:small_loss"
        return out

    # charge-normalize both sides so ionic forms still match structurally
    try:
        parent_n = _uncharger().uncharge(parent)
        prod_n = _uncharger().uncharge(prod)
        Chem.SanitizeMol(parent_n)
        Chem.SanitizeMol(prod_n)
    except Exception:
        parent_n, prod_n = parent, prod

    # match product (relaxed bonds) inside charge-normalized parent
    query = _relaxed_query(prod_n)
    matches = parent_n.GetSubstructMatches(query, maxMatches=200)
    if not matches:
        out["unexplained"] = True
        out["reason"] = "flag:product_not_substructure"
        return out

    best = None  # (flagged_any, reason_list, n_lost)
    for m in matches:
        matched = set(m)
        lost_idx = [a.GetIdx() for a in parent_n.GetAtoms() if a.GetIdx() not in matched]
        bond_pairs = [(b.GetBeginAtomIdx(), b.GetEndAtomIdx()) for b in parent_n.GetBonds()]
        pieces = _connected_pieces(lost_idx, bond_pairs)

        reasons = []
        flagged = False
        for piece in pieces:
            piece_syms = {i: parent_n.GetAtomWithIdx(i).GetSymbol() for i in piece}
            # attachment atom(s): matched atom(s) bonded to this piece
            attach_syms = set()
            for a, b in bond_pairs:
                if a in piece and b in matched:
                    attach_syms.add(parent_n.GetAtomWithIdx(b).GetSymbol())
                elif b in piece and a in matched:
                    attach_syms.add(parent_n.GetAtomWithIdx(a).GetSymbol())
            verdict = _classify_piece(piece_syms, sorted(attach_syms)[0] if attach_syms else None)
            if verdict.startswith("flag"):
                flagged = True
            piece_sym_str = "".join(sorted(piece_syms.values()))
            attach_str = sorted(attach_syms)[0] if attach_syms else "?"
            reasons.append(f"{verdict}[{piece_sym_str}]->{attach_str}")
        cand = (flagged, reasons, len(lost_idx))
        if best is None or (cand[0], cand[2]) < (best[0], best[2]):
            best = cand
        if not flagged:
            break

    assert best is not None
    flagged, reasons, _ = best
    out["unexplained"] = bool(flagged)
    out["reason"] = "ok:attributed_loss:" + ";".join(reasons) if not flagged \
        else "flag:" + ";".join(reasons)
    return out


# --------------------------------------------------------------------------- #
# 3. Charge-variant merge + v3.3 fusion
# --------------------------------------------------------------------------- #
def merge_charge_variants(cands: list[dict]) -> list[dict]:
    """Group candidate variants that differ only by protonation state.

    Input candidates need: product_smiles, source, p_uspto / p_envipath /
    p_retrieval (already computed by the v3.1/v3.2 path).  Returns one dict
    per normalized identity:
      product_smiles    neutral normalized form (display identity)
      charge_variants   the raw member dicts (full provenance preserved)
      source            combined label, e.g. 'uspto+envipath'
      p_<sk>            per-source max over members (evidence-max pooling)
      best_variant      member dict with the highest member ns_score
    Deterministic: groups sorted by identity; members kept in input order.
    """
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for c in cands:
        key = normalize_charge_smiles(c.get("product_smiles", ""))
        if key is None:
            key = "unparseable:" + str(c.get("product_smiles", ""))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(c)

    merged = []
    for key in sorted(groups):  # deterministic group order
        members = groups[key]
        sources: set[str] = set()
        for m in members:
            sources |= source_set(m.get("source", ""))
        p_max = {}
        for sk in _SOURCE_ORDER:
            vals = [m.get(f"p_{sk}", 0.0) for m in members
                    if sk in source_set(m.get("source", ""))]
            p_max[sk] = max(vals) if vals else 0.0

        def _member_ns(m: dict) -> float:
            return max((m.get(f"p_{sk}", 0.0) for sk in _SOURCE_ORDER
                        if sk in source_set(m.get("source", ""))), default=0.0) / 3.0

        best_variant = max(members, key=_member_ns)
        m = {
            "product_smiles": key,
            "product_smiles_full": best_variant.get("product_smiles_full",
                                                    best_variant.get("product_smiles", key)),
            "charge_variants": members,
            "source": combined_source_label(sources),
            "p_uspto": p_max["uspto"],
            "p_envipath": p_max["envipath"],
            "p_retrieval": p_max["retrieval"],
            "best_variant": best_variant,
        }
        # aggregate frequency/evidence fields from best member (auditable, max)
        for f in ("template_freq", "reactions_count", "pattern_atom_count",
                  "n_evidence", "max_tanimoto", "mean_tanimoto",
                  "donor_exact_match"):
            m[f] = max((mv.get(f, 0) for mv in members), key=lambda v: (v is not None, v)) \
                if f not in ("donor_exact_match",) else any(mv.get(f, False) for mv in members)
        merged.append(m)
    for m in merged:
        m["member_canons"] = sorted({stereo_blind(v.get("product_smiles", ""))
                                     for v in m["charge_variants"]
                                     if v.get("product_smiles")} - {None})
    return merged


def fused_ns33(p_by_source: dict[str, float], sources: set[str],
               skeleton_unexplained: bool) -> tuple[float, dict]:
    """v3.3 fused score + audit trail.  Returns (ns33, detail dict)."""
    base = max((p_by_source.get(sk, 0.0) for sk in _SOURCE_ORDER
                if sk in sources), default=0.0) / 3.0
    agree = 1.0 + AGREE_BONUS * (max(len(sources), 1) - 1)
    skel = SKELETON_KEEP_FACTOR if skeleton_unexplained else 1.0
    ns33 = min(base * agree * skel, NS_CAP)
    return ns33, {
        "ns33_base": round(base, 6),
        "ns33_agree_mult": round(agree, 4),
        "ns33_skeleton_mult": round(skel, 4),
    }


def score_candidates_v33(cands: list[dict], parent_smiles: str) -> list[dict]:
    """Full v3.3 pass: merge charge variants, skeleton flags, fused score, sort.

    Expects per-candidate p_uspto/p_envipath/p_retrieval (v3.2 path output).
    Adds to each merged candidate: ns_score, ns_semantics, skeleton_*
    audit fields, ion_filtered / wildcard_filtered (from best variant),
    then sorts by (wildcard, ion, -ns33, product_smiles).
    """
    import bbd_v32_ion_filter as IF  # local import: no hard dependency cycle

    merged = merge_charge_variants(cands)
    out = []
    for m in merged:
        m["tie_break_canon"] = stereo_blind(m["product_smiles"]) or m["product_smiles"]
        sk_ass = assess_skeleton_change(parent_smiles, m["product_smiles"])
        ns33, detail = fused_ns33(
            {"uspto": m["p_uspto"], "envipath": m["p_envipath"],
             "retrieval": m["p_retrieval"]},
            source_set(m["source"]),
            sk_ass["unexplained"],
        )
        bv = m["best_variant"]
        m["ns_score"] = round(ns33, 6)
        m["ns_semantics"] = "ns33_max_source_x_agreement_x_skeleton_over_3"
        m["is_calibrated_probability"] = False
        m["n_independent_sources"] = len(source_set(m["source"]))
        m["skeleton_unexplained"] = sk_ass["unexplained"]
        m["skeleton_n_heavy_lost"] = sk_ass["n_heavy_lost"]
        m["skeleton_reason"] = sk_ass["reason"]
        m.update(detail)
        m["ion_filtered"] = IF.is_ion_fragment(bv.get("product_smiles", ""))
        m["wildcard_filtered"] = any(
            a.GetAtomicNum() == 0
            for a in (Chem.MolFromSmiles(bv.get("product_smiles", "")) or Chem.Mol())
            .GetAtoms()) if bv.get("product_smiles") else False
        out.append(m)

    out.sort(key=lambda c: (c["wildcard_filtered"], c["ion_filtered"],
                            -c["ns_score"], c["tie_break_canon"],
                            c["product_smiles"]))
    return out
