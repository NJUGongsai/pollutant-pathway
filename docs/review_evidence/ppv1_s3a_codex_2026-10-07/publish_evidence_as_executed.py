#!/usr/bin/env python3
"""Publish only the authorized new S3a review document and evidence directory."""
import datetime,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path

SCRATCH=Path(__file__).resolve().parent
REPO=Path('/Volumes/CC/Enzyme_Agent/dependingv43')
REPORT=REPO/'docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_2026-10-07.md'
EVIDENCE=REPO/'docs/review_evidence/ppv1_s3a_codex_2026-10-07'
ROOT_FILES=('input_snapshot.json','request_probe.py','request_probe.run.json',
    'request_probe.stdout.jsonl','request_probe.stderr.txt','policy_probe.py',
    'policy_probe.run.json','policy_probe.stdout.jsonl','policy_probe.stderr.txt',
    'assert_root_observed.py','assert_root_observed.run.json',
    'assert_root_observed.stdout.jsonl','assert_root_observed.stderr.txt',
    'root_probe_reproduction.py','root_probe_reproduction.static_check.json')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=REPO)
def write_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n')

def verify_inputs(snapshot):
    failures=[]
    for name,expected in snapshot['input_sha256'].items():
        path=Path(name)
        if not path.is_file() or sha(path)!=expected:failures.append(name)
    head=git('rev-parse','HEAD').decode().strip()
    parent=git('rev-parse','HEAD^').decode().strip()
    diff=hashlib.sha256(git('diff','--binary')).hexdigest()
    assert not failures,('existing input changed',failures)
    assert head==snapshot['actual_head'] and parent==snapshot['parent_head']
    assert diff==snapshot['initial_tracked_diff_sha256'],'tracked diff changed'
    return {'head':head,'parent':parent,'input_count':len(snapshot['input_sha256']),
            'all_existing_input_hashes_unchanged':True,
            'tracked_diff_sha256':diff,'initial_tracked_diff_preserved':True,
            'git_status_short':git('status','--short').decode()}

