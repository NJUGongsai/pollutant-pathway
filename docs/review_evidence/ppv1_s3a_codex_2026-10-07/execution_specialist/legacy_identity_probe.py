#!/usr/bin/env python3
"""Synthetic dynamic code_identity/refusal control, isolated src only."""
from __future__ import annotations
import argparse, ast, hashlib, json, os, subprocess, sys, time
from pathlib import Path

CODE = '''import json
from pathway_v43.storage.run_identity import code_identity,check_resume_identity,IdentityMismatch
from pathway_v43.workflow.runner import _refuse_undelivered_profile,RunError
x={"legacy_code_identity":code_identity("legacy_v43")}
x["legacy_refusal_return"]=_refuse_undelivered_profile("legacy_v43")
try:
    _refuse_undelivered_profile("pollutant_pathway_v1")
except RunError as e:
    x["ppv1_refusal"]={"type":type(e).__name__,"detail":e.detail,"message":str(e)}
else:
    raise AssertionError("PPV1 should be refused")
print(json.dumps(x,ensure_ascii=False,sort_keys=True))
'''

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-run',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--python',default=sys.executable,type=Path)
    a=ap.parse_args();out=a.out.resolve();run=a.source_run.resolve()
    if out.exists():raise RuntimeError('fresh output required')
    out.mkdir();records=[];cases={}
    for tag in ('baseline','current'):
        root=run/(tag+'_source');env=dict(os.environ)|{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root/'src'),'BBD_DATA_ROOT':str(out/'empty_external_data')}
        cmd=[str(a.python.resolve()),'-B','-c',CODE];start=time.monotonic()
        p=subprocess.run(cmd,cwd=root,env=env,text=True,capture_output=True)
        (out/(tag+'.stdout.txt')).write_text(p.stdout);(out/(tag+'.stderr.txt')).write_text(p.stderr)
        records.append({'case':tag,'argv':cmd,'cwd':str(root),'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-start,
                        'pinned_environment':{k:env[k] for k in ('PYTHONDONTWRITEBYTECODE','PYTHONPATH','BBD_DATA_ROOT')}})
        if p.returncode:raise RuntimeError(tag+' failed')
        cases[tag]=json.loads(p.stdout)
    b=cases['baseline']['legacy_code_identity'];c=cases['current']['legacy_code_identity']
    changed=[p for p in sorted(set(b['files'])|set(c['files'])) if b['files'].get(p)!=c['files'].get(p)]
    module_asts=[]
    for tag in ('baseline','current'):
        p=run/(tag+'_source/src/pathway_v43/workflow/runner.py')
        tree=ast.parse(p.read_text())
        tree.body=[n for n in tree.body if not isinstance(n,ast.FunctionDef) or n.name!='_refuse_undelivered_profile']
        module_asts.append(ast.dump(tree,include_attributes=False))
    env=dict(os.environ)|{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(run/'current_source/src')}
    checkcode='''import json
from pathway_v43.storage.run_identity import check_resume_identity,IdentityMismatch
old=json.loads(%r);new=json.loads(%r)
try:
    check_resume_identity({'profile':{'name':'legacy_v43'},'code_identity':old},{'profile':{'name':'legacy_v43'},'code_identity':new})
except IdentityMismatch as e:
    print(json.dumps({'type':type(e).__name__,'detail':e.detail},sort_keys=True))
else:raise AssertionError('changed identity should reject')
'''%(json.dumps(b),json.dumps(c))
    cmd=[str(a.python.resolve()),'-B','-c',checkcode];start=time.monotonic()
    p=subprocess.run(cmd,cwd=run/'current_source',env=env,text=True,capture_output=True)
    (out/'resume_compare.stdout.txt').write_text(p.stdout);(out/'resume_compare.stderr.txt').write_text(p.stderr)
    # full input code including hashes retained in commands.json, synthetic only.
    records.append({'case':'resume_compare','argv':cmd,'cwd':str(run/'current_source'),'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-start})
    if p.returncode:raise RuntimeError('identity compare failed')
    comparison=json.loads(p.stdout)
    assert changed==['pathway_v43/workflow/runner.py'],changed
    assert b['aggregate_sha256']!=c['aggregate_sha256']
    assert module_asts[0]==module_asts[1]
    assert cases['current']['legacy_refusal_return'] is None
    assert cases['current']['ppv1_refusal']['detail']=={'profile':'pollutant_pathway_v1','delivered_stages':'S0-S2,S3a-base','missing_stages':'S3b-S5'}
    assert list(comparison['detail']['differences'])==['code_identity']
    summary={'actual_current_head':'9b78f4279cc6fa50b3b51c31a5c8e07abbeda207','actual_baseline_head':'00e509a974b40a7c9779fcd35e53b16637a13d60',
             'legacy_changed_source_files':changed,'legacy_current_aggregate_sha256':c['aggregate_sha256'],'legacy_baseline_aggregate_sha256':b['aggregate_sha256'],
             'runner_AST_excluding_PPv1_refusal_function_unchanged':True,'same_legacy_refusal_return_None':True,
             'synthetic_cross_code_resume_refused':comparison,'case_outputs':cases,'all_assertions_passed':True,
             'scope':'Identity/branch evidence; no old real run loaded; same-version G01 controls separate; not scientific performance'}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (out/'commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='case_outputs'},ensure_ascii=False))
    return 0
if __name__=='__main__':raise SystemExit(main())
