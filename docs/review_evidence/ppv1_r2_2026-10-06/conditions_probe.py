"""Synthetic, deterministic PPV1 R2 review probes; no assets or models.

Run with PYTHONDONTWRITEBYTECODE=1 and the target repo src on PYTHONPATH.
"""
import json
import tempfile
from fractions import Fraction
from pathlib import Path

from pathway_v43.pollutant.path_context import (
    aggregate_environment_fit as assess, build_condition_fact as fact,
    build_requirement as req, build_path_context as context,
    derive_child_context, build_dependency, resolve_dependency,
    detect_circular_dependencies,
)
from pathway_v43.pollutant.provenance import build_support_groups, map_legacy_card
from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission

OUT = {}

def f(key, value, **kw):
    return fact(key=key, value=value, status="known_present", **kw)

def r(key, value, **kw):
    return req(key=key, value=value, level="essential", source_refs=["src:synthetic"], **kw)

def save(name, value):
    OUT[name] = value.to_dict() if hasattr(value, "to_dict") else value

# Fixed-scenario F02 controls.
for actual in (45, 25):
    parent = context(condition_facts=[f("temperature_C", actual)],
        accumulated_requirements=[r("temperature_C", {"lo": 20, "hi": 30})],
        assessment_scope=["temperature_C"])
    child = derive_child_context(parent, step_requirements=[
        r("temperature_C", {"lo": 40, "hi": 50})])
    save(f"fixed_F02_{actual}", {"parent": parent.assessed_scope,
        "child": child.assessed_scope, "requirements": len(child.accumulated_requirements)})

# Legitimate aerobic -> anaerobic sequence: each edge matches its own phase.
facts = [f("oxygen_regime", "aerobic", phase_id="p0", subject_scenario_ref="s"),
         f("oxygen_regime", "anaerobic", phase_id="p1", subject_scenario_ref="s")]
parent = context(condition_facts=facts, phase_id="p0", scenario_ref="s",
    accumulated_requirements=[r("oxygen_regime", "aerobic")],
    assessment_scope=["oxygen_regime"])
child = derive_child_context(parent, step_requirements=[r("oxygen_regime", "anaerobic")],
    scenario_transition={"new_phase_id": "p1", "source_ref": "user:explicit_transition"})
save("phase_transition_false_conflict", {"parent": parent.assessed_scope,
    "child": child.assessed_scope, "assessment": assess(facts=child.condition_facts,
    requirements=child.accumulated_requirements, declared_scope=child.assessment_scope,
    scenario_ref=child.scenario_ref, phase_id=child.phase_id).to_dict()})

# Past edge conflict must survive a future phase transition.
parent2 = context(condition_facts=facts, phase_id="p0", scenario_ref="s",
    accumulated_requirements=[r("oxygen_regime", "anaerobic")],
    assessment_scope=["oxygen_regime"])
child2 = derive_child_context(parent2,
    scenario_transition={"new_phase_id": "p1", "source_ref": "user:explicit_transition"})
save("phase_transition_erases_past_conflict", {"parent": parent2.assessed_scope,
    "child": child2.assessed_scope, "parent_unchanged": parent2.assessed_scope})

# A point inside an uncertain interval is unknown; a singleton equal interval satisfies.
for fv in ({"lo": 6.8, "hi": 7.2}, {"lo": 7.0, "hi": 7.0}, {"lo": 8.0, "hi": 9.0}):
    save(f"point_interval_{fv['lo']}_{fv['hi']}", assess(facts=[f("pH", fv)],
        requirements=[r("pH", 7.0, value_basis="point")], declared_scope=["pH"]))

# Same-valued observations from two independent refs do not contradict each other.
save("identical_facts_distinct_sources", assess(facts=[
    f("pH", 7.0, source_ref="src:A"), f("pH", 7.0, source_ref="src:B")],
    requirements=[r("pH", {"lo": 6, "hi": 8})], declared_scope=["pH"]))

# Absence is entity-specific; acetate absence does not establish NADH absence.
save("unrelated_donor_absence", assess(facts=[fact(key="electron_donor", value="acetate",
    status="known_absent")], requirements=[r("electron_donor", "NADH")],
    declared_scope=["electron_donor"]))
save("multiple_present_donors", assess(facts=[f("electron_donor", "NADH"),
    f("electron_donor", "acetate")], requirements=[r("electron_donor", "NADH")],
    declared_scope=["electron_donor"]))

# Unit has no effect: 25 K is compared as if 25 Celsius.
save("temperature_kelvin_compared_as_celsius", assess(facts=[f("temperature_C", 25, unit="K")],
    requirements=[r("temperature_C", {"lo": 20, "hi": 30})],
    declared_scope=["temperature_C"]))

# Caller can claim assessed dimensions with no facts or requirements for those dimensions.
save("scope_claim_without_evaluation", assess(facts=[f("oxygen_regime", "aerobic")],
    requirements=[r("oxygen_regime", "aerobic")],
    declared_scope=["oxygen_regime", "pH", "temperature_C"]))

# R2 coverage last-wins issue.
save("coverage_conflict_then_satisfied", assess(facts=[f("pH", 7.0)],
    requirements=[r("pH", {"lo": 4, "hi": 5}), r("pH", {"lo": 6, "hi": 8})],
    declared_scope=["pH"]))

