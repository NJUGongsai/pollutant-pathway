#!/usr/bin/env python3
from pathlib import Path
import ast,json,hashlib,re
OUT=Path(__file__).resolve().parents[1];src=OUT/'current_source/src/pathway_v43';base=OUT/'baseline_source/src/pathway_v43'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=sorted(src.rglob('*.py'));tests=sorted((OUT/'g01/repo/tests').glob('*.py'))
body='\n'.join(p.read_text() for p in files)
names=['donor_present','donor_consistency','_walk_conversions','same_cid','conversion_warnings','registered_missing','documented_absent','unrecorded']
raw_token_hits={n:[{'file':str(p.relative_to(src)),'lines':[i for i,l in enumerate(p.read_text().splitlines(),1) if re.search(r'\b'+re.escape(n)+r'\b',l)]} for p in files if re.search(r'\b'+re.escape(n)+r'\b',p.read_text())] for n in names}
funcdefs=[];calls=[];excepts=[];assess=[]
for p in files+tests:
 tree=ast.parse(p.read_text())
 for n in ast.walk(tree):
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in ['validate_frozen_search_limits','verify_event_attachment_content','build_substrate_profile','assess_conditions','assess_candidate_conditions','route_assessment']:
   funcdefs.append({'file':str(p.relative_to(OUT)),'name':n.name,'line':n.lineno,'end_lineno':n.end_lineno,'source':ast.get_source_segment(p.read_text(),n)})
   if n.name in ['assess_conditions','assess_candidate_conditions','route_assessment']:assess.append({'function':n.name,'line':n.lineno,'validate_calls':[a.lineno for a in ast.walk(n) if isinstance(a,ast.Call) and getattr(a.func,'id',None)=='validate_context_object']})
  if isinstance(n,ast.Call):
   name=getattr(n.func,'id',None) or getattr(n.func,'attr',None)
   if name in ['audit_hypothesis','center_evidence_from_donor_diagnostic','check_edit_against_donor','build_substrate_profile','validate_context_object']:
    calls.append({'file':str(p.relative_to(OUT)),'line':n.lineno,'name':name,'production_src':p in files})
  if isinstance(n,ast.ExceptHandler):
   typ=ast.unparse(n.type) if n.type else ''
   if 'AuditContractError' in typ:excepts.append({'file':str(p.relative_to(OUT)),'line':n.lineno,'type':typ})
refs={'chemstate.py':[(61,62),(180,226),(237,238),(266,266),(395,476),(629,649),(839,910),(913,929)],'hypothesis.py':[(136,173)],'audit.py':[(615,681),(727,770),(831,839),(888,1014),(1064,1116),(1131,1174),(1513,1571),(1660,1818),(1919,1930),(2553,2592),(2705,2707),(2742,2746),(2983,2993)],'path_context.py':[(706,837),(1117,1172),(1245,1278),(1386,1399),(1479,1548),(1942,1943),(2060,2091),(2112,2125),(2265,2274),(2327,2335),(2404,2418)],'store.py':[(595,643),(1988,2021)],'substrate_profile.py':[(71,107)],'profile.py':[(297,371)]}
excerpts={}
for f,ranges in refs.items():
 lines=(src/'pollutant'/f).read_text().splitlines();excerpts[f]=[{'start':a,'end':b,'exists':a>0 and b<=len(lines),'excerpt':'\n'.join(f'{i}: {lines[i-1]}' for i in range(a,b+1))} for a,b in ranges]
chemfiles=['chemstate.py','audit.py','path_context.py','hypothesis.py','events.py'];unchanged={n:{'current':sha(src/'pollutant'/n),'baseline':sha(base/'pollutant'/n),'equal':sha(src/'pollutant'/n)==sha(base/'pollutant'/n)} for n in chemfiles}
runtime={k:json.loads((OUT/(k+'_runtime/stdout.txt')).read_text()) for k in ['current','baseline']}
x={'scanned_src_file_count':len(files),'scanned_whitelisted_test_file_count':len(tests),'five_chemical_files_byte_unchanged':unchanged,'runner_byte_equal':sha(src/'workflow/runner.py')==sha(base/'workflow/runner.py'),'legacy_code_identity_equal':runtime['current']['legacy_code_identity']==runtime['baseline']['legacy_code_identity'],'raw_token_hits':raw_token_hits,'function_definitions':funcdefs,'calls':calls,'except_AuditContractError':excepts,'assess_validate_calls':assess,'source_line_excerpts':excerpts,'scope':'Full src plus safe G01 white-listed tests only; no unlisted scripts/tools/history/science inputs','actual_HEAD':'41d0cd55f3def050a62325f00235cf22da302d2e','actual_parent':'dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03'}
(OUT/'static_precision_inventory.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
assert all(d['equal'] for d in unchanged.values());assert x['runner_byte_equal'] and x['legacy_code_identity_equal'];assert not excepts;assert all(not r['validate_calls'] for r in assess)
print(json.dumps({'assertions':'complete','src':len(files),'white_listed_tests':len(tests),'chemistry_unchanged':True,'runner_legacy_identity_unchanged':True,'except_AuditContractError':len(excepts),'absent_token_counts':{n:len(v) for n,v in raw_token_hits.items()}},ensure_ascii=False))
