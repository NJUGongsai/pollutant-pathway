"""R8 expected public observations, explicit refusal and legal controls; no pytest."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
old={r['case']:r for l in (ROOT/'chemical_boundary_output.jsonl').read_text().splitlines() if (r:=json.loads(l))}
new={r['case']:r for l in (ROOT/'state_first_consumer_output.jsonl').read_text().splitlines() if (r:=json.loads(l))}
assert len(old)==55
run=json.loads((ROOT/'chemical_probe_run.json').read_text())
assert run['returncode']==1 and 'ChemicalStateError' in (ROOT/'chemical_boundary_stderr.txt').read_text()
assert 'C1_chiral_raw_unknown_flag' not in old and 'C1_CN_only_honest_unknown_control' not in old
for label in ['canonical_substrate_unknown_flag','canonical_product_unknown_flag','canonical_uncovered_H2_unknown_flag']:
 r=old['C1_'+label];assert not r['ok'] and r['exception']=='ChemicalStateError' and r['detail']['kind']=='state_structure_unparseable' and r['detail']['reason']['kind']=='unregistered_cx_class'
for label in ['raw_substrate_unknown_flag','raw_product_unknown_flag','raw_uncovered_H2_unknown_flag','raw_uncovered_H2_different_molecule']:
 r=old['C1_'+label];assert not r['ok'] and r['exception']=='ChemicalStateError'
for label in ['clean_factory_public_chain','C1_restore_control_clean','C1_restore_control_same_graph_spelling','C1_restore_control_registered_metadata','C1_chiral_clean_control']:
 assert old[label]['ok'] and old[label]['result']['admission']==['expand',['R6:all_verified_no_conflict']]
for i in [0,5,6,7,8,9]:
 r=old['C3_retained_'+str(i)]['result'];assert r['guard_accepted'] and r['same_identity'] and r['different_from_bare'] and r['canonical_writer_stable'] and r['radical_multiset_equal']
for i in [1,2,3,4]:
 assert not old['C3_retained_'+str(i)]['result']['guard_accepted']
for i in range(3):
 r=old['C3_removed_'+str(i)]['result'];assert r['guard_accepted'] and r['same_identity'] and not r['different_from_bare'] and r['canonical_writer_stable']
for co in ['CC=O','C1CO1','C=CO']:
 r=old['R6_01_'+co]['result'];assert r['admission'][0]=='retain_conditional';c=next(x for x in r['audit']['checks'] if x['name']=='transformation_center');assert c['status']=='unknown' and c['detail']['product_coverage']=='partial_unchecked_transformation'
for field in ['current','mapped','plain','target']:
 r=old['C6_execution_success_'+field];assert not r['ok'] and r['exception']=='AuditContractError' and r['detail']['kind']=='raw_input_cx_class_unregistered'
 r=old['C6_execution_failure_'+field];assert r['ok'];d=r['result']['diagnostic'];assert all(d[k] is None for k in ['reaction_center_match','strict_target_match','legacy_cn_match']) and d['center_evidence']=={} and r['result']['evidence']['center_match'] is None
for case,r in new.items():
 if case=='metadata':continue
 if case.endswith('_writer'):
  assert r['ok'] and not r['result']['accepted'] and r['result']['before']==r['result']['after'],case
 elif case.startswith(('unknown_r_','raw_H2_cross_molecule_','fact_')) or case.startswith('chiral_unknown_r_'):
  assert not r['ok'] and r['exception']=='ChemicalStateError',case
  if '_smiles_isomeric_' in case:assert r['detail']['kind']=='state_structure_unparseable' and r['detail']['reason']['kind']=='unregistered_cx_class'
  if '_structure_smiles_raw_' in case or case.startswith('chiral_unknown_r_'):assert r['detail']['kind']=='raw_structure_rejected' and r['detail']['reason']['kind']=='unregistered_cx_class'
 elif case.startswith('positive_') or case.startswith('chiral_clean_'):
  assert r['ok'] and r['result']['admission']==['expand',['R6:all_verified_no_conflict']],case
 elif case.startswith(('CN_only_honest_unknown_','archive_absent_axes_')):
  assert r['ok'] and r['result']['admission'][0]=='retain_conditional',case
  a=r['result']['audit'];c=next(x for x in a['checks'] if x['name']=='identity_fidelity');assert c['status']=='unknown',case
 elif case.startswith('retained_restore_'):
  assert r['ok'] and r['result']['same_identity'],case
 elif case.startswith('scope_'):
  assert r['ok'],case
  c=next(x for x in r['result']['audit']['checks'] if x['name']=='transformation_center')
  d=c['detail'];assert 'completion_license' in d and 'completion_license_scope' in d and d['product_coverage']=='full'
  if case=='scope_license_used':assert d['uncovered_product_refs'] and not d['unlicensed_uncovered_identities'] and r['result']['admission'][0]=='expand'
  else:assert not d['uncovered_product_refs'] and not d['uncovered_reactant_refs'] and r['result']['admission'][0]!='expand'
 else:raise AssertionError('unclassified case: '+case)
inv=json.loads((ROOT/'static_contract_inventory.json').read_text());assert inv['literal_grep']['returncode']==1 and not inv['literal_grep']['stdout'];assert inv['summary']['ChemicalState_calls']==2 and inv['summary']['audit_hypothesis_calls']==0 and inv['summary']['check_edit_against_donor_calls']==1 and inv['summary']['state_field_attribute_assignments']==0
print(json.dumps({'R7_original_records':len(old),'R8_first_consumer_records':len(new),'static_inventory':'validated','result':'all expected observations verified'},ensure_ascii=False))
