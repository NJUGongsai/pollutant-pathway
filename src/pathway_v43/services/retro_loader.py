#!/usr/bin/env python3
"""RetroRules (rhea.json / METANETX.json / mnx+rhea) retro-template loader and index.

Ported from n004 stage 1/2 (``channel_patch.diff``) and enhanced for Phase 2b:
  * Supports datasets:
      - ``"rhea"``: ``assets/retrorules/raw/rhea.json`` (134,738 records)
        -> ``assets/retrorules/derived/rhea_retro_index.npz`` + ``.meta.json``
      - ``"mnx"``: ``assets/retrorules/raw/METANETX.json`` (336,966 records)
        -> ``assets/retrorules/derived/mnx_retro_index.npz`` + ``.meta.json``
      - ``"mnx+rhea"``: union of ``mnx`` and ``rhea`` deduplicated by
        ``TEMPLATE`` string (``lhs>>rhs``), merging ``radii``, ``reactions``
        (``MNXR...`` + ``RHEA:xxxx``), ``ecs``, and ``score``.
  * Normalizes balanced component-group parentheses ``(A.B).C`` so all
    134,738 ``rhea.json`` and 336,966 ``METANETX.json`` records parse and
    convert with zero skips (100% conversion rate).
  * Indexes both fully sanitized SMILES templates (``FLAG_BOTH_SIDES_SANITIZED``)
    and radius-truncated aromatic fragments (``unsanitized_fragment``) so
    small-radius rules (``r=2, 4, 6``) that cut through aromatic rings are
    preserved for substructure matching and ``bridge_occurrence_to_spec``
    instantiation.
  * Stores both Morgan r2 2048-bit fingerprints (``fp``) and RDKit 2048-bit
    ``PatternFingerprint`` (``pat_fp``) per unique LHS, plus a ``uint16``
    ``radii_mask`` bitfield per rule for O(1) exact radius-set filtering
    (``allowed_radii``).
  * Cross-maps shared ``TEMPLATE`` strings between ``METANETX.json`` and
    ``rhea.json`` (77,144 shared templates) so ``RHEA:xxxx`` IDs are attached
    to ``parent_reaction_ids`` for self-record leakage detection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from multiprocessing import get_context
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402
from rdkit import Chem, RDLogger  # noqa: E402
from rdkit.Chem import rdMolDescriptors  # noqa: E402

RDLogger.DisableLog("rdApp.*")

# ---------------------------------------------------------------- constants

RETRO_LOADER_VERSION = "n004-retro-loader-2-phase2b"
RETRO_INDEX_VERSION = "n004-retro-index-morgan-r2-b2048-1"
RETRO_SCHEMA_VERSION = "n004-retro-manifest-1"
RETRO_LIBRARY = "rhea"

FP_RADIUS = 2
FP_BITS = 2048
FP_CHIRALITY = False
FP_BYTES = FP_BITS // 8

INDEX_NPZ = "retro_index.npz"
TEMPLATES_JSONL = "retro_templates.jsonl"
MANIFEST_JSON = "retro_manifest.json"
STATS_JSON = "retro_stats.json"

DATASET_RAW_FILES = {
    "rhea": "rhea.json",
    "mnx": "METANETX.json",
    "metanetx": "METANETX.json",
}

DATASET_INDEX_PREFIX = {
    "rhea": "rhea_retro_index",
    "mnx": "mnx_retro_index",
    "metanetx": "mnx_retro_index",
    "mnx+rhea": "mnx_rhea_retro_index",
    "rhea+mnx": "mnx_rhea_retro_index",
}

SKIP_REASONS = (
    "no_template_id",
    "no_template",
    "no_arrow",
    "multi_arrow",
    "empty_lhs",
    "empty_rhs",
    "valid_false",
    "duplicate_template_id",
    "lhs_smarts_unparseable",
    "rhs_smarts_unparseable",
    "lhs_convert_wildcard",
    "lhs_convert_unsupported_primitive",
    "lhs_convert_forbidden_token",
    "lhs_convert_bracket_parse_fail",
    "lhs_convert_map_lost",
    "lhs_convert_smiles_parse_fail",
    "lhs_convert_aromatic_fragment",
    "rhs_convert_wildcard",
    "rhs_convert_unsupported_primitive",
    "rhs_convert_forbidden_token",
    "rhs_convert_bracket_parse_fail",
    "rhs_convert_map_lost",
    "rhs_convert_smiles_parse_fail",
    "rhs_convert_aromatic_fragment",
    "lhs_unmapped",
    "rhs_unmapped",
    "internal_error",
)

# Flags stored per template (uint8 bitfield)
FLAG_INDEXED = 1 << 0
FLAG_VALID = 1 << 1
FLAG_LHS_ALL_MAPPED = 1 << 2
FLAG_RHS_ALL_MAPPED = 1 << 3
FLAG_MULTI_COMPONENT_RHS = 1 << 4
FLAG_CONVERTED_LHS_FROM_SMARTS = 1 << 5
FLAG_CONVERTED_RHS_FROM_SMARTS = 1 << 6
FLAG_BOTH_SIDES_SANITIZED = 1 << 7


class RetroAssetError(RuntimeError):
    """Fail-closed loader/manifest error (missing, tampered, inconsistent)."""

    def __init__(self, message: str, detail: dict | None = None) -> None:
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- SMARTS text


def strip_outer_parens(s: str) -> str:
    """Strip only *balanced enclosing* parentheses (RetroRules wraps sides)."""
    s = (s or "").strip()
    while s.startswith("(") and s.endswith(")"):
        depth = 0
        balanced = True
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i < len(s) - 1:
                    balanced = False
                    break
        if not balanced or depth != 0:
            break
        s = s[1:-1].strip()
    return s


def split_components(s: str) -> list[str]:
    """Top-level ``.`` split (bracket/paren depth aware)."""
    out: list[str] = []
    buf: list[str] = []
    bracket = paren = 0
    for ch in s:
        if ch == "[":
            bracket += 1
        elif ch == "]":
            bracket -= 1
        elif ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1
        if ch == "." and bracket == 0 and paren == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return [x for x in out if x]


def normalize_side_smarts(s: str) -> str:
    """Strip balanced outer and component-group parentheses ``(A.B).C -> A.B.C``."""
    s = strip_outer_parens(s)
    prev = None
    while prev != s:
        prev = s
        comps = [strip_outer_parens(c) for c in split_components(s)]
        s = ".".join(c for c in comps if c)
    return s


_BRACKET_RE = re.compile(r"\[([^\[\]]*)\]")
_MAP_SUFFIX_RE = re.compile(r":(\d+)$")
_ELEM_RE = re.compile(
    r"^(\d*)(\*|[A-Z][a-z]?|[a-z]{1,2})(@{1,2})?(H\d?)?([+-]\d*)?$")
_ATOMIC_NUMBER_RE = re.compile(r"^#(\d+)$")
_H_TOKEN_RE = re.compile(r"^H(\d*)$")
_CHARGE_TOKEN_RE = re.compile(r"^([+-])(\d*)$")
_FORBIDDEN = set("~$!&?;")
_PERIODIC = Chem.GetPeriodicTable()


class _ConversionError(Exception):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}:{detail}")
        self.reason = reason
        self.detail = detail


def _parse_element_token(tok: str) -> tuple[str, str, str, str | None]:
    """Return (isotope_prefix, symbol, stereo, h_token); raise if unsupported."""
    m = _ATOMIC_NUMBER_RE.match(tok)
    if m:
        z = int(m.group(1))
        if z == 1:
            return "", "H", "", None
        if z < 1 or z > 118:
            raise _ConversionError("unsupported_primitive", tok)
        return "", _PERIODIC.GetElementSymbol(z), "", None
    m = _ELEM_RE.match(tok)
    if not m:
        raise _ConversionError("unsupported_primitive", tok)
    iso, sym, stereo, h, charge = m.groups()
    if sym == "*":
        raise _ConversionError("wildcard", tok)
    if charge is not None:
        raise _ConversionError("bracket_parse_fail", tok)
    return iso, sym, (stereo or ""), h


def _format_charge(sign: str, digits: str) -> str:
    n = int(digits or "1")
    if n == 0:
        return ""
    if n == 1:
        return sign
    return f"{sign}{n}"


def _bracket_to_smiles(body: str) -> str:
    """Convert one ``[...]`` SMARTS primitive conjunction to a SMILES atom."""
    parts = body.split(";")
    if not parts or not parts[0]:
        raise _ConversionError("bracket_parse_fail", body)
    map_no: int | None = None
    cleaned: list[str] = []
    for part in parts:
        m = _MAP_SUFFIX_RE.search(part)
        if m:
            if map_no is not None:
                raise _ConversionError("bracket_parse_fail", body)
            map_no = int(m.group(1))
            part = part[: m.start()]
        if part:
            cleaned.append(part)
    if not cleaned:
        raise _ConversionError("bracket_parse_fail", body)

    iso, sym, stereo, h_token = _parse_element_token(cleaned[0])
    charge = ""
    for tok in cleaned[1:]:
        if tok in ("@", "@@"):
            if stereo:
                raise _ConversionError("unsupported_primitive", tok)
            stereo = tok
            continue
        m = _H_TOKEN_RE.match(tok)
        if m:
            if h_token is not None:
                same = ({h_token, tok} <= {"H", "H1"})
                if not same:
                    raise _ConversionError("bracket_parse_fail", body)
            h_token = tok
            continue
        m = _CHARGE_TOKEN_RE.match(tok)
        if m:
            charge = _format_charge(m.group(1), m.group(2))
            continue
        raise _ConversionError("unsupported_primitive", tok)

    if h_token is None:
        h_part = ""
    else:
        digits = h_token[1:]
        if digits == "" or digits == "1":
            h_part = "H"
        elif int(digits) == 0:
            h_part = ""
        else:
            h_part = f"H{int(digits)}"

    out = "[" + iso + sym + stereo + h_part + charge
    if map_no:
        out += f":{map_no}"
    return out + "]"


def convert_smarts_to_mapped_smiles(smarts: str) -> str:
    """Map-preserving SMARTS -> mapped SMILES (raises ``_ConversionError``)."""
    s = normalize_side_smarts(smarts)
    comps = [strip_outer_parens(c) for c in split_components(s)]
    comps = [c for c in comps if c]
    if not comps:
        raise _ConversionError("empty", "")
    out: list[str] = []
    for comp in comps:
        converted: list[str] = []
        pos = 0
        for m in _BRACKET_RE.finditer(comp):
            outside = comp[pos:m.start()]
            _check_outside(outside)
            converted.append(outside)
            converted.append(_bracket_to_smiles(m.group(1)))
            pos = m.end()
        tail = comp[pos:]
        _check_outside(tail)
        converted.append(tail)
        piece = "".join(converted)
        if not piece:
            raise _ConversionError("bracket_parse_fail", comp)
        out.append(piece)
    return ".".join(out)


def _check_outside(text: str) -> None:
    for ch in text:
        if ch == "*":
            raise _ConversionError("wildcard", text[:60])
        if ch in _FORBIDDEN:
            raise _ConversionError(
                "forbidden_token", f"{ch!r} in {text[:60]!r}")
        if ch.isspace():
            raise _ConversionError("forbidden_token", "whitespace")


# ---------------------------------------------------------------- record pass


def _bump(counter: dict, key: str) -> None:
    counter[key] = counter.get(key, 0) + int(1)


def _hist(counter: dict, value: int, cap: int = 20) -> None:
    counter[str(min(int(value), cap))] = counter.get(
        str(min(int(value), cap)), 0) + 1


def _percentiles(values: list[int], points=(50, 90, 99)) -> dict:
    if not values:
        return {}
    arr = np.asarray(values, dtype=np.int64)
    out = {}
    for p in points:
        out[f"p{p}"] = int(np.percentile(arr, p))
    out["max"] = int(arr.max())
    out["min"] = int(arr.min())
    return out


def _radii_to_mask(radii: list[int]) -> int:
    mask = 0
    for r in radii:
        ri = int(r)
        if 0 <= ri < 16:
            mask |= (1 << ri)
    return mask


_SIDE_PARSE_CACHE: dict[str, dict] = {}


def _analyze_side_cached(raw_side: str, side: str) -> dict:
    """Parse and convert one normalized SMARTS side, caching per worker."""
    cached = _SIDE_PARSE_CACHE.get(raw_side)
    if cached is not None:
        return cached
    query = Chem.MolFromSmarts(raw_side)
    if query is None:
        res = {"smarts_ok": False, "reason": "smarts_unparseable"}
        if len(_SIDE_PARSE_CACHE) < 250_000:
            _SIDE_PARSE_CACHE[raw_side] = res
        return res
    n_atoms = query.GetNumAtoms()
    want_maps = {a.GetAtomMapNum() for a in query.GetAtoms()
                 if a.GetAtomMapNum()}
    n_mapped = sum(1 for a in query.GetAtoms() if a.GetAtomMapNum())
    try:
        converted = convert_smarts_to_mapped_smiles(raw_side)
    except _ConversionError as exc:
        res = {"smarts_ok": True, "n_atoms": n_atoms, "n_mapped": n_mapped,
               "converted_ok": False, "reason": f"convert_{exc.reason}"}
        if len(_SIDE_PARSE_CACHE) < 250_000:
            _SIDE_PARSE_CACHE[raw_side] = res
        return res

    mol = Chem.MolFromSmiles(converted)
    sanitized = mol is not None
    unsanitized_reason = None
    if mol is None:
        unsanitized_reason = "convert_smiles_parse_fail"
        try:
            raw_mol = Chem.MolFromSmiles(converted, sanitize=False)
            if raw_mol is not None:
                Chem.SanitizeMol(raw_mol)
        except Exception as exc:  # noqa: BLE001
            text = str(exc).lower()
            if "marked aromatic" in text or "kekul" in text:
                unsanitized_reason = "convert_aromatic_fragment"
        mol = Chem.MolFromSmiles(converted, sanitize=False)
        if mol is not None:
            try:
                mol.UpdatePropertyCache(strict=False)
                Chem.FastFindRings(mol)
            except Exception:  # noqa: BLE001
                mol = None

    if mol is None:
        res = {"smarts_ok": True, "n_atoms": n_atoms, "n_mapped": n_mapped,
               "converted_ok": False,
               "reason": unsanitized_reason or "convert_smiles_parse_fail"}
        if len(_SIDE_PARSE_CACHE) < 250_000:
            _SIDE_PARSE_CACHE[raw_side] = res
        return res

    got_maps = {a.GetAtomMapNum() for a in mol.GetAtoms()
                if a.GetAtomMapNum()}
    if want_maps != got_maps:
        res = {"smarts_ok": True, "n_atoms": n_atoms, "n_mapped": n_mapped,
               "converted_ok": False, "reason": "convert_map_lost"}
        if len(_SIDE_PARSE_CACHE) < 250_000:
            _SIDE_PARSE_CACHE[raw_side] = res
        return res

    res = {
        "smarts_ok": True,
        "n_atoms": n_atoms,
        "n_mapped": n_mapped,
        "converted_ok": True,
        "converted": converted,
        "sanitized": sanitized,
        "unsanitized_reason": unsanitized_reason,
    }
    if len(_SIDE_PARSE_CACHE) < 250_000:
        _SIDE_PARSE_CACHE[raw_side] = res
    return res


def process_record(rec: dict, *,
                   allow_unsanitized_fragments: bool = True) -> dict:
    """Pure per-record parse/convert; never raises (returns outcome dict).

    When ``allow_unsanitized_fragments=True`` (Phase 2b default), rules whose
    converted SMILES fail Kekulization because the local radius cuts through an
    aromatic ring (``lhs_convert_aromatic_fragment`` / ``rhs_convert_aromatic_fragment``)
    are still indexed (with ``both_sides_sanitized=False`` and ``FLAG_BOTH_SIDES_SANITIZED``
    cleared) so they can be retrieved by substructure/Morgan search and
    compiled via ``bridge_occurrence_to_spec``.
    When ``allow_unsanitized_fragments=False``, reproduces strict n004 stage-1
    skip behavior.
    """
    try:
        return _process_record(
            rec, allow_unsanitized_fragments=allow_unsanitized_fragments)
    except Exception as exc:  # noqa: BLE001 — reported, never hidden
        return {"status": "skip", "reason": "internal_error",
                "error": f"{type(exc).__name__}:{str(exc)[:200]}"}


def _process_record_strict(rec: dict) -> dict:
    return process_record(rec, allow_unsanitized_fragments=False)


def _process_record(rec: dict, *,
                    allow_unsanitized_fragments: bool = True) -> dict:
    tid = str(rec.get("TEMPLATE_ID") or "").strip()
    tpl = rec.get("TEMPLATE")
    rmin = rec.get("RADIUS_MIN")
    rmax = rec.get("RADIUS_MAX")
    radii = rec.get("RADII") or []
    ecs = rec.get("ECS") or []
    reactions = rec.get("REACTIONS") or []
    score = rec.get("SCORE") or []
    valid = rec.get("VALID", True)

    out = {
        "template_id": tid,
        "radius_min": int(rmin) if isinstance(rmin, (int, float)) else 0,
        "radius_max": int(rmax) if isinstance(rmax, (int, float)) else 0,
        "radii": [int(x) for x in radii if isinstance(x, (int, float))],
        "ecs": [str(x) for x in ecs],
        "reactions": [str(x) for x in reactions],
        "score": [float(x) for x in score if isinstance(x, (int, float))],
        "valid": bool(valid),
        "status": "skip", "reason": None,
        "lhs_smarts": "", "rhs_smarts": "",
        "lhs": "", "rhs": "", "lhs_canonical": "",
        "lhs_components": 0, "rhs_components": 0,
        "lhs_atoms": 0, "rhs_atoms": 0,
        "lhs_mapped_atoms": 0, "rhs_mapped_atoms": 0,
        "lhs_smarts_ok": False, "rhs_smarts_ok": False,
        "both_sides_sanitized": False,
        "unsanitized_reason": None,
        "flags": 0,
    }
    if not tid:
        out["reason"] = "no_template_id"
        return out
    if not isinstance(tpl, str) or not tpl.strip():
        out["reason"] = "no_template"
        return out
    arrows = tpl.count(">>")
    if arrows == 0:
        out["reason"] = "no_arrow"
        return out
    if arrows > 1:
        out["reason"] = "multi_arrow"
        return out
    lhs_raw, rhs_raw = tpl.split(">>", 1)
    lhs_raw = normalize_side_smarts(lhs_raw)
    rhs_raw = normalize_side_smarts(rhs_raw)
    out["lhs_smarts"] = lhs_raw
    out["rhs_smarts"] = rhs_raw
    if not lhs_raw:
        out["reason"] = "empty_lhs"
        return out
    if not rhs_raw:
        out["reason"] = "empty_rhs"
        return out
    out["lhs_components"] = len(split_components(lhs_raw))
    out["rhs_components"] = len(split_components(rhs_raw))
    if not out["valid"]:
        out["reason"] = "valid_false"
        return out

    l_info = _analyze_side_cached(lhs_raw, "lhs")
    r_info = _analyze_side_cached(rhs_raw, "rhs")
    out["lhs_smarts_ok"] = bool(l_info.get("smarts_ok"))
    out["rhs_smarts_ok"] = bool(r_info.get("smarts_ok"))
    if not out["lhs_smarts_ok"]:
        out["reason"] = "lhs_smarts_unparseable"
        return out
    if not out["rhs_smarts_ok"]:
        out["reason"] = "rhs_smarts_unparseable"
        return out

    for side, info in (("lhs", l_info), ("rhs", r_info)):
        out[f"{side}_atoms"] = int(info["n_atoms"])
        out[f"{side}_mapped_atoms"] = int(info["n_mapped"])
        if info["n_atoms"] and info["n_mapped"] == info["n_atoms"]:
            out["flags"] |= (FLAG_LHS_ALL_MAPPED if side == "lhs"
                             else FLAG_RHS_ALL_MAPPED)
    if out["rhs_components"] > 1:
        out["flags"] |= FLAG_MULTI_COMPONENT_RHS

    for side, info in (("lhs", l_info), ("rhs", r_info)):
        if not info.get("converted_ok"):
            out["reason"] = f"{side}_{info['reason']}"
            return out
        if not info.get("sanitized") and not allow_unsanitized_fragments:
            out["reason"] = f"{side}_{info['unsanitized_reason']}"
            return out
        if not info.get("sanitized") and out["unsanitized_reason"] is None:
            out["unsanitized_reason"] = f"{side}_{info['unsanitized_reason']}"
        converted = str(info["converted"])
        out[side] = converted
        out["flags"] |= (FLAG_CONVERTED_LHS_FROM_SMARTS if side == "lhs"
                         else FLAG_CONVERTED_RHS_FROM_SMARTS)
        if side == "lhs":
            out["lhs_canonical"] = converted

    if out["lhs_mapped_atoms"] == 0:
        out["reason"] = "lhs_unmapped"
        return out
    if out["rhs_mapped_atoms"] == 0:
        out["reason"] = "rhs_unmapped"
        return out

    both_san = bool(l_info.get("sanitized") and r_info.get("sanitized"))
    out["both_sides_sanitized"] = both_san
    if both_san:
        out["flags"] |= FLAG_BOTH_SIDES_SANITIZED
    out["status"] = "indexed"
    out["flags"] |= FLAG_INDEXED
    if out["valid"]:
        out["flags"] |= FLAG_VALID
    return out


# ---------------------------------------------------------------- fingerprints


_POPCOUNT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def _mol_for_fp(smiles: str):
    """Parse sanitized SMILES or fallback to property-cached unsanitized fragment."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is not None:
        return mol
    mol = Chem.MolFromSmiles(smiles, sanitize=False)
    if mol is not None:
        try:
            mol.UpdatePropertyCache(strict=False)
            Chem.FastFindRings(mol)
        except Exception:  # noqa: BLE001
            return None
    return mol


