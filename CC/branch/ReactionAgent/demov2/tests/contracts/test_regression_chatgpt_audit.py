"""Regression tests for ChatGPT audit findings.

Tests 18 specific illegal objects that the previous implementation
incorrectly accepted. Each test MUST call real product schemas.
"""

import pytest
from pydantic import ValidationError
from reaction_agent.schemas import (
    MappingReport,
    MappingStatus,
    MappingQualityClass,
    SourceAssignmentMethod,
    FormalSourceAssignment,
    MechanisticAtomOrigin,
    ProductionSelectionHypothesis,
    AgentProposedHypothesis,
    HypothesisReferenceRegistry,
    UnknownReferenceError,
    validate_hypothesis_references,
    AtomTarget,
    BondTarget,
    PredictionResult,
    ResultStatus,
    DecisionKind,
    Candidate,
    Lane,
    ApplicabilityLabel,
    ScientificAbstentionReason,
    SystemFailureReason,
    SourceReactionLedger,
    CandidateAnalogyLedger,
    LedgerBalanceStatus,
    LineageHypothesis,
    LineageResolutionQuality,
    FORBIDDEN_FIELD_NAMES,
)
from reaction_agent.schemas.result import Abstention, Failure


# ============================================================
# 1. unknown_reference_ids
# ============================================================

@pytest.mark.contract
def test_unknown_support_reaction_id_rejected():
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn_known"}),
        lineage_ids=frozenset({"lin_known"}),
        transformation_ids=frozenset({"t_known"}),
        site_ids=frozenset({"s_known"}),
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn_nonexistent"],
        transformation_id="t_known",
        site_id="s_known",
    )
    with pytest.raises(UnknownReferenceError, match="unknown support_reaction_id"):
        validate_hypothesis_references(h, registry)


@pytest.mark.contract
def test_unknown_support_lineage_id_rejected():
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        lineage_ids=frozenset(),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset({"s1"}),
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        support_lineage_ids=["lin_nonexistent"],
        transformation_id="t1",
        site_id="s1",
    )
    with pytest.raises(UnknownReferenceError, match="unknown support_lineage_id"):
        validate_hypothesis_references(h, registry)


@pytest.mark.contract
def test_unknown_transformation_id_rejected():
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        lineage_ids=frozenset(),
        transformation_ids=frozenset(),
        site_ids=frozenset({"s1"}),
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        transformation_id="t_nonexistent",
        site_id="s1",
    )
    with pytest.raises(UnknownReferenceError, match="unknown transformation_id"):
        validate_hypothesis_references(h, registry)


@pytest.mark.contract
def test_unknown_site_id_rejected():
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        lineage_ids=frozenset(),
        transformation_ids=frozenset({"t1"}),
        site_ids=frozenset(),
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1",
        support_reaction_ids=["rxn1"],
        transformation_id="t1",
        site_id="s_nonexistent",
    )
    with pytest.raises(UnknownReferenceError, match="unknown site_id"):
        validate_hypothesis_references(h, registry)


# ============================================================
# 2. free_text_relaxation
# ============================================================

@pytest.mark.contract
def test_free_text_relaxation_policy_id_rejected():
    registry = HypothesisReferenceRegistry(
        transformation_family_ids=frozenset({"oxidation"}),
        relaxation_policy_ids=frozenset(),  # empty — nothing registered
        relaxation_ids=frozenset(),
    )
    h = AgentProposedHypothesis(
        hypothesis_id="h1",
        transformation_family_id="oxidation",
        typed_target_atom_or_bond_set=[AtomTarget(kind="atom", atom_id=0)],
        relaxation_policy_id="relax anything the LLM wants",
    )
    with pytest.raises(UnknownReferenceError, match="unknown relaxation_policy_id"):
        validate_hypothesis_references(h, registry)


@pytest.mark.contract
def test_free_text_allowed_relaxation_ids_rejected():
    registry = HypothesisReferenceRegistry(
        transformation_family_ids=frozenset({"oxidation"}),
        relaxation_policy_ids=frozenset(),
        relaxation_ids=frozenset(),
    )
    h = AgentProposedHypothesis(
        hypothesis_id="h1",
        transformation_family_id="oxidation",
        typed_target_atom_or_bond_set=[AtomTarget(kind="atom", atom_id=0)],
        allowed_relaxation_ids=["free text arbitrary rule"],
    )
    with pytest.raises(UnknownReferenceError, match="unknown allowed_relaxation_id"):
        validate_hypothesis_references(h, registry)


# ============================================================
# 3. numeric_string_target
# ============================================================

