"""Assert recorded R6 observations, including CURRENT DEFECTS.

This is an evidence check, NOT the desired behavior after repair. It reads only
cx_boundary_probe.output.jsonl next to this file; it imports no repository code,
does not call RDKit, and creates no new probe inputs or results.
Run with python -B cx_assert_observed.py after replaying cx_boundary_probe.py.
"""
import json
from pathlib import Path

HEAD = '6d9020130a481866ce2f3b79933907a33d8cfc9e'
source = Path(__file__).resolve().with_name('cx_boundary_probe.output.jsonl')
records = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines() if line.strip()]

def check(condition, description):
    if not condition:
        raise AssertionError(description)

check(len(records) == 9, 'R6 evidence must contain exactly nine top-level records')
check(all(not any(k in r for k in ('exception_type', 'exception', 'traceback', 'error_type')) for r in records),
      'No top-level probe exception may be counted as an observed success')
cases = {r['case']: r for r in records}
check(len(cases) == 9, 'Case names must be unique')
check(set(cases) == {
    'meta', 'cx_registered_head_comma_appended_unknown',
    'rdkit_writer_generated_registered_content_spaces',
    'donor_public_ethanol_clean', 'donor_public_ethanol_current_r',
    'donor_public_ethanol_mapped_r', 'donor_public_ethanol_plain_r',
    'donor_public_ethanol_target_r', 'donor_public_specified_stereo_current_r',
}, 'All expected R6 cases must be present')
check(cases['meta']['head'] == HEAD, 'Recorded runtime must identify the audited R6 HEAD')

def accepted_identity(row, expected_identity):
    check(row['rdkit_parsed'] is True, 'RDKit must actually parse the recorded input')
    check(row['build']['accepted'] is True and row['strict']['accepted'] is True,
          'Recorded build/strict acceptance must hold')
    state = row['build']['value']
    check(state['smiles_isomeric'] == expected_identity, 'Factory identity must equal the recorded bare/retained control')
    check(row['strict']['value'] == expected_identity, 'Strict identity must equal the same control')
    check(set(state['representation_fidelity'].values()) == {'as_written'},
          'Current accepted input still declares all fidelity axes as_written')
    return state['state_id']

def rejected_unregistered(row):
    for entry in ('build', 'strict'):
        check(row[entry]['accepted'] is False, 'Both current public entries must reject this control')
        check(row[entry]['error_type'] == 'ChemicalStateError', 'Rejection must be the recorded chemical contract error')
        check(row[entry]['detail']['kind'] == 'unregistered_cx_class', 'Rejection must identify unregistered CX')

matrix_rows = cases['cx_registered_head_comma_appended_unknown']['rows']
check(len(matrix_rows) == 9, 'The recorded CX input matrix has nine rows')
matrix = {r['input']: r for r in matrix_rows}
bare_alanine = 'C[C@@H](N)C(=O)O'
rejected_unregistered(matrix[bare_alanine + ' |r|'])
check(matrix[bare_alanine + ' |r|']['rdkit_reemitted'] == bare_alanine,
      'The standalone r control is genuinely dropped by RDKit but rejected by guarded entries')
ordinary = matrix[bare_alanine + ' |atomProp:0.note.hello|']
with_r = matrix[bare_alanine + ' |atomProp:0.note.hello,r|']
ordinary_id = accepted_identity(ordinary, bare_alanine)
check(accepted_identity(with_r, bare_alanine) == ordinary_id,
      'CURRENT DEFECT: comma-appended r is accepted and shares the bare-normalized annotation control identity')
check(ordinary_id == 'cs_5110e7190bdbd9979a26', 'The recorded bare-normalized identity ID must match the audited observation')
check(with_r['rdkit_reemitted'] == ordinary['input'], 'RDKit must retain atomProp while dropping only the appended r')
accepted_identity(matrix['C1CCCCC1 |atomProp:0.note.hello,Ln:1|'], 'C1CCCCC1')
dat_control_id = accepted_identity(matrix['CO |SgD:0:note:hello::::|'], 'CO')
for s in ['CO |SgD:0:note:hello::::,r|', 'CO |SgD:0:note:a,b::::,r|']:
    check(accepted_identity(matrix[s], 'CO') == dat_control_id,
          'CURRENT DEFECT: registered DAT content plus appended r is accepted with the same bare identity')
