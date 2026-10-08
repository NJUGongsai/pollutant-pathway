#!/usr/bin/env python3
"""Read completed suites and hashes only; never runs tests or probes."""
import json,hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
def load(n):return json.loads((OUT/n).read_text())
def dump(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
current=load('ppv1_corrected/summary.json');new=load('baseline_new_corrected/summary.json');old=load('baseline_updated_existing/summary.json');g01=load('g01_summary.json')
new_cases=[r for r in current['cases'] if r['classname']=='tests.test_ppv1_s3b_r2']
d={'actual_HEAD':'2bedfc060a9b19019ba44aa2a56dcacb88450c3b','parent':'c1211183c0874b12c5b5461845d3c61f0a84719c','final_ppv1':current['totals'],'ppv1_file_count':len(load('test_inputs.json')['PPV1_exact_files']),'current_new20_extracted_from_full_suite':new_cases,'current_new20_passed':sum(r['state']=='passed' for r in new_cases),'parent_new20':new['totals'],'parent_updated3':old['totals'],'parent_combined':{'failed':new['totals']['failures']+old['totals']['failures'],'passed':new['totals']['passed']+old['totals']['passed']},'g01':g01['totals'],'g01_independent_once':True,'new20_in_current_not_separately_rerun':True,'first_reviewer_environment_error_retained':load('environment_correction.json'),'legacy_and_production':{'legacy_all_bytes_equal':load('legacy_identity_and_core_integrity.json')['legacy_all_bytes_equal'],'legacy_aggregate':load('legacy_identity_and_core_integrity.json')['legacy_aggregate_current'],'production':load('legacy_identity_and_core_integrity.json')['production_chemistry_and_shared_cores']['src/pathway_v43/pollutant/production.py']}}
dump('independent_execution_results.json',d)
originals=load('input_hashes.json');records={}
for key,val in originals.items():
 if key.startswith('current/'):
  rel=key[len('current/'):];p=Path('/Volumes/CC/Enzyme_Agent/dependingv43')/rel;q=OUT/'current_source'/rel
  records[key]={'expected_sha256':val,'repository_after':sha(p),'copy_after':sha(q),'equal':val==sha(p)==sha(q)}
 elif key.startswith('baseline/'):
  p=OUT/'baseline_source'/key[len('baseline/'):]
  records[key]={'expected_sha256':val,'copy_after':sha(p),'equal':val==sha(p)}
dump('post_corrected_source_integrity.json',{'all_unchanged':all(r['equal'] for r in records.values()),'count':len(records),'files':records})
print(json.dumps({k:d[k] for k in ['final_ppv1','ppv1_file_count','parent_new20','parent_updated3','parent_combined','g01']},ensure_ascii=False))
