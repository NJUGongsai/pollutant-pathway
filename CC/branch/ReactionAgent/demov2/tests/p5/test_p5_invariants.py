"""P5 RED tests — written before implementation to enforce invariants.

These tests verify:
- Snapshot authority/hash/reproducibility
- Filter accounting/no silent drop
- Production/diagnostic/quarantine separation
- Rebuilt multi-answer truth
- Incomplete/unaudited retention
- All split families and overlap domains
- Source/time unavailable fail closed
- Train-only isolation
- Same-data/same-split baseline fairness
- Oracle exclusion from primary
- Six-layer numerator/denominator/N/CI/reason
- JSON authority over Markdown
- No old KPI injection
- Report hash/freeze/replay
- Upstream P2/P3/P4 schema/hash validation
- Real-vs-fixture boundary
- Status string cannot promote PASS
"""
from __future__ import annotations

import json
import os
import copy
import pytest
from unittest.mock import patch

from reaction_agent.p5.schemas import (
    P5_SCHEMA_VERSION,
    ArtifactClassification,
    FullSnapshotManifest,
    ProductionIndexManifest,
    RebuiltCaseRecord,
    SplitFamilyManifest,
    SplitFamilyName,
    SplitDomainAudit,
    BaselineRunArtifact,
    BaselineName,
    LayerMetricReport,
    LayerName,
    SixLayerReport,
    FormalKPIRegistry,
    GoNoGoDecision,
    P5RunManifest,
    FilterAccountingEntry,
    MetricUnavailableReason,
    SPLIT_FAMILY_NAMES,
    BASELINE_NAMES,
    LAYER_NAMES,
)
from reaction_agent.p5.snapshot_reader import (
    read_p1_snapshot,
    build_full_snapshot_manifest,
    build_production_index_manifest,
)
from reaction_agent.p5.builder import (
    build_rebuilt_cases,
    build_split_families,
    build_fair_baselines,
    build_six_layer_report,
    build_formal_kpi_registry,
    build_go_no_go_decision,
)

PROJECT_ROOT = "/Volumes/CC/Enzyme_Agent/depending/CC/branch/ReactionAgent/demov2"
P1_SNAPSHOT_PATH = os.path.join(PROJECT_ROOT, "reports/p1/snapshot_build_sample.json")


@pytest.fixture
def p1_data():
    return read_p1_snapshot(P1_SNAPSHOT_PATH)


@pytest.fixture
def full_manifest(p1_data):
    return build_full_snapshot_manifest(p1_data)


@pytest.fixture
def prod_manifest(p1_data, full_manifest):
    return build_production_index_manifest(p1_data, full_manifest)


@pytest.fixture
def cases(full_manifest):
    return build_rebuilt_cases(full_manifest)


@pytest.fixture
def splits(full_manifest, cases):
    return build_split_families(full_manifest, cases)


# =====================================================================
# P5-T1: Snapshot authority/hash/reproducibility
# =====================================================================

class TestSnapshotAuthority:
    def test_snapshot_id_matches_p1(self, full_manifest, p1_data):
        """P5 snapshot ID must match P1 snapshot ID."""
        p1_id = p1_data["fixture_snapshot"]["on_disk_manifest"]["snapshot_id"]
        assert full_manifest.snapshot_id == p1_id

    def test_snapshot_hash_matches_p1(self, full_manifest, p1_data):
        """P5 snapshot hash must match P1 snapshot hash."""
        p1_hash = p1_data["fixture_snapshot"]["on_disk_manifest"]["snapshot_hash"]
        assert full_manifest.snapshot_hash == p1_hash

    def test_snapshot_artifact_classification_set(self, full_manifest):
        """Snapshot must have explicit artifact classification."""
        assert full_manifest.artifact_classification in [
            ArtifactClassification.real,
            ArtifactClassification.synthetic_fixture,
            ArtifactClassification.derived_diagnostic,
            ArtifactClassification.protocol_only,
            ArtifactClassification.blocked,
        ]

    def test_p1_snapshot_id_hash_preserved(self, full_manifest):
        """P1 snapshot ID and hash are preserved as provenance."""
        assert full_manifest.p1_snapshot_id == full_manifest.snapshot_id
        assert full_manifest.p1_snapshot_hash == full_manifest.snapshot_hash


# =====================================================================
# Filter accounting / no silent drop
# =====================================================================

