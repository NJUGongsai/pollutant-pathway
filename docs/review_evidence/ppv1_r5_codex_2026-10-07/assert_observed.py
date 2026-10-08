"""Assert R5 observations and controls, not desired post-fix behavior."""
import json
from pathlib import Path

ROOT=Path(__file__).parent
def rows(name,key='probe'):
 return {d[key]:d for d in (json.loads(x) for x in (ROOT/name).read_text().splitlines()) if key in d}
ad=rows('admission_coverage_probe.output.jsonl')
for name in ('genuine_bound_control','genuine_hydrogenation_control','one_sided_product_unchecked_isomer_half','one_sided_cosubstrate_unchecked_to_same_product'):
 d=ad[name]
 assert d['center']['status']=='verified' and d['admission'][0]=='expand'
 assert all(c['status']=='verified' for c in d['audit']['checks'] if c['name'] in ('element_accounting','formal_charge_accounting'))
assert ad['old_two_sided_unchecked_control']['center']['status']=='unknown'
assert ad['old_two_sided_unchecked_control']['admission'][0]=='retain_conditional'
assert ad['observations']['verified_proof_scope'] is None
assert 'basis=)' in ad['observations']['verified_reason']
old=rows('r4_admission_probe_recheck.output.jsonl')
assert old['binding_only_two_identity_strings']['admission'][0]=='retain_conditional'
assert old['genuine_evidence_mutated_alignment_ref']['detail']['kind']=='center_evidence_integrity_mismatch'
assert old['strict_axis_type_str_false']['detail']['kind']=='center_evidence_type_violation'
assert old['real_fragment_products_separate_participants']['admission'][0]=='expand'
ch=rows('chemistry_boundary_probe.output.jsonl','case')
cx=ch['cx_raw_unregistered_r_and_Ln']['rows']
assert cx[0]['state']['state_id']==cx[1]['state']['state_id']
assert cx[2]['state']['state_id']==cx[3]['state']['state_id']
assert not cx[4]['accepted']
ez=ch['real_adjacent_sigma_break_removes_EZ']
assert ez['validation']['ok'] and ez['execution']['ok']
assert ez['diagnostic']['reaction_center_match'] is None
assert ez['actual_bond_diff']==ez['mirror_reparsed_bond_diff']
assert ez['actual_bond_diff']!=ez['mirror_in_memory_bond_diff']
co=json.loads((ROOT/'conditions_probe.results.json').read_text())
assert all(v['completed'] for v in co.values())
for d in co['known_absent_non_species_false_satisfied']['result'].values():assert d['audit']['admission'][0]=='expand'
snap=co['snapshot_from_dict_conflict_summary_and_flag_tamper']['result']
assert snap['before']['audit']['admission'][0]=='defer'
for k in ('summary_changed','has_gate_false'):assert snap[k]['audit']['admission'][0]=='expand'
st=rows('storage_boundary_probe.output.jsonl')
assert st['pre_stored_all_first_success_replay_corrupt']['first']['created']
assert st['pre_stored_all_first_success_replay_corrupt']['replay']['error']=='Ppv1LedgerCorrupt'
assert not st['pre_stored_partial_actual_source_deleted_replay_success']['replay']['result']['created']
assert st['supplied_all_manifest_control']['damaged_replay']['error']=='Ppv1LedgerCorrupt'
assert not st['manifest_nonempty_subset_tampered_replay_success']['replay']['result']['created']
assert st['existing_hypothesis_invalid_first_submit']['first']['created']
assert st['existing_hypothesis_invalid_first_submit']['replay']['detail']['kind']=='hypothesis_payload_id_corrupt'
bad=st['legacy_same_parent_wrong_sibling_source_accepted']
assert bad['actual_path_id']!=bad['expected_path_id_from_source']
assert bad['uncertainty_notes']==[] and bad['old_bytes_unchanged']
assert bad['imported_substrate']['structure_smiles_raw']!=bad['expected_raw']
assert '381 passed' in (ROOT/'pytest_output.txt').read_text()
print('R5 observed regressions and controls reproduced; this is not implementation acceptance.')
