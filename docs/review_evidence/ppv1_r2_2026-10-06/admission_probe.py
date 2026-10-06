from pathlib import Path
import json
import sys
sys.path.insert(0, "/Volumes/CC/Enzyme_Agent/dependingv43/src")
from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis
from pathway_v43.pollutant.path_context import build_path_context, build_requirement, build_condition_fact
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission, CHECK_STRUCTURE_PARSE_VALENCE
states = {v:build_chemical_state(v, "raw_input" if v=="CCO" else "source_product") for v in ["CCO","O=O","CC(=O)O","O"]}
def p(v, side, role):
    return Participant(state_ref=states[v].state_id, side=side, role=role, coefficient=1, coefficient_status="known")
req=build_requirement(key="oxygen_regime", level="essential", value="aerobic", source_refs=["synthetic:essential"])
hyp=build_hypothesis(parent_path_id="synthetic-parent",substrate_state_ref=states["CCO"].state_id,
    participants=[p("CCO","reactant","primary_substrate"),p("O=O","reactant","cosubstrate"),
        p("CC(=O)O","product","principal_product"),p("O","product","coproduct")],
    participant_list_status="declared_complete",step_scope="net_reaction",
    requirements=[req.to_dict()],transformation_signature_status="verified",origin_group_key="synthetic-oxidation")
by_id={s.state_id:s for s in states.values()}
ctx=build_path_context(condition_facts=[build_condition_fact(key="oxygen_regime",value="aerobic",status="known_present")],
    assessment_scope=["oxygen_regime"],scenario_ref="synthetic-scenario")
out={"repo_head":"0002f71","method":"synthetic contract/API; no models/datasets"}
for name, kwargs in [
    ("no_context", {}),
    ("only_structure_parse", {"audit_scope":{CHECK_STRUCTURE_PARSE_VALENCE}}),
    ("context_provided",{"context":ctx}),
]:
    audit=audit_hypothesis(hyp,states=by_id,**kwargs)
    out[name]={"checks":[c.to_dict() for c in audit.checks],"admission":decide_admission(audit)}
text=json.dumps(out,indent=2,ensure_ascii=False)
Path("/private/tmp/ppv1_r2_admission_scope_probe_0002f71.json").write_text(text+"\n")
print(text)
