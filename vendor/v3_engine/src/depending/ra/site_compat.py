"""M3 site-compatibility filter (MASTER_PLAN loop-3 step 3).

Given (X, a fragment/transform with atom mapping, the matched site, the product Y),
return a compatibility verdict ``compatible | incompatible | ambiguous`` plus a reason.

The three required checks:

1. electronic / valence  -- after the transform, the product must be a valid molecule:
   it must parse AND sanitise (RDKit ``SanitizeMol`` enforces valence, kekulisation /
   aromaticity and a valid formal-charge state). A product that violates any of these
   is ``incompatible``.

   NOTE (documented, deliberate): net-charge *difference* between X and Y is NOT flagged.
   The enviPath rules are single-moiety abstractions that omit co-reactants / co-products
   (H2O, H+, O2, cofactors). Net-charge non-conservation is therefore EXPECTED for
   legitimate decarboxylation / deamination / hydrolysis / sulfonation transforms
   (measured: 32/89 transfer candidates change net charge). A hard net-charge-equality
   gate would kill correct candidates (recall regression). Charge *state* validity is
   instead enforced by sanitisation, and the per-candidate ``charge_delta_x_to_y`` is
   still reported for audit.

2. steric -- two deterministic, published-constant heuristics (no guessing):
   (a) ring strain: the transform forms a 3- or 4-membered ring that was not present in
       X (Baeyer small-ring strain -> sterically/geometrically unfavourable);
   (b) van-der-Waals bump: with a deterministic fixed-seed ETKDG embedding of Y, any
       *non-bonded* introduced-atom / retained-atom distance below
       ``VDW_BUMP_SCALE * (r_i + r_j)`` (Bondi radii) is a hard steric clash.

3. multi-site conflict -- if the transform hits X at >=2 AUTOMORPHISM-EQUIVALENT
   reaction-centre sites (symmetry-related, i.e. the same change is applicable at more
   than one interchangeable position), ALL such sites are enumerated and the verdict is
   ``ambiguous`` (M2/P1-T6: no forced primary pair, no independent side picking).
   Distinct (non-equivalent) sites are NOT collapsed: each is a separate site.

Confidence normalisation (M2 audit conclusion): ``mapper_confidence`` is a per-atom
PRODUCT and shrinks with molecule size, so a raw threshold mis-kills big molecules.
M3 uses option (i)::

    conf_norm = conf ** (1 / n_atoms)

(geometric mean per-atom confidence). The enviPath rules that generate the candidate
pool carry a domain-curated per-rule SCORE (== 1.0 for all 286 rules, already
size-independent, not a per-atom product), so their ``conf_norm`` is read from that
score directly -- see the driver.

Deterministic, fail-closed, answer-isolated.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from rdkit import Chem
from rdkit.Chem import rdChemReactions as R

from ra import aam
from ra.chem import ChemParseError, parse_mol

logger = logging.getLogger(__name__)


VERDICT_COMPATIBLE = "compatible"
VERDICT_INCOMPATIBLE = "incompatible"
VERDICT_AMBIGUOUS = "ambiguous"

# Bondi van der Waals radii (Angstrom). Elements not listed fall back to 1.70.
VDW_RADII = {
    1: 1.20, 6: 1.70, 7: 1.55, 8: 1.52, 9: 1.47,
    15: 1.80, 16: 1.80, 17: 1.75, 35: 1.85, 53: 1.98,
}
VDW_DEFAULT = 1.70
# Non-bonded distance below scale * (r_i + r_j) is a hard steric bump (heuristic).
VDW_BUMP_SCALE = 0.8

SMALL_RING_SIZES = (3, 4)  # Baeyer-strained rings flagged as sterically unfavourable


# --------------------------------------------------------------------------- #
# confidence normalisation (M2 audit conclusion, option i)
# --------------------------------------------------------------------------- #
def norm_conf(conf, n_atoms) -> Optional[float]:
    """Geometric-mean per-atom confidence: ``conf ** (1 / n_atoms)``.

    M2 audit conclusion: raw ``mapper_confidence`` is a per-atom *product* that shrinks
    with molecule size, so raw thresholds mis-kill large molecules. This returns the size
    de-biased confidence. ``None`` on missing/degenerate input (caller decides the
    fail-closed consequence).
    """
    if conf is None or n_atoms is None:
        return None
    try:
        c = float(conf)
        n = int(n_atoms)
    except (TypeError, ValueError):
        return None
    if n <= 0 or c < 0.0:
        return None
    return c ** (1.0 / n)


# --------------------------------------------------------------------------- #
# electronic / valence helpers
# --------------------------------------------------------------------------- #
def net_charge(mol) -> int:
    return sum(a.GetFormalCharge() for a in mol.GetAtoms())


def validate_product(y_smiles: str):
    """Return (ok, error). ok=True only if Y parses and sanitises (valence/aromatic/charge)."""
    if not isinstance(y_smiles, str) or not y_smiles.strip():
        return False, "empty product smiles"
    m = Chem.MolFromSmiles(y_smiles)
    if m is None:
        return False, "product unparseable"
    try:
        Chem.SanitizeMol(m)
        return True, None
    except Exception as exc:  # noqa: BLE001 -- fail-closed reason capture
        return False, f"valence/aromatic/charge violation: {type(exc).__name__}: {str(exc)[:200]}"


# --------------------------------------------------------------------------- #
# steric helpers
# --------------------------------------------------------------------------- #
def _ring_size_multiset(mol) -> Dict[int, int]:
    """Map ring-size -> count (from symmetric smallest ring set, deterministic)."""
    info = mol.GetRingInfo()
    out: Dict[int, int] = {}
    for ring in info.AtomRings():
        size = len(ring)
        out[size] = out.get(size, 0) + 1
    return out


def new_small_rings(x_mol, y_mol) -> List[int]:
    """Ring sizes in {3,4} that appear in Y but not in X (transform-created small rings)."""
    xr = _ring_size_multiset(x_mol)
    yr = _ring_size_multiset(y_mol)
    out = []
    for size in SMALL_RING_SIZES:
        extra = yr.get(size, 0) - xr.get(size, 0)
        if extra > 0:
            out.extend([size] * extra)
    return sorted(out)


def _embed3d(mol):
    """Deterministic fixed-seed 3D conformer; None on failure (never raises)."""
    m = Chem.Mol(mol)
    try:
        m = Chem.AddHs(m)
        res = Chem.AllChem.EmbedMolecule(m, randomSeed=0)
        if res != 0:
            res = Chem.AllChem.EmbedMolecule(m, randomSeed=0, useRandomCoords=True)
            if res != 0:
                return None
        Chem.AllChem.MMFFOptimizeMolecule(m, maxIters=200)  # relax; deterministic given seed
    except Exception:  # noqa: BLE001
        return None
    return m


def _vdw(atomic_num: int) -> float:
    return VDW_RADII.get(atomic_num, VDW_DEFAULT)


def vdw_bump_between(mol_with_conf, set_a, set_b) -> List[Tuple[int, int, float]]:
    """Non-bonded pairs (a in set_a, b in set_b) closer than VDW_BUMP_SCALE * (r_a + r_b).

    Bonded pairs are excluded (a chemical bond is not a clash). Returns sorted list of
    (a_idx, b_idx, distance). Deterministic given the input conformer.
    """
    if not set_a or not set_b:
        return []
    conf = mol_with_conf.GetConformer()
    bonds_a = {tuple(sorted((b.GetBeginAtomIdx(), b.GetEndAtomIdx()))) for b in mol_with_conf.GetBonds()}
    bumps = []
    for a in set_a:
        pa = conf.GetAtomPosition(a)
        ra = _vdw(mol_with_conf.GetAtomWithIdx(a).GetAtomicNum())
        for b in set_b:
            if a == b:
                continue
            if tuple(sorted((a, b))) in bonds_a:
                continue
            pb = conf.GetAtomPosition(b)
            rb = _vdw(mol_with_conf.GetAtomWithIdx(b).GetAtomicNum())
            d = pa.Distance(pb)
            if d < VDW_BUMP_SCALE * (ra + rb):
                bumps.append((a, b, round(d, 3)))
    bumps.sort()
    return bumps


# --------------------------------------------------------------------------- #
# multi-site helpers
# --------------------------------------------------------------------------- #
def _atom_env(mol, idx: int) -> tuple:
    """Query-safe local environment signature (element/charge/aromatic/degree/bonds)."""
    a = mol.GetAtomWithIdx(idx)
    bonds = tuple(sorted(
        (
            round(b.GetBondTypeAsDouble(), 1),
            mol.GetAtomWithIdx(b.GetOtherAtomIdx(idx)).GetAtomicNum(),
            mol.GetAtomWithIdx(b.GetOtherAtomIdx(idx)).GetAtomMapNum(),
        )
        for b in a.GetBonds()
    ))
    return (a.GetAtomicNum(), a.GetFormalCharge(), int(a.GetIsAromatic()), a.GetDegree(), bonds)


def reactive_template_atoms(rxn) -> List[int]:
    """Reactant-template atom indices that actually change (reaction centre).

    Mapped (map != 0) atoms whose local environment differs between reactant and product
    templates, or whose map number disappears entirely (removed). Unmapped (map == 0)
    query atoms are deliberately excluded: they may be persistent environment constraints
    (explicit ``[H]``) or leaving/entering groups, and are not needed to locate the site
    (the mapped attachment atom is always part of the centre).
    """
    rt = rxn.GetReactantTemplate(0)
    # map -> list of (mol, atom_idx) per side
    def bymap(mol):
        d: Dict[int, List[Tuple[object, int]]] = {}
        for a in mol.GetAtoms():
            m = a.GetAtomMapNum()
            if m != 0:
                d.setdefault(m, []).append((mol, a.GetIdx()))
        return d

    rm = bymap(rt)
    pm: Dict[int, List[Tuple[object, int]]] = {}
    for i in range(rxn.GetNumProductTemplates()):
        for m, pairs in bymap(rxn.GetProductTemplate(i)).items():
            pm.setdefault(m, []).extend(pairs)

    reactive = set()
    for m in rm:
        if m not in pm:  # mapped atom removed
            reactive.update(idx for _, idx in rm[m])
    for m in set(rm) & set(pm):
        for _, ri in rm[m]:
            for pmol, pj in pm[m]:
                if _atom_env(rt, ri) != _atom_env(pmol, pj):
                    reactive.add(ri)
                    break
    return sorted(reactive)


def site_atoms_for_match(match, reactive_indices) -> frozenset:
    """X-atom set of the reaction centre for one match (match[j] = X atom idx)."""
    return frozenset(match[j] for j in reactive_indices)


def symmetry_classes(mol) -> List[int]:
    return list(Chem.CanonicalRankAtoms(mol, breakTies=False))


def equivalent_sites(x_mol, transform_smarts: str) -> Dict:
    """Enumerate the transform's reaction-centre sites in X, grouped by equivalence.

    Returns:
      {"n_distinct_sites": int,          # distinct reaction-centre atom sets
       "n_equivalent_sites": int,        # total sites in equivalence groups of size >=2
       "equivalent_groups": [[site_atom_list, ...], ...],  # each group = equivalent sites
       "all_sites": [[int,...], ...],    # every distinct site (sorted atom lists)
       "reactive_indices": [int,...]}    # template atom indices treated as the centre
    """
    rxn = R.ReactionFromSmarts(transform_smarts)
    pat = rxn.GetReactantTemplate(0)
    reactive = reactive_template_atoms(rxn)
    if not reactive:
        # fallback: no mapped centre detected -> whole matched pattern is the site
        reactive = list(range(pat.GetNumAtoms()))
    matches = x_mol.GetSubstructMatches(pat, uniquify=False)
    sc = symmetry_classes(x_mol)

    # distinct sites: reaction-centre atom sets (dedup raw matches by atom set)
    seen: Dict[frozenset, Tuple] = {}
    for m in matches:
        site = site_atoms_for_match(m, reactive)
        if site in seen:
            continue
        sig = tuple(sorted(
            (sc[a], x_mol.GetAtomWithIdx(a).GetAtomicNum(), x_mol.GetAtomWithIdx(a).GetFormalCharge())
            for a in site
        ))
        seen[site] = sig

    # group distinct sites by symmetry signature -> equivalent sites share a signature
    by_sig: Dict[Tuple, List[frozenset]] = {}
    for site, sig in seen.items():
        by_sig.setdefault(sig, []).append(site)

    equivalent_groups = []
    all_sites = []
    n_equiv = 0
    for sig, sites in by_sig.items():
        ordered = [sorted(s) for s in sites]
        all_sites.extend(ordered)
        if len(ordered) >= 2:
            equivalent_groups.append(ordered)
            n_equiv += len(ordered)

    all_sites.sort(key=lambda s: (min(s), s))
    return {
        "n_distinct_sites": len(all_sites),
        "n_equivalent_sites": n_equiv,
        "equivalent_groups": equivalent_groups,
        "all_sites": all_sites,
        "reactive_indices": reactive,
    }


# --------------------------------------------------------------------------- #
# the assessment
# --------------------------------------------------------------------------- #
def assess_site(
    x_smiles: str,
    transform_smarts: str,
    y_smiles: str,
    conf=None,
    n_atoms=None,
) -> Dict:
    """Assess a transform-site/product triple. Never raises; returns a verdict dict.

    ``transform_smarts`` is an atom-mapped reaction SMARTS (the fragment transform), e.g.
    an enviPath rule. ``conf`` / ``n_atoms`` are the optional evidence confidence and the
    molecule-atom count used for size-normalised confidence (``conf_norm``).
    """
    out = {
        "site_verdict": VERDICT_AMBIGUOUS,
        "reason": "",
        "conf_norm": norm_conf(conf, n_atoms),
        "site_index": None,
        "sites": None,
        "n_equivalent_sites": 0,
        "n_distinct_sites": 0,
        "charge_delta_x_to_y": None,
        "n_added": 0,
        "n_removed": 0,
        "n_new_small_rings": 0,
        "n_vdw_bumps": 0,
    }

    # ---- parse inputs (fail-closed: unparseable -> incompatible) ----------------
    try:
        x_mol = parse_mol(x_smiles)
    except ChemParseError as exc:
        out["site_verdict"] = VERDICT_INCOMPATIBLE
        out["reason"] = f"X unparseable: {exc}"
        return out

    ok, err = validate_product(y_smiles)
    if not ok:
        out["site_verdict"] = VERDICT_INCOMPATIBLE
        out["reason"] = f"product invalid: {err}"
        return out
    y_mol = Chem.MolFromSmiles(y_smiles)

    # ---- charge delta (reported, not fatal -- see module docstring) -------------
    out["charge_delta_x_to_y"] = net_charge(y_mol) - net_charge(x_mol)

    # ---- reaction centre on X via MCES correspondence ----------------------------
    center_r, center_p, removed_r, added_p, cstatus = aam.reaction_center(x_mol, y_mol)
    out["n_added"] = len(added_p)
    out["n_removed"] = len(removed_r)
    reaction_center_r = sorted(set(center_r) | set(removed_r))
    out["site_index"] = min(reaction_center_r) if reaction_center_r else None

    # ---- check 1: electronic / valence (already gated above) --------------------
    # (parse+sanitise is the check; failures already returned incompatible)

    # ---- check 2: steric ---------------------------------------------------------
    steric_reasons = []

    small_rings = new_small_rings(x_mol, y_mol)
    out["n_new_small_rings"] = len(small_rings)
    if small_rings:
        steric_reasons.append(
            "ring strain: transform creates %d new %s-membered ring(s)"
            % (len(small_rings), "/".join(str(s) for s in small_rings))
        )

    if added_p:
        try:
            y_with_conf = _embed3d(y_mol)
            if y_with_conf is not None:
                # Locate introduced atoms: AddHs does NOT reorder heavy atoms, so the
                # heavy-atom indices (0 .. y_mol.GetNumAtoms()-1) map 1:1 onto y_with_conf.
                added_set = set(added_p)
                n_heavy = y_mol.GetNumAtoms()
                retained_set = set(range(n_heavy)) - added_set
                bumps = vdw_bump_between(y_with_conf, added_set, retained_set)
                out["n_vdw_bumps"] = len(bumps)
                if bumps:
                    steric_reasons.append(
                        "steric clash: %d non-bonded introduced/retained contact(s) below vdW threshold"
                        % len(bumps)
                    )
        except Exception as exc:  # noqa: BLE001 -- steric is a prune, never crash
            logger.debug("steric 3D check failed: %r", exc)

    # ---- check 3: multi-site -----------------------------------------------------
    try:
        sites = equivalent_sites(x_mol, transform_smarts)
    except Exception as exc:  # noqa: BLE001
        sites = {"n_distinct_sites": 1, "n_equivalent_sites": 0,
                 "equivalent_groups": [], "all_sites": [reaction_center_r]}
        logger.debug("multi-site check failed: %r", exc)

    out["n_distinct_sites"] = sites["n_distinct_sites"]
    out["n_equivalent_sites"] = sites["n_equivalent_sites"]

    multi_equiv = sites["n_equivalent_sites"] >= 2

    # ---- assemble verdict ---------------------------------------------------------
    # enumerate the full equivalent site atom-sets (P1-T6: no silent single pick)
    equivalent_site_sets = sorted(
        {tuple(sorted(s)) for g in sites["equivalent_groups"] for s in g}
    )
    combined_sites = None
    if equivalent_site_sets:
        combined_sites = [list(s) for s in equivalent_site_sets]

    if steric_reasons:
        out["site_verdict"] = VERDICT_INCOMPATIBLE
        out["reason"] = "; ".join(steric_reasons)
        if multi_equiv:
            out["reason"] += " [also multi-site ambiguous]"
            out["sites"] = combined_sites
        return out

    if multi_equiv:
        out["site_verdict"] = VERDICT_AMBIGUOUS
        out["reason"] = (
            "multi-site ambiguity: transform hits %d distinct reaction-centre site(s), "
            "%d mutually-equivalent site(s) (cannot pick a primary site)"
            % (sites["n_distinct_sites"], sites["n_equivalent_sites"])
        )
        out["sites"] = combined_sites
        out["site_index"] = None
        return out

    out["site_verdict"] = VERDICT_COMPATIBLE
    out["reason"] = (
        "valid product; single reaction-centre site"
        if sites["n_distinct_sites"] == 1
        else "valid product; %d distinct (non-equivalent) reaction-centre site(s)"
        % sites["n_distinct_sites"]
    )
    out["sites"] = combined_sites
    return out