"""R4 independent audit consumer probes: synthetic structures, no data/model/run."""
import copy
import json
from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis
from pathway_v43.pollutant.path_context import build_condition_fact, build_requirement, build_path_context
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission, check_edit_against_donor, center_evidence_from_donor_diagnostic
from pathway_v43.services.atom_tool import roundtrip, execute_edits

HEAD='e80f4594ea44b5f2bf8c78360dc2ed2368dd94ae'
def emit(name, **kw):
    print(json.dumps({'probe':name,**kw},ensure_ascii=False,default=str))
def reaction(reac,prod):
    ss=[build_chemical_state(s,'raw_input') for s in reac+prod]
    parts=[Participant(state_ref=s.state_id,side='reactant' if i<len(reac) else 'product',
        role='primary_substrate' if i==0 else 'cosubstrate' if i<len(reac) else 'principal_product' if i==len(reac) else 'coproduct',
        coefficient=1,coefficient_status='known') for i,s in enumerate(ss)]
    h=build_hypothesis(parent_path_id='synthetic:root',substrate_state_ref=ss[0].state_id,
        participants=parts,participant_list_status='declared_complete',step_scope='net_reaction',origin_group_key='synthetic:r4')
    return h,{s.state_id:s for s in ss}
ctx=build_path_context(condition_facts=[build_condition_fact(key='oxygen_regime',value='aerobic',status='known_present')],
    accumulated_requirements=[build_requirement(key='oxygen_regime',level='essential',value='aerobic',source_refs=['synthetic:requirement'])],
    assessment_scope=['oxygen_regime'])
def diagnostic(edits):
    r=roundtrip('CCO',name='S')
    ex=execute_edits(r,edits)
    assert ex['ok'],ex
    ids=list(dict.fromkeys(e[k] for e in edits for k in ('atom1','atom2') if k in e))
    donor=[f'd{i}' for i in range(len(ids))]
    d=check_edit_against_donor(current={'smiles':r.smiles,'atom_id_map':r.atom_id_map},
        donor={'center_atom_ids':donor},alignment={'status':'resolved','donor_to_current':dict(zip(donor,ids)),'ref':'synthetic:diagnostic'},
        expectation={'target_smiles':ex['product_smiles']},result=ex,edits=edits)
    return d,ex
def audit_case(name,h,states,ev,**kw):
    a=audit_hypothesis(h,states=states,context=ctx,center_evidence=ev,**kw)
    emit(name,hypothesis=h.to_dict(),audit=a.to_dict(),admission=decide_admission(a),evidence=ev)
    return a
emit('meta',head=HEAD,disclaimer='Synthetic API fixtures; numeric balance is not biological feasibility.')
diag,ex=diagnostic([{'op':'change_bond_order','atom1':'S_C_2','atom2':'S_O_1','from_order':'single','to_order':'double'}])
ev=center_evidence_from_donor_diagnostic(diag)
emit('genuine_ethanol_diagnostic',diagnostic=diag.to_dict(),execution=ex)
h,ss=reaction(['CCO'],['CC=O','[H][H]'])
base=audit_case('genuine_bound_control',h,ss,ev)
minimal={k:copy.deepcopy(ev[k]) for k in ['checker_version','checker_scope','center_match','strict_target_match','declaration_mismatch']}
minimal['bound_inputs']={k:ev['bound_inputs'][k] for k in ['substrate_identity','product_identity']}
audit_case('binding_only_two_identity_strings',h,ss,minimal)
fabricated=copy.deepcopy(minimal)
fabricated['bound_inputs'].update(edits_signature='fictional:no-edits',execution_fingerprint='fictional:no-result',donor_centers=['fictional:carbon'],alignment_ref='fictional:no-mapping')
audit_case('six_fields_all_claimed_no_checker_execution',h,ss,fabricated)
for key in ('edits_signature','execution_fingerprint','donor_centers','alignment_ref'):
    altered=copy.deepcopy(ev)
    altered['bound_inputs'][key]=['fake:other-center'] if key=='donor_centers' else 'fake:other-input'
    audit_case('genuine_evidence_mutated_'+key,h,ss,altered)
for value in ['false',0,{},[],False,None]:
    altered=copy.deepcopy(ev)
    altered['strict_target_match']=value
    audit_case('strict_axis_type_'+type(value).__name__+'_'+str(value),h,ss,altered)
run=audit_case('finite_rule_diagnostic_active',h,ss,ev,finite_rule_diagnostic={'status':'diagnostic_only','reason':'synthetic:active'})
emit('finite_rule_hash_comparison',baseline_hash=base.input_hash,active_hash=run.input_hash,
    baseline_admission=decide_admission(base),active_admission=decide_admission(run),baseline_scope=base.scope,
    active_scope=run.scope)
custom=audit_case('explicit_audit_scope_label',h,ss,ev,scope='synthetic:review-scope')
emit('audit_scope_label_comparison',requested='synthetic:review-scope',actual=custom.scope,default=base.scope)
breakdiag,breakex=diagnostic([{'op':'break_bond','atom1':'S_C_1','atom2':'S_C_2'}])
bev=center_evidence_from_donor_diagnostic(breakdiag)
emit('real_break_fragment_diagnostic',diagnostic=breakdiag.to_dict(),execution=breakex)
assert breakex['product_smiles']=='C.CO',breakex
bh,bss=reaction(['CCO','[H][H]'],['C','CO'])
audit_case('real_fragment_products_separate_participants',bh,bss,bev)
lh,lss=reaction(['CCO','[H][H]'],['C.CO'])
audit_case('real_fragment_products_lumped_control',lh,lss,bev)
extra_h,extra_ss=reaction(['CCO','C1CC1'],['CC=O','[H][H]','CC=C'])
audit_case('genuine_primary_evidence_unchecked_additional_transformation',extra_h,extra_ss,ev)
