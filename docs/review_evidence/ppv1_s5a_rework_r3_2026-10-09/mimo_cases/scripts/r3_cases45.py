from __future__ import annotations
"""S5a r3 补控(自构造,如实标注:复审 R3 §4.2 的 4 号"checked 正规
合法新内容+新 context_id 但旧地址"补控**未在本审执行**、5 号合法
新地址正控**须构造**;本脚本为 r3 实施方构造,不冒称复审已执行)。

共用本审 mimo 专项的 fresh iso 树与同一 layout:
  - 案 4(load + 公共 start/resume):checked 正规合法新内容
    (build_path_context + build_condition_fact 全 checked 构造)写入
    旧 ctx: 地址(重封 H07)⇒ 首消费 context_reference_binding_
    mismatch 拒;events 0;坏(合法载荷占旧地址)artifact 保全;
    同一载荷存自己的新地址可正常消费(冻结判据四"重建半边")。
  - 案 5(load + 公共 start/resume):合法新内容新 ID 新地址 +
    parent_context_ref 链允许;正常子上下文/场景转换保持(transition
    派生子 ctx 存新地址、followup 沿新引用、全 run 地址-身份对应)。
每案前后全表快照,逐表披露(不伪报全表零变化)。
"""
import copy, json, os, sqlite3, sys
from pathlib import Path

OBSERVE = os.environ.get('OBSERVE', '') == '1'

HERE = Path(__file__).resolve().parents[1]
SCRATCH = HERE.parent
sys.path[:0] = [str(SCRATCH / 'iso' / 'src'),
                str(SCRATCH / 'iso' / 'tests')]
from pathway_v43.pollutant.path_context import (
    ConditionFact, PathContext, Requirement, Dependency,
    build_condition_fact, build_path_context, build_requirement,
    derive_child_context)
from pathway_v43.pollutant.production import (
    persist_context, load_context, CONTEXT_ARTIFACT_NAME)
from pathway_v43.storage.artifact_store import ArtifactStore
from pathway_v43.domain.models import content_hash
from pathway_v43.config import resolve_config
from pathway_v43.workflow.runner import start_run, resume_run
from pathway_v43.storage.run_identity import PROFILE_POLLUTANT_PATHWAY_V1
from pathway_v43.pollutant.search import SearchCrashInjection
from test_ppv1_s4a_endpoint import spec


def save(name, obj):
    p = HERE / 'results' / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False,
                            default=str) + '\n')


def cap(fn, *args, **kwargs):
    try:
        return {'ok': True, 'return': fn(*args, **kwargs)}
    except Exception as e:
        return {'ok': False, 'type': type(e).__name__,
                'error': str(e),
                'detail': getattr(e, 'detail', None)}


def table_snapshot(path):
    c = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    d = {}
    for row in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
            " ORDER BY name"):
        n = row[0]
        d[n] = [dict(x) for x in c.execute(
            'SELECT * FROM ' + n + ' ORDER BY rowid')]
    c.close()
    return d


def table_deltas(before, after):
    return {name: len(after.get(name, [])) - len(before.get(name, []))
            for name in sorted(set(before) | set(after))}


def ctx_files(artifacts):
    return sorted(artifacts.base.glob(
        f'ctx:*/{CONTEXT_ARTIFACT_NAME}.json'))


def req():
    return build_requirement(
        key='electron_acceptor', level='essential', value='O2',
        source_refs=['src:synthetic-necessity'])


def checked_facts():
    return [build_condition_fact(key='electron_acceptor', value=None,
                                 status='unknown',
                                 source_ref='src:synthetic-unknown'),
            build_condition_fact(key='electron_acceptor', value='O2',
                                 status='known_present',
                                 source_ref='src:synthetic-present')]


