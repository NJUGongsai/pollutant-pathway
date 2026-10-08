#!/usr/bin/env python3
"""Read-only AST/text inventory over previously copied ordinary source/tests."""
import ast,collections,hashlib,json,re
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];SRC=OUT/'current_source/src';PKG=SRC/'pathway_v43';TESTS=OUT/'g01/repo/tests'
def dump(name,x):(OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def name(n):return n.id if isinstance(n,ast.Name) else n.attr if isinstance(n,ast.Attribute) else None
def names(n):return sorted({x.id for x in ast.walk(n) if isinstance(x,ast.Name)}) if n else ['bare']
raises=[];handlers=[];callers=[]
for root,tag in [(SRC,'src'),(TESTS,'tests')]:
    for p in sorted(root.rglob('*.py')):
        tree=ast.parse(p.read_text());relative=tag+'/'+str(p.relative_to(root));parents={c:n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
        for n in ast.walk(tree):
            if isinstance(n,ast.ExceptHandler) and 'AuditContractError' in names(n.type):handlers.append({'file':relative,'line':n.lineno,'handler':ast.unparse(n)})
            if isinstance(n,ast.Raise) and isinstance(n.exc,ast.Call) and name(n.exc.func)=='AuditContractError':
                chain=[];x=n
                while x in parents:x=parents[x];chain.append(x)
                broad=[];child=n
                for a in chain:
                    if isinstance(a,ast.Try) and child in a.body:
                        broad.extend({'try_line':a.lineno,'handler_line':h.lineno,'names':names(h.type)} for h in a.handlers
                                     if h.type is None or any(k in ['Exception','BaseException'] for k in names(h.type)))
                    child=a
                raises.append({'file':relative,'line':n.lineno,'inside_function':next((a.name for a in chain if isinstance(a,(ast.FunctionDef,ast.AsyncFunctionDef))),None),
                               'source':ast.unparse(n),'enclosing_broad_handlers':broad})
            if isinstance(n,ast.Call) and name(n.func) in ['audit_hypothesis','validate_context_object']:
                callers.append({'file':relative,'line':n.lineno,'call':name(n.func)})
pc=(PKG/'pollutant/path_context.py').read_text();pct=ast.parse(pc);af=(PKG/'pollutant/audit.py').read_text()
functions=[]
for n in ast.walk(pct):
    if isinstance(n,ast.FunctionDef) and n.name in ['assess_conditions','assess_candidate_conditions','route_assessment','derive_child_context','from_dict','validate_context_object']:
        calls=[{'name':name(x.func),'line':x.lineno} for x in ast.walk(n) if isinstance(x,ast.Call)]
        functions.append({'name':n.name,'line':n.lineno,'end_lineno':n.end_lineno,'validate_context_calls':[x for x in calls if x['name']=='validate_context_object'],
                          'validation_related_calls':[x for x in calls if x['name'] in ['_validate_phase_history_snapshot','_recompute_context_hash','_context_hash']]})
symbols=['donor_present','donor_element','donor_charge','donor_consistency','_walk_conversions','same_cid','graph_simple_iso','formal_iso',
         'conversion_warnings','donor_structure_charge_conflict','unknown_charge','missing_donor_structure','donor_ligand_context',
         'conversion_not_exhausted','donor_transition_not_found','donor_legacy_cn_match','unsupported_donor_detail','donor_profile_resolution_failed',
         'nn_transition_center','coverage_diagnostics','registered_missing','documented_absent','unrecorded','transformation_class']
texts=[(str(p.relative_to(SRC)),p.read_text()) for p in sorted(SRC.rglob('*.py'))]
symbol_counts={s:{'source_whole_token_count':sum(len(re.findall(r'(?<!\w)'+re.escape(s)+r'(?!\w)',body)) for _,body in texts),
                  'matches':[{'file':rel,'line':i,'source_line':line} for rel,body in texts for i,line in enumerate(body.splitlines(),1)
                             if re.search(r'(?<!\w)'+re.escape(s)+r'(?!\w)',line)]} for s in symbols}
auditlines=af.splitlines()
ranges=[(1866,1899),(1911,1930),(1988,1992),(2430,2430),(2553,2608),(2576,2599),(2906,2906),(2968,2968),(2983,2993),(1064,1066)]
cited_actual=[{'mimo_cited_range':[a,b],'actual_lines':[{'line':i,'text':auditlines[i-1]} for i in range(a,min(b,len(auditlines))+1)]} for a,b in ranges]
five={rel:{'current_sha256':hashlib.sha256((OUT/'current_source'/rel).read_bytes()).hexdigest(),
           'baseline_sha256':hashlib.sha256((OUT/'baseline_source'/rel).read_bytes()).hexdigest(),
           'equal':(OUT/'current_source'/rel).read_bytes()==(OUT/'baseline_source'/rel).read_bytes()}
      for rel in ['src/pathway_v43/pollutant/'+f+'.py' for f in ['chemstate','audit','path_context','hypothesis','events']]}
inventory={'actual_HEAD':'dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03','actual_baseline_HEAD':'9b78f4279cc6fa50b3b51c31a5c8e07abbeda207',
   'AuditContractError_raises':raises,'source_raise_distribution':dict(collections.Counter(x['file'] for x in raises if x['file'].startswith('src/'))),
   'except_AuditContractError_handlers':handlers,'calls':callers,'context_function_validation':functions,
   'mimo_named_symbols_actual_source':symbol_counts,'mimo_cited_audit_ranges_actual_content':cited_actual,'chemical_five_byte_parity':five,
   'source_files_scanned':len(texts),'test_files_scanned':len(list(TESTS.rglob('*.py'))),'scope':'copied src and allowlisted tests only; no assertion about uncopied scripts/tools'}
dump('static_precision_inventory.json',inventory)
baseline=json.loads((OUT/'baseline_r2/summary.json').read_text());test=(OUT/'baseline_source/tests/test_ppv1_s3a_rework_r2.py').read_text();testlines=test.splitlines();tt=ast.parse(test)
classification=[]
for row in baseline['cases']:
    item=dict(row);case_name=row['name'].split('[')[0];fn=next(n for n in tt.body if isinstance(n,ast.FunctionDef) and n.name==case_name)
    if row['state']=='passed':item.update(classification='legal_positive_control',all_test_body_completed=True)
    else:
        locations=re.findall(r'tests/test_ppv1_s3a_rework_r2.py:(\d+):',row['body']);line=int(locations[-1]) if locations else None
        kind='return_shape_failure' if row['message'].startswith('TypeError:') else 'earlier_normal_submit_rejection_kind_failure' if case_name=='test_b3_wrong_identity_event_rejected_before_consume' else 'behavior_assertion_failure'
        item.update(classification=kind,failure_source_line=line,failure_source_text=testlines[line-1] if line else None,
                    remaining_assertions_not_executed=[n.lineno for n in ast.walk(fn) if isinstance(n,ast.Assert) and line and n.lineno>line],
                    all_test_body_completed=False,
                    separate_supplemental_full_B3_capture=('baseline_extended/b3_'+row['name'].split('[')[-1].rstrip(']')+'.json') if case_name=='test_b3_wrong_identity_event_rejected_before_consume' else None)
    classification.append(item)
dump('baseline_case_classification.json',{'totals':baseline['totals'],'classification_counts':dict(collections.Counter(c['classification'] for c in classification)),
     'all_cases':classification,'bare_52_failures_not_claimed_52_completed_behavior_tests':True,'retryfoo_absent_from_r2_new_test_file':('retryfoo' not in test),
     'historical_updated_existing_2_fail_79_pass_or_655c7e8_not_executed_in_this_review':True})
observations=json.loads((OUT/'g01/pytest_observations.json').read_text())
dump('g01_exclusions_detail.json',{'skipped':observations['skip_reports'],
      'deselected':[{'nodeid':x,'reason':'explicitly excluded one export test presupposing absent evaluation scripts' if 'test_charge_fixture_cn_hits_raw_sb' in x else 'pytest marker slow excluded by -m not slow; no test body executed'} for x in observations['deselected_nodeids']],
      'observer_selected_nodeids_scope':'collection_modifyitems callback observations; final execution inventory uses JUnit and actual deselection hook, not ordering of selected list'})
print(json.dumps({'source_raise_distribution':inventory['source_raise_distribution'],'except_AuditContractError':handlers,
      'five_chemical_sources_unchanged':all(v['equal'] for v in five.values()),'baseline_classification_counts':dict(collections.Counter(c['classification'] for c in classification)),
      'nonzero_mimo_symbol_counts':{k:v['source_whole_token_count'] for k,v in symbol_counts.items() if v['source_whole_token_count']}}))
