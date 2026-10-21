#!/usr/bin/env python3
"""Auxiliary context for the T-I ranking-variable list.

Reads the same read-only local mirror as extract_lever1_rank.py and reports,
for all 126 matched_strict questions, the strict-event channel split between
rank1 (hit) and non-first. Metadata only: no SMILES, no reaction_spec, no
gold/reference-graph content.

This is descriptive association inside the 298 seen-question domain; it is not
a causal claim and does not change the 37-row lever-1 classification.
"""
from __future__ import annotations

import collections
import glob
import json
import os
from pathlib import Path

REPO = Path('/Volumes/CC/Enzyme_Agent/dependingv43')
METRICS = REPO / 'reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json'


def channel(lid) -> str:
    lid = str(lid or '')
    if lid.startswith('rec-'):
        return 'recorded'
    if lid.startswith('tpl-'):
        return 'analog'
    if lid:
        return 'novel'
    return 'unknown'


def main() -> int:
    metrics = json.loads(METRICS.read_text())
    pq = {r['qid']: r for r in metrics['per_qid']}
    root = os.environ.get('PAYLOAD_ROOT', '/tmp/t_h_p0_r2/runs')

    strict_all = collections.Counter()
    strict_hit = collections.Counter()
    strict_nonfirst = collections.Counter()
    rank1_hit = collections.Counter()
    rank1_nonfirst = collections.Counter()
    pair_nonfirst = collections.Counter()
    n = {'matched_strict': 0, 'rank1': 0, 'nonfirst': 0, 'payload_missing': 0}

    for qid, entry in pq.items():
        if entry['main'].get('match_status') != 'matched_strict':
            continue
        n['matched_strict'] += 1
        rank = entry['main'].get('rank')
        files = glob.glob(os.path.join(
            root, entry['run_id'], 'native_export', '*', 'payload.json'))
        if len(files) != 1:
            n['payload_missing'] += 1
            continue
        payload = json.loads(Path(files[0]).read_text())
        actions = {a.get('action_id'): a for a in payload.get('search_actions') or []}
        event_to_action = {
            c.get('event_id'): c.get('action_id')
            for c in payload.get('search_commit_records') or []
            if c.get('commit_kind') == 'event_committed'}
        strict_lid = None
        rank1_lid = None
        for ev in payload.get('events') or []:
            action = actions.get(event_to_action.get(ev.get('event_id'))) or {}
            apay = action.get('payload') or {}
            if apay.get('effective_rank') == rank:
                strict_lid = apay.get('logical_proposal_id')
            if apay.get('effective_rank') == 1:
                rank1_lid = apay.get('logical_proposal_id')
        if strict_lid is None:
            n['payload_missing'] += 1
            continue
        strict_channel = channel(strict_lid)
        rank1_channel = channel(rank1_lid)
        strict_all[strict_channel] += 1
        if rank == 1:
            n['rank1'] += 1
            strict_hit[strict_channel] += 1
            rank1_hit[rank1_channel] += 1
        else:
            n['nonfirst'] += 1
            strict_nonfirst[strict_channel] += 1
            rank1_nonfirst[rank1_channel] += 1
            pair_nonfirst[f'{rank1_channel}->{strict_channel}'] += 1

    out = {
        'schema': 't-h-lever1-strict126-channel-context-1',
        'domain_tag': '298',
        'scope': ('T-H r2 sealed batch, post-hoc, seen questions; all 126 '
                  'matched_strict questions used as background context only'),
        'source': {
            'metrics': str(METRICS),
            'payload_root_local_mirror': root,
            'payload_authority': ('~/ppv1_hpc/runs/t_h_s5b_298_20261020r2 '
                                  '(sealed, read-only)'),
        },
        'counts': dict(n),
        'strict_event_channel_all': dict(strict_all),
        'strict_event_channel_rank1': dict(strict_hit),
        'strict_event_channel_nonfirst': dict(strict_nonfirst),
        'rank1_event_channel_in_rank1_questions': dict(rank1_hit),
        'rank1_event_channel_in_nonfirst_questions': dict(rank1_nonfirst),
        'rank1_to_strict_channel_nonfirst': dict(pair_nonfirst),
        'note': ('Descriptive within strict-matched seen questions only. '
                 'Not causal, not a channel-quality claim, and not a hit@1 '
                 'benefit estimate.'),
    }
    print(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())