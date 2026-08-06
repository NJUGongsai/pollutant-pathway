"""P5 Schemas — Full Snapshot, Rebuilt Benchmark, Six-Layer Reporting.

All schemas use Pydantic v2 StrictModel (extra='forbid') inherited from
reaction_agent.schemas.common. JSON is authority; Markdown is rendered.

Key design decisions:
- Every artifact has an ``artifact_classification`` field that must be
  one of: real, synthetic_fixture, derived_diagnostic, protocol_only, blocked.
- Every metric carries N, denominator, CI or unavailable_reason.
- Splits carry frozen hash/ID and overlap audit.
- Baselines carry same-data/same-split/same-case-registry binding.
- Oracle outputs are diagnostic-only; never primary.
- Status strings cannot promote Gate PASS.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import Field, model_validator

from reaction_agent.schemas.common import StrictModel, NonEmptyStr


P5_SCHEMA_VERSION = "p5-1"

# =====================================================================
# Constants
# =====================================================================

SPLIT_FAMILY_NAMES = [
    "exact_x",
    "scaffold",
    "transformation_family",
    "source",
    "time",
    "ood_challenge",
]

BASELINE_NAMES = [
    "morgan",
    "legacy_template",
    "drfp_reference_similarity",
    "random_order",
    "nearest_donor",
    "strict_kernel",
]

LAYER_NAMES = [
    "data",
    "retrieval",
    "transform_site",
    "generation",
    "rank_abstention",
    "cost_runtime",
]

METRIC_UNAVAILABLE_REASONS = [
    "upstream_p2_blocked",
    "upstream_p3_missing",
    "upstream_p4_missing",
    "real_snapshot_missing",
    "truth_unavailable",
    "split_unavailable",
    "source_provenance_insufficient",
    "time_provenance_insufficient",
    "chemistry_backend_unavailable",
    "insufficient_data_for_ci",
    "not_applicable",
]

ARTIFACT_CLASSIFICATIONS = [
    "real",
    "synthetic_fixture",
    "derived_diagnostic",
    "protocol_only",
    "blocked",
]


class ArtifactClassification(str, Enum):
    real = "real"
    synthetic_fixture = "synthetic_fixture"
    derived_diagnostic = "derived_diagnostic"
    protocol_only = "protocol_only"
    blocked = "blocked"


class SplitFamilyName(str, Enum):
    exact_x = "exact_x"
    scaffold = "scaffold"
    transformation_family = "transformation_family"
    source = "source"
    time = "time"
    ood_challenge = "ood_challenge"


class BaselineName(str, Enum):
    morgan = "morgan"
    legacy_template = "legacy_template"
    drfp_reference_similarity = "drfp_reference_similarity"
    random_order = "random_order"
    nearest_donor = "nearest_donor"
    strict_kernel = "strict_kernel"


class LayerName(str, Enum):
    data = "data"
    retrieval = "retrieval"
    transform_site = "transform_site"
    generation = "generation"
    rank_abstention = "rank_abstention"
    cost_runtime = "cost_runtime"


class MetricUnavailableReason(str, Enum):
    upstream_p2_blocked = "upstream_p2_blocked"
    upstream_p3_missing = "upstream_p3_missing"
    upstream_p4_missing = "upstream_p4_missing"
    real_snapshot_missing = "real_snapshot_missing"
    truth_unavailable = "truth_unavailable"
    split_unavailable = "split_unavailable"
    source_provenance_insufficient = "source_provenance_insufficient"
    time_provenance_insufficient = "time_provenance_insufficient"
    chemistry_backend_unavailable = "chemistry_backend_unavailable"
    insufficient_data_for_ci = "insufficient_data_for_ci"
    not_applicable = "not_applicable"


# =====================================================================
# Filter accounting
# =====================================================================

class FilterAccountingEntry(StrictModel):
    """One filter step in the snapshot pipeline."""
    filter_name: NonEmptyStr
    filter_stage: NonEmptyStr  # e.g. "normalization", "mapping", "lineage", "eligibility"
    denominator_before: int = Field(ge=0)
    denominator_after: int = Field(ge=0)
    removed_count: int = Field(ge=0)
    reason: NonEmptyStr
    quarantine_reason: Optional[NonEmptyStr] = None

    @model_validator(mode="after")
    def _check_consistency(self):
        if self.removed_count != self.denominator_before - self.denominator_after:
            raise ValueError(
                f"Filter '{self.filter_name}': removed_count ({self.removed_count}) "
                f"!= denominator_before ({self.denominator_before}) - "
                f"denominator_after ({self.denominator_after})"
            )
        return self


# =====================================================================
# Full Snapshot Manifest (P5-T1)
# =====================================================================

class FullSnapshotManifest(StrictModel):
    """Versioned manifest/index of the full P1 snapshot.

    P5 reads P1 snapshot authority (read-only). This manifest records
    production, diagnostic, quarantine indices, source counts, filter
    accounting, and provenance.
    """
    schema_version: str = P5_SCHEMA_VERSION
    snapshot_id: NonEmptyStr
    snapshot_hash: NonEmptyStr
    artifact_classification: ArtifactClassification

    # Source counts
    source_counts: dict[str, int] = Field(default_factory=dict)

    # Pre/post normalization
    pre_normalization_count: int = Field(ge=0)
    post_normalization_count: int = Field(ge=0)

    # Index partition
    production_count: int = Field(ge=0)
    diagnostic_count: int = Field(ge=0)
    quarantine_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)

    # Quality
    duplicate_count: int = Field(ge=0)
    unresolved_count: int = Field(ge=0)

    # Filter accounting (no silent drop)
    filter_accounting: list[FilterAccountingEntry] = Field(default_factory=list)

    # Provenance
    p1_snapshot_id: NonEmptyStr
    p1_snapshot_hash: NonEmptyStr
    builder_version: NonEmptyStr

    # Index hashes (from P1)
    production_index_hash: Optional[NonEmptyStr] = None
    diagnostic_index_hash: Optional[NonEmptyStr] = None
    quarantine_index_hash: Optional[NonEmptyStr] = None

    @model_validator(mode="after")
    def _check_partition(self):
        total = self.production_count + self.diagnostic_count + self.quarantine_count + self.excluded_count
        if total != self.post_normalization_count:
            raise ValueError(
                f"Index partition: production({self.production_count}) + "
                f"diagnostic({self.diagnostic_count}) + "
                f"quarantine({self.quarantine_count}) + "
                f"excluded({self.excluded_count}) = {total} != "
                f"post_normalization_count({self.post_normalization_count})"
            )
        return self


# =====================================================================
# Production Index Manifest (P5-T1)
# =====================================================================

class ProductionIndexManifest(StrictModel):
    """Production index extracted from the full snapshot.

    Namespace isolation: production records are strictly separated from
    diagnostic and quarantine. Each record carries its eligibility decision
    and filter trail.
    """
    schema_version: str = P5_SCHEMA_VERSION
    snapshot_id: NonEmptyStr
    snapshot_hash: NonEmptyStr
    artifact_classification: ArtifactClassification

    production_record_count: int = Field(ge=0)
    production_record_ids: list[NonEmptyStr] = Field(default_factory=list)

    # Strict vs conditional subsets
    strict_count: int = Field(ge=0)
    conditional_count: int = Field(ge=0)

    # Namespace isolation proof
    diagnostic_ids: list[NonEmptyStr] = Field(default_factory=list)
    quarantine_ids: list[NonEmptyStr] = Field(default_factory=list)

    # Mapping/lineage/ledger quality distributions
    mapping_status_distribution: dict[str, int] = Field(default_factory=dict)
    lineage_quality_distribution: dict[str, int] = Field(default_factory=dict)
    ledger_balance_distribution: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_no_overlap(self):
        prod_set = set(self.production_record_ids)
        diag_set = set(self.diagnostic_ids)
        quar_set = set(self.quarantine_ids)
        overlap_pd = prod_set & diag_set
        overlap_pq = prod_set & quar_set
        if overlap_pd:
            raise ValueError(
                f"Production/diagnostic namespace overlap: {overlap_pd}"
            )
        if overlap_pq:
            raise ValueError(
                f"Production/quarantine namespace overlap: {overlap_pq}"
            )
        if self.strict_count + self.conditional_count != self.production_record_count:
            raise ValueError(
                f"strict_count({self.strict_count}) + "
                f"conditional_count({self.conditional_count}) != "
                f"production_record_count({self.production_record_count})"
            )
        return self


# =====================================================================
# Rebuilt Case Record (P5-T2)
# =====================================================================

class RebuiltCaseRecord(StrictModel):
    """A rebuilt benchmark case from verified P1 lineage / P2 truth / P3-P4 artifacts.

    Multi-answer truth is preserved (allowed Y set, not compressed).
    Incomplete/unaudited cases are retained and marked, not deleted.
    """
    schema_version: str = P5_SCHEMA_VERSION
    case_id: NonEmptyStr
    artifact_classification: ArtifactClassification

    # Query
    query_smiles: NonEmptyStr
    query_identity_hash: Optional[NonEmptyStr] = None

    # Allowed Y set (multi-answer, not compressed)
    allowed_product_set: list[NonEmptyStr] = Field(default_factory=list)

    # Source/reaction context
    source_reaction_ids: list[NonEmptyStr] = Field(default_factory=list)
    donor_molecule_ids: list[NonEmptyStr] = Field(default_factory=list)
    donor_availability: Optional[bool] = None

    # Transform/site truth
    transformation_ids: list[NonEmptyStr] = Field(default_factory=list)
    site_ids: list[NonEmptyStr] = Field(default_factory=list)

    # Ambiguity/incomplete truth
    has_ambiguity: bool = False
    incomplete_truth: bool = False
    incomplete_reason: Optional[NonEmptyStr] = None

    # Provenance
    provenance: dict[str, Any] = Field(default_factory=dict)

    # Fold eligibility
    fold_eligible: bool = False
    fold_id: Optional[NonEmptyStr] = None

    # Binding hashes
    snapshot_id: NonEmptyStr
    snapshot_hash: NonEmptyStr
    case_hash: Optional[NonEmptyStr] = None

    @model_validator(mode="after")
    def _check_incomplete(self):
        if self.incomplete_truth and not self.incomplete_reason:
            raise ValueError(
                f"Case {self.case_id}: incomplete_truth=True but "
                f"incomplete_reason is not set"
            )
        return self


# =====================================================================
# Split Domain Audit
# =====================================================================

class SplitDomainAudit(StrictModel):
    """Overlap and leakage audit for a single split domain."""
    domain_name: NonEmptyStr
    train_query_ids: list[NonEmptyStr] = Field(default_factory=list)
    val_query_ids: list[NonEmptyStr] = Field(default_factory=list)
    test_query_ids: list[NonEmptyStr] = Field(default_factory=list)
    train_reaction_ids: list[NonEmptyStr] = Field(default_factory=list)
    test_reaction_ids: list[NonEmptyStr] = Field(default_factory=list)
    train_evidence_ids: list[NonEmptyStr] = Field(default_factory=list)
    test_evidence_ids: list[NonEmptyStr] = Field(default_factory=list)
    train_source_ids: list[NonEmptyStr] = Field(default_factory=list)
    test_source_ids: list[NonEmptyStr] = Field(default_factory=list)

    # Overlap findings
    query_overlap: list[NonEmptyStr] = Field(default_factory=list)
    reaction_overlap: list[NonEmptyStr] = Field(default_factory=list)
    evidence_overlap: list[NonEmptyStr] = Field(default_factory=list)
    source_overlap: list[NonEmptyStr] = Field(default_factory=list)

    # Leakage
    leakage_count: int = Field(ge=0)
    leakage_details: list[NonEmptyStr] = Field(default_factory=list)

    # Audit status
    audit_complete: bool = False
    unavailable: bool = False
    unavailable_reason: Optional[MetricUnavailableReason] = None

    @model_validator(mode="after")
    def _check_leakage(self):
        if self.leakage_count > 0 and not self.leakage_details:
            raise ValueError(
                f"Domain {self.domain_name}: leakage_count={self.leakage_count} "
                f"but leakage_details is empty"
            )
        if self.unavailable and not self.unavailable_reason:
            raise ValueError(
                f"Domain {self.domain_name}: unavailable=True but "
                f"unavailable_reason is not set"
            )
        return self


# =====================================================================
# Split Family Manifest (P5-T3)
# =====================================================================

class SplitFamilyManifest(StrictModel):
    """One split family (exact-X, scaffold, etc.) with frozen fold/split ID/hash.

    Source/time provenance insufficient -> unavailable, not fabricated.
    Retrieval/support/counterevidence/ranking/calibration must not access test.
    """
    schema_version: str = P5_SCHEMA_VERSION
    split_family_name: SplitFamilyName
    split_id: NonEmptyStr
    split_hash: NonEmptyStr
    artifact_classification: ArtifactClassification

    snapshot_id: NonEmptyStr
    snapshot_hash: NonEmptyStr
    fold_id: NonEmptyStr

    # Train/val/test identity sets
    train_query_ids: list[NonEmptyStr] = Field(default_factory=list)
    val_query_ids: list[NonEmptyStr] = Field(default_factory=list)
    test_query_ids: list[NonEmptyStr] = Field(default_factory=list)

    # Capability views
    train_only_view_id: Optional[NonEmptyStr] = None
    val_calibration_view_id: Optional[NonEmptyStr] = None
    test_label_view_id: Optional[NonEmptyStr] = None

    # Overlap / leakage audit
    domain_audit: SplitDomainAudit

    # Cache identity
    cache_key: Optional[NonEmptyStr] = None

    # Availability
    unavailable: bool = False
    unavailable_reason: Optional[MetricUnavailableReason] = None

    @model_validator(mode="after")
    def _check_unavailable(self):
        if self.unavailable and not self.unavailable_reason:
            raise ValueError(
                f"Split {self.split_family_name}: unavailable=True but "
                f"unavailable_reason is not set"
            )
        return self


# =====================================================================
# Baseline Run Artifact (P5-T4)
# =====================================================================

class BaselineRunArtifact(StrictModel):
    """A single baseline run on a specific snapshot+split+case-registry.

    Same data, same split, same case registry, same train-only view.
    Oracle upper bound is diagnostic-only; unavailable cannot use fake output.
    """
    schema_version: str = P5_SCHEMA_VERSION
    baseline_id: NonEmptyStr
    baseline_name: BaselineName
    baseline_version: NonEmptyStr
    artifact_classification: ArtifactClassification

    # Binding
    snapshot_id: NonEmptyStr
    snapshot_hash: NonEmptyStr
    split_id: NonEmptyStr
    split_hash: NonEmptyStr
    fold_id: NonEmptyStr
    case_registry_id: NonEmptyStr

    # Config
    config_hash: NonEmptyStr
    seed: int = Field(ge=0)
    train_only_resource_id: NonEmptyStr

    # Output
    output_hash: Optional[NonEmptyStr] = None
    candidate_count: int = Field(ge=0)
    valid_candidate_count: int = Field(ge=0)

    # Availability
    available: bool = True
    unavailable_reason: Optional[MetricUnavailableReason] = None

    # Oracle flag
    is_oracle: bool = False
    namespace: str = "primary"  # "primary" or "diagnostic"

    @model_validator(mode="after")
    def _check_oracle(self):
        if self.is_oracle and self.namespace != "diagnostic":
            raise ValueError(
                f"Baseline {self.baseline_id}: is_oracle=True but "
                f"namespace='{self.namespace}' (must be 'diagnostic')"
            )
        if not self.available and not self.unavailable_reason:
            raise ValueError(
                f"Baseline {self.baseline_id}: available=False but "
                f"unavailable_reason is not set"
            )
        return self


# =====================================================================
# Layer Metric Report (P5-T5)
# =====================================================================

class LayerMetricReport(StrictModel):
    """One metric in a six-layer report.

    Every metric carries numerator, denominator, N, CI or unavailable reason,
    coverage, and failure/abstention reasons.
    """
    metric_name: NonEmptyStr
    layer: LayerName

    # Core values
    numerator: Optional[float] = None
    denominator: Optional[int] = None
    n: Optional[int] = None

    # CI
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    ci_method: Optional[NonEmptyStr] = None

    # Coverage
    coverage: Optional[float] = None

    # Unavailable
    unavailable: bool = False
    unavailable_reason: Optional[MetricUnavailableReason] = None

    # Failure/abstention reasons
    failure_reasons: list[NonEmptyStr] = Field(default_factory=list)
    abstention_reasons: list[NonEmptyStr] = Field(default_factory=list)
    system_failures: list[NonEmptyStr] = Field(default_factory=list)
    incomplete_truth_not_scored: int = Field(default=0, ge=0)

    # Evidence scope
    evidence_scope: NonEmptyStr = "train_only"

    # Artifact binding
    snapshot_id: NonEmptyStr
    split_id: NonEmptyStr
    run_id: Optional[NonEmptyStr] = None

    @model_validator(mode="after")
    def _check_metric(self):
        if self.unavailable:
            if not self.unavailable_reason:
                raise ValueError(
                    f"Metric {self.metric_name}: unavailable=True but "
                    f"unavailable_reason is not set"
                )
            if self.numerator is not None or self.denominator is not None:
                raise ValueError(
                    f"Metric {self.metric_name}: unavailable=True but "
                    f"numerator/denominator is set"
                )
        else:
            if self.numerator is None or self.denominator is None or self.n is None:
                raise ValueError(
                    f"Metric {self.metric_name}: available but missing "
                    f"numerator/denominator/N"
                )
            if self.denominator == 0:
                raise ValueError(
                    f"Metric {self.metric_name}: denominator is 0"
                )
        return self


class SixLayerReport(StrictModel):
    """Complete six-layer report for a split/baseline/run.

    Layers: data, retrieval, transform_site, generation, rank_abstention,
    cost_runtime.
    JSON is authority; Markdown is rendered from this.
    """
    schema_version: str = P5_SCHEMA_VERSION
    report_id: NonEmptyStr
    artifact_classification: ArtifactClassification

    snapshot_id: NonEmptyStr
    snapshot_hash: NonEmptyStr
    split_id: NonEmptyStr
    split_hash: NonEmptyStr
    fold_id: NonEmptyStr
    baseline_id: Optional[NonEmptyStr] = None
    run_id: Optional[NonEmptyStr] = None

    # Six layers
    metrics: list[LayerMetricReport] = Field(default_factory=list)

    # Hash for replay
    report_hash: Optional[NonEmptyStr] = None

    def get_layer_metrics(self, layer: LayerName) -> list[LayerMetricReport]:
        return [m for m in self.metrics if m.layer == layer]


# =====================================================================
# Formal KPI Registry (P5-T6)
# =====================================================================

class FormalKPIRegistry(StrictModel):
    """Formal KPI registry — only populated when real frozen data exists.

    No pre-claimed accuracy thresholds. KPIs are recorded only after
    real frozen data produces results.
    """
    schema_version: str = P5_SCHEMA_VERSION
    artifact_classification: ArtifactClassification

    snapshot_id: NonEmptyStr
    split_id: NonEmptyStr

    # KPI entries (each is a LayerMetricReport)
    kpi_entries: list[LayerMetricReport] = Field(default_factory=list)

    # Registration status
    registered: bool = False
    registration_reason: Optional[NonEmptyStr] = None

    @model_validator(mode="after")
    def _check_registration(self):
        if self.registered and not self.kpi_entries:
            raise ValueError(
                "FormalKPIRegistry: registered=True but kpi_entries is empty"
            )
        if not self.registered and self.kpi_entries:
            raise ValueError(
                "FormalKPIRegistry: registered=False but kpi_entries is not empty"
            )
        return self


# =====================================================================
# Go/No-Go Decision (P5-T6)
# =====================================================================

class GoNoGoDecision(StrictModel):
    """Go/No-Go decision based on data integrity, retrieval availability,
    failure funnel, deterministic slice viability, research/service value.

    Not a pre-claimed accuracy threshold.
    """
    schema_version: str = P5_SCHEMA_VERSION
    decision: str  # "go", "no_go", "blocked"
    artifact_classification: ArtifactClassification

    # Decision basis
    data_integrity_assessed: bool = False
    retrieval_availability_assessed: bool = False
    failure_funnel_assessed: bool = False
    deterministic_slice_viability_assessed: bool = False
    research_service_value_assessed: bool = False

    # Evidence
    decision_evidence: list[NonEmptyStr] = Field(default_factory=list)
    decision_reason: NonEmptyStr

    # Blockers
    blockers: list[NonEmptyStr] = Field(default_factory=list)

    snapshot_id: NonEmptyStr
    split_id: Optional[NonEmptyStr] = None

    @model_validator(mode="after")
    def _check_decision(self):
        if self.decision == "go":
            if not all([
                self.data_integrity_assessed,
                self.retrieval_availability_assessed,
                self.failure_funnel_assessed,
                self.deterministic_slice_viability_assessed,
                self.research_service_value_assessed,
            ]):
                raise ValueError(
                    "GoNoGoDecision: decision='go' but not all assessment "
                    "dimensions are assessed"
                )
            if self.blockers:
                raise ValueError(
                    "GoNoGoDecision: decision='go' but blockers is non-empty"
                )
        if self.decision == "blocked" and not self.blockers:
            raise ValueError(
                "GoNoGoDecision: decision='blocked' but blockers is empty"
            )
        return self


# =====================================================================
# P5 Run Manifest
# =====================================================================

class P5RunManifest(StrictModel):
    """Top-level P5 run manifest binding all artifacts."""
    schema_version: str = P5_SCHEMA_VERSION
    run_id: NonEmptyStr
    run_timestamp: NonEmptyStr
    artifact_classification: ArtifactClassification

    # P1 binding
    p1_snapshot_id: NonEmptyStr
    p1_snapshot_hash: NonEmptyStr

    # Upstream status
    p1_status: NonEmptyStr  # "PASS"
    p2_status: NonEmptyStr  # "BLOCKED"
    p3_status: NonEmptyStr  # "MISSING" or "BLOCKED"
    p4_status: NonEmptyStr  # "MISSING" or "BLOCKED"

    # Artifact references
    full_snapshot_manifest_path: Optional[NonEmptyStr] = None
    production_index_manifest_path: Optional[NonEmptyStr] = None
    rebuilt_case_manifest_path: Optional[NonEmptyStr] = None
    split_family_manifest_path: Optional[NonEmptyStr] = None
    baseline_run_manifest_path: Optional[NonEmptyStr] = None
    six_layer_report_path: Optional[NonEmptyStr] = None
    fixture_vs_real_evidence_manifest_path: Optional[NonEmptyStr] = None
    p5_p6_interface_manifest_path: Optional[NonEmptyStr] = None
    formal_kpi_registry_path: Optional[NonEmptyStr] = None
    go_no_go_decision_path: Optional[NonEmptyStr] = None

    # Gate
    gate_status: NonEmptyStr  # "PASS", "BLOCKED", "FAIL"

    # Hash for replay
    run_hash: Optional[NonEmptyStr] = None
