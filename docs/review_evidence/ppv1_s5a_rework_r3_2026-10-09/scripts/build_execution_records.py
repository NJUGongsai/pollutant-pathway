from __future__ import annotations
import hashlib
import json
import os
import re
from pathlib import Path

EVID = Path('/private/tmp/ppv1_s5a_r3_evidence')


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def execution_record(out_dir: Path, argv: list, cwd: str,
                     env: dict, exit_code: int) -> dict:
    stdout = out_dir / 'stdout.txt'
    text = stdout.read_text(encoding='utf-8')
    summary = [line for line in text.splitlines()
               if re.search(r'\d+ (?:passed|failed|skipped'
                            r'|deselected|error)', line)
               or line.startswith('EXIT=')]
    failed = [line.split('FAILED ')[1] for line in text.splitlines()
              if line.startswith('FAILED ')]
    errors = [line.split('ERROR ')[1] for line in text.splitlines()
              if line.startswith('ERROR ')]
    return {
        'command': argv, 'cwd': cwd,
        'pinned_environment': env,
        'exit_code': exit_code,
        'summary_lines': summary,
        'failed_nodeids': failed, 'error_nodeids': errors,
        'stdout_sha256': sha(stdout),
        'stderr_sha256': sha(out_dir / 'stderr.txt'),
        'junit_sha256': sha(out_dir / 'junit.xml'),
    }


def main() -> None:
    py = '/Users/cc/miniconda3/envs/depending43/bin/python'
    env = {'PYTHONDONTWRITEBYTECODE': '1',
           'PYTHONPATH': '/Volumes/CC/Enzyme_Agent/dependingv43/src',
           'PATH': os.environ.get('PATH', '/usr/bin:/bin')}
    files = (EVID / 'ppv1_file_list.txt').read_text().split()
    record = execution_record(
        EVID / 'ppv1',
        [py, '-B', '-m', 'pytest', '-p', 'no:cacheprovider', *files,
         '-q', '--junitxml', str(EVID / 'ppv1' / 'junit.xml')],
        '/Volumes/CC/Enzyme_Agent/dependingv43', env, 0)
    record['test_file_count'] = len(files)
    (EVID / 'ppv1' / 'execution_record.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')

    penv = {'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONPATH': str(EVID / 'parent_39d739d' / 'src'),
            'PATH': os.environ.get('PATH', '/usr/bin:/bin')}
    pfiles = ['tests/test_ppv1_s5a_rework_r3.py',
              'tests/test_ppv1_s5a_rework_r2.py',
              'tests/test_ppv1_s5a_rework_r1.py',
              'tests/test_ppv1_profile.py',
              'tests/test_ppv1_s4b_export.py',
              'tests/test_ppv1_s5a_schema.py']
    precord = execution_record(
        EVID / 'parent_baseline',
        [py, '-B', '-m', 'pytest', '-p', 'no:cacheprovider', *pfiles,
         '-q', '--junitxml', str(EVID / 'parent_baseline' / 'junit.xml')],
        str(EVID / 'parent_39d739d'), penv, 1)
    precord['test_file_count'] = len(pfiles)
    precord['worktree'] = {
        'head': '39d739d04f9b3e6e7ad78cb0ec5f1547ac54c962',
        'mode': 'detached git worktree, src/tests/pyproject same-byte '
                'as the r2 baseline commit; the six current new/updated '
                'test files copied over the parent test bytes (the '
                'current tests run against parent src)',
        'copied_test_files': pfiles}
    # ---- red classification (behavior / field / version / collection) ----
    behavior = [
        'tests/test_ppv1_s5a_rework_r3.py::'
        'test_s5a_r3_case3_self_consistent_new_id_old_address_rejected',
        'tests/test_ppv1_s5a_rework_r3.py::'
        'test_s5a_r3_case4_checked_legal_new_content_old_address_rejected',
        'tests/test_ppv1_s5a_rework_r3.py::'
        'test_s5a_r3_case3_public_new_id_old_address_rejected',
        'tests/test_ppv1_s5a_rework_r3.py::'
        'test_s5a_r3_case4_public_checked_legal_old_address_rejected',
        'tests/test_ppv1_s5a_rework_r3.py::'
        'test_s5a_r3_endpoint_entries_reuse_common_guard']
    field = [
        'tests/test_ppv1_s5a_rework_r3.py::'
        'test_s5a_r3_entry_matrix_static_guard',
        'tests/test_ppv1_s5a_rework_r3.py::'
        'test_s5a_r3_p2_text_sync_species_key_limitation']
    version = [
        'tests/test_ppv1_s5a_rework_r3.py::'
        'test_s5a_r3_contract_version_registration_and_frozen_integrity',
        'tests/test_ppv1_s5a_rework_r2.py::'
        'test_s5a_r2_contract_version_registration_and_frozen_integrity',
        'tests/test_ppv1_s5a_rework_r1.py::'
        'test_s5a_rework_contract_version_registration',
        'tests/test_ppv1_profile.py::test_ppv1_identity_block_contract'
        '_versions',
        'tests/test_ppv1_s4b_export.py::'
        'test_native_export_public_chain_files_and_manifest']
    observed = set(precord['failed_nodeids'])
    declared = set(behavior + field + version)
    precord['red_classification'] = {
        'behavior_red': behavior, 'field_red': field,
        'version_literal_red': version,
        'collection_red': [],
        'observed_equals_declared': observed == declared,
        'undeclared_observed': sorted(observed - declared),
        'declared_not_observed': sorted(declared - observed)}
    (EVID / 'parent_baseline' / 'execution_record.json').write_text(
        json.dumps(precord, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    print('ppv1 record:', record['summary_lines'][:2])
    print('parent record:', precord['summary_lines'][:2])
    print('red classification exact:',
          precord['red_classification']['observed_equals_declared'])

    # ---- frozen integrity (evidence level) ----
    repo = Path('/Volumes/CC/Enzyme_Agent/dependingv43')
    frozen = {
        'criteria_frozen': 'docs/POLLUTANT_PATHWAY_CRITERIA_FROZEN_V1_'
                           '2026-10-08.md',
        'freeze_record': 'docs/POLLUTANT_PATHWAY_CRITERIA_FREEZE_RECORD'
                         '_V1_2026-10-08.md',
        'path_context_frozen_judgment':
            'src/pathway_v43/pollutant/path_context.py',
    }
    expected = {
        'criteria_frozen': '7fd35aabdb4d2d5b67b0bf58693dab6f8765ad87'
                           '2efedf5f886503c4907064e4',
        'freeze_record': '6e046e2970a102c63e693cebb81f2564b5d79fea1b'
                         '6e7a776b0fc00c09662610',
        'path_context_frozen_judgment':
            '971ad00f42fc56915bad3724300759aa86552bf08199f8335c7f0286'
            'b40d588d',
    }
    out = {'note': 'S5a r3: frozen texts byte-identical to the parent '
                   'commit and the review-registered SHAs; path_context '
                   'frozen judgment untouched (the binding guard lives '
                   'in production.load_context consumption side)'}
    for key, rel in frozen.items():
        actual = sha(repo / rel)
        out[key] = {'sha256': actual, 'expected': expected[key],
                    'match': actual == expected[key]}
    (EVID / 'frozen_integrity.json').write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    print('frozen integrity all match:',
          all(v['match'] for k, v in out.items() if isinstance(v, dict)))


if __name__ == '__main__':
    main()
