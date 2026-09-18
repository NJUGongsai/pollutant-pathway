#!/usr/bin/env python3
"""BBD v3.4 fusion: per-source calibrated fusion + Top-K policy.

Motivation (soil/sludge feedback 2026-09-17, diagnostics 2026-09-18):
  v3.3 fuses per-source ranker scores as ``max(p_source)/3``.  The three
  per-source LightGBM rankers were trained independently (RHEA domain), so
  their raw outputs are NOT on a comparable scale: in the environmental
  domain the USPTO ranker's top feature (log1p_template_freq) keeps pushing
  high-frequency synthetic templates to the top even though USPTO-only
  candidates there have ~0.3% generation precision (14/5046 correct in the
  EAWAG donor cache), while enviPath-family candidates cover 78% of the
  positives.  On the colleague's soil/sludge run USPTO-only filled 71% of
  Top-10 slots with a 1.35% rank-1 hit rate.

Repair design (feedback §五 1-5, all parameters fitted on LOCAL
calibration data only — never on soil/sludge gold):

  1. ``SourceCalibrator`` — one isotonic regression per source fitted on
     (p_source, label) pairs from the EAWAG donor cache calibration split
     (environmental domain, unseen by the v3.1 rankers).  Converts each
     source's raw score into a calibrated P(correct), making cross-source
     fusion meaningful.
  2. ``score_candidates_v34`` — same auditable identity convention as v3.3
     (charge-normalized merge, skeleton plausibility, agreement bonus) but
     the base score is the calibrated max-source probability (cap 1.0).
  3. ``apply_topk_policy`` — display-level Top-K policy for recall:
     rank-1 is untouched (Top-1 precision is the fusion's job); positions
     2..K cap same-Murcko-scaffold runs and reserve a minimum number of
     enviPath-family rows when they exist.  Demote-not-delete.
  4. Dual-form emission: ``product_smiles`` carries the best RAW charge
     variant (strict-caliber scorers match library forms; A7 gly lesson),
     ``product_identity`` carries the normalized identity (our dual-caliber
     scorers), ``charge_variants`` keeps every raw member.

Not a model retrain: the v3.1 rankers stay frozen; calibration + policy are
post-hoc layers.  Ranker-level repair (domain feature, skeleton features)
remains follow-up work.
"""
from __future__ import annotations

import json

from rdkit import Chem, RDLogger

import bbd_v33_fusion as V33
import bbd_v32_ion_filter as IF

RDLogger.DisableLog("rdApp.*")

SOURCES = ("uspto", "envipath", "retrieval")
NS_CAP_V34 = 1.0  # calibrated probability ceiling (v3.3 used 1/3 for p/3)

# Top-K policy defaults — selected on the EAWAG calib/val split by the
# pre-registered rule (hit@10 -> hit@1 -> simpler), never on soil/sludge gold.
# Grid evidence (v34_val_grid.json): Murcko-scaffold demotion HURTS recall in
# the environmental domain (correct degradation products often share the
# parent scaffold, e.g. positional-oxidation series) -> scaffold cap OFF.
# The enviPath-family quota alone is neutral on val and targets the deployed
# regime where USPTO-only rows flood Top-10 (71% on the colleague's
# soil/sludge run vs 9% in the cache regime).
DEFAULT_TOPK = 10
DEFAULT_MAX_SAME_SCAFFOLD = 10  # 10 = scaffold demotion OFF
DEFAULT_MIN_ENV = 2             # min enviPath-family rows in Top-K (if any)
DEFAULT_COMBINER = "max"         # selected on the EAWAG calib split with the
                                 # regime gate active, pre-registered rule
                                 # hit@1 > hit@10 > mrr (noisy_or wins h10/mrr
                                 # but loses h1 by one case; see
                                 # v34_fit_report.json)


