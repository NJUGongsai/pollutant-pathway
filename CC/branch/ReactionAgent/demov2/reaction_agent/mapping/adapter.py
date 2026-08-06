"""Atom-mapping adapter implementations (chatgpt_p1_train.md §10).

Contains:
- FakeAtomMapper: deterministic mapper for unit tests (formal only, §10.4).
- compute_quality_flags: §10.3 8-dimension quality computation.
- RealMapperAdapter: explicit atom-map validation plus conservative RDKit MCS
  diagnostic fallback (INTEGRATION_BLOCKED only when dependencies are absent).

Key invariants enforced:
- §10.4 formal ≠ mechanistic: FakeAtomMapper NEVER sets mechanistic_atom_origin.
  Only formal_mapped_source_assignment is produced.
- §10.5 MCS/center-pair fallback: downgrades mapping_status (never
  fully_mapped), sets fallback_method explicitly, uses formal_mcs assignment.
- §10.2 frozen vocabulary: MappingStatus enum only.
- §10.3 quality: 8 dimensions computed from the report fields.
"""
from __future__ import annotations

import time
from typing import Any

from reaction_agent.hashing import canonical_hash
from reaction_agent.schemas.common import (
    MappingStatus,
    MappingQualityClass,
    SourceAssignmentMethod,
)
from reaction_agent.schemas.mapping import (
    MappingReport,
    FormalSourceAssignment,
    FormalMappedAtomPair,
)
from reaction_agent.schemas.p1_entities import NormalizedReactionRecord


# =====================================================================
# Quality flags (§10.3)
# =====================================================================

# The 8 quality dimensions from §10.3. These are the authoritative names;
# compute_quality_flags emits one entry per dimension.
QUALITY_DIMENSIONS = (
    "map_number_uniqueness",
    "mapped_heavy_atom_fraction",
    "changed_atom_coverage",
    "reactant_product_map_consistency",
    "duplicate_map_ids",
    "unmapped_changed_atoms",
    "symmetry_ambiguity",
    "resonance_tautomer_ambiguity",
)


def compute_quality_flags(report: MappingReport) -> list[str]:
    """Compute the 8 §10.3 quality dimensions from a MappingReport.

    Each dimension is emitted as a ``name=value`` string. The 8 dimensions:
    1. map_number_uniqueness — pass/fail (from report.map_number_uniqueness)
    2. mapped_heavy_atom_fraction — float in [0, 1]
    3. changed_atom_coverage — float in [0, 1]
    4. reactant_product_map_consistency — pass/partial/fail (derived from
       status: fully_mapped→pass, partially_mapped/mapping_ambiguous→partial,
       unmapped/mapping_failed→fail). A failed/unmapped mapping has no valid
       reactant-product correspondence, so 'partial' would be semantically
       wrong.
    5. duplicate_map_ids — none/detected (inverse of map_number_uniqueness)
    6. unmapped_changed_atoms — none/present (derived from changed_atom_coverage)
    7. symmetry_ambiguity — none/detected (from report.symmetry_ambiguity)
    8. resonance_tautomer_ambiguity — none/detected (from report field)

    Args:
        report: A MappingReport (formal or with mechanistic evidence).

    Returns:
        List of 8 non-empty quality dimension strings.
    """
    flags: list[str] = [
        f"map_number_uniqueness={'pass' if report.map_number_uniqueness else 'fail'}",
        f"mapped_heavy_atom_fraction={report.mapped_heavy_atom_fraction:.4f}",
        f"changed_atom_coverage={report.changed_atom_coverage:.4f}",
        f"reactant_product_map_consistency={_map_consistency(report.mapping_status)}",
        f"duplicate_map_ids={'detected' if not report.map_number_uniqueness else 'none'}",
        f"unmapped_changed_atoms={'present' if report.changed_atom_coverage < 1.0 else 'none'}",
        f"symmetry_ambiguity={'detected' if report.symmetry_ambiguity else 'none'}",
        f"resonance_tautomer_ambiguity={'detected' if report.resonance_tautomer_ambiguity else 'none'}",
    ]
    return flags


