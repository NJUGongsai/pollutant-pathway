import json,sys
from pathlib import Path
R=Path(sys.argv[1]);P=R/'package'; rows=[]
for x in json.loads((P/'results/mimo/conditions_summary.json').read_text())[:6]:
 name=x['name'];actual=x['public_evaluation_buckets'];expected='condition_unknown' if name in ['B1_requirement_K_298_vs_25C','B1_requirement_K_25_vs_25C','B1_requirement_F_77_vs_25C','B1_dimensionless_unit_unexpected'] else 'compatible'
 rows.append({'name':name,'expected_bucket':expected,'actual_buckets':actual,'passes_contract':actual=={expected:1}})
(P/'results/B1_contract_assertions.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
for x in rows:print(x['name'], 'PASS' if x['passes_contract'] else 'FAIL',x['expected_bucket'],x['actual_buckets'])
assert all(x['passes_contract'] for x in rows), '4 unsupported requirement-unit public classifications are wrongly classified despite disclosures; 2 lawful canonical/default controls remain.'
