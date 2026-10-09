from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path

AFTER = Path('/private/tmp/ppv1_s5a_r3_mimo_r1_k4q7')
BEFORE = Path('/private/tmp/ppv1_s5a_r3_mimo_before_p39d739d')
DEST = Path('/private/tmp/ppv1_s5a_r3_evidence/mimo_cases')


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def copy(rel_src: Path, rel_dst: str) -> None:
    target = DEST / rel_dst
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(rel_src, target)


def main() -> None:
    # ---- run logs (argv recorded in meta; stdout/stderr/exit files) ----
    for name in ('probe_r3', 'cases45_r3', 'cases45_r3_observe'):
        for ext in ('stdout.txt', 'stderr.txt', 'exit.txt'):
            copy(AFTER / f'{name}.{ext}', f'after/{name}.{ext}')
    for name in ('probe_before', 'cases45_before_observe'):
        for ext in ('stdout.txt', 'stderr.txt', 'exit.txt'):
            copy(BEFORE / f'{name}.{ext}', f'before/{name}.{ext}')
    # ---- scripts (byte copies, hashed) ----
    copy(AFTER / 'package/scripts/probe.py', 'scripts/probe.py')
    copy(AFTER / 'package/scripts/r3_cases45.py',
         'scripts/r3_cases45.py')
    # ---- after results ----
    for rel in ('results/public_restore/control.json',
                'results/public_restore/old_id_resealed.json',
                'results/public_restore/new_id_resealed.json',
                'results/typed_restore.json',
                'results/old_identity_resealed_tamper.json',
                'results/checked_key_families.json',
                'results/species_fact_unit_narrow_semantics.json',
                'results/public_restore_summary.json',
                'results/r3_case4_checked_legal_old_address.json',
                'results/r3_case5_legal_new_address_chain.json'):
        copy(AFTER / 'package' / rel, f'after/{rel}')
    # ---- before results (observe mode + probe cases) ----
    for rel in ('results/public_restore/control.json',
                'results/public_restore/old_id_resealed.json',
                'results/public_restore/new_id_resealed.json',
                'results/public_restore_summary.json',
                'results/r3_case4_checked_legal_old_address.json'
                '.observe',
                'results/r3_case5_legal_new_address_chain.json.observe'):
        copy(BEFORE / 'package' / rel, f'before/{rel}')
    # ---- source guard ----
    repo = Path('/Volumes/CC/Enzyme_Agent/dependingv43')
    changed = ['src/pathway_v43/pollutant/production.py',
               'src/pathway_v43/pollutant/evaluation.py',
               'src/pathway_v43/pollutant/preregistration.py',
               'src/pathway_v43/pollutant/profile.py',
               'src/pathway_v43/pollutant/path_context.py',
               'src/pathway_v43/pollutant/runflow.py',
               'src/pathway_v43/pollutant/endpoint.py',
               'src/pathway_v43/pollutant/search.py',
               'src/pathway_v43/pollutant/store.py']
    guard = {
        'after_tree': str(AFTER), 'before_tree': str(BEFORE),
        'after_src_matches_repo_working_tree': {
            rel: sha(AFTER / 'iso' / rel) == sha(repo / rel)
            for rel in changed},
        'before_src_matches_parent_39d739d': {
            rel: sha(BEFORE / 'iso' / rel) == sha(
                Path('/private/tmp/ppv1_s5a_r3_evidence/'
                     'parent_39d739d') / rel)
            for rel in changed},
        'probe_py_byte_faithful': {
            'after': sha(AFTER / 'package/scripts/probe.py'),
            'before': sha(BEFORE / 'package/scripts/probe.py'),
            'review_original': sha(
                repo / 'docs/review_evidence/ppv1_s5a_codex_r3_2026-10-09'
                '/mimo/scripts/probe.py')},
        'cases45_script_identical_both_trees': sha(
            AFTER / 'package/scripts/r3_cases45.py') == sha(
            BEFORE / 'package/scripts/r3_cases45.py'),
        'v3_mirror': 'source-only copy of the ordinary sibling '
                     'dependingv3/src/depending code (no evaluation '
                     'assets, no reports, no .git metadata -> '
                     'v3_code_identity git_available=False, consistent '
                     'between start and resume of each case); the '
                     'original v3 evaluation assets were NOT read',
        'env': {'python': '/Users/cc/miniconda3/envs/'
                          'depending43/bin/python (3.11.16)',
                'flags': '-B, PYTHONDONTWRITEBYTECODE=1, pytest cache '
                         'off (PYTEST_ADDOPTS -p no:cacheprovider)',
                'cwd': '<scratch>/iso for every run',
                'PYTHONPATH': '<scratch>/iso/src'},
        'run_layout': 'each scratch tree: iso/{src,tests,pyproject,'
                      'assets} + package/scripts + dependingv3/src/'
                      'depending mirror; runs written to <scratch>/'
                      '{low_runs,public_runs,case4_runs,case5_runs}; '
                      'sqlite binaries and run dirs not sealed',
    }
    (DEST / 'source_guard.json').write_text(
        json.dumps(guard, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    ok_after = all(guard['after_src_matches_repo_working_tree'].values())
    ok_before = all(guard['before_src_matches_parent_39d739d'].values())
    print('after tree matches repo working tree:', ok_after)
    print('before tree matches parent:', ok_before)
    print('probe byte-faithful:',
          len({guard['probe_py_byte_faithful'][k] for k in
               ('after', 'before', 'review_original')}) == 1)
    print('files collected:', sum(
        1 for _ in DEST.rglob('*') if _.is_file()))


if __name__ == '__main__':
    main()