def _map_consistency(status: MappingStatus) -> str:
    """§10.3 reactant_product_map_consistency derived from mapping_status.

    - fully_mapped → pass (full reactant-product correspondence)
    - partially_mapped / mapping_ambiguous → partial (incomplete correspondence)
    - unmapped / mapping_failed → fail (no valid correspondence; 'partial'
      would be semantically wrong for a failed mapping)
    """
    if status == MappingStatus.fully_mapped:
        return "pass"
    if status in (MappingStatus.partially_mapped, MappingStatus.mapping_ambiguous):
        return "partial"
    return "fail"


# =====================================================================
# FakeAtomMapper — deterministic unit-test mapper
# =====================================================================

class FakeAtomMapper:
    """Deterministic fake atom mapper for unit tests.

    Produces a well-formed MappingReport with formal mapping ONLY (§10.4).
    Never auto-populates mechanistic_atom_origin. MCS/center-pair fallback
    downgrades mapping_status (§10.5).

    Determinism: same input record + same parameters → same output_hash.
    The mapper does NOT execute real chemistry — atom pairs are syntactic
    and deterministic, sufficient for contract testing.

    Args:
        status: MappingStatus member name (§10.2 vocabulary). Controls the
            output mapping_status. If fallback is mcs/center_pair and status
            is fully_mapped, status is downgraded.
        fallback: None | "mcs" | "center_pair". When set, fallback_method is
            populated and status is downgraded (§10.5).
        timeout: Timeout in seconds (captured in mapper_parameters, §10.1).
        duplicate_map_ids: If True, map_number_uniqueness=False (§10.6 test).
        symmetry_ambiguity: If True, symmetry_ambiguity=True on the report.
        resonance_tautomer_ambiguity: If True, resonance_tautomer_ambiguity
            on the report.
        timed_out: If True, simulates a mapper that exceeded its timeout
            (§10.6 timeout test case). Forces mapping_status=mapping_failed
            regardless of requested status, and records timed_out=true in
            mapper_parameters. Bypasses fallback (timeout = failure).
    """

    MAPPER_NAME = "fake"
    MAPPER_VERSION = "p1-fake-1"

    def __init__(
        self,
        status: str = "fully_mapped",
        fallback: str | None = None,
        timeout: int = 30,
        duplicate_map_ids: bool = False,
        symmetry_ambiguity: bool = False,
        resonance_tautomer_ambiguity: bool = False,
        timed_out: bool = False,
    ) -> None:
        if status not in MappingStatus.__members__:
            raise ValueError(
                f"Unknown status {status!r}. Valid: {list(MappingStatus.__members__)}"
            )
        if fallback is not None and fallback not in ("mcs", "center_pair"):
            raise ValueError(
                f"Unknown fallback {fallback!r}. Valid: None, 'mcs', 'center_pair'"
            )
        self._status = MappingStatus[status]
        self._fallback = fallback
        self._timeout = timeout
        self._duplicate_map_ids = duplicate_map_ids
        self._symmetry_ambiguity = symmetry_ambiguity
        self._resonance_tautomer_ambiguity = resonance_tautomer_ambiguity
        self._timed_out = timed_out

    # -- Public properties (§10.1 capture list) --

    @property
    def mapper_name(self) -> str:
        return self.MAPPER_NAME

    @property
    def mapper_version(self) -> str:
        return self.MAPPER_VERSION

    def is_available(self) -> bool:
        """FakeAtomMapper is always available (it's deterministic, no deps)."""
        return True

    # -- Core Protocol method --

    def map_reaction(self, reaction: NormalizedReactionRecord) -> MappingReport:
        """Produce a deterministic formal MappingReport.

        §10.4: formal ONLY. mechanistic_atom_origin is never set.
        §10.5: fallback downgrades status.
        """
        start = time.monotonic()

        # -- Resolve final status + fallback + assignment_method --
        status = self._status
        fallback_method: str | None = None
        assignment_method = SourceAssignmentMethod.formal_mapped

        # §10.6 timeout: a timed-out mapping forces mapping_failed (no fallback).
        # Timeout = failure regardless of requested status; bypasses fallback.
        if self._timed_out:
            status = MappingStatus.mapping_failed
        elif self._fallback == "mcs":
            fallback_method = "mcs"
            assignment_method = SourceAssignmentMethod.formal_mcs
            # §10.5: MCS must not pretend full mapping
            if status == MappingStatus.fully_mapped:
                status = MappingStatus.partially_mapped
        elif self._fallback == "center_pair":
            fallback_method = "center_pair"
            assignment_method = SourceAssignmentMethod.unknown
            # §10.5: center-pair must not pretend full mapping
            if status == MappingStatus.fully_mapped:
                status = MappingStatus.partially_mapped

        # -- Input hash (basic types only — T1 fix, no datetime/Path) --
        input_payload = {
            "reaction_id": reaction.reaction_id,
            "normalized_reaction": reaction.normalized_reaction,
            "source_record_id": reaction.source_record_id,
        }
        input_hash = canonical_hash(input_payload)

        # -- Deterministic formal atom pairs (typed, §11) --
        atom_pairs = self._generate_atom_pairs(reaction, status)

        # -- Fractions + uniqueness (derived from status + duplicate flag) --
        mapped_fraction, changed_coverage, map_uniqueness = (
            self._compute_fractions(status)
        )
        # §10.6: duplicate_map_ids overrides uniqueness to False
        if self._duplicate_map_ids:
            map_uniqueness = False

        # -- Formal source assignment (FORMAL ONLY — §10.4) --
        formal_assignment = FormalSourceAssignment(
            mapper_name=self.MAPPER_NAME,
            mapper_version=self.MAPPER_VERSION,
            mapped_atom_pairs=atom_pairs,
            assignment_method=assignment_method,
            assignment_quality=self._quality_class(status),
            assignment_ambiguity=(status == MappingStatus.mapping_ambiguous),
        )

        # -- mapper_parameters (basic types only, §10.1 capture) --
        mapper_parameters: dict[str, str] = {
            "status": status.value,
            "timeout": str(self._timeout),
        }
        if fallback_method is not None:
            mapper_parameters["fallback"] = fallback_method
        if self._timed_out:
            mapper_parameters["timed_out"] = "true"

        # -- Output hash (content-addressed, deterministic) --
        output_payload = {
            "input_hash": input_hash,
            "mapper_name": self.MAPPER_NAME,
            "mapper_version": self.MAPPER_VERSION,
            "mapping_status": status.value,
            "fallback_method": fallback_method,
            "assignment_method": assignment_method.value,
        }
        output_hash = canonical_hash(output_payload)

        # -- Build report WITHOUT quality_flags first (to compute from fields) --
        report = MappingReport(
            mapper_name=self.MAPPER_NAME,
            mapper_version=self.MAPPER_VERSION,
            mapper_parameters=mapper_parameters,
            input_hash=input_hash,
            output_hash=output_hash,
            mapping_status=status,
            mapped_heavy_atom_fraction=mapped_fraction,
            map_number_uniqueness=map_uniqueness,
            changed_atom_coverage=changed_coverage,
            formal_mapped_source_assignment=formal_assignment,
            mechanistic_atom_origin=None,  # §10.4: NEVER auto-populated
            fallback_method=fallback_method,
            symmetry_ambiguity=self._symmetry_ambiguity,
            resonance_tautomer_ambiguity=self._resonance_tautomer_ambiguity,
            quality_flags=[],  # placeholder; computed below
        )

        # -- Compute quality flags + attach immutably --
        flags = compute_quality_flags(report)
        runtime_ms = int((time.monotonic() - start) * 1000)
        # Store runtime in mapper_parameters for §10.1 capture (non-mutating copy)
        final_params = {**mapper_parameters, "runtime_ms": str(runtime_ms)}
        return report.model_copy(update={
            "quality_flags": flags,
            "mapper_parameters": final_params,
        })

    # -- Internal helpers --

    def _generate_atom_pairs(
        self, reaction: NormalizedReactionRecord, status: MappingStatus
    ) -> list[FormalMappedAtomPair]:
        """Generate deterministic formal atom pairs (typed, §11).

        For fully_mapped: 3 pairs (full correspondence).
        For partially_mapped/mapping_ambiguous: 1 pair (partial).
        For unmapped/mapping_failed: 0 pairs.
        """
        if status in (MappingStatus.unmapped, MappingStatus.mapping_failed):
            return []

        rid = reaction.reaction_id
        reactant_pid = f"{rid}_reactant_0"
        product_pid = f"{rid}_product_0"

        if status == MappingStatus.fully_mapped:
            return [
                FormalMappedAtomPair(
                    reactant_participant_id=reactant_pid,
                    reactant_atom_map=i,
                    product_participant_id=product_pid,
                    product_atom_map=i,
                )
                for i in range(3)
            ]
        # partially_mapped / mapping_ambiguous: single pair
        return [
            FormalMappedAtomPair(
                reactant_participant_id=reactant_pid,
                reactant_atom_map=0,
                product_participant_id=product_pid,
                product_atom_map=0,
            )
        ]

    @staticmethod
    def _compute_fractions(
        status: MappingStatus
    ) -> tuple[float, float, bool]:
        """Return (mapped_heavy_atom_fraction, changed_atom_coverage, map_uniqueness)."""
        if status == MappingStatus.fully_mapped:
            return (1.0, 1.0, True)
        if status == MappingStatus.partially_mapped:
            return (0.6, 0.5, True)
        if status == MappingStatus.mapping_ambiguous:
            return (0.5, 0.5, True)
        # unmapped / mapping_failed
        return (0.0, 0.0, True)

    @staticmethod
    def _quality_class(status: MappingStatus) -> MappingQualityClass:
        if status == MappingStatus.fully_mapped:
            return MappingQualityClass.high_quality
        if status == MappingStatus.partially_mapped:
            return MappingQualityClass.acceptable
        if status == MappingStatus.mapping_ambiguous:
            return MappingQualityClass.low_quality
        return MappingQualityClass.unknown