# Value/basis mismatch: explicit point+interval is silently rewritten; range+point accepted.
save("basis_point_interval_silently_rewritten", r("pH", {"lo": 6, "hi": 8}, value_basis="point"))
save("basis_range_point_accepted", r("pH", 7.0, value_basis="range"))

# F06 IDs distinguish scope / dependencies after repair.
a = context(assessment_scope=[])
b = context(assessment_scope=["pH"])
c = derive_child_context(a, step_dependency_refs=["dep:X"])
d = derive_child_context(a, step_dependency_refs=["dep:Y"])
save("F06_identity_controls", {"scope_ids_different": a.context_id != b.context_id,
    "dependency_ids_different": c.context_id != d.context_id})

# Requirement objects remain shared between parent and sibling branches.
mutable_parent = context(condition_facts=[f("temperature_C", 25)],
    accumulated_requirements=[r("temperature_C", {"lo": 20, "hi": 30})],
    assessment_scope=["temperature_C"])
mutable_a = derive_child_context(mutable_parent)
mutable_b = derive_child_context(mutable_parent)
before = mutable_parent.assessed_scope
frozen_id = mutable_parent.context_id
mutable_a.accumulated_requirements[0].value.update({"lo": 40, "hi": 50})
save("requirement_branch_alias", {"parent_before": before,
    "parent_after": mutable_parent.assessed_scope, "sibling_after": mutable_b.assessed_scope,
    "parent_id_unchanged": frozen_id == mutable_parent.context_id,
    "same_requirement_object": mutable_a.accumulated_requirements[0]
        is mutable_parent.accumulated_requirements[0]})

# All three regeneration edges observed, but no evidence of an external initial pool.
deps = [build_dependency(kind="cosubstrate_supply", statement=s)
    for s in ("supplies:A:B", "supplies:B:C", "supplies:C:A")]
save("three_node_unresolved_control", detect_circular_dependencies(deps))
resolved = [resolve_dependency(d, new_evidence=[f"src:regeneration:{i}"],
    resolution="supported", note="Synthetic observation of regeneration edge; no initial supply")
    for i, d in enumerate(deps)]
save("regeneration_only_cycle_loses_startup_unknown", detect_circular_dependencies(resolved))

# F10 repaired controls and residual partially traced independence reporting.
cards = [{"kind": "recorded_reaction", "source_id": "dbA", "evidence_id": "a"},
         {"kind": "recorded_reaction", "source_id": "dbB", "evidence_id": "b"}]
save("F10_no_study_map", [g.to_dict() for g in build_support_groups(cards)])
save("F10_same_study", [g.to_dict() for g in build_support_groups(cards,
    study_map={"recorded_reaction:dbA": "doi:synthetic", "recorded_reaction:dbB": "doi:synthetic"})])
save("partial_study_map", [g.to_dict() for g in build_support_groups(cards,
    study_map={"recorded_reaction:dbA": "doi:synthetic"})])
save("empty_study_map", [g.to_dict() for g in build_support_groups(cards, study_map={})])
save("F10_unidentified_rule", map_legacy_card({"kind": "rule_application", "source_id": "engine_pred"}))
save("F10_mixed_components", map_legacy_card({"kind": "rule_application", "source_id": "envipath+retrieval",
    "asset_sources": [{"role": "envipath"}, {"role": "retrieval"}]}))

# Hypothesis hash collision for different condition and dependency semantics.
sub = build_chemical_state("CCO", origin="raw_input")
prod = build_chemical_state("CCO", origin="source_product")
def hyp(requirements, dependencies=None):
    return build_hypothesis(parent_path_id="synthetic:parent", substrate_state_ref=sub.state_id,
        participants=[Participant(state_ref=sub.state_id, side="reactant", role="primary_substrate",
            coefficient=Fraction(1), coefficient_status="known"),
            Participant(state_ref=prod.state_id, side="product", role="principal_product",
                coefficient=Fraction(1), coefficient_status="known")],
        participant_list_status="declared_complete", step_scope="net_reaction",
        transformation_signature_status="verified", origin_group_key="same:source",
        requirements=[v.to_dict() for v in requirements], dependency_refs=dependencies)
h1 = hyp([r("oxygen_regime", "aerobic")])
h2 = hyp([r("oxygen_regime", "anaerobic")])
h3 = hyp([r("oxygen_regime", "aerobic")], ["dep:unknown"])
ctx = context(condition_facts=[f("oxygen_regime", "aerobic")], assessment_scope=["oxygen_regime"])
audits = [audit_hypothesis(h, states={sub.state_id: sub}, context=ctx) for h in (h1,h2)]
with tempfile.TemporaryDirectory(prefix="synthetic_db_", dir=Path(__file__).parent) as tmp:
    store = PollutantPathwayStore(Path(tmp)/"store.sqlite")
    store.put_hypothesis(h1.to_dict(), context_hash=ctx.context_id)
    try:
        store.put_hypothesis(h2.to_dict(), context_hash=ctx.context_id)
        failure = None
    except Exception as e:
        failure = {"type": type(e).__name__, "message": str(e)}
    store.close()
save("hypothesis_condition_dependency_identity_collision", {"ids": [h.hypothesis_id for h in (h1,h2,h3)],
    "input_hashes": [a.input_hash for a in audits],
    "admission": [decide_admission(a) for a in audits], "second_put": failure})

print(json.dumps(OUT, ensure_ascii=False, indent=2, sort_keys=True))
