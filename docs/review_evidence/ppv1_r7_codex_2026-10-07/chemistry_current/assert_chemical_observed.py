"""Assert R7 pinned observations, including the remaining raw restore defect.
This is review evidence, not a post-fix acceptance script.
"""
import json
from pathlib import Path
rows=[json.loads(x) for x in Path(__file__).with_name('chemical_boundary_output.jsonl').read_text().splitlines()]
r={x['case']:x for x in rows}
assert len(rows)==57

def admission(case):return r[case]['result']['admission'][0]
def checks(case):return {x['name']:x for x in r[case]['result']['audit']['checks']}
for k in ['canonical_substrate_unknown_flag','canonical_product_unknown_flag','canonical_uncovered_H2_unknown_flag']:
 assert admission('C1_'+k)=='retain_conditional'
 assert checks('C1_'+k)['transformation_center']['status']=='unknown'
 assert checks('C1_'+k)['identity_fidelity']['status']=='verified'
for k in ['raw_substrate_unknown_flag','raw_product_unknown_flag','raw_uncovered_H2_unknown_flag','raw_uncovered_H2_different_molecule']:
 assert admission('C1_'+k)=='expand'
 assert checks('C1_'+k)['identity_fidelity']['status']=='verified'
 assert checks('C1_'+k)['structure_parse_valence']['status']=='verified'
for case in ['clean_factory_public_chain','C1_restore_control_clean','C1_restore_control_same_graph_spelling','C1_restore_control_registered_metadata','C1_chiral_clean_control','C1_chiral_raw_unknown_flag']:
 assert admission(case)=='expand'
assert admission('C1_CN_only_honest_unknown_control')=='retain_conditional'
assert checks('C1_CN_only_honest_unknown_control')['identity_fidelity']['status']=='unknown'
for case in r:
 if case.startswith('store_first_use_'):
  q=r[case]['result'];assert q['accepted'] is False and q['before']==q['after'],case
for i in [0,5,6,7,8,9]:
 q=r['C3_retained_'+str(i)]['result'];assert q['guard_accepted'] and q['same_identity'] and q['different_from_bare'] and q['canonical_writer_stable'] and q['radical_multiset_equal']
for i in [1,2,3,4]:
 q=r['C3_retained_'+str(i)]['result'];assert not q['guard_accepted'] and q['exception']=='ChemicalStateError' and q['canonical_writer_stable']
for i in [0,1,2]:
 q=r['C3_removed_'+str(i)]['result'];assert q['guard_accepted'] and q['same_identity'] and not q['different_from_bare']
for co in ['CC=O','C1CO1','C=CO']:
 case='R6_01_'+co;assert admission(case)=='retain_conditional'
 c=checks(case)['transformation_center'];assert c['status']=='unknown' and c['detail']['product_coverage']=='partial_unchecked_transformation'
 assert c['detail']['unlicensed_uncovered_identities']==[co]
for field in ['current','mapped','plain','target']:
 q=r['C6_execution_success_'+field];assert not q['ok'] and q['exception']=='AuditContractError' and q['detail']['kind']=='raw_input_cx_class_unregistered'
 q=r['C6_execution_failure_'+field]['result']['diagnostic'];assert q['reaction_center_match'] is None and q['strict_target_match'] is None and q['legacy_cn_match'] is None and q['center_evidence']=={}
print('57 records checked: fixes/controls and R7 raw restore defect reproduced')
