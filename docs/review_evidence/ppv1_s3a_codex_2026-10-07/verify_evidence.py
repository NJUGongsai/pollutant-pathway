#!/usr/bin/env python3
"""Read-only attachment, nested-manifest and report verification. No probes."""
import hashlib,json
from pathlib import Path

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    root=Path(__file__).resolve().parent
    manifest=json.loads((root/'manifest.json').read_text())
    expected=manifest['attachments']
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()
            and p.relative_to(root).as_posix() not in {'manifest.json','SHA256SUMS'}}
    assert set(expected)==actual, 'outer file set mismatch'
    assert not any(p.is_symlink() for p in root.rglob('*')), 'symlink found'
    for relative,sha in expected.items():
        path=root/relative
        assert digest(path)==sha, ('outer SHA mismatch',relative)
    sha_lines={line.split('  ',1)[1]:line.split('  ',1)[0]
               for line in (root/'SHA256SUMS').read_text().splitlines()}
    assert sha_lines==expected, 'outer checksum listing mismatch'
    counts={}
    for name in ('execution_specialist','search_specialist','inheritance_specialist'):
        subroot=root/name
        sub=json.loads((subroot/'manifest.json').read_text())
        inner=sub.get('files') or sub.get('attachments') or sub.get('sha256')
        assert inner
        for relative,sha in inner.items():
            assert digest(subroot/relative)==sha,('nested SHA mismatch',name,relative)
        counts[name]=len(inner)
    report_sha,report_name=(root/'report.sha256').read_text().strip().split('  ',1)
    assert digest(Path(report_name))==report_sha,'report SHA mismatch'
    print(json.dumps({'outer_attachments':len(expected),'nested_attachments':counts,
                      'report_sha256':report_sha,'status':'all_verified',
                      'read_only':True,'probe_or_suite_execution':False},ensure_ascii=False))

if __name__=='__main__':main()