# --------------------------------------------------------------------------- #
# 1. per-source isotonic calibration
# --------------------------------------------------------------------------- #
class SourceCalibrator:
    """Per-source isotonic calibration of v3.1 ranker scores.

    Fitted on (raw p, label) pairs; ``transform`` returns calibrated
    P(correct) in [0, 1].  Serializable to JSON (cutpoints + values) so the
    deployment chain can load it without sklearn.
    """

    def __init__(self):
        self._models: dict[str, object] = {}
        self._cuts: dict[str, list] = {}
        self._vals: dict[str, list] = {}
        self._tan_cuts: list | None = None
        self._tan_vals: list | None = None
        self.meta: dict = {}

    # ---- fit ----
    def fit(self, pairs: dict[str, list[tuple[float, int]]]) -> None:
        """pairs: {source: [(p_raw, label), ...]} — labels 0/1."""
        from sklearn.isotonic import IsotonicRegression
        for sk, rows in pairs.items():
            if not rows:
                continue
            xs = [r[0] for r in rows]
            ys = [r[1] for r in rows]
            if sum(ys) == 0 or sum(ys) == len(ys):
                # degenerate: constant prediction (pos rate)
                const = float(sum(ys)) / len(ys)
                self._cuts[sk] = [0.0, 1.0]
                self._vals[sk] = [const, const]
                continue
            ir = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            ir.fit(xs, ys)
            self._models[sk] = ir
            self._cuts[sk] = [float(x) for x in ir.X_thresholds_]
            self._vals[sk] = [float(y) for y in ir.y_thresholds_]
        self.meta = {sk: {"n": len(rows), "pos": int(sum(r[1] for r in rows))}
                     for sk, rows in pairs.items()}

    # ---- transform ----
    def transform(self, source: str, p: float) -> float:
        if source in self._models:
            return float(self._models[source].transform([p])[0])
        cuts = self._cuts.get(source)
        if not cuts:
            return 0.0
        vals = self._vals[source]
        # piecewise-constant interpolation (sklearn semantics, clipped)
        if p <= cuts[0]:
            return vals[0]
        if p >= cuts[-1]:
            return vals[-1]
        lo = 0
        for i in range(1, len(cuts)):
            if p <= cuts[i]:
                lo = i
                break
            lo = i
        # sklearn isotonic is piecewise LINEAR between thresholds
        x0, x1 = cuts[lo - 1], cuts[lo]
        y0, y1 = vals[lo - 1], vals[lo]
        if x1 == x0:
            return y1
        return y0 + (y1 - y0) * (p - x0) / (x1 - x0)

    # ---- transfer calibration (v3.5): donor-Tanimoto -> P(correct) ----
    def fit_tanimoto(self, pairs: list[tuple[float, int]]) -> None:
        """Fit the retrieval transfer isotonic on (max_tanimoto, label)."""
        from sklearn.isotonic import IsotonicRegression
        if not pairs or sum(l for _, l in pairs) == 0:
            return
        ir = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        ir.fit([p for p, _ in pairs], [l for _, l in pairs])
        self._tan_cuts = [float(x) for x in ir.X_thresholds_]
        self._tan_vals = [float(y) for y in ir.y_thresholds_]

    def transform_tanimoto(self, tanimoto: float) -> float:
        """P(candidate correct | donor Tanimoto) — transfer probability.

        Returns 0.0 when no transfer calibration is loaded (v3.4
        calibrator only)."""
        if not self._tan_cuts:
            return 0.0
        cuts, vals = self._tan_cuts, self._tan_vals
        if tanimoto <= cuts[0]:
            return vals[0]
        if tanimoto >= cuts[-1]:
            return vals[-1]
        import bisect
        i = min(bisect.bisect_left(cuts, tanimoto), len(vals) - 1)
        x0, x1 = cuts[i - 1], cuts[i]
        y0, y1 = vals[i - 1], vals[i]
        if x1 == x0:
            return y1
        return y0 + (y1 - y0) * (tanimoto - x0) / (x1 - x0)

    # ---- serialization ----
    def to_json_dict(self) -> dict:
        return {
            "version": "v35-calibrator-1" if self._tan_cuts
            else "v34-calibrator-1",
            "sources": {
                sk: {"cuts": self._cuts.get(sk, []),
                     "vals": self._vals.get(sk, [])}
                for sk in self._cuts},
            "retrieval_tanimoto": {
                "cuts": self._tan_cuts or [],
                "vals": self._tan_vals or []},
            "meta": self.meta,
        }

    @classmethod
    def from_json_dict(cls, d: dict) -> "SourceCalibrator":
        c = cls()
        for sk, v in d.get("sources", {}).items():
            c._cuts[sk] = [float(x) for x in v.get("cuts", [])]
            c._vals[sk] = [float(y) for y in v.get("vals", [])]
        tan = d.get("retrieval_tanimoto") or {}
        if tan.get("cuts"):
            c._tan_cuts = [float(x) for x in tan["cuts"]]
            c._tan_vals = [float(y) for y in tan["vals"]]
        c.meta = d.get("meta", {})
        return c

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_json_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "SourceCalibrator":
        with open(path) as f:
            return cls.from_json_dict(json.load(f))