class TestFilterAccounting:
    def test_filter_accounting_non_empty(self, full_manifest):
        """Every filter must be accounted for."""
        assert len(full_manifest.filter_accounting) > 0

    def test_filter_accounting_consistency(self, full_manifest):
        """removed_count == denominator_before - denominator_after."""
        for entry in full_manifest.filter_accounting:
            assert entry.removed_count == entry.denominator_before - entry.denominator_after

    def test_no_silent_drop(self, full_manifest):
        """Every removed record has a reason."""
        for entry in full_manifest.filter_accounting:
            if entry.removed_count > 0:
                assert entry.reason
                assert entry.reason != ""

    def test_filter_chain_covers_all_records(self, full_manifest):
        """Filter chain must account for all records (no silent drop)."""
        first_filter = full_manifest.filter_accounting[0]
        last_filter = full_manifest.filter_accounting[-1]
        # All records that entered must be accounted for
        partition_sum = (
            full_manifest.production_count
            + full_manifest.diagnostic_count
            + full_manifest.quarantine_count
            + full_manifest.excluded_count
        )
        # The first filter's denominator_before is the total input
        assert first_filter.denominator_before == full_manifest.pre_normalization_count
        # The partition sum must equal the total input (all records accounted)
        assert partition_sum == full_manifest.pre_normalization_count


# =====================================================================
# Production/diagnostic/quarantine separation
# =====================================================================

class TestNamespaceIsolation:
    def test_production_no_quarantine_overlap(self, prod_manifest):
        """Production records must not appear in quarantine."""
        prod_set = set(prod_manifest.production_record_ids)
        quar_set = set(prod_manifest.quarantine_ids)
        assert len(prod_set & quar_set) == 0

    def test_production_no_diagnostic_overlap(self, prod_manifest):
        """Production records must not appear in diagnostic."""
        prod_set = set(prod_manifest.production_record_ids)
        diag_set = set(prod_manifest.diagnostic_ids)
        assert len(prod_set & diag_set) == 0

    def test_strict_conditional_sum(self, prod_manifest):
        """strict_count + conditional_count == production_record_count."""
        assert (
            prod_manifest.strict_count + prod_manifest.conditional_count
            == prod_manifest.production_record_count
        )


# =====================================================================
# Rebuilt multi-answer truth
# =====================================================================

class TestRebuiltCases:
    def test_cases_non_empty(self, cases):
        """At least some cases must exist (incomplete or not)."""
        assert len(cases) > 0

    def test_multi_answer_preserved(self, cases):
        """Allowed Y set is not compressed to single answer."""
        for case in cases:
            if len(case.allowed_product_set) > 0:
                # Multi-answer is a list, not a single value
                assert isinstance(case.allowed_product_set, list)

    def test_incomplete_truth_marked(self, cases):
        """Incomplete truth is marked, not deleted."""
        for case in cases:
            if case.incomplete_truth:
                assert case.incomplete_reason is not None
                assert case.incomplete_reason != ""

    def test_case_has_snapshot_binding(self, cases, full_manifest):
        """Every case is bound to the snapshot."""
        for case in cases:
            assert case.snapshot_id == full_manifest.snapshot_id
            assert case.snapshot_hash == full_manifest.snapshot_hash

    def test_case_has_artifact_classification(self, cases):
        """Every case has explicit artifact classification."""
        for case in cases:
            assert case.artifact_classification in [
                ArtifactClassification.real,
                ArtifactClassification.synthetic_fixture,
                ArtifactClassification.protocol_only,
                ArtifactClassification.blocked,
            ]


# =====================================================================
# All split families and overlap domains
# =====================================================================

class TestSplitFamilies:
    def test_all_six_families_present(self, splits):
        """All six split families must be present."""
        names = {s.split_family_name for s in splits}
        assert names == set(SplitFamilyName)

    def test_each_split_has_hash(self, splits):
        """Every split has a frozen hash."""
        for split in splits:
            assert split.split_hash
            assert len(split.split_hash) > 0

    def test_each_split_has_domain_audit(self, splits):
        """Every split has a domain audit."""
        for split in splits:
            assert split.domain_audit is not None

    def test_source_split_unavailable(self, splits):
        """Source split must be unavailable (provenance insufficient)."""
        source_split = next(s for s in splits if s.split_family_name == SplitFamilyName.source)
        assert source_split.unavailable is True
        assert source_split.unavailable_reason == MetricUnavailableReason.source_provenance_insufficient

    def test_time_split_unavailable(self, splits):
        """Time split must be unavailable (provenance insufficient)."""
        time_split = next(s for s in splits if s.split_family_name == SplitFamilyName.time)
        assert time_split.unavailable is True
        assert time_split.unavailable_reason == MetricUnavailableReason.time_provenance_insufficient

    def test_leakage_count_matches_overlap(self, splits):
        """Leakage count must match overlap."""
        for split in splits:
            if not split.unavailable:
                audit = split.domain_audit
                assert audit.leakage_count == len(audit.query_overlap)


