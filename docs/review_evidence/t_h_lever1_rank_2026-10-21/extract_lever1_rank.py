#!/usr/bin/env python3
"""Teacher lever 1: per-question rank-cause extraction for the 37 strict non-first qids.

Read-only. No model calls, no batch runs, no gold/reference-graph content.
The script copies only IDs/counts/rank metadata from the native export payload;
it never selects SMILES, reaction_spec, signature, or any structure body.

Sources:
  * reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json  (headline v2 per_qid)
  * /tmp/t_h_p0_r2/runs/<run_id>/native_export/*/payload.json
    (read-only local mirror downloaded from the sealed HPC runs root
     ~/ppv1_hpc/runs/t_h_s5b_298_20261020r2; the mirror itself is volatile and
     each source payload hash is recorded below)
  * docs/review_evidence/t_h_p0_2026-10-20/p0a_candidate_lineage.json
    (cross-check only)

Usage:
    python3 extract_lever1_rank.py \
        --payload-root /tmp/t_h_p0_r2/runs \
        --out lever1_rank.json
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

REPO = Path('/Volumes/CC/Enzyme_Agent/dependingv43')
METRICS = REPO / 'reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json'
P0A = REPO / 'docs/review_evidence/t_h_p0_2026-10-20/p0a_candidate_lineage.json'

CHANNEL_BY_LID_PREFIX = {'rec-': 'recorded', 'tpl-': 'analog'}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def channel_from_lid(lid) -> str:
    lid = str(lid or '')
    for prefix, channel in CHANNEL_BY_LID_PREFIX.items():
        if lid.startswith(prefix):
            return channel
    if lid:
        return 'novel'
    return 'unknown'


def channel_from_secondary(lid, action_payload, hypothesis_payload) -> tuple[str, str]:
    """Independent channel signal used only as a cross-check."""
    origin = str(hypothesis_payload.get('origin_group_key') or '')
    if origin.startswith('rec-source:'):
        return 'recorded', 'hypothesis.payload.origin_group_key=rec-source:*'
    if origin.startswith('analog-template:'):
        return 'analog', 'hypothesis.payload.origin_group_key=analog-template:*'
    pctx = action_payload.get('proposal_context') or {}
    if pctx.get('output_origin') == 'novel_outside_pool':
        return 'novel', 'search_action.payload.proposal_context.output_origin=novel_outside_pool'
    if not str(lid or ''):
        return 'unknown', 'no_lid_no_context'
    # A lid with no recorded/analog prefix and no proposal context is treated as
    # novel by the rank policy, but the cross-check stays unknown on purpose.
    return 'unknown', 'lid_prefix_only'


def rank_declaration(action_payload) -> str:
    basis = action_payload.get('rank_basis')
    has_key = 'model_rank' in action_payload
    value = action_payload.get('model_rank')
    if basis == 'deterministic_fallback':
        return 'fallback'
    if basis == 'model_selection' and isinstance(value, int) and has_key:
        return 'explicit_int'
    if basis == 'model_selection' and has_key and value is None:
        return 'explicit_null'
    if basis == 'model_selection' and not has_key:
        return 'default_order'
    return 'unknown'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--payload-root', default='/tmp/t_h_p0_r2/runs')
    ap.add_argument('--out', default='lever1_rank.json')
    args = ap.parse_args()

    metrics = json.loads(METRICS.read_text())
    p0a = json.loads(P0A.read_text())
    p0_by_qid = {r['qid']: r for r in p0a['rows']}

    pq = {r['qid']: r for r in metrics['per_qid']}
    targets = [
        q for q, r in pq.items()
        if r['main'].get('match_status') == 'matched_strict'
        and (r['main'].get('rank') or 0) > 1
    ]
    targets.sort(key=lambda q: (pq[q]['main']['rank'], q))

    rows = []
    payload_hashes = {}
    for qid in targets:
        entry = pq[qid]
        run_id = entry['run_id']
        main_rank = entry['main'].get('rank')
        candidates = glob.glob(os.path.join(
            args.payload_root, run_id, 'native_export', '*', 'payload.json'))
        rec: dict = {
            'qid': qid,
            'qid_prefix': qid[:20],
            'run_id': run_id,
            'main_rank': main_rank,
            'rank_bucket': '2_5' if 2 <= (main_rank or 0) <= 5 else 'gt5',
            'metrics_field_ref': 'metrics.json:per_qid[].main.{match_status,rank}',
        }
        if len(candidates) != 1:
            rec.update({
                'closed': False,
                'classification': 'unknown',
                'classification_reason': f'payload_count={len(candidates)}',
            })
            rows.append(rec)
            continue
        payload_path = candidates[0]
        payload_hashes[run_id] = sha256_file(payload_path)
        payload = json.loads(Path(payload_path).read_text())

        actions = {a.get('action_id'): a for a in payload.get('search_actions') or []}
        hyp_by_id = {h.get('hypothesis_id'): h.get('payload') or {}
                     for h in payload.get('hypotheses') or []}
        event_to_commit = {}
        for c in payload.get('search_commit_records') or []:
            if c.get('commit_kind') == 'event_committed':
                event_to_commit[c.get('event_id')] = c

        events = sorted(
            payload.get('events') or [],
            key=lambda e: (str(e.get('created_at')), str(e.get('event_id'))))
        ev_rows = []
        for pos, ev in enumerate(events, 1):
            commit = event_to_commit.get(ev.get('event_id')) or {}
            action = actions.get(commit.get('action_id')) or {}
            apay = action.get('payload') or {}
            ev_rows.append({
                'event': ev,
                'position': pos,
                'commit': commit,
                'action': action,
                'action_payload': apay,
                'effective_rank': apay.get('effective_rank'),
            })

        matched = [x for x in ev_rows if x['effective_rank'] == main_rank]
        rank1 = [x for x in ev_rows if x['effective_rank'] == 1]
        seq = [x['effective_rank'] for x in ev_rows]
        consistent = all(x['effective_rank'] == x['position'] for x in ev_rows)
        rank_gaps = sorted(set(range(1, max([r for r in seq if isinstance(r, int)] or [1]) + 1))
                           - {r for r in seq if isinstance(r, int)})

        # dedup / fold metadata (aggregate unique notes, no structure fields)
        dedup = []
        model_rank_by_id: dict = {}
        pool_size = None
        for outcome in payload.get('expansion_outcomes') or []:
            detail = (((outcome.get('outcome_payload') or {}).get('outcome') or {})
                      .get('detail') or {})
            if isinstance(detail.get('pool_size'), int):
                pool_size = detail['pool_size']
            model_note = detail.get('model') or {}
            for k, v in (model_note.get('model_rank_by_id') or {}).items():
                model_rank_by_id[str(k)] = v
            for d in model_note.get('dedup_rejections') or []:
                dedup.append({
                    'folded_lid': d.get('logical_proposal_id'),
                    'folded_model_rank': d.get('folded_model_rank'),
                    'folded_entry_source': d.get('folded_entry_source'),
                    'rank_inherited': bool(d.get('rank_inherited')),
                })
        dedup_unique = []
        seen = set()
        for d in dedup:
            key = (d['folded_lid'], d['folded_model_rank'], d['rank_inherited'])
            if key not in seen:
                seen.add(key)
                dedup_unique.append(d)

        if len(matched) != 1:
            rec.update({
                'closed': False,
                'classification': 'unknown',
                'classification_reason': f'matched_event_count={len(matched)}',
                'n_events': len(ev_rows),
                'effective_rank_sequence': seq,
                'payload_sha256': payload_hashes[run_id],
                'payload_field_ref': 'payload.json:events/search_commit_records/search_actions',
            })
            rows.append(rec)
            continue

        m = matched[0]
        apay = m['action_payload']
        ev = m['event']
        lid = apay.get('logical_proposal_id')
        channel = channel_from_lid(lid)
        hyp_payload = hyp_by_id.get(ev.get('hypothesis_id')) or {}
        secondary_channel, secondary_signal = channel_from_secondary(
            lid, apay, hyp_payload)
        declaration = rank_declaration(apay)
        model_rank = apay.get('model_rank')
        effective_rank = apay.get('effective_rank')
        inherited_from = apay.get('model_rank_inherited_from')
        prepared_id = apay.get('prepared_hypothesis_id')
        own_model_rank = model_rank_by_id.get(str(lid))
        if own_model_rank is None and prepared_id is not None:
            own_model_rank = model_rank_by_id.get(str(prepared_id))

        pre_fold_rank_sequence = sorted(
            v for v in model_rank_by_id.values() if isinstance(v, int))
        matched_lid_folded = any(d['folded_lid'] == lid for d in dedup_unique)
        dedup_lost = bool(matched_lid_folded and not any(
            d['folded_lid'] == lid and d['rank_inherited'] for d in dedup_unique))
        # Compare the proposal's own declared rank (before folding) with its
        # final effective rank. Negative delta = moved up by inheritance.
        rank_delta = None
        if isinstance(own_model_rank, int) and isinstance(effective_rank, int):
            rank_delta = effective_rank - own_model_rank
        if rank_delta is None:
            rank_shift = 'unknown'
        elif rank_delta < 0:
            rank_shift = 'up'
        elif rank_delta > 0:
            rank_shift = 'down'
        else:
            rank_shift = 'same'
        # A matched candidate that was not itself folded, but whose final rank is
        # higher than its own declared rank, was moved up by inheritance, not lost.
        rank_inherited_up = rank_shift == 'up'

        if declaration == 'fallback' or model_rank is None:
            classification = 'fallback_default'
            reason = ('rank_basis=deterministic_fallback'
                      if declaration == 'fallback' else 'model_rank=null')
        elif m['position'] != effective_rank or effective_rank != model_rank:
            classification = 'execution_assembly'
            reason = (f'position={m["position"]},effective_rank={effective_rank},'
                      f'model_rank={model_rank}')
        elif rank_shift == 'down':
            classification = 'execution_assembly'
            reason = (f'own_model_rank={own_model_rank} moved down to '
                      f'effective_rank={effective_rank}')
        elif dedup_lost:
            classification = 'execution_assembly'
            reason = 'matched_lid_folded_without_rank_inheritance'
        else:
            classification = 'model_ranking'
            reason = ('model_selection explicit rank; matched rank > 1 and '
                      'commit/effective rank agree')
            if inherited_from:
                reason += f'; rank inherited from {inherited_from}'
            if rank_inherited_up:
                reason += (f'; own_model_rank={own_model_rank} moved up to '
                           f'{effective_rank} by fold inheritance')

        rec.update({
            'closed': True,
            'pool_size': pool_size,
            'empty_pool': pool_size == 0,
            'source_channel': channel,
            'source_channel_primary_ref': (
                'payload.json:search_actions[].payload.logical_proposal_id'),
            'source_channel_secondary': secondary_channel,
            'source_channel_secondary_ref': secondary_signal,
            'source_channel_crosscheck_ok': secondary_channel in (channel, 'unknown'),
            'matched_event_id': ev.get('event_id'),
            'matched_action_id': m['action'].get('action_id'),
            'matched_commit_id': m['commit'].get('commit_id'),
            'matched_logical_proposal_id': lid,
            'model_rank': model_rank,
            'own_model_rank_from_rank_table': own_model_rank,
            'pre_fold_model_rank_sequence': pre_fold_rank_sequence,
            'n_model_rank_by_id': len(pre_fold_rank_sequence),
            'model_rank_key_present': 'model_rank' in apay,
            'rank_basis': apay.get('rank_basis'),
            'rank_declaration': declaration,
            'rank_policy_version': apay.get('rank_policy_version'),
            'model_rank_inherited_from': inherited_from,
            'effective_rank': effective_rank,
            'pre_to_post_rank_delta': rank_delta,
            'rank_shift': rank_shift,
            'commit_position': m['position'],
            'matched_position_equals_effective': m['position'] == effective_rank,
            'matched_rank_equals_effective': model_rank == effective_rank,
            'n_events': len(ev_rows),
            'effective_rank_sequence': seq,
            'sequence_effective_equals_position': consistent,
            'rank_gaps': rank_gaps,
            'rank1_event_present': bool(rank1),
            'rank1_channel': channel_from_lid(
                (rank1[0]['action_payload'].get('logical_proposal_id')
                 if rank1 else None)),
            'rank1_model_rank': (rank1[0]['action_payload'].get('model_rank')
                                 if rank1 else None),
            'dedup_rejections': dedup_unique,
            'n_dedup_rejections': len(dedup_unique),
            'matched_lid_folded': matched_lid_folded,
            'dedup_lost_position': dedup_lost,
            'rank_inherited_up': rank_inherited_up,
            'attribution': (f"{apay.get('rank_basis')}:{declaration}"),
            'classification': classification,
            'classification_reason': reason,
            'commit_order_ref': ('payload.json:search_commit_records[].created_at;'
                                 'payload.json:events[].created_at'),
            'rank_fields_ref': ('payload.json:search_actions[].payload.'
                                '{model_rank,effective_rank,rank_basis,'
                                'model_rank_inherited_from,logical_proposal_id}'),
            'dedup_fields_ref': ('payload.json:expansion_outcomes[].outcome_payload.'
                                 'outcome.detail.model.dedup_rejections'),
            'payload_sha256': payload_hashes[run_id],
            'payload_path_hint': ('~/ppv1_hpc/runs/t_h_s5b_298_20261020r2/'
                                  f'{run_id}/native_export/*/payload.json'),
        })
        rows.append(rec)

    # ---- summary ----
    by_class = collections.Counter(r.get('classification') for r in rows)
    by_channel = collections.Counter(r.get('source_channel') for r in rows
                                     if r.get('closed'))
    by_basis = collections.Counter(r.get('rank_basis') for r in rows
                                   if r.get('closed'))
    by_decl = collections.Counter(r.get('rank_declaration') for r in rows
                                 if r.get('closed'))
    by_rank1_channel = collections.Counter(r.get('rank1_channel') for r in rows
                                           if r.get('closed'))
    by_channel_pair = collections.Counter(
        (r.get('rank1_channel'), r.get('source_channel'))
        for r in rows if r.get('closed'))
    buckets = collections.Counter(r.get('rank_bucket') for r in rows)

    p0_mismatches = []
    for r in rows:
        p0 = p0_by_qid.get(r['qid'])
        if not p0:
            p0_mismatches.append({'qid_prefix': r['qid_prefix'],
                                  'issue': 'not_in_p0a'})
            continue
        checks = {
            'main_rank': (r.get('main_rank'), p0.get('main_rank')),
            'matched_model_rank': (r.get('model_rank'),
                                   p0.get('matched_model_rank')),
            'matched_effective_rank': (r.get('effective_rank'),
                                       p0.get('matched_effective_rank')),
            'matched_rank_basis': (r.get('rank_basis'),
                                   p0.get('matched_rank_basis')),
            'matched_inherited': (bool(r.get('model_rank_inherited_from')),
                                  bool(p0.get('matched_inherited'))),
            'pool_size': (r.get('pool_size'), p0.get('pool_size')),
        }
        for field, (ours, theirs) in checks.items():
            if ours != theirs:
                p0_mismatches.append({'qid_prefix': r['qid_prefix'],
                                      'field': field, 'ours': ours,
                                      'p0a': theirs})

    summary = {
        'total_targets': len(targets),
        'closed': sum(1 for r in rows if r.get('closed')),
        'classification_counts': dict(by_class),
        'channel_counts': dict(by_channel),
        'rank_basis_counts': dict(by_basis),
        'rank_declaration_counts': dict(by_decl),
        'rank_bucket_counts': dict(buckets),
        'rank1_channel_counts': dict(by_rank1_channel),
        'rank1_vs_strict_channel_counts': {
            f'{a}->{b}': n for (a, b), n in sorted(by_channel_pair.items())},
        'all_matched_model_rank_equals_effective': all(
            r.get('matched_rank_equals_effective') for r in rows if r.get('closed')),
        'matched_position_equals_effective': sum(
            1 for r in rows if r.get('matched_position_equals_effective')),
        'sequence_effective_equals_position': sum(
            1 for r in rows if r.get('sequence_effective_equals_position')),
        'rows_with_dedup': sum(1 for r in rows if r.get('n_dedup_rejections')),
        'dedup_rejections_total': sum(r.get('n_dedup_rejections', 0)
                                      for r in rows),
        'empty_pool_subset': sum(1 for r in rows if r.get('empty_pool')),
        'empty_pool_prefixes': sorted(r['qid_prefix'] for r in rows
                                      if r.get('empty_pool')),
        'matched_lid_folded': sum(1 for r in rows if r.get('matched_lid_folded')),
        'dedup_lost_position': sum(1 for r in rows if r.get('dedup_lost_position')),
        'rank_shift_counts': dict(collections.Counter(
            r.get('rank_shift') for r in rows if r.get('closed'))),
        'rank_inherited_up': sum(1 for r in rows if r.get('rank_inherited_up')),
        'channel_crosscheck_ok': sum(1 for r in rows
                                     if r.get('source_channel_crosscheck_ok')),
        'p0a_crosscheck': {
            'p0a_path': str(P0A),
            'p0a_sha256': sha256_file(str(P0A)),
            'rows_compared': len(rows),
            'mismatches': p0_mismatches,
        },
    }

    out = {
        'schema': 't-h-lever1-rank-1',
        'domain_tag': '298',
        'scope': ('T-H r2 sealed batch, post-hoc, seen questions; strict non-first '
                  '37 = 36 rank 2-5 + 1 rank >5'),
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'sources': {
            'metrics': {'path': str(METRICS),
                        'sha256': sha256_file(str(METRICS))},
            'payload_root_local_mirror': args.payload_root,
            'payload_authority': ('~/ppv1_hpc/runs/t_h_s5b_298_20261020r2 '
                                  '(sealed, read-only)'),
            'payload_provenance': ('read-only local mirror downloaded earlier from '
                                   'the sealed HPC runs root; each payload hash is '
                                   'recorded per row so the source file is '
                                   'identifiable without copying structure content'),
            'payload_sha256_by_run': payload_hashes,
        },
        'field_legend': {
            'M': 'metrics.json per_qid[].main',
            'A': 'payload.json search_actions[].payload rank fields',
            'C': 'payload.json search_commit_records[] + events[].created_at',
            'D': 'payload.json expansion_outcomes[].outcome_payload.outcome.detail.model.dedup_rejections',
        },
        'classification_rule': {
            'fallback_default': ('matched event rank_basis=deterministic_fallback '
                                 'or model_rank is null'),
            'execution_assembly': ('matched commit position or effective_rank differs '
                                   'from model_rank, or the matched proposal was '
                                   'folded without rank inheritance'),
            'model_ranking': ('explicit model_selection rank > 1 and commit position '
                              '== effective_rank == model_rank (fold inheritance, if '
                              'any, only moves the candidate up)'),
            'unknown': 'payload missing, matched event not unique, or missing fields',
        },
        'summary': summary,
        'rows': rows,
    }
    Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + '\n')
    print(json.dumps({
        k: v for k, v in out.items()
        if k not in ('rows', 'sources', 'field_legend', 'classification_rule')
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())