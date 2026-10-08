"""Assert R7 flips of original R6 cases and preserved old controls.
Run on fresh replay output, never write permanent evidence.
"""
import argparse,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);ap.add_argument('--reference',required=True,type=Path)
a=ap.parse_args();P=a.out
def records(rel):return [json.loads(x) for x in (P/rel).read_text().splitlines()]
raw=records('admission_completion_probe.output.jsonl');assert len(raw)==14
r={x['probe']:x for x in raw}
for k in ['genuine_bound_control','genuine_hydrogenation_control','unmapped_radical_completion']:
    assert r[k]['center']['status']=='verified' and r[k]['admission'][0]=='expand',k
for k in ['old_two_sided_unchecked_control','one_sided_product_unchecked_isomer_half','one_sided_cosubstrate_unchecked_to_same_product']:
    assert r[k]['center']['status']=='unknown' and r[k]['admission'][0]=='retain_conditional',k
d=r['real_atom_addition_diagnostic'];assert d['validation']['ok'] and d['result']['ok'] and d['result']['product_smiles']=='CCCO'
for smi in ['CC=O','C1CO1','C=CO']:
    x=r['unmapped_organic_completion_'+smi]
    assert x['center']['status']=='unknown' and x['center']['detail']['product_coverage']=='partial_unchecked_transformation'
    assert x['admission'][0]=='retain_conditional' and smi in x['center']['detail']['unlicensed_uncovered_identities']
cx=records('chem/cx_boundary_probe.output.jsonl');assert len(cx)==9
c={x['case']:x for x in cx}
for x in c['cx_registered_head_comma_appended_unknown']['rows']:
    accepted=x['input'] in ['C[C@@H](N)C(=O)O |atomProp:0.note.hello|','CO |SgD:0:note:hello::::|']
    assert x['build']['accepted']==x['strict']['accepted']==accepted,x
for x in c['rdkit_writer_generated_registered_content_spaces']['rows']:
    assert x['build']['accepted'] and x['strict']['accepted'],x
assert c['donor_public_ethanol_clean']['admission'][0]=='expand'
for k in ['donor_public_ethanol_current_r','donor_public_ethanol_mapped_r','donor_public_ethanol_plain_r','donor_public_ethanol_target_r','donor_public_specified_stereo_current_r']:
    assert c[k]['exception_type']=='AuditContractError',k
conds=json.loads((P/'conditions/summary.json').read_text());assert len(conds)==10
for k in ['legal_historical_conflict_roundtrip','legal_historical_satisfied_roundtrip','genuine_unknown_historical_requirement_retained']:
    assert conds[k]['completed'],k
for k in set(conds)-{'legal_historical_conflict_roundtrip','legal_historical_satisfied_roundtrip','genuine_unknown_historical_requirement_retained'}:
    assert not conds[k]['completed'] and conds[k]['error_type']=='ConditionContractError',k
sraw=records('storage/r6_storage_boundary_probe.output.jsonl');assert len(sraw)==18
s={x.get('probe'):x for x in sraw}
for k,kind in [('existing_state_first_cn_identity','state_row_corrupt'),('existing_state_first_schema_version','state_schema_corrupt'),('existing_state_first_state_id','state_inner_id_corrupt'),('existing_appearance_bad_hash_first','appearance_hash_corrupt')]:
    for phase in ['first','replay']:
        x=s[k][phase];assert x['error']=='Ppv1LedgerCorrupt' and x['detail']['kind']==kind and x['counts_preserved'],(k,phase)
for k in ['existing_state_first_valid','existing_hypothesis_first_valid','ambiguous_first_explicit_state_control','multi_occurrence_manifest_normal']:
    assert s[k]['first']['result']['created'] and not s[k]['replay']['result']['created'] and s[k]['replay']['counts_preserved'],k
for k in ['existing_hypothesis_first_assumptions','existing_hypothesis_first_inner_id','existing_hypothesis_first_schema','existing_hypothesis_first_participant_entry','existing_hypothesis_self_consistent_bad_participant']:
    assert s[k]['first']['error']=='Ppv1LedgerCorrupt' and s[k]['first']['counts_preserved'],k
x=s['ambiguous_first_without_explicit_state_rejected']['first'];assert x['error']=='Ppv1SubmitContractError' and x['counts_preserved']
for suffix,kind in [('remove_manifest_A_only','event_appearance_manifest_link_corrupt'),('remove_row_A_only','event_appearance_manifest_entry_missing'),('remove_manifest_and_row_A','event_appearance_manifest_link_corrupt')]:
    x=s['multi_occurrence_manifest_'+suffix]
    assert x['normal_replay']['result']['created']==False
    x=x['replay'];assert x['error']=='Ppv1LedgerCorrupt' and x['detail']['kind']==kind and x['counts_preserved'],suffix
# Compare selected public outcomes in six pre-R6 replay lanes. Version strings,
# regenerated IDs, provenance path and new disclosure fields are not compared.
keys={'reaction_center_match','strict_target_match','center_match','product_coverage','created','counts_preserved','error','error_type','exception_type','admission','actual_equal','expected_equal','accepted'}
def project(value,path=''):
    result={}
    if isinstance(value,dict):
        for k,v in value.items():
            p=path+'/'+k
            if k in keys:
                # Error text was revised by the repaired CX guard. Preserve
                # rejection presence and separately recorded exception type;
                # do not treat changed explanatory wording as changed behavior.
                result[p]='message_present' if k=='error' and isinstance(v,str) and not v.isidentifier() else v
            else:result.update(project(v,p))
    elif isinstance(value,list):
        for i,v in enumerate(value):result.update(project(v,path+'/'+str(i)))
    return result
ref=json.loads(a.reference.read_text())
for rel,expected in ref.items():
    actual=[project(x) for x in records(rel)]
    assert actual==expected,rel
print('PASS: five original R6 groups flipped; legal controls and six older replay lanes retained. Compound rejected blocks are not claimed internally complete.')
