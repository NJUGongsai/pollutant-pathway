from __future__ import annotations
import copy,hashlib,inspect,json,os,sys,traceback
from pathlib import Path
from unittest.mock import patch
ROOT=Path(sys.argv[1]); OUT=ROOT/'package'/'results'/'mimo'; WORK=ROOT/'work'/'mimo'; OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(ROOT/'current'/'tests'),str(ROOT/'current'/'src')]
import test_ppv1_s5a_evaluator as e
import test_ppv1_s5a_schema as s
from pathway_v43.pollutant.evaluation import evaluate_scientific,classify_condition_requirement,check_endpoint_claims
from pathway_v43.pollutant.path_context import build_requirement,build_path_context,build_condition_fact,assess_candidate_conditions
from pathway_v43.pollutant.preregistration import build_preregistration_template
from pathway_v43.domain.models import canonical_json

def save(n,x):
 p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n')

def req(key,value,**kwargs):
 return {**s.condition_scope(key,value), 'subject_scenario_ref':'', **kwargs}
def fact(key,value,status='known_present',unit=''):
 return {'key':key,'value':value,'status':status,'unit':unit,'source_ref':'src:synthetic-observation'}
CASES=[
 ('B1_requirement_K_298_vs_25C',req('temperature_C','298',unit='K'),[fact('temperature_C',25,unit='C')], 298,'point'),
 ('B1_requirement_K_25_vs_25C',req('temperature_C','25',unit='K'),[fact('temperature_C',25,unit='C')], 25,'point'),
 ('B1_requirement_F_77_vs_25C',req('temperature_C','77',unit='F'),[fact('temperature_C',25,unit='C')], 77,'point'),
 ('B1_requirement_C_25_vs_25C',req('temperature_C','25',unit='C'),[fact('temperature_C',25,unit='C')], 25,'point'),
 ('B1_requirement_unit_empty_25_vs_25C',req('temperature_C','25',unit=''),[fact('temperature_C',25,unit='C')], 25,'point'),
 ('B1_dimensionless_unit_unexpected',req('electron_acceptor','O2',unit='mg/L'),[fact('electron_acceptor','O2')], 'O2','entity'),
 ('B2_species_present_unknown',req('electron_acceptor','O2'),[fact('electron_acceptor','O2'),fact('electron_acceptor','O2','unknown')], 'O2','entity'),
 ('B2_species_unknown_present',req('electron_acceptor','O2'),[fact('electron_acceptor','O2','unknown'),fact('electron_acceptor','O2')], 'O2','entity'),
 ('B2_species_absent_unknown',req('electron_acceptor','O2'),[fact('electron_acceptor','O2','known_absent'),fact('electron_acceptor','O2','unknown')], 'O2','entity'),
 ('B2_species_unknown_absent',req('electron_acceptor','O2'),[fact('electron_acceptor','O2','unknown'),fact('electron_acceptor','O2','known_absent')], 'O2','entity'),
 ('B2_species_present_absent',req('electron_acceptor','O2'),[fact('electron_acceptor','O2'),fact('electron_acceptor','O2','known_absent')], 'O2','entity'),
 ('B2_species_absent_present',req('electron_acceptor','O2'),[fact('electron_acceptor','O2','known_absent'),fact('electron_acceptor','O2')], 'O2','entity'),
 ('B2_species_O2_NO3',req('electron_acceptor','O2'),[fact('electron_acceptor','O2'),fact('electron_acceptor','NO3')], 'O2','entity'),
 ('B2_species_NO3_O2',req('electron_acceptor','O2'),[fact('electron_acceptor','NO3'),fact('electron_acceptor','O2')], 'O2','entity'),
 ('B2_species_other_NO3_Fe3',req('electron_acceptor','O2'),[fact('electron_acceptor','NO3'),fact('electron_acceptor','Fe3')], 'O2','entity'),
 ('B2_species_other_Fe3_NO3',req('electron_acceptor','O2'),[fact('electron_acceptor','Fe3'),fact('electron_acceptor','NO3')], 'O2','entity'),
 ('B3_point_mismatch_disclosed',req('temperature_C','25',unit='C'),[fact('temperature_C',30,unit='C')], 25,'point'),
]


