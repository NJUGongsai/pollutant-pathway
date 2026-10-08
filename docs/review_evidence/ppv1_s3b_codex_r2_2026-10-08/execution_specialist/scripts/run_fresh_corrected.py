#!/usr/bin/env python3
"""Independent S3b execution. External fresh scratch only; no model/network."""
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, time, xml.etree.ElementTree as ET
from pathlib import Path

REPO=Path('/Volumes/CC/Enzyme_Agent/dependingv43')
OUT=Path(__file__).resolve().parents[1]
PY=Path('/Users/cc/miniconda3/envs/depending43/bin/python')
HEAD='2bedfc060a9b19019ba44aa2a56dcacb88450c3b'
BASE='c1211183c0874b12c5b5461845d3c61f0a84719c'
UPDATED=['tests/test_ppv1_profile.py','tests/test_ppv1_s3b_queue.py','tests/test_ppv1_s3b_model.py']
NEW_FILES=['tests/test_ppv1_s3b_r2.py']
WORKERS=['tests/s3a_worker.py','tests/s3b_worker.py']
META=['pyproject.toml','LICENSE','LICENSE.md','MANIFEST.in']
commands=[]; hashes={}; source_origins={}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()
def run(name,cmd,cwd,env):
    folder=OUT/name;folder.mkdir(parents=True,exist_ok=True)
    t=time.monotonic()
    with (folder/'stdout.txt').open('w') as so,(folder/'stderr.txt').open('w') as se:
        r=subprocess.run([str(c) for c in cmd],cwd=cwd,env=env,stdout=so,stderr=se)
    rec={'name':name,'argv':[str(c) for c in cmd],'cwd':str(cwd),'exit_code':r.returncode,
         'elapsed_seconds':round(time.monotonic()-t,6),'environment':{k:env.get(k) for k in
         ['PYTHONDONTWRITEBYTECODE','PYTHONPATH','BBD_DATA_ROOT','V3_CODE_ROOT','V43_ASSET_ROOT','DEPENDING_V3_ROOT']},
         'stdout':str((folder/'stdout.txt').relative_to(OUT)),
         'stderr':str((folder/'stderr.txt').relative_to(OUT)),
         'stdout_sha256':sha(folder/'stdout.txt'),'stderr_sha256':sha(folder/'stderr.txt')}
    commands.append(rec);dump(OUT/'commands.json',commands)
    print(json.dumps(rec,ensure_ascii=False),flush=True)
    return r.returncode
def copied(src,dst,key,origin=True):
    if not src.is_file():raise RuntimeError(f'Missing input {src}')
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    x=sha(src)
    if sha(dst)!=x:raise RuntimeError('Copy mismatch')
    hashes[key]=x
    if origin:source_origins[key]=str(src)