def fp_to_packed(mol) -> tuple[np.ndarray, int]:
    fp = rdMolDescriptors.GetMorganFingerprintAsBitVect(
        mol, FP_RADIUS, nBits=FP_BITS, useChirality=FP_CHIRALITY)
    bits = np.frombuffer(fp.ToBitString().encode("ascii"), dtype=np.uint8) - 48
    return np.packbits(bits), int(fp.GetNumOnBits())


def pat_fp_to_packed(mol) -> tuple[np.ndarray, int]:
    fp = Chem.PatternFingerprint(mol, fpSize=FP_BITS)
    bits = np.frombuffer(fp.ToBitString().encode("ascii"), dtype=np.uint8) - 48
    return np.packbits(bits), int(fp.GetNumOnBits())


def worker_fp(chunk: list[tuple[str, str]]
              ) -> list[tuple[bytes | None, int, int, bytes | None, int]]:
    out: list[tuple[bytes | None, int, int, bytes | None, int]] = []
    for smiles, smarts in chunk:
        mol = _mol_for_fp(smiles)
        if mol is None:
            out.append((None, 0, 0, None, 0))
            continue
        packed, nbits = fp_to_packed(mol)
        qmol = Chem.MolFromSmarts(smarts) if smarts else None
        if qmol is None:
            qmol = mol
        pat_packed, pat_nbits = pat_fp_to_packed(qmol)
        out.append((packed.tobytes(), nbits, mol.GetNumHeavyAtoms(),
                    pat_packed.tobytes(), pat_nbits))
    return out