@pytest.mark.contract
def test_numeric_string_atom_target_rejected():
    """String '7' must not be silently converted to int 7."""
    with pytest.raises(ValidationError):
        AtomTarget(kind="atom", atom_id="7")


@pytest.mark.contract
def test_numeric_string_bond_target_rejected():
    with pytest.raises(ValidationError):
        BondTarget(kind="bond", begin_atom_id="3", end_atom_id="5")


# ============================================================
# 4. status_decision_mismatch
# ============================================================

@pytest.mark.contract
def test_completed_with_abstained_decision_rejected():
    c = Candidate(
        candidate_id="c1", canonical_product="CCCC=O",
        lane=Lane.strict, origin="agent_selected_from_evidence_space",
    )
    with pytest.raises(ValidationError, match="requires decision=predicted"):
        PredictionResult(
            run_id="r1", status=ResultStatus.completed,
            decision=DecisionKind.abstained,
            normalized_query="CCCCO", snapshot_id="snap1",
            candidates=[c],
        )


# ============================================================
# 5. completed_with_failure
# ============================================================

@pytest.mark.contract
def test_completed_with_failure_rejected():
    c = Candidate(
        candidate_id="c1", canonical_product="CCCC=O",
        lane=Lane.strict, origin="agent_selected_from_evidence_space",
    )
    with pytest.raises(ValidationError, match="must not have failure"):
        PredictionResult(
            run_id="r1", status=ResultStatus.completed,
            decision=DecisionKind.predicted,
            normalized_query="CCCCO", snapshot_id="snap1",
            candidates=[c],
            failure=Failure(reason_code=SystemFailureReason.STORAGE_FAILURE),
        )


# ============================================================
# 6. failed_with_scientific_abstention
# ============================================================

@pytest.mark.contract
def test_failed_with_scientific_abstention_rejected():
    with pytest.raises(ValidationError, match="must not have scientific abstention"):
        PredictionResult(
            run_id="r1", status=ResultStatus.failed,
            decision=DecisionKind.failed,
            normalized_query="CCCCO", snapshot_id="snap1",
            failure=Failure(reason_code=SystemFailureReason.STORAGE_FAILURE),
            abstention=Abstention(reason_code=ScientificAbstentionReason.NO_IN_DOMAIN_DONOR),
        )


# ============================================================
# 7. lineage_qualitative_confidence
# ============================================================

@pytest.mark.contract
def test_lineage_has_no_confidence_field():
    """LineageHypothesis must not have a 'confidence' field."""
    schema = LineageHypothesis.model_json_schema()
    props = schema.get("properties", {})
    assert "confidence" not in props, "LineageHypothesis still has 'confidence' field"


@pytest.mark.contract
def test_all_schemas_no_forbidden_confidence_fields():
    """Scan ALL exported schemas for forbidden field names."""
    from reaction_agent.schemas import (
        MappingReport, ReactionEvidence, LineageResolution,
        SourceReactionLedger, CandidateAnalogyLedger,
        TransformationHypothesis, SiteHypothesis,
        ProductionSelectionHypothesis, AgentProposedHypothesis,
        Candidate, PredictionResult,
    )
    all_schemas = [
        MappingReport, ReactionEvidence, LineageResolution,
        SourceReactionLedger, CandidateAnalogyLedger,
        TransformationHypothesis, SiteHypothesis,
        ProductionSelectionHypothesis, AgentProposedHypothesis,
        Candidate, PredictionResult, LineageHypothesis,
    ]
    for schema_cls in all_schemas:
        js = schema_cls.model_json_schema()
        props = js.get("properties", {})
        for forbidden in FORBIDDEN_FIELD_NAMES:
            assert forbidden not in props, (
                f"{schema_cls.__name__} has forbidden field '{forbidden}'"
            )


# ============================================================
# 8. float_string_coercion
# ============================================================

@pytest.mark.contract
def test_float_string_coercion_rejected():
    """String '1.0' must not silently convert to float 1.0."""
    with pytest.raises(ValidationError):
        MappingReport(
            mapper_name="test", mapper_version="1.0",
            input_hash="abc", output_hash="def",
            mapping_status=MappingStatus.fully_mapped,
            mapped_heavy_atom_fraction="1.0",
            map_number_uniqueness=True,
            changed_atom_coverage="1.0",
        )


@pytest.mark.contract
def test_int_string_coercion_rejected():
    """String '7' must not silently convert to int."""
    with pytest.raises(ValidationError):
        AtomTarget(kind="atom", atom_id="7")


# ============================================================
# 9. mechanistic origin without evidence IDs
# ============================================================