# --------------------------------------------------------------------------- #
# 2. calibrated fusion (v3.4)
# --------------------------------------------------------------------------- #
def fused_ns34(p_by_source: dict[str, float], sources: set[str],
               calibrator: SourceCalibrator,
               skeleton_unexplained: bool,
               combiner: str = DEFAULT_COMBINER,
               max_tanimoto: float = 0.0) -> tuple[float, dict]:
    """v3.4/v3.5 fused score + audit trail.

    base = combiner over belonging sources' calibrated P(correct):
      "max"      max_s calib(sk, p_sk)  (v3.3 semantics, calibrated)
      "noisy_or" 1 - prod_s (1 - calib(sk, p_sk))  (agreement as independent
                 evidence; boosts multi-source candidates more than the
                 additive AGREE_BONUS)
    v3.5 transfer calibration: the retrieval source's calibrated value is
    max(P(pos|p_retrieval), P(pos|donor Tanimoto)) — the v3.1 retrieval
    ranker's score does not reflect donor similarity for NON-exact donors
    (its top feature is donor_exact_match), so the Tanimoto isotonic
    (fitted on the calib2 split, fit_v35_transfer_calib.py) supplies the
    transfer evidence directly.  No-op when the calibrator is v3.4-only.
    ns34 = min(base * agree * skeleton, 1.0)
    """
    def _cal(sk: str) -> float:
        v = calibrator.transform(sk, p_by_source.get(sk, 0.0))
        if sk == "retrieval" and max_tanimoto > 0.0:
            v = max(v, calibrator.transform_tanimoto(max_tanimoto))
        return v

    cals = {sk: _cal(sk) for sk in V33._SOURCE_ORDER if sk in sources}
    if combiner == "noisy_or" and cals:
        base = 1.0
        for v in cals.values():
            base *= (1.0 - min(v, 0.999))
        base = 1.0 - base
        base_src = max(cals, key=cals.get) if cals else ""
    else:
        base = max(cals.values(), default=0.0)
        base_src = max(cals, key=cals.get) if cals else ""
    agree = 1.0 + V33.AGREE_BONUS * (max(len(sources), 1) - 1)
    skel = V33.SKELETON_KEEP_FACTOR if skeleton_unexplained else 1.0
    ns34 = min(base * agree * skel, NS_CAP_V34)
    return ns34, {
        "ns34_base": round(base, 6),
        "ns34_base_source": base_src,
        "ns34_agree_mult": round(agree, 4),
        "ns34_skeleton_mult": round(skel, 4),
        "ns34_retrieval_tan": round(max_tanimoto, 4),
    }


def score_candidates_v34(cands: list[dict], parent_smiles: str,
                         calibrator: SourceCalibrator,
                         combiner: str = DEFAULT_COMBINER,
                         regime_gate: bool = True) -> list[dict]:
    """Full v3.4 pass: v3.3 merge + calibrated fusion + dual-form emission.

    Input candidates need p_uspto/p_envipath/p_retrieval (v3.1/v3.2 path
    output).  Output per merged identity (same merge semantics as v3.3):
      product_smiles     best RAW charge variant (strict-caliber display)
      product_identity   charge-normalized identity (dual-caliber matching)
      charge_variants    all raw members (full provenance)
      ns_score / ns_semantics / skeleton_* / calibration audit fields

    Regime gate (2026-09-18, after the RHEA-val regression check failed):
    ranker score distributions are DOMAIN-conditional — the EAWAG-fitted
    calibration is right for library-external parents (soil/sludge regime)
    but destroys the corpus-covered regime (RHEA val: the same saturated
    retrieval score means P(correct)~0.7+ there vs ~0.2 in EAWAG).  When the
    parent has exact-donor retrieval evidence (donor_exact_match — the
    product-level analog of the lookup tier), the case keeps v3.3 score
    semantics (v3.3 Top-1 = 95% on RHEA val) and is flagged
    ``v34_regime=corpus_covered_v33_semantics``; dual-form emission still
    applies.  Library-external cases use the calibrated noisy-OR fusion.
    """
    if regime_gate and any(c.get("donor_exact_match") for c in cands):
        ranked = V33.score_candidates_v33(cands, parent_smiles)
        for m in ranked:
            bv = m.get("best_variant") or {}
            m["product_identity"] = m["product_smiles"]
            if bv.get("product_smiles"):
                m["product_smiles"] = bv["product_smiles"]
            m["v34_regime"] = "corpus_covered_v33_semantics"
        return ranked
    merged = V33.merge_charge_variants(cands)
    out = []
    for m in merged:
        m["tie_break_canon"] = V33.stereo_blind(m["product_smiles"]) or \
            m["product_smiles"]
        sk_ass = V33.assess_skeleton_change(parent_smiles, m["product_smiles"])
        src_set = V33.source_set(m["source"])
        ns34, detail = fused_ns34(
            {"uspto": m["p_uspto"], "envipath": m["p_envipath"],
             "retrieval": m["p_retrieval"]},
            src_set, calibrator, sk_ass["unexplained"], combiner,
            max_tanimoto=float(m.get("max_tanimoto", 0.0) or 0.0))
        bv = m["best_variant"]
        # dual-form emission: display the best RAW variant, keep identity
        raw_best = bv.get("product_smiles", m["product_smiles"])
        m["product_identity"] = m["product_smiles"]
        m["product_smiles"] = raw_best
        m["product_smiles_full"] = bv.get(
            "product_smiles_full", raw_best)
        m["ns_score"] = round(ns34, 6)
        m["ns_semantics"] = (
            "ns34_calibrated_" +
            ("noisy_or" if combiner == "noisy_or" else "max_source") +
            "_x_agreement_x_skeleton")
        m["v34_regime"] = "library_external_calibrated"
        m["is_calibrated_probability"] = True  # per-source calibrated base
        m["n_independent_sources"] = len(src_set)
        m["skeleton_unexplained"] = sk_ass["unexplained"]
        m["skeleton_n_heavy_lost"] = sk_ass["n_heavy_lost"]
        m["skeleton_reason"] = sk_ass["reason"]
        m.update(detail)
        m["ion_filtered"] = IF.is_ion_fragment(raw_best)
        m["wildcard_filtered"] = any(
            a.GetAtomicNum() == 0
            for a in (Chem.MolFromSmiles(raw_best) or Chem.Mol()).GetAtoms()
        ) if raw_best else False
        out.append(m)

    out.sort(key=lambda c: (c["wildcard_filtered"], c["ion_filtered"],
                            -c["ns_score"], c["tie_break_canon"],
                            c["product_identity"]))
    return out


