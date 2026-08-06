"""P5 real-data adapters — honest mapping of the real P1/P2/P3/P4 chain.

Every assertion verifies that the real artifacts are consumed faithfully:
- real snapshot counts match the on-disk manifest;
- rebuilt cases carry real query SMILES + P2 audited allowed-product sets;
- multi-answer truth is preserved (not compressed), incomplete retained;
- splits are disjoint (leakage zero) where available, honestly unavailable
  for source/time/transformation-family;
- baselines share one snapshot/split/case registry; strict kernel comes from
  the real P3 artifact; oracle stays diagnostic-only;
- six-layer metrics carry N/denominator or an explicit unavailable reason;
- KPI registers only when P3+P4 real data allow; Go/No-Go is traceable.

Nothing is fabricated: unavailable stays unavailable, never zero.
"""
from __future__ import annotations

import pytest

from reaction_agent.p5 import real_data as rd
from reaction_agent.p5.schemas import (
    ArtifactClassification,
    BaselineName,
    LayerName,
    MetricUnavailableReason,
    SplitFamilyName,
)


@pytest.fixture(scope="module")
def p1_data():
    return rd.load_real_p1_snapshot()


@pytest.fixture(scope="module")
def full(p1_data):
    return rd.build_real_full_snapshot_manifest(p1_data)


@pytest.fixture(scope="module")
def cases(p1_data, full):
    truth = rd._load_json(rd.P2_TRUTH_PATH)
    return rd.build_real_rebuilt_cases(p1_data, truth)


@pytest.fixture(scope="module")
def splits(full, cases):
    p2_split = rd._load_json(rd.P2_SPLIT_PATH)
    return rd.build_real_split_families(full, cases, p2_split)


@pytest.fixture(scope="module")
def p3_artifact():
    return rd._load_json(rd.P3_ARTIFACT_PATH)


@pytest.fixture(scope="module")
def p4_gate():
    return rd._load_json(f"{rd._DEMOV2_ROOT}/reports/p4/P4_GATE_REPORT.json")


# =====================================================================
# P1 — real snapshot authority
# =====================================================================

class TestRealSnapshot:
    def test_snapshot_id_and_count(self, p1_data):
        manifest = p1_data["fixture_snapshot"]["on_disk_manifest"]
        assert manifest["snapshot_id"] == "snap_19caddc6b312"
        assert len(p1_data["fixture_snapshot"]["items"]) == 50

    def test_full_manifest_partition(self, full):
        assert full.artifact_classification == ArtifactClassification.real
        assert full.pre_normalization_count == 50
        assert full.production_count == 7
        assert full.diagnostic_count == 43
        assert full.quarantine_count == 0

    def test_filter_accounting_no_silent_drop(self, full):
        for f in full.filter_accounting:
            assert f.removed_count == f.denominator_before - f.denominator_after


# =====================================================================
# P5-T2 — rebuilt cases (real truth, multi-answer preserved)
# =====================================================================

class TestRealCases:
    def test_50_real_cases(self, cases):
        assert len(cases) == 50
        assert all(c.artifact_classification == ArtifactClassification.real
                   for c in cases)

    def test_query_smiles_valid(self, cases):
        from rdkit import Chem
        for case in cases:
            assert Chem.MolFromSmiles(case.query_smiles) is not None, \
                f"invalid query SMILES for {case.case_id}"

    def test_multi_answer_preserved(self, cases):
        multi = [c for c in cases if len(c.allowed_product_set) > 1]
        assert len(multi) > 0, "multi-answer truth must not be compressed"
        for c in cases:
            assert len(c.allowed_product_set) >= 1

    def test_snapshot_binding(self, cases, full):
        for c in cases:
            assert c.snapshot_id == full.snapshot_id
            assert c.snapshot_hash == full.snapshot_hash

    def test_incomplete_truth_retained_with_reason(self, cases):
        for c in cases:
            if c.incomplete_truth:
                assert c.incomplete_reason is not None


# =====================================================================
# P5-T3 — split families (disjoint where available, honest unavailable)
# =====================================================================

class TestRealSplits:
    def test_exact_x_uses_p2_split(self, splits):
        exact = next(s for s in splits
                     if s.split_family_name == SplitFamilyName.exact_x)
        assert len(exact.train_query_ids) == 30
        assert len(exact.val_query_ids) == 10
        assert len(exact.test_query_ids) == 10
        assert exact.domain_audit.leakage_count == 0

    def test_scaffold_disjoint(self, splits):
        scaf = next(s for s in splits
                    if s.split_family_name == SplitFamilyName.scaffold)
        if not scaf.unavailable:
            assert scaf.domain_audit.leakage_count == 0
            assert len(scaf.domain_audit.train_query_ids) >= 1

    def test_source_time_unavailable(self, splits):
        for name in (SplitFamilyName.source, SplitFamilyName.time):
            s = next(x for x in splits if x.split_family_name == name)
            assert s.unavailable is True
            assert s.unavailable_reason is not None

    def test_transformation_family_honest_unavailable(self, splits):
        txf = next(s for s in splits
                   if s.split_family_name == SplitFamilyName.transformation_family)
        assert txf.unavailable is True
        assert txf.unavailable_reason == MetricUnavailableReason.split_unavailable


# =====================================================================
# P5-T4 — fair baselines (same registry; strict kernel from real P3)
# =====================================================================