def tanimoto_vs_matrix(query_packed: np.ndarray,
                       matrix: np.ndarray) -> np.ndarray:
    """Vectorised Tanimoto of one packed fp (uint8 [B]) vs uint8 [N, B]."""
    and_bits = np.bitwise_and(matrix, query_packed)
    or_bits = np.bitwise_or(matrix, query_packed)
    a = _POPCOUNT[and_bits].sum(axis=1, dtype=np.int64)
    b = _POPCOUNT[or_bits].sum(axis=1, dtype=np.int64)
    return a / np.maximum(b, 1)


def tanimoto_and_containment_vs_matrix(
    query_packed: np.ndarray,
    query_nbits: int,
    matrix: np.ndarray,
    matrix_nbits: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Simultaneous Tanimoto and template-in-substrate containment."""
    nz = np.flatnonzero(query_packed)
    if nz.size == 0:
        a = np.zeros(len(matrix), dtype=np.int32)
    else:
        and_bits = np.bitwise_and(matrix[:, nz], query_packed[nz])
        a = _POPCOUNT[and_bits].sum(axis=1, dtype=np.int32)
    m_bits = matrix_nbits.astype(np.int32)
    union = m_bits + int(query_nbits) - a
    tanimoto = a / np.maximum(union, 1)
    containment = a / np.maximum(m_bits, 1)
    return tanimoto, containment


# ---------------------------------------------------------------- build


def _sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _load_rhea_cross_map(rhea_source: str | Path | None) -> tuple[
        dict[str, list[str]], dict | None]:
    """Map TEMPLATE string -> RHEA reaction IDs from rhea.json for MNX cross-map."""
    if rhea_source is None:
        return {}, None
    p = Path(rhea_source)
    if not p.is_file():
        return {}, None
    with open(p, encoding="utf-8") as f:
        records = json.load(f)
    if not isinstance(records, list):
        return {}, None
    tpl_to_rhea: dict[str, list[str]] = {}
    for rec in records:
        tpl = rec.get("TEMPLATE")
        if not isinstance(tpl, str) or ">>" not in tpl:
            continue
        l_raw, r_raw = tpl.split(">>", 1)
        norm_tpl = f"{normalize_side_smarts(l_raw)}>>{normalize_side_smarts(r_raw)}"
        rxns = [str(x) for x in (rec.get("REACTIONS") or []) if x]
        if rxns:
            existing = tpl_to_rhea.setdefault(norm_tpl, [])
            for rx in rxns:
                if rx not in existing:
                    existing.append(rx)
            # Also index by raw TEMPLATE string
            tpl_to_rhea.setdefault(tpl, existing)
    meta = {
        "rhea_source_file": p.name,
        "rhea_source_sha256": _sha256_file(p),
        "rhea_source_bytes": int(p.stat().st_size),
        "rhea_templates_count": len(records),
    }
    return tpl_to_rhea, meta


def build_index(
    source: str | Path,
    out_dir: str | Path,
    *,
    library: str | None = None,
    rhea_cross_map_source: str | Path | None = None,
    allow_unsanitized_fragments: bool = True,
    write_jsonl_sidecar: bool = True,
    meta_filename: str | None = None,
    npz_filename: str | None = None,
    workers: int = 8,
    max_skip_ratio: float = 0.25,
    chunk_size: int = 1000,
    progress: bool = True,
) -> dict:
    """Read the library, build the index artifacts, return stats + identity."""
    t_all = time.time()
    source = Path(source)
    out_dir = Path(out_dir)
    if not source.is_file():
        raise RetroAssetError(f"来源库缺失:{source}",
                              {"source": str(source)})
    out_dir.mkdir(parents=True, exist_ok=True)

    lib_name = library
    if not lib_name:
        sname = source.name.lower()
        if "metanetx" in sname or "mnx" in sname:
            lib_name = "mnx"
        else:
            lib_name = RETRO_LIBRARY

    # Auto-discover rhea.json for cross-mapping when building mnx
    if rhea_cross_map_source is None and lib_name in ("mnx", "metanetx"):
        cand = source.parent / "rhea.json"
        if cand.is_file():
            rhea_cross_map_source = cand
    tpl_to_rhea, cross_map_meta = _load_rhea_cross_map(rhea_cross_map_source)

    t0 = time.time()
    with open(source, encoding="utf-8") as f:
        records = json.load(f)
    if not isinstance(records, list):
        raise RetroAssetError(
            "来源库不是 JSON 数组(RetroRules 导出约定)",
            {"source": str(source), "type": type(records).__name__})
    load_s = time.time() - t0
    n_templates = len(records)
    if progress:
        print(f"[load:{lib_name}] n={n_templates} in {load_s:.1f}s",
              flush=True)

    # ---- pass 1: parse / convert (parallel) ----
    t0 = time.time()
    outcomes: list[dict] = [None] * n_templates  # type: ignore[list-item]
    skip_counts: dict[str, int] = {}
    seen_tids: set[str] = set()
    ctx = get_context("fork")
    worker_fn = (process_record if allow_unsanitized_fragments
                 else _process_record_strict)
    if workers and workers > 1 and n_templates > 1000:
        with ctx.Pool(workers) as pool:
            it = pool.imap(worker_fn, records, chunksize=chunk_size)
            for i, outcome in enumerate(it):
                outcomes[i] = outcome
    else:
        for i, rec in enumerate(records):
            outcomes[i] = worker_fn(rec)

    for outcome in outcomes:
        if outcome["status"] != "indexed":
            _bump(skip_counts, str(outcome["reason"] or "internal_error"))
            continue
        tid = outcome["template_id"]
        if tid in seen_tids:
            outcome["status"] = "skip"
            outcome["reason"] = "duplicate_template_id"
            _bump(skip_counts, "duplicate_template_id")
            continue
        seen_tids.add(tid)
    convert_s = time.time() - t0
    if progress:
        print(f"[convert:{lib_name}] in {convert_s:.1f}s skips={skip_counts}",
              flush=True)

    # ---- aggregate stats + unique lhs ----
    indexed = [o for o in outcomes if o["status"] == "indexed"]
    n_indexed = len(indexed)
    n_skipped = n_templates - n_indexed
    skip_ratio = (n_skipped / n_templates) if n_templates else 0.0
    if n_indexed == 0:
        raise RetroAssetError("索引为空:没有任何模板通过解析/转换",
                              {"source": str(source)})
    if skip_ratio > float(max_skip_ratio):
        raise RetroAssetError(
            f"跳过率 {skip_ratio:.4f} 超过上限 {max_skip_ratio}"
            "(fail-closed:不发布静默退化的索引)",
            {"n_templates": n_templates, "n_skipped": n_skipped,
             "skip_reasons": skip_counts})

    hist = {
        "radius_min": {}, "radius_max": {}, "radii_len": {},
        "ecs_count": {}, "reactions_count": {},
        "lhs_components": {}, "rhs_components": {},
        "lhs_atoms": {}, "rhs_atoms": {},
        "lhs_map_fraction": {}, "rhs_map_fraction": {},
        "fp_nbits": {}, "template_len": [],
    }
    radii_counts: Counter = Counter()
    sanitized_radii_counts: Counter = Counter()
    unsanitized_reasons: Counter = Counter()
    token_inventory = {k: 0 for k in
                       (";H", ";+", ";-", ";@", ";R", ";r", ";x", ";X",
                        ";v", "~", "$", "*", "!", "&")}
    for o in indexed:
        _hist(hist["radius_min"], o["radius_min"], 10)
        _hist(hist["radius_max"], o["radius_max"], 10)
        _hist(hist["radii_len"], len(o["radii"]), 11)
        _hist(hist["ecs_count"], len(o["ecs"]), 5)
        _hist(hist["reactions_count"], len(o["reactions"]), 5)
        _hist(hist["lhs_components"], o["lhs_components"], 5)
        _hist(hist["rhs_components"], o["rhs_components"], 5)
        _hist(hist["lhs_atoms"], o["lhs_atoms"], 20)
        _hist(hist["rhs_atoms"], o["rhs_atoms"], 20)
        for rad in set(o["radii"]):
            radii_counts[int(rad)] += 1
            if o.get("both_sides_sanitized"):
                sanitized_radii_counts[int(rad)] += 1
        if not o.get("both_sides_sanitized"):
            unsanitized_reasons[str(o.get("unsanitized_reason") or "other")] += 1
        lf = (o["lhs_mapped_atoms"] / o["lhs_atoms"]) if o["lhs_atoms"] else 0
        rf = (o["rhs_mapped_atoms"] / o["rhs_atoms"]) if o["rhs_atoms"] else 0
        _hist(hist["lhs_map_fraction"], int(round(lf * 20)), 20)
        _hist(hist["rhs_map_fraction"], int(round(rf * 20)), 20)
        tpl = f"{o['lhs_smarts']}>>{o['rhs_smarts']}"
        hist["template_len"].append(len(tpl))
        for tok in token_inventory:
            if tok in tpl:
                token_inventory[tok] += 1

    # contiguous arrays (row order == source order, filtered)
    n = n_indexed
    flags = np.zeros(n, dtype=np.uint8)
    radii_mask = np.zeros(n, dtype=np.uint16)
    radius_min = np.zeros(n, dtype=np.uint8)
    radius_max = np.zeros(n, dtype=np.uint8)
    n_components_lhs = np.zeros(n, dtype=np.int16)
    n_components_rhs = np.zeros(n, dtype=np.int16)
    n_atoms_lhs = np.zeros(n, dtype=np.int16)
    n_atoms_rhs = np.zeros(n, dtype=np.int16)
    n_reactions = np.zeros(n, dtype=np.int32)
    lhs_uid = np.zeros(n, dtype=np.int32)
    tids: list[str] = []
    row_templates: list[dict] = []

    canonical_to_uid: dict[str, int] = {}
    uid_examples: list[str] = []
    uid_smarts: list[str] = []
    uid_counts: list[int] = []
    shared_rhea_count = 0

    for row, o in enumerate(indexed):
        canon = o["lhs_canonical"] or o["lhs"]
        uid = canonical_to_uid.get(canon)
        if uid is None:
            uid = len(uid_examples)
            canonical_to_uid[canon] = uid
            uid_examples.append(canon)
            uid_smarts.append(o["lhs_smarts"])
            uid_counts.append(0)
        uid_counts[uid] += 1
        lhs_uid[row] = uid
        flags[row] = o["flags"]
        radii_mask[row] = _radii_to_mask(o["radii"])
        radius_min[row] = min(int(o["radius_min"]), 255)
        radius_max[row] = min(int(o["radius_max"]), 255)
        n_components_lhs[row] = min(int(o["lhs_components"]), 32767)
        n_components_rhs[row] = min(int(o["rhs_components"]), 32767)
        n_atoms_lhs[row] = min(int(o["lhs_atoms"]), 32767)
        n_atoms_rhs[row] = min(int(o["rhs_atoms"]), 32767)
        n_reactions[row] = len(o["reactions"])
        tids.append(o["template_id"])

        tpl_str = f"{o['lhs_smarts']}>>{o['rhs_smarts']}"
        rhea_rxns = tpl_to_rhea.get(tpl_str) or []
        if rhea_rxns:
            shared_rhea_count += 1

        row_entry = {
            "row": row,
            "template_id": o["template_id"],
            "template": tpl_str,
            "lhs_mapped_smiles": o["lhs"],
            "rhs_mapped_smiles": o["rhs"],
            "radius_min": o["radius_min"],
            "radius_max": o["radius_max"],
            "radii": o["radii"],
            "ecs": o["ecs"],
            "reactions": o["reactions"],
            "score": o["score"],
            "both_sides_sanitized": bool(o["both_sides_sanitized"]),
        }
        if rhea_rxns:
            row_entry["rhea_reactions"] = list(rhea_rxns)
        if not o["both_sides_sanitized"] and o.get("unsanitized_reason"):
            row_entry["unsanitized_reason"] = str(o["unsanitized_reason"])
        row_templates.append(row_entry)

    n_unique = len(uid_examples)

    # ---- pass 2: fingerprints for unique canonical lhs ----
    t0 = time.time()
    fp = np.zeros((n_unique, FP_BYTES), dtype=np.uint8)
    fp_nbits = np.zeros(n_unique, dtype=np.uint16)
    fp_nheavy = np.zeros(n_unique, dtype=np.uint16)
    pat_fp = np.zeros((n_unique, FP_BYTES), dtype=np.uint8)
    pat_nbits = np.zeros(n_unique, dtype=np.uint16)
    uid_pairs = list(zip(uid_examples, uid_smarts))
    chunks = list(_chunks(uid_pairs, 2000))
    if workers and workers > 1 and len(chunks) > 1:
        with ctx.Pool(workers) as pool:
            results = list(pool.imap(worker_fp, chunks, chunksize=1))
    else:
        results = [worker_fp(c) for c in chunks]
    pos = 0
    fp_fail = 0
    for res in results:
        for packed, nbits, heavy, p_packed, p_nbits in res:
            if packed is None or p_packed is None:
                fp_fail += 1
            else:
                fp[pos] = np.frombuffer(packed, dtype=np.uint8)
                fp_nbits[pos] = nbits
                fp_nheavy[pos] = heavy
                pat_fp[pos] = np.frombuffer(p_packed, dtype=np.uint8)
                pat_nbits[pos] = p_nbits
            pos += 1
    fp_s = time.time() - t0
    if fp_fail:
        raise RetroAssetError(
            f"唯一 lhs 指纹计算失败 {fp_fail} 条",
            {"n_unique_lhs": n_unique, "n_fp_fail": fp_fail})
    if progress:
        print(f"[fp:{lib_name}] unique_lhs={n_unique} in {fp_s:.1f}s",
              flush=True)

    for v in fp_nbits:
        _hist(hist["fp_nbits"], int(v) // 16 * 16, 2048)

    npz_name = npz_filename or INDEX_NPZ
    offsets = np.zeros(n + 1, dtype=np.int64)
    templates_path = out_dir / TEMPLATES_JSONL
    if write_jsonl_sidecar:
        with open(templates_path, "w", encoding="utf-8") as f:
            for row, row_obj in enumerate(row_templates):
                offsets[row] = f.tell()
                f.write(json.dumps(row_obj, ensure_ascii=False,
                                   separators=(",", ":")) + "\n")
            offsets[n] = f.tell()

    index_path = out_dir / npz_name
    np.savez_compressed(
        index_path,
        fp=fp, fp_nbits=fp_nbits, fp_nheavy=fp_nheavy,
        pat_fp=pat_fp, pat_nbits=pat_nbits,
        lhs_uid=lhs_uid, flags=flags,
        radii_mask=radii_mask,
        radius_min=radius_min, radius_max=radius_max,
        n_components_lhs=n_components_lhs,
        n_components_rhs=n_components_rhs,
        n_atoms_lhs=n_atoms_lhs, n_atoms_rhs=n_atoms_rhs,
        n_reactions=n_reactions,
        byte_offsets=offsets,
        unique_lhs=np.asarray(uid_examples, dtype=object),
        unique_lhs_smarts=np.asarray(uid_smarts, dtype=object),
        unique_counts=np.asarray(uid_counts, dtype=np.int32),
        template_ids=np.asarray(tids, dtype=object),
    )

    n_sanitized_both = sum(1 for o in indexed if o.get("both_sides_sanitized"))
    n_unsanitized = n_indexed - n_sanitized_both
    stats = {
        "library": lib_name,
        "source": str(source),
        "loader_version": RETRO_LOADER_VERSION,
        "index_version": RETRO_INDEX_VERSION,
        "fingerprint": {"kind": "morgan", "radius": FP_RADIUS,
                        "bits": FP_BITS, "chirality": FP_CHIRALITY,
                        "metric": "tanimoto", "cmp": "ge",
                        "pattern_fp_bits": FP_BITS},
        "n_templates": n_templates,
        "n_indexed": n_indexed,
        "n_sanitized_both": n_sanitized_both,
        "n_unsanitized_fragment": n_unsanitized,
        "unsanitized_reasons": dict(sorted(unsanitized_reasons.items())),
        "n_skipped": n_skipped,
        "skip_ratio": round(skip_ratio, 6),
        "radii_counts": {str(k): int(v) for k, v in sorted(radii_counts.items())},
        "sanitized_radii_counts": {
            str(k): int(v) for k, v in sorted(sanitized_radii_counts.items())
        },
        "shared_rhea_templates_count": shared_rhea_count,
        "build_policy": {"max_skip_ratio": float(max_skip_ratio),
                         "allow_unsanitized_fragments":
                             bool(allow_unsanitized_fragments),
                         "fail_closed_on_excess_skip": True},
        "skip_reasons": dict(sorted(skip_counts.items())),
        "n_unique_lhs": n_unique,
        "duplicate_lhs_rows": n - n_unique,
        "max_lhs_multiplicity": int(max(uid_counts)) if uid_counts else 0,
        "n_valid_true": sum(1 for o in indexed if o["valid"]),
        "n_valid_false_excluded": skip_counts.get("valid_false", 0),
        "hist": {k: dict(sorted(v.items(), key=lambda kv: kv[0]))
                 for k, v in hist.items() if isinstance(v, dict)},
        "token_inventory_templates": token_inventory,
        "template_len": _percentiles(hist["template_len"]),
        "fp_nbits_percentiles": _percentiles(
            [int(x) for x in fp_nbits.tolist()]),
        "timing_seconds": {
            "load": round(load_s, 2),
            "convert_parallel": round(convert_s, 2),
            "fingerprints_parallel": round(fp_s, 2),
            "total": round(time.time() - t_all, 2),
        },
        "workers": int(workers),
    }

    source_sha = _sha256_file(source)
    artifacts_block = {
        npz_name: {"sha256": _sha256_file(index_path),
                   "bytes": int(index_path.stat().st_size)},
    }
    if write_jsonl_sidecar:
        stats_path = out_dir / STATS_JSON
        stats_path.write_text(
            json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
        artifacts_block[TEMPLATES_JSONL] = {
            "sha256": _sha256_file(templates_path),
            "bytes": int(templates_path.stat().st_size),
        }
        artifacts_block[STATS_JSON] = {
            "sha256": _sha256_file(stats_path),
            "bytes": int(stats_path.stat().st_size),
        }

    manifest = {
        "schema_version": RETRO_SCHEMA_VERSION,
        "library": lib_name,
        "loader_version": RETRO_LOADER_VERSION,
        "index_version": RETRO_INDEX_VERSION,
        "fingerprint": stats["fingerprint"],
        "source": {"file": source.name, "sha256": source_sha,
                   "bytes": int(source.stat().st_size)},
        "cross_map": (dict(cross_map_meta,
                           shared_templates_count=shared_rhea_count)
                      if cross_map_meta else None),
        "artifacts": artifacts_block,
        "build_policy": stats["build_policy"],
        "counts": {
            "n_templates": n_templates,
            "n_indexed": n_indexed,
            "n_sanitized_both": n_sanitized_both,
            "n_unsanitized_fragment": n_unsanitized,
            "n_skipped": n_skipped,
            "n_unique_lhs": n_unique,
            "radii_counts": stats["radii_counts"],
            "sanitized_radii_counts": stats["sanitized_radii_counts"],
            "shared_rhea_templates_count": shared_rhea_count,
        },
        "skip_reasons": stats["skip_reasons"],
        "stats": stats,
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if meta_filename:
        meta_path = out_dir / meta_filename
        meta_payload = dict(manifest)
        meta_payload["templates"] = row_templates
        meta_path.write_text(
            json.dumps(meta_payload, ensure_ascii=False,
                       separators=(",", ":")),
            encoding="utf-8",
        )
        manifest_sha = _sha256_file(meta_path)
    else:
        manifest_path = out_dir / MANIFEST_JSON
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1),
            encoding="utf-8")
        manifest_sha = _sha256_file(manifest_path)

    if progress:
        print(f"[done:{lib_name}] total={time.time() - t_all:.1f}s "
              f"indexed={n_indexed} (sanitized={n_sanitized_both}, "
              f"fragment={n_unsanitized}) unique_lhs={n_unique}", flush=True)
    return {
        "stats": stats,
        "manifest": manifest,
        "identity": identity_from_manifest(
            manifest, manifest_sha256=manifest_sha),
    }


def build_dataset_index(
    dataset: str,
    *,
    raw_dir: str | Path = "assets/retrorules/raw",
    derived_dir: str | Path = "assets/retrorules/derived",
    allow_unsanitized_fragments: bool = True,
    workers: int = 8,
    progress: bool = True,
) -> dict:
    """Build ``<dataset>_retro_index.npz`` and ``<dataset>_retro_index.meta.json``."""
    ds = str(dataset).strip().lower()
    if ds not in DATASET_RAW_FILES:
        raise RetroAssetError(f"未知的 RetroRules 数据集:{dataset!r}",
                              {"dataset": dataset})
    raw_path = Path(raw_dir) / DATASET_RAW_FILES[ds]
    out_dir = Path(derived_dir)
    prefix = DATASET_INDEX_PREFIX[ds]
    rhea_src = Path(raw_dir) / "rhea.json" if ds in ("mnx", "metanetx") else None
    return build_index(
        source=raw_path,
        out_dir=out_dir,
        library=("mnx" if ds in ("mnx", "metanetx") else "rhea"),
        rhea_cross_map_source=rhea_src,
        allow_unsanitized_fragments=allow_unsanitized_fragments,
        write_jsonl_sidecar=False,
        npz_filename=f"{prefix}.npz",
        meta_filename=f"{prefix}.meta.json",
        workers=workers,
        progress=progress,
    )


# ---------------------------------------------------------------- runtime


def identity_from_manifest(manifest: dict, *,
                           manifest_sha256: str) -> dict:
    """Deterministic identity block for build fingerprints (no timestamps)."""
    counts = dict(manifest.get("counts") or {})
    return {
        "mode": "retro_assets",
        "library": str(manifest.get("library") or ""),
        "manifest_sha256": str(manifest_sha256),
        "source_sha256": str((manifest.get("source") or {}).get("sha256", "")),
        "loader_version": str(manifest.get("loader_version") or ""),
        "index_version": str(manifest.get("index_version") or ""),
        "n_templates": int(counts.get("n_templates", 0)),
        "n_indexed": int(counts.get("n_indexed", 0)),
        "n_unique_lhs": int(counts.get("n_unique_lhs", 0)),
    }


def _strip_atom_maps(smiles: str) -> str:
    """Return canonical SMILES with atom map numbers cleared (or '' if unsanitized)."""
    mol = Chem.MolFromSmiles(str(smiles or ""))
    if mol is None:
        return ""
    for atom in mol.GetAtoms():
        atom.SetAtomMapNum(0)
    return Chem.MolToSmiles(mol)


class RetroLibrary:
    """Verified, queryable view over RetroRules index artifacts.

    Supports both:
      1) Phase 2b ``<prefix>_retro_index.npz`` + ``<prefix>_retro_index.meta.json``
      2) n004 directory layout (``retro_manifest.json`` + ``retro_index.npz`` +
         ``retro_templates.jsonl``)
      3) In-memory merged union ``RetroLibrary.from_merged(mnx_lib, rhea_lib)``
         for ``"mnx+rhea"`` (deduplicated by ``TEMPLATE`` string).
    """

    def __init__(self, index_dir: str | Path | None = None, *,
                 source: str | Path | None = None,
                 dataset: str | None = None,
                 meta_path: str | Path | None = None,
                 npz_path: str | Path | None = None,
                 verify_artifacts: bool = True,
                 verify_source: bool = True,
                 _preloaded: dict | None = None) -> None:
        self._smarts_mol_cache: dict[int, object] = {}
        self._unmapped_cache: dict[str, str] = {}
        self._templates_in_memory: list[dict] | None = None
        self._handle = None

        if _preloaded is not None:
            self._init_from_preloaded(_preloaded)
            return

        if index_dir is None and meta_path is None:
            raise RetroAssetError("retro index_dir 未提供", {})

        resolved_dir, resolved_meta, resolved_npz, is_meta_layout = (
            self._locate_files(index_dir, dataset=dataset,
                               meta_path=meta_path, npz_path=npz_path)
        )
        self.index_dir = resolved_dir
        if not resolved_meta.is_file():
            raise RetroAssetError(f"retro manifest 缺失:{resolved_meta}",
                                  {"index_dir": str(self.index_dir)})

        raw_manifest = json.loads(resolved_meta.read_text(encoding="utf-8"))
        for key in ("schema_version", "library", "index_version",
                    "fingerprint", "source", "artifacts", "counts"):
            if key not in raw_manifest:
                raise RetroAssetError(
                    f"retro manifest 缺字段 {key}:{resolved_meta}",
                    {"index_dir": str(self.index_dir)})
        if raw_manifest["schema_version"] != RETRO_SCHEMA_VERSION:
            raise RetroAssetError(
                f"retro manifest schema 不识别:"
                f"{raw_manifest['schema_version']}",
                {"expected": RETRO_SCHEMA_VERSION})
        if raw_manifest["index_version"] != RETRO_INDEX_VERSION:
            raise RetroAssetError(
                f"retro index 版本不匹配:{raw_manifest['index_version']}",
                {"expected": RETRO_INDEX_VERSION})

        if is_meta_layout and "templates" in raw_manifest:
            self._templates_in_memory = raw_manifest.pop("templates")
        self.manifest = raw_manifest
        self.identity = identity_from_manifest(
            self.manifest, manifest_sha256=_sha256_file(resolved_meta))

        # ---- artifact integrity (fail-closed) ----
        self.paths: dict[str, Path] = {}
        for name, meta in (self.manifest.get("artifacts") or {}).items():
            path = self.index_dir / name
            if not path.is_file():
                raise RetroAssetError(f"retro 产物缺失:{path}",
                                      {"artifact": name})
            if verify_artifacts:
                actual = _sha256_file(path)
                if actual != meta.get("sha256"):
                    raise RetroAssetError(
                        f"retro 产物哈希不符:{name}",
                        {"artifact": name, "manifest": meta.get("sha256"),
                         "actual": actual})
                if int(path.stat().st_size) != int(meta.get("bytes", -1)):
                    raise RetroAssetError(
                        f"retro 产物字节数不符:{name}",
                        {"artifact": name, "actual": path.stat().st_size,
                         "manifest": meta.get("bytes")})
            self.paths[name] = path

        npz_target = resolved_npz if resolved_npz.is_file() else (
            self.paths.get(INDEX_NPZ))
        if npz_target is None or not npz_target.is_file():
            raise RetroAssetError("retro 产物清单不完整(缺索引 npz)",
                                  {"artifacts": sorted(self.paths)})
        if not is_meta_layout and TEMPLATES_JSONL not in self.paths:
            raise RetroAssetError("retro 产物清单不完整(缺索引或 sidecar)",
                                  {"artifacts": sorted(self.paths)})

        # ---- source integrity ----
        self.source_path = self._resolve_source(source)
        if verify_source:
            if self.source_path is None:
                raise RetroAssetError(
                    "retro 来源库缺失且未显式提供(--source);"
                    "fail-closed(索引来源不可核对)",
                    {"index_dir": str(self.index_dir)})
            actual = _sha256_file(self.source_path)
            want = str(self.manifest["source"].get("sha256") or "")
            if actual != want:
                raise RetroAssetError(
                    f"retro 来源库哈希不符:{self.source_path}",
                    {"source": str(self.source_path), "manifest": want,
                     "actual": actual})
            if int(self.source_path.stat().st_size) != int(
                    self.manifest["source"].get("bytes", -1)):
                raise RetroAssetError(
                    f"retro 来源库字节数不符:{self.source_path}",
                    {"source": str(self.source_path)})

        # ---- arrays ----
        with np.load(npz_target, allow_pickle=True) as data:
            self.fp = data["fp"]
            self.fp_nbits = data["fp_nbits"]
            self.fp_nheavy = data["fp_nheavy"]
            self.pat_fp = (data["pat_fp"] if "pat_fp" in data
                           else np.zeros_like(self.fp))
            self.pat_nbits = (data["pat_nbits"] if "pat_nbits" in data
                              else np.zeros_like(self.fp_nbits))
            self.lhs_uid = data["lhs_uid"]
            self.flags = data["flags"]
            self.radius_min = data["radius_min"]
            self.radius_max = data["radius_max"]
            self.radii_mask = (
                data["radii_mask"] if "radii_mask" in data
                else self._derive_radii_mask_fallback()
            )
            self.n_components_lhs = (
                data["n_components_lhs"] if "n_components_lhs" in data
                else np.ones(len(self.lhs_uid), dtype=np.int16)
            )
            self.n_components_rhs = data["n_components_rhs"]
            self.n_atoms_lhs = data["n_atoms_lhs"]
            self.n_atoms_rhs = data["n_atoms_rhs"]
            self.n_reactions = (
                data["n_reactions"] if "n_reactions" in data
                else np.ones(len(self.lhs_uid), dtype=np.int32)
            )
            self.byte_offsets = data["byte_offsets"]
            self.unique_lhs = [str(x) for x in data["unique_lhs"]]
            self.unique_lhs_smarts = (
                [str(x) for x in data["unique_lhs_smarts"]]
                if "unique_lhs_smarts" in data else list(self.unique_lhs)
            )
            self.unique_counts = data["unique_counts"]
            self.template_ids = [str(x) for x in data["template_ids"]]

        counts = self.manifest["counts"]
        if len(self.lhs_uid) != int(counts["n_indexed"]):
            raise RetroAssetError(
                "retro 索引行数与 manifest 不符",
                {"npz_rows": len(self.lhs_uid),
                 "manifest": counts["n_indexed"]})
        if len(self.fp) != int(counts["n_unique_lhs"]):
            raise RetroAssetError(
                "retro 指纹行数与 manifest 不符",
                {"npz_fp_rows": len(self.fp),
                 "manifest": counts["n_unique_lhs"]})
        if len(self.byte_offsets) != len(self.lhs_uid) + 1:
            raise RetroAssetError("retro sidecar 偏移表长度不符", {})
        if not is_meta_layout:
            self._handle = open(self.paths[TEMPLATES_JSONL], "rb")
        elif (self._templates_in_memory is None
              or len(self._templates_in_memory) != len(self.lhs_uid)):
            raise RetroAssetError(
                "retro meta.json 模板条目数与索引不符",
                {"meta_templates": len(self._templates_in_memory or []),
                 "npz_rows": len(self.lhs_uid)})

    def _init_from_preloaded(self, pre: dict) -> None:
        self.index_dir = Path(pre["index_dir"])
        self.source_path = pre.get("source_path")
        self.manifest = pre["manifest"]
        self.identity = pre["identity"]
        self.paths = pre.get("paths") or {}
        self.fp = pre["fp"]
        self.fp_nbits = pre["fp_nbits"]
        self.fp_nheavy = pre["fp_nheavy"]
        self.pat_fp = pre["pat_fp"]
        self.pat_nbits = pre["pat_nbits"]
        self.lhs_uid = pre["lhs_uid"]
        self.flags = pre["flags"]
        self.radii_mask = pre["radii_mask"]
        self.radius_min = pre["radius_min"]
        self.radius_max = pre["radius_max"]
        self.n_components_lhs = pre["n_components_lhs"]
        self.n_components_rhs = pre["n_components_rhs"]
        self.n_atoms_lhs = pre["n_atoms_lhs"]
        self.n_atoms_rhs = pre["n_atoms_rhs"]
        self.n_reactions = pre["n_reactions"]
        self.byte_offsets = pre["byte_offsets"]
        self.unique_lhs = pre["unique_lhs"]
        self.unique_lhs_smarts = pre["unique_lhs_smarts"]
        self.unique_counts = pre["unique_counts"]
        self.template_ids = pre["template_ids"]
        self._templates_in_memory = pre["templates"]

    def _locate_files(
        self,
        index_dir: str | Path | None,
        *,
        dataset: str | None,
        meta_path: str | Path | None,
        npz_path: str | Path | None,
    ) -> tuple[Path, Path, Path, bool]:
        if meta_path is not None:
            mp = Path(meta_path)
            base_dir = mp.parent
            np_p = Path(npz_path) if npz_path else (
                base_dir / mp.name.replace(".meta.json", ".npz"))
            return base_dir, mp, np_p, True

        p = Path(index_dir)  # type: ignore[arg-type]
        if p.suffix == ".npz":
            base_dir = p.parent
            mp = base_dir / (p.stem + ".meta.json")
            return base_dir, mp, p, True
        if p.name.endswith(".meta.json"):
            base_dir = p.parent
            np_p = base_dir / p.name.replace(".meta.json", ".npz")
            return base_dir, p, np_p, True

        if dataset:
            ds = str(dataset).strip().lower()
            prefix = DATASET_INDEX_PREFIX.get(ds, f"{ds}_retro_index")
            mp = p / f"{prefix}.meta.json"
            np_p = p / f"{prefix}.npz"
            if mp.is_file():
                return p, mp, np_p, True

        # Check n004 layout first if retro_manifest.json exists
        if (p / MANIFEST_JSON).is_file():
            return p, p / MANIFEST_JSON, p / INDEX_NPZ, False

        # Fallback to rhea_retro_index.meta.json inside index_dir
        for prefix in ("rhea_retro_index", "mnx_retro_index"):
            mp = p / f"{prefix}.meta.json"
            np_p = p / f"{prefix}.npz"
            if mp.is_file():
                return p, mp, np_p, True

        return p, p / MANIFEST_JSON, p / INDEX_NPZ, False

    def _derive_radii_mask_fallback(self) -> np.ndarray:
        n = len(self.lhs_uid)
        masks = np.zeros(n, dtype=np.uint16)
        if self._templates_in_memory is not None:
            for i, meta in enumerate(self._templates_in_memory):
                masks[i] = _radii_to_mask(meta.get("radii") or [])
        else:
            for i in range(n):
                rmin = int(self.radius_min[i])
                rmax = int(self.radius_max[i])
                for r in range(rmin, rmax + 1):
                    if 0 <= r < 16:
                        masks[i] |= (1 << r)
        return masks

    def _resolve_source(self, source: str | Path | None) -> Path | None:
        if source is not None:
            p = Path(source)
            return p if p.is_file() else None
        name = str((self.manifest.get("source") or {}).get("file") or "")
        for candidate in (
            self.index_dir / name,
            self.index_dir.parent / "raw" / name,
            self.index_dir.parent / name,
            self.index_dir.parent.parent / name,
        ):
            if name and candidate.is_file():
                return candidate
        return None

    @classmethod
    def from_merged(cls, primary: "RetroLibrary",
                    secondary: "RetroLibrary", *,
                    library_name: str = "mnx+rhea") -> "RetroLibrary":
        """Merge two RetroLibrary instances deduplicated by TEMPLATE string (`lhs>>rhs`).

        Merges ``radii``, ``radii_mask``, ``radius_min``, ``radius_max``,
        ``reactions`` (preserving both ``MNXR...`` and ``RHEA:xxxx``),
        ``rhea_reactions``, ``ecs``, and ``score``.
        """
        t0 = time.time()
        prim_templates = [primary.row(i) for i in range(len(primary.lhs_uid))]
        sec_templates = [secondary.row(i) for i in range(len(secondary.lhs_uid))]

        tpl_to_row: dict[str, int] = {}
        merged_rows: list[dict] = []
        for idx, rec in enumerate(prim_templates):
            copy_rec = dict(rec)
            copy_rec["row"] = idx
            copy_rec["reactions"] = list(rec.get("reactions") or [])
            copy_rec["rhea_reactions"] = list(rec.get("rhea_reactions") or [])
            copy_rec["ecs"] = list(rec.get("ecs") or [])
            copy_rec["radii"] = list(rec.get("radii") or [])
            copy_rec["score"] = list(rec.get("score") or [])
            tpl_to_row[copy_rec["template"]] = idx
            merged_rows.append(copy_rec)

        flags_list = primary.flags.tolist()
        rmask_list = primary.radii_mask.tolist()
        rmin_list = primary.radius_min.tolist()
        rmax_list = primary.radius_max.tolist()
        ncomp_lhs_list = primary.n_components_lhs.tolist()
        ncomp_rhs_list = primary.n_components_rhs.tolist()
        natoms_lhs_list = primary.n_atoms_lhs.tolist()
        natoms_rhs_list = primary.n_atoms_rhs.tolist()
        nrxns_list = primary.n_reactions.tolist()
        tids_list = list(primary.template_ids)
        lhs_uid_list = primary.lhs_uid.tolist()

        canon_to_uid = {s: i for i, s in enumerate(primary.unique_lhs)}
        unique_lhs = list(primary.unique_lhs)
        unique_lhs_smarts = list(primary.unique_lhs_smarts)
        unique_counts = primary.unique_counts.tolist()
        extra_fp = []
        extra_fp_nbits = []
        extra_fp_nheavy = []
        extra_pat_fp = []
        extra_pat_nbits = []

        n_shared = 0
        for s_row, s_rec in enumerate(sec_templates):
            tpl = s_rec["template"]
            existing_idx = tpl_to_row.get(tpl)
            if existing_idx is not None:
                n_shared += 1
                target = merged_rows[existing_idx]
                merged_radii = sorted(
                    set(target["radii"]) | set(s_rec.get("radii") or []))
                target["radii"] = merged_radii
                if merged_radii:
                    target["radius_min"] = min(merged_radii)
                    target["radius_max"] = max(merged_radii)
                rmask_list[existing_idx] |= int(secondary.radii_mask[s_row])
                rmin_list[existing_idx] = min(
                    int(rmin_list[existing_idx]), int(secondary.radius_min[s_row]))
                rmax_list[existing_idx] = max(
                    int(rmax_list[existing_idx]), int(secondary.radius_max[s_row]))
                for rx in (s_rec.get("reactions") or []):
                    if rx not in target["reactions"]:
                        target["reactions"].append(rx)
                    if str(rx).startswith("RHEA:") and rx not in target["rhea_reactions"]:
                        target["rhea_reactions"].append(rx)
                for ec in (s_rec.get("ecs") or []):
                    if ec not in target["ecs"]:
                        target["ecs"].append(ec)
                nrxns_list[existing_idx] = len(target["reactions"])
                continue

            new_row = len(merged_rows)
            copy_rec = dict(s_rec)
            copy_rec["row"] = new_row
            copy_rec["reactions"] = list(s_rec.get("reactions") or [])
            copy_rec["rhea_reactions"] = [
                r for r in copy_rec["reactions"] if str(r).startswith("RHEA:")
            ]
            tpl_to_row[tpl] = new_row
            merged_rows.append(copy_rec)

            s_uid = int(secondary.lhs_uid[s_row])
            canon = secondary.unique_lhs[s_uid]
            uid = canon_to_uid.get(canon)
            if uid is None:
                uid = len(unique_lhs)
                canon_to_uid[canon] = uid
                unique_lhs.append(canon)
                unique_lhs_smarts.append(secondary.unique_lhs_smarts[s_uid])
                unique_counts.append(0)
                extra_fp.append(secondary.fp[s_uid])
                extra_fp_nbits.append(secondary.fp_nbits[s_uid])
                extra_fp_nheavy.append(secondary.fp_nheavy[s_uid])
                extra_pat_fp.append(secondary.pat_fp[s_uid])
                extra_pat_nbits.append(secondary.pat_nbits[s_uid])
            unique_counts[uid] += 1
            lhs_uid_list.append(uid)
            flags_list.append(int(secondary.flags[s_row]))
            rmask_list.append(int(secondary.radii_mask[s_row]))
            rmin_list.append(int(secondary.radius_min[s_row]))
            rmax_list.append(int(secondary.radius_max[s_row]))
            ncomp_lhs_list.append(int(secondary.n_components_lhs[s_row]))
            ncomp_rhs_list.append(int(secondary.n_components_rhs[s_row]))
            natoms_lhs_list.append(int(secondary.n_atoms_lhs[s_row]))
            natoms_rhs_list.append(int(secondary.n_atoms_rhs[s_row]))
            nrxns_list.append(int(secondary.n_reactions[s_row]))
            tids_list.append(str(secondary.template_ids[s_row]))

        if extra_fp:
            fp = np.vstack([primary.fp, np.asarray(extra_fp, dtype=np.uint8)])
            fp_nbits = np.concatenate([
                primary.fp_nbits, np.asarray(extra_fp_nbits, dtype=np.uint16)])
            fp_nheavy = np.concatenate([
                primary.fp_nheavy, np.asarray(extra_fp_nheavy, dtype=np.uint16)])
            pat_fp = np.vstack([
                primary.pat_fp, np.asarray(extra_pat_fp, dtype=np.uint8)])
            pat_nbits = np.concatenate([
                primary.pat_nbits, np.asarray(extra_pat_nbits, dtype=np.uint16)])
        else:
            fp = primary.fp
            fp_nbits = primary.fp_nbits
            fp_nheavy = primary.fp_nheavy
            pat_fp = primary.pat_fp
            pat_nbits = primary.pat_nbits

        n_total = len(merged_rows)
        comb_sha = hashlib.sha256(
            f"{primary.identity['manifest_sha256']}+{secondary.identity['manifest_sha256']}"
            .encode("utf-8")
        ).hexdigest()
        src_sha = hashlib.sha256(
            f"{primary.identity['source_sha256']}+{secondary.identity['source_sha256']}"
            .encode("utf-8")
        ).hexdigest()
        manifest = {
            "schema_version": RETRO_SCHEMA_VERSION,
            "library": library_name,
            "loader_version": RETRO_LOADER_VERSION,
            "index_version": RETRO_INDEX_VERSION,
            "fingerprint": primary.manifest.get("fingerprint") or {},
            "source": {"file": f"{primary.manifest['source']['file']}+{secondary.manifest['source']['file']}",
                       "sha256": src_sha, "bytes": 0},
            "counts": {
                "n_templates": n_total,
                "n_indexed": n_total,
                "n_skipped": 0,
                "n_unique_lhs": len(unique_lhs),
                "n_shared_templates": n_shared,
                "merge_elapsed_s": round(time.time() - t0, 3),
            },
        }
        preloaded = {
            "index_dir": primary.index_dir,
            "source_path": primary.source_path,
            "manifest": manifest,
            "identity": identity_from_manifest(manifest, manifest_sha256=comb_sha),
            "fp": fp,
            "fp_nbits": fp_nbits,
            "fp_nheavy": fp_nheavy,
            "pat_fp": pat_fp,
            "pat_nbits": pat_nbits,
            "lhs_uid": np.asarray(lhs_uid_list, dtype=np.int32),
            "flags": np.asarray(flags_list, dtype=np.uint8),
            "radii_mask": np.asarray(rmask_list, dtype=np.uint16),
            "radius_min": np.asarray(rmin_list, dtype=np.uint8),
            "radius_max": np.asarray(rmax_list, dtype=np.uint8),
            "n_components_lhs": np.asarray(ncomp_lhs_list, dtype=np.int16),
            "n_components_rhs": np.asarray(ncomp_rhs_list, dtype=np.int16),
            "n_atoms_lhs": np.asarray(natoms_lhs_list, dtype=np.int16),
            "n_atoms_rhs": np.asarray(natoms_rhs_list, dtype=np.int16),
            "n_reactions": np.asarray(nrxns_list, dtype=np.int32),
            "byte_offsets": np.zeros(n_total + 1, dtype=np.int64),
            "unique_lhs": unique_lhs,
            "unique_lhs_smarts": unique_lhs_smarts,
            "unique_counts": np.asarray(unique_counts, dtype=np.int32),
            "template_ids": tids_list,
            "templates": merged_rows,
        }
        return cls(_preloaded=preloaded)

    # ------------------------------------------------------------ accessors

    def row(self, row: int) -> dict:
        if row < 0 or row >= len(self.lhs_uid):
            raise IndexError(row)
        if self._templates_in_memory is not None:
            return self._templates_in_memory[row]
        self._handle.seek(int(self.byte_offsets[row]))  # type: ignore[union-attr]
        line = self._handle.readline()  # type: ignore[union-attr]
        return json.loads(line.decode("utf-8"))

    def fp_of(self, smiles: str):
        mol = _mol_for_fp(smiles)
        if mol is None:
            return None
        packed, nbits = fp_to_packed(mol)
        return packed, nbits

    def _query_mol_for_uid(self, uid: int):
        q = self._smarts_mol_cache.get(uid)
        if q is not None:
            return q
        smarts = self.unique_lhs_smarts[uid]
        q = Chem.MolFromSmarts(smarts)
        if len(self._smarts_mol_cache) < 100_000:
            self._smarts_mol_cache[uid] = q
        return q

    def _unmapped_smiles(self, mapped_smiles: str) -> str:
        cached = self._unmapped_cache.get(mapped_smiles)
        if cached is not None:
            return cached
        res = _strip_atom_maps(mapped_smiles)
        if len(self._unmapped_cache) < 100_000:
            self._unmapped_cache[mapped_smiles] = res
        return res

    def _radii_row_mask(
        self,
        *,
        allowed_radii: set[int] | list[int] | tuple[int, ...] | None = None,
        radius_min: int | None = None,
        radius_max: int | None = None,
        include_nonvalid: bool = False,
        require_sanitized: bool = False,
    ) -> np.ndarray:
        mask = np.ones(len(self.lhs_uid), dtype=bool)
        if not include_nonvalid:
            mask &= (self.flags & FLAG_INDEXED).astype(bool)
        if require_sanitized:
            mask &= (self.flags & FLAG_BOTH_SIDES_SANITIZED).astype(bool)
        if allowed_radii is not None:
            want_bits = _radii_to_mask([int(r) for r in allowed_radii])
            mask &= (self.radii_mask & want_bits) != 0
        if radius_min is not None:
            mask &= (self.radius_max >= int(radius_min))
        if radius_max is not None:
            mask &= (self.radius_min <= int(radius_max))
        return mask

    def search(
        self,
        substrate_smiles: str,
        *,
        threshold: float = 0.45,
        top_k: int = 20,
        allowed_radii: set[int] | list[int] | tuple[int, ...] | None = None,
        radius_min: int | None = None,
        radius_max: int | None = None,
        mode: str = "tanimoto",
        dedupe_same_lhs: bool | None = None,
        max_per_lhs: int | None = None,
        require_sanitized: bool | None = None,
        include_nonvalid: bool = False,
    ) -> list[dict]:
        """Retrieve RetroRules templates for ``substrate_smiles``.

        Supported ``mode`` values:
          * ``"tanimoto"`` (default on ``RetroLibrary.search`` for n004
            compatibility): Morgan r2 Tanimoto >= ``threshold``, ordered by
            ``(-similarity, -radius_max, row)``.
          * ``"substruct"``: exact substructure match of single-component
            ``lhs_smarts`` on ``substrate_smiles`` (screened by 2048-bit
            ``PatternFingerprint`` containment with zero false negatives),
            ordered by ``(-similarity, -n_atoms_lhs, -n_reactions, -radius_max, row)``.
          * ``"containment"``: Morgan r2 containment
            ``|FP(lhs) & FP(sub)| / |FP(lhs)| >= threshold``, ordered by
            ``(-containment, -similarity, -radius_max, row)``.
          * ``"hybrid"``: union of ``"tanimoto"`` (for sanitized whole/large
            donor templates) and ``"substruct"`` (for exact substructure &
            small-radius ``r=2, 4, 6`` rules), deduplicated by row.
        """
        if top_k <= 0:
            return []
        smol = Chem.MolFromSmiles(str(substrate_smiles or ""))
        if smol is None:
            return []

        mode_norm = str(mode or "tanimoto").strip().lower()
        if dedupe_same_lhs is None:
            dedupe_same_lhs = (mode_norm == "tanimoto")
        if require_sanitized is None:
            require_sanitized = (mode_norm == "tanimoto")

        query_packed, query_nbits = fp_to_packed(smol)
        sims, conts = tanimoto_and_containment_vs_matrix(
            query_packed, query_nbits, self.fp, self.fp_nbits)

        base_mask = self._radii_row_mask(
            allowed_radii=allowed_radii,
            radius_min=radius_min,
            radius_max=radius_max,
            include_nonvalid=include_nonvalid,
            require_sanitized=bool(require_sanitized),
        )

        if mode_norm == "tanimoto":
            if not (0.0 < threshold <= 1.0):
                return []
            uid_hit = sims >= float(threshold)
            mask = base_mask & uid_hit[self.lhs_uid]
            rows = np.flatnonzero(mask)
            if rows.size == 0:
                return []
            row_sims = sims[self.lhs_uid]
            order = np.lexsort((rows, -self.radius_max[rows],
                                -np.round(row_sims[rows], 6)))
            return self._collect_hits(
                rows[order], sims=sims, conts=conts,
                top_k=int(top_k), dedupe_same_lhs=bool(dedupe_same_lhs),
                max_per_lhs=max_per_lhs, match_kind="tanimoto")

        if mode_norm == "containment":
            if not (0.0 < threshold <= 1.0):
                return []
            uid_hit = conts >= float(threshold)
            mask = base_mask & uid_hit[self.lhs_uid]
            rows = np.flatnonzero(mask)
            if rows.size == 0:
                return []
            row_sims = sims[self.lhs_uid]
            row_conts = conts[self.lhs_uid]
            order = np.lexsort((
                rows,
                -self.radius_max[rows],
                -np.round(row_sims[rows], 6),
                -np.round(row_conts[rows], 6),
            ))
            return self._collect_hits(
                rows[order], sims=sims, conts=conts,
                top_k=int(top_k), dedupe_same_lhs=bool(dedupe_same_lhs),
                max_per_lhs=max_per_lhs, match_kind="containment")

        if mode_norm == "substruct":
            sub_rows = self._substruct_matching_rows(smol, base_mask)
            if sub_rows.size == 0:
                return []
            row_sims = sims[self.lhs_uid]
            order = np.lexsort((
                sub_rows,
                -self.radius_max[sub_rows],
                -self.n_reactions[sub_rows],
                -self.n_atoms_lhs[sub_rows],
                -np.round(row_sims[sub_rows], 6),
            ))
            return self._collect_hits(
                sub_rows[order], sims=sims, conts=conts,
                top_k=int(top_k), dedupe_same_lhs=bool(dedupe_same_lhs),
                max_per_lhs=max_per_lhs, match_kind="substruct")

        if mode_norm == "hybrid":
            # 1) Tanimoto branch (on sanitized rules >= threshold)
            tan_mask = self._radii_row_mask(
                allowed_radii=allowed_radii,
                radius_min=radius_min,
                radius_max=radius_max,
                include_nonvalid=include_nonvalid,
                require_sanitized=True,
            )
            if 0.0 < threshold <= 1.0:
                tan_rows = np.flatnonzero(tan_mask & (sims >= float(threshold))[self.lhs_uid])
            else:
                tan_rows = np.array([], dtype=np.int64)
            if tan_rows.size > 0:
                row_sims = sims[self.lhs_uid]
                t_order = np.lexsort((
                    tan_rows,
                    -self.radius_max[tan_rows],
                    -np.round(row_sims[tan_rows], 6),
                ))
                tan_sorted = tan_rows[t_order]
            else:
                tan_sorted = np.array([], dtype=np.int64)

            # 2) Substructure branch (includes unsanitized fragments at r=2,4,6)
            sub_mask = self._radii_row_mask(
                allowed_radii=allowed_radii,
                radius_min=radius_min,
                radius_max=radius_max,
                include_nonvalid=include_nonvalid,
                require_sanitized=False,
            )
            sub_rows = self._substruct_matching_rows(smol, sub_mask)
            if sub_rows.size > 0:
                row_sims = sims[self.lhs_uid]
                s_order = np.lexsort((
                    sub_rows,
                    -self.radius_max[sub_rows],
                    -self.n_reactions[sub_rows],
                    -self.n_atoms_lhs[sub_rows],
                    -np.round(row_sims[sub_rows], 6),
                ))
                sub_sorted = sub_rows[s_order]
            else:
                sub_sorted = np.array([], dtype=np.int64)

            sub_set = set(sub_sorted.tolist())
            combined_rows: list[int] = []
            seen_rows: set[int] = set()
            # Interleave / rank by unified priority: substructure-confirmed
            # high-similarity first, then remaining tanimoto & substruct
            for r in sub_sorted.tolist():
                if r not in seen_rows:
                    seen_rows.add(r)
                    combined_rows.append(r)
            for r in tan_sorted.tolist():
                if r not in seen_rows:
                    seen_rows.add(r)
                    combined_rows.append(r)
            if not combined_rows:
                return []
            comb_arr = np.asarray(combined_rows, dtype=np.int64)
            row_sims = sims[self.lhs_uid]
            is_sub = np.asarray([1 if int(r) in sub_set else 0 for r in comb_arr],
                                dtype=np.int8)
            # Sort by (-is_substruct, -round(sim, 6), -n_atoms_lhs, -n_reactions, -radius_max, row)
            c_order = np.lexsort((
                comb_arr,
                -self.radius_max[comb_arr],
                -self.n_reactions[comb_arr],
                -self.n_atoms_lhs[comb_arr],
                -np.round(row_sims[comb_arr], 6),
                -is_sub,
            ))
            return self._collect_hits(
                comb_arr[c_order], sims=sims, conts=conts,
                top_k=int(top_k), dedupe_same_lhs=bool(dedupe_same_lhs),
                max_per_lhs=max_per_lhs, match_kind="hybrid",
                substruct_rows=sub_set)

        raise ValueError(f"Unknown RetroLibrary search mode: {mode!r}")

    def _substruct_matching_rows(self, smol, base_mask: np.ndarray) -> np.ndarray:
        """Screen single-component LHS rules via PatternFingerprint then verify HasSubstructMatch."""
        single_mask = base_mask & (self.n_components_lhs == 1)
        cand_rows = np.flatnonzero(single_mask)
        if cand_rows.size == 0:
            return np.array([], dtype=np.int64)
        cand_uids = np.unique(self.lhs_uid[cand_rows])
        s_pat, _ = pat_fp_to_packed(smol)
        screen_pass = np.all((self.pat_fp[cand_uids] & ~s_pat) == 0, axis=1)
        screened_uids = cand_uids[screen_pass]
        if screened_uids.size == 0:
            return np.array([], dtype=np.int64)
        matched_uids: set[int] = set()
        for uid in screened_uids.tolist():
            qmol = self._query_mol_for_uid(int(uid))
            if qmol is not None and smol.HasSubstructMatch(qmol):
                matched_uids.add(int(uid))
        if not matched_uids:
            return np.array([], dtype=np.int64)
        uid_hit = np.zeros(len(self.unique_lhs), dtype=bool)
        uid_hit[list(matched_uids)] = True
        return np.flatnonzero(single_mask & uid_hit[self.lhs_uid])

    def _collect_hits(
        self,
        ordered_rows: np.ndarray,
        *,
        sims: np.ndarray,
        conts: np.ndarray,
        top_k: int,
        dedupe_same_lhs: bool,
        max_per_lhs: int | None,
        match_kind: str,
        substruct_rows: set[int] | None = None,
    ) -> list[dict]:
        out: list[dict] = []
        uid_counts: dict[int, int] = {}
        for row_val in ordered_rows:
            row = int(row_val)
            uid = int(self.lhs_uid[row])
            prev_c = uid_counts.get(uid, 0)
            if dedupe_same_lhs and prev_c >= 1:
                continue
            if max_per_lhs is not None and prev_c >= int(max_per_lhs):
                continue
            uid_counts[uid] = prev_c + 1
            meta = self.row(row)
            lhs_smarts, _, rhs_smarts = meta["template"].partition(">>")
            rxns = list(meta.get("reactions") or [])
            rhea_rxns = list(meta.get("rhea_reactions") or [
                r for r in rxns if str(r).startswith("RHEA:")
            ])
            parent_rxns = list(rxns)
            for rr in rhea_rxns:
                if rr not in parent_rxns:
                    parent_rxns.append(rr)
            both_san = bool(meta.get(
                "both_sides_sanitized",
                bool(self.flags[row] & FLAG_BOTH_SIDES_SANITIZED),
            ))
            lhs_map_smi = str(meta.get("lhs_mapped_smiles") or "")
            rhs_map_smi = str(meta.get("rhs_mapped_smiles") or "")
            is_sub = (True if match_kind == "substruct"
                      else (row in substruct_rows if substruct_rows is not None
                            else False))
            out.append({
                "row": row,
                "lhs_uid": uid,
                "template_id": meta["template_id"],
                "template": meta["template"],
                "similarity": round(float(sims[uid]), 6),
                "containment": round(float(conts[uid]), 6),
                "similarity_version": RETRO_INDEX_VERSION,
                "similarity_rank": len(out) + 1,
                "retrieval_mode": match_kind,
                "substruct_matched": bool(is_sub),
                "both_sides_sanitized": both_san,
                "n_atoms_lhs": int(self.n_atoms_lhs[row]),
                "n_atoms_rhs": int(self.n_atoms_rhs[row]),
                "radius_min": int(self.radius_min[row]),
                "radius_max": int(self.radius_max[row]),
                "radii": list(meta.get("radii") or []),
                "ecs": list(meta.get("ecs") or []),
                "reactions": rxns,
                "rhea_reactions": rhea_rxns,
                "parent_reaction_ids": parent_rxns,
                "score": list(meta.get("score") or []),
                "lhs_smarts": lhs_smarts,
                "rhs_smarts": rhs_smarts,
                "lhs_mapped_smiles": lhs_map_smi,
                "rhs_mapped_smiles": rhs_map_smi,
                "library": self.identity["library"],
                "asset_sha256": self.identity["source_sha256"],
                "manifest_sha256": self.identity["manifest_sha256"],
            })
            if len(out) >= int(top_k):
                break
        return out

    def selftest(self, n: int = 10, *, seed: int = 20261027) -> dict:
        """Recompute sampled fingerprints and prove the index is exact."""
        import random
        rng = random.Random(seed)
        san_rows = np.flatnonzero(
            (self.flags & FLAG_BOTH_SIDES_SANITIZED).astype(bool)).tolist()
        pool_rows = san_rows if san_rows else list(range(len(self.lhs_uid)))
        rows = sorted(rng.sample(pool_rows, min(n, len(pool_rows))))
        details = []
        ok = 0
        for row in rows:
            meta = self.row(row)
            mol = _mol_for_fp(meta["lhs_mapped_smiles"])
            packed, nbits = fp_to_packed(mol)
            uid = int(self.lhs_uid[row])
            stored = self.fp[uid]
            recomputed_ok = bool(np.array_equal(packed, stored))
            bits_ok = int(nbits) == int(self.fp_nbits[uid])
            self_sim = float(tanimoto_vs_matrix(packed, self.fp[uid:uid + 1])[0])
            hits = self.search(meta["lhs_mapped_smiles"], threshold=0.99,
                               top_k=10, mode="tanimoto")
            top = hits[0] if hits else {}
            hit_uids = [int(h["lhs_uid"]) for h in hits]
            passed = (recomputed_ok and bits_ok and self_sim == 1.0
                      and top.get("similarity") == 1.0)
            ok += int(passed)
            details.append({
                "row": row, "template_id": meta["template_id"],
                "lhs_uid": uid, "fp_equal": recomputed_ok,
                "nbits_equal": bits_ok, "self_similarity": self_sim,
                "sampled_uid_in_topk": uid in hit_uids,
                "rank1_lhs_uid": top.get("lhs_uid"),
                "rank1_template_id": top.get("template_id"),
                "rank1_similarity": top.get("similarity"),
                "passed": passed,
            })
        return {"checked": len(rows), "passed": ok,
                "all_passed": ok == len(rows), "details": details,
                "index_version": RETRO_INDEX_VERSION,
                "manifest_sha256": self.identity["manifest_sha256"]}


# ---------------------------------------------------------------- CLI


def _cmd_build(args) -> int:
    if getattr(args, "dataset", None):
        result = build_dataset_index(
            args.dataset,
            raw_dir=args.raw_dir,
            derived_dir=args.out,
            allow_unsanitized_fragments=not args.strict_sanitized_only,
            workers=args.workers,
            progress=not args.quiet,
        )
    else:
        result = build_index(
            args.source,
            args.out,
            allow_unsanitized_fragments=not args.strict_sanitized_only,
            workers=args.workers,
            max_skip_ratio=args.max_skip_ratio,
            progress=not args.quiet,
        )
    print(json.dumps(result["identity"], ensure_ascii=False, indent=1))
    return 0


def _cmd_verify(args) -> int:
    lib = RetroLibrary(args.index_dir, source=args.source,
                       dataset=args.dataset,
                       verify_artifacts=True, verify_source=True)
    out = {"ok": True, "identity": lib.identity,
           "n_rows": int(len(lib.lhs_uid)),
           "n_unique_lhs": int(len(lib.fp))}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def _cmd_selftest(args) -> int:
    lib = RetroLibrary(args.index_dir, source=args.source,
                       dataset=args.dataset)
    result = lib.selftest(args.n)
    if args.out:
        Path(args.out).write_text(
            json.dumps(result, ensure_ascii=False, indent=1),
            encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "details"},
                     ensure_ascii=False, indent=1))
    return 0 if result["all_passed"] else 1


def _cmd_search(args) -> int:
    lib = RetroLibrary(args.index_dir, source=args.source,
                       dataset=args.dataset)
    radii = ([int(x) for x in args.radii.split(",") if x.strip()]
             if getattr(args, "radii", None) else None)
    hits = lib.search(args.smiles, threshold=args.threshold,
                      top_k=args.top_k, allowed_radii=radii,
                      radius_min=args.radius_min,
                      radius_max=args.radius_max,
                      mode=args.mode)
    print(json.dumps({"smiles": args.smiles, "n_hits": len(hits),
                      "hits": hits}, ensure_ascii=False, indent=1))
    return 0


def _cmd_stats(args) -> int:
    t0 = time.time()
    with open(args.source, encoding="utf-8") as f:
        records = json.load(f)
    outcomes = [process_record(r) for r in records]
    skip: dict[str, int] = {}
    for o in outcomes:
        if o["status"] != "indexed":
            _bump(skip, str(o["reason"] or "internal_error"))
    out = {"n_templates": len(records),
           "n_indexed": sum(1 for o in outcomes if o["status"] == "indexed"),
           "n_sanitized_both": sum(
               1 for o in outcomes
               if o["status"] == "indexed" and o.get("both_sides_sanitized")),
           "skip_reasons": skip,
           "timing_seconds": round(time.time() - t0, 1)}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("build", help="build index artifacts from rhea.json / METANETX.json")
    p.add_argument("--source", default=None)
    p.add_argument("--dataset", default=None, choices=["rhea", "mnx", "metanetx"])
    p.add_argument("--raw-dir", default="assets/retrorules/raw")
    p.add_argument("--out", required=True)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--max-skip-ratio", type=float, default=0.25)
    p.add_argument("--strict-sanitized-only", action="store_true")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=_cmd_build)

    p = sub.add_parser("verify", help="verify manifest/artifacts/source")
    p.add_argument("--index-dir", required=True)
    p.add_argument("--dataset", default=None)
    p.add_argument("--source", default=None)
    p.set_defaults(func=_cmd_verify)

    p = sub.add_parser("selftest", help="10-row fingerprint/self-recall check")
    p.add_argument("--index-dir", required=True)
    p.add_argument("--dataset", default=None)
    p.add_argument("--source", default=None)
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--out", default=None)
    p.set_defaults(func=_cmd_selftest)

    p = sub.add_parser("search", help="substrate vs lhs recall")
    p.add_argument("--index-dir", required=True)
    p.add_argument("--dataset", default=None)
    p.add_argument("--source", default=None)
    p.add_argument("--smiles", required=True)
    p.add_argument("--threshold", type=float, default=0.45)
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--radii", default=None, help="comma-separated radii e.g. 2,4,6")
    p.add_argument("--radius-min", type=int, default=None)
    p.add_argument("--radius-max", type=int, default=None)
    p.add_argument("--mode", default="tanimoto",
                   choices=["tanimoto", "substruct", "containment", "hybrid"])
    p.set_defaults(func=_cmd_search)

    p = sub.add_parser("stats", help="parse-only statistics (no artifacts)")
    p.add_argument("--source", required=True)
    p.set_defaults(func=_cmd_stats)

    args = ap.parse_args(argv)
    try:
        return int(args.func(args))
    except RetroAssetError as exc:
        print(json.dumps({"ok": False, "error": str(exc),
                          "detail": exc.detail}, ensure_ascii=False,
                         indent=1), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