def conditions():
 summary=[]
 for ix,(name,rq,fs,value,basis) in enumerate(CASES):
  plan=e._plan(select=1);plan['condition_facts']=copy.deepcopy(fs)
  graph=s.synth_reference_graph(graph_id='rg-'+name)
  graph['edges']=graph['edges'][:1]
  graph['edges'][0]['condition_requirements']=[rq]
  for n in graph['nodes']:n['condition_scope']=[]
  runid='condition-'+name
  case={'name':name,'reference_graph':graph,'ppv1_plan':plan,'literal_classifier':classify_condition_requirement(rq,fs)}
  try:
   runs,out=e._run(WORK/name,runid,plan)
   read=e._reader(runs,runid)
   request=s.synth_evaluation_input(graphs=[graph],split_manifest=s.synth_split_manifest(graph_id=graph['reference_graph_id']),exports=[{'run_id':runid,'export_digest':out['native_export']['export_digest']}])
   request['run_identity']['run_id']=runid
   payload_read=read(request['native_path_exports'][0])
   result=evaluate_scientific(request,reference_graphs={graph['reference_graph_id']:graph},native_export_reader=read,preregistration=build_preregistration_template())
   case.update(run_output=out,evaluation_input=request,validated_reader_output=payload_read,evaluation_output=result)
   env=result['sample_results'][0]['environment_conflicts']
   if value is not None:
    frozen_facts=[build_condition_fact(**f) for f in fs]
    frozen_req=build_requirement(key=rq['key'],level=rq['required'],value=value,value_basis=basis,source_refs=rq['source_refs'])
    ctx=build_path_context(condition_facts=frozen_facts,assessment_scope=[rq['key']])
    assessed=assess_candidate_conditions(ctx,{'hypothesis_id':'synthetic-condition-compare','requirements':[frozen_req.to_dict()]})
    case.update(frozen_context=ctx.to_dict(),frozen_requirement=frozen_req.to_dict(),frozen_assessment=assessed.to_dict())
    public=assessed.to_dict()['per_requirement'][0] if 'per_requirement' in assessed.to_dict() else assessed.to_dict()
   else:
    public={'status':'not_directly_representable','reason':'Requirement has no status=known_absent field; this case is reference schema semantics only'}
    case['frozen_not_compared']=public
   row={'name':name,'literal_classifier':case['literal_classifier'],'public_evaluation_buckets':env['buckets'],'public_evaluation_status':result['status'],'frozen_assessment':public,'scoring_status':result['sample_results'][0]['scoring_status']}
   summary.append(row);case['summary']=row
   print(name,canonical_json(row),flush=True)
  except BaseException as ex:
   case['exception']={'type':type(ex).__name__,'message':str(ex),'detail':getattr(ex,'detail',None),'traceback':traceback.format_exc()}
   summary.append({'name':name,'exception':case['exception']});print('CASE_ERROR',name,type(ex).__name__,str(ex),flush=True)
  save('conditions/'+name+'.json',case)
 save('conditions_summary.json',summary)
 if any('exception' in x for x in summary):raise RuntimeError('One or more condition public cases failed before observation')

def matrix():
 selected=[(e,'test_s5_13_14_15_condition_axes_end_to_end'),(e,'test_s5_16_unknown_partial_not_confirmed_not_error'),(e,'test_s5_17_mineralization_negative_control'),(e,'test_s5_17_correct_mineralization_claim_with_root_carbon'),(e,'test_s5_18_stop_reason_is_not_endpoint'),(e,'test_s5_17_mineralization_without_root_carbon_flagged'),(e,'test_s5_19_unresolved_dependency_not_washed'),(e,'test_s5_20_budget_unexpanded_edge_separate_bucket'),(s,'test_s5_21_mixed_domain_refused'),(s,'test_s5_22_mixed_track_refused'),(s,'test_s5_23_preregistration_template_tbd_marking'),(e,'test_interface_mode_status_and_pending_semantics'),(e,'test_s5_24_repeat_evaluation_deterministic'),(e,'test_s5_25_natural_language_cannot_change_result'),(s,'test_s5_26_paid_provider_off_by_default'),(s,'test_s5_27_gold_output_write_guard'),(s,'test_s5_28_no_native_export_pending'),(e,'test_s5_28_unreadable_export_disclosed'),(s,'test_emitted_status_never_evaluated')]
 summary=[]
 for mod,name in selected:
  cap=[];original_eval=mod.evaluate_scientific;original_start=getattr(mod,'start_run',None);original_persist=getattr(mod,'persist_evaluation_output',None)
  def wrap(call,key):
   def wrapped(*args,**kwargs):
    row={'public_api':key,'args':copy.deepcopy(args),'kwargs':{k:copy.deepcopy(v) if not callable(v) else getattr(v,'__name__',repr(v)) for k,v in kwargs.items()}};cap.append(row)
    try:
     result=call(*args,**kwargs);row['result']=copy.deepcopy(result);return result
    except BaseException as ex:row['exception']={'type':type(ex).__name__,'message':str(ex),'detail':getattr(ex,'detail',None)};raise
   return wrapped
  patched=[patch.object(mod,'evaluate_scientific',wrap(original_eval,'evaluate_scientific'))]
  if original_start:patched.append(patch.object(mod,'start_run',wrap(original_start,'start_run')))
  if original_persist:patched.append(patch.object(mod,'persist_evaluation_output',wrap(original_persist,'persist_evaluation_output')))
  for p in patched:p.start()
  result={'name':name,'function_source':inspect.getsource(getattr(mod,name))}
  try:
   fn=getattr(mod,name);args={'tmp_path':WORK/'matrix'/name} if 'tmp_path' in inspect.signature(fn).parameters else {}
   if args:args['tmp_path'].mkdir(parents=True,exist_ok=True)
   fn(**args);result['assertions']='passed';print('MATRIX',name,'passed',flush=True)
  except BaseException as ex:
   result['assertions']='failed';result['exception']={'type':type(ex).__name__,'message':str(ex),'traceback':traceback.format_exc()};print('MATRIX',name,'FAILED',str(ex),flush=True)
  finally:
   for p in patched:p.stop()
  result['calls']=cap;save('matrix/'+name+'.json',result);summary.append({'name':name,'assertions':result['assertions'],'public_api_count':len(cap)})
 save('matrix_summary.json',summary)
 if any(x['assertions']!='passed' for x in summary):raise RuntimeError('Matrix regression failed')

if __name__=='__main__':
 mode=sys.argv[2]
 if mode=='conditions':conditions()
 elif mode=='matrix':matrix()
 else:raise RuntimeError(mode)
