"""R8 post-fix expectations for copied R7 storage probe; not old-gap assertion."""
from pathlib import Path
import sys, json
rows = [json.loads(x) for x in Path(sys.argv[1]).read_text().splitlines()]
by_case = {r['case']: r for r in rows}
assert len(rows) == 16 and len(by_case) == 16
assert by_case['metadata']['schema'] == 'ppv1-store-8'
for supply in ('none', 'prod_only', 'all'):
    valid = by_case[f'first_existing_appearance_{supply}_valid']
    assert valid['first']['outcome'] == {'created': True}
    assert valid['replay']['outcome'] == {'created': False}
    assert valid['replay']['zero_write']
    corrupt = by_case[f'first_existing_appearance_{supply}_corrupt']
    assert corrupt['first']['outcome']['error'] == 'Ppv1LedgerCorrupt'
    assert corrupt['first']['outcome']['kind'] == 'appearance_hash_corrupt'
    assert corrupt['first']['zero_write'] and corrupt['replay'] is None
for field, kind in [('cn_identity', 'state_row_corrupt'), ('schema_version', 'state_schema_corrupt'), ('state_id', 'state_inner_id_corrupt')]:
    rec = by_case[f'first_reused_semantic_{field}']['first']
    assert rec['outcome']['error'] == 'Ppv1LedgerCorrupt'
    assert rec['outcome']['kind'] == kind and rec['zero_write']
for mutation in ('none', 'reverse_manifest'):
    rec = by_case['multi_occurrence_' + mutation]
    assert rec['first']['outcome'] == {'created': True}
    assert rec['replay']['outcome'] == {'created': False}
    assert rec['replay']['zero_write']
for mutation in ('manifest_A_only', 'manifest_and_row_A', 'row_A_only', 'link_A_only'):
    rec = by_case['multi_occurrence_' + mutation]
    assert rec['first']['outcome'] == {'created': True}
    assert rec['replay']['outcome']['error'] == 'Ppv1LedgerCorrupt'
    expected = 'event_appearance_manifest_entry_missing' if mutation == 'row_A_only' else 'event_appearance_manifest_link_corrupt'
    assert rec['replay']['outcome']['kind'] == expected
    assert rec['replay']['zero_write']
print('R8 storage: 15 cases independently checked; R7-02 flips; R6-04/R6-05 and legal controls preserved.')
