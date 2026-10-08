"""Independent R8 replay of R7 frozen synthetic inputs into fresh tmp only."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent;REPO=Path('/Volumes/CC/Enzyme_Agent/dependingv43')
B=REPO/'docs/review_evidence/ppv1_r7_codex_2026-10-07';PY=sys.executable
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');commands=[]
def run(argv,cwd,stem,expected=0):
    so=P/(stem+'.stdout.txt');se=P/(stem+'.stderr.txt')
    with so.open('w') as o,se.open('w') as e:r=subprocess.run(argv,cwd=cwd,env=env,stdout=o,stderr=e)
    commands.append({'argv':argv,'cwd':str(cwd),'exit_code':r.returncode,'expected_exit_code':expected,'stdout':str(so.relative_to(P)),'stderr':str(se.relative_to(P))})
    (P/'root_commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
    assert r.returncode==expected,(stem,r.returncode,se.read_text())
    return so,se
actual=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
assert actual=='00e509a974b40a7c9779fcd35e53b16637a13d60'
# Freeze the controller itself into scratch before execution.
old=P/'r6_original';shutil.copytree(B/'r6_original',old)
run([PY,'-B',str(old/'reproduce.py'),'--repo',str(REPO),'--out',str(P/'r6_replay'),'--allow-head-change','--skip-pytest'],P,'r6_reproduce')
shutil.copy2(B/'assert_r7_replay.py',P/'assert_r7_replay.py')
shutil.copy2(B/'r6_selected_outcome_reference.json',P/'r6_selected_outcome_reference.json')
run([PY,'-B',str(P/'assert_r7_replay.py'),'--out',str(P/'r6_replay'),'--reference',str(P/'r6_selected_outcome_reference.json')],P,'r6_closed_groups_assert')
run([PY,'-B',str(P/'r6_replay/assert_observed.py')],P/'r6_replay','r6_old_gap_assert',expected=1)
assert "x['center']['status']=='verified'" in (P/'r6_old_gap_assert.stderr.txt').read_text()
for name in ['chemistry_current','conditions_current','storage_current']:
    lane=P/name;lane.mkdir();(lane/'src').symlink_to(P/'r6_replay/src',target_is_directory=True)
    for f in (B/name).glob('*.py'):shutil.copy2(f,lane/f.name)
    if (B/name/'tests').exists():shutil.copytree(B/name/'tests',lane/'tests')
chem=P/'chemistry_current'
so,se=run([PY,'-B',str(chem/'chemical_boundary_probe.py')],chem,'r7_chemical_replay',expected=1)
assert len(so.read_text().splitlines())==55
assert 'raw_structure_rejected' not in se.read_text() or 'ChemicalStateError' in se.read_text()
shutil.copy2(so,chem/'chemical_boundary_output.jsonl')
shutil.copy2(REPO/'docs/review_evidence/ppv1_r8_impl_2026-10-07/chem/r8_probe_completion.py',chem/'r8_probe_completion.py')
so,se=run([PY,'-B',str(chem/'r8_probe_completion.py')],chem,'r7_chemical_tail_completion')
assert len(so.read_text().splitlines())==3
run([PY,'-B',str(chem/'assert_chemical_observed.py')],chem,'r7_old_chemical_gap_assert',expected=1)
storage=P/'storage_current'
so,se=run([PY,'-B',str(storage/'storage_contract_probe.py'),str(P/'r6_replay')],storage,'r7_storage_replay')
shutil.copy2(so,storage/'storage_contract_probe.output.jsonl')
assert len(so.read_text().splitlines())==16
run([PY,'-B',str(storage/'storage_assert_observed.py'),str(storage/'storage_contract_probe.output.jsonl')],storage,'r7_old_storage_gap_assert',expected=1)
cond=P/'conditions_current'
so,se=run([PY,'-B',str(cond/'conditions_public_probe.py'),'--source',str(cond)],cond,'r7_conditions_replay')
assert len(so.read_text().splitlines())==17
shutil.copy2(so,cond/'conditions_public_probe.jsonl')
metadata={'actual_head':actual,'parent_acceptance_head':'858dd94c7c6c8fc387940242403d67b6b36b5313','python':sys.version,'commands':commands,'synthetic_only':True,'chemical_original_top_level_rows':55,'chemical_original_exit':'expected 1 at unwrapped from_dict chiral raw rejection, not all internal parts executed','chemical_tail_rows':3,'storage_cases':15,'condition_cases':16,'R6_closed_groups_assert':'passed','old_gap_assertions':'expected failures, first changed predicate only; later clauses not claimed run','copied_source_sha256':json.loads((P/'r6_replay/run_metadata.json').read_text())['copied_source_sha256']}
(P/'root_replay_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'actual_head':actual,'root_commands':len(commands),'R6_probes':12,'chemical_rows':55,'tail':3,'storage_cases':15,'condition_cases':16,'old_gap_assert_expected_failures':3},ensure_ascii=False))