def source(root,dst,tag):
    dst.mkdir()
    for dirname in ['src','vendor']:
        folder=root/dirname
        if not folder.exists():continue
        for p in sorted(folder.rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts or p.suffix in ['.pyc','.pyo']:continue
            if root.resolve() not in p.resolve().parents:raise RuntimeError('Source symlink escape')
            rel=p.relative_to(root);copied(p,dst/rel,tag+'/'+str(rel),origin=(root==REPO))
    for name in META:
        if (root/name).is_file():copied(root/name,dst/name,tag+'/'+name,origin=(root==REPO))
def junit(p):
    r=ET.parse(p).getroot();ss=[r] if r.tag=='testsuite' else list(r.findall('testsuite'))
    totals={k:sum(int(s.get(k,0)) for s in ss) for k in ['tests','errors','failures','skipped']}
    totals['passed']=totals['tests']-totals['errors']-totals['failures']-totals['skipped']
    cases=[]
    for c in r.iter('testcase'):
        state=next((k for k in ['failure','error','skipped'] if c.find(k) is not None),'passed')
        row={'classname':c.get('classname'),'name':c.get('name'),'state':state}
        if state!='passed':
            n=c.find(state);row.update(message=n.get('message'),body=n.text)
        cases.append(row)
    return {'totals':totals,'cases':cases}

def main():
    if git('rev-parse','HEAD')!=HEAD:raise RuntimeError('HEAD drift')
    dump(OUT/'initial_metadata.json',{'actual_HEAD':git('rev-parse','HEAD'),'actual_parent':git('rev-parse','HEAD^'),
        'actual_branch':git('branch','--show-current'),'worktree_status':git('status','--short'),
        'source_boundary':'ordinary src/vendor/metadata, exact PPV1 test inputs; G01 explicit old path allowlists; no gold/question/evaluation/v4/sealed run; no external provider or model'})
    env=dict(os.environ)|{'PYTHONDONTWRITEBYTECODE':'1','BBD_DATA_ROOT':str(OUT/'empty_external_data'),
        'V3_CODE_ROOT':str(OUT/'dependingv3'),'DEPENDING_V3_ROOT':str(OUT/'dependingv3'),
        'V43_ASSET_ROOT':str(OUT/'absent_assets')}
    current=OUT/'current_source';source(REPO,current,'current')
    pp=sorted(str(p.relative_to(REPO)) for p in (REPO/'tests').glob('test_ppv1*.py'))
    for rel in pp+WORKERS:copied(REPO/rel,current/rel,'current/'+rel)
    dump(OUT/'test_inputs.json',{'PPV1_exact_files':pp,'workers':WORKERS,'updated_files':UPDATED,'new_files':NEW_FILES})
    cenv=env|{'PYTHONPATH':str(current/'src')}
    folder=OUT/'ppv1_full';folder.mkdir()
    cmd=[PY,'-B','-m','pytest','-p','no:cacheprovider','-q','-rs','--junitxml',folder/'junit.xml',
         '--basetemp',OUT/'ppv1_pytest_tmp',*pp]
    rc=run('ppv1_full',cmd,current,cenv)
    result=junit(folder/'junit.xml');result['exit_code']=rc;dump(folder/'summary.json',result)
    wt=OUT/'baseline_worktree';added=False
    try:
        if run('worktree_create',['git','worktree','add','--detach','--no-checkout',wt,BASE],REPO,env):raise RuntimeError('worktree add')
        added=True
        for name,cmd in [('worktree_sparse_init',['git','sparse-checkout','init','--cone']),
                         ('worktree_sparse_set',['git','sparse-checkout','set','src','vendor']),
                         ('worktree_checkout',['git','checkout','--detach',BASE])]:
            if run(name,cmd,wt,env):raise RuntimeError(name)
        dump(OUT/'baseline_actual_metadata.json',{'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=wt,text=True).strip(),
             'detached':subprocess.check_output(['git','branch','--show-current'],cwd=wt,text=True).strip()==''})
        base=OUT/'baseline_source';source(wt,base,'baseline')
        for rel in UPDATED+NEW_FILES+WORKERS:copied(REPO/rel,base/rel,'baseline/'+rel)
        dump(OUT/'same_byte_test_inputs.json',{rel:{'repository':sha(REPO/rel),'current':sha(current/rel),'baseline':sha(base/rel)}
             for rel in UPDATED+NEW_FILES+WORKERS})
        benv=env|{'PYTHONPATH':str(base/'src')}; bresults={}
        for label,files in [('updated_existing',UPDATED),('new_regressions',NEW_FILES)]:
            bf=OUT/('baseline_'+label);bf.mkdir()
            rc=run('baseline_'+label,[PY,'-B','-m','pytest','-p','no:cacheprovider','-q','-rs','--junitxml',bf/'junit.xml',
                   '--basetemp',OUT/('baseline_'+label+'_pytest_tmp'),*files],base,benv)
            parsed=junit(bf/'junit.xml');parsed['exit_code']=rc;dump(bf/'summary.json',parsed);bresults[label]=parsed
        # Identity uses exact copied source and ordinary code only; actual version/schema separately recorded.
        for tag,root,renv in [('current',current,cenv),('baseline',base,benv)]:
            code="import json,sys,sqlite3,rdkit;from pathlib import Path;from pathway_v43.pollutant.profile import contract_versions,SEARCH_LIMITS_VERSION;from pathway_v43.pollutant.store import PollutantPathwayStore;from pathway_v43.storage.run_identity import code_identity;s=PollutantPathwayStore(sys.argv[1]);x={'python':sys.version,'rdkit':rdkit.__version__,'sqlite':sqlite3.sqlite_version,'contracts':contract_versions(),'search_limits':SEARCH_LIMITS_VERSION,'actual_db_meta':[dict(r) for r in s.conn.execute('SELECT * FROM meta')],'actual_schema':[dict(r) for r in s.conn.execute(\"SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name\")],'legacy_code_identity':code_identity('legacy_v43')};print(json.dumps(x,ensure_ascii=False,sort_keys=True));s.close()"
            if run(tag+'_runtime',[PY,'-B','-c',code,OUT/(tag+'_runtime')/'synthetic.sqlite'],root,renv):raise RuntimeError('runtime')
    finally:
        if added:
            rc=run('worktree_remove',['git','worktree','remove','--force',wt],REPO,env)
            dump(OUT/'worktree_cleanup.json',{'exit_code':rc,'worktree_exists':wt.exists(),'worktree_list':git('worktree','list','--porcelain')})
    # Supplied controller is copied into scratch before execution, instrumented only to observe pytest deselection/skip nodeids.
    supplied=OUT/'scripts/safe_g01_supplied.py';body=supplied.read_text()
    observer="""import json,os\nfrom pathlib import Path\nresult={'selected_nodeids':[],'deselected_nodeids':[],'skip_reports':[]}\ndef pytest_collection_modifyitems(session,config,items):\n    result['selected_nodeids']=[i.nodeid for i in items]\ndef pytest_deselected(items):\n    result['deselected_nodeids'].extend(i.nodeid for i in items)\ndef pytest_runtest_logreport(report):\n    if report.skipped:result['skip_reports'].append({'nodeid':report.nodeid,'when':report.when,'reason':str(report.longrepr)})\ndef pytest_sessionfinish(session,exitstatus):\n    result['exitstatus']=int(exitstatus)\n    Path(os.environ['REVIEW_OBSERVATION']).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\\n')\n"""
    observer_path=OUT/'scripts/review_observer.py';observer_path.write_text(observer)
    needle="'-m', 'pytest', '-p', 'no:cacheprovider', '-q', '-rs',"
    replacement="'-m', 'pytest', '-p', 'no:cacheprovider', '-p', 'review_observer', '-q', '-rs',"
    assert body.count(needle)==1
    body=body.replace(needle,replacement)
    needle="'PYTHONPATH': str(dst / 'src'),"
    replacement="'PYTHONPATH': str(dst / 'src') + os.pathsep + str(Path(__file__).resolve().parent),\n        'REVIEW_OBSERVATION': str(out / 'pytest_observations.json'),"
    assert body.count(needle)==1;body=body.replace(needle,replacement)
    ctrl=OUT/'scripts/safe_g01_instrumented.py';ctrl.write_text(body)
    dump(OUT/'g01_instrumentation.json',{'supplied_sha256':sha(supplied),'instrumented_sha256':sha(ctrl),'observer_sha256':sha(observer_path),
         'only_changes':'adds passive pytest reporting plugin and its external Python path; no test inputs, expected behavior, preparation or selection changed',
         'recorded_Historical_whitelist_hashes_not_treated_as_current':True})
    rc=run('g01_controller',[PY,'-B',ctrl,'--repo',REPO,'--out',OUT/'g01','--python',PY,
           '--r7-path-manifests',OUT/'allowlists'],REPO,env)
    gr=junit(OUT/'g01/g01_junit.xml');gr['exit_code']=rc;dump(OUT/'g01_summary.json',gr)
    prep=json.loads((OUT/'g01/preparation.json').read_text());ginputs=json.loads((OUT/'g01/input_sha256.json').read_text())
    gafter={};goriginal_after={}
    for key,value in ginputs.items():
        gafter[key]=sha(OUT/'g01'/key)
        if key.startswith('repo/'):origin=REPO/key[5:]
        elif key.startswith('dependingv3/src/'):origin=REPO.parent/key
        elif key.startswith('dependingv3/assets/'):origin=REPO/'assets/v3_reactions'/key[len('dependingv3/assets/'):]
        else:raise RuntimeError('Unexpected G01 origin')
        goriginal_after[key]=sha(origin)
    dump(OUT/'g01_input_integrity_after.json',{'input_count':len(ginputs),'copy_hashes_after':gafter,'ordinary_original_hashes_after':goriginal_after,
         'all_copied_inputs_unchanged':gafter==ginputs,'all_allowed_original_inputs_unchanged':goriginal_after==ginputs,
         'ordinary_v3_src_count':sum(k.startswith('dependingv3/src/') for k in ginputs),'mirrored_ordinary_asset_count':sum(k.startswith('dependingv3/assets/') for k in ginputs),
         'repository_count':sum(k.startswith('repo/') for k in ginputs),'actual_preparation_HEAD':prep['actual_input_head']})
    after={key:sha(path) for key,path in source_origins.items()}
    dump(OUT/'input_hashes.json',hashes);dump(OUT/'input_integrity_after.json',{'original_hashes_after':after,'all_originals_unchanged':all(hashes[k]==v for k,v in after.items())})
    dump(OUT/'final_repo_metadata.json',{'HEAD':git('rev-parse','HEAD'),'status':git('status','--short')})
    dump(OUT/'execution_summary.json',{'ppv1':result['totals'],'baseline_updated_existing':bresults['updated_existing']['totals'],'baseline_new_regressions':bresults['new_regressions']['totals'],'g01':gr['totals'],
         'exact_G01_deselections':json.loads((OUT/'g01/pytest_observations.json').read_text())['deselected_nodeids'],
         'no_existing_implementation_run_results_reused':True})
    print(json.dumps({'ppv1':result['totals'],'baseline_updated_existing':bresults['updated_existing']['totals'],'baseline_new_regressions':bresults['new_regressions']['totals'],'g01':gr['totals']}),flush=True)

if __name__=='__main__':main()
