#!/usr/bin/env python3
"""Copy frozen review packages by manifest; no project/probe execution."""
import hashlib
import json
import shutil
from pathlib import Path
from verify_evidence import mapping, safe, sha

ROOT = Path(__file__).resolve().parent
PACKAGES = {
    'execution_specialist': (
        '/private/tmp/ppv1_s3b_r2_execution_gvh309hu/package',
        '26c0e4bb0541642bf95287bac4b37786ba79642c8b3cccfcb76a6c6386140251'),
    'recovery_specialist': (
        '/private/tmp/ppv1_s3b_r2_recovery_7bipev0i/package',
        '26f066ad359549a89f9e23b8c63ecea2d3dfa2661899ac7fec2b14ace37e017e'),
    'protocol_specialist': (
        '/private/tmp/ppv1_s3b_r2_protocol_1ex8j4tb/package',
        'ac346c9e9450470dd2d6195fe7290450983102b7b469646272a7848437ca6d77'),
}


def main():
    stage = ROOT / 'evidence_stage'
    assert not stage.exists(), 'one-time fresh staging only'
    stage.mkdir()
    records = {}
    for label, (source, expected_manifest) in PACKAGES.items():
        src = Path(source)
        assert sha(src / 'manifest.json') == expected_manifest, label
        entries = mapping(json.loads((src / 'manifest.json').read_text()))
        controls = {n for n in ('manifest.json', 'SHA256SUMS', 'manifest.sha256') if (src/n).is_file()}
        actual = set()
        for path in src.rglob('*'):
            assert not path.is_symlink(), path
            assert path.name not in ('__pycache__', '.pytest_cache') and path.suffix != '.pyc', path
            assert path.suffix not in ('.sqlite', '.sqlite3', '.db'), path
            if path.is_file():
                actual.add(str(path.relative_to(src)))
        assert actual == set(entries) | controls, label + ': inventory mismatch'
        for rel, expected in entries.items():
            assert sha(safe(src, rel)) == expected, label + ':' + rel
        for control in ('SHA256SUMS', 'manifest.sha256'):
            if control in controls:
                for line in (src/control).read_text().splitlines():
                    if line.strip():
                        expected, rel = line.split(maxsplit=1)
                        assert sha(safe(src, rel.lstrip('*'))) == expected, label + ':' + control
        dst = stage / label
        shutil.copytree(src, dst)
        for rel in actual:
            assert sha(safe(src, rel)) == sha(safe(dst, rel)), label + ':copy:' + rel
        records[label] = {
            'source': source, 'manifest_sha256': expected_manifest,
            'payload_files': len(entries), 'controls': sorted(controls),
            'copied_files': len(actual),
            'payload_bytes': sum(safe(src, rel).stat().st_size for rel in entries),
            'all_original_and_copied_hashes_verified': True,
        }
    result = {'all_copied': True, 'no_hash_or_symlink_or_cache_issues': True,
              'packages': records, 'project_imports': 0, 'probe_executions': 0,
              'database_open_count': 0, 'old_permanent_evidence_modified': False}
    (ROOT/'package_assembly.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
