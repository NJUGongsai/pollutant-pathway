#!/usr/bin/env python3
"""Only the unexecuted legal assembly controls, with existing required version preserved."""
from pathlib import Path
import copy,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'source/src'),str(ROOT/'source/tests')]
from pathway_v43.pollutant.profile import build_profile_identity_block,SEARCH_LIMITS_VERSION
from pathway_v43.pollutant.search import SearchLedger
from pathway_v43.pollutant.store import PollutantPathwayStore
D=ROOT/'legal_assembly_data';D.mkdir(exist_ok=False)
TABLES=['search_runs','search_actions','search_attempts','budget_reservations','model_requests','search_commit_records','events']
def rows(l):return {t:[dict(r) for r in l.conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in TABLES}
def cap(f):
 try:return {'accepted':True,'result':f()}
 except Exception as e:return {'accepted':False,'exception':type(e).__name__,'detail':getattr(e,'detail',{}),'message':str(e)}
for name,partial in [('legal_override',{'version':SEARCH_LIMITS_VERSION,'max_total_search_actions':0}),('legal_empty',{'version':SEARCH_LIMITS_VERSION})]:
 d=D/name;d.mkdir();s=PollutantPathwayStore(d/'run.sqlite');l=SearchLedger(s,None,name);p=build_profile_identity_block();p['search_limits']=partial;b=rows(l);first=cap(lambda:l.register_search_run(name,p));stored=l.search_policy_block(name);same=copy.deepcopy(p);same['search_limits']=copy.deepcopy(stored['search_limits']);mid=rows(l);repeat=cap(lambda:l.register_search_run(name,same));rec=cap(lambda:l.recover_run(name,policy_block=p));budget=cap(lambda:l.budget_snapshot(name));af=rows(l);ck={'first_accepted':first['accepted'],'complete_11_keys':len(stored['search_limits'])==11,'version_present':stored['search_limits'].get('version')==SEARCH_LIMITS_VERSION,'same_effective_accepted':repeat['accepted'],'repeat_recover_zero_writes':mid==af,'recover_partial_accepted':rec['accepted'],'budget_accepted':budget['accepted'],'total_zero_kept':budget['result']['run_level']['max_total_search_actions']['max']==0 if name=='legal_override' else True}
 print(json.dumps({'case':name,'group':'S3A-03','input':{'submitted_policy':p,'effective_full_policy':same},'before':b,'observed':{'first':first,'repeat':repeat,'recover':rec,'budget':budget},'after':af,'checks':ck,'contract_passed':all(ck.values()),'actual_network_requests':0},ensure_ascii=False,sort_keys=True),flush=True);s.close()
