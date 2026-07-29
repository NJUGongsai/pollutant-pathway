#!/usr/bin/env python3
"""V3 remediation: verify the 12 residual false positives are now REJECTED.

BEFORE remediation: all 12 ACCEPTED (false positives) — see worklog.
AFTER remediation:  all 12 REJECTED.

c1/c2/c3 require the caller to supply a relation-aware context (Section 6/7);
c4/c5/c6/c7/c8 are rejected at schema/validator construction time;
c9-c12 are the new fail-open counterexamples (§3.2 A/B/C + §3.3 registry
self-contradiction) now rejected by fail-closed validation.

Usage:
    .venv/bin/python scripts/reproduce_v3_false_positives.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reaction_agent.schemas import (
    ProductionSelectionHypothesis,
    AgentProposedHypothesis,
    HypothesisReferenceRegistry,
    HypothesisValidationContext,
    LedgerReferenceRegistry,
    validate_hypothesis_references,
    validate_hypothesis_against_context,
    validate_candidate_ledger_references,
    AtomTarget,
    BondTarget,
    CandidateAnalogyLedger,
    InheritedDonorContext,
    QueryCandidateAdaptation,
    MappingReport,
    MappingStatus,
    FormalSourceAssignment,
    MechanisticAtomOrigin,
    SourceAssignmentMethod,
)
from pydantic import ValidationError

results: list[tuple[str, str]] = []


def case(name: str, fn) -> None:
    try:
        fn()
        results.append((name, "ACCEPTED (false positive — REGRESSION)"))
    except Exception as e:  # noqa: BLE001
        results.append((name, f"REJECTED ({type(e).__name__})"))


# 1. site_transform_mismatch: s1 belongs to t1, hypothesis selects t2 + s1
def c1() -> None:
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"rxn1"}),
        transformation_ids=frozenset({"t1", "t2"}),
        site_ids=frozenset({"s1"}),
        site_to_transformation_id={"s1": "t1"},
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1", support_reaction_ids=["rxn1"],
        transformation_id="t2", site_id="s1",
    )
    validate_hypothesis_references(h, registry)


case("site_transform_mismatch", c1)


# 2. target_not_in_query: AtomTarget(atom_id=999999) not in query
def c2() -> None:
    registry = HypothesisReferenceRegistry(
        transformation_family_ids=frozenset({"ox"}),
    )
    context = HypothesisValidationContext(
        registry=registry, query_atom_ids=frozenset({0, 1, 2}),
    )
    h = AgentProposedHypothesis(
        hypothesis_id="h2", transformation_family_id="ox",
        typed_target_atom_or_bond_set=[AtomTarget(atom_id=999999)],
    )
    validate_hypothesis_against_context(h, context)


case("target_not_in_query", c2)


# 3. unknown_source_ledger_reference (non-empty but unknown)
def c3() -> None:
    registry = LedgerReferenceRegistry(
        source_ledger_ids=frozenset({"sl1"}),
        candidate_ids=frozenset({"c1"}),
    )
    ledger = CandidateAnalogyLedger(
        ledger_id="cl1", source_ledger_id="DOES_NOT_EXIST", candidate_id="c1",
    )
    validate_candidate_ledger_references(ledger, registry)


case("unknown_source_ledger_reference", c3)


# 4. donor_context_not_assumption
def c4() -> None:
    InheritedDonorContext(
        donor_reaction_id="rxn1", donor_participant_id="p1", is_assumption=False,
    )


case("donor_context_not_assumption", c4)


# 5. qualitative_confidence_note (field removed, extra=forbid)
def c5() -> None:
    QueryCandidateAdaptation(donor_participant_id="p1", confidence_note="high confidence")


case("qualitative_confidence_note", c5)


# 6. self_bond_target
def c6() -> None:
    BondTarget(begin_atom_id=4, end_atom_id=4)


case("self_bond_target", c6)


# 7. mechanistic_evidence_mismatch (typed vs flat conflict)
def c7() -> None:
    MappingReport(
        mapper_name="t", mapper_version="1", input_hash="a", output_hash="b",
        mapping_status=MappingStatus.fully_mapped,
        mapped_heavy_atom_fraction=1.0, map_number_uniqueness=True,
        changed_atom_coverage=1.0,
        mechanistic_atom_origin=MechanisticAtomOrigin(
            evidence_ids=["E1"], evidence_type="iso"),
        mechanistic_origin_evidence_ids=["E2"],
    )


case("mechanistic_evidence_mismatch", c7)


# 8. formal_assignment_method_mismatch (typed vs flat conflict)
def c8() -> None:
    MappingReport(
        mapper_name="t", mapper_version="1", input_hash="a", output_hash="b",
        mapping_status=MappingStatus.fully_mapped,
        mapped_heavy_atom_fraction=1.0, map_number_uniqueness=True,
        changed_atom_coverage=1.0,
        formal_mapped_source_assignment=FormalSourceAssignment(
            mapper_name="t", mapper_version="1",
            assignment_method=SourceAssignmentMethod.manual_curation),
        source_assignment_method=SourceAssignmentMethod.formal_mapped,
    )


case("formal_assignment_method_mismatch", c8)


# 9. production_empty_relation_maps_mismatch (§3.2 A): all IDs exist, ALL relation maps empty
def c9() -> None:
    registry = HypothesisReferenceRegistry(
        reaction_ids=frozenset({"r"}),
        lineage_ids=frozenset({"l"}),
        transformation_ids=frozenset({"t1", "t2"}),
        site_ids=frozenset({"s1"}),
        # all relation maps empty
    )
    h = ProductionSelectionHypothesis(
        hypothesis_id="h1", support_reaction_ids=["r"],
        support_lineage_ids=["l"], transformation_id="t2", site_id="s1",
    )
    validate_hypothesis_references(h, registry)


case("production_empty_relation_maps_mismatch", c9)


# 10. agent_empty_query_context_target (§3.2 B): target present, query context not provided
def c10() -> None:
    registry = HypothesisReferenceRegistry(transformation_family_ids=frozenset({"ox"}))
    context = HypothesisValidationContext(
        registry=registry, query_atom_ids=None, query_bond_pairs=None,
    )
    h = AgentProposedHypothesis(
        hypothesis_id="h2", transformation_family_id="ox",
        typed_target_atom_or_bond_set=[AtomTarget(atom_id=999999)],
    )
    validate_hypothesis_against_context(h, context)


case("agent_empty_query_context_target", c10)


# 11. relaxation_without_selected_policy (§3.2 C): relaxation present, policy null
def c11() -> None:
    registry = HypothesisReferenceRegistry(
        transformation_family_ids=frozenset({"ox"}),
        relaxation_ids=frozenset({"r1"}),
    )
    h = AgentProposedHypothesis(
        hypothesis_id="h2", transformation_family_id="ox",
        typed_target_atom_or_bond_set=[AtomTarget(atom_id=0)],
        relaxation_policy_id=None, allowed_relaxation_ids=["r1"],
    )
    validate_hypothesis_references(h, registry)


case("relaxation_without_selected_policy", c11)


# 12. registry_internal_contradiction (§3.3): site map value not in transformation_ids
def c12() -> None:
    HypothesisReferenceRegistry(
        transformation_ids=frozenset({"t"}),
        site_ids=frozenset({"s"}),
        site_to_transformation_id={"s": "not_known"},
    )


case("registry_internal_contradiction", c12)


# -- Report --
print("=" * 70)
print("V3 Remediation: 12 False Positives — post-remediation verification")
print("=" * 70)
print("  original 8 (c1-c8) + new 4 fail-open counterexamples (c9-c12)")
print("-" * 70)
for name, result in results:
    print(f"  {name:45s} {result}")
accepted = sum(1 for _, r in results if "ACCEPTED" in r)
rejected = sum(1 for _, r in results if "REJECTED" in r)
print(f"\nACCEPTED: {accepted}/12")
print(f"REJECTED: {rejected}/12")
print()
if rejected == 12:
    print("STATUS: all 12 false positives eliminated — remediation successful")
else:
    print(f"STATUS: partial — {accepted} still accepted (regression)")
