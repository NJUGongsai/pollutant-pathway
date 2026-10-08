#!/usr/bin/env python3
"""Pure attachment assembly / SHA verification only. No suite execution."""
from pathlib import Path
import json,hashlib,shutil
out=Path(__file__).resolve().parents[1];pkg=out/'package';pkg.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(p,rel):
 assert p.is_file() and not p.is_symlink();dst=pkg/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst);assert sha(p)==sha(dst)
# Explicit top-level metadata/logs only, not ephemeral SQLite/db directories.
for p in sorted(out.iterdir()):
 if p.is_file() and p.suffix in {'.json','.md','.txt','.diff','.gz'}:copy(p,p.name)
for name in ['scripts','allowlists','chemistry_inputs','ppv1_full','baseline_r4','current_runtime','baseline_runtime','worktree_create','worktree_sparse_init','worktree_sparse_set','worktree_checkout','worktree_remove','g01_controller','factory_r1','chemistry_probe','public_controls']:
 for p in sorted((out/name).rglob('*')):
  if p.is_file() and p.suffix in {'.py','.json','.xml','.txt','.diff','.md'} and '__pycache__' not in p.parts:copy(p,p.relative_to(out))
for name in ['current_source','baseline_source']:
 for p in sorted((out/name).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo','.sqlite','.db'}:copy(p,Path('sources')/name.replace('_source','')/p.relative_to(out/name))
for p in sorted((out/'g01').iterdir()):
 if p.is_file() and p.suffix in {'.json','.xml','.txt'}:copy(p,Path('g01')/p.name)
files={str(p.relative_to(pkg)):sha(p) for p in sorted(pkg.rglob('*')) if p.is_file()}
x={'actual_HEAD':'b7f2bba02ca49edd0a45a13bc9b8434909d99175','actual_parent':'41d0cd55f3def050a62325f00235cf22da302d2e','attachment_count':len(files),'attachment_bytes':sum((pkg/k).stat().st_size for k in files),'sha256':files,'excluded_manifest_self':['manifest.json','SHA256SUMS'],'scope':'ordinary source/tests/approved assets and synthetic proof only; source SHA original/copy checked; no SQLite/cache/symlink/runtime DB/archive unlisted member'}
(pkg/'manifest.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');(pkg/'SHA256SUMS').write_text(''.join(f'{v}  {k}\n' for k,v in files.items()))
assert all(sha(pkg/k)==v for k,v in files.items());assert not any(p.is_symlink() or '__pycache__' in p.parts or p.suffix in {'.sqlite','.db','.pyc','.pyo'} for p in pkg.rglob('*'))
print(json.dumps({'package':str(pkg),'attachments':len(files),'bytes':x['attachment_bytes'],'manifest_sha256':sha(pkg/'manifest.json'),'all_attachment_sha_verified':True},indent=2))
