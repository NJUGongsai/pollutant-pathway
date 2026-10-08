"""Read-only oracle over this confirmation run's independently captured public-chain records.
Two original F02 necessary-condition assertions fail on current HEAD; controls must pass.
No test executes a second start/resume, writes SQL or touches archived evidence.
"""
from pathlib import Path
import json
import pytest
PKG=Path(__file__).resolve().parents[1]
ROWS={r['case']:r for r in json.loads((PKG/'logs/endpoint_readback.json').read_text())}

@pytest.mark.parametrize('name',['unknown_essential_condition','explicit_unknown_essential_condition'])
def test_original_f02_unknown_necessary_condition_limits_endpoint(name):
 row=ROWS[name]
 assert any('oxygen_regime' in c['route_assessment']['requirement_coverage']['unknown_keys'] for c in row['contexts'])
 assert len(row['native_export']['payload']['events'])==1
 # Source proof is independent source-reported input, never authenticated reality.
 ev=row['endpoint']['endpoint_evidence'][0]
 assert ev['conditions_environment'].startswith('aerobic')
 assert ev['proof_scope']=='source-reported; not verified by this repo'
 actual={'strict_endpoint':row['endpoint']['chemical_endpoint_assessment'], 'native_export':row['native_export']['payload']['endpoint_record']['chemical_endpoint_assessment'], 'v3_summary':row['v3_projection']['unprojectable_summaries']['endpoint_assessment']}
 assert all(v=='unknown' for v in actual.values()), {'original_acceptance':'S4 task §4.2 and §8 endpoint-condition unknown/control','name':name,'actual':actual}

@pytest.mark.parametrize('name,expected',[('known_essential_condition','supported_mineralization'),('unresolved_cyclic_dependency','unknown'),('supported_cyclic_dependency','supported_mineralization')])
def test_legal_supported_and_explicit_dependency_controls(name,expected):
 row=ROWS[name]
 assert row['endpoint']['chemical_endpoint_assessment']==expected
 assert row['native_export']['payload']['endpoint_record']['chemical_endpoint_assessment']==expected
 assert row['v3_projection']['unprojectable_summaries']['endpoint_assessment']==expected
 assert row['network_calls']==[]
