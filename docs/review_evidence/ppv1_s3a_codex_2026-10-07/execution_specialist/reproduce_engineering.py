#!/usr/bin/env python3
"""Independent S3a engineering verification, fresh external output only.

No original v3 assets/evaluation, v4, reports, gold, questions or sealed run
are read. Current source and exact tests are copied; baseline is a sparse
detached worktree limited to src plus ordinary top-level metadata.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
import xml.etree.ElementTree as ET

HEAD = '9b78f4279cc6fa50b3b51c31a5c8e07abbeda207'
BASE = '00e509a974b40a7c9779fcd35e53b16637a13d60'
NEW = ['tests/test_ppv1_s3a_search.py', 'tests/test_ppv1_s3a_recover.py']
COPY_TESTS = NEW + ['tests/test_ppv1_profile.py', 'tests/s3a_worker.py']
META = ['pyproject.toml', 'LICENSE', 'LICENSE.md', 'MANIFEST.in']

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def dump(p, obj):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')

def junit_summary(p):
    r = ET.parse(p).getroot()
    suites = [r] if r.tag == 'testsuite' else list(r.findall('testsuite'))
    totals = {k: sum(int(s.get(k, 0)) for s in suites)
              for k in ('tests', 'errors', 'failures', 'skipped')}
    totals['passed'] = totals['tests']-totals['errors']-totals['failures']-totals['skipped']
    cases = []
    for c in r.iter('testcase'):
        state = next((x for x in ('failure','error','skipped') if c.find(x) is not None), 'passed')
        entry = {'classname': c.get('classname'), 'name': c.get('name'), 'state': state}
        if state != 'passed':
            n=c.find(state); entry['message']=n.get('message');entry['body']=n.text
        cases.append(entry)
    return {'totals':totals, 'cases':cases}

def copy_source(srcroot, target, hashes, tag):
    for p in sorted((srcroot/'src').rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p.suffix in ('.pyc','.pyo'):
            continue
        real=p.resolve()
        if srcroot.resolve() not in real.parents:
            raise RuntimeError(f'source symlink escape: {p}')
        rel=p.relative_to(srcroot); q=target/rel
        q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
        hashes[tag+'/'+str(rel)] = sha(q)
    for name in META:
        p=srcroot/name
        if p.is_file():
            shutil.copy2(p,target/name);hashes[tag+'/'+name]=sha(p)

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--repo',required=True,type=Path)
    a.add_argument('--out',required=True,type=Path)
    a.add_argument('--python',required=True,type=Path)
    args=a.parse_args();repo=args.repo.expanduser().resolve();out=args.out.expanduser().resolve()
    py=args.python.expanduser().resolve()
    if out.exists() or repo==out or repo in out.parents or out in repo.parents:
        raise RuntimeError('fresh output outside repo required')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    if head != HEAD: raise RuntimeError(f'HEAD mismatch {head}')
    out.mkdir(); commands=[]; hashes={};results={}
    baseenv=dict(os.environ);baseenv['PYTHONDONTWRITEBYTECODE']='1'
    baseenv['BBD_DATA_ROOT']=str(out/'empty_external_data')
    def run(name,cmd,cwd,env=None):
        folder=out/name;folder.mkdir(exist_ok=True)
        start=time.monotonic()
        with (folder/'stdout.txt').open('w') as so,(folder/'stderr.txt').open('w') as se:
            p=subprocess.run(cmd,cwd=cwd,env=env or baseenv,stdout=so,stderr=se)
        record={'name':name,'argv':[str(x) for x in cmd],'cwd':str(cwd),'exit_code':p.returncode,
                'elapsed_seconds':round(time.monotonic()-start,3),
                'environment':{k:(env or baseenv).get(k) for k in ('PYTHONDONTWRITEBYTECODE','PYTHONPATH','BBD_DATA_ROOT','V3_CODE_ROOT','V43_ASSET_ROOT','DEPENDING_V3_ROOT')},
                'stdout':name+'/stdout.txt','stderr':name+'/stderr.txt',
                'stdout_sha256':sha(folder/'stdout.txt'),'stderr_sha256':sha(folder/'stderr.txt')}
        commands.append(record);dump(out/'commands.json',commands);print(json.dumps(record),flush=True)
        return p.returncode
    dump(out/'initial_metadata.json',{'head':head,'parent':subprocess.check_output(['git','rev-parse','HEAD^'],cwd=repo,text=True).strip(),
           'status':subprocess.check_output(['git','status','--short'],cwd=repo,text=True),
           'discipline':'synthetic/off/scripted; source-copy vendor; no actual question/gold/run/v4 access; bytecode and pytest cache off'})
    current=out/'current_source';current.mkdir();copy_source(repo,current,hashes,'current')
    ppfiles=sorted(subprocess.check_output(['rg','--files','tests'],cwd=repo,text=True).splitlines())
    ppfiles=[x for x in ppfiles if Path(x).name.startswith('test_ppv1') and Path(x).suffix=='.py']
    for rel in ppfiles+['tests/s3a_worker.py']:
        p=repo/rel;q=current/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
        hashes['current/'+rel]=sha(p)
    env=baseenv|{'PYTHONPATH':str(current/'src')}
    for name,files in [('ppv1_full',ppfiles),('s3a_current',NEW)]:
        (out/name).mkdir()
        cmd=[str(py),'-B','-m','pytest','-p','no:cacheprovider','-q','-rs',
             '--junitxml',str(out/name/'junit.xml'),'--basetemp',str(out/(name+'_pytest_tmp'))]+files
        rc=run(name,cmd,current,env)
        results[name]=junit_summary(out/name/'junit.xml')|{'exit_code':rc}
        dump(out/name/'summary.json',results[name])
    wt=out/'baseline_worktree'
    added=False
    try:
        if run('worktree_create',['git','worktree','add','--detach','--no-checkout',str(wt),BASE],repo)!=0:
            raise RuntimeError('worktree create failed')
        added=True
        for name,cmd in [('sparse_init',['git','sparse-checkout','init','--cone']),
                         ('sparse_set',['git','sparse-checkout','set','src']),
                         ('baseline_checkout',['git','checkout','--detach',BASE])]:
            if run(name,cmd,wt)!=0:raise RuntimeError(name+' failed')
        base=out/'baseline_source';base.mkdir();copy_source(wt,base,hashes,'baseline')
        for rel in COPY_TESTS:
            p=repo/rel;q=base/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
            hashes['baseline/'+rel]=sha(p)
        dump(out/'test_byte_equality.json',{rel:{'repo':sha(repo/rel),'current':sha(current/rel),'baseline':sha(base/rel)} for rel in COPY_TESTS})
        env=baseenv|{'PYTHONPATH':str(base/'src')}
        for name,files in [('baseline_collection',NEW+['tests/test_ppv1_profile.py']),('baseline_profile',['tests/test_ppv1_profile.py'])]:
            (out/name).mkdir()
            cmd=[str(py),'-B','-m','pytest','-p','no:cacheprovider','-q','-rs',
                 '--junitxml',str(out/name/'junit.xml'),'--basetemp',str(out/(name+'_pytest_tmp'))]+files
            rc=run(name,cmd,base,env)
            results[name]=junit_summary(out/name/'junit.xml')|{'exit_code':rc}
            dump(out/name/'summary.json',results[name])
    finally:
        if added:
            rc=run('worktree_remove',['git','worktree','remove','--force',str(wt)],repo)
            dump(out/'worktree_cleanup.json',{'exit_code':rc,'worktree_exists':wt.exists(),
                 'worktree_list':subprocess.check_output(['git','worktree','list','--porcelain'],cwd=repo,text=True)})
    # Safe controller: exact supplied preparation and selection, with one
    # instrumentation-only addition of junit output in the external tree.
    supplied=repo/'docs/review_evidence/ppv1_s3a_impl_2026-10-07/s3a_r1/safe_g01_s3a.py'
    original=supplied.read_text();shutil.copy2(supplied,out/'safe_g01_s3a_original.py')
    needle="'-m', 'not slow', '--deselect', EXCLUDED_CASE, 'tests/']"
    replacement="'-m', 'not slow', '--deselect', EXCLUDED_CASE, '--junitxml', str(out / 'g01_junit.xml'), 'tests/']"
    if original.count(needle)!=1:raise RuntimeError('unexpected G01 command')
    controller=out/'safe_g01_s3a_instrumented.py';controller.write_text(original.replace(needle,replacement))
    dump(out/'g01_instrumentation.json',{'original_path':str(supplied),'original_sha256':sha(supplied),
         'instrumented_sha256':sha(controller),'change':'only append --junitxml in fresh output; preparation, allowlist, selection, expectations unchanged',
         'old_text':needle,'new_text':replacement})
    rc=run('g01_controller',[str(py),'-B',str(controller),'--repo',str(repo),'--out',str(out/'g01_safe_isolation'),'--python',str(py)],repo)
    g01=out/'g01_safe_isolation'
    results['g01']=junit_summary(g01/'g01_junit.xml')|{'exit_code':rc,'execution_result':json.loads((g01/'execution_result.json').read_text())}
    dump(out/'g01_summary.json',results['g01'])
    dump(out/'input_hashes.json',hashes)
    dump(out/'execution_summary.json',results)
    # Minimal runtime identity/schema/version capture in isolated source.
    code="import json,sys,sqlite3,rdkit;from pathway_v43.pollutant.profile import contract_versions,SEARCH_LIMITS_VERSION;print(json.dumps(dict(python=sys.version,rdkit=rdkit.__version__,sqlite=sqlite3.sqlite_version,contracts=contract_versions(),search_limits=SEARCH_LIMITS_VERSION),sort_keys=True))"
    run('runtime_environment',[str(py),'-B','-c',code],current,baseenv|{'PYTHONPATH':str(current/'src')})
    run('runner_diff',['git','diff',BASE+'..'+HEAD,'--','src/pathway_v43/workflow/runner.py'],repo)
    dump(out/'final_repo_metadata.json',{'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
         'status':subprocess.check_output(['git','status','--short'],cwd=repo,text=True)})
    good=(results['ppv1_full']['totals']=={'tests':594,'errors':0,'failures':0,'skipped':0,'passed':594}
          and results['s3a_current']['totals']['passed']==58
          and results['baseline_collection']['totals']['errors']==2
          and results['baseline_profile']['totals']['failures']==2
          and results['baseline_profile']['totals']['passed']==21
          and results['g01']['totals']['passed']==1196
          and results['g01']['totals']['skipped']==8
          and rc==0)
    dump(out/'assertion_result.json',{'passed':good,'no_fields_or_missing_tables_behavior_claimed':True,
         'baseline_new_cases_unexecuted':58,'baseline_collection_error_files':2,'baseline_behavior_red':2,'baseline_profile_positive':21})
    return 0 if good else 1

if __name__=='__main__':raise SystemExit(main())
