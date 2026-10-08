#!/usr/bin/env python3
"""Replay R7 safe G01 preparation/execution without real evaluation/v4 data.

Reads only exact SHA-256 allowlisted repo source/tests/config/scripts/ordinary
reaction assets, plus allowlisted ordinary sibling dependingv3/src files.
The two manifests default to sibling files from this evidence bundle.
Never copy .git, reports, data, evaluation, benchmark, gold, sealed runs or v4.
Run this script from a fresh output directory; it never writes in the input repo.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

EXPECTED_HEAD='858dd94c7c6c8fc387940242403d67b6b36b5313'
EXCLUDED_CASE='tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden'
ALLOWED_TOP={'pyproject.toml','LICENSE','LICENSE.md','MANIFEST.in'}
ALLOWED_DIRS={'src','tests','configs','scripts','assets'}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def relative_safe(name: str) -> Path:
    rel=Path(name)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:
        raise RuntimeError(f'Unsafe manifest relative path: {name!r}')
    return rel

def verified_copy(source: Path, target: Path, expected_hash: str, boundary: Path) -> None:
    if not source.is_file(): raise RuntimeError(f'Input file missing: {source}')
    real=source.resolve(); bound=boundary.resolve()
    if real != bound and bound not in real.parents:
        raise RuntimeError(f'Input symlink escapes allowlisted root: {source}')
    actual=sha(source)
    if actual != expected_hash:
        raise RuntimeError(f'Input hash drift: {source} ({actual} != {expected_hash})')
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    if sha(target) != expected_hash: raise RuntimeError(f'Copy hash mismatch: {target}')

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path,help='New directory; existing output is refused')
    parser.add_argument('--python',required=True,help='depending43 Python executable')
    parser.add_argument('--repo-input-hashes',type=Path,default=Path(__file__).resolve().with_name('input_hashes.json'))
    parser.add_argument('--v3-input-hashes',type=Path,default=Path(__file__).resolve().with_name('g01_v3_source_addition_hashes.json'))
    parser.add_argument('--v3-src',type=Path,help='Ordinary v3 source only; defaults to sibling dependingv3/src')
    parser.add_argument('--prepare-only',action='store_true',help='Copy/verify and log exact command, but do not execute pytest')
    args=parser.parse_args()
    repo=args.repo.expanduser().resolve();out=args.out.expanduser().resolve()
    if out.exists(): raise RuntimeError(f'Output already exists; use fresh tmp: {out}')
    if repo == out or repo in out.parents or out in repo.parents:
        raise RuntimeError('Output must be outside and separate from the input repo')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    if head != EXPECTED_HEAD: raise RuntimeError(f'R7 snapshot HEAD required: {head} != {EXPECTED_HEAD}')
    inputs=json.loads(args.repo_input_hashes.read_text(encoding='utf-8'))
    v3_inputs=json.loads(args.v3_input_hashes.read_text(encoding='utf-8'))
    dst=out/'repo';out.mkdir();dst.mkdir()
    copied={}
    for name,expected in sorted(inputs.items()):
        rel=relative_safe(name)
        if len(rel.parts)==1:
            if name not in ALLOWED_TOP: raise RuntimeError(f'Non-allowlisted top-level input: {name}')
        elif rel.parts[0] not in ALLOWED_DIRS:
            raise RuntimeError(f'Non-allowlisted repository prefix: {name}')
        verified_copy(repo/rel,dst/rel,expected,repo)
        copied['repo/'+name]=expected
    v3_source=(args.v3_src or repo.parent/'dependingv3'/'src').expanduser().resolve()
    for name,expected in sorted(v3_inputs.items()):
        rel=relative_safe(name)
        if rel.parts[:2]==('dependingv3','src'):
            tail=Path(*rel.parts[2:])
            verified_copy(v3_source/tail,out/rel,expected,v3_source)
        elif rel.parts[:2]==('dependingv3','assets'):
            tail=Path(*rel.parts[2:])
            # Physical mirror of copied ordinary v43 reaction assets. No original v3 assets read.
            verified_copy(dst/'assets'/'v3_reactions'/tail,out/rel,expected,dst/'assets'/'v3_reactions')
        else:
            raise RuntimeError(f'Non-allowlisted v3 prefix: {name}')
        copied[name]=expected
    prohibited=[out/'dependingv3'/'evaluation',out/'dependingv4',dst/'reports',dst/'data',dst/'evaluation']
    if any(p.exists() for p in prohibited): raise RuntimeError('Prohibited input tree unexpectedly present')
    command=[str(Path(args.python).expanduser().resolve()),'-B','-m','pytest','-p','no:cacheprovider','-q','-rs','-m','not slow','--deselect',EXCLUDED_CASE,'tests/']
    env=dict(os.environ)
    # Same roots resolved by defaults in the observed run, now explicit against inherited external overrides.
    pinned_env={'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(dst/'src'),'BBD_DATA_ROOT':str(out/'empty_external_data'),
                'V3_CODE_ROOT':str(out/'dependingv3'),'V43_ASSET_ROOT':str(dst/'assets'),'DEPENDING_V3_ROOT':str(out/'dependingv3')}
    env.update(pinned_env)
    metadata={'actual_input_head':head,'repo':str(repo),'copied_repo':str(dst),'ordinary_v3_source':str(v3_source),
              'file_allowlist_source':str(args.repo_input_hashes.resolve()),'v3_allowlist_source':str(args.v3_input_hashes.resolve()),
              'input_sha256':copied,'excluded_trees':[str(p) for p in prohibited],
              'ordinary_v3_assets_source':str(dst/'assets'/'v3_reactions'),'original_v3_assets_not_read':True,
              'pytest_command':command,'cwd':str(dst),'pinned_environment':pinned_env,
              'explicit_deselected_case':EXCLUDED_CASE,
              'expected_skip_categories':{'real_evaluation_benchmark':5,'missing_v4_parser_source':1,'uncopied_phase_d_provenance_summary':2},
              'slow_deselected_expected':16,'extra_explicit_deselected':1,
              'expected_observed_R7_result':'1110 passed, 8 skipped, 17 deselected; engineering only, not 1119 full result',
              'no_real_question_gold_sealed_run_evaluation_or_v4_copied':True}
    (out/'preparation.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'input_sha256.json').write_text(json.dumps(copied,indent=2)+'\n',encoding='utf-8')
    if args.prepare_only:
        print(json.dumps({'prepared':True,'pytest_not_executed':True,'out':str(out),'command':command},ensure_ascii=False))
        return 0
    start=time.monotonic()
    with (out/'g01_safe.stdout.txt').open('w',encoding='utf-8') as stdout, (out/'g01_safe.stderr.txt').open('w',encoding='utf-8') as stderr:
        result=subprocess.run(command,cwd=dst,env=env,stdout=stdout,stderr=stderr)
    output=(out/'g01_safe.stdout.txt').read_text(encoding='utf-8')
    observed={'exit_code':result.returncode,'elapsed_wall_seconds':round(time.monotonic()-start,3),
              'command':command,'cwd':str(dst),'stdout':'g01_safe.stdout.txt','stderr':'g01_safe.stderr.txt',
              'skip_lines':[line for line in output.splitlines() if line.startswith('SKIPPED ')],
              'summary_lines':[line for line in output.splitlines() if re.search(r'\d+ (?:passed|failed|skipped|deselected)',line)],
              'stdout_sha256':sha(out/'g01_safe.stdout.txt'),'stderr_sha256':sha(out/'g01_safe.stderr.txt')}
    (out/'execution_result.json').write_text(json.dumps(observed,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(observed,ensure_ascii=False))
    return result.returncode

if __name__=='__main__':
    raise SystemExit(main())