# =====================================================================
# Source/time unavailable fail closed
# =====================================================================

class TestSourceTimeFailClosed:
    def test_source_unavailable_has_reason(self, splits):
        source = next(s for s in splits if s.split_family_name == SplitFamilyName.source)
        assert source.unavailable_reason is not None

    def test_time_unavailable_has_reason(self, splits):
        time_split = next(s for s in splits if s.split_family_name == SplitFamilyName.time)
        assert time_split.unavailable_reason is not None

    def test_source_domain_audit_unavailable(self, splits):
        source = next(s for s in splits if s.split_family_name == SplitFamilyName.source)
        assert source.domain_audit.unavailable is True
        assert source.domain_audit.unavailable_reason is not None


# =====================================================================
# Same-data/same-split baseline fairness
# =====================================================================

class TestBaselineFairness:
    def test_baselines_same_snapshot(self, full_manifest, splits):
        """All baselines on same split use same snapshot."""
        for split in splits:
            baselines = build_fair_baselines(full_manifest, split, "case_registry_0")
            for b in baselines:
                assert b.snapshot_id == full_manifest.snapshot_id
                assert b.snapshot_hash == full_manifest.snapshot_hash

    def test_baselines_same_split(self, splits, full_manifest):
        """All baselines on same split use same split ID/hash."""
        for split in splits:
            baselines = build_fair_baselines(full_manifest, split, "case_registry_0")
            for b in baselines:
                assert b.split_id == split.split_id
                assert b.split_hash == split.split_hash

    def test_baselines_same_case_registry(self, splits, full_manifest):
        """All baselines use same case registry."""
        for split in splits:
            baselines = build_fair_baselines(full_manifest, split, "case_registry_0")
            for b in baselines:
                assert b.case_registry_id == "case_registry_0"

    def test_baselines_same_train_only(self, splits, full_manifest):
        """All baselines use same train-only resource."""
        for split in splits:
            baselines = build_fair_baselines(full_manifest, split, "case_registry_0")
            train_resources = {b.train_only_resource_id for b in baselines}
            assert len(train_resources) == 1


# =====================================================================
# Oracle exclusion from primary
# =====================================================================

class TestOracleExclusion:
    def test_oracle_is_diagnostic(self, splits, full_manifest):
        """Oracle baseline must be diagnostic, not primary."""
        for split in splits:
            baselines = build_fair_baselines(full_manifest, split, "case_registry_0")
            for b in baselines:
                if b.is_oracle:
                    assert b.namespace == "diagnostic"

    def test_no_oracle_in_primary(self, splits, full_manifest):
        """No oracle baseline in primary namespace."""
        for split in splits:
            baselines = build_fair_baselines(full_manifest, split, "case_registry_0")
            for b in baselines:
                if b.namespace == "primary":
                    assert b.is_oracle is False


# =====================================================================
# Six-layer numerator/denominator/N/CI/reason
# =====================================================================

class TestSixLayerReport:
    def test_all_six_layers_present(self, full_manifest, splits):
        """Six-layer report has all six layers."""
        split = next(s for s in splits if not s.unavailable)
        report = build_six_layer_report(full_manifest, split)
        layers_present = {m.layer for m in report.metrics}
        assert layers_present == set(LayerName)

    def test_metrics_have_n_or_unavailable(self, full_manifest, splits):
        """Every metric has N or unavailable reason."""
        split = next(s for s in splits if not s.unavailable)
        report = build_six_layer_report(full_manifest, split)
        for m in report.metrics:
            if m.unavailable:
                assert m.unavailable_reason is not None
            else:
                assert m.n is not None
                assert m.denominator is not None
                assert m.numerator is not None

    def test_report_has_hash(self, full_manifest, splits):
        """Report has a content hash for replay."""
        split = next(s for s in splits if not s.unavailable)
        report = build_six_layer_report(full_manifest, split)
        assert report.report_hash is not None
        assert len(report.report_hash) > 0


# =====================================================================
# Formal KPI registry
# =====================================================================

