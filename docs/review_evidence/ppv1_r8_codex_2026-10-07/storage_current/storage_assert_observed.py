"""Assert R7 observed behavior, including the two still-open first-submit cases.
These assert current defects exist; this is not a post-fix acceptance suite.
"""
from pathlib import Path
import json,sys
rows=[json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
data={row['case']:row for row in rows}
assert len(rows)==16 and len(data)==16

def outcome(case,phase,expected):
 got=data[case][phase]['outcome']
 assert {k:got.get(k) for k in expected}==expected,(case,phase,got,expected)

def reject_zero(case,phase,kind):
 outcome(case,phase,{'error':'Ppv1LedgerCorrupt','kind':kind})
 assert data[case][phase]['zero_write'],case

for supply in ('none','prod_only','all'):
 case=f'first_existing_appearance_{supply}_valid'
 outcome(case,'first',{'created':True});outcome(case,'replay',{'created':False})
 assert data[case]['replay']['zero_write']
reject_zero('first_existing_appearance_none_corrupt','first','appearance_hash_corrupt')
for supply in ('prod_only','all'):
 case=f'first_existing_appearance_{supply}_corrupt'
 outcome(case,'first',{'created':True})
 assert not data[case]['first']['zero_write']
 for key,delta in (('events',1),('report_projections',1),('expansion_plans',1),('event_appearance_links',2)):
  f=data[case]['first'];assert f['after'][key]-f['before'][key]==delta,(case,key,f)
 reject_zero(case,'replay','appearance_hash_corrupt')
for field,kind in (('cn_identity','state_row_corrupt'),('schema_version','state_schema_corrupt'),('state_id','state_inner_id_corrupt')):
 reject_zero(f'first_reused_semantic_{field}','first',kind)
for mutation in ('none','reverse_manifest'):
 case='multi_occurrence_'+mutation
 outcome(case,'first',{'created':True});outcome(case,'replay',{'created':False})
 assert data[case]['replay']['zero_write'] and len(data[case]['links'])==3
 assert len({x['appearance_hash'] for x in data[case]['manifest_before']})==3
for mutation in ('manifest_A_only','manifest_and_row_A','link_A_only'):
 reject_zero('multi_occurrence_'+mutation,'replay','event_appearance_manifest_link_corrupt')
reject_zero('multi_occurrence_row_A_only','replay','event_appearance_manifest_entry_missing')
print('PASS: 15 independent storage cases match R7 observations; two supplied-SID corruption cases remain P1, not post-fix acceptance.')
