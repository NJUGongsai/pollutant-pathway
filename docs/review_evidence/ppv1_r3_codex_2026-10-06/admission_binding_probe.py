"""Synthetic R3 review: real donor evidence reused across reaction inputs.

No assets, model, gold or persistent ledger. Prints actual public API results.
"""
import json
from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis
from pathway_v43.pollutant.path_context import build_condition_fact, build_requirement, build_path_context
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission, check_edit_against_donor, center_evidence_from_donor_diagnostic, AdmissionPolicy
from pathway_v43.services.atom_tool import roundtrip, execute_edits

def state(s):
    return build_chemical_state(s, 'raw_input')

def reaction(reactants, products):
    ss = [state(s) for s in reactants + products]
    pp = [Participant(state_ref=s.state_id, side='reactant' if i < len(reactants) else 'product',
        role='primary_substrate' if i == 0 else 'cosubstrate' if i < len(reactants)
        else 'principal_product' if i == len(reactants) else 'coproduct',
        coefficient=1, coefficient_status='known') for i, s in enumerate(ss)]
    h = build_hypothesis(parent_path_id='synthetic:root', substrate_state_ref=ss[0].state_id,
        participants=pp, participant_list_status='declared_complete', step_scope='net_reaction',
        origin_group_key='synthetic:binding')
    return h, {s.state_id:s for s in ss}

ctx = build_path_context(condition_facts=[build_condition_fact(key='oxygen_regime',
    value='aerobic', status='known_present')], accumulated_requirements=[build_requirement(
        key='oxygen_regime', level='essential', value='aerobic', source_refs=['synthetic:requirement'])],
    assessment_scope=['oxygen_regime'])
render = roundtrip('CCO', name='S')
edits = [{'op':'change_bond_order','atom1':'S_C_2','atom2':'S_O_1','from_order':'single','to_order':'double'}]
executed = execute_edits(render, edits)
diag = check_edit_against_donor(current={'smiles':render.smiles,'atom_id_map':render.atom_id_map},
    donor={'center_atom_ids':['dC','dO']}, alignment={'status':'resolved',
        'donor_to_current':{'dC':'S_C_2','dO':'S_O_1'}, 'ref':'synthetic:ethanol-to-acetaldehyde'},
    expectation={'target_smiles':'CC=O'}, result=executed, edits=edits)
evidence = center_evidence_from_donor_diagnostic(diag)
out = {'head':'af14fb2bb66e8afbbbbecd38722a9cacbd0699c3',
    'actual_execution':executed, 'real_diagnostic':diag.to_dict(), 'center_evidence':evidence,
    'disclaimer':'Inputs are synthetic contract fixtures, not biological feasibility claims.'}
audits = {}
for name, reac, prod in [('acetic_acid', ['CCO','O=O'], ['CC(=O)O','O']),
                         ('unrelated_propene_cyclization', ['CC=C'], ['C1CC1'])]:
    h, ss = reaction(reac, prod)
    a = audit_hypothesis(h, states=ss, context=ctx, center_evidence=evidence)
    out[name] = {'hypothesis':h.to_dict(), 'audit':a.to_dict(), 'admission':decide_admission(a)}
    audits[name] = a

gates = {'per_product_verdicts':[{'position':0,'accepted':False,'reasons':['synthetic:element_gate_rejected']},
                                {'position':1,'accepted':True,'reasons':[]}]}
out['gate_consumption_on'] = decide_admission(audits['acetic_acid'], gate_decisions=gates)
out['gate_consumption_off'] = decide_admission(audits['acetic_acid'], gate_decisions=gates,
    policy=AdmissionPolicy(per_product_gate_consumption='off'))
out['registered_name_only'] = {}
h, ss = reaction(['CC=C'], ['C1CC1'])
a = audit_hypothesis(h, states=ss, context=ctx,
    center_evidence={'checker_version':'ppv1-donor-diagnostic-3','center_match':True})
out['registered_name_only'] = {'center_check':[c.to_dict() for c in a.checks if c.name=='transformation_center'],
                              'admission':decide_admission(a)}
print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