def main():
    assert not REPORT.exists() and not EVIDENCE.exists(),'new output must not exist'
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    assert now.date().isoformat()=='2026-10-07','actual date differs; revise filenames'
    snapshot=json.loads((SCRATCH/'input_snapshot.json').read_text())
    before=verify_inputs(snapshot)
    assert before['git_status_short']==snapshot['initial_git_status'],'preexisting status changed'
    stage=SCRATCH/'evidence_stage'
    assert stage.is_dir()
    root_probes=stage/'root_probes';root_probes.mkdir()
    for name in ROOT_FILES:shutil.copy2(SCRATCH/name,root_probes/name)
    shutil.copy2(SCRATCH/'ROOT_PROBE_REPRODUCTION_README.md',root_probes/'README.md')
    shutil.copy2(SCRATCH/'EVIDENCE_README.md',stage/'README.md')
    shutil.copy2(SCRATCH/'package_assembly.json',stage/'package_assembly.json')
    shutil.copy2(SCRATCH/'verify_evidence.py',stage/'verify_evidence.py')
    shutil.copy2(Path(__file__),stage/'publish_evidence_as_executed.py')
    report_sha=sha(SCRATCH/'REPORT_DRAFT.md')
    (stage/'report.sha256').write_text(report_sha+'  '+str(REPORT)+'\n')
    metadata={
        'schema':'ppv1-s3a-codex-review-1','actual_head':before['head'],
        'parent_head':before['parent'],'actual_date':'2026-10-07',
        'timezone':'Asia/Shanghai','archive_started':now.isoformat(),
        'review_start_utc':'2026-10-07 12:10:04 UTC',
        'conclusion':'S3a_not_pass_S3b_not_released',
        'p1':['S3A-01','S3A-02','S3A-03','S3A-04','S3A-05'],
        'task_spec_sha256':snapshot['input_sha256'][str(REPO/'docs/POLLUTANT_PATHWAY_S3_IMPLEMENTATION_TASK_2026-10-07.md')],
        'report_sha256':report_sha,'report_path':str(REPORT),
        'evidence_path':str(EVIDENCE),
        'runtime':{'python':'3.11.16','rdkit':'2026.03.6','sqlite':'3.53.4',
            'python_path':'/Users/cc/miniconda3/envs/depending43/bin/python',
            'bytecode_disabled':True,'pytest_cache_disabled':True},
        'contracts':{'profile':'ppv1-profile-9','store':'ppv1-store-9',
            'search':'ppv1-search-1','limits':'ppv1-search-limits-3',
            'inherited_chemical_contracts':'-8 unchanged, see execution_specialist/runtime_environment/stdout.txt'},
        'independent_counts':{'ppv1':{'passed':594,'skipped':0,'failed':0},
            's3a_new':{'passed':58,'search':45,'recover':13},
            'parent_collection':{'errors':2,'new_cases_not_executed':58,'exit':2},
            'parent_profile':{'failed':2,'passed':21,'exit':1},
            'safe_g01':{'passed':1196,'skipped':8,'deselected':17,'failed':0},
            'search_synthetic_completed_cases':22,'inheritance_authority_cases':26,
            'inheritance_raw_submit_case':1,'root_request_cases':11,
            'root_request_metadata_rows':1,'root_request_footer_rows':0,
            'root_policy_cases':5,'chemistry_small_cases':15,'r8_literal_cx_cases':9},
        'provenance':{'execution':'this reviewer delegated engineering specialist, independent execution',
            'search':'this reviewer delegated public-chain specialist, independent synthetic probes',
            'inheritance':'this reviewer delegated integrity/chemistry specialist, independent probes',
            'root':'this reviewer public request/policy probes, not implementation evidence',
            'mimo':'read-only response, no execution attributed to mimo'},
        'safety':{'synthetic_only':True,'external_model_calls':0,'actual_network_requests':0,
            'real_provider_send_calls':0,'gold_question_sealed_run_access':False,
            'dependingv4_access':False,'git_push':False,'git_commit':False,
            'only_new_report_and_evidence_repository_writes':True,
            'source_tests_existing_docs_agents_unchanged':True},
        'reuse':'completed current-round executions reused during archive assembly; no suite/probe rerun',
        'limitations':['root request/policy original wall-clock elapsed was not separately captured; do not invent it',
            'new portable wrappers only syntax/safety checked, not runtime executed',
            'preparation errors and early stops retained; not counted as completed full matrices',
            'historical R8 full evidence suite not rerun; necessary current controls and full PPV1 executed',
            'no chemical performance or criteria-freeze certification'],
        'publication_command':{'argv':[sys.executable,'-B',str(Path(__file__))],
            'cwd':os.getcwd(),'env_overrides':{'PYTHONDONTWRITEBYTECODE':'1'},
            'operation':'new report/evidence only, no testing or probe execution'},
    }
    write_json(stage/'run_metadata.json',metadata)
    with REPORT.open('x') as out:out.write((SCRATCH/'REPORT_DRAFT.md').read_text())
    shutil.copytree(stage,EVIDENCE)
    after=verify_inputs(snapshot)
    expected=set(snapshot['initial_git_status'].splitlines())|{
        '?? docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_2026-10-07.md',
        '?? docs/review_evidence/ppv1_s3a_codex_2026-10-07/'}
    assert set(after['git_status_short'].splitlines())==expected,'unexpected status change'
    write_json(EVIDENCE/'workspace_integrity.json',{
        'before':before,'after':after,'new_paths':[str(REPORT),str(EVIDENCE)],
        'only_expected_new_untracked_paths':True,'existing_inputs_sha256_unchanged':True,
        'no_preexisting_file_rewritten_or_staged':True})
    for path in EVIDENCE.rglob('*'):
        assert not path.is_symlink(),'evidence symlink'
        assert path.suffix not in {'.sqlite','.db','.pyc','.pyo'},'unexpected binary/cache'
        assert '__pycache__' not in path.parts and '.pytest_cache' not in path.parts
    files={str(p.relative_to(EVIDENCE)):sha(p) for p in sorted(EVIDENCE.rglob('*')) if p.is_file()
           and p.relative_to(EVIDENCE).as_posix() not in {'manifest.json','SHA256SUMS'}}
    write_json(EVIDENCE/'manifest.json',{'schema':'ppv1-review-evidence-1','hash':'SHA-256',
        'actual_head':before['head'],'parent_head':before['parent'],
        'report_sha256':report_sha,'attachment_count':len(files),'attachments':files,
        'only_root_manifest_and_SHA256SUMS_excluded':True,'nested_manifests_included':True})
    (EVIDENCE/'SHA256SUMS').write_text(''.join(sha+'  '+name+'\n' for name,sha in files.items()))
    check=subprocess.run([sys.executable,'-B',str(EVIDENCE/'verify_evidence.py')],
                         text=True,capture_output=True,env=dict(os.environ)|{'PYTHONDONTWRITEBYTECODE':'1'})
    (SCRATCH/'final_archive_verify.stdout.json').write_text(check.stdout)
    (SCRATCH/'final_archive_verify.stderr.txt').write_text(check.stderr)
    assert check.returncode==0,(check.returncode,check.stderr)
    print(json.dumps({'report':str(REPORT),'evidence':str(EVIDENCE),'actual_head':before['head'],
                      'existing_inputs_unchanged':after['input_count'],
                      'attachment_count':len(files),'report_sha256':report_sha,
                      'verification':json.loads(check.stdout)},ensure_ascii=False))

if __name__=='__main__':main()