# --------------------------------------------------------------------------- #
# 3. Top-K display policy (recall side; rank-1 untouched)
# --------------------------------------------------------------------------- #
def _murcko(smi: str) -> str:
    try:
        from rdkit.Chem.Scaffolds import MurckoScaffold
        return MurckoScaffold.MurckoScaffoldSmiles(smiles=smi) or ""
    except Exception:
        return ""


def _is_env_family(cand: dict) -> bool:
    return "envipath" in cand.get("source", "") or \
        cand.get("layer") == "lookup" or \
        cand.get("source") == "eawag_lookup"


def apply_topk_policy(ranked: list[dict], k: int = DEFAULT_TOPK,
                      max_same_scaffold: int = DEFAULT_MAX_SAME_SCAFFOLD,
                      min_env: int = DEFAULT_MIN_ENV) -> list[dict]:
    """Demote-not-delete Top-K policy; positions 2..K only (rank-1 frozen).

    Pass 1: walk the fused order, keep a candidate in the Top-K block while
    its Murcko scaffold has appeared < max_same_scaffold times.
    Pass 2 (only if enviPath-family rows in the block < min_env): swap the
    lowest-scored USPTO-only rows of the block for the best enviPath-family
    candidates below it.
    The result is a permutation of the input (nothing deleted, sinks last).
    """
    if k <= 1 or len(ranked) <= 1:
        return list(ranked)

    clean_ids = {id(c) for c in ranked
                 if not c.get("ion_filtered")
                 and not c.get("wildcard_filtered")}
    clean = [c for c in ranked if id(c) in clean_ids]
    sinks = [c for c in ranked if id(c) not in clean_ids]

    head = clean[:1]  # rank-1: fusion's choice, untouched
    tail = clean[1:]

    block: list[dict] = []
    below: list[dict] = []
    scaf_count: dict[str, int] = {}
    for c in tail:
        if len(block) < k - 1:
            sc = _murcko(c.get("product_smiles", ""))
            if scaf_count.get(sc, 0) >= max_same_scaffold:
                below.append(c)
                continue
            scaf_count[sc] = scaf_count.get(sc, 0) + 1
            block.append(c)
        else:
            below.append(c)

    n_env = sum(1 for c in block if _is_env_family(c))
    if n_env < min_env:
        env_below = [c for c in below if _is_env_family(c)]
        need = min(min_env - n_env, len(env_below))
        for _ in range(need):
            swap_idx = None
            for i in range(len(block) - 1, -1, -1):
                if block[i].get("source", "") == "uspto" and \
                        not _is_env_family(block[i]):
                    swap_idx = i
                    break
            if swap_idx is None:
                break
            env_cand = env_below.pop(0)
            below.remove(env_cand)
            below.append(block[swap_idx])
            block[swap_idx] = env_cand

    return head + block + below + sinks
