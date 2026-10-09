from __future__ import annotations
"""Seal the S5a rework r3 evidence package: manifest.json +
SHA256SUMS over every actual file (including nested controls and this
seal script itself), excluding only the two root self-control files
(manifest.json / SHA256SUMS). No SQLite binaries, no .pyc, no run
directories are in the tree at seal time."""
import hashlib
import json
from pathlib import Path

ROOT = Path('/Volumes/CC/Enzyme_Agent/dependingv43/'
            'docs/review_evidence/ppv1_s5a_rework_r3_2026-10-09')
EXCLUDED = {'manifest.json', 'SHA256SUMS'}
FORBIDDEN_SUFFIXES = ('.sqlite', '.pyc', '.db')
FORBIDDEN_NAMES = {'__pycache__'}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    entries = {}
    problems = []
    for path in sorted(ROOT.rglob('*')):
        if path.is_dir():
            if path.name in FORBIDDEN_NAMES:
                problems.append(f'pycache dir present: {path}')
            continue
        rel = str(path.relative_to(ROOT))
        if rel in EXCLUDED:
            continue
        if path.suffix in FORBIDDEN_SUFFIXES:
            problems.append(f'forbidden binary in package: {rel}')
            continue
        entries[rel] = sha(path)
    if problems:
        raise SystemExit('refusing to seal: ' + '; '.join(problems))
    manifest = {
        'package': 'ppv1_s5a_rework_r3_2026-10-09',
        'round': 'S5a rework r3 (review R3 section 4 sole P1 S5A-05 '
                 'first-consumption context reference binding + '
                 'section 5 five P2 text syncs)',
        'baseline_commit': '39d739d04f9b3e6e7ad78cb0ec5f1547ac54'
                           'c962',
        'n_files': len(entries),
        'excluded_root_self_controls': sorted(EXCLUDED),
        'files': entries,
    }
    (ROOT / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2,
                   sort_keys=True) + '\n', encoding='utf-8')
    lines = [f'{digest}  {rel}' for rel, digest in
             sorted(entries.items())]
    (ROOT / 'SHA256SUMS').write_text('\n'.join(lines) + '\n',
                                     encoding='utf-8')
    print(f'sealed {len(entries)} files under {ROOT}')


if __name__ == '__main__':
    main()
