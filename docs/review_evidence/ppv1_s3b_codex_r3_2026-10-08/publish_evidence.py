#!/usr/bin/env python3
"""One-time publication of two new review paths, with existing-file guard."""
import datetime
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
from verify_evidence import verify, sha

ROOT = Path(__file__).resolve().parent
REPO = Path('/Volumes/CC/Enzyme_Agent/dependingv43')
DATE = '2026-10-08'
REPORT_REL = f'docs/POLLUTANT_PATHWAY_S3B_CODEX_REVIEW_R3_{DATE}.md'
EVIDENCE_REL = f'docs/review_evidence/ppv1_s3b_codex_r3_{DATE}'
REPORT = REPO/REPORT_REL
EVIDENCE = REPO/EVIDENCE_REL


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO)


def source_guard(snapshot, published=False):
    changed = [name for name, expected in snapshot['input_sha256'].items()
               if not Path(name).is_file() or sha(Path(name)) != expected]
    assert not changed, changed
    head = git('rev-parse', 'HEAD').decode().strip()
    parent = git('rev-parse', 'HEAD^').decode().strip()
    assert (head, parent) == (snapshot['actual_head'], snapshot['parent_head'])
    diff = hashlib.sha256(git('diff')).hexdigest()
    assert diff == snapshot['initial_tracked_diff_sha256'], 'tracked diff changed'
    status = git('status', '--short').decode()
    expected = set(snapshot['initial_git_status'].splitlines())
    if published:
        expected |= {'?? '+REPORT_REL, '?? '+EVIDENCE_REL+'/'}
    assert set(status.splitlines()) == expected, 'unexpected working-tree change'
    return {'checked_existing_files': len(snapshot['input_sha256']),
            'changed_existing_files': changed, 'head': head, 'parent': parent,
            'tracked_diff_sha256': diff, 'git_status': status,
            'only_authorized_new_paths': published,
            'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def main():
    assert datetime.datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat() == DATE
    assert not REPORT.exists() and not EVIDENCE.exists(), 'refuse replacing existing review'
    snapshot = json.loads((ROOT/'input_snapshot.json').read_text())
    before = source_guard(snapshot)
    assembly = json.loads((ROOT/'package_assembly.json').read_text())
    assert assembly['all_copied'] and assembly['no_hash_or_symlink_or_cache_issues']
    stage = ROOT/'evidence_stage'
    files = {
        'README.md': 'EVIDENCE_README.md',
        'input_snapshot.json': 'input_snapshot.json',
        'intermediate_workspace_integrity.json': 'intermediate_workspace_integrity.json',
        'review_execution_events.json': 'review_execution_events.json',
        'run_metadata.json': 'run_metadata.json',
        'draft_crosscheck.json': 'draft_crosscheck.json',
        'package_assembly.json': 'package_assembly.json',
        'assemble_evidence.py': 'assemble_evidence.py',
        'verify_evidence.py': 'verify_evidence.py',
        'publish_evidence.py': 'publish_evidence.py',
    }
    for name, source in files.items():
        assert not (stage/name).exists()
        shutil.copy2(ROOT/source, stage/name)
    with REPORT.open('xb') as stream:
        stream.write((ROOT/'REPORT_DRAFT.md').read_bytes())
    shutil.copytree(stage, EVIDENCE)
    after = source_guard(snapshot, published=True)
    write_json(EVIDENCE/'workspace_integrity.json', {'before_publication': before,
               'after_publication': after, 'probe_executions_during_publication': 0})
    report_sha = sha(REPORT)
    (EVIDENCE/'report.sha256').write_text(report_sha+'  '+str(REPORT)+'\n')
    entries = [{'path': str(p.relative_to(EVIDENCE)), 'size': p.stat().st_size,
                'sha256': sha(p)} for p in sorted(EVIDENCE.rglob('*')) if p.is_file()]
    doc = {'actual_head': snapshot['actual_head'], 'parent_head': snapshot['parent_head'],
           'date_Asia_Shanghai': DATE, 'synthetic_engineering_only': True,
           'report': {'absolute_path': str(REPORT), 'sha256': report_sha},
           'nested_manifests_and_controls_included': True,
           'controls_excluded': ['manifest.json', 'SHA256SUMS'],
           'probe_executions_during_archiving': 0, 'files': entries}
    write_json(EVIDENCE/'manifest.json', doc)
    lines = [e['sha256']+'  '+e['path'] for e in entries]
    lines.append(sha(EVIDENCE/'manifest.json')+'  manifest.json')
    (EVIDENCE/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
    result = verify(EVIDENCE, REPORT)
    result['final_source_guard'] = source_guard(snapshot, published=True)
    write_json(ROOT/'publication_result.json', result)
    print(json.dumps({k:v for k,v in result.items() if k != 'final_source_guard'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