class TestRealBaselines:
    def test_fair_same_registry(self, full, splits, p3_artifact):
        exact = next(s for s in splits
                     if s.split_family_name == SplitFamilyName.exact_x)
        baselines = rd.build_real_baselines(full, exact, p3_artifact)
        assert len({b.snapshot_id for b in baselines}) == 1
        assert len({b.split_id for b in baselines}) == 1
        assert len({b.case_registry_id for b in baselines}) == 1

    def test_strict_kernel_from_p3(self, full, splits, p3_artifact):
        exact = next(s for s in splits
                     if s.split_family_name == SplitFamilyName.exact_x)
        baselines = rd.build_real_baselines(full, exact, p3_artifact)
        sk = next(b for b in baselines
                  if b.baseline_name == BaselineName.strict_kernel)
        assert sk.available is True
        assert sk.candidate_count == 1
        assert sk.artifact_classification == ArtifactClassification.real

    def test_oracle_diagnostic_only(self, full, splits, p3_artifact):
        exact = next(s for s in splits
                     if s.split_family_name == SplitFamilyName.exact_x)
        baselines = rd.build_real_baselines(full, exact, p3_artifact)
        for b in baselines:
            if b.is_oracle:
                assert b.namespace == "diagnostic"


# =====================================================================
# P5-T5 — six-layer report (N or explicit unavailable)
# =====================================================================

class TestRealSixLayer:
    def test_metrics_have_n_or_unavailable(self, full, splits, p3_artifact, p4_gate):
        exact = next(s for s in splits
                     if s.split_family_name == SplitFamilyName.exact_x)
        baselines = rd.build_real_baselines(full, exact, p3_artifact)
        sk = next(b for b in baselines
                  if b.baseline_name == BaselineName.strict_kernel)
        report = rd.build_real_six_layer_report(full, exact, sk, p3_artifact, p4_gate)
        for m in report.metrics:
            if m.unavailable:
                assert m.unavailable_reason is not None
            else:
                assert m.n is not None
                assert m.denominator is not None

    def test_data_layer_real_counts(self, full, splits, p3_artifact, p4_gate):
        exact = next(s for s in splits
                     if s.split_family_name == SplitFamilyName.exact_x)
        baselines = rd.build_real_baselines(full, exact, p3_artifact)
        sk = next(b for b in baselines
                  if b.baseline_name == BaselineName.strict_kernel)
        report = rd.build_real_six_layer_report(full, exact, sk, p3_artifact, p4_gate)
        data_metrics = [m for m in report.metrics if m.layer == LayerName.data]
        assert all(m.denominator == 50 for m in data_metrics)

    def test_cost_runtime_not_fabricated(self, full, splits, p3_artifact, p4_gate):
        exact = next(s for s in splits
                     if s.split_family_name == SplitFamilyName.exact_x)
        baselines = rd.build_real_baselines(full, exact, p3_artifact)
        sk = next(b for b in baselines
                  if b.baseline_name == BaselineName.strict_kernel)
        report = rd.build_real_six_layer_report(full, exact, sk, p3_artifact, p4_gate)
        cost = [m for m in report.metrics if m.layer == LayerName.cost_runtime]
        for m in cost:
            assert m.unavailable is True or m.unavailable_reason is not None


# =====================================================================
# P5-T6 — KPI registry + Go/No-Go (only when data allows)
# =====================================================================

class TestRealKpiGoNoGo:
    def test_kpi_registered_with_real_data(self, full, splits, p3_artifact, p4_gate):
        exact = next(s for s in splits
                     if s.split_family_name == SplitFamilyName.exact_x)
        kpi = rd.build_real_kpi_registry(full, exact, p3_artifact, p4_gate)
        assert kpi.registered is True
        assert len(kpi.kpi_entries) >= 1

    def test_kpi_not_registered_without_p3(self, full, splits):
        exact = next(s for s in splits
                     if s.split_family_name == SplitFamilyName.exact_x)
        kpi = rd.build_real_kpi_registry(full, exact, p3_artifact=None, p4_gate=None)
        assert kpi.registered is False
        assert kpi.kpi_entries == []

    def test_go_no_go_traceable(self, full, splits, p3_artifact, p4_gate):
        exact = next(s for s in splits
                     if s.split_family_name == SplitFamilyName.exact_x)
        kpi = rd.build_real_kpi_registry(full, exact, p3_artifact, p4_gate)
        gng = rd.build_real_go_no_go(
            full, kpi, {"p2": True, "p3": True, "p4": True})
        assert gng.decision in ("go", "no_go", "blocked")
        assert gng.decision_evidence
        assert gng.data_integrity_assessed is True

    def test_go_no_go_blocked_without_upstream(self, full, splits, p3_artifact, p4_gate):
        exact = next(s for s in splits
                     if s.split_family_name == SplitFamilyName.exact_x)
        kpi = rd.build_real_kpi_registry(full, exact, p3_artifact, p4_gate)
        gng = rd.build_real_go_no_go(
            full, kpi, {"p2": False, "p3": False, "p4": False})
        assert gng.decision == "blocked"
        assert len(gng.blockers) >= 1


# =====================================================================
# Upstream status — dynamic, not hardcoded
# =====================================================================

class TestUpstreamStatus:
    def test_real_chain_ready(self):
        status = rd.load_upstream_status()
        assert status["p2"][1] is True
        assert status["p3"][1] is True
        assert status["p4"][1] is True