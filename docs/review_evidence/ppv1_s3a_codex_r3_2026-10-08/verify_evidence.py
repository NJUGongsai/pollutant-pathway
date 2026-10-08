#!/usr/bin/env python3
"""Read-only evidence verification. Does not import project code or open SQLite."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def safe(root, rel):
    parts = PurePosixPath(rel)
    if parts.is_absolute() or '..' in parts.parts:
        raise ValueError('unsafe evidence path: ' + rel)
    path = root / rel
    for i in range(1, len(parts.parts) + 1):
        if root.joinpath(*parts.parts[:i]).is_symlink():
            raise ValueError('evidence symlink: ' + rel)
    return path


def mapping(doc):
    for key in ('files', 'artifacts', 'attachments'):
        if key in doc:
            entries = doc[key]
            return ({e['path']: e['sha256'] for e in entries}
                    if isinstance(entries, list) else {k: (v['sha256'] if isinstance(v, dict) else v) for k, v in entries.items()})
    raise ValueError('unrecognized manifest')


def verify(root, report=None):
    root = root.resolve()
    doc = json.loads((root / 'manifest.json').read_text())
    files = mapping(doc)
    for rel, expected in files.items():
        path = safe(root, rel)
        assert path.is_file() and sha(path) == expected, rel
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    assert actual == set(files) | {'manifest.json', 'SHA256SUMS'}, 'outer inventory'
    sha_checks = 0
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        expected, rel = line.split(maxsplit=1)
        rel = rel.lstrip('*')
        assert sha(safe(root, rel)) == expected, 'SHA256SUMS:' + rel
        sha_checks += 1
    nested = {}
    for label in ('execution_specialist', 'authority_specialist', 'budget_request_specialist'):
        sub = root / label
        entries = mapping(json.loads((sub / 'manifest.json').read_text()))
        for rel, expected in entries.items():
            assert sha(safe(sub, rel)) == expected, label + ':' + rel
        for control in ('SHA256SUMS', 'manifest.sha256'):
            if (sub / control).is_file():
                for line in (sub / control).read_text().splitlines():
                    if line.strip():
                        expected, rel = line.split(maxsplit=1)
                        assert sha(safe(sub, rel.lstrip('*'))) == expected, label + ':' + control
        nested[label] = {'payload_files': len(entries), 'manifest_sha256': sha(sub / 'manifest.json')}
    report_path = Path(report) if report else Path(doc['report']['absolute_path'])
    assert sha(report_path) == doc['report']['sha256'], 'report digest'
    for p in root.rglob('*'):
        assert not p.is_symlink(), 'symlink: ' + str(p)
        assert p.suffix != '.pyc' and p.name not in ('__pycache__', '.pytest_cache'), 'cache: ' + str(p)
    return {'all_verified': True, 'outer_payload_files': len(files),
            'outer_SHA_checks': sha_checks, 'nested': nested,
            'report_sha256': sha(report_path), 'manifest_sha256': sha(root / 'manifest.json'),
            'probe_execution_count': 0, 'database_open_count': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--report')
    args = parser.parse_args()
    print(json.dumps(verify(Path(args.evidence), args.report), ensure_ascii=False, indent=2))
