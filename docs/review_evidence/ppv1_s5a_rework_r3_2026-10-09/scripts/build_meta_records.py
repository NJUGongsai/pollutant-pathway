from __future__ import annotations
import json
from pathlib import Path

EVID = Path('/private/tmp/ppv1_s5a_r3_evidence')


def main() -> None:
    py = ('/Users/cc/miniconda3/envs/'
          'depending43/bin/python')
    common_env = {
        'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONPATH': '<scratch>/iso/src',
        'PYTEST_ADDOPTS': '-p no:cacheprovider',
        'CONDA_PREFIX': '/Users/cc/miniconda3/envs/depending43',
    }
    runs = [
        {'name': 'probe_r3 (after tree, review probe byte-faithful)',
         'scratch': '/private/tmp/ppv1_s5a_r3_mimo_r1_k4q7',
         'argv': [py, '-B',
                  '/private/tmp/ppv1_s5a_r3_mimo_r1_k4q7/package/'
                  'scripts/probe.py'],
         'cwd': '<scratch>/iso', 'env': common_env,
         'exit_code': 0,
         'note': 'cases 1-3 use the review R3 real public inputs; '
                 'case 3 (new_id_resealed) flips from accepted to '
                 'binding-mismatch rejection under r3'},
        {'name': 'cases45_r3 (after tree, contract mode with asserts)',
         'scratch': '/private/tmp/ppv1_s5a_r3_mimo_r1_k4q7',
         'argv': [py, '-B',
                  '/private/tmp/ppv1_s5a_r3_mimo_r1_k4q7/package/'
                  'scripts/r3_cases45.py'],
         'cwd': '<scratch>/iso', 'env': common_env,
         'exit_code': 0,
         'note': 'r3-constructed cases 4/5, contract asserts enforced'},
        {'name': 'cases45_r3_observe (after tree, OBSERVE=1)',
         'scratch': '/private/tmp/ppv1_s5a_r3_mimo_r1_k4q7',
         'argv': [py, '-B',
                  '/private/tmp/ppv1_s5a_r3_mimo_r1_k4q7/package/'
                  'scripts/r3_cases45.py'],
         'cwd': '<scratch>/iso',
         'env': {**common_env, 'OBSERVE': '1'},
         'exit_code': 0,
         'note': 'same script with asserts skipped for the observation '
                 'record; run dirs wiped between invocations '
                 '(ArtifactStore refuses different-content rewrites)'},
        {'name': 'probe_before (parent 39d739d bytes)',
         'scratch': '/private/tmp/ppv1_s5a_r3_mimo_before_p39d739d',
         'argv': [py, '-B',
                  '/private/tmp/ppv1_s5a_r3_mimo_before_p39d739d/'
                  'package/scripts/probe.py'],
         'cwd': '<scratch>/iso', 'env': common_env,
         'exit_code': 0,
         'note': 'before-tree run reproducing the review P1: case 3 '
                 'accepted, events 0->1'},
        {'name': 'cases45_before_observe (parent bytes, OBSERVE=1)',
         'scratch': '/private/tmp/ppv1_s5a_r3_mimo_before_p39d739d',
         'argv': [py, '-B',
                  '/private/tmp/ppv1_s5a_r3_mimo_before_p39d739d/'
                  'package/scripts/r3_cases45.py'],
         'cwd': '<scratch>/iso',
         'env': {**common_env, 'OBSERVE': '1'},
         'exit_code': 0,
         'note': 'before-tree case 4 accepted (load + public resume '
                 'succeed, events 1); case 5 positive control green'},
    ]
    (EVID / 'mimo_cases' / 'run_meta.json').write_text(
        json.dumps({'runs': runs}, ensure_ascii=False, indent=2)
        + '\n', encoding='utf-8')

    g01 = {
        'round': 'S5a rework r3 G01 safety isolation',
        'incidents': [],
        'attempts': [
            {'attempt': 1,
             'out_dir': 'attempt1/',
             'exit_code': 0,
             'result': ('1719 passed / 10 skipped / 17 deselected, '
                        'exit 0, 306 allowlisted inputs, all input '
                        'SHAs reverified unchanged after the run, 7 '
                        'isolated pyc files honestly recorded'),
             'logs': ('full stdout/stderr/junit/preparation/input '
                      'SHA/post-run verification preserved inside '
                      'attempt1/; the console capture is '
                      'attempt1_console.txt; nothing was deleted '
                      'before or after the run')},
        ],
        'first_run_success': True,
        'history_note': (
            'The r2 delivery lost its first G01 run stdout (registered '
            'as a process lesson in the r2 evidence g01/incidents.json '
            'and accepted by the R3 review as a P2 process defect, not '
            'a product failure). This round applies the lesson: every '
            'attempt writes to its own fresh output root and no log is '
            'removed; no incident occurred this round.'),
        'scheduling_failures': 'none this round',
        'unexecuted_segments': [
            'The review R3 mimo session plan of a checked-legal-new-'
            'content public control (its case 4) was platform-blocked '
            'and NOT executed by the review; this round constructed and '
            'executed its own case 4/5 controls and labels them '
            'r3-constructed, never review-executed.',
            "r2's conditions/identity/write-boundary specialty probes "
            'and the 17-bucket business probe were NOT rerun this round '
            '(S5A-02 is closed per review R3 section 3; this round '
            'scope is S5A-05 only). Their behavior stays guarded by '
            'the r1/r2 regression suites inside the 1119-passed PPV1 '
            'full run and the 1719-passed G01 isolation run.',
            'A1 root-pairing, C1 participant_list_status and other '
            'morning-report P2 items: no new fixtures this round.'],
        'cache_observation': (
            'G01 isolation tree test subprocesses produced 7 .pyc '
            'files despite -B and PYTHONDONTWRITEBYTECODE=1 (list in '
            'attempt1/post_run_sha_result.json, same count as the r1/'
            'r2 observations); repo tree runs left no pyc. No '
            '"all-no-pyc" claim is made.'),
    }
    (EVID / 'g01' / 'incidents.json').write_text(
        json.dumps(g01, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    print('run_meta.json and g01/incidents.json written')


if __name__ == '__main__':
    main()