accepted_identity(matrix['CCCCCC |Sg:n:1,2,3:3:ht:::,r|'], 'CCCCCC |Sg:n:1,2,3:3:ht:::|')
rejected_unregistered(matrix['CO |atomProp:0.note.hello,w:1.0|'])

writer_rows = cases['rdkit_writer_generated_registered_content_spaces']['rows']
check(len(writer_rows) == 6, 'The recorded writer matrix has six rows')
writer = {r['generation']: r for r in writer_rows}
for mode in ['label_space', 'atomprop_space', 'dat_space']:
    row = writer[mode]
    check(row['rdkit_parsed'] is True and row['rdkit_reemitted'] == row['input'],
          'Space-content cases must be legal RDKit-generated round-trip inputs')
    rejected_unregistered(row)  # CURRENT conservative over-rejection, not repair expectation.
for mode in ['label_no_space', 'atomprop_no_space', 'dat_comma']:
    check(accepted_identity(writer[mode], 'CO') == dat_control_id,
          'No-space and DAT-comma registered-content controls must retain the same CO identity')

def center_check(row):
    selected = [c for c in row['audit']['checks'] if c['name'] == 'transformation_center']
    check(len(selected) == 1, 'Each full audit must contain one center check')
    return selected[0]

for case in ['donor_public_ethanol_clean', 'donor_public_ethanol_current_r',
             'donor_public_ethanol_mapped_r', 'donor_public_specified_stereo_current_r']:
    row = cases[case]
    check(row['real_execution']['ok'] is True, 'The clean base AtomTool output must be genuine and successful')
    diag = row['diagnostic']
    check(diag['reaction_center_match'] is True and diag['strict_target_match'] is True,
          'Recorded R6 clean/current/mapped/chiral diagnostic axes must be True/True')
    check(diag['missing_info_reasons'] == [] and diag['declaration_mismatches'] == [],
          'Recorded acceptance must have no hidden unknown or declaration mismatch')
    center = center_check(row)
    check(center['status'] == 'verified' and center['detail']['product_coverage'] == 'full',
          'CURRENT DEFECT for flagged fields: center remains verified/full')
    check(row['admission'] == ['expand', ['R6:all_verified_no_conflict']],
          'Recorded clean/current/mapped/chiral public admission must reach R6')

clean = cases['donor_public_ethanol_clean']['diagnostic']['center_evidence']['bound_inputs']
flagged = cases['donor_public_ethanol_current_r']['diagnostic']['center_evidence']
check(flagged['proof_record']['current']['smiles'] == 'CCO |r|', 'Original r input must remain in the current proof record')
check(flagged['bound_inputs']['substrate_identity'] == clean['substrate_identity'] == 'CCO',
      'CURRENT DEFECT: current r identity is silently merged with the clean substrate control')
mapped = cases['donor_public_ethanol_mapped_r']['diagnostic']['center_evidence']['proof_record']['result']
check(mapped['product_mapped_smiles'].endswith(' |r|'), 'Mapped-product r must be present in the actually diagnosed input')
chiral = cases['donor_public_specified_stereo_current_r']['diagnostic']['center_evidence']
check(chiral['proof_record']['current']['smiles'] == 'F[C@H](Cl)CCO |r|', 'Specified-stereo control must carry original r')
check(chiral['bound_inputs']['substrate_identity'] == 'OCC[C@H](F)Cl',
      'CURRENT DEFECT: flagged specified-stereo substrate loses r in its bound identity')

for case in ['donor_public_ethanol_plain_r', 'donor_public_ethanol_target_r']:
    row = cases[case]
    check(row['diagnostic']['reaction_center_match'] is True and row['diagnostic']['strict_target_match'] is None,
          'Plain/target r must record True/None, not be overstated as incorrect R6 acceptance')
    check('target_or_result_unparseable' in row['diagnostic']['missing_info_reasons'],
          'Guarded strict branch must disclose its unknown result')
    check(center_check(row)['status'] == 'unknown', 'Plain/target r center audit must stay unknown')
    check(row['admission'][0] == 'retain_conditional', 'Plain/target r must retain, not expand')

print(json.dumps({'purpose':'R6 observed behavior evidence check, NOT post-repair expectations',
                  'head':HEAD,'records':len(records),'result':'all observed assertions passed'},ensure_ascii=False))
