"""Atom-mapping adapter implementations (chatgpt_p1_train.md §10).

Contains:
- FakeAtomMapper: deterministic mapper for unit tests (formal only, §10.4).
- compute_quality_flags: §10.3 8-dimension quality computation.
- RealMapperAdapter: real mapper wrapper skeleton (INTEGRATION_BLOCKED when
  rdkit/numpy/networkx/scipy absent).

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
    """Real atom-mapper adapter skeleton (§10.1).

    Wraps a real mapper backend (rdkit/rxnmapper/rxn4chemistry). When the
    backend is unavailable (Preflight BLOCKED: rdkit/numpy/networkx/scipy
    absent), ``map_reaction`` raises NotImplementedError with the
    INTEGRATION_BLOCKED marker (§10.7).

    This is NOT a skip — the adapter explicitly reports the blocked state so
    the P1 Gate (G04) can act on it. T4 is marked UNIT_CONTRACT_COMPLETE /
    INTEGRATION_BLOCKED (not PASS) until a real backend is installed.

    When the backend IS available, the real mapping implementation would go
    in ``_do_map``. Currently a skeleton — not reachable when blocked.
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
        """Map atoms using the real backend.

        Raises NotImplementedError with INTEGRATION_BLOCKED marker when the
        backend is unavailable (§10.7).
        """
        if not self._available:
            raise NotImplementedError(
                f"RealMapperAdapter backend={self.backend!r} is not available — "
                f"INTEGRATION_BLOCKED. Preflight status: BLOCKED "
                f"(rdkit_absent: rdkit/numpy/networkx/scipy all absent in .venv). "
                f"Install the real mapper backend to unblock T4 integration."
            )
        # Backend is available but real mapping is not yet implemented.
        # This path is only reachable when the backend is installed.
        raise NotImplementedError(
            f"RealMapperAdapter.map_reaction for {self.backend!r} is a skeleton — "
            f"backend is available but the real mapping implementation is not yet "
            f"wired. This is a T4 follow-up task."
        )

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
