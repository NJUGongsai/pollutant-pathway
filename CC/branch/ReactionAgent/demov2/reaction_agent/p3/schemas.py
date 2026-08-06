"""P3 frozen interface schemas (final_plan §6, CHATGPT_P3 prompt §6).

These are the P3->P4 frozen contracts.  P4 must be able to consume them
without reading P3 internal mutable objects.

Every output record carries a case_id / query_id / fold_id / snapshot_id /
snapshot_hash / run_id namespace plus an ``evidence_kind`` that declares
whether the record is real, synthetic_fixture, blocked or diagnostic.

Discipline (final_plan §2.3, ADR-0005):
- StrictModel everywhere: extra="forbid", strict=True (no coercion).
- No forbidden bias field names (confidence / *_probability / etc.).
- Scientific and system failures are separate (``KernelFailure.category``).
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import field_validator, model_validator

from reaction_agent.schemas.common import StrictModel, NonEmptyStr
from reaction_agent.schemas.evidence import ReactionEvidence
from reaction_agent.schemas.mapping import MappingReport
from reaction_agent.schemas.ledger import (
    CandidateAnalogyLedger,
    SourceReactionLedger,
)
from reaction_agent.schemas.p1_entities import (
    DonorEligibilityAssessment,
    EligibilityDecision,
    ResolvedTransformedLineage,
)

P3_SCHEMA_VERSION = "p3-1"
P3_KERNEL_VERSION = "p3-1"


# -- Enumerations -----------------------------------------------------------


class EvidenceKind(str, Enum):
    """Evidence provenance class.  Synthetic fixtures never masquerade as real."""
    real = "real"
    synthetic_fixture = "synthetic_fixture"
    blocked = "blocked"
    diagnostic = "diagnostic"


class EvidenceReference(StrictModel):
    """A typed, versioned evidence reference bound to an EXECUTED artifact
    (R4-A).  Never an arbitrary string: the reference binds

    - artifact type (kernel_run / capability_probe / mutation_case / ...);
    - artifact path-or-ID;
    - the content hash over a canonical content preimage (RECOMPUTED by the
      gate verifier — a tampered content whose hash was not updated is
      rejected);
    - the schema/version;
    - the run ID and the fold/snapshot namespace the artifact belongs to.

    ``content`` is the canonical content preimage the hash is computed over;
    keeping it embedded makes the hash independently recomputable.
    """
    artifact_type: NonEmptyStr
    artifact_id: NonEmptyStr
    content_hash: NonEmptyStr
    schema_version: NonEmptyStr = P3_SCHEMA_VERSION
    run_id: NonEmptyStr
    fold_id: str = ""
    snapshot_id: str = ""
    snapshot_hash: str = ""
    content: dict = {}


class CapabilityState(str, Enum):
    """Component availability state."""
    available = "available"
    unavailable = "unavailable"
    unknown = "unknown"


class KernelStage(str, Enum):
    """Deterministic predictor lifecycle (final_plan §6.10)."""
    RECEIVED = "RECEIVED"
    NORMALIZED = "NORMALIZED"
    BASELINE_EVIDENCE_LOADED = "BASELINE_EVIDENCE_LOADED"
    HYPOTHESES_COMPILED = "HYPOTHESES_COMPILED"
    SITES_ENUMERATED = "SITES_ENUMERATED"
    CANDIDATES_VALIDATED = "CANDIDATES_VALIDATED"


class KernelStatus(str, Enum):
    """Top-level kernel outcome."""
    completed = "completed"
    blocked = "blocked"
    failed = "failed"


class SiteEligibility(str, Enum):
    eligible = "eligible"
    ineligible = "ineligible"


# -- Capability (CHATGPT_P3 prompt §6: CapabilityStatus) --------------------


class ComponentCapability(StrictModel):
    """Availability of a single kernel dependency."""
    component: NonEmptyStr
    state: CapabilityState
    version: str = ""
    detail: str = ""
    evidence_kind: EvidenceKind = EvidenceKind.blocked


class CapabilityStatus(StrictModel):
    """Per-run capability inventory (R2-H: split capability semantics).

    - chemistry_backend: RDKit is importable (NOT an atom mapper).
    - explicit_map_validator: the P1 adapter can validate explicit atom maps.
    - strict_atom_mapper: a true learned atom mapper (rxnmapper etc.) is wired.
    - mcs_diagnostic: RDKit MCS fallback available (diagnostic, NEVER strict).
    - real_snapshot / automatic_donor: real evidence capabilities.
    """
    run_id: NonEmptyStr
    query_id: NonEmptyStr
    fold_id: NonEmptyStr
    case_id: NonEmptyStr
    snapshot_id: str = ""
    snapshot_hash: str = ""
    components: list[ComponentCapability] = []
    chemistry_backend_available: bool = False
    explicit_map_validator_available: bool = False
    strict_atom_mapper_available: bool = False
    mcs_diagnostic_available: bool = False
    real_snapshot_available: bool = False
    automatic_donor_available: bool = False

    @model_validator(mode="after")
    def _flags_match_components(self) -> "CapabilityStatus":
        for flag_name, component_name in (
            ("chemistry_backend_available", "chemistry_backend"),
            ("explicit_map_validator_available", "explicit_map_validator"),
            ("strict_atom_mapper_available", "strict_atom_mapper"),
            ("mcs_diagnostic_available", "mcs_diagnostic"),
            ("real_snapshot_available", "real_snapshot"),
            ("automatic_donor_available", "automatic_donor"),
        ):
            present = any(c.component == component_name for c in self.components)
            flag = bool(getattr(self, flag_name))
            if present and flag != next(
                c.state is CapabilityState.available
                for c in self.components
                if c.component == component_name
            ):
                raise ValueError(
                    f"CapabilityStatus: flag {flag_name} contradicts "
                    f"component {component_name} state"
                )
            if not present and flag:
                raise ValueError(
                    f"CapabilityStatus: flag {flag_name} is set but component "
                    f"{component_name} is absent from components"
                )
        return self


# -- KernelRunManifest (CHATGPT_P3 prompt §6) -------------------------------


class ComponentVersion(StrictModel):
    name: NonEmptyStr
    version: NonEmptyStr
    schema_version: str = P3_SCHEMA_VERSION


class KernelRunManifest(StrictModel):
    """Run / request / snapshot / fold / config / component versions."""
    run_id: NonEmptyStr
    request: NonEmptyStr
    request_hash: NonEmptyStr
    query_id: NonEmptyStr
    case_id: NonEmptyStr
    fold_id: NonEmptyStr
    snapshot_id: str = ""
    snapshot_hash: str = ""
    config: dict[str, str] = {}
    component_versions: list[ComponentVersion] = []
    seed: int = 0
    kernel_version: NonEmptyStr = P3_KERNEL_VERSION
    schema_version: NonEmptyStr = P3_SCHEMA_VERSION
    manifest_hash: str = ""


# -- NormalizedQuery (CHATGPT_P3 prompt §6) ---------------------------------


class NormalizationPolicy(StrictModel):
    version: NonEmptyStr
    canonical_smiles: bool = True
    charge_policy: NonEmptyStr = "keep_formal_charge"
    salt_policy: NonEmptyStr = "preserve_multi_fragment"
    tautomer_policy: NonEmptyStr = "no_tautomer_canonicalization"
    isotope_policy: NonEmptyStr = "preserve_isotopes"
    stereo_policy: NonEmptyStr = "ignore_stereo_for_identity"


class NormalizedQuery(StrictModel):
    query_id: NonEmptyStr
    run_id: NonEmptyStr
    case_id: NonEmptyStr
    fold_id: NonEmptyStr
    snapshot_id: str = ""
    snapshot_hash: str = ""
    input_smiles: NonEmptyStr
    canonical_smiles: NonEmptyStr
    identity_hash: NonEmptyStr
    heavy_atom_count: int
    formal_charge: int
    fragment_count: int
    normalization_policy: NormalizationPolicy
    evidence_kind: EvidenceKind = EvidenceKind.real

    @field_validator("heavy_atom_count")
    @classmethod
    def _heavy_atom_count_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"heavy_atom_count must be non-negative, got {v}")
        return v

    @field_validator("fragment_count")
    @classmethod
    def _fragment_count_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"fragment_count must be >= 1 for a valid query, got {v}")
        return v

    # formal_charge is a signed integer (anions/cations are legal queries).
    # No non-negative constraint is applied.


# -- ResolvedDonorEvidence (CHATGPT_P3 prompt §6) ---------------------------


class DonorContext(StrictModel):
    """Complete auditable donor package (final_plan §6.4)."""
    donor_participant_id: NonEmptyStr
    donor_molecule_id: NonEmptyStr
    donor_canonical_smiles: NonEmptyStr
    reaction_id: NonEmptyStr
    reaction_evidence: ReactionEvidence
    mapping_report: MappingReport
    resolved_lineages: list[ResolvedTransformedLineage]
    source_ledger: SourceReactionLedger
    eligibility_decision: EligibilityDecision
    donor_eligibility: DonorEligibilityAssessment
    similarity_features: dict[str, float] = {}
    evidence_kind: EvidenceKind = EvidenceKind.synthetic_fixture

    @model_validator(mode="after")
    def _lineages_match_reaction(self) -> "DonorContext":
        # reaction_evidence.resolved_transformed_lineages is a list of lineage
        # ID strings; self.resolved_lineages are ResolvedTransformedLineage
        # objects.  Check cross-consistency without dereferencing strings.
        ev_ids = set(self.reaction_evidence.resolved_transformed_lineages)
        for lineage in self.resolved_lineages:
            if ev_ids and lineage.lineage_id not in ev_ids:
                raise ValueError(
                    f"resolved lineage {lineage.lineage_id} not declared on "
                    f"reaction_evidence.resolved_transformed_lineages"
                )
        return self


class ResolvedDonorEvidence(StrictModel):
    """Frozen donor evidence bundle consumed by transform extraction."""
    donor_id: NonEmptyStr
    run_id: NonEmptyStr
    fold_id: NonEmptyStr
    query_id: NonEmptyStr
    case_id: NonEmptyStr
    snapshot_id: str = ""
    snapshot_hash: str = ""
    context: DonorContext
    retrieval_round: int = 1
    stop_reason: str = "donor_set_complete"
    evidence_kind: EvidenceKind = EvidenceKind.synthetic_fixture
    # R3-B: the verified reaction authority hash bound to this evidence
    # bundle (recomputed from the live complete record by the loader).
    reaction_authority_hash: str = ""


# -- StrictTransformation (CHATGPT_P3 prompt §6, final_design §12) ----------


class BondChange(StrictModel):
    atom_map_a: int
    atom_map_b: int
    operation: Literal["add", "delete", "order_change"]
    # 1 / 2 / 3 = single / double / triple; 1.5 = aromatic.  Aromaticity is
    # never silently truncated to single (R2-D).
    new_order: float | None = None

    @field_validator("new_order")
    @classmethod
    def _valid_order(cls, v: float | None) -> float | None:
        if v is not None and v not in (1, 2, 3, 1.5):
            raise ValueError(f"bond order must be 1/2/3/1.5, got {v}")
        return v


class AtomStateChange(StrictModel):
    atom_map_number: int
    element_change: str | None = None          # new element symbol, if element changes
    formal_charge_change: int | None = None
    target_formal_charge: int | None = None
    h_count_change: int | None = None
    target_h_count: int | None = None
    aromaticity_change: Literal["none", "to_aromatic", "from_aromatic"] = "none"


class TransferredAtom(StrictModel):
    transfer_map_number: int
    element: NonEmptyStr
    formal_charge: int = 0
    h_count: int = 0
    source_participant_id: NonEmptyStr
    bonds_to: list[dict[str, int]] = []  # bonds to COMMON atoms: [{"atom_map": n, "order": 1}, ...]
    bonds_to_transferred: list[dict[str, int]] = []  # bonds to OTHER transferred atoms (transfer_map_number refs)


class RemovedSinkAssignment(StrictModel):
    """Exact map-to-sink participant assignment for ONE removed atom (R3-C).

    The transform preimage hashes these PAIRS — hashing only the removed map
    keys (Round 2) silently dropped the sink participant values.
    """
    atom_map: int
    sink_participant_id: NonEmptyStr


class SitePrecondition(StrictModel):
    precondition_id: NonEmptyStr
    kind: NonEmptyStr  # e.g. "functional_group", "atom_degree", "charge", "aromaticity"
    atom_map_number: int | None = None
    params: dict[str, object] = {}


class StrictTransformation(StrictModel):
    """Canonical, content-addressed, replayable transform (final_design §12.1)."""
    transformation_id: NonEmptyStr
    run_id: NonEmptyStr
    case_id: NonEmptyStr
    query_id: NonEmptyStr
    fold_id: NonEmptyStr
    snapshot_id: str = ""
    snapshot_hash: str = ""
    source_lineage_ids: list[NonEmptyStr]
    # R3-B/R3-C: authority bindings carried on the transform itself so the
    # canonical preimage is recomputable from the model fields alone.
    source_lineage_hash: str = ""
    donor_reaction_id: NonEmptyStr
    reaction_authority_hash: str = ""
    mapped_atom_edits: list[int]
    bond_changes: list[BondChange]
    atom_state_changes: list[AtomStateChange]
    transferred_atoms: list[TransferredAtom]
    removed_atom_maps: list[int] = []
    # R3-C: exact map-to-sink participant assignments (never keys-only).
    removed_atom_sinks: list[RemovedSinkAssignment] = []
    donor_site_atom_map_numbers: list[int]
    donor_site_smiles: NonEmptyStr
    donor_site_pattern: NonEmptyStr  # SMARTS query for site matching
    local_environment: list[int] = []
    strict_preconditions: list[SitePrecondition] = []
    ledger_requirements: list[NonEmptyStr] = []
    canonical_transform_hash: NonEmptyStr
    transform_version: NonEmptyStr = "p3-1"
    evidence_kind: EvidenceKind = EvidenceKind.synthetic_fixture

    @model_validator(mode="after")
    def _edits_referenced(self) -> "StrictTransformation":
        known = set(self.mapped_atom_edits)
        for bc in self.bond_changes:
            if bc.atom_map_a not in known or bc.atom_map_b not in known:
                raise ValueError(
                    f"BondChange references atom map numbers outside "
                    f"mapped_atom_edits: {bc.atom_map_a},{bc.atom_map_b}"
                )
        for st in self.atom_state_changes:
            if st.atom_map_number not in known:
                raise ValueError(
                    f"AtomStateChange references atom map {st.atom_map_number} "
                    f"outside mapped_atom_edits"
                )
        return self

    @model_validator(mode="after")
    def _removed_sinks_consistent(self) -> "StrictTransformation":
        # R3-C: sink assignments reference removed maps only, without
        # duplicates.  EXACT coverage is enforced on the production
        # extraction + candidate-validation paths (a hand-built transform
        # with a partial sink list is still structurally consistent).
        seen: set[int] = set()
        removed = set(self.removed_atom_maps)
        for sink in self.removed_atom_sinks:
            if sink.atom_map in seen:
                raise ValueError(
                    f"duplicate removed-sink assignment for atom map "
                    f"{sink.atom_map}"
                )
            if sink.atom_map not in removed:
                raise ValueError(
                    f"removed-sink assignment for atom map {sink.atom_map} "
                    f"that is not a removed atom map"
                )
            seen.add(sink.atom_map)
        return self


# -- ConditionedSite (CHATGPT_P3 prompt §6, final_design §13) ---------------


class ConditionedSite(StrictModel):
    site_id: NonEmptyStr
    run_id: NonEmptyStr
    case_id: NonEmptyStr
    fold_id: NonEmptyStr
    query_id: NonEmptyStr
    snapshot_id: str = ""
    snapshot_hash: str = ""
    transformation_id: NonEmptyStr
    query_atom_ids: list[int]
    query_bond_ids: list[int]
    atom_map_correspondence: dict[str, int]  # transform map number -> query atom idx
    matched_preconditions: list[NonEmptyStr]
    failed_preconditions: list[SitePrecondition]
    symmetry_class: NonEmptyStr
    ambiguity_group: int
    eligibility: SiteEligibility
    local_environment_similarity: float = 0.0

    @field_validator("local_environment_similarity")
    @classmethod
    def _similarity_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"similarity must be in [0, 1], got {v}")
        return v


# -- GenerationReport (final_design §14) ------------------------------------


class EditApplicationLog(StrictModel):
    step: NonEmptyStr
    detail: str = ""


class GenerationReport(StrictModel):
    generation_id: NonEmptyStr
    transformation_id: NonEmptyStr
    site_id: NonEmptyStr
    edit_application_log: list[EditApplicationLog] = []
    raw_product: str = ""
    canonical_product: str = ""
    changed_atoms: list[int] = []
    changed_bonds: list[int] = []
    sanitize_report: str = ""
    dedup_key: str = ""
    failure_code: str | None = None
    component_version: NonEmptyStr = "p3-1"


# -- StrictCandidate (CHATGPT_P3 prompt §6, final_design §14/§15) -----------


class CandidateValidation(StrictModel):
    valid_molecule: bool
    transform_fidelity: bool
    precondition_recheck: bool
    formal_source_accounting: bool
    candidate_ledger_valid: bool
    critical_contradiction: bool = False
    relaxation_used: bool = False
    critical_ambiguity: bool = False
    reason_codes: list[NonEmptyStr] = []
    failure_code: str | None = None


def validation_is_strict_clean(v: "CandidateValidation") -> bool:
    """The strict-lane rule set for ONE validation record (R3-E).

    Shared by the candidate-level and the per-path checks so a path can
    never smuggle a failing validation into the strict lane.
    """
    return (
        v.valid_molecule
        and v.transform_fidelity
        and v.precondition_recheck
        and v.formal_source_accounting
        and v.candidate_ledger_valid
        and not v.relaxation_used
        and not v.critical_ambiguity
        and not v.critical_contradiction
        and v.failure_code is None
    )


PATH_BINDING_VERSION = "p3-r3-1"


def candidate_path_preimage(
    *,
    donor_id: str,
    reaction_id: str,
    lineage_id: str,
    transformation_id: str,
    site_id: str,
    generation_report: "GenerationReport",
    source_ledger_id: str,
    candidate_analogy_ledger: "CandidateAnalogyLedger",
    run_id: str,
    case_id: str,
    query_id: str,
    fold_id: str,
    snapshot_id: str,
    snapshot_hash: str,
) -> dict:
    """Content-addressed evidence-path preimage (R3-E).

    Includes donor, reaction, lineage, transformation, site, generation,
    source ledger and candidate ledger — plus the FULL parent run namespace.
    Nested records are bound cryptographically to the parent namespace and
    can never be used independently of it.
    """
    return {
        "path_binding_version": PATH_BINDING_VERSION,
        "donor_id": donor_id,
        "reaction_id": reaction_id,
        "lineage_id": lineage_id,
        "transformation_id": transformation_id,
        "site_id": site_id,
        # R4-C: the FULL generation report content (edit_application_log,
        # raw_product, changed_atoms, changed_bonds, sanitize_report,
        # dedup_key, ...) — not an ID-only projection.
        "generation": generation_report.model_dump(mode="json"),
        "source_ledger_id": source_ledger_id,
        # R4-C: the FULL candidate analogy ledger content (adaptation,
        # inherited_context, inherited_assumptions, formal transfers,
        # balance, unknowns, evidence_ids, ...) — not an ID-only projection.
        "candidate_ledger": candidate_analogy_ledger.model_dump(mode="json"),
        "run_id": run_id,
        "case_id": case_id,
        "query_id": query_id,
        "fold_id": fold_id,
        "snapshot_id": snapshot_id,
        "snapshot_hash": snapshot_hash,
    }


def compute_candidate_path_binding(**kwargs) -> tuple[str, str]:
    """Return (path_id, path_hash) for the evidence-path preimage (R3-E)."""
    preimage = candidate_path_preimage(**kwargs)
    from reaction_agent.hashing import canonical_hash, stable_id
    return stable_id("path", preimage), canonical_hash(preimage)


class CandidateEvidencePath(StrictModel):
    """One donor/reaction/lineage/transform/site/generation/ledger evidence path.

    Candidate merge MUST preserve every path (R2-F): per-path candidate
    analogy ledger + validation + generation report are never dropped.

    R3-E: every linkage is enforced at construction time and the path is
    content-addressedly bound (``path_id`` / ``path_hash``) to its fields
    AND the parent run namespace; ``StrictCandidate`` recomputes the binding
    so a forged/tampered path can never validate.
    """
    donor_id: NonEmptyStr
    reaction_id: NonEmptyStr
    lineage_id: NonEmptyStr
    transformation_id: NonEmptyStr
    site_id: NonEmptyStr
    generation_report: GenerationReport
    source_ledger_id: NonEmptyStr
    candidate_analogy_ledger: CandidateAnalogyLedger
    validation: CandidateValidation
    path_id: NonEmptyStr
    path_hash: NonEmptyStr

    @model_validator(mode="after")
    def _linkage_consistent(self) -> "CandidateEvidencePath":
        if self.generation_report.transformation_id != self.transformation_id:
            raise ValueError(
                f"evidence path generation report references transform "
                f"{self.generation_report.transformation_id!r}, path declares "
                f"{self.transformation_id!r}"
            )
        if self.generation_report.site_id != self.site_id:
            raise ValueError(
                f"evidence path generation report references site "
                f"{self.generation_report.site_id!r}, path declares "
                f"{self.site_id!r}"
            )
        if self.generation_report.failure_code is not None:
            raise ValueError(
                "evidence path carries a FAILED generation report — it cannot "
                "enter the strict lane"
            )
        if self.candidate_analogy_ledger.source_ledger_id != self.source_ledger_id:
            raise ValueError(
                f"evidence path nested candidate ledger source "
                f"{self.candidate_analogy_ledger.source_ledger_id!r} != path "
                f"source ledger {self.source_ledger_id!r}"
            )
        if not validation_is_strict_clean(self.validation):
            raise ValueError(
                "evidence path validation does not satisfy the strict lane "
                f"(failure_code={self.validation.failure_code!r})"
            )
        return self


class StrictCandidate(StrictModel):
    candidate_id: NonEmptyStr
    run_id: NonEmptyStr
    case_id: NonEmptyStr
    query_id: NonEmptyStr
    fold_id: NonEmptyStr
    snapshot_id: str = ""
    snapshot_hash: str = ""
    canonical_product_identity: NonEmptyStr
    lane: Literal["strict"] = "strict"
    origin: Literal["deterministic_kernel"] = "deterministic_kernel"
    generation_paths: list[GenerationReport]
    support_lineage_ids: list[NonEmptyStr]
    transformation_ids: list[NonEmptyStr]
    site_ids: list[NonEmptyStr]
    validation: CandidateValidation
    source_ledger_ids: list[NonEmptyStr]
    candidate_analogy_ledger: CandidateAnalogyLedger
    candidate_evidence_paths: list[CandidateEvidencePath] = []
    provenance: list[NonEmptyStr]
    evidence_kind: EvidenceKind = EvidenceKind.synthetic_fixture

    @model_validator(mode="after")
    def _validation_pass_requires_candidate(self) -> "StrictCandidate":
        if not validation_is_strict_clean(self.validation):
            raise ValueError(
                "candidate with failing validation cannot enter the strict lane"
            )
        return self

    @model_validator(mode="after")
    def _evidence_paths_binding(self) -> "StrictCandidate":
        """R3-E: full evidence-path integrity.

        - the candidate-level analogy ledger belongs to THIS candidate;
        - a strict candidate has at least one evidence path;
        - every nested ledger belongs to THIS candidate;
        - every path binding recomputes under the parent namespace;
        - parent ID sets exactly equal the union of path IDs;
        - parent generation paths exactly correspond to path reports;
        - support lineages cover every path lineage.
        """
        if self.candidate_analogy_ledger.candidate_id != self.candidate_id:
            raise ValueError(
                f"candidate analogy ledger candidate_id "
                f"{self.candidate_analogy_ledger.candidate_id!r} != candidate "
                f"{self.candidate_id!r}"
            )
        if not self.candidate_evidence_paths:
            raise ValueError(
                "strict candidate requires at least one evidence path"
            )
        if not self.generation_paths:
            raise ValueError(
                "strict candidate requires at least one generation report"
            )
        # R4-C: the candidate-level analogy ledger must be byte-identical to
        # the ledger of AT LEAST ONE evidence path (identity + content).  A
        # forged candidate-level ledger (e.g. replacing source_ledger_id or
        # inherited_assumptions) can never smuggle different content that no
        # path carries.  Multiple paths may carry different ledgers (merge of
        # paths from different donors), so the candidate ledger must match
        # one of them — not necessarily all.
        candidate_ledger_dump = self.candidate_analogy_ledger.model_dump(mode="json")
        path_transformations: list[str] = []
        path_sites: list[str] = []
        path_ledgers: list[str] = []
        path_generations: list[str] = []
        path_lineages: set[str] = set()
        ledger_matches_a_path = False
        for path in self.candidate_evidence_paths:
            if path.candidate_analogy_ledger.candidate_id != self.candidate_id:
                raise ValueError(
                    f"evidence path nested ledger candidate_id "
                    f"{path.candidate_analogy_ledger.candidate_id!r} != "
                    f"candidate {self.candidate_id!r}"
                )
            if path.candidate_analogy_ledger.model_dump(mode="json") == candidate_ledger_dump:
                ledger_matches_a_path = True
            expected_id, expected_hash = compute_candidate_path_binding(
                donor_id=path.donor_id,
                reaction_id=path.reaction_id,
                lineage_id=path.lineage_id,
                transformation_id=path.transformation_id,
                site_id=path.site_id,
                generation_report=path.generation_report,
                source_ledger_id=path.source_ledger_id,
                candidate_analogy_ledger=path.candidate_analogy_ledger,
                run_id=self.run_id,
                case_id=self.case_id,
                query_id=self.query_id,
                fold_id=self.fold_id,
                snapshot_id=self.snapshot_id,
                snapshot_hash=self.snapshot_hash,
            )
            if path.path_hash != expected_hash:
                raise ValueError(
                    f"evidence path path_hash {path.path_hash[:12]}... != "
                    f"recomputed binding {expected_hash[:12]}... for path "
                    f"{path.path_id} (forged or namespace-smuggled path)"
                )
            if path.path_id != expected_id:
                raise ValueError(
                    f"evidence path path_id {path.path_id!r} != recomputed "
                    f"binding {expected_id!r}"
                )
            path_transformations.append(path.transformation_id)
            path_sites.append(path.site_id)
            path_ledgers.append(path.source_ledger_id)
            path_generations.append(path.generation_report.generation_id)
            path_lineages.add(path.lineage_id)
        if not ledger_matches_a_path:
            raise ValueError(
                "candidate-level analogy ledger does not match any evidence "
                "path ledger (forged candidate ledger)"
            )
        if set(self.transformation_ids) != set(path_transformations):
            raise ValueError(
                "candidate transformation_ids do not exactly equal the union "
                "of evidence path transformations"
            )
        if set(self.site_ids) != set(path_sites):
            raise ValueError(
                "candidate site_ids do not exactly equal the union of "
                "evidence path sites"
            )
        if set(self.source_ledger_ids) != set(path_ledgers):
            raise ValueError(
                "candidate source_ledger_ids do not exactly equal the union "
                "of evidence path source ledgers"
            )
        # R4-C: CONTENT-level correspondence, never ID-only.  Every parent
        # generation report must be byte-identical to the matching
        # evidence-path generation report (same generation_id but tampered
        # content is rejected).  Multiple evidence paths may reference the
        # SAME generation report (merge/dedup), so a duplicate parent
        # generation entry is legal only when its content is identical.
        path_generation_by_id = {
            p.generation_report.generation_id: p.generation_report
            for p in self.candidate_evidence_paths
        }
        for report in self.generation_paths:
            path_report = path_generation_by_id.get(report.generation_id)
            if path_report is None:
                raise ValueError(
                    f"candidate generation_paths entry {report.generation_id!r} "
                    "has no matching evidence-path generation report"
                )
            if path_report.model_dump(mode="json") != report.model_dump(mode="json"):
                raise ValueError(
                    f"candidate generation_paths entry {report.generation_id!r} "
                    "content differs from the evidence-path generation report"
                )
        # R4-C (reverse direction): every evidence-path generation report must
        # also be present in the parent generation_paths with identical
        # content.  A forged path whose generation content differs from the
        # candidate's declared generation paths fails even if all IDs match.
        parent_generation_by_id = {
            g.generation_id: g for g in self.generation_paths
        }
        for path in self.candidate_evidence_paths:
            parent = parent_generation_by_id.get(
                path.generation_report.generation_id
            )
            if parent is None or parent.model_dump(mode="json") != (
                path.generation_report.model_dump(mode="json")
            ):
                raise ValueError(
                    f"evidence path generation report "
                    f"{path.generation_report.generation_id!r} does not match "
                    "the candidate generation_paths content"
                )
        # R4-C: support lineage ids must EXACTLY equal the path lineage set
        # (no orphans, no missing, no duplicates).
        if len(self.support_lineage_ids) != len(set(self.support_lineage_ids)):
            raise ValueError(
                "candidate support_lineage_ids contain duplicates"
            )
        if set(self.support_lineage_ids) != path_lineages:
            raise ValueError(
                "candidate support_lineage_ids do not exactly equal the "
                "evidence path lineage ids"
            )
        return self


# -- CandidateTrace (CHATGPT_P3 prompt §6, final_discussion D/T/S/Δ/Y/L) ----


class StageTraceEntry(StrictModel):
    """One lifecycle stage entry.

    R3-D: failures are recorded through DECLARED, JSON-serializable typed
    diagnostics — ``failure_code`` + ``component`` + ``input_ref`` (the
    failing reaction ID) + ``detail`` (``str(exc)``, NEVER an Exception
    object).  An undeclared ``detail=exc`` keyword previously crashed the
    whole run with a Pydantic ValidationError.
    """
    stage: KernelStage
    input_ref: str = ""
    output_ref: str = ""
    evidence_ids: list[NonEmptyStr] = []
    content_hash: str = ""
    failure_code: str | None = None
    component: str = ""
    detail: str = ""
    metrics: dict[str, float] = {}


class CandidateTrace(StrictModel):
    run_id: NonEmptyStr
    query_id: NonEmptyStr
    case_id: NonEmptyStr
    fold_id: NonEmptyStr
    snapshot_id: str = ""
    snapshot_hash: str = ""
    stages: list[StageTraceEntry]
    donor_ids: list[NonEmptyStr] = []
    transformation_ids: list[NonEmptyStr] = []
    site_ids: list[NonEmptyStr] = []
    generation_ids: list[NonEmptyStr] = []
    candidate_ids: list[NonEmptyStr] = []
    source_ledger_ids: list[NonEmptyStr] = []
    evidence_kind: EvidenceKind = EvidenceKind.synthetic_fixture

    @model_validator(mode="after")
    def _stages_ordered(self) -> "CandidateTrace":
        # Lifecycle is a DAG walk; intermediate stages may repeat across
        # donors (HYPOTHESES_COMPILED -> SITES_ENUMERATED per donor), and a
        # run may terminate early (scientific stop).  Only the transition
        # legality is enforced.
        allowed: dict[str, set[str]] = {
            KernelStage.RECEIVED.value: {KernelStage.NORMALIZED.value},
            KernelStage.NORMALIZED.value: {KernelStage.BASELINE_EVIDENCE_LOADED.value},
            KernelStage.BASELINE_EVIDENCE_LOADED.value: {
                KernelStage.HYPOTHESES_COMPILED.value,
            },
            KernelStage.HYPOTHESES_COMPILED.value: {
                KernelStage.SITES_ENUMERATED.value,
                KernelStage.HYPOTHESES_COMPILED.value,
                # R3-D: a run whose last donor reaction failed hypotheses
                # compilation (isolated bad reaction) terminates directly at
                # CANDIDATES_VALIDATED with zero/fewer candidates — a legal
                # scientific/system stop, not a skipped stage.
                KernelStage.CANDIDATES_VALIDATED.value,
            },
            KernelStage.SITES_ENUMERATED.value: {
                KernelStage.CANDIDATES_VALIDATED.value,
                KernelStage.HYPOTHESES_COMPILED.value,
            },
            KernelStage.CANDIDATES_VALIDATED.value: set(),
        }
        values = [s.stage.value for s in self.stages]
        for prev, nxt in zip(values, values[1:]):
            if nxt not in allowed.get(prev, set()):
                raise ValueError(
                    f"trace stage transition {prev} -> {nxt} violates the "
                    f"lifecycle DAG"
                )
        if values and values[0] != KernelStage.RECEIVED.value:
            raise ValueError("trace must start at RECEIVED")
        return self


# -- KernelFailure / KernelResult -------------------------------------------


class KernelFailure(StrictModel):
    failure_code: NonEmptyStr
    category: Literal["system", "scientific"]
    reason: NonEmptyStr
    component: str = ""
    detail: str = ""


class KernelResult(StrictModel):
    run_id: NonEmptyStr
    status: KernelStatus
    query_id: NonEmptyStr
    case_id: NonEmptyStr
    fold_id: NonEmptyStr
    snapshot_id: str = ""
    snapshot_hash: str = ""
    manifest: KernelRunManifest
    normalized_query: NormalizedQuery
    capability_status: CapabilityStatus
    candidates: list[StrictCandidate]
    trace: CandidateTrace
    failures: list[KernelFailure]
    evidence_kind: EvidenceKind = EvidenceKind.synthetic_fixture

    @model_validator(mode="after")
    def _cross_field_invariants(self) -> "KernelResult":
        if self.status is KernelStatus.completed:
            # completed does NOT guarantee >=1 candidate (abstention is P4);
            # but completed must have zero failures (scientific stops are
            # recorded in the trace, not as KernelFailure).
            sys_failures = [f for f in self.failures if f.category == "system"]
            if sys_failures:
                raise ValueError(
                    "completed result cannot carry system failures"
                )
            if not self.trace.stages:
                raise ValueError("completed result requires a non-empty trace")
        if self.status is KernelStatus.failed:
            system = [f for f in self.failures if f.category == "system"]
            if not system:
                raise ValueError(
                    "failed result must carry at least one system failure"
                )
        if self.status is KernelStatus.blocked:
            blocked_failures = [f for f in self.failures if f.category == "system"]
            if not blocked_failures:
                raise ValueError(
                    "blocked result must carry at least one typed blocker"
                )
        return self