def legal_new_context():
    """checked 正规合法新内容(全部事实经 checked 构造器;unknown 值
    None)。与控制内容不同(新增一条已知道)⇒ 新 context_id。"""
    return build_path_context(
        condition_facts=[
            build_condition_fact(key='electron_acceptor', value='O2',
                                 status='known_present',
                                 source_ref='src:synthetic-present-2')],
        accumulated_requirements=[req()],
        assessment_scope=['electron_acceptor'])


def case4():
    out = {'case': '4 checked legal new content + new context_id at'
                   ' OLD address (self-constructed this round)',
           'origin': 'r3 implementer-constructed; the r3 review did NOT'
                     ' execute this control (its planned fixture was'
                     ' platform-blocked); not claimed as'
                     ' review-executed'}
    # ---- load 级 ----
    runs = SCRATCH / 'case4_runs'
    artifacts = ArtifactStore(runs, 'c4-load')
    base = build_path_context(condition_facts=checked_facts(),
                              accumulated_requirements=[req()],
                              assessment_scope=['electron_acceptor'])
    ref = persist_context(artifacts, base)
    legal_new = legal_new_context()
    assert OBSERVE or legal_new.context_id != ref
    path = artifacts._path('ctx:' + ref, CONTEXT_ARTIFACT_NAME)
    envelope = json.loads(path.read_text(encoding='utf-8'))
    envelope['payload'] = legal_new.to_dict()
    envelope['payload_hash'] = content_hash(envelope['payload'])
    path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False)
                    + '\n')
    mutation = json.loads(path.read_text(encoding='utf-8'))
    load_old = cap(load_context, artifacts, ref)
    # 同一载荷存自己的新地址(合法重建半边)
    new_ref = persist_context(artifacts, legal_new)
    load_new = cap(load_context, artifacts, new_ref)
    out['load'] = {
        'old_address_load': load_old,
        'new_address_load': load_new,
        'expected_recovered': legal_new.context_id,
        'artifact_after': json.loads(path.read_text(
            encoding='utf-8')),
        'ctx_files': [str(p.relative_to(artifacts.base))
                      for p in ctx_files(artifacts)],
        'artifact_preserved': json.loads(path.read_text(
            encoding='utf-8')) == mutation,
    }
    assert OBSERVE or load_old['ok'] is False
    assert OBSERVE or load_old['detail']['kind'] == \
        'context_reference_binding_mismatch'
    assert OBSERVE or load_old['detail']['expected_context_ref'] == ref
    assert OBSERVE or load_old['detail']['recovered_context_id'] == \
        legal_new.context_id
    assert OBSERVE or load_new['ok'] is True
    # ---- 公共链 ----
    run_id = 'c4-public'
    plan = {'condition_facts': [
        {'key': 'electron_acceptor', 'value': 'O2',
         'status': 'unknown', 'source_ref': 'src:synthetic-unknown'},
        {'key': 'electron_acceptor', 'value': 'O2',
         'status': 'known_present', 'source_ref': 'src:synthetic'}],
        'pools': {'CCO': [spec('A', 'CC=O', 'donor-A',
                                coproducts=['[H][H]'],
                                requirements=[{
                                    'key': 'electron_acceptor',
                                    'level': 'essential', 'value': 'O2',
                                    'source_refs': [
                                        'src:synthetic-necessity']}])]},
        'schedule_budget': {'max_select': 1}}
    started = cap(start_run, config=resolve_config(), runs_root=runs,
                  run_id=run_id, smiles='CCO', max_depth=2,
                  max_expansions=5, max_frontier_width=2, finder=object(),
                  scripted=True, profile=PROFILE_POLLUTANT_PATHWAY_V1,
                  ppv1_plan=plan, crash_after='after_claim')
    assert OBSERVE or started['ok'] is False and \
        started['type'] == 'SearchCrashInjection', started
    artifacts = ArtifactStore(runs, run_id)
    files = ctx_files(artifacts)
    assert OBSERVE or len(files) == 1, files
    root_ref = json.loads(files[0].read_text(
        encoding='utf-8'))['payload']['context_id']
    legal_new = legal_new_context()
    path = artifacts._path('ctx:' + root_ref, CONTEXT_ARTIFACT_NAME)
    envelope = json.loads(path.read_text(encoding='utf-8'))
    envelope['payload'] = legal_new.to_dict()
    envelope['payload_hash'] = content_hash(envelope['payload'])
    path.write_text(json.dumps(envelope, indent=2,
                               ensure_ascii=False) + '\n')
    mutation = json.loads(path.read_text(encoding='utf-8'))
    pre = table_snapshot(runs / run_id / 'pollutant.sqlite')
    resumed = cap(resume_run, config=resolve_config(), runs_root=runs,
                  run_id=run_id)
    post = table_snapshot(runs / run_id / 'pollutant.sqlite')
    out['public'] = {
        'start': started, 'old_reference': root_ref,
        'expected_recovered': legal_new.context_id,
        'resume': resumed,
        'table_deltas': table_deltas(pre, post),
        'table_counts_after': {k: len(v)
                               for k, v in post.items()},
        'artifact_preserved': json.loads(path.read_text(
            encoding='utf-8')) == mutation,
        'ctx_files': [str(p.relative_to(artifacts.base))
                      for p in ctx_files(artifacts)],
    }
    assert OBSERVE or resumed['ok'] is False
    assert OBSERVE or resumed['detail']['kind'] == \
        'context_reference_binding_mismatch'
    deltas = out['public']['table_deltas']
    assert OBSERVE or deltas['events'] == 0
    assert OBSERVE or [n for n, d in deltas.items() if d == 1] == [
        'budget_reservations', 'search_actions',
        'search_commit_records']
    save('r3_case4_checked_legal_old_address.json'
          + ('.observe' if OBSERVE else ''), out)
    return out