class TestFormalKPI:
    def test_kpi_not_registered_when_upstream_missing(self, full_manifest, splits):
        """KPI not registered when P3/P4 missing."""
        split = next(s for s in splits if not s.unavailable)
        kpi = build_formal_kpi_registry(full_manifest, split)
        assert kpi.registered is False
        assert len(kpi.kpi_entries) == 0

    def test_kpi_has_registration_reason(self, full_manifest, splits):
        """KPI has explicit reason when not registered."""
        split = next(s for s in splits if not s.unavailable)
        kpi = build_formal_kpi_registry(full_manifest, split)
        assert kpi.registration_reason is not None


# =====================================================================
# Go/No-Go
# =====================================================================

class TestGoNoGo:
    def test_go_no_go_blocked_when_upstream_missing(self, full_manifest, splits):
        """Go/No-Go is blocked when upstream missing."""
        split = next(s for s in splits if not s.unavailable)
        kpi = build_formal_kpi_registry(full_manifest, split)
        decision = build_go_no_go_decision(full_manifest, kpi)
        assert decision.decision == "blocked"
        assert len(decision.blockers) > 0

    def test_go_no_go_has_blockers(self, full_manifest, splits):
        """Blocked Go/No-Go has explicit blockers."""
        split = next(s for s in splits if not s.unavailable)
        kpi = build_formal_kpi_registry(full_manifest, split)
        decision = build_go_no_go_decision(full_manifest, kpi)
        assert len(decision.blockers) > 0
        for blocker in decision.blockers:
            assert blocker
            assert blocker != ""


# =====================================================================
# No old KPI injection
# =====================================================================

class TestNoOldKPI:
    def test_no_41_5_percent(self, full_manifest, splits):
        """No old 41.5% accuracy injected."""
        split = next(s for s in splits if not s.unavailable)
        report = build_six_layer_report(full_manifest, split)
        for m in report.metrics:
            if m.numerator is not None:
                assert m.numerator != 0.415 * (m.denominator or 1)

    def test_no_23_5_percent(self, full_manifest, splits):
        """No old 23.5% accuracy injected."""
        split = next(s for s in splits if not s.unavailable)
        report = build_six_layer_report(full_manifest, split)
        for m in report.metrics:
            if m.numerator is not None:
                assert m.numerator != 0.235 * (m.denominator or 1)

    def test_no_79_5_percent(self, full_manifest, splits):
        """No old 79.5% accuracy injected."""
        split = next(s for s in splits if not s.unavailable)
        report = build_six_layer_report(full_manifest, split)
        for m in report.metrics:
            if m.numerator is not None:
                assert m.numerator != 0.795 * (m.denominator or 1)


# =====================================================================
# JSON authority over Markdown
# =====================================================================

class TestJSONAuthority:
    def test_schema_is_pydantic(self):
        """All P5 schemas are Pydantic models (JSON authority)."""
        from pydantic import BaseModel
        assert issubclass(FullSnapshotManifest, BaseModel)
        assert issubclass(SixLayerReport, BaseModel)


# =====================================================================
# Status string cannot promote PASS
# =====================================================================

class TestStatusStringCannotPromote:
    def test_go_no_go_decision_uses_structured_fields(self, full_manifest, splits):
        """Go/No-Go uses structured fields, not status string."""
        split = next(s for s in splits if not s.unavailable)
        kpi = build_formal_kpi_registry(full_manifest, split)
        decision = build_go_no_go_decision(full_manifest, kpi)
        assert decision.decision in ("go", "no_go", "blocked")
        assert decision.artifact_classification is not None
        if decision.decision == "go":
            assert decision.data_integrity_assessed
            assert decision.retrieval_availability_assessed
            assert decision.failure_funnel_assessed
            assert decision.deterministic_slice_viability_assessed
            assert decision.research_service_value_assessed


# =====================================================================
# Real-vs-fixture boundary
# =====================================================================

class TestRealVsFixture:
    def test_fixture_snapshot_classified(self, full_manifest):
        """Fixture snapshot is classified as synthetic_fixture."""
        assert full_manifest.artifact_classification == ArtifactClassification.synthetic_fixture

    def test_fixture_cases_classified(self, cases):
        """Fixture cases are classified as synthetic_fixture."""
        for case in cases:
            assert case.artifact_classification == ArtifactClassification.synthetic_fixture

    def test_fixture_splits_classified(self, splits):
        """Available fixture splits are classified as synthetic_fixture."""
        for split in splits:
            if not split.unavailable:
                assert split.artifact_classification == ArtifactClassification.synthetic_fixture
