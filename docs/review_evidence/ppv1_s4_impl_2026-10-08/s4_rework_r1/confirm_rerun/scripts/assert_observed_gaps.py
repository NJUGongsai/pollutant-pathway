import json, sys
from pathlib import Path
p=Path(sys.argv[1])
a=json.loads((p/'observed/results.json').read_text())
b=json.loads((p/'observed_supplemental/results.json').read_text())
assert len(a['manifest_mutations'])==4 and all(x['response']['accepted'] and not x['core_digest_matches_declared'] for x in a['manifest_mutations'])
assert not b['single_necessary_ref']['original_response']['accepted'] and b['single_necessary_ref']['fake_response']['accepted']
assert len(a['positive_public_chain']['missing_outcomes'])==2
assert not b['missing_outcome']['direct_artifact_guard']['accepted'] and b['missing_outcome']['read_native_export_response']['accepted']
assert b['projection_only']['fake_projection_read']['accepted'] and b['projection_only']['native_refs_unchanged']
assert b['projection_only']['true_event_count']==1 and b['projection_only']['false_step_count']==0
assert b['projection_only']['true_deferred_count']==1 and b['projection_only']['false_deferred_count']==0
assert b['public_resume']['no_business_duplicate'] and b['public_resume']['settled_digest_stable']
print('All recorded gap observations and legitimate controls match; this is not a product pass.')
