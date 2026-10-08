"""R8 completion for the R7 chemistry probe tail cases.

The R7 reviewer probe (chemical_boundary_probe.py) uses
ChemicalState.from_dict directly (outside its capture wrapper) at line
123, so with the R8 fix the run stops there with the structured
rejection traceback (see r7_chemistry_probe_replay.stderr.txt — the
crash IS the from_dict entrance closing). This script re-runs the two
tail cases with the same capture semantics so the full case list is
covered. Synthetic only; no gold/benchmark/sealed material.
"""
import copy, json, runpy, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from pathway_v43.pollutant.chemstate import (
    ChemicalState, build_chemical_state_from_cn_only)
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission
fx = runpy.run_path(str(ROOT / 'tests/test_ppv1_r7_chem.py'))

def emit(case, **kw):
    print(json.dumps(dict(case=case, **kw), ensure_ascii=False,
                     sort_keys=True, default=str))

def capture(case, f, **meta):
    try:
        emit(case, ok=True, result=f(), **meta)
    except Exception as e:
        emit(case, ok=False, exception=type(e).__name__,
             message=str(e), detail=getattr(e, 'detail', {}), **meta)

def audit(states, hyp, ev):
    a = audit_hypothesis(hyp, states={st.state_id: st for st in states.values()},
                         context=fx['_aerobic_context'](), center_evidence=ev)
    return dict(admission=decide_admission(a))

ev = fx['_oxidation_evidence']()
base = fx['_states']('CCO', 'CC=O', '[H][H]')
hyp = fx['_hyp'](base, [('CCO', 1)], [('CC=O', 1), ('[H][H]', 1)],
                 group='C1-direct-restore')

# R7-01 chiral raw counterexample: from_dict entrance now rejects.
sub = 'F[C@H](Cl)CCO'
cev = fx['_donor_evidence'](sub, 'S_C_3', 'S_O_1', 'single', 'double')
prod = cev['bound_inputs']['product_identity']
cs = fx['_states'](sub, prod, '[H][H]')
ch = fx['_hyp'](cs, [(sub, 1)], [(prod, 1), ('[H][H]', 1)],
                group='C1-chiral-raw')
pay = cs[sub].to_dict()
pay['structure_smiles_raw'] = sub + ' |r|'
capture('C1_chiral_raw_unknown_flag',
        lambda: ChemicalState.from_dict(pay), restored_payload=pay)
# direct dataclass bypass of from_dict: audit entrance rejects.
direct = copy.copy(cs[sub])
direct.structure_smiles_raw = sub + ' |r|'
capture('C1_chiral_raw_direct_dataclass',
        lambda: audit({**cs, sub: direct}, ch, cev))
# CN-only honest unknown control (unchanged, must stay reachable).
legacy_states = copy.deepcopy(base)
legacy_states['CCO'] = ChemicalState.from_dict(
    build_chemical_state_from_cn_only('CCO').to_dict())
legacy_hyp = fx['_hyp'](legacy_states, [('CCO', 1)],
                        [('CC=O', 1), ('[H][H]', 1)],
                        group='C1-legacy-cn-only')
capture('C1_CN_only_honest_unknown_control',
        lambda: audit(legacy_states, legacy_hyp, ev))
