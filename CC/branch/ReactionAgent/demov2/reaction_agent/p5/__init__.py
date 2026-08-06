"""P5 — Full Snapshot, Rebuilt Benchmark, Six-Layer Reporting.

This module implements P5 schemas, artifact readers, snapshot/index
reporting, rebuilt cases, split families, fair baselines, six-layer
reports, formal KPI registry, Go/No-Go decision, and P5 Gate.

P5 consumes P1 snapshot/hash, mapping, lineage, ledgers, eligibility.
P2 truth/fold/views, P3 frozen candidate/trace, P4 frozen evidence/ranking
are required for full Gate PASS. When upstream artifacts are missing or
BLOCKED, P5 outputs machinery-complete + Gate BLOCKED.

All JSON reports are authority. Markdown is rendered from JSON only.
"""

from reaction_agent.p5.schemas import (
    # Core schemas
    ArtifactClassification,
    FullSnapshotManifest,
    ProductionIndexManifest,
    RebuiltCaseRecord,
    SplitFamilyManifest,
    BaselineRunArtifact,
    LayerMetricReport,
    MetricUnavailableReason,
    FormalKPIRegistry,
    GoNoGoDecision,
    P5RunManifest,
    FilterAccountingEntry,
    SplitDomainAudit,
    SixLayerReport,
    # Constants
    P5_SCHEMA_VERSION,
    SPLIT_FAMILY_NAMES,
    BASELINE_NAMES,
    LAYER_NAMES,
    METRIC_UNAVAILABLE_REASONS,
    ARTIFACT_CLASSIFICATIONS,
)

__all__ = [
    "ArtifactClassification",
    "FullSnapshotManifest",
    "ProductionIndexManifest",
    "RebuiltCaseRecord",
    "SplitFamilyManifest",
    "BaselineRunArtifact",
    "LayerMetricReport",
    "MetricUnavailableReason",
    "FormalKPIRegistry",
    "GoNoGoDecision",
    "P5RunManifest",
    "FilterAccountingEntry",
    "SplitDomainAudit",
    "SixLayerReport",
    "P5_SCHEMA_VERSION",
    "SPLIT_FAMILY_NAMES",
    "BASELINE_NAMES",
    "LAYER_NAMES",
    "METRIC_UNAVAILABLE_REASONS",
    "ARTIFACT_CLASSIFICATIONS",
]