@pytest.mark.contract
def test_mechanistic_origin_without_evidence_ids_rejected():
    with pytest.raises(ValidationError, match="at least 1 evidence ID"):
        MechanisticAtomOrigin(evidence_ids=[], evidence_type="isotope_tracing")


# ============================================================
# 10. evidence IDs without compatible mechanistic origin
# ============================================================

@pytest.mark.contract
def test_mechanistic_evidence_ids_without_origin_field_rejected():
    """Section 12 (ADR-0003): unbound mechanistic evidence is prohibited.
    mechanistic_origin_evidence_ids non-empty without mechanistic_atom_origin
    must be rejected."""
    with pytest.raises(ValidationError, match="Unbound"):
        MappingReport(
            mapper_name="test", mapper_version="1.0",
            input_hash="abc", output_hash="def",
            mapping_status=MappingStatus.fully_mapped,
            mapped_heavy_atom_fraction=1.0,
            map_number_uniqueness=True,
            changed_atom_coverage=1.0,
            mechanistic_origin_evidence_ids=["ev1"],
            mechanistic_atom_origin=None,
        )


# ============================================================
# 11. candidate ledger references unknown source ledger
# ============================================================

@pytest.mark.contract
def test_candidate_ledger_requires_source_ledger_id():
    with pytest.raises(ValidationError):
        CandidateAnalogyLedger(
            ledger_id="cl1",
            candidate_id="c1",
        )


# ============================================================
# 12. arbitrary nested ledger field
# ============================================================

@pytest.mark.contract
def test_source_ledger_rejects_unknown_nested_fields():
    with pytest.raises(ValidationError):
        SourceReactionLedger(
            ledger_id="sl1",
            reaction_evidence_id="rxn1",
            balance_status=LedgerBalanceStatus.fully_balanced_explicit_reaction,
            arbitrary_unknown_field="bad",
        )


@pytest.mark.contract
def test_candidate_ledger_rejects_unknown_nested_fields():
    with pytest.raises(ValidationError):
        CandidateAnalogyLedger(
            ledger_id="cl1",
            source_ledger_id="sl1",
            candidate_id="c1",
            arbitrary_unknown_field="bad",
        )


# ============================================================
# 13. empty target set
# ============================================================

@pytest.mark.contract
def test_empty_target_set_rejected():
    with pytest.raises(ValidationError, match="must not be empty"):
        AgentProposedHypothesis(
            hypothesis_id="h1",
            transformation_family_id="ox",
            typed_target_atom_or_bond_set=[],
        )


# ============================================================
# 14. unknown atom/bond target kind
# ============================================================

@pytest.mark.contract
def test_unknown_target_kind_rejected():
    with pytest.raises(ValidationError):
        AgentProposedHypothesis(
            hypothesis_id="h1",
            transformation_family_id="ox",
            typed_target_atom_or_bond_set=[{"kind": "unknown_kind", "id": 5}],
        )


# ============================================================
# 15. empty manifest URI when required
# ============================================================

@pytest.mark.contract
def test_empty_manifest_uri_rejected():
    """manifest_uri must not accept empty string."""
    with pytest.raises(ValidationError):
        PredictionResult(
            run_id="r1", status=ResultStatus.completed,
            decision=DecisionKind.predicted,
            normalized_query="CCCCO", snapshot_id="snap1",
            candidates=[Candidate(
                candidate_id="c1", canonical_product="CCCC=O",
                lane=Lane.strict, origin="agent_selected_from_evidence_space",
            )],
            manifest_uri="",
        )


# ============================================================
# 16. stale JSON Schema export
# ============================================================

@pytest.mark.contract
def test_json_schema_freshness():
    """Verify exported JSON schemas match current model schemas."""
    import json
    import os
    from reaction_agent.schemas import (
        MappingReport, PredictionResult, Candidate,
        ProductionSelectionHypothesis, AgentProposedHypothesis,
    )
    schemas_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "schemas", "json"
    )
    for schema_cls in [MappingReport, PredictionResult, Candidate,
                       ProductionSelectionHypothesis, AgentProposedHypothesis]:
        json_path = os.path.join(schemas_dir, f"{schema_cls.__name__}.json")
        if not os.path.isfile(json_path):
            pytest.fail(f"Missing JSON Schema export: {schema_cls.__name__}.json")
        with open(json_path) as f:
            exported = json.load(f)
        current = schema_cls.model_json_schema()
        # Compare titles and property keys
        assert exported.get("title") == current.get("title"), (
            f"{schema_cls.__name__}: exported JSON Schema is stale (title mismatch)"
        )
        exported_props = set(exported.get("properties", {}).keys())
        current_props = set(current.get("properties", {}).keys())
        assert exported_props == current_props, (
            f"{schema_cls.__name__}: exported JSON Schema is stale "
            f"(props diff: {exported_props ^ current_props})"
        )


