"""ppv1-route-status-v1 五态路线状态与工程失败分离契约单元测试。

全合成夹具测试（零金标、零题面、零外部调用），并显式校验冻结判分器
SHA256 未被任何改动破坏。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pathway_v43.pollutant.route_status import (
    ROUTE_STATUS_SCHEMA_VERSION,
    DeliveryStatus,
    ExpertReviewRecord,
    RouteStatus,
    RouteStatusRecord,
    ScientificEvalLabel,
    ZeroReason,
    classify_route_status,
    summarize_route_statuses,
    validate_route_status_record,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

FROZEN_SCORER_SHA256 = {
    "scripts/eval/score_disclosure_v4cn.py": (
        "0ffb8b71330653f7b0373a67d028b14a84d4c5f13a83abd17db89a3c82a28f2f"
    ),
    "src/pathway_v43/pollutant/evaluation.py": (
        "ac38ea393bfb91e420e98730415cba334df2f9d3d9de4ecfde90914f45363f41"
    ),
    "src/pathway_v43/pollutant/s5b_scoring.py": (
        "5a677550ef54a3a1e16d5b5a1ce4dd8d2cdcb55dd56224e8a148f50511dc456d"
    ),
}


def test_frozen_scorers_sha256_unchanged() -> None:
    for rel_path, expected in FROZEN_SCORER_SHA256.items():
        actual = hashlib.sha256((REPO_ROOT / rel_path).read_bytes()).hexdigest()
        assert actual == expected, f"{rel_path} SHA256 mismatch: {actual} != {expected}"


def test_classify_in_gold_exact_by_bucket_and_rank() -> None:
    rec = classify_route_status(
        qid="SYNTH_CASE_01__S01__R01",
        case_id="SYNTH_CASE_01",
        hit_rank=1,
        match_bucket="matched_product_hit",
    )
    assert rec.route_status == RouteStatus.IN_GOLD_EXACT
    assert rec.scientific_eval_label == ScientificEvalLabel.HIT_EXACT
    assert rec.zero_reason == ZeroReason.NONE
    assert rec.delivery_status == DeliveryStatus.OK
    assert rec.primary_score_immutable is True

    rec_by_rank = classify_route_status(
        qid="SYNTH_CASE_01__S02__R02",
        case_id="SYNTH_CASE_01",
        hit_rank=3,
    )
    assert rec_by_rank.route_status == RouteStatus.IN_GOLD_EXACT
    assert rec_by_rank.hit_rank == 3


def test_classify_in_gold_partial() -> None:
    rec = classify_route_status(
        qid="SYNTH_CASE_02__S01__R01",
        case_id="SYNTH_CASE_02",
        hit_rank=None,
        match_bucket="product_hit_partial",
    )
    assert rec.route_status == RouteStatus.IN_GOLD_PARTIAL
    assert rec.scientific_eval_label == ScientificEvalLabel.HIT_PARTIAL
    assert rec.zero_reason == ZeroReason.NONE


def test_unreviewed_outside_gold_fails_closed_to_unresolved_ne() -> None:
    rec = classify_route_status(
        qid="SYNTH_CASE_03__S01__R01",
        case_id="SYNTH_CASE_03",
        hit_rank=None,
        match_bucket="unmatched_product_mismatch",
        expert_review=None,
    )
    assert rec.route_status == RouteStatus.UNRESOLVED
    assert rec.scientific_eval_label == ScientificEvalLabel.NE
    assert rec.zero_reason == ZeroReason.UNRESOLVED


def test_unconfirmed_expert_review_stays_unresolved_ne() -> None:
    draft_review = ExpertReviewRecord(
        reviewer_id="chemist_01",
        reviewer_role="senior_chemist",
        reviewed_at="2026-11-21",
        verdict=RouteStatus.OUTSIDE_GOLD_CONTRADICTED,
        evidence="pending double check",
        confirmed=False,
    )
    rec = classify_route_status(
        qid="SYNTH_CASE_04__S01__R01",
        case_id="SYNTH_CASE_04",
        match_bucket="unmatched_product_mismatch",
        expert_review=draft_review,
    )
    assert rec.route_status == RouteStatus.UNRESOLVED
    assert rec.scientific_eval_label == ScientificEvalLabel.NE
    assert rec.zero_reason == ZeroReason.UNRESOLVED


def test_confirmed_outside_gold_plausible_is_ne_not_zero() -> None:
    review = ExpertReviewRecord(
        reviewer_id="chemist_01",
        reviewer_role="senior_chemist",
        reviewed_at="2026-11-21",
        verdict=RouteStatus.OUTSIDE_GOLD_PLAUSIBLE,
        evidence="Alternative textbook hydroxylation pathway verified by senior chemist.",
        confirmed=True,
    )
    rec = classify_route_status(
        qid="SYNTH_CASE_05__S01__R01",
        case_id="SYNTH_CASE_05",
        match_bucket="unmatched_product_mismatch",
        expert_review=review,
    )
    assert rec.route_status == RouteStatus.OUTSIDE_GOLD_PLAUSIBLE
    assert rec.scientific_eval_label == ScientificEvalLabel.NE
    assert rec.zero_reason == ZeroReason.OUTSIDE_COVERAGE


def test_confirmed_outside_gold_contradicted_requires_evidence_and_is_zero() -> None:
    with pytest.raises(ValueError, match="evidence"):
        ExpertReviewRecord(
            reviewer_id="chemist_01",
            reviewer_role="senior_chemist",
            reviewed_at="2026-11-21",
            verdict=RouteStatus.OUTSIDE_GOLD_CONTRADICTED,
            evidence="   ",
            confirmed=True,
        )

    review = ExpertReviewRecord(
        reviewer_id="chemist_01",
        reviewer_role="senior_chemist",
        reviewed_at="2026-11-21",
        verdict=RouteStatus.OUTSIDE_GOLD_CONTRADICTED,
        evidence="Valence overflow on C-3 atom under aerobic monooxygenase mechanism.",
        confirmed=True,
    )
    rec = classify_route_status(
        qid="SYNTH_CASE_06__S01__R01",
        case_id="SYNTH_CASE_06",
        match_bucket="unmatched_product_mismatch",
        expert_review=review,
    )
    assert rec.route_status == RouteStatus.OUTSIDE_GOLD_CONTRADICTED
    assert rec.scientific_eval_label == ScientificEvalLabel.ZERO
    assert rec.zero_reason == ZeroReason.WRONG_CHEMISTRY


def test_disallowed_reviewer_role_rejected() -> None:
    with pytest.raises(ValueError, match="reviewer_role"):
        ExpertReviewRecord(
            reviewer_id="auto_bot",
            reviewer_role="llm_auto",
            reviewed_at="2026-11-21",
            verdict=RouteStatus.OUTSIDE_GOLD_PLAUSIBLE,
            evidence="auto generated",
            confirmed=True,
        )


def test_direct_construction_outside_gold_without_expert_review_rejected() -> None:
    with pytest.raises(ValueError, match="ExpertReviewRecord"):
        RouteStatusRecord(
            schema_version=ROUTE_STATUS_SCHEMA_VERSION,
            qid="SYNTH_CASE_07__S01__R01",
            case_id="SYNTH_CASE_07",
            caliber="ppv1-criteria-v6",
            hit_rank=None,
            delivery_status=DeliveryStatus.OK,
            route_status=RouteStatus.OUTSIDE_GOLD_PLAUSIBLE,
            scientific_eval_label=ScientificEvalLabel.NE,
            zero_reason=ZeroReason.OUTSIDE_COVERAGE,
            expert_review=None,
        )

    with pytest.raises(ValueError, match="ExpertReviewRecord"):
        RouteStatusRecord(
            schema_version=ROUTE_STATUS_SCHEMA_VERSION,
            qid="SYNTH_CASE_07__S02__R02",
            case_id="SYNTH_CASE_07",
            caliber="ppv1-criteria-v6",
            hit_rank=None,
            delivery_status=DeliveryStatus.OK,
            route_status=RouteStatus.OUTSIDE_GOLD_CONTRADICTED,
            scientific_eval_label=ScientificEvalLabel.ZERO,
            zero_reason=ZeroReason.WRONG_CHEMISTRY,
            expert_review=None,
        )


def test_outside_gold_plausible_forced_to_zero_rejected() -> None:
    review = ExpertReviewRecord(
        reviewer_id="expert_01",
        reviewer_role="domain_expert",
        reviewed_at="2026-11-21",
        verdict=RouteStatus.OUTSIDE_GOLD_PLAUSIBLE,
        evidence="Plausible isomerization",
        confirmed=True,
    )
    with pytest.raises(ValueError, match="严禁记 ZERO"):
        RouteStatusRecord(
            schema_version=ROUTE_STATUS_SCHEMA_VERSION,
            qid="SYNTH_CASE_08__S01__R01",
            case_id="SYNTH_CASE_08",
            caliber="ppv1-criteria-v6",
            hit_rank=None,
            delivery_status=DeliveryStatus.OK,
            route_status=RouteStatus.OUTSIDE_GOLD_PLAUSIBLE,
            scientific_eval_label=ScientificEvalLabel.ZERO,
            zero_reason=ZeroReason.OUTSIDE_COVERAGE,
            expert_review=review,
        )


@pytest.mark.parametrize(
    "failure_status",
    [
        DeliveryStatus.LENGTH_EMPTY,
        DeliveryStatus.INVALID_JSON,
        DeliveryStatus.RESULT_UNKNOWN,
        DeliveryStatus.RUN_ERROR,
        DeliveryStatus.NO_EVENT,
    ],
)
def test_engineering_failure_separated_to_delivery_axis_and_ne(
    failure_status: DeliveryStatus,
) -> None:
    rec = classify_route_status(
        qid="SYNTH_CASE_09__S01__R01",
        case_id="SYNTH_CASE_09",
        delivery_status=failure_status,
    )
    assert rec.delivery_status == failure_status
    assert rec.route_status == RouteStatus.UNRESOLVED
    assert rec.scientific_eval_label == ScientificEvalLabel.NE
    assert rec.zero_reason == ZeroReason.ENGINEERING_FAILURE

    with pytest.raises(ValueError, match="NE"):
        RouteStatusRecord(
            schema_version=ROUTE_STATUS_SCHEMA_VERSION,
            qid="SYNTH_CASE_09__S01__R01",
            case_id="SYNTH_CASE_09",
            caliber="ppv1-criteria-v6",
            hit_rank=None,
            delivery_status=failure_status,
            route_status=RouteStatus.UNRESOLVED,
            scientific_eval_label=ScientificEvalLabel.ZERO,
            zero_reason=ZeroReason.ENGINEERING_FAILURE,
        )


def test_unmatched_no_event_bucket_maps_to_no_event_delivery_status() -> None:
    rec = classify_route_status(
        qid="SYNTH_CASE_10__S01__R01",
        case_id="SYNTH_CASE_10",
        match_bucket="unmatched_no_event",
    )
    assert rec.delivery_status == DeliveryStatus.NO_EVENT
    assert rec.route_status == RouteStatus.UNRESOLVED
    assert rec.scientific_eval_label == ScientificEvalLabel.NE
    assert rec.zero_reason == ZeroReason.ENGINEERING_FAILURE


def test_primary_score_immutable_must_be_true() -> None:
    with pytest.raises(ValueError, match="primary_score_immutable"):
        RouteStatusRecord(
            schema_version=ROUTE_STATUS_SCHEMA_VERSION,
            qid="SYNTH_CASE_11__S01__R01",
            case_id="SYNTH_CASE_11",
            caliber="ppv1-criteria-v6",
            hit_rank=1,
            delivery_status=DeliveryStatus.OK,
            route_status=RouteStatus.IN_GOLD_EXACT,
            scientific_eval_label=ScientificEvalLabel.HIT_EXACT,
            zero_reason=ZeroReason.NONE,
            primary_score_immutable=False,
        )


def test_roundtrip_to_dict_and_from_dict() -> None:
    review = ExpertReviewRecord(
        reviewer_id="chemist_02",
        reviewer_role="senior_chemist",
        reviewed_at="2026-11-21",
        verdict=RouteStatus.OUTSIDE_GOLD_PLAUSIBLE,
        evidence="MetaCyc curated sibling pathway match.",
        confirmed=True,
    )
    original = classify_route_status(
        qid="SYNTH_CASE_12__S01__R01",
        case_id="SYNTH_CASE_12",
        match_bucket="unmatched_product_mismatch",
        expert_review=review,
        notes="plausible alternative",
    )
    payload = original.to_dict()
    rebuilt = RouteStatusRecord.from_dict(payload)
    validate_route_status_record(rebuilt)
    assert rebuilt == original


def test_summarize_route_statuses_dual_denominators() -> None:
    recs = [
        classify_route_status(
            qid="S1__01__R1", case_id="S1", hit_rank=1, match_bucket="matched_product_hit"
        ),
        classify_route_status(
            qid="S1__02__R2", case_id="S1", hit_rank=3, match_bucket="matched_product_hit"
        ),
        classify_route_status(
            qid="S2__01__R3", case_id="S2", match_bucket="unmatched_product_mismatch"
        ),
        classify_route_status(
            qid="S3__01__R4", case_id="S3", match_bucket="unmatched_no_event"
        ),
        classify_route_status(
            qid="S4__01__R5", case_id="S4", delivery_status=DeliveryStatus.INVALID_JSON
        ),
    ]
    summary = summarize_route_statuses(recs)
    assert summary["n_total"] == 5
    assert summary["n_delivery_ok"] == 3
    assert summary["n_api_or_format_failures"] == 1
    assert summary["n_no_event"] == 1
    assert summary["n_engineering_failures"] == 2
    assert summary["route_status_counts"] == {
        "IN_GOLD_EXACT": 2,
        "IN_GOLD_PARTIAL": 0,
        "OUTSIDE_GOLD_PLAUSIBLE": 0,
        "OUTSIDE_GOLD_CONTRADICTED": 0,
        "UNRESOLVED": 3,
    }
    assert summary["primary_hit_at_k"]["denominator"] == 5
    assert summary["primary_hit_at_k"]["hit@1"] == {"count": 1, "denominator": 5, "pct": 20.0}
    assert summary["primary_hit_at_k"]["hit@3"] == {"count": 2, "denominator": 5, "pct": 40.0}
    assert summary["sensitivity_excl_engineering_fail_hit_at_k"]["denominator"] == 4
    assert summary["sensitivity_excl_engineering_fail_hit_at_k"]["hit@1"] == {
        "count": 1,
        "denominator": 4,
        "pct": 25.0,
    }
    assert summary["sensitivity_excl_no_event_hit_at_k"]["denominator"] == 3
    assert summary["sensitivity_excl_no_event_hit_at_k"]["hit@1"] == {
        "count": 1,
        "denominator": 3,
        "pct": 33.33,
    }
