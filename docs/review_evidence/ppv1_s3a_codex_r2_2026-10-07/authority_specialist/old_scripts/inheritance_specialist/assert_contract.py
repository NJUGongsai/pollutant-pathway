#!/usr/bin/env python3
"""Desired existing S3a authority contract. Expected fail at this HEAD."""
import argparse,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);a=ap.parse_args()
rows=[json.loads(l) for l in (Path(a.root)/'inheritance_v2.stdout.jsonl').read_text().splitlines()]
for r in rows:
    if '__' not in r['case'] or r['case'].endswith('__clean'):continue
    assert 'error' in r['recovery'] and not r['recovery_changed'],(
      f"{r['case']}: corrupted authority must fail before bookkeeping; observed {r['recovery']}")
