#!/usr/bin/env python3
"""S3a rework r2 safe G01 (S3A-01~05 rework): same allowlist discipline
as the S3a first-batch controller, adds the r2 regression test file
(tests/test_ppv1_s3a_rework_r2.py) to the copied inputs; profile.py and
the updated test files come from the R7 path allowlist with fresh hashes.
Engineering-only expectation: 1196 + 54 new r2 tests = 1250 passed /
8 skipped / 17 deselected (recorded, not enforced).

Adapts the R8 implementer's safe_g01_r8.py (which itself adapted the R7
reviewer's storage_specialist/safe_g01_reproduce.py) to the S3a working
tree. Same boundary discipline: path allowlist from the R7 manifests
(source/tests/configs/scripts/assets + ordinary sibling dependingv3/src +
mirrored v43 reaction assets), never copies .git/reports/data/evaluation/
benchmark/gold/sealed runs/v4 — fresh SHA-256 of the CURRENT inputs
(actual HEAD recorded, working-tree dirty state recorded), and adds the
R8 test files plus the new S3a inputs (pollutant/search.py, two S3a test
files, the s3a_worker crash driver) to the allowlist. Pinned environment
and explicit deselect of the one export case that presupposes absent
evaluation scripts match the R7/R8 runs; pytest -m "not slow".

Expected (engineering-only, zero real gold/benchmark access):
1138 + 58 new S3a tests = 1196 passed / 8 skipped / 17 deselected.

Writes only to --out (a fresh directory outside the repo); never writes
in the input repo or in this permanent evidence directory.
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
        + S3A_NEW_INPUTS
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
            # Physical mirror of copied ordinary v43 reaction assets; the
            # original v3 assets tree is never read.
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
    command = [str(Path(args.python).expanduser().resolve()), '-B',
               '-m', 'pytest', '-p', 'no:cacheprovider', '-q', '-rs',
               '-m', 'not slow', '--deselect', EXCLUDED_CASE, '--junitxml', str(out / 'g01_junit.xml'), 'tests/']
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
                       'input_sha256.json (S3a implementer evidence; the '
                       'R7/R8 reviewer scripts pin their own hashes '
                       'separately)',
        'r8_new_tests_added': R8_NEW_TESTS,
        's3a_new_inputs_added': S3A_NEW_INPUTS,
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
            'uncopied_phase_d_provenance_summary': 2},
        'slow_deselected_expected': 16,
        'extra_explicit_deselected': 1,
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
    print(json.dumps(observed, ensure_ascii=False))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