# =====================================================================
# RealMapperAdapter — real mapper wrapper skeleton
# =====================================================================

class RealMapperAdapter:
    """Validated atom-map reader with a conservative RDKit MCS fallback.

    RDKit is not a learned atom mapper.  This adapter therefore makes the
    evidence boundary explicit:

    * complete, unique atom-map numbers already present in the source reaction
      are validated and emitted as ``formal_mapped`` evidence;
    * reactions without map numbers use RDKit MCS only as a diagnostic
      fallback and can never receive ``fully_mapped`` status;
    * no path creates mechanistic atom-origin evidence.

    The optional rxnmapper/rxn4chemistry names remain reserved integration
    points.  They fail closed until their real implementations are wired.
    """

    SUPPORTED_BACKENDS = ("rdkit", "rxnmapper", "rxn4chemistry")

    def __init__(
        self,
        backend: str = "rdkit",
        timeout: int = 300,
        parameters: dict[str, str] | None = None,
    ) -> None:
        if backend not in self.SUPPORTED_BACKENDS:
            raise ValueError(
                f"Unsupported backend {backend!r}. "
                f"Supported: {list(self.SUPPORTED_BACKENDS)}"
            )
        self.backend = backend
        self.timeout = timeout
        self.parameters: dict[str, str] = parameters or {}
        self._available = self._probe_backend()

    def is_available(self) -> bool:
        """Return True if the real mapper backend is importable."""
        return self._available

    def map_reaction(self, reaction: NormalizedReactionRecord) -> MappingReport:
        """Return a formal mapping report without overstating MCS evidence."""
        if not self._available:
            raise NotImplementedError(
                f"RealMapperAdapter backend={self.backend!r} is not available — "
                f"INTEGRATION_BLOCKED. Install the declared backend dependencies "
                f"to unblock T4 integration."
            )
        if self.backend != "rdkit":
            raise NotImplementedError(
                f"RealMapperAdapter backend={self.backend!r} is importable but its "
                f"integration is not implemented — INTEGRATION_BLOCKED."
            )
        return self._map_with_rdkit(reaction)

    def _map_with_rdkit(
        self, reaction: NormalizedReactionRecord
    ) -> MappingReport:
        """Validate explicit maps or compute a non-strict RDKit MCS fallback."""
        start = time.monotonic()
        input_hash = canonical_hash({
            "reaction_id": reaction.reaction_id,
            "normalized_reaction": reaction.normalized_reaction,
            "source_record_id": reaction.source_record_id,
        })

        try:
            from rdkit import Chem, rdBase
        except ImportError as exc:  # defensive against environment changes
            raise NotImplementedError(
                "RDKit disappeared after the availability probe — "
                "INTEGRATION_BLOCKED"
            ) from exc

        parsed, parse_error = self._parse_reaction(Chem, reaction.normalized_reaction)
        if parsed is None:
            return self._build_report(
                reaction=reaction,
                input_hash=input_hash,
                mapper_version=getattr(rdBase, "rdkitVersion", "unknown"),
                status=MappingStatus.mapping_failed,
                atom_pairs=[],
                mapped_fraction=0.0,
                changed_coverage=0.0,
                map_uniqueness=True,
                assignment_method=SourceAssignmentMethod.unknown,
                assignment_quality=MappingQualityClass.unknown,
                fallback_method=None,
                symmetry_ambiguity=False,
                extra_parameters={"parse_error": parse_error or "invalid_reaction"},
                started_at=start,
            )

        reactants, products = parsed
        explicit = self._explicit_map_result(reaction, reactants, products)
        if explicit is not None:
            return self._build_report(
                reaction=reaction,
                input_hash=input_hash,
                mapper_version=getattr(rdBase, "rdkitVersion", "unknown"),
                started_at=start,
                **explicit,
            )

        mcs = self._mcs_result(reaction, reactants, products)
        return self._build_report(
            reaction=reaction,
            input_hash=input_hash,
            mapper_version=getattr(rdBase, "rdkitVersion", "unknown"),
            started_at=start,
            **mcs,
        )

    @staticmethod
    def _parse_reaction(Chem: Any, reaction_smiles: str) -> tuple[Any, str | None]:
        """Parse both sides fragment-by-fragment; never silently drop a fragment."""
        if reaction_smiles.count(">>") != 1:
            return None, "reaction_must_contain_exactly_one_double_arrow"
        left, right = reaction_smiles.split(">>")
        if not left or not right:
            return None, "reaction_side_is_empty"

        def parse_side(text: str) -> list[Any] | None:
            fragments = text.split(".")
            if any(not fragment for fragment in fragments):
                return None
            molecules = [Chem.MolFromSmiles(fragment) for fragment in fragments]
            return None if any(mol is None for mol in molecules) else molecules

        reactants = parse_side(left)
        products = parse_side(right)
        if reactants is None or products is None:
            return None, "rdkit_failed_to_parse_one_or_more_fragments"
        return (reactants, products), None

    @staticmethod
    def _heavy_atom_count(molecules: list[Any]) -> int:
        return sum(
            1
            for molecule in molecules
            for atom in molecule.GetAtoms()
            if atom.GetAtomicNum() > 1
        )

    def _explicit_map_result(
        self,
        reaction: NormalizedReactionRecord,
        reactants: list[Any],
        products: list[Any],
    ) -> dict[str, Any] | None:
        """Validate map numbers supplied by the source; return None if absent."""
        def collect(molecules: list[Any]) -> dict[int, list[tuple[int, int, int]]]:
            result: dict[int, list[tuple[int, int, int]]] = {}
            for fragment_index, molecule in enumerate(molecules):
                for atom in molecule.GetAtoms():
                    map_number = atom.GetAtomMapNum()
                    if map_number > 0:
                        result.setdefault(map_number, []).append(
                            (fragment_index, atom.GetIdx(), atom.GetAtomicNum())
                        )
            return result

        r_maps = collect(reactants)
        p_maps = collect(products)
        if not r_maps and not p_maps:
            return None

        unique = all(len(v) == 1 for v in r_maps.values()) and all(
            len(v) == 1 for v in p_maps.values()
        )
        atom_pairs: list[FormalMappedAtomPair] = []
        element_mismatch = False
        for map_number in sorted(set(r_maps) & set(p_maps)):
            if len(r_maps[map_number]) != 1 or len(p_maps[map_number]) != 1:
                continue
            r_fragment, _r_index, r_element = r_maps[map_number][0]
            p_fragment, _p_index, p_element = p_maps[map_number][0]
            if r_element != p_element:
                element_mismatch = True
                continue
            atom_pairs.append(FormalMappedAtomPair(
                reactant_participant_id=(
                    f"{reaction.reaction_id}_reactant_{r_fragment}"
                ),
                reactant_atom_map=map_number,
                product_participant_id=(
                    f"{reaction.reaction_id}_product_{p_fragment}"
                ),
                product_atom_map=map_number,
            ))

        total_r = self._heavy_atom_count(reactants)
        total_p = self._heavy_atom_count(products)
        denominator = max(total_r, total_p, 1)
        mapped_fraction = len(atom_pairs) / denominator
        all_atoms_mapped = (
            len(r_maps) == total_r
            and len(p_maps) == total_p
            and set(r_maps) == set(p_maps)
            and len(atom_pairs) == total_r == total_p
        )

        ambiguous = (not unique) or element_mismatch
        if ambiguous:
            status = MappingStatus.mapping_ambiguous
            quality = MappingQualityClass.low_quality
        elif all_atoms_mapped:
            status = MappingStatus.fully_mapped
            quality = MappingQualityClass.high_quality
        elif atom_pairs:
            status = MappingStatus.partially_mapped
            quality = MappingQualityClass.acceptable
        else:
            status = MappingStatus.unmapped
            quality = MappingQualityClass.unknown

        return {
            "status": status,
            "atom_pairs": atom_pairs,
            "mapped_fraction": min(1.0, mapped_fraction),
            # A complete validated source map covers every formally changed atom.
            # Partial maps remain conservative because unmapped changes are unknown.
            "changed_coverage": 1.0 if all_atoms_mapped else min(1.0, mapped_fraction),
            "map_uniqueness": unique,
            "assignment_method": SourceAssignmentMethod.formal_mapped,
            "assignment_quality": quality,
            "fallback_method": None,
            "symmetry_ambiguity": ambiguous,
            "extra_parameters": {
                "mode": "validate_explicit_atom_maps",
                "element_mismatch": str(element_mismatch).lower(),
            },
        }

    def _mcs_result(
        self,
        reaction: NormalizedReactionRecord,
        reactants: list[Any],
        products: list[Any],
    ) -> dict[str, Any]:
        """Find one best fragment-pair MCS and mark it as non-strict evidence."""
        from rdkit import Chem
        from rdkit.Chem import rdFMCS

        candidates: list[tuple[int, int, int, str, Any, Any]] = []
        timed_out = False
        for r_index, reactant in enumerate(reactants):
            for p_index, product in enumerate(products):
                result = rdFMCS.FindMCS(
                    [reactant, product],
                    atomCompare=rdFMCS.AtomCompare.CompareElements,
                    bondCompare=rdFMCS.BondCompare.CompareOrder,
                    ringMatchesRingOnly=True,
                    completeRingsOnly=True,
                    timeout=max(1, int(self.timeout)),
                )
                timed_out = timed_out or bool(result.canceled)
                if result.numAtoms > 0 and result.smartsString:
                    candidates.append((
                        result.numAtoms,
                        r_index,
                        p_index,
                        result.smartsString,
                        reactant,
                        product,
                    ))

        if not candidates:
            status = MappingStatus.mapping_failed if timed_out else MappingStatus.unmapped
            return {
                "status": status,
                "atom_pairs": [],
                "mapped_fraction": 0.0,
                "changed_coverage": 0.0,
                "map_uniqueness": True,
                "assignment_method": SourceAssignmentMethod.formal_mcs,
                "assignment_quality": MappingQualityClass.unknown,
                "fallback_method": "mcs",
                "symmetry_ambiguity": False,
                "extra_parameters": {
                    "mode": "rdkit_mcs_fallback",
                    "timed_out": str(timed_out).lower(),
                },
            }

        # Deterministic ordering: most atoms first, then participant positions,
        # then SMARTS. Equal best candidates are retained as ambiguity evidence.
        candidates.sort(key=lambda item: (-item[0], item[1], item[2], item[3]))
        best = candidates[0]
        best_size, r_index, p_index, smarts, reactant, product = best
        query = Chem.MolFromSmarts(smarts)
        r_matches = reactant.GetSubstructMatches(query, uniquify=True)
        p_matches = product.GetSubstructMatches(query, uniquify=True)
        tied_best = sum(1 for item in candidates if item[0] == best_size) > 1
        ambiguous = tied_best or len(r_matches) != 1 or len(p_matches) != 1

        atom_pairs: list[FormalMappedAtomPair] = []
        if r_matches and p_matches:
            for r_atom, p_atom in zip(r_matches[0], p_matches[0]):
                atom_pairs.append(FormalMappedAtomPair(
                    reactant_participant_id=(
                        f"{reaction.reaction_id}_reactant_{r_index}"
                    ),
                    reactant_atom_map=int(r_atom),
                    product_participant_id=(
                        f"{reaction.reaction_id}_product_{p_index}"
                    ),
                    product_atom_map=int(p_atom),
                ))

        denominator = max(
            self._heavy_atom_count(reactants),
            self._heavy_atom_count(products),
            1,
        )
        mapped_fraction = min(1.0, len(atom_pairs) / denominator)
        status = (
            MappingStatus.mapping_ambiguous
            if ambiguous
            else MappingStatus.partially_mapped
        )
        return {
            "status": status,
            "atom_pairs": atom_pairs,
            "mapped_fraction": mapped_fraction,
            # MCS is scaffold overlap, not changed-atom mapping.
            "changed_coverage": 0.0,
            "map_uniqueness": True,
            "assignment_method": SourceAssignmentMethod.formal_mcs,
            "assignment_quality": (
                MappingQualityClass.low_quality
                if ambiguous
                else MappingQualityClass.acceptable
            ),
            "fallback_method": "mcs",
            "symmetry_ambiguity": ambiguous,
            "extra_parameters": {
                "mode": "rdkit_mcs_fallback",
                "mcs_smarts": smarts,
                "timed_out": str(timed_out).lower(),
                "best_fragment_tie": str(tied_best).lower(),
            },
        }

    def _build_report(
        self,
        *,
        reaction: NormalizedReactionRecord,
        input_hash: str,
        mapper_version: str,
        status: MappingStatus,
        atom_pairs: list[FormalMappedAtomPair],
        mapped_fraction: float,
        changed_coverage: float,
        map_uniqueness: bool,
        assignment_method: SourceAssignmentMethod,
        assignment_quality: MappingQualityClass,
        fallback_method: str | None,
        symmetry_ambiguity: bool,
        extra_parameters: dict[str, str],
        started_at: float,
    ) -> MappingReport:
        """Build and hash the authoritative formal report."""
        formal_assignment = FormalSourceAssignment(
            mapper_name=self.backend,
            mapper_version=mapper_version,
            mapped_atom_pairs=atom_pairs,
            assignment_method=assignment_method,
            assignment_quality=assignment_quality,
            assignment_ambiguity=(status == MappingStatus.mapping_ambiguous),
        )
        output_hash = canonical_hash({
            "input_hash": input_hash,
            "mapper_name": self.backend,
            "mapper_version": mapper_version,
            "mapping_status": status.value,
            "mapped_heavy_atom_fraction": mapped_fraction,
            "changed_atom_coverage": changed_coverage,
            "map_number_uniqueness": map_uniqueness,
            "fallback_method": fallback_method,
            "atom_pairs": [pair.model_dump(mode="json") for pair in atom_pairs],
        })
        parameters = {
            "timeout": str(self.timeout),
            **self.parameters,
            **extra_parameters,
        }
        report = MappingReport(
            mapper_name=self.backend,
            mapper_version=mapper_version,
            mapper_parameters=parameters,
            input_hash=input_hash,
            output_hash=output_hash,
            mapping_status=status,
            mapped_heavy_atom_fraction=mapped_fraction,
            map_number_uniqueness=map_uniqueness,
            changed_atom_coverage=changed_coverage,
            formal_mapped_source_assignment=formal_assignment,
            mechanistic_atom_origin=None,
            fallback_method=fallback_method,
            symmetry_ambiguity=symmetry_ambiguity,
            resonance_tautomer_ambiguity=False,
            quality_flags=[],
        )
        return report.model_copy(update={
            "quality_flags": compute_quality_flags(report),
            "mapper_parameters": {
                **parameters,
                "runtime_ms": str(int((time.monotonic() - started_at) * 1000)),
            },
        })

    # -- Backend probes --

    def _probe_backend(self) -> bool:
        """Probe whether the configured backend is importable."""
        probes = {
            "rdkit": self._probe_rdkit,
            "rxnmapper": self._probe_rxnmapper,
            "rxn4chemistry": self._probe_rxn4chemistry,
        }
        return probes[self.backend]()

    @staticmethod
    def _probe_rdkit() -> bool:
        """Probe for rdkit + numpy + networkx + scipy (all 4 declared deps).

        The adapter's INTEGRATION_BLOCKED message and checkpoint report
        declare rdkit/numpy/networkx/scipy as dependencies. _probe_rdkit must
        probe all 4 so that a partial install (e.g. rdkit+numpy present but
        networkx/scipy absent) does NOT report is_available()=True — _do_map
        would crash on the missing dep later. Keeps the probe aligned with
        the declared dependencies.
        """
        try:
            import rdkit  # noqa: F401
            import numpy  # noqa: F401
            import networkx  # noqa: F401
            import scipy  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _probe_rxnmapper() -> bool:
        """Probe for rxnmapper package."""
        try:
            import rxnmapper  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _probe_rxn4chemistry() -> bool:
        """Probe for rxn4chemistry package."""
        try:
            import rxn4chemistry  # noqa: F401
            return True
        except ImportError:
            return False
