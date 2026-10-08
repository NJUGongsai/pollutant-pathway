"""Assert observed R6 behavior, including repaired controls and the residual."""
import json
from pathlib import Path
p=Path(__file__).parent
d=json.loads((p/'results.json').read_text())
r5=json.loads((p/'r5_replay/results.json').read_text())
r4=json.loads((p/'r4_replay/results.json').read_text())
def v(k):return d[k]['result']
def admission(x):return x.get('audit',x)['admission'][0]
assert len(d)==10 and len(r5)==7 and len(r4)==19
assert sum(x['completed'] for x in r5.values())==6
assert sum(x['completed'] for x in r4.values())==10
assert v('legal_historical_conflict_roundtrip')['same_id']
assert v('legal_historical_conflict_roundtrip')['same_payload']
assert admission(v('legal_historical_conflict_roundtrip'))=='defer'
assert admission(v('legal_historical_satisfied_roundtrip'))=='expand'
for key in ('summary_tamper_from_dict_rejected','flag_tamper_from_dict_rejected','summary_tamper_direct_audit_rejected','flag_tamper_direct_audit_rejected','signature_not_in_requirements_rejected'):
    assert d[key]['error_type']=='ConditionContractError'
    assert d[key]['detail']['kind']=='context_snapshot_inconsistent'
assert d['signature_not_in_requirements_rejected']['detail']['check']=='signature_not_in_requirements'
assert d['fact_changed_kept_context_id_rejected']['detail']['kind']=='context_content_identity_mismatch'
x=v('derive_launders_empty_evaluation_with_existing_signature')
assert admission(x['before'])=='retain_conditional'
assert x['before']['candidate']['requirement_coverage']['unknown_keys']==['pH']
assert x['invalid_parent_audit']['detail']['kind']=='context_content_identity_mismatch'
assert admission(x['after_public_derive'])=='expand'
assert 'pH' not in x['after_public_derive']['candidate']['requirement_coverage']['essential_keys']
assert x['history'][0]['per_requirement']==[]
assert x['history'][0]['covered_requirement_signatures']==x['retained_signature']
assert admission(x['accepted_roundtrip'])=='expand'
assert admission(v('genuine_unknown_historical_requirement_retained'))=='retain_conditional'
for key,x in r5['known_absent_non_species_false_satisfied']['result'].items():
    assert admission(x)==('retain_conditional' if key=='temperature_C' else 'defer')
axes=r5['axis_controls_and_cross_axis_diagnostic']['result']
assert axes['initial_supported_reaction_contradicted']['circular']['unresolved_initial_supply']==[]
assert axes['initial_supported_reaction_contradicted']['circular']['unsupported_relation_cycles']==[['A','B']]
assert axes['initial_contradicted_later_regen']['circular']['unresolved_initial_supply']==[['A','B']]
assert axes['initial_contradicted_later_regen']['circular']['unsupported_relation_cycles']==[]
assert len(r4['old_R3_probe_segmented']['result']['caught_blocks'])==4
print('R6 previous controls, all captured rejection blocks, and one residual API false green confirmed.')
