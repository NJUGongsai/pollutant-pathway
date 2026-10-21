#!/usr/bin/env python3
"""T-H teacher lever 3: 53 partial coverage-gap classification (read-only).

Scope
-----
298 domain, T-H r2 sealed batch, zero model calls, zero new batches.
This script consumes:
  - P0-C aggregate machine file (53 partial qids + mechanical direction)
  - local metrics.json.v1 / metrics.json.v2 (T-1 redemption crosswalk)
  - staged batch manifest / reference graphs / native export payloads
    under /tmp/t_h_p0_r2 (same staging precedents as P0-C)

Hard boundaries
---------------
- The reference graph is consumed only inside the frozen evaluator
  (match_reference_nodes / match_reference_edges).  This script never
  reads reference `structure_smiles` or `state_identity` text.
- Candidate native-export structures are read in-process to compute
  formula / heavy-atom / Murcko-scaffold relations.  Only class labels
  and counts are written; no SMILES, no formula, no structure text.
- No gold/task text, no scoring change, no sealed-batch write.

Classification (teacher lever-3 wording)
----------------------------------------
bookkeeping_exempt : extra participant is in the criteria-v2 exempt
                     family (H2O / H+ / Pi / PPi).  A qid with only this
                     class would have been promoted to strict; the five
                     redeemed T-1 qids are exactly this class and are
                     outside the 53.
cofactor           : non-exempt extra with a cosubstrate role (any
                     size), or a >=30-heavy-atom species containing N
                     plus P/S.  Chemistry adjudication goes to sister.
structural_near    : missing reference node represented by a strict
                     matched candidate state ("proxy") whose formula is
                     the same as an event-side participant, or whose
                     Murcko scaffold matches with >=6 heavy atoms; also
                     same-identity wrong-side bookkeeping extras.
other              : remaining gap components, split by subtype:
                     undeclared_coproduct (a non-exempt extra with the
                     coproduct role), extra_principal_product (an extra
                     principal product), missing_other (a missing node
                     with no formula/scaffold proxy).  No identity or
                     near-identity route is claimed for the latter two.
unknown            : no gap component or unparseable proxy.

Destination
-----------
fixable (可修)          : structural_near / bookkeeping_exempt /
                          other.undeclared_coproduct
pending_cofactor (待裁定): cofactor
abandon (放弃)          : other.extra_principal_product /
                          other.missing_other (this round only, not a
                          permanent verdict)
unknown                 : unknown

Usage
-----
  python3 lever3_partial_classify.py \
      --batch-root /tmp/t_h_p0_r2/scoring \
      --runs-root /tmp/t_h_p0_r2/runs \
      --out-dir .
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

REPO = Path('/Volumes/CC/Enzyme_Agent/dependingv43')
sys.path.insert(0, str(REPO / 'src'))

from rdkit import Chem, RDLogger  # noqa: E402
from rdkit.Chem import rdMolDescriptors  # noqa: E402
from rdkit.Chem.Scaffolds import MurckoScaffold  # noqa: E402

RDLogger.DisableLog('rdApp.*')

from pathway_v43.pollutant.evaluation import (  # noqa: E402
    PPV1_CRITERIA_V2,
    _CRITERIA_V2_IDENTITIES,
    _event_participants,
    _export_states,
    match_reference_edges,
    match_reference_nodes,
)
from pathway_v43.pollutant.reference_graph import (  # noqa: E402
    load_reference_graph,
    reference_graph_sha256,
)

P0C = (REPO / 'docs/review_evidence/t_h_p0_2026-10-20/'
       'p0c_scoring_gaps.json')
METRICS_V1 = (REPO / 'reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json.v1')
METRICS_V2 = (REPO / 'reports/ppv1_s5b/t_h_2026-10-20/r2/metrics.json.v2')

PARTIAL_STATUS = 'matched_participant_coverage_partial'
STRICT_STATUS = 'matched_strict'
EXEMPT_FAMILIES = frozenset({'v1:H2O', 'v1:H+', 'v1:Pi', 'v1:PPi'})

CLASS_ORDER = ('bookkeeping_exempt', 'cofactor', 'structural_near',
               'other', 'unknown')
DEST_BY_CLASS = {
    'bookkeeping_exempt': 'fixable',
    'cofactor': 'pending_cofactor',
    'structural_near': 'fixable',
    'other': 'abandon',
    'unknown': 'unknown',
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def mol_profile(smiles: str) -> dict | None:
    """Candidate-side composition/scaffold profile (never serialized)."""
    if not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    try:
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol)
    except Exception:
        scaffold = ''
    symbols = {a.GetSymbol() for a in mol.GetAtoms()}
    return {
        'formula': rdMolDescriptors.CalcMolFormula(mol),
        'heavy': mol.GetNumHeavyAtoms(),
        'scaffold_sha12': hashlib.sha256(
            (scaffold or '').encode('utf-8')).hexdigest()[:12] if scaffold else None,
        'has_P': 'P' in symbols,
        'has_S': 'S' in symbols,
        'has_N': 'N' in symbols,
        'has_C': 'C' in symbols,
    }


def is_cofactor(profile: dict | None, role: str | None) -> bool:
    """Cofactor/cosubstrate signature; no identity strings emitted.

    A non-exempt extra with role ``cosubstrate`` is treated as the
    cofactor/cosubstrate class (O2/H2O2/NAD-scale redox or carrier
    species): chemistry necessity goes to sister.  The scale fallback
    catches a large cofactor even when the role label is coproduct
    (e.g. NADH on the product side).
    """
    if not profile:
        return False
    heavy = profile['heavy'] or 0
    if str(role or '') == 'cosubstrate':
        return True
    if heavy >= 30 and profile['has_N'] and (
            profile['has_P'] or profile['has_S']):
        return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch-root', default='/tmp/t_h_p0_r2/scoring')
    ap.add_argument('--runs-root', default='/tmp/t_h_p0_r2/runs')
    ap.add_argument('--out-dir', default='.')
    args = ap.parse_args()
    out_dir = Path(args.out_dir).resolve()
    sc = Path(args.batch_root)
    runs = Path(args.runs_root)

    p0c = json.loads(P0C.read_text())
    p0c_rows = p0c['rows_partial']
    assert len(p0c_rows) == 53, len(p0c_rows)
    p0c_class = {str(r['qid_prefix']): str(r['class'])
                 for r in p0c_rows}
    p0c_pool = {str(r['qid_prefix']): str(r['pool'])
                for r in p0c_rows}
    p0c_remap = {str(r['qid_prefix']): str(r['remap'])
                 for r in p0c_rows}

    metrics_v1 = json.loads(METRICS_V1.read_text())
    metrics_v2 = json.loads(METRICS_V2.read_text())
    m1 = {str(r['qid']): r['main'] for r in metrics_v1['per_qid']}
    m2 = {str(r['qid']): r['main'] for r in metrics_v2['per_qid']}
    v2_partial = {q for q, row in m2.items()
                  if row.get('match_status') == PARTIAL_STATUS}
    prefix_to_qid = {}
    for q in sorted(v2_partial):
        hits = [p for p in p0c_class if q.startswith(p)]
        assert len(hits) == 1, (q, hits)
        prefix_to_qid[hits[0]] = q
    assert set(prefix_to_qid) == set(p0c_class), 'p0c prefixes unresolved'
    p0c_partial = [prefix_to_qid[str(r['qid_prefix'])]
                   for r in p0c_rows]
    assert len(p0c_partial) == 53
    assert set(p0c_partial) == v2_partial, (
        'p0c partial set != metrics v2 partial set')
    t1_qids = sorted(
        q for q in m1
        if m1[q].get('match_status') == PARTIAL_STATUS
        and m2.get(q, {}).get('match_status') == STRICT_STATUS
        and m2.get(q, {}).get('rank') == 1)
    assert len(t1_qids) == 5, len(t1_qids)
    assert not (set(t1_qids) & set(p0c_partial)), \
        'T-1 redeemed qids must be outside the 53 partial set'

    manifest = json.loads((sc / 'batch_manifest.json').read_text())
    entries = {str(e['qid']): e for e in manifest['entries']}
    missing_entries = [q for q in p0c_partial if q not in entries]
    assert not missing_entries, missing_entries[:3]

    exempt_by_cn = _CRITERIA_V2_IDENTITIES['family_by_cn']
    rows = []
    component_totals = collections.Counter()
    tier_totals = collections.Counter()
    unknown_fields = collections.Counter()

    for qid in p0c_partial:
        prefix = qid[:20]
        entry = entries[qid]
        graph_path = sc / str(entry['graph_rel'])
        graph = load_reference_graph(graph_path)
        assert reference_graph_sha256(graph) == entry['graph_sha256'], qid
        run_id = str(entry['run_id'])
        payload_files = sorted(
            (runs / run_id / 'native_export').glob('*/payload.json'))
        assert len(payload_files) == 1, (qid, len(payload_files))
        payload = json.loads(payload_files[0].read_text())
        states = _export_states(payload)
        node_matches = match_reference_nodes(
            graph, payload, criteria_version=PPV1_CRITERIA_V2)
        edge_matches = match_reference_edges(
            graph, payload, node_matches,
            criteria_version=PPV1_CRITERIA_V2)
        partial_edges = [e for e in edge_matches
                         if e.get('match_status') == PARTIAL_STATUS]
        assert partial_edges, qid
        strict_by_node = {
            str(e['node_id']): set(e.get('matched_state_ids') or [])
            for e in node_matches
            if e.get('match_status') == 'strict_structure'}
        node_roles = {str(e['node_id']): str(e.get('role') or '')
                      for e in node_matches}
        events_by_id = {str(e.get('event_id')): e
                        for e in payload.get('events') or []}

        counts = collections.Counter()
        other_role_counts = collections.Counter()
        n_events = 0
        direction_labels = []
        tier_counts = collections.Counter()
        for edge in partial_edges:
            for tier, n in (edge.get('criteria_v2_tier_counts') or {}).items():
                tier_counts[str(tier)] += int(n)
            edge_def = next(
                (x for x in graph.get('edges') or []
                 if str(x.get('edge_id')) == str(edge.get('edge_id'))), {})
            from_ids = [str(x) for x in edge_def.get('from_node_ids') or []]
            to_ids = [str(x) for x in edge_def.get('to_node_ids') or []]
            from_states = set().union(*(
                strict_by_node.get(n, set()) for n in from_ids)) \
                if from_ids else set()
            to_states = set().union(*(
                strict_by_node.get(n, set()) for n in to_ids)) \
                if to_ids else set()
            required_states = from_states | to_states
            required_cn = {states.get(s, {}).get('cn_identity')
                           for s in required_states}
            required_profiles = [
                mol_profile(states.get(s, {}).get('smiles_isomeric', ''))
                for s in required_states]
            required_formulas = {p['formula'] for p in required_profiles
                                 if p}
            for ce in edge.get('coverage_mismatch_events') or []:
                n_events += 1
                direction_labels.append(str(
                    ce.get('participant_coverage') or 'unknown'))
                event = events_by_id.get(str(ce.get('event_id'))) or {}
                participants = _event_participants(event)
                reactants = {str(p.get('state_ref')) for p in participants
                             if str(p.get('side')) == 'reactant'}
                products = {str(p.get('state_ref')) for p in participants
                            if str(p.get('side')) == 'product'}
                role_by_state = {str(p.get('state_ref')):
                                 str(p.get('role') or '')
                                 for p in participants}

                for side, event_side, required_side in (
                        ('reactant', reactants, from_states),
                        ('product', products, to_states)):
                    extras = event_side - required_side
                    for sid in sorted(extras):
                        state = states.get(sid) or {}
                        cn = state.get('cn_identity', '')
                        profile = mol_profile(
                            state.get('smiles_isomeric', ''))
                        family = exempt_by_cn.get(cn)
                        role = role_by_state.get(sid)
                        same_identity_required = cn in required_cn
                        same_formula_required = bool(
                            profile and profile['formula'] in
                            required_formulas)
                        if family in EXEMPT_FAMILIES:
                            counts['exempt_family_components'] += 1
                        elif is_cofactor(profile, role):
                            counts['cofactor_components'] += 1
                        elif same_identity_required:
                            counts['bookkeeping_role_components'] += 1
                        elif same_formula_required:
                            counts['structural_extra_components'] += 1
                        else:
                            counts['other_extra_components'] += 1
                            other_role_counts[str(role or 'unknown')] += 1
                            if not profile:
                                unknown_fields['extra_profile_unparseable'] += 1

                # Missing reference nodes: a node is missing when none of
                # its strict matched candidate states ("identity proxies")
                # appears on the event side.  Proxies are candidate states,
                # so no reference structure text is read here.
                for side, event_side, node_ids in (
                        ('reactant', reactants, from_ids),
                        ('product', products, to_ids)):
                    for nid in node_ids:
                        proxies = strict_by_node.get(nid, set())
                        if not proxies or (proxies & event_side):
                            continue
                        counts['missing_nodes'] += 1
                        proxy_profiles = [
                            mol_profile(states.get(s, {}).get(
                                'smiles_isomeric', ''))
                            for s in sorted(proxies)]
                        proxy_profiles = [p for p in proxy_profiles if p]
                        if not proxy_profiles:
                            counts['missing_unknown'] += 1
                            unknown_fields[
                                'missing_proxy_unparseable'] += 1
                            continue
                        event_profiles = [
                            mol_profile(states.get(s, {}).get(
                                'smiles_isomeric', ''))
                            for s in event_side]
                        event_profiles = [p for p in event_profiles if p]
                        near = False
                        for proxy in proxy_profiles:
                            for cand in event_profiles:
                                if proxy['formula'] == cand['formula']:
                                    near = True
                                    break
                                if proxy['scaffold_sha12'] and \
                                        proxy['scaffold_sha12'] == \
                                        cand['scaffold_sha12'] and \
                                        max(proxy['heavy'], cand['heavy']) >= 6:
                                    near = True
                                    break
                            if near:
                                break
                        if near:
                            counts['missing_near_components'] += 1
                        else:
                            counts['missing_other_components'] += 1

        has_extra = any(counts[k] for k in (
            'exempt_family_components', 'cofactor_components',
            'bookkeeping_role_components', 'structural_extra_components',
            'other_extra_components'))
        has_missing = counts['missing_nodes'] > 0
        if has_extra and has_missing:
            component_direction = 'mixed_components'
        elif has_extra:
            component_direction = 'extra'
        elif has_missing:
            component_direction = 'missing'
        else:
            component_direction = 'unknown'

        if counts['missing_near_components']:
            klass = 'structural_near'
        elif counts['cofactor_components']:
            klass = 'cofactor'
        elif (counts['structural_extra_components'] or
              counts['bookkeeping_role_components']):
            klass = 'structural_near'
        elif has_extra or has_missing:
            non_exempt = (
                counts['other_extra_components'] +
                counts['missing_other_components'] +
                counts['missing_unknown'])
            if counts['exempt_family_components'] and non_exempt == 0:
                klass = 'bookkeeping_exempt'
            else:
                klass = 'other'
        else:
            klass = 'unknown'

        other_subtype = ''
        if klass == 'other':
            if other_role_counts.get('principal_product'):
                other_subtype = 'extra_principal_product'
            elif counts['missing_other_components'] or \
                    counts['missing_unknown']:
                other_subtype = 'missing_other'
            elif other_role_counts.get('coproduct'):
                other_subtype = 'undeclared_coproduct'
            else:
                other_subtype = 'other'
            destination = ('fixable' if other_subtype ==
                           'undeclared_coproduct' else 'abandon')
        else:
            destination = DEST_BY_CLASS[klass]

        notes = []
        if klass == 'bookkeeping_exempt':
            notes.append(
                '簿记族身份;v2 tier v1_exempt='
                f"{tier_counts.get('v1_exempt', 0)}/not_exempt="
                f"{tier_counts.get('not_exempt_maintains_partial', 0)}")
        if p0c_class[prefix] != component_direction and \
                not (p0c_class[prefix] == 'extra' and
                     component_direction == 'mixed_components'):
            notes.append(
                f'p0c事件形态={p0c_class[prefix]};逐事件差集='
                f'{component_direction}')
        if counts['bookkeeping_role_components']:
            notes.append('含参考侧同身份错侧/重复(簿记角色)')
        if counts['cofactor_components']:
            if klass == 'cofactor':
                notes.append('辅因子/共底物(化学裁定)')
            else:
                notes.append('含次要辅因子/共底物成分(主缺口非辅因子)')
        if counts['missing_near_components']:
            notes.append('缺参考主产物与事件产物同式/同骨架(身份归一候选)')
        if other_subtype == 'undeclared_coproduct':
            notes.append('未声明副产物(共产物声明/忽略档修复面;'
                         '不得删真实副产物)')
        elif other_subtype == 'extra_principal_product':
            notes.append('多声明主产物(化学裁定前放弃)')
        elif other_subtype == 'missing_other':
            notes.append('缺主产物且无可接受近结构(放弃)')
        elif other_subtype == 'other':
            notes.append('其他覆盖缺口(放弃)')
        if p0c_pool[prefix] == 'empty':
            notes.append('空池')

        row = {
            'qid': qid,
            'qid_prefix': prefix,
            'pool': p0c_pool[prefix],
            'remap': p0c_remap[prefix],
            'p0c_mechanical_direction': p0c_class[prefix],
            'component_direction': component_direction,
            'n_mismatch_events': n_events,
            'n_v2_v1_exempt_occurrences':
                tier_counts.get('v1_exempt', 0),
            'n_v2_not_exempt_occurrences':
                tier_counts.get('not_exempt_maintains_partial', 0),
            'p0c_event_coverage_labels': dict(
                collections.Counter(direction_labels)),
            'n_exempt_family_components':
                counts['exempt_family_components'],
            'n_cofactor_components': counts['cofactor_components'],
            'n_bookkeeping_role_components':
                counts['bookkeeping_role_components'],
            'n_structural_extra_components':
                counts['structural_extra_components'],
            'n_other_extra_components': counts['other_extra_components'],
            'n_missing_nodes': counts['missing_nodes'],
            'n_missing_near_components':
                counts['missing_near_components'],
            'n_missing_other_components':
                counts['missing_other_components'],
            'n_missing_unknown': counts['missing_unknown'],
            'component_class': klass,
            'other_subtype': other_subtype,
            'destination': destination,
            't1_relation': 'outside_53_redeemed' if qid in t1_qids
                           else 'not_t1_redeemed',
            'notes': ';'.join(notes),
        }
        rows.append(row)
        tier_totals.update(tier_counts)
        component_totals.update({
            'exempt_family_components': counts[
                'exempt_family_components'],
            'cofactor_components': counts['cofactor_components'],
            'bookkeeping_role_components':
                counts['bookkeeping_role_components'],
            'structural_extra_components':
                counts['structural_extra_components'],
            'other_extra_components': counts['other_extra_components'],
            'missing_nodes': counts['missing_nodes'],
            'missing_near_components':
                counts['missing_near_components'],
            'missing_other_components':
                counts['missing_other_components'],
            'missing_unknown': counts['missing_unknown'],
        })

    # ---- closure and aggregate checks ----
    assert len(rows) == 53, len(rows)
    assert len({r['qid'] for r in rows}) == 53
    assert all(r['component_class'] in CLASS_ORDER for r in rows)
    assert all(r['destination'] in
               {'fixable', 'pending_cofactor', 'abandon', 'unknown'}
               for r in rows)
    assert all(r['t1_relation'] == 'not_t1_redeemed' for r in rows)
    assert not unknown_fields.get('partial_without_gap_component')
    by_class = collections.Counter(r['component_class'] for r in rows)
    by_dest = collections.Counter(r['destination'] for r in rows)
    by_direction = collections.Counter(
        r['component_direction'] for r in rows)
    by_p0c = collections.Counter(
        r['p0c_mechanical_direction'] for r in rows)
    assert by_class['unknown'] == 0
    assert by_dest['unknown'] == 0
    assert sum(by_class.values()) == 53
    # bookkeeping_exempt may be 0 expected; kept informational, not asserted
    # until the first full run is reviewed.
    by_other_subtype = collections.Counter(
        r['other_subtype'] for r in rows if r['other_subtype'])
    assert sum(by_other_subtype.values()) == by_class.get('other', 0)

    # class x destination must be deterministic; the only class whose
    # destination splits is "other" (undeclared coproduct is fixable,
    # extra principal product / missing-other is abandon).
    for row in rows:
        if row['component_class'] == 'other':
            expected = ('fixable' if row['other_subtype'] ==
                        'undeclared_coproduct' else 'abandon')
            assert row['destination'] == expected, row['qid_prefix']
        else:
            assert row['destination'] == \
                DEST_BY_CLASS[row['component_class']]

    result = {
        'schema': 't-h-lever3-partial-table-1',
        'generated_at_utc': __import__('datetime').datetime.utcnow()
        .replace(microsecond=0).isoformat() + 'Z',
        'domain_tag': '298',
        'data_scope': 'real',
        'batch': 't_h_s5b_298_20261020r2',
        'task': ('teacher lever 3: 53 partial coverage-gap classification, '
                 'T-1 relation and destination'),
        'red_lines': {
            'zero_model_calls': True,
            'zero_new_batches': True,
            'reference_structure_text_read_by_this_script': False,
            'reference_graph_consumed_only_inside_frozen_evaluator': True,
            'outputs_smiles_or_structure_text': False,
            'sealed_batch_or_main_tree_modified': False,
            'git_push': False,
        },
        'definitions': {
            'partial': ('metrics v2 match_status = '
                        'matched_participant_coverage_partial'),
            'p0c_mechanical_direction': (
                '题内 superset / partial_subset 事件形态分组; '
                '45/6/2 不是逐事件 missing-only 证明'),
            'component_direction': (
                '逐事件两侧 state_ref 差集: extra / missing / '
                'mixed_components'),
            'bookkeeping_exempt': (
                'extra identity in criteria-v2 exempt families '
                '(H2O/H+/Pi/PPi); only this class would be promoted'),
            'cofactor': (
                'non-exempt extra with role=cosubstrate (O2/H2O2/NAD-scale '
                'redox or carrier species), or >=30 heavy atoms with P/N '
                'or S/N; chemistry adjudication to sister'),
            'structural_near': (
                'missing reference node proxy vs event-side participant: '
                'same formula, or same Murcko scaffold with >=6 heavy '
                'atoms; plus same-identity wrong-side extras'),
            'other': (
                'remaining coverage gap, subtyped as undeclared '
                'coproduct / extra principal product / missing-other; '
                'no identity or near-identity route'),
            'destination': {
                'fixable': 'next-batch fix surface candidate (not a '
                           'conversion promise)',
                'pending_cofactor': 'chemistry adjudication to sister',
                'abandon': 'not in this round fix surface; re-open '
                           'requires new chemistry/contract decision',
                'unknown': 'insufficient evidence',
            },
        },
        't1_exemption': {
            'n_redeemed_outside_53': len(t1_qids),
            'qid_prefixes': [q[:20] for q in t1_qids],
            'evidence': ('metrics.json.v1 partial -> metrics.json.v2 '
                         'strict rank 1; criteria-v2 H2O exemption; '
                         'P0-C v2_exemptions 5 occurrences'),
            'all_outside_53': True,
        },
        'aggregates': {
            'n_partial': len(rows),
            'closure': '53/53',
            'by_component_class': {k: by_class.get(k, 0)
                                   for k in CLASS_ORDER},
            'by_destination': {
                'fixable': by_dest.get('fixable', 0),
                'pending_cofactor': by_dest.get('pending_cofactor', 0),
                'abandon': by_dest.get('abandon', 0),
                'unknown': by_dest.get('unknown', 0),
            },
            'by_other_subtype': dict(by_other_subtype),
            'by_component_direction': dict(by_direction),
            'by_p0c_mechanical_direction': dict(by_p0c),
            'class_x_destination': {
                k: dict(collections.Counter(
                    r['destination'] for r in rows
                    if r['component_class'] == k))
                for k in CLASS_ORDER},
            'other_subtype_x_destination': {
                k: dict(collections.Counter(
                    r['destination'] for r in rows
                    if r['other_subtype'] == k))
                for k in sorted(by_other_subtype)},
            'component_totals': dict(component_totals),
            'v2_tier_totals': dict(tier_totals),
            'pool': dict(collections.Counter(r['pool'] for r in rows)),
            'remap': dict(collections.Counter(r['remap'] for r in rows)),
            'pool_x_class': {
                pool: dict(collections.Counter(
                    r['component_class'] for r in rows
                    if r['pool'] == pool))
                for pool in sorted({r['pool'] for r in rows})},
            'remap_x_class': {
                remap: dict(collections.Counter(
                    r['component_class'] for r in rows
                    if r['remap'] == remap))
                for remap in sorted({r['remap'] for r in rows})},
            'p0c_direction_x_class': {
                d: dict(collections.Counter(
                    r['component_class'] for r in rows
                    if r['p0c_mechanical_direction'] == d))
                for d in sorted({r['p0c_mechanical_direction']
                                 for r in rows})},
        },
        'unknown_fields': {
            'counts': dict(unknown_fields),
            'note': ('No row is class/destination unknown. Missing-node '
                     'reference identity is proxied by the strict matched '
                     'candidate state; no reference structure text is read '
                     'or emitted. Chemistry of real byproducts is not '
                     'adjudicated here.'),
        },
        'conversion_expectation': {
            'written': False,
            'note': ('No candidate-level gold evidence; 53 is a pool '
                     'count, not a promised conversion. Full-switch upper '
                     'bound +53 is an upper bound only.'),
        },
        'inputs': {
            'p0c': {'path': str(P0C), 'sha256': sha256_file(P0C)},
            'metrics_v1': {'path': str(METRICS_V1),
                           'sha256': sha256_file(METRICS_V1)},
            'metrics_v2': {'path': str(METRICS_V2),
                           'sha256': sha256_file(METRICS_V2)},
            'batch_manifest': {
                'path': str(sc / 'batch_manifest.json'),
                'sha256': sha256_file(sc / 'batch_manifest.json')},
            'staged_batch_root': str(sc),
            'staged_runs_root': str(runs),
        },
        'rows': rows,
    }
    out_path = out_dir / 'lever3_partial_table.json'
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1,
                                   sort_keys=False) + '\n')
    print('wrote', out_path)
    print('closure 53/53')
    print('class', dict(by_class))
    print('destination', dict(by_dest))
    print('direction', dict(by_direction))
    print('p0c direction', dict(by_p0c))
    print('component totals', dict(component_totals))
    print('t1 outside', [q[:20] for q in t1_qids])


if __name__ == '__main__':
    main()