# ============================================================
# 17. ADR status text says Not Approved
# ============================================================

@pytest.mark.contract
def test_adr_status_not_approved_would_fail():
    """An ADR with 'Not Approved' or 'Pending' status must fail gate."""
    import os
    docs_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docs", "decisions"
    )
    for fname in os.listdir(docs_dir):
        if fname.startswith("ADR-") and fname.endswith(".md"):
            path = os.path.join(docs_dir, fname)
            with open(path) as f:
                content = f.read()
            # Parse first "Status:" line
            for line in content.split("\n"):
                stripped = line.strip()
                if stripped.startswith("Status:") or stripped.startswith("**Status:**"):
                    status_text = stripped.split(":", 1)[1].strip().strip("*").strip()
                    assert status_text == "Approved", (
                        f"{fname} has status '{status_text}', expected 'Approved'"
                    )
                    break


# ============================================================
# 18. old document still declares itself current authority
# ============================================================

@pytest.mark.contract
def test_old_documents_have_historical_banner():
    """Non-final files that previously claimed authority must have HISTORICAL banner."""
    import os
    plan_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "plan"
    )
    files_needing_banner = [
        "UNIFIED_DESIGN_REACTION_ANALOGY_AGENT_2026-07-29.md",
        "UNIFIED_PLAN_REACTION_ANALOGY_AGENT_2026-07-29.md",
        "FUSION_DESIGN_V5.md",
        "chatgpt-reaction-analogy-agent-design-v2.md",
    ]
    for fname in files_needing_banner:
        path = os.path.join(plan_dir, fname)
        if os.path.isfile(path):
            with open(path) as f:
                first_10_lines = "".join(f.readline() for _ in range(10))
            assert "HISTORICAL" in first_10_lines or "NON-AUTHORITATIVE" in first_10_lines, (
                f"{fname} missing HISTORICAL banner in first 10 lines"
            )


# ============================================================
# Additional: complete PredictionResult state machine matrix
# ============================================================

@pytest.mark.contract
def test_completed_with_partial_reason_rejected():
    c = Candidate(
        candidate_id="c1", canonical_product="CCCC=O",
        lane=Lane.strict, origin="agent_selected_from_evidence_space",
    )
    with pytest.raises(ValidationError, match="must not have partial_reason"):
        PredictionResult(
            run_id="r1", status=ResultStatus.completed,
            decision=DecisionKind.predicted,
            normalized_query="CCCCO", snapshot_id="snap1",
            candidates=[c], partial_reason="some reason",
        )


@pytest.mark.contract
def test_abstained_with_failure_rejected():
    with pytest.raises(ValidationError, match="must not have failure"):
        PredictionResult(
            run_id="r1", status=ResultStatus.abstained,
            decision=DecisionKind.abstained,
            normalized_query="CCCCO", snapshot_id="snap1",
            abstention=Abstention(reason_code=ScientificAbstentionReason.NO_IN_DOMAIN_DONOR),
            failure=Failure(reason_code=SystemFailureReason.STORAGE_FAILURE),
        )


@pytest.mark.contract
def test_partial_with_failure_rejected():
    with pytest.raises(ValidationError, match="must not have failure"):
        PredictionResult(
            run_id="r1", status=ResultStatus.partial,
            decision=DecisionKind.partial,
            normalized_query="CCCCO", snapshot_id="snap1",
            partial_reason="only generalized",
            failure=Failure(reason_code=SystemFailureReason.STORAGE_FAILURE),
        )


@pytest.mark.contract
def test_failed_with_decision_abstained_rejected():
    with pytest.raises(ValidationError, match="requires decision=failed"):
        PredictionResult(
            run_id="r1", status=ResultStatus.failed,
            decision=DecisionKind.abstained,
            normalized_query="CCCCO", snapshot_id="snap1",
            failure=Failure(reason_code=SystemFailureReason.STORAGE_FAILURE),
        )


@pytest.mark.contract
def test_abstained_with_partial_reason_rejected():
    with pytest.raises(ValidationError, match="must not have partial_reason"):
        PredictionResult(
            run_id="r1", status=ResultStatus.abstained,
            decision=DecisionKind.abstained,
            normalized_query="CCCCO", snapshot_id="snap1",
            abstention=Abstention(reason_code=ScientificAbstentionReason.NO_IN_DOMAIN_DONOR),
            partial_reason="some reason",
        )
