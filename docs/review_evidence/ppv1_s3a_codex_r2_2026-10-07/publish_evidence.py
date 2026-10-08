#!/usr/bin/env python3
"""One-time publication of this review's two new paths. No probe execution."""
import datetime
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
from verify_evidence import verify

ROOT = Path(__file__).resolve().parent
REPO = Path('/Volumes/CC/Enzyme_Agent/dependingv43')
DATE = '2026-10-07'
REPORT_REL = f'docs/POLLUTANT_PATHWAY_S3A_CODEX_REVIEW_R2_{DATE}.md'
EVIDENCE_REL = f'docs/review_evidence/ppv1_s3a_codex_r2_{DATE}'
REPORT = REPO / REPORT_REL
EVIDENCE = REPO / EVIDENCE_REL


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def git(*args):
    p = subprocess.run(['git', *args], cwd=REPO, capture_output=True, check=True)
    return p.stdout


def source_guard(snapshot, published=False):
    changed = [name for name, expected in snapshot['input_sha256'].items()
               if not Path(name).is_file() or digest(Path(name)) != expected]
    assert not changed, changed
    head = git('rev-parse', 'HEAD').decode().strip()
    parent = git('rev-parse', 'HEAD^').decode().strip()
    assert head == snapshot['actual_head'] and parent == snapshot['parent_head']
    diff = hashlib.sha256(git('diff')).hexdigest()
    assert diff == snapshot['initial_tracked_diff_sha256'], 'tracked diff changed'
    status = git('status', '--short').decode()
    lines = set(status.splitlines())
    expected = set(snapshot['initial_git_status'].splitlines())
    if published:
        expected |= {'?? ' + REPORT_REL, '?? ' + EVIDENCE_REL + '/'}
    assert lines == expected, {'unexpected': sorted(lines - expected), 'missing': sorted(expected - lines)}
    return {'checked_existing_files': len(snapshot['input_sha256']), 'changed_existing_files': changed,
            'head': head, 'parent': parent, 'tracked_diff_sha256': diff, 'git_status': status,
            'only_authorized_new_paths': published, 'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    assert datetime.datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat() == DATE, 'actual local date changed'
    assert not REPORT.exists() and not EVIDENCE.exists(), 'refuse replacing any existing review'
    snapshot = json.loads((ROOT / 'input_snapshot.json').read_text())
    before = source_guard(snapshot)
    assembly = json.loads((ROOT / 'package_assembly.json').read_text())
    assert assembly['all_copied'] and assembly['no_hash_or_symlink_or_cache_issues']
    stage = ROOT / 'evidence_stage'
    root_files = {'README.md': ROOT / 'EVIDENCE_README.md',
                  'input_snapshot.json': ROOT / 'input_snapshot.json',
                  'INTERRUPTION_RESUME.json': ROOT / 'INTERRUPTION_RESUME.json',
                  'package_assembly.json': ROOT / 'package_assembly.json',
                  'assembly_confirmation.json': ROOT / 'assembly_confirmation.json',
                  'assemble_evidence.py': ROOT / 'assemble_evidence.py',
                  'verify_nested_archives.py': ROOT / 'verify_nested_archives.py',
                  'verify_nested_archives_initial.py': ROOT / 'verify_nested_archives_initial.py',
                  'nested_verification_first_attempt.json': ROOT / 'nested_verification_first_attempt.json',
                  'verify_evidence.py': ROOT / 'verify_evidence.py',
                  'publish_evidence.py': ROOT / 'publish_evidence.py',
                  'run_metadata.json': ROOT / 'run_metadata.json'}
    for name, source in root_files.items():
        target = stage / name
        assert not target.exists(), name
        shutil.copy2(source, target)
    with REPORT.open('xb') as stream:
        stream.write((ROOT / 'REPORT_DRAFT.md').read_bytes())
    shutil.copytree(stage, EVIDENCE, symlinks=False)
    after = source_guard(snapshot, published=True)
    write_json(EVIDENCE / 'workspace_integrity.json', {'before_publication': before, 'after_publication': after,
               'preserved_AGENTS_and_zcodeignore_and_old_review_files': True,
               'probes_executed_during_publication': 0})
    report_sha = digest(REPORT)
    (EVIDENCE / 'report.sha256').write_text(report_sha + '  ' + str(REPORT) + '\n')
    files = []
    for p in sorted(EVIDENCE.rglob('*')):
        if p.is_file():
            assert not p.is_symlink()
            files.append({'path': str(p.relative_to(EVIDENCE)), 'size': p.stat().st_size, 'sha256': digest(p)})
    manifest = {'actual_head': snapshot['actual_head'], 'parent_head': snapshot['parent_head'],
                'date_Asia_Shanghai': DATE, 'synthetic_engineering_only': True,
                'report': {'absolute_path': str(REPORT), 'sha256': report_sha},
                'outer_controls_excluded': ['manifest.json', 'SHA256SUMS'],
                'nested_manifests_and_controls_included': True,
                'synthetic_SQLite_files_preserved_read_only': 162,
                'full_suite_reruns_during_resume_archiving': 0, 'files': files}
    write_json(EVIDENCE / 'manifest.json', manifest)
    sha_lines = [entry['sha256'] + '  ' + entry['path'] for entry in files]
    sha_lines.append(digest(EVIDENCE / 'manifest.json') + '  manifest.json')
    (EVIDENCE / 'SHA256SUMS').write_text('\n'.join(sha_lines) + '\n')
    result = verify(EVIDENCE, REPORT)
    result['final_source_guard'] = source_guard(snapshot, published=True)
    write_json(ROOT / 'publication_result.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'final_source_guard'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
