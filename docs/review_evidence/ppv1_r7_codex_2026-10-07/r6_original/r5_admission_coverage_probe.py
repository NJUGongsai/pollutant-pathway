"""R5 independent, synthetic public API probes. Balance is not pathway feasibility."""
import copy
import json
import sys
from rdkit import rdBase
from pathway_v43.pollutant.chemstate import build_chemical_state
from pathway_v43.pollutant.hypothesis import Participant, build_hypothesis
from pathway_v43.pollutant.path_context import build_condition_fact, build_requirement, build_path_context
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission, check_edit_against_donor, center_evidence_from_donor_diagnostic
from pathway_v43.services.atom_tool import roundtrip, execute_edits

def emit(name, **kw):
    print(json.dumps({'probe': name, **kw}, ensure_ascii=False, default=str))

ctx = build_path_context(condition_facts=[build_condition_fact(key='oxygen_regime', value='aerobic', status='known_present')],
    accumulated_requirements=[build_requirement(key='oxygen_regime', level='essential', value='aerobic', source_refs=['synthetic:requirement'])],
    assessment_scope=['oxygen_regime'])

def evidence(substrate, frm, to):
    render = roundtrip(substrate, name='S')
    edits = [{'op':'change_bond_order', 'atom1':'S_C_2', 'atom2':'S_O_1', 'from_order':frm, 'to_order':to}]
    result = execute_edits(render, edits)
    assert result['ok'], result
    diag = check_edit_against_donor(current={'smiles':render.smiles, 'atom_id_map':render.atom_id_map},
        donor={'center_atom_ids':['dC','dO']}, alignment={'status':'resolved', 'donor_to_current':{'dC':'S_C_2','dO':'S_O_1'}, 'ref':'synthetic:proof'},
        expectation={'target_smiles':result['product_smiles']}, result=result, edits=edits)
    assert diag.reaction_center_match is True and diag.strict_target_match is True, diag.to_dict()
    return center_evidence_from_donor_diagnostic(diag), result, diag

def run(name, reactants, products, ev):
    states = {}
    parts = []
    for side, species in [('reactant', reactants), ('product', products)]:
        for i, (smi, coefficient) in enumerate(species):
            state = build_chemical_state(smi, 'raw_input')
            states[state.state_id] = state
            role = 'primary_substrate' if side == 'reactant' and i == 0 else 'cosubstrate' if side == 'reactant' else 'principal_product' if i == 0 else 'coproduct'
            parts.append(Participant(state_ref=state.state_id, side=side, role=role, coefficient=coefficient, coefficient_status='known'))
    hyp = build_hypothesis(parent_path_id='synthetic:root', substrate_state_ref=parts[0].state_ref, participants=parts,
        participant_list_status='declared_complete', step_scope='net_reaction', origin_group_key='synthetic:r5:'+name)
    audit = audit_hypothesis(hyp, states=states, context=ctx, center_evidence=ev)
    admission = decide_admission(audit, gate_decisions={'gate_direction_source':{'ok':True}})
    center = next(c for c in audit.checks if c.name == 'transformation_center')
    emit(name, hypothesis=hyp.to_dict(), audit=audit.to_dict(), admission=admission, center=center.to_dict())
    return audit, center, admission

emit('meta', head='293bc627f57b1f778aa433750f7f61d00b4a9d18', python=sys.version.split()[0], rdkit=rdBase.rdkitVersion,
    scope='synthetic API inputs; not biology, pollutant performance, or historical execution attestation')
oxidation, result, diag = evidence('CCO','single','double')
emit('genuine_oxidation_diagnostic', result=result, diagnostic=diag.to_dict())
base = run('genuine_bound_control', [('CCO',1)], [('CC=O',1),('[H][H]',1)], oxidation)
assert base[1].status == 'verified' and base[2][0] == 'expand'
partial = run('old_two_sided_unchecked_control', [('CCO',1),('C1CC1',1)], [('CC=O',1),('[H][H]',1),('CC=C',1)], oxidation)
assert partial[1].status == 'unknown' and partial[2][0] != 'expand'
mixed = run('one_sided_product_unchecked_isomer_half', [('CCO',1)], [('CC=O','1/2'),('C1CO1','1/2'),('[H][H]',1)], oxidation)
reduction, result, diag = evidence('CC=O','double','single')
emit('genuine_reduction_diagnostic', result=result, diagnostic=diag.to_dict())
reduced = run('genuine_hydrogenation_control', [('CC=O',1),('[H][H]',1)], [('CCO',1)], reduction)
assert reduced[1].status == 'verified' and reduced[2][0] == 'expand'
extra = run('one_sided_cosubstrate_unchecked_to_same_product', [('CC=O',1),('C1CO1',1),('[H][H]',2)], [('CCO',2)], reduction)
emit('observations', mixed_product_center=mixed[1].status, mixed_product_coverage=mixed[1].detail.get('product_coverage'), mixed_product_admission=mixed[2][0],
    extra_cosubstrate_center=extra[1].status, extra_cosubstrate_coverage=extra[1].detail.get('product_coverage'), extra_cosubstrate_admission=extra[2][0],
    verified_proof_scope=base[1].detail.get('proof_scope'), verified_reason=base[1].reason_code)
