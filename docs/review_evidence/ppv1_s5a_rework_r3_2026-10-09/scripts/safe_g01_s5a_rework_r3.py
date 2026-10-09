#!/usr/bin/env python3
"""S5a rework r3 safe G01 (engineering-only isolation): same allowlist
discipline (lineage: R7 -> s3a_r4 -> s3b_r1/r2/r3 -> s4a_r1 -> s4b_r1 ->
s4_rework_r1/r2/r3 -> s5a -> s5a_rework_r1 -> s5a_rework_r2 ->
s5a_rework_r3). S5a rework r3 (Codex review R3
POLLUTANT_PATHWAY_S5A_CODEX_REVIEW_R3_2026-10-09 section 4 sole P1
S5A-05 production context first-consumption reference binding) adds
tests/test_ppv1_s5a_rework_r3.py (14 tests) and modifies (already
allowlisted, current bytes copied with fresh hashes; diff vs the r2 G01
input set disclosed and script-enforced):
src/pathway_v43/pollutant/{production,evaluation,preregistration,
profile}.py (search-production-2 / profile-23 registration + five P2
pre-freeze text syncs) and 5 test files (version literals, disclosed).
Baseline note: the r2 G01 actual numbers were 1706 passed / 9 skipped /
17 deselected (review-confirmed). Engineering-only expectation for this
round: 1706 + 14 new = 1720 expected passed minus the new frozen-integrity
guard skipping inside the isolation tree = 1719 passed / 10 skipped
(recorded, not enforced; the r2 lesson stands: every attempt uses a fresh
output directory and no log is ever deleted).

Same boundary discipline: path allowlist from the R7 manifests
(source/tests/configs/scripts/assets + ordinary sibling dependingv3/src
+ mirrored v43 reaction assets), never copies .git/reports/data/
evaluation/benchmark/gold/sealed runs/v4 -- fresh SHA-256 of the CURRENT
inputs (actual HEAD recorded, working-tree dirty state recorded), and
adds the R8/S3a/S3b/S3b-r2/S3b-r3/S4a/S4b/S4-rework/S5a/S5a-rework-r1/
S5a-rework-r2 inputs to the allowlist. Pinned environment and explicit
deselect of the one export case that presupposes absent evaluation
scripts match the R7/R8/S3a/S3b runs; pytest -m "not slow".

Writes only to --out (a fresh directory outside the repo); never writes
in the input repo or in any permanent evidence directory. Post-run:
re-verify every input SHA-256, list changed-vs-r1-G01 inputs, scan for
stray .pyc files (subprocess cache exceptions honestly recorded), and
disclose per-item absence (skips/deselects) from the junit output.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ALLOWED_TOP = {'pyproject.toml', 'LICENSE', 'LICENSE.md', 'MANIFEST.in'}
ALLOWED_DIRS = {'src', 'tests', 'configs', 'scripts', 'assets'}
EXCLUDED_CASE = ('tests/test_export_v3.py::'
                 'test_charge_fixture_cn_hits_raw_sb_misses_'
                 'neutralization_forbidden')
R8_NEW_TESTS = ['tests/test_ppv1_r8_chem.py',
                'tests/test_ppv1_r8_storage.py']
S3A_NEW_INPUTS = ['src/pathway_v43/pollutant/search.py',
                  'tests/test_ppv1_s3a_search.py',
                  'tests/test_ppv1_s3a_recover.py',
                  'tests/s3a_worker.py',
                  'tests/test_ppv1_s3a_rework_r2.py',
                  'tests/test_ppv1_s3a_rework_r3.py',
                  'tests/test_ppv1_s3a_rework_r4.py']
S3B_NEW_INPUTS = ['src/pathway_v43/pollutant/queue.py',
                  'src/pathway_v43/pollutant/model_protocol.py',
                  'src/pathway_v43/pollutant/production.py',
                  'src/pathway_v43/pollutant/runflow.py',
                  'src/pathway_v43/pollutant/profile.py',
                  'src/pathway_v43/workflow/runner.py',
                  'tests/test_ppv1_s3b_queue.py',
                  'tests/test_ppv1_s3b_model.py',
                  'tests/test_ppv1_s3b_production.py',
                  'tests/test_ppv1_s3b_runner.py',
                  'tests/s3b_worker.py',
                  'tests/test_ppv1_profile.py']
S3B_R2_NEW_INPUTS = ['tests/test_ppv1_s3b_r2.py']
S3B_R3_NEW_INPUTS = ['tests/test_ppv1_s3b_r3.py']
S4A_R1_NEW_INPUTS = ['src/pathway_v43/pollutant/endpoint.py',
                     'src/pathway_v43/pollutant/native_result.py',
                     'tests/test_ppv1_s4a_endpoint.py']
S4B_R1_NEW_INPUTS = ['src/pathway_v43/pollutant/native_export.py',
                     'src/pathway_v43/pollutant/v3_projection.py',
                     'tests/test_ppv1_s4b_export.py']
S4_REWORK_R1_NEW_INPUTS = ['tests/test_ppv1_s4_rework_r1.py']
S4_REWORK_R2_NEW_INPUTS = ['tests/test_ppv1_s4_rework_r2.py']
S4_REWORK_R3_NEW_INPUTS = ['tests/test_ppv1_s4_rework_r3.py']
S5A_NEW_INPUTS = ['src/pathway_v43/pollutant/reference_graph.py',
                  'src/pathway_v43/pollutant/evaluation.py',
                  'src/pathway_v43/pollutant/preregistration.py',
                  'tests/test_ppv1_s5a_schema.py',
                  'tests/test_ppv1_s5a_evaluator.py',
                  'tests/test_ppv1_s5a_isotope_regressions.py']
S5A_REWORK_R1_NEW_INPUTS = ['tests/test_ppv1_s5a_rework_r1.py']
S5A_REWORK_R2_NEW_INPUTS = ['tests/test_ppv1_s5a_rework_r2.py']
S5A_REWORK_R3_NEW_INPUTS = ['tests/test_ppv1_s5a_rework_r3.py']
# Inputs whose bytes legitimately changed this round vs the r2 G01 set
# (9: production binding guard + evaluation/preregistration/profile P2
# text syncs under search-production-2/profile-23, plus five test files'
# version literals).
S5A_REWORK_R3_CHANGED_VS_R2 = [
    'repo/src/pathway_v43/pollutant/production.py',
    'repo/src/pathway_v43/pollutant/evaluation.py',
    'repo/src/pathway_v43/pollutant/preregistration.py',
    'repo/src/pathway_v43/pollutant/profile.py',
    'repo/tests/test_ppv1_s5a_rework_r1.py',
    'repo/tests/test_ppv1_s5a_rework_r2.py',
    'repo/tests/test_ppv1_profile.py',
    'repo/tests/test_ppv1_s4b_export.py',
    'repo/tests/test_ppv1_s5a_schema.py']
# Inputs whose bytes legitimately changed this round vs the r1 G01 set
# (7: three pollutant sources registered under evaluation-3 + four test
# files' version literals / condition-policy text).
S5A_REWORK_R2_CHANGED_VS_R1 = [
    'repo/src/pathway_v43/pollutant/evaluation.py',
    'repo/src/pathway_v43/pollutant/preregistration.py',
    'repo/src/pathway_v43/pollutant/profile.py',
    'repo/tests/test_ppv1_s5a_rework_r1.py',
    'repo/tests/test_ppv1_profile.py',
    'repo/tests/test_ppv1_s5a_schema.py',
    'repo/tests/test_ppv1_s4b_export.py']


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_safe(name: str) -> Path:
    rel = Path(name)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:
        raise RuntimeError(f'Unsafe manifest relative path: {name!r}')
    return rel


def boundary_copy(source: Path, target: Path, boundary: Path) -> str:
    if not source.is_file():
        raise RuntimeError(f'Input file missing: {source}')
    real = source.resolve()
    bound = boundary.resolve()
    if real != bound and bound not in real.parents:
        raise RuntimeError(f'Input symlink escapes allowlisted root: {source}')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    digest = sha(target)
    if digest != sha(source):
        raise RuntimeError(f'Copy hash mismatch: {target}')
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path,
                        help='New directory; existing output is refused')
    parser.add_argument('--python', required=True,
                        help='depending43 Python executable')
    parser.add_argument('--r7-path-manifests', type=Path,
                        default=Path('/Volumes/CC/Enzyme_Agent/dependingv43'
                                     '/docs/review_evidence/'
                                     'ppv1_r7_codex_2026-10-07/'
                                     'storage_specialist'),
                        help='Directory holding the R7 input_hashes.json /'
                             ' g01_v3_source_addition_hashes.json used as'
                             ' PATH allowlists (hashes ignored, paths kept)')
    parser.add_argument('--r1-g01-inputs', type=Path,
                        default=Path('/Volumes/CC/Enzyme_Agent/dependingv43'
                                     '/docs/review_evidence/'
                                     'ppv1_s5a_rework_r2_2026-10-09/g01/'
                                     'input_sha256.json'),
                        help='r2 G01 input SHA set for changed-input diff')
    parser.add_argument('--v3-src', type=Path,
                        help='Ordinary v3 source only; defaults to sibling'
                             ' dependingv3/src')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    out = args.out.expanduser().resolve()
    if out.exists():
        raise RuntimeError(f'Output already exists; use fresh tmp: {out}')
    if repo == out or repo in out.parents or out in repo.parents:
        raise RuntimeError('Output must be outside and separate from repo')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                    cwd=repo, text=True).strip()
    dirty = subprocess.check_output(
        ['git', 'status', '--porcelain'], cwd=repo, text=True).strip()
    repo_paths = sorted(json.loads(
        (args.r7_path_manifests / 'input_hashes.json')
        .read_text(encoding='utf-8')).keys()) + R8_NEW_TESTS \
        + S3A_NEW_INPUTS + S3B_NEW_INPUTS + S3B_R2_NEW_INPUTS \
        + S3B_R3_NEW_INPUTS + S4A_R1_NEW_INPUTS + S4B_R1_NEW_INPUTS \
        + S4_REWORK_R1_NEW_INPUTS + S4_REWORK_R2_NEW_INPUTS \
        + S4_REWORK_R3_NEW_INPUTS + S5A_NEW_INPUTS \
        + S5A_REWORK_R1_NEW_INPUTS + S5A_REWORK_R2_NEW_INPUTS \
        + S5A_REWORK_R3_NEW_INPUTS
    v3_paths = sorted(json.loads(
        (args.r7_path_manifests / 'g01_v3_source_addition_hashes.json')
        .read_text(encoding='utf-8')).keys())
    dst = out / 'repo'
    out.mkdir()
    dst.mkdir()
    copied = {}
    for name in repo_paths:
        rel = relative_safe(name)
        if len(rel.parts) == 1:
            if name not in ALLOWED_TOP:
                raise RuntimeError(f'Non-allowlisted top-level input: {name}')
        elif rel.parts[0] not in ALLOWED_DIRS:
            raise RuntimeError(f'Non-allowlisted repository prefix: {name}')
        copied['repo/' + name] = boundary_copy(repo / rel, dst / rel, repo)
    v3_source = (args.v3_src or repo.parent / 'dependingv3' / 'src'
                 ).expanduser().resolve()
    for name in v3_paths:
        rel = relative_safe(name)
        if rel.parts[:2] == ('dependingv3', 'src'):
            tail = Path(*rel.parts[2:])
            copied[name] = boundary_copy(v3_source / tail, out / rel,
                                         v3_source)
        elif rel.parts[:2] == ('dependingv3', 'assets'):
            tail = Path(*rel.parts[2:])
            copied[name] = boundary_copy(
                dst / 'assets' / 'v3_reactions' / tail, out / rel,
                dst / 'assets' / 'v3_reactions')
        else:
            raise RuntimeError(f'Non-allowlisted v3 prefix: {name}')
    prohibited = [out / 'dependingv3' / 'evaluation', out / 'dependingv4',
                  dst / 'reports', dst / 'data', dst / 'evaluation',
                  dst / 'benchmark']
    if any(p.exists() for p in prohibited):
        raise RuntimeError('Prohibited input tree unexpectedly present')
    # diff vs r1 G01 inputs: which allowlisted bytes changed this round
    r2_inputs = json.loads(args.r1_g01_inputs.read_text(encoding='utf-8'))
    changed_vs_r2 = {
        'expected_changed': sorted(S5A_REWORK_R3_CHANGED_VS_R2),
        'observed_changed': sorted(
            k for k, v in r2_inputs.items() if k in copied
            and copied[k] != v),
        'new_inputs_vs_r2': sorted(
            k for k in copied if k not in r2_inputs),
        'missing_inputs_vs_r2': sorted(
            k for k in r2_inputs if k not in copied),
    }
    if changed_vs_r2['observed_changed'] != \
            changed_vs_r2['expected_changed']:
        raise RuntimeError(
            f'Changed-input set deviates from the disclosed r3 set: '
            f'{changed_vs_r2}')
    if changed_vs_r2['missing_inputs_vs_r2']:
        raise RuntimeError(
            f'Inputs dropped vs r2 G01: '
            f'{changed_vs_r2["missing_inputs_vs_r2"]}')
    command = [str(Path(args.python).expanduser().resolve()), '-B',
               '-m', 'pytest', '-p', 'no:cacheprovider', '-q', '-rs',
               '-m', 'not slow', '--deselect', EXCLUDED_CASE,
               '--junitxml', str(out / 'g01_junit.xml'), 'tests/']
    env = dict(os.environ)
    pinned_env = {
        'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONPATH': str(dst / 'src'),
        'BBD_DATA_ROOT': str(out / 'empty_external_data'),
        'V3_CODE_ROOT': str(out / 'dependingv3'),
        'V43_ASSET_ROOT': str(dst / 'assets'),
        'DEPENDING_V3_ROOT': str(out / 'dependingv3'),
    }
    env.update(pinned_env)
    metadata = {
        'actual_input_head': head,
        'working_tree_dirty_at_run': dirty,
        'repo': str(repo), 'copied_repo': str(dst),
        'ordinary_v3_source': str(v3_source),
        'path_allowlist_source': str(args.r7_path_manifests.resolve()),
        'hash_policy': 'fresh SHA-256 of current inputs recorded in '
                       'input_sha256.json (S5a rework r2 implementer '
                       'evidence; the R7/R8 reviewer scripts pin their own '
                       'hashes separately)',
        'r8_new_tests_added': R8_NEW_TESTS,
        's3a_new_inputs_added': S3A_NEW_INPUTS,
        's3b_new_inputs_added': S3B_NEW_INPUTS,
        's3b_r2_new_inputs_added': S3B_R2_NEW_INPUTS,
        's3b_r3_new_inputs_added': S3B_R3_NEW_INPUTS,
        's4a_r1_new_inputs_added': S4A_R1_NEW_INPUTS,
        's4b_r1_new_inputs_added': S4B_R1_NEW_INPUTS,
        's4_rework_r1_new_inputs_added': S4_REWORK_R1_NEW_INPUTS,
        's4_rework_r2_new_inputs_added': S4_REWORK_R2_NEW_INPUTS,
        's4_rework_r3_new_inputs_added': S4_REWORK_R3_NEW_INPUTS,
        's5a_new_inputs_added': S5A_NEW_INPUTS,
        's5a_rework_r1_new_inputs_added': S5A_REWORK_R1_NEW_INPUTS,
        's5a_rework_r2_new_inputs_added': S5A_REWORK_R2_NEW_INPUTS,
        's5a_rework_r3_new_inputs_added': S5A_REWORK_R3_NEW_INPUTS,
        'changed_inputs_vs_r2_g01': changed_vs_r2,
        'input_sha256': copied,
        'excluded_trees': [str(p) for p in prohibited],
        'ordinary_v3_assets_source': str(dst / 'assets' / 'v3_reactions'),
        'original_v3_assets_not_read': True,
        'pytest_command': command, 'cwd': str(dst),
        'pinned_environment': pinned_env,
        'explicit_deselected_case': EXCLUDED_CASE,
        'expected_skip_categories': {
            'real_evaluation_benchmark': 5,
            'missing_v4_parser_source': 1,
            'uncopied_phase_d_provenance_summary': 2,
            'r3_frozen_integrity_guard_docs_absent': 1},
        'slow_deselected_expected': 16,
        'extra_explicit_deselected': 1,
        'expected_passed_engineering_only': 1719,
        'baseline_note': 'r2 G01 actual 1706 passed / 9 skipped / 17 '
                         'deselected (review-confirmed); rework r3 adds '
                         '14 new tests (one frozen-integrity guard '
                         'skipifs inside the isolation tree, evidence-'
                         'level shasum instead) and 9 already-allowlisted '
                         'inputs change bytes (search-production-2 / '
                         'profile-23 + five P2 text syncs + test literal '
                         'sync, disclosed in changed_inputs_vs_'
                         'r2_g01)',
        'engineering_only_no_gold_benchmark_sealed_or_v4': True,
    }
    (out / 'preparation.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    (out / 'input_sha256.json').write_text(
        json.dumps(copied, indent=2) + '\n', encoding='utf-8')
    if args.prepare_only:
        print(json.dumps({'prepared': True, 'pytest_not_executed': True,
                          'out': str(out), 'command': command,
                          'n_inputs': len(copied)},
                         ensure_ascii=False))
        return 0
    start = time.monotonic()
    with (out / 'g01_safe.stdout.txt').open('w', encoding='utf-8') as stdout, \
         (out / 'g01_safe.stderr.txt').open('w', encoding='utf-8') as stderr:
        result = subprocess.run(command, cwd=dst, env=env,
                                stdout=stdout, stderr=stderr)
    output = (out / 'g01_safe.stdout.txt').read_text(encoding='utf-8')
    observed = {
        'exit_code': result.returncode,
        'elapsed_wall_seconds': round(time.monotonic() - start, 3),
        'command': command, 'cwd': str(dst),
        'stdout': 'g01_safe.stdout.txt', 'stderr': 'g01_safe.stderr.txt',
        'skip_lines': [line for line in output.splitlines()
                       if line.startswith('SKIPPED ')],
        'summary_lines': [line for line in output.splitlines()
                          if re.search(r'\d+ (?:passed|failed|skipped'
                                       r'|deselected)', line)],
        'stdout_sha256': sha(out / 'g01_safe.stdout.txt'),
        'stderr_sha256': sha(out / 'g01_safe.stderr.txt'),
    }
    (out / 'execution_result.json').write_text(
        json.dumps(observed, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    # ---- post-run verification: every input SHA re-hashed ----
    mismatches = []
    for name, digest in copied.items():
        rel = relative_safe(name)
        if sha(out / rel) != digest:
            mismatches.append(name)
    pycs = sorted(str(p.relative_to(out)) for p in out.rglob('*.pyc'))
    # per-item absence disclosure from junit (skips only; deselects are
    # command-level and listed in the command record)
    junit = (out / 'g01_junit.xml').read_text(encoding='utf-8')
    skipped_nodeids = sorted(set(re.findall(
        r'<testcase[^>]*name="([^"]+)"[^>]*time="[^"]*">\s*'
        r'<skipped[^>]*/?>', junit)))
    post = {
        'input_sha_mismatches': mismatches,
        'n_inputs_reverified': len(copied),
        'pyc_files_after_run': pycs,
        'pyc_note': ('test subprocesses may still emit a few isolated '
                     '.pyc files despite PYTHONDONTWRITEBYTECODE=1 -B; '
                     'honestly recorded, not reported as "no pyc"'),
        'junit_skipped_nodeids': skipped_nodeids,
    }
    (out / 'post_run_sha_result.json').write_text(
        json.dumps(post, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    print(json.dumps({'exit_code': observed['exit_code'],
                      'summary': observed['summary_lines'],
                      'sha_mismatches': mismatches,
                      'pyc_count': len(pycs),
                      'skipped_count': len(skipped_nodeids)},
                     ensure_ascii=False))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
