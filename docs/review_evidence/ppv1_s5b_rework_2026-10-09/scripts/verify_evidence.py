"""Read-only exact evidence inventory verification.

Never imports project code, never writes. Adapted from the S5b codex
review verify_evidence.py (same contract): manifest.json files must
exactly match the on-disk inventory; the only files allowed outside
the manifest are the two root control files (manifest.json and
SHA256SUMS) plus this script's own listing rules; no symlink / pyc /
pytest cache / SQLite binary anywhere in the package.
"""
from pathlib import Path
import hashlib
import json
import sys

CONTROLS = {'manifest.json', 'SHA256SUMS'}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inventory(root: Path) -> dict:
    out = {}
    for p in root.rglob('*'):
        if p.is_symlink():
            raise ValueError(f'symlink: {p}')
        if not p.is_file():
            continue
        if '__pycache__' in p.parts or '.pytest_cache' in p.parts \
                or p.suffix == '.pyc':
            raise ValueError(f'cache: {p}')
        with p.open('rb') as f:
            if f.read(16) == b'SQLite format 3\x00':
                raise ValueError(f'database: {p}')
        out[p.relative_to(root).as_posix()] = sha(p)
    return out


def verify(root: Path) -> dict:
    actual = inventory(root)
    mf = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    entries = mf['files']
    if isinstance(entries, list):
        entries = {v['path']: v for v in entries}
    for rel, v in entries.items():
        assert not Path(rel).is_absolute() and '..' not in Path(rel).parts, rel
        h = v['sha256'] if isinstance(v, dict) else v
        assert actual.get(rel) == h, (rel, 'manifest SHA mismatch')
    assert set(actual) - set(entries) <= CONTROLS, \
        sorted(set(actual) - set(entries) - CONTROLS)
    assert set(entries) <= set(actual), sorted(set(entries) - set(actual))
    sums = root / 'SHA256SUMS'
    lines = {}
    for line in sums.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        h, rel = line.split(maxsplit=1)
        rel = rel.lstrip('*')
        rel = Path(rel).as_posix()
        assert not Path(rel).is_absolute() and '..' not in Path(rel).parts, rel
        assert rel not in lines, rel
        assert actual.get(rel) == h, (rel, 'SHA256SUMS mismatch')
        lines[rel] = h
    assert set(entries) <= set(lines), sorted(set(entries) - set(lines))
    return {'root': str(root), 'files': len(actual),
            'manifest_records': len(entries),
            'sums_records': len(lines),
            'manifest_sha256': actual['manifest.json'],
            'verified': True}


if __name__ == '__main__':
    root = Path(sys.argv[1])
    results = [verify(root)]
    print(json.dumps(results, ensure_ascii=False, indent=2))