def case5():
    out = {'case': '5 legal new content + new ID + NEW address +'
                   ' parent_context_ref chain (self-constructed this'
                   ' round)',
           'origin': 'r3 implementer-constructed; the r3 review'
                     ' required this positive control to be constructed'
                     ' (5 号须构造); not claimed as review-executed'}
    # ---- load 级 ----
    runs = SCRATCH / 'case5_runs'
    artifacts = ArtifactStore(runs, 'c5-load')
    parent = build_path_context(condition_facts=checked_facts(),
                                accumulated_requirements=[req()],
                                assessment_scope=['electron_acceptor'])
    parent_ref = persist_context(artifacts, parent)
    restored = load_context(artifacts, parent_ref)
    child = derive_child_context(
        restored,
        scenario_transition={
            'source_ref': 'user:switch-anaerobic',
            'new_phase_id': 'phase-1',
            'new_scenario_ref': 'scenario-anaerobic'},
        step_edge_ref='hyp-c5')
    child_ref = persist_context(artifacts, child)
    child_load = cap(load_context, artifacts, child_ref)
    out['load'] = {
        'parent_ref': parent_ref, 'child_ref': child_ref,
        'child_parent_context_ref': child.parent_context_ref,
        'child_load': child_load,
        'ctx_files': [str(p.relative_to(artifacts.base))
                      for p in ctx_files(artifacts)],
    }
    assert OBSERVE or child.context_id != parent_ref
    assert OBSERVE or child.parent_context_ref == parent_ref
    assert OBSERVE or child_ref == child.context_id
    assert OBSERVE or child_load['ok'] is True
    # ---- 公共链(合法场景转换链) ----
    run_id = 'c5-public'
    plan = {'condition_facts': [
        {'key': 'electron_acceptor', 'value': 'O2',
         'status': 'unknown', 'source_ref': 'src:synthetic-unknown'}],
        'pools': {'CCO': [spec('A', 'CC=O', 'donor-A',
                                coproducts=['[H][H]'],
                                requirements=[{
                                    'key': 'electron_acceptor',
                                    'level': 'essential', 'value': 'O2',
                                    'source_refs': [
                                        'src:synthetic-necessity']}])]},
        'scenario_transitions': [{
            'after_hypothesis_key': 'A',
            'transition': {
                'source_ref': 'user:switch-anaerobic',
                'new_phase_id': 'phase-1',
                'new_scenario_ref': 'scenario-anaerobic'}}],
        'schedule_budget': {'max_select': 1}}
    started = cap(start_run, config=resolve_config(), runs_root=runs,
                  run_id=run_id, smiles='CCO', max_depth=2,
                  max_expansions=5, max_frontier_width=2, finder=object(),
                  scripted=True, profile=PROFILE_POLLUTANT_PATHWAY_V1,
                  ppv1_plan=plan, crash_after='after_claim')
    assert OBSERVE or started['ok'] is False and \
        started['type'] == 'SearchCrashInjection', started
    resumed = cap(resume_run, config=resolve_config(), runs_root=runs,
                  run_id=run_id)
    assert OBSERVE or resumed['ok'] is True, resumed
    artifacts = ArtifactStore(runs, run_id)
    address_identity = []
    payloads = {}
    for file in ctx_files(artifacts):
        envelope = json.loads(file.read_text(encoding='utf-8'))
        address_id = file.parent.name[len('ctx:'):]
        address_identity.append(
            {'address': 'ctx:' + address_id,
             'payload_context_id': envelope['payload']['context_id'],
             'match': envelope['payload']['context_id'] == address_id,
             'phase_id': envelope['payload'].get('phase_id'),
             'parent_context_ref':
                 envelope['payload'].get('parent_context_ref')})
        payloads[address_id] = envelope['payload']
    conn = sqlite3.connect(str(runs / run_id / 'pollutant.sqlite'))
    conn.row_factory = sqlite3.Row
    transitions = [dict(r) for r in conn.execute(
        "SELECT * FROM search_actions WHERE action_kind ="
        " 'scenario_transition'")]
    followups = [dict(r) for r in conn.execute(
        "SELECT * FROM search_actions WHERE action_kind = 'retrieve'"
        " ORDER BY created_at, action_id")]
    conn.close()
    followups = [r for r in followups if
                 (json.loads(r['payload']) or {}).get('source_event_id')]
    child_ids = [aid for aid, p in payloads.items()
                 if p.get('phase_id') == 'phase-1']
    root_ids = [aid for aid, p in payloads.items()
                if p.get('phase_id') != 'phase-1']
    out['public'] = {
        'start': started, 'resume': resumed,
        'ctx_address_identity': address_identity,
        'transitions': [{'status': t['status'],
                         'context_ref': t['context_ref']}
                        for t in transitions],
        'followup_context_refs': [str(r['context_ref'])
                                  for r in followups],
        'child_ids': child_ids, 'root_ids': root_ids,
    }
    assert OBSERVE or all(entry['match'] for entry in address_identity)
    assert OBSERVE or len(transitions) == 1 and transitions[0]['status'] == 'done'
    assert OBSERVE or child_ids and root_ids
    assert OBSERVE or {str(r['context_ref']) for r in followups} == set(child_ids)
    for cid in child_ids:
        assert OBSERVE or payloads[cid]['parent_context_ref'] in root_ids
    save('r3_case5_legal_new_address_chain.json'
          + ('.observe' if OBSERVE else ''), out)
    return out


if __name__ == '__main__':
    a = case4()
    b = case5()
    print(json.dumps({
        'case4_load_rejected': not a['load']['old_address_load']['ok'],
        'case4_public_rejected': not a['public']['resume']['ok'],
        'case4_new_address_load_ok': a['load']['new_address_load']['ok'],
        'case5_child_load_ok': b['load']['child_load']['ok'],
        'case5_public_resume_ok': b['public']['resume']['ok'],
        'case5_address_identity_all_match': all(
            e['match'] for e in b['public']['ctx_address_identity']),
        'observation_completed': True}, ensure_ascii=False))
