"""retro_source — RetroRules (rhea.json / METANETX.json / mnx+rhea) channel adapter.

Ported from n004 stage 2 (``channel_patch.diff``) and Archive repo
``v44_retrorules_archive_20261012/src/pathway_v43/pollutant/retrorules_source.py``
(``bridge_occurrence_to_spec``), enhanced for Phase 2b offline pool coverage:

* Supports datasets:
    - ``"rhea"``: ``assets/retrorules/derived/rhea_retro_index.npz`` + ``.meta.json``
    - ``"mnx"``: ``assets/retrorules/derived/mnx_retro_index.npz`` + ``.meta.json``
    - ``"mnx+rhea"``: in-memory deduplicated union of ``mnx`` and ``rhea``
      by ``TEMPLATE`` string (``lhs>>rhs``), merging ``radii`` and
      ``reactions`` (``MNXR...`` + ``RHEA:xxxx``).
* Supports exact radius filtering via ``allowed_radii: set[int] | list[int] | None``
  (e.g. ``{6}``, ``{2}``, ``{4}``, ``{2, 4}``) as well as ``radius_min`` /
  ``radius_max``.
* Supports retrieval modes:
    - ``"tanimoto"``: whole-molecule Morgan r2 Tanimoto >= ``threshold``
    - ``"substruct"``: PatternFingerprint-screened ``HasSubstructMatch`` of
      template ``lhs_smarts`` on ``substrate_smiles``
    - ``"containment"``: Morgan r2 template-in-substrate containment
    - ``"hybrid"``: union of ``"substruct"`` and ``"tanimoto"`` so both
      large whole-skeleton templates and small-radius (``r=2, 4, 6``) local
      templates are recalled.
* Supports compilation modes:
    - ``"direct"``: n004 direct ``compile_donor_template`` on converted
      ``mapped_lhs`` / ``mapped_rhs``
    - ``"bridge"``: ``bridge_occurrence_to_spec`` instantiating the template
      on ``substrate_smiles`` via ``rdChemReactions.ReactionFromSmarts`` +
      ``RunReactants`` + ``compile_donor_template`` + strict multiset fidelity
      verification
    - ``"hybrid"``: tries ``"direct"`` first when ``both_sides_sanitized`` is
      True, and falls back to ``"bridge"`` when direct compilation fails
      (e.g. ``no_alignment``, ``ambiguous_alignment``, or unsanitized aromatic
      ring fragments at ``r=2, 4, 6``).
* Provides ``check_retro_self_record`` for self-record leakage detection by
  BOTH reaction ID overlap (``RHEA:xxxx`` / ``MNXR...``, including the 77,144
  templates cross-mapped between ``METANETX.json`` and ``rhea.json``) AND
  strict structure identity match of ``(substrate, principal_product)`` against
  unmapped ``(lhs_mapped_smiles, rhs_mapped_smiles)``.
* Provides ``compile_retro_candidates_for_substrate`` and
  ``merge_retro_specs_into_pool`` (``ranking_mode="append" | "unified_score"``)
  for a 3-line hook in ``s5b_builder.py`` / ``pool_coverage_eval.py``.

Zero model calls, zero network calls, read-only assets.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from rdkit import Chem, RDLogger
from rdkit.Chem import rdChemReactions

from .retro_loader import (
    DATASET_INDEX_PREFIX,
    DATASET_RAW_FILES,
    MANIFEST_JSON,
    RETRO_INDEX_VERSION,
    RETRO_LOADER_VERSION,
    RetroAssetError,
    RetroLibrary,
    _strip_atom_maps,
    split_components,
)

RDLogger.DisableLog("rdApp.*")

# Version keys for builder diagnostics and build identity
RETRO_SOURCE_VERSION = "s5b-retro-source-2-phase2b"
RETRO_COMPILE_ADAPTER_VERSION = "s5b-retro-adapter-2-phase2b"
RETRO_CHANNEL_VERSION = "s5b-retro-channel-2-phase2b"
RETRO_POOL_POLICY_VERSION = "s5b-pool-policy-10"

DEFAULT_LIBRARY = "rhea"
INDEX_DIR_NAME = "retro"
RETRORULES_DIR_NAME = "retrorules"
SOURCE_FILE_NAME = "rhea.json"


_CENTER_GLOBAL_CACHE: dict[tuple[str, str], tuple[list[int], str, str | None]] = {}
_UNMAPPED_GLOBAL_CACHE: dict[str, str] = {}


def _cached_unmapped(mapped_smiles: str, both_sanitized: bool = True) -> str:
    if not both_sanitized or not mapped_smiles:
        return ""
    cached = _UNMAPPED_GLOBAL_CACHE.get(mapped_smiles)
    if cached is not None:
        return cached
    res = _strip_atom_maps(mapped_smiles)
    if len(_UNMAPPED_GLOBAL_CACHE) < 100_000:
        _UNMAPPED_GLOBAL_CACHE[mapped_smiles] = res
    return res


def _cached_center_global(lhs: str, rhs: str,
                          both_sanitized: bool = True) -> tuple[list[int], str, str | None]:
    if not both_sanitized:
        return [], "unsanitized_fragment_deferred_to_bridge", "unsanitized_fragment"
    key = (lhs, rhs)
    cached = _CENTER_GLOBAL_CACHE.get(key)
    if cached is not None:
        return cached
    res = _derive_center_atoms(lhs, rhs)
    if len(_CENTER_GLOBAL_CACHE) < 100_000:
        _CENTER_GLOBAL_CACHE[key] = res
    return res


@dataclass
class RetroDonorRef:
    """One retrieved retro template, compatible with ``analog_source.DonorRef``."""

    record_id: str
    template_id: str
    mapped_lhs: str
    mapped_rhs: str
    _center_atoms: list[int] | None = field(default=None, repr=False)
    _center_derivation: str | None = field(default=None, repr=False)
    _center_error: str | None = field(default=None, repr=False)
    _center_resolved: bool = field(default=False, repr=False)
    radius_min: int = 0
    radius_max: int = 0
    radii: list[int] = field(default_factory=list)
    similarity: float = 0.0
    containment: float = 0.0
    similarity_version: str = ""
    similarity_rank: int = 0
    retrieval_mode: str = "tanimoto"
    substruct_matched: bool = False
    both_sides_sanitized: bool = True
    n_atoms_lhs: int = 0
    n_atoms_rhs: int = 0
    ecs: list[str] = field(default_factory=list)
    reactions: list[str] = field(default_factory=list)
    rhea_reactions: list[str] = field(default_factory=list)
    parent_reaction_ids: list[str] = field(default_factory=list)
    score: list[float] = field(default_factory=list)
    template: str = ""
    lhs_smarts: str = ""
    rhs_smarts: str = ""
    _lhs_unmapped_smiles: str | None = field(default=None, repr=False)
    _rhs_unmapped_smiles: str | None = field(default=None, repr=False)
    dataset: str = "rhea"
    asset_sha256: str = ""
    manifest_sha256: str = ""
    index: str = "retro_rhea_templates"
    mapping_quality: str = "native_retrorules"

    def _ensure_center(self) -> None:
        if not self._center_resolved:
            c, d, e = _cached_center_global(
                self.mapped_lhs, self.mapped_rhs, self.both_sides_sanitized)
            self._center_atoms = list(c)
            self._center_derivation = d
            self._center_error = e
            self._center_resolved = True

    @property
    def center_atoms(self) -> list[int]:
        self._ensure_center()
        return self._center_atoms or []

    @center_atoms.setter
    def center_atoms(self, value: list[int]) -> None:
        self._center_atoms = list(value)
        self._center_resolved = True

    @property
    def center_derivation(self) -> str:
        self._ensure_center()
        return self._center_derivation or ""

    @center_derivation.setter
    def center_derivation(self, value: str) -> None:
        self._center_derivation = str(value)

    @property
    def center_error(self) -> str | None:
        self._ensure_center()
        return self._center_error

    @center_error.setter
    def center_error(self, value: str | None) -> None:
        self._center_error = value

    @property
    def lhs_unmapped_smiles(self) -> str:
        if self._lhs_unmapped_smiles is None:
            self._lhs_unmapped_smiles = _cached_unmapped(
                self.mapped_lhs, self.both_sides_sanitized)
        return self._lhs_unmapped_smiles

    @lhs_unmapped_smiles.setter
    def lhs_unmapped_smiles(self, value: str) -> None:
        self._lhs_unmapped_smiles = str(value)

    @property
    def rhs_unmapped_smiles(self) -> str:
        if self._rhs_unmapped_smiles is None:
            self._rhs_unmapped_smiles = _cached_unmapped(
                self.mapped_rhs, self.both_sides_sanitized)
        return self._rhs_unmapped_smiles

    @rhs_unmapped_smiles.setter
    def rhs_unmapped_smiles(self, value: str) -> None:
        self._rhs_unmapped_smiles = str(value)

    @property
    def lhs_mapped_smiles(self) -> str:
        return self.mapped_lhs

    @property
    def rhs_mapped_smiles(self) -> str:
        return self.mapped_rhs

    def to_dict(self) -> dict:
        self._ensure_center()
        return {
            "record_id": self.record_id,
            "template_id": self.template_id,
            "mapped_lhs": self.mapped_lhs,
            "mapped_rhs": self.mapped_rhs,
            "center_atoms": self.center_atoms,
            "center_derivation": self.center_derivation,
            "center_error": self.center_error,
            "radius_min": self.radius_min,
            "radius_max": self.radius_max,
            "radii": list(self.radii),
            "similarity": self.similarity,
            "containment": self.containment,
            "similarity_version": self.similarity_version,
            "similarity_rank": self.similarity_rank,
            "retrieval_mode": self.retrieval_mode,
            "substruct_matched": self.substruct_matched,
            "both_sides_sanitized": self.both_sides_sanitized,
            "n_atoms_lhs": self.n_atoms_lhs,
            "n_atoms_rhs": self.n_atoms_rhs,
            "ecs": list(self.ecs),
            "reactions": list(self.reactions),
            "rhea_reactions": list(self.rhea_reactions),
            "parent_reaction_ids": list(self.parent_reaction_ids),
            "score": list(self.score),
            "template": self.template,
            "lhs_smarts": self.lhs_smarts,
            "rhs_smarts": self.rhs_smarts,
            "lhs_unmapped_smiles": self.lhs_unmapped_smiles,
            "rhs_unmapped_smiles": self.rhs_unmapped_smiles,
            "dataset": self.dataset,
            "asset_sha256": self.asset_sha256,
            "manifest_sha256": self.manifest_sha256,
            "index": self.index,
            "mapping_quality": self.mapping_quality,
        }


def _normalize_dataset_name(dataset: str | None) -> str:
    ds = str(dataset or DEFAULT_LIBRARY).strip().lower()
    if ds == "metanetx":
        return "mnx"
    if ds == "rhea+mnx":
        return "mnx+rhea"
    return ds or DEFAULT_LIBRARY


def discover_retro_index_dir(assets_root, *,
                             dataset: str = DEFAULT_LIBRARY) -> Path | None:
    """Locate derived index directory under ``assets_root``."""
    if assets_root is None:
        return None
    root = Path(assets_root)
    ds = _normalize_dataset_name(dataset)
    prefixes = (
        ["mnx_retro_index", "rhea_retro_index"]
        if ds == "mnx+rhea"
        else [DATASET_INDEX_PREFIX.get(ds, f"{ds}_retro_index")]
    )
    for cand_dir in (
        root / RETRORULES_DIR_NAME / "derived",
        root / INDEX_DIR_NAME,
        root / RETRORULES_DIR_NAME,
        root,
    ):
        if not cand_dir.is_dir():
            continue
        if all((cand_dir / f"{p}.meta.json").is_file() for p in prefixes):
            return cand_dir
        if ds == "rhea" and (cand_dir / MANIFEST_JSON).is_file():
            return cand_dir
    return None


def discover_retro_source(assets_root, *,
                          dataset: str = DEFAULT_LIBRARY) -> Path | None:
    """Locate raw JSON file (``rhea.json`` or ``METANETX.json``) under ``assets_root``."""
    if assets_root is None:
        return None
    root = Path(assets_root)
    ds = _normalize_dataset_name(dataset)
    if ds == "mnx+rhea":
        ds = "mnx"
    raw_name = DATASET_RAW_FILES.get(ds, SOURCE_FILE_NAME)
    for candidate in (
        root / RETRORULES_DIR_NAME / "raw" / raw_name,
        root / RETRORULES_DIR_NAME / raw_name,
        root / INDEX_DIR_NAME / raw_name,
        root / raw_name,
    ):
        if candidate.is_file():
            return candidate
    return None


def _derive_center_atoms(mapped_lhs: str, mapped_rhs: str) -> tuple[
        list[int], str, str | None]:
    """Compiler-source center derivation (no independent chemistry)."""
    from ..pollutant.s5b_compiler import (
        extract_mapped_transform,
        l1_maps_of_transform,
    )

    try:
        transform = extract_mapped_transform(mapped_lhs, mapped_rhs)
    except Exception as exc:  # noqa: BLE001 - disclosed, not swallowed
        reason = str(getattr(exc, "reason", "") or type(exc).__name__)
        return [], "s5b_compiler.extract_mapped_transform", reason
    try:
        return ([int(x) for x in l1_maps_of_transform(transform)],
                "s5b_compiler.l1_maps_of_transform", None)
    except Exception as exc:  # noqa: BLE001
        reason = str(getattr(exc, "reason", "") or type(exc).__name__)
        return [], "s5b_compiler.l1_maps_of_transform", reason


def _strict_identity_key(smiles: str) -> str:
    """PPV1 strict structure identity key (falls back to canonical isomeric SMILES)."""
    text = str(smiles or "").strip()
    if not text:
        raise ValueError("empty smiles")
    try:
        from ..pollutant.chemstate import build_chemical_state

        st = build_chemical_state(
            text, "raw_input", [{"record": "retro-strict-key"}])
        return f"strict:{st.smiles_isomeric}"
    except Exception:
        mol = Chem.MolFromSmiles(text)
        if mol is None:
            raise
        for a in mol.GetAtoms():
            a.SetAtomMapNum(0)
        return f"strict:{Chem.MolToSmiles(mol, isomericSmiles=True)}"


class RetroTemplateResolver:
    """Verified, cached view over stage-1 RetroLibrary (supports rhea, mnx, mnx+rhea)."""

    _CACHE: dict = {}

    def __init__(self, config=None, *, index_dir=None, source=None,
                 dataset: str | None = None,
                 verify_artifacts: bool = True,
                 verify_source: bool = True,
                 library: RetroLibrary | None = None) -> None:
        self._center_cache: dict[tuple[str, str], tuple[list[int], str, str | None]] = {}
        if library is not None:
            self.library = library
            self.dataset = _normalize_dataset_name(
                dataset or library.identity.get("library") or DEFAULT_LIBRARY)
            self.index_dir = Path(library.index_dir)
            self.source_path = library.source_path
            self.identity = dict(library.identity)
            self.last_search_elapsed_s = None
            return

        ds = _normalize_dataset_name(
            dataset
            or (getattr(config, "retro_dataset", None) if config is not None else None)
            or DEFAULT_LIBRARY
        )
        self.dataset = ds
        assets_root = (
            getattr(config, "assets_root", None) if config is not None else None
        )
        if assets_root is None:
            try:
                from ..config import repo_root as _repo_root

                cand_assets = Path(_repo_root()) / "assets"
                if cand_assets.is_dir():
                    assets_root = cand_assets
            except Exception:  # noqa: BLE001
                assets_root = None

        idx = (
            Path(index_dir)
            if index_dir is not None
            else (
                Path(getattr(config, "retro_index_dir"))
                if config is not None and getattr(config, "retro_index_dir", None)
                else None
            )
        )
        if idx is None:
            idx = discover_retro_index_dir(assets_root, dataset=ds)
        if idx is None:
            raise RetroAssetError(
                "retro 索引目录未提供且默认 derived 目录不存在(显式关闭通道"
                "不得触发本构造)",
                {"assets_root": str(assets_root) if assets_root else None,
                 "dataset": ds})

        if ds == "mnx+rhea":
            lib = self._load_merged_library(
                idx, assets_root=assets_root,
                verify_artifacts=bool(verify_artifacts),
                verify_source=bool(verify_source),
            )
        else:
            src = (
                Path(source)
                if source is not None
                else (
                    Path(getattr(config, "retro_source"))
                    if config is not None and getattr(config, "retro_source", None)
                    else None
                )
            )
            if src is None:
                src = discover_retro_source(assets_root, dataset=ds)
            key = (
                str(Path(idx).resolve()),
                ds,
                str(src.resolve()) if src and src.is_file() else (str(src) if src else None),
                bool(verify_artifacts),
                bool(verify_source),
            )
            lib = RetroTemplateResolver._CACHE.get(key)
            if lib is None:
                lib = RetroLibrary(
                    idx,
                    source=src,
                    dataset=ds,
                    verify_artifacts=bool(verify_artifacts),
                    verify_source=bool(verify_source),
                )
                RetroTemplateResolver._CACHE[key] = lib

        self.library = lib
        self.index_dir = Path(lib.index_dir)
        self.source_path = lib.source_path
        self.identity = dict(lib.identity)
        self.last_search_elapsed_s = None

    @classmethod
    def _load_merged_library(
        cls,
        idx: Path,
        *,
        assets_root: Path | None,
        verify_artifacts: bool,
        verify_source: bool,
    ) -> RetroLibrary:
        resolved_idx = Path(idx).resolve()
        merge_key = (
            str(resolved_idx),
            "mnx+rhea",
            bool(verify_artifacts),
            bool(verify_source),
        )
        cached = cls._CACHE.get(merge_key)
        if cached is not None:
            return cached

        mnx_src = discover_retro_source(assets_root, dataset="mnx")
        rhea_src = discover_retro_source(assets_root, dataset="rhea")
        mnx_res = cls(
            index_dir=resolved_idx,
            source=mnx_src,
            dataset="mnx",
            verify_artifacts=verify_artifacts,
            verify_source=verify_source,
        )
        rhea_res = cls(
            index_dir=resolved_idx,
            source=rhea_src,
            dataset="rhea",
            verify_artifacts=verify_artifacts,
            verify_source=verify_source,
        )
        merged = RetroLibrary.from_merged(
            mnx_res.library, rhea_res.library, library_name="mnx+rhea")
        cls._CACHE[merge_key] = merged
        return merged

    # ------------------------------------------------------------ search

    def templates_similar_to(
        self,
        substrate_smiles: str,
        *,
        threshold: float = 0.45,
        top_k: int = 24,
        allowed_radii: set[int] | list[int] | tuple[int, ...] | None = None,
        radius_min: int | None = None,
        radius_max: int | None = None,
        mode: str = "tanimoto",
        dedupe_same_lhs: bool | None = None,
        max_per_lhs: int | None = None,
        require_sanitized: bool | None = None,
    ) -> list[RetroDonorRef]:
        """Retrieve RetroDonorRef candidates for ``substrate_smiles``."""
        t0 = time.time()
        hits = self.library.search(
            substrate_smiles,
            threshold=float(threshold),
            top_k=int(top_k),
            allowed_radii=allowed_radii,
            radius_min=radius_min,
            radius_max=radius_max,
            mode=mode,
            dedupe_same_lhs=dedupe_same_lhs,
            max_per_lhs=max_per_lhs,
            require_sanitized=require_sanitized,
        )
        self.last_search_elapsed_s = round(time.time() - t0, 4)
        return [self._to_ref(hit) for hit in hits]

    def _cached_center(self, lhs: str, rhs: str,
                       both_sanitized: bool) -> tuple[list[int], str, str | None]:
        if not both_sanitized:
            return [], "unsanitized_fragment_deferred_to_bridge", "unsanitized_fragment"
        key = (lhs, rhs)
        cached = self._center_cache.get(key)
        if cached is not None:
            return cached
        res = _derive_center_atoms(lhs, rhs)
        if len(self._center_cache) < 100_000:
            self._center_cache[key] = res
        return res

    def _to_ref(self, hit: dict) -> RetroDonorRef:
        lhs = str(hit.get("lhs_mapped_smiles") or "")
        rhs = str(hit.get("rhs_mapped_smiles") or "")
        both_san = bool(hit.get("both_sides_sanitized", True))
        tid = str(hit.get("template_id") or "")
        lib_name = str(hit.get("library") or self.dataset or DEFAULT_LIBRARY)
        rxns = list(hit.get("reactions") or [])
        rhea_rxns = list(hit.get("rhea_reactions") or [
            r for r in rxns if str(r).startswith("RHEA:")
        ])
        parent_rxns = list(hit.get("parent_reaction_ids") or rxns)
        for rr in rhea_rxns:
            if rr not in parent_rxns:
                parent_rxns.append(rr)
        return RetroDonorRef(
            record_id=tid,
            template_id=tid,
            mapped_lhs=lhs,
            mapped_rhs=rhs,
            radius_min=int(hit.get("radius_min") or 0),
            radius_max=int(hit.get("radius_max") or 0),
            radii=[int(x) for x in (hit.get("radii") or [])],
            similarity=float(hit.get("similarity") or 0.0),
            containment=float(hit.get("containment") or 0.0),
            similarity_version=str(hit.get("similarity_version") or RETRO_INDEX_VERSION),
            similarity_rank=int(hit.get("similarity_rank") or 0),
            retrieval_mode=str(hit.get("retrieval_mode") or "tanimoto"),
            substruct_matched=bool(hit.get("substruct_matched", False)),
            both_sides_sanitized=both_san,
            n_atoms_lhs=int(hit.get("n_atoms_lhs") or 0),
            n_atoms_rhs=int(hit.get("n_atoms_rhs") or 0),
            ecs=list(hit.get("ecs") or []),
            reactions=rxns,
            rhea_reactions=rhea_rxns,
            parent_reaction_ids=parent_rxns,
            score=[float(x) for x in (hit.get("score") or [])],
            template=str(hit.get("template") or f"{hit.get('lhs_smarts', '')}>>{hit.get('rhs_smarts', '')}"),
            lhs_smarts=str(hit.get("lhs_smarts") or ""),
            rhs_smarts=str(hit.get("rhs_smarts") or ""),
            dataset=lib_name,
            asset_sha256=str(hit.get("asset_sha256") or ""),
            manifest_sha256=str(hit.get("manifest_sha256") or ""),
            index=f"retro_{lib_name.replace('+', '_')}_templates",
        )

    @property
    def source_version(self) -> str:
        return RETRO_SOURCE_VERSION


def retro_asset_identity(*, index_dir=None, source=None, config=None,
                         dataset: str = DEFAULT_LIBRARY,
                         verify: bool = True) -> dict:
    """Fail-closed retro asset identity block."""
    resolver = RetroTemplateResolver(
        config, index_dir=index_dir, source=source, dataset=dataset,
        verify_artifacts=bool(verify), verify_source=bool(verify))
    return dict(resolver.identity)


# ---------------------------------------------------------------- bridge compile


def _extract_rule_fields(rule_or_ref: dict | RetroDonorRef) -> dict:
    if isinstance(rule_or_ref, RetroDonorRef):
        tpl = rule_or_ref.template or f"{rule_or_ref.lhs_smarts}>>{rule_or_ref.rhs_smarts}"
        return {
            "template_id": rule_or_ref.template_id or rule_or_ref.record_id,
            "template": tpl,
            "rule_sha256": rule_or_ref.asset_sha256,
        }
    tid = str(
        rule_or_ref.get("TEMPLATE_ID")
        or rule_or_ref.get("template_id")
        or rule_or_ref.get("record_id")
        or ""
    )
    tpl = str(rule_or_ref.get("TEMPLATE") or rule_or_ref.get("template") or "")
    if not tpl and rule_or_ref.get("lhs_smarts") and rule_or_ref.get("rhs_smarts"):
        tpl = f"{rule_or_ref['lhs_smarts']}>>{rule_or_ref['rhs_smarts']}"
    return {
        "template_id": tid,
        "template": tpl,
        "rule_sha256": str(
            rule_or_ref.get("V44_RULE_SHA256")
            or rule_or_ref.get("asset_sha256")
            or ""
        ),
    }


def bridge_occurrence_to_spec(
    *,
    rule: dict | RetroDonorRef | None = None,
    rule_or_ref: dict | RetroDonorRef | None = None,
    substrate_smiles: str,
    outcome_index: int = 0,
    record_id: str | None = None,
    allow_full_skeleton_fallback: bool = True,
    coefficient: int | None = None,
) -> dict:
    """Instantiate a RetroRules SMARTS template on ``substrate_smiles`` and compile via ``compile_donor_template``.

    Ported from ``v44_retrorules_archive_20261012/.../retrorules_source.py``
    and enhanced for small-radius (``r=2, 4, 6``) and aromatic-fragment rules:
      1. Matches the reactant SMARTS template onto ``substrate_smiles`` and
         executes ``rxn.RunReactants((substrate_mol,))`` to obtain concrete
         product molecules.
      2. Instantiates ``mapped_lhs`` on ``substrate_mol`` and ``mapped_rhs``
         on the sanitized product molecules, assigning fresh map numbers to
         newly introduced product template atoms.
      3. Derives ``center_atoms`` via ``s5b_compiler`` and invokes
         ``compile_donor_template``.  When ``allow_full_skeleton_fallback=True``
         and the instantiated full-substrate ``mapped_lhs`` hits
         ``ambiguous_alignment`` or ``no_alignment`` due to symmetric local
         centers, retries ``compile_donor_template`` with
         ``full_donor_skeleton=True``.
      4. Enforces strict multiset fidelity: the compiled ``target_smiles``
         strict-identity multiset MUST equal the ``RunReactants`` outcome
         strict-identity multiset, else returns ``bridge_target_mismatch``.
    """
    from ..pollutant.s5b_compiler import compile_donor_template

    target_rule = rule if rule is not None else rule_or_ref
    if target_rule is None:
        return {
            "status": "unsupported",
            "reason": "bridge_missing_rule",
            "detail": {},
            "mapping": {},
            "fidelity": {},
        }
    info = _extract_rule_fields(target_rule)
    tid = info["template_id"]
    template = info["template"]
    detail: dict = {"template_id": tid, "rule_sha256": info["rule_sha256"]}

    if not template or ">>" not in template:
        return {
            "status": "unsupported",
            "reason": "bridge_invalid_template",
            "detail": detail,
            "mapping": {},
            "fidelity": {},
        }

    rxn = rdChemReactions.ReactionFromSmarts(template)
    if rxn is None or rxn.GetNumReactantTemplates() != 1:
        return {
            "status": "unsupported",
            "reason": "bridge_requires_single_reactant_template",
            "detail": detail,
            "mapping": {},
            "fidelity": {},
        }
    substrate_mol = Chem.MolFromSmiles(str(substrate_smiles or ""))
    if substrate_mol is None:
        return {
            "status": "unsupported",
            "reason": "bridge_substrate_unparseable",
            "detail": detail,
            "mapping": {},
            "fidelity": {},
        }

    pattern = rxn.GetReactants()[0]
    try:
        matches = substrate_mol.GetSubstructMatches(pattern, uniquify=False)
        if not matches:
            matches = substrate_mol.GetSubstructMatches(pattern)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "unsupported",
            "reason": f"bridge_reactant_match_error:{type(exc).__name__}",
            "detail": detail,
            "mapping": {},
            "fidelity": {},
        }
    if not matches:
        return {
            "status": "unsupported",
            "reason": "bridge_no_reactant_match",
            "detail": detail,
            "mapping": {},
            "fidelity": {},
        }

    try:
        outcomes = rxn.RunReactants((substrate_mol,))
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "unsupported",
            "reason": f"bridge_run_error:{type(exc).__name__}",
            "detail": detail,
            "mapping": {},
            "fidelity": {},
        }
    if outcome_index >= len(outcomes):
        return {
            "status": "unsupported",
            "reason": "bridge_outcome_index_out_of_range",
            "detail": dict(detail, n_outcomes=len(outcomes)),
            "mapping": {},
            "fidelity": {},
        }

    outcome = outcomes[outcome_index]
    product_templates = [
        rxn.GetProducts()[i] for i in range(rxn.GetNumProductTemplates())
    ]
    if len(product_templates) != len(outcome):
        return {
            "status": "unsupported",
            "reason": "bridge_product_template_count_mismatch",
            "detail": detail,
            "mapping": {},
            "fidelity": {},
        }

    # Instantiate RHS from outcome product molecules
    all_template_maps: set[int] = set()
    for mol in [pattern] + product_templates:
        for a in mol.GetAtoms():
            if a.GetAtomMapNum():
                all_template_maps.add(int(a.GetAtomMapNum()))
    next_fresh = (max(all_template_maps) if all_template_maps else 0) + 1
    rhs_parts: list[str] = []
    rr_products: list[dict] = []
    for member_mol, pat_prod in zip(outcome, product_templates):
        try:
            sanitized = Chem.Mol(member_mol)
            Chem.SanitizeMol(sanitized)
        except Exception:  # noqa: BLE001
            return {
                "status": "unsupported",
                "reason": "bridge_product_unsanitizable",
                "detail": detail,
                "mapping": {},
                "fidelity": {},
            }
        pm = sanitized.GetSubstructMatches(pat_prod)
        if not pm:
            return {
                "status": "unsupported",
                "reason": "bridge_product_template_no_match",
                "detail": detail,
                "mapping": {},
                "fidelity": {},
            }
        prod_match = pm[0]
        assigned = Chem.Mol(sanitized)
        for q_idx, p_idx in enumerate(prod_match):
            mnum = pat_prod.GetAtomWithIdx(q_idx).GetAtomMapNum()
            if mnum:
                assigned.GetAtomWithIdx(p_idx).SetAtomMapNum(int(mnum))
            else:
                assigned.GetAtomWithIdx(p_idx).SetAtomMapNum(next_fresh)
                next_fresh += 1
        rhs_parts.append(Chem.MolToSmiles(assigned))
        stripped = Chem.Mol(assigned)
        for a in stripped.GetAtoms():
            a.SetAtomMapNum(0)
        canon = Chem.MolToSmiles(stripped)
        try:
            rr_products.append({
                "smiles": canon,
                "strict_identity": _strict_identity_key(canon),
            })
        except Exception:  # noqa: BLE001
            return {
                "status": "unsupported",
                "reason": "bridge_product_strict_identity_failed",
                "detail": detail,
                "mapping": {},
                "fidelity": {},
            }
    mapped_rhs = ".".join(rhs_parts)
    rr_multiset = sorted(p["strict_identity"] for p in rr_products)

    # Order candidate reactant matches starting with the one corresponding to outcome_index
    primary_match_idx = min(outcome_index, len(matches) - 1)
    ordered_matches = [matches[primary_match_idx]] + [
        m for idx_m, m in enumerate(matches) if idx_m != primary_match_idx
    ]

    last_failure: dict | None = None
    for match in ordered_matches[:4]:
        lhs_mol = Chem.Mol(substrate_mol)
        for q_idx, s_idx in enumerate(match):
            mnum = pattern.GetAtomWithIdx(q_idx).GetAtomMapNum()
            if mnum:
                lhs_mol.GetAtomWithIdx(s_idx).SetAtomMapNum(int(mnum))
        mapped_lhs = Chem.MolToSmiles(lhs_mol)
        center, _deriv, _err = _derive_center_atoms(mapped_lhs, mapped_rhs)

        mapping = {
            "mapping_origin": "rr_runreactants_instance",
            "mapped_lhs": mapped_lhs,
            "mapped_rhs": mapped_rhs,
            "center_maps": center,
            "reactant_match": list(match),
            "outcome_index": outcome_index,
            "note": (
                "inferred instance mapping derived from template SMARTS matched "
                "against the concrete substrate/product molecules; NOT the "
                "template's native atom mapping and NOT an experimental "
                "reaction mapping"
            ),
        }

        skeleton_modes = [False]
        if allow_full_skeleton_fallback:
            skeleton_modes.append(True)

        out = None
        used_full_skeleton = False
        for full_skel in skeleton_modes:
            out = compile_donor_template(
                mapped_lhs=mapped_lhs,
                mapped_rhs=mapped_rhs,
                center_atoms=center,
                substrate_smiles=str(substrate_smiles),
                record_id=(record_id or f"rr:{tid}"),
                mapping_origin="rr_runreactants_instance",
                alignment_ref=f"rr-instance:{tid}",
                key_prefix="rrtpl",
                full_donor_skeleton=full_skel,
            )
            if out.get("status") == "compiled":
                used_full_skeleton = full_skel
                break
            if str(out.get("reason")) not in ("ambiguous_alignment", "no_alignment"):
                break

        if out is None or out.get("status") != "compiled":
            last_failure = {
                "status": "unsupported",
                "reason": str((out or {}).get("reason") or "compile_unsupported"),
                "detail": dict(detail, compile_detail=(out or {}).get("detail")),
                "mapping": mapping,
                "fidelity": {},
            }
            continue

        spec = dict(out["spec"])
        spec["coefficient"] = coefficient
        spec.setdefault("compile", {})["rr_stoichiometry_status"] = (
            "unknown: RR carries no stoichiometry; the compiler default "
            "coefficient=1 is NOT RR stoichiometry evidence and is explicitly "
            "handled here"
        )
        spec["compile"]["bridge_full_donor_skeleton"] = bool(used_full_skeleton)

        try:
            target = str(spec["expectation"]["target_smiles"])
            compiled_components = [
                _strict_identity_key(c) for c in target.split(".") if c
            ]
            fidelity_ok = sorted(compiled_components) == rr_multiset
        except Exception:  # noqa: BLE001
            fidelity_ok = False

        fidelity = {
            "compiled_target": spec["expectation"]["target_smiles"],
            "rr_rule_products": [p["smiles"] for p in rr_products],
            "multiset_match": fidelity_ok,
            "check": (
                "compiled executed product components multiset (strict "
                "keys) must equal the RR outcome rule_products multiset"
            ),
        }
        if not fidelity_ok:
            last_failure = {
                "status": "unsupported",
                "reason": "bridge_target_mismatch",
                "detail": detail,
                "mapping": mapping,
                "fidelity": fidelity,
            }
            continue

        return {
            "status": "compiled",
            "reason": "",
            "detail": detail,
            "spec": spec,
            "mapping": mapping,
            "fidelity": fidelity,
        }

    return last_failure or {
        "status": "unsupported",
        "reason": "bridge_compile_failed",
        "detail": detail,
        "mapping": {},
        "fidelity": {},
    }


# ---------------------------------------------------------------- candidate compilation & pool integration


def _attach_retro_metadata(spec: dict, ref: RetroDonorRef, *,
                           compile_route: str) -> dict:
    """Attach channel and RetroRules provenance metadata to a compiled spec."""
    spec = dict(spec)
    spec["channel"] = "retro"
    spec["origin_group_key"] = f"retro-template:{ref.record_id}"
    spec["parent_reaction_ids"] = list(ref.parent_reaction_ids)
    lhs_strict_keys = sorted(
        _component_strict_keys(ref.lhs_unmapped_smiles or ref.mapped_lhs)
    )
    rhs_strict_keys = sorted(
        _component_strict_keys(ref.rhs_unmapped_smiles or ref.mapped_rhs)
    )
    comp = dict(spec.get("compile") or {})
    comp["parent_reaction_ids"] = list(ref.parent_reaction_ids)
    comp["donor_lhs_strict_keys"] = lhs_strict_keys
    comp["donor_rhs_strict_keys"] = rhs_strict_keys
    spec["compile"] = comp
    spec["retro_meta"] = {
        "template_id": ref.template_id,
        "record_id": ref.record_id,
        "dataset": ref.dataset,
        "radii": list(ref.radii),
        "radius_min": int(ref.radius_min),
        "radius_max": int(ref.radius_max),
        "similarity": float(ref.similarity),
        "containment": float(ref.containment),
        "similarity_rank": int(ref.similarity_rank),
        "retrieval_mode": ref.retrieval_mode,
        "substruct_matched": bool(ref.substruct_matched),
        "both_sides_sanitized": bool(ref.both_sides_sanitized),
        "n_atoms_lhs": int(ref.n_atoms_lhs),
        "n_atoms_rhs": int(ref.n_atoms_rhs),
        "compile_route": compile_route,
        "ecs": list(ref.ecs),
        "reactions": list(ref.reactions),
        "rhea_reactions": list(ref.rhea_reactions),
        "parent_reaction_ids": list(ref.parent_reaction_ids),
        "donor_lhs_strict_keys": lhs_strict_keys,
        "donor_rhs_strict_keys": rhs_strict_keys,
        "score": list(ref.score),
        "lhs_mapped_smiles": ref.mapped_lhs,
        "rhs_mapped_smiles": ref.mapped_rhs,
        "lhs_unmapped_smiles": ref.lhs_unmapped_smiles,
        "rhs_unmapped_smiles": ref.rhs_unmapped_smiles,
        "asset_sha256": ref.asset_sha256,
        "manifest_sha256": ref.manifest_sha256,
    }
    return spec


def compile_retro_ref(
    ref: RetroDonorRef,
    substrate_smiles: str,
    *,
    compile_mode: str = "hybrid",
    full_donor_skeleton: bool = False,
    max_bridge_outcomes: int = 2,
) -> dict:
    """Compile a single ``RetroDonorRef`` against ``substrate_smiles``.

    ``compile_mode``:
      * ``"direct"``: n004 stage-2 direct compile (``center_anchor_probe`` +
        ``compile_donor_template`` on ``ref.mapped_lhs`` / ``ref.mapped_rhs``).
      * ``"bridge"``: ``bridge_occurrence_to_spec`` instantiation on
        ``substrate_smiles``.
      * ``"hybrid"`` (default): tries ``"direct"`` first when
        ``ref.both_sides_sanitized`` is True, and falls back to ``"bridge"``
        when direct compile fails (e.g. ``no_alignment``,
        ``ambiguous_alignment``, or unsanitized aromatic fragment at small
        radius ``r=2, 4, 6``).

    Returns ``{"status": "compiled" | "rejected", "specs": [...], "spec": dict | None,
    "reason": str | None, "compile_route": str, "f1_elements_fit": bool, "f5": str}``.
    """
    from ..pollutant.s5b_compiler import (
        center_anchor_probe,
        compile_donor_template,
        template_elements_fit,
    )

    mode = str(compile_mode or "hybrid").strip().lower()
    lhs = str(ref.mapped_lhs or "")
    rhs = str(ref.mapped_rhs or "")
    f1 = bool(template_elements_fit(lhs, substrate_smiles)) if ref.both_sides_sanitized else False
    f5_status = "defer"
    direct_reason: str | None = None

    if mode in ("direct", "hybrid"):
        if not ref.both_sides_sanitized:
            direct_reason = "unsanitized_fragment"
        else:
            f5 = center_anchor_probe(lhs, rhs, substrate_smiles)
            f5_status = "pass" if f5["status"] == "present" else (
                "reject" if f5["status"] == "absent" else "defer"
            )
            if f5["status"] == "absent":
                direct_reason = "no_alignment"
            else:
                out = compile_donor_template(
                    mapped_lhs=lhs,
                    mapped_rhs=rhs,
                    center_atoms=[int(x) for x in (ref.center_atoms or [])],
                    substrate_smiles=substrate_smiles,
                    record_id=str(ref.record_id or "rtpl"),
                    mapping_origin="native",
                    alignment_ref=f"retro-template:{ref.record_id}",
                    key_prefix="rtpl",
                    full_donor_skeleton=bool(full_donor_skeleton),
                )
                if out.get("status") == "compiled":
                    spec = _attach_retro_metadata(
                        out["spec"], ref, compile_route="direct")
                    spec["coefficient"] = 1
                    return {
                        "status": "compiled",
                        "spec": spec,
                        "specs": [spec],
                        "reason": None,
                        "compile_route": "direct",
                        "f1_elements_fit": f1,
                        "f5": f5_status,
                    }
                direct_reason = str(out.get("reason") or "compile_rejected")

        if mode == "direct":
            return {
                "status": "rejected",
                "spec": None,
                "specs": [],
                "reason": direct_reason,
                "compile_route": "direct",
                "f1_elements_fit": f1,
                "f5": f5_status,
            }

    # Bridge compilation (either mode == "bridge" or fallback in "hybrid")
    compiled_specs: list[dict] = []
    bridge_reason: str | None = None
    for out_idx in range(max(1, int(max_bridge_outcomes))):
        b_res = bridge_occurrence_to_spec(
            rule_or_ref=ref,
            substrate_smiles=substrate_smiles,
            outcome_index=out_idx,
            record_id=str(ref.record_id or "rtpl"),
            allow_full_skeleton_fallback=True,
            coefficient=1,
        )
        if b_res.get("status") == "compiled":
            spec = _attach_retro_metadata(
                b_res["spec"], ref, compile_route="bridge")
            compiled_specs.append(spec)
        else:
            r = str(b_res.get("reason") or "bridge_compile_failed")
            if bridge_reason is None:
                bridge_reason = r
            if r in (
                "bridge_outcome_index_out_of_range",
                "bridge_no_reactant_match",
                "bridge_requires_single_reactant_template",
                "bridge_substrate_unparseable",
            ):
                break

    if compiled_specs:
        return {
            "status": "compiled",
            "spec": compiled_specs[0],
            "specs": compiled_specs,
            "reason": None,
            "compile_route": "bridge",
            "f1_elements_fit": f1,
            "f5": f5_status,
        }

    return {
        "status": "rejected",
        "spec": None,
        "specs": [],
        "reason": direct_reason or bridge_reason or "compile_rejected",
        "compile_route": "bridge" if mode == "bridge" else "hybrid_failed",
        "f1_elements_fit": f1,
        "f5": f5_status,
    }


def compile_retro_candidates_for_substrate(
    substrate_smiles: str,
    *,
    config=None,
    dataset: str = DEFAULT_LIBRARY,
    allowed_radii: set[int] | list[int] | tuple[int, ...] | None = None,
    radius_min: int | None = None,
    radius_max: int | None = None,
    threshold: float = 0.45,
    top_k: int = 24,
    retrieval_mode: str = "hybrid",
    compile_mode: str = "hybrid",
    dedupe_same_lhs: bool | None = None,
    max_per_lhs: int | None = 8,
    full_donor_skeleton: bool = False,
    resolver: RetroTemplateResolver | None = None,
    index_dir=None,
    source=None,
    existing_specs: list[dict] | None = None,
) -> tuple[list[dict], dict]:
    """Retrieve, compile, and deduplicate RetroRules candidates for one substrate.

    Designed as a drop-in 3-line hook for ``s5b_builder.py`` and
    ``pool_coverage_eval.py``:

    .. code-block:: python

        retro_kept, retro_stats = compile_retro_candidates_for_substrate(
            substrate, config=config, dataset="rhea", allowed_radii={6},
            existing_specs=ordered + analog_specs)
    """
    from ..pollutant.s5b_compiler import net_reaction_signature

    retro_obj = resolver
    if retro_obj is None:
        retro_obj = RetroTemplateResolver(
            config, index_dir=index_dir, source=source, dataset=dataset)

    t_retro = time.time()
    retro_refs = retro_obj.templates_similar_to(
        substrate_smiles,
        threshold=float(threshold),
        top_k=int(top_k),
        allowed_radii=allowed_radii,
        radius_min=radius_min,
        radius_max=radius_max,
        mode=retrieval_mode,
        dedupe_same_lhs=dedupe_same_lhs,
        max_per_lhs=max_per_lhs,
    )
    retro_search_s = round(time.time() - t_retro, 4)

    retro_hist: dict[str, int] = {}
    retro_candidates: list[dict] = []
    retro_specs: list[dict] = []
    retro_entry_by_spec: dict[int, dict] = {}
    n_f1_reject = 0
    n_checked = n_skipped = n_deferred = n_attempted = 0
    n_center_error = 0
    n_compiled_direct = 0
    n_compiled_bridge = 0

    for ref in retro_refs:
        rank = int(ref.similarity_rank or (len(retro_candidates) + 1))
        if ref.center_error:
            n_center_error += 1
        n_checked += 1
        res = compile_retro_ref(
            ref,
            substrate_smiles,
            compile_mode=compile_mode,
            full_donor_skeleton=full_donor_skeleton,
        )
        f1 = bool(res["f1_elements_fit"])
        if not f1:
            n_f1_reject += 1
        f5_val = str(res["f5"])
        if f5_val == "defer":
            n_deferred += 1
        elif f5_val == "reject" and res["status"] != "compiled":
            n_skipped += 1

        if res["status"] != "compiled":
            reason = str(res["reason"] or "compile_rejected")
            retro_hist[reason] = retro_hist.get(reason, 0) + 1
            retro_candidates.append({
                "retrieval_rank": rank,
                "template_id": str(ref.record_id),
                "dataset": ref.dataset,
                "similarity": float(ref.similarity),
                "containment": float(ref.containment),
                "retrieval_mode": ref.retrieval_mode,
                "substruct_matched": bool(ref.substruct_matched),
                "radii": list(ref.radii),
                "radius_min": int(ref.radius_min),
                "radius_max": int(ref.radius_max),
                "parent_reaction_ids": list(ref.parent_reaction_ids),
                "f1_elements_fit": f1,
                "f5": f5_val,
                "outcome": "compile_rejected",
                "compile_route": res["compile_route"],
                "reason": reason,
            })
            continue

        n_attempted += 1
        if res["compile_route"] == "direct":
            n_compiled_direct += 1
        else:
            n_compiled_bridge += 1

        for spec in res["specs"]:
            retro_specs.append(spec)
            comp_info = spec.get("compile") or {}
            entry = {
                "retrieval_rank": rank,
                "template_id": str(ref.record_id),
                "dataset": ref.dataset,
                "similarity": float(ref.similarity),
                "containment": float(ref.containment),
                "retrieval_mode": ref.retrieval_mode,
                "substruct_matched": bool(ref.substruct_matched),
                "radii": list(ref.radii),
                "radius_min": int(ref.radius_min),
                "radius_max": int(ref.radius_max),
                "parent_reaction_ids": list(ref.parent_reaction_ids),
                "donor_lhs_strict_keys": list(comp_info.get("donor_lhs_strict_keys") or []),
                "donor_rhs_strict_keys": list(comp_info.get("donor_rhs_strict_keys") or []),
                "f1_elements_fit": f1,
                "f5": f5_val,
                "outcome": "compiled",
                "compile_route": res["compile_route"],
                "reason": None,
                "spec_key": str(spec["key"]),
            }
            retro_candidates.append(entry)
            retro_entry_by_spec[id(spec)] = entry

    existing_sig: dict[tuple, str] = {}
    for spec in (existing_specs or []):
        existing_sig.setdefault(
            net_reaction_signature(spec), str(spec.get("key")))

    retro_sig: dict[tuple, dict] = {}
    retro_kept: list[dict] = []
    n_dup_existing = n_dup_retro = 0
    for spec in retro_specs:
        sig = net_reaction_signature(spec)
        entry = retro_entry_by_spec.get(id(spec))
        if sig in existing_sig:
            n_dup_existing += 1
            if entry is not None:
                entry["outcome"] = "duplicate_of_existing"
                entry["merged_into"] = existing_sig[sig]
            continue
        if sig in retro_sig:
            n_dup_retro += 1
            first = retro_sig[sig]
            f_comp = first.setdefault("compile", {})
            f_comp.setdefault("merged_source_keys", []).append(str(spec["key"]))
            s_comp = spec.get("compile") or {}
            f_comp.setdefault("merged_retro_sources", {})[str(spec["key"])] = {
                "template_id": str((spec.get("retro_meta") or {}).get("template_id") or ""),
                "parent_reaction_ids": list(
                    s_comp.get("parent_reaction_ids")
                    or spec.get("parent_reaction_ids")
                    or []
                ),
                "donor_lhs_strict_keys": list(s_comp.get("donor_lhs_strict_keys") or []),
                "donor_rhs_strict_keys": list(s_comp.get("donor_rhs_strict_keys") or []),
            }
            if entry is not None:
                entry["outcome"] = "merged_into"
                entry["merged_into"] = str(first["key"])
            continue
        retro_sig[sig] = spec
        retro_kept.append(spec)

    top20_retrieved = sum(
        1 for c in retro_candidates if int(c["retrieval_rank"]) <= 20
    )
    top20_compiled = sum(
        1 for c in retro_candidates
        if int(c["retrieval_rank"]) <= 20
        and c["outcome"] in ("compiled", "duplicate_of_existing", "merged_into")
    )
    retro_stats = {
        "retro_channel": True,
        "retro_channel_version": RETRO_CHANNEL_VERSION,
        "retro_pool_policy_version": RETRO_POOL_POLICY_VERSION,
        "retro_source_version": RETRO_SOURCE_VERSION,
        "retro_compile_adapter_version": RETRO_COMPILE_ADAPTER_VERSION,
        "retro_dataset": retro_obj.dataset,
        "retro_asset_identity": dict(retro_obj.identity),
        "retro_search_threshold": float(threshold),
        "retro_raw_top": int(top_k),
        "retro_allowed_radii": (
            sorted(int(r) for r in allowed_radii)
            if allowed_radii is not None else None
        ),
        "retro_radius_min": radius_min,
        "retro_radius_max": radius_max,
        "retro_retrieval_mode": retrieval_mode,
        "retro_compile_mode": compile_mode,
        "retro_search_elapsed_s": retro_search_s,
        "retro_n_retrieved": len(retro_refs),
        "retro_n_checked": n_checked,
        "retro_n_f1_reject": n_f1_reject,
        "retro_n_center_derivation_error": n_center_error,
        "retro_n_f5_absent": n_skipped,
        "retro_n_f5_defer": n_deferred,
        "retro_n_compile_attempted": n_attempted,
        "retro_n_compiled": len(retro_specs),
        "retro_n_compiled_direct": n_compiled_direct,
        "retro_n_compiled_bridge": n_compiled_bridge,
        "retro_compile_failure_histogram": dict(sorted(retro_hist.items())),
        "retro_n_duplicate_of_existing": n_dup_existing,
        "retro_n_duplicate_within_retro": n_dup_retro,
        "retro_n_unique_new_net_reactions": len(retro_kept),
        "retro_top20_retrieved": top20_retrieved,
        "retro_top20_compiled": top20_compiled,
        "retro_candidates": retro_candidates,
    }
    return retro_kept, retro_stats


def merge_retro_specs_into_pool(
    existing_specs: list[dict],
    retro_specs: list[dict],
    *,
    max_pool: int = 8,
    ranking_mode: str = "append",
) -> list[dict]:
    """Merge ``existing_specs`` and ``retro_specs`` under ``ranking_mode`` (``S4-位次``).

    ``ranking_mode``:
      * ``"append"`` (default): existing specs (recorded + analog) retain their
        exact positions first, and deduplicated ``retro_specs`` fill remaining
        slots up to ``max_pool``.
      * ``"unified_score"``: recorded exact/corpus specs stay in tier 0, while
        analog and retro template specs are ranked together by
        ``(-similarity, -is_substruct, -n_atoms_lhs, channel_order, orig_idx)``
        before deduplicating by ``net_reaction_signature`` and truncating to
        ``max_pool``.
    """
    from ..pollutant.s5b_compiler import net_reaction_signature

    mode = str(ranking_mode or "append").strip().lower()
    if mode == "append":
        sequence = list(existing_specs) + list(retro_specs)
    elif mode == "unified_score":
        recorded_tier: list[dict] = []
        template_tier: list[tuple[tuple, dict]] = []
        for idx, spec in enumerate(existing_specs):
            ch = str(spec.get("channel") or "")
            origin = str(spec.get("origin_group_key") or spec.get("key") or "")
            skey = str(spec.get("key") or "")
            is_analog = (
                ch == "analog"
                or origin.startswith("analog")
                or skey.startswith("atpl")
                or skey.startswith("tpl-")
            )
            if not is_analog:
                recorded_tier.append(spec)
            else:
                sim = float(
                    spec.get("similarity")
                    or (spec.get("compile") or {}).get("similarity")
                    or 0.0
                )
                sort_key = (-round(sim, 6), 0, 0, 0, idx)
                template_tier.append((sort_key, spec))
        for idx, spec in enumerate(retro_specs):
            rmeta = spec.get("retro_meta") or {}
            sim = float(rmeta.get("similarity") or spec.get("similarity") or 0.0)
            cont = float(rmeta.get("containment") or 0.0)
            is_sub = 1 if rmeta.get("substruct_matched") else 0
            eff_sim = max(sim, round(0.5 * sim + 0.5 * cont, 6)) if is_sub else sim
            n_atoms = int(rmeta.get("n_atoms_lhs") or 0)
            sort_key = (-round(eff_sim, 6), -is_sub, -n_atoms, 1, idx)
            template_tier.append((sort_key, spec))
        template_tier.sort(key=lambda pair: pair[0])
        sequence = recorded_tier + [s for _k, s in template_tier]
    else:
        raise ValueError(f"Unknown ranking_mode: {ranking_mode!r}")

    merged: list[dict] = []
    signature_of: dict[tuple, dict] = {}
    for spec in sequence:
        sig = net_reaction_signature(spec)
        if sig in signature_of:
            first = signature_of[sig]
            f_comp = first.setdefault("compile", {})
            f_merged = f_comp.setdefault("merged_source_keys", [])
            skey = str(spec.get("key"))
            if skey not in f_merged:
                f_merged.append(skey)
            s_comp = spec.get("compile") or {}
            for sub_k in (s_comp.get("merged_source_keys") or []):
                if str(sub_k) not in f_merged:
                    f_merged.append(str(sub_k))
            if (
                spec.get("channel") in ("retro", "retrorules")
                or "retro_meta" in spec
                or "parent_reaction_ids" in s_comp
            ):
                f_retro_map = f_comp.setdefault("merged_retro_sources", {})
                f_retro_map[skey] = {
                    "template_id": str((spec.get("retro_meta") or {}).get("template_id") or ""),
                    "parent_reaction_ids": list(
                        s_comp.get("parent_reaction_ids")
                        or spec.get("parent_reaction_ids")
                        or []
                    ),
                    "donor_lhs_strict_keys": list(s_comp.get("donor_lhs_strict_keys") or []),
                    "donor_rhs_strict_keys": list(s_comp.get("donor_rhs_strict_keys") or []),
                }
            if s_comp.get("merged_retro_sources"):
                f_comp.setdefault("merged_retro_sources", {}).update(
                    s_comp["merged_retro_sources"]
                )
            continue
        signature_of[sig] = spec
        merged.append(spec)
        if len(merged) >= int(max_pool):
            break
    return merged[:int(max_pool)]


# ---------------------------------------------------------------- self-record detection


_RHEA_DIGITS_RE = re.compile(r"(?:^|[^0-9])(\d{4,6})$")


def _normalize_reaction_id_tokens(raw_ids: list[str] | set[str] | tuple[str, ...] | None) -> set[str]:
    """Normalize reaction IDs (e.g. ``RHEA:18901``, ``18901``, ``MNXR107022``)."""
    tokens: set[str] = set()
    for raw in (raw_ids or []):
        s = str(raw or "").strip()
        if not s:
            continue
        up = s.upper()
        tokens.add(up)
        if up.startswith("RHEA:"):
            num = up.split(":", 1)[1].strip()
            if num.isdigit():
                tokens.add(f"RHEA:{num}")
                tokens.add(num)
        elif up.isdigit():
            tokens.add(f"RHEA:{up}")
            tokens.add(up)
        else:
            m = _RHEA_DIGITS_RE.search(up)
            if m and "RHEA" in up:
                num = m.group(1)
                tokens.add(f"RHEA:{num}")
                tokens.add(num)
    return tokens


def _component_strict_keys(smiles: str) -> set[str]:
    out: set[str] = set()
    text = str(smiles or "").strip()
    if not text:
        return out
    for comp in split_components(text):
        unmapped = _strip_atom_maps(comp) or comp
        try:
            out.add(_strict_identity_key(unmapped))
        except Exception:  # noqa: BLE001
            continue
    return out


def check_retro_self_record(
    spec_or_ref: dict | RetroDonorRef,
    *,
    question_source_ids: list[str] | set[str] | tuple[str, ...] | None = None,
    substrate_smiles: str | None = None,
    gold_principal_smiles: list[str] | set[str] | tuple[str, ...] | None = None,
) -> dict:
    """Check whether a RetroRules candidate is a self-record of the question (§4 Phase 2b).

    Checks two criteria:
      1. ``by_reaction_id``: overlap between the rule's ``parent_reaction_ids``
         (native ``REACTIONS`` such as ``RHEA:xxxx`` / ``MNXR...`` plus
         cross-mapped ``rhea_reactions`` from shared ``TEMPLATE`` strings) and
         ``question_source_ids``.
      2. ``by_strict_pair``: whether the rule's unmapped ``lhs_mapped_smiles``
         contains a component with the exact same strict structure identity as
         ``substrate_smiles`` AND the rule's unmapped ``rhs_mapped_smiles``
         contains a component with the exact same strict structure identity as
         any ``gold_principal_smiles``.
    """
    if isinstance(spec_or_ref, RetroDonorRef):
        parent_ids = list(spec_or_ref.parent_reaction_ids or spec_or_ref.reactions)
        lhs_smi = spec_or_ref.lhs_unmapped_smiles or spec_or_ref.mapped_lhs
        rhs_smi = spec_or_ref.rhs_unmapped_smiles or spec_or_ref.mapped_rhs
        pre_lhs_keys: set[str] = set()
        pre_rhs_keys: set[str] = set()
    else:
        rmeta = spec_or_ref.get("retro_meta") or {}
        comp = spec_or_ref.get("compile") or {}
        parent_ids = list(
            spec_or_ref.get("parent_reaction_ids")
            or comp.get("parent_reaction_ids")
            or rmeta.get("parent_reaction_ids")
            or rmeta.get("reactions")
            or spec_or_ref.get("reactions")
            or []
        )
        lhs_smi = str(
            rmeta.get("lhs_unmapped_smiles")
            or rmeta.get("lhs_mapped_smiles")
            or spec_or_ref.get("lhs_unmapped_smiles")
            or spec_or_ref.get("lhs_mapped_smiles")
            or ""
        )
        rhs_smi = str(
            rmeta.get("rhs_unmapped_smiles")
            or rmeta.get("rhs_mapped_smiles")
            or spec_or_ref.get("rhs_unmapped_smiles")
            or spec_or_ref.get("rhs_mapped_smiles")
            or ""
        )
        pre_lhs_keys = set(
            comp.get("donor_lhs_strict_keys")
            or rmeta.get("donor_lhs_strict_keys")
            or spec_or_ref.get("donor_lhs_strict_keys")
            or []
        )
        pre_rhs_keys = set(
            comp.get("donor_rhs_strict_keys")
            or rmeta.get("donor_rhs_strict_keys")
            or spec_or_ref.get("donor_rhs_strict_keys")
            or []
        )

    q_tokens = _normalize_reaction_id_tokens(question_source_ids)
    r_tokens = _normalize_reaction_id_tokens(parent_ids)
    matched_rxn_ids = sorted(
        t for t in (q_tokens & r_tokens) if not t.isdigit()
    )
    if not matched_rxn_ids and (q_tokens & r_tokens):
        matched_rxn_ids = sorted(q_tokens & r_tokens)
    by_reaction_id = bool(matched_rxn_ids)

    by_strict_pair = False
    matched_lhs: list[str] = []
    matched_rhs: list[str] = []
    if substrate_smiles and gold_principal_smiles:
        lhs_keys = pre_lhs_keys or (_component_strict_keys(lhs_smi) if lhs_smi else set())
        rhs_keys = pre_rhs_keys or (_component_strict_keys(rhs_smi) if rhs_smi else set())
        if lhs_keys and rhs_keys:
            sub_keys = _component_strict_keys(substrate_smiles)
            gold_keys: set[str] = set()
            for gp in gold_principal_smiles:
                gold_keys |= _component_strict_keys(gp)
            matched_lhs = sorted(sub_keys & lhs_keys)
            matched_rhs = sorted(gold_keys & rhs_keys)
            by_strict_pair = bool(matched_lhs and matched_rhs and (gold_keys <= rhs_keys))

    return {
        "is_self_record": bool(by_reaction_id or by_strict_pair),
        "by_reaction_id": by_reaction_id,
        "matched_reaction_ids": matched_rxn_ids,
        "by_strict_pair": by_strict_pair,
        "matched_lhs_strict": matched_lhs,
        "matched_rhs_strict": matched_rhs,
    }
