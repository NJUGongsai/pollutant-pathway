"""R8 independent first-consumer matrix; synthetic representations, no assets/models.
Run only from copied fresh tmp beside complete isolated src and helper tests.
"""
import copy, hashlib, json, runpy, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from rdkit import rdBase
from pathway_v43.pollutant.chemstate import ChemicalState, ChemicalStateError, build_chemical_state, build_chemical_state_from_cn_only, archive_recovered_fidelity, validate_state_object
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission
fx=runpy.run_path(str(ROOT/'tests/test_ppv1_r8_chem.py'))
def emit(case,**kw):
 print(json.dumps(dict(case=case,**kw),ensure_ascii=False,sort_keys=True,default=str))
def capture(case,f,**meta):
 try: emit(case,ok=True,result=f(),**meta)
 except Exception as e:emit(case,ok=False,exception=type(e).__name__,message=str(e),detail=getattr(e,'detail',{}),**meta)
def run_chain(payload,key,states,hyp,evidence,mode):
 supplied=ChemicalState.from_dict(payload) if mode=='restore' else ChemicalState(**payload)
 items=dict(states);items[key]=supplied
 audit=fx['_audit'](items,hyp,evidence)
 return dict(states={k:v.to_dict() for k,v in items.items()},hypothesis=hyp.to_dict(),center_evidence=evidence,audit=audit.to_dict(),admission=decide_admission(audit))
def writer(payload,case):
 store=PollutantPathwayStore(ROOT/(case+'.sqlite'))
 before=store.counts()
 try:
  store.put_state(payload)
  return dict(accepted=True,before=before,after=store.counts())
 except Exception as e:
  return dict(accepted=False,before=before,after=store.counts(),exception=type(e).__name__,detail=getattr(e,'detail',{}))
 finally:store.conn.close()
meta=json.loads((ROOT/'metadata.json').read_text())
emit('metadata',actual_source_HEAD=meta['actual_HEAD'],parent_source_HEAD=meta['parent_HEAD'],rdkit=rdBase.rdkitVersion,schema=ChemicalState.__dataclass_fields__['schema_version'].default,source_sha256=meta['source_files'])
states,hyp,evidence=fx['_oxidation_base']()
for key in ['CCO','CC=O','[H][H]']:
 for field in ['structure_smiles_raw','smiles_isomeric']:
  payload=states[key].to_dict();payload[field]=key+' |r|'
  for mode in ['restore','direct']:
   capture('unknown_r_'+key+'_'+field+'_'+mode,lambda p=payload,k=key,m=mode:run_chain(p,k,states,hyp,evidence,m),payload=payload,hypothesis=hyp.to_dict(),evidence=evidence,entry=mode)
  if field=='structure_smiles_raw':
   capture('unknown_r_'+key+'_writer',lambda p=payload,k=key:writer(p,'unknown_raw_'+k.replace('[','').replace(']','').replace('=','')),payload=payload,entry='writer')
payload=states['[H][H]'].to_dict();payload['structure_smiles_raw']='CC=O'
for mode in ['restore','direct']:
 capture('raw_H2_cross_molecule_'+mode,lambda m=mode:run_chain(payload,'[H][H]',states,hyp,evidence,m),payload=payload,hypothesis=hyp.to_dict(),evidence=evidence,entry=mode)
capture('raw_H2_cross_molecule_writer',lambda:writer(payload,'H2_cross_molecule'),payload=payload,entry='writer')
# All facts already validated by writer; consumer coverage is original R7-01 minimum.
for field,value in [('state_id','cs_wrong'),('cn_identity','CCN'),('formal_charge',99),('stereo_information_status','unknown'),('isotope_information_status','unknown'),('structure_origin','bogus-origin'),('schema_version','ppv1-chemstate-future')]:
 payload=states['CCO'].to_dict();payload[field]=value
 for mode in ['restore','direct']:
  capture('fact_'+field+'_'+mode,lambda p=payload,m=mode:run_chain(p,'CCO',states,hyp,evidence,m),payload=payload,hypothesis=hyp.to_dict(),evidence=evidence,entry=mode)
# Registered metadata and same graph raw retain R6; refusal is not universal rejection.
for label,raw in [('clean','CCO'),('same_graph_OCC','OCC'),('atomProp_space','CCO |atomProp:0.note.hello world|'),('SgD_comma_space','CCO |SgD:0:note:a,b hello world::::|'),('label_space','CCO |$foo bar;;$|')]:
 payload=states['CCO'].to_dict();payload['structure_smiles_raw']=raw
 for mode in ['restore','direct']:
  capture('positive_'+label+'_'+mode,lambda p=payload,m=mode:run_chain(p,'CCO',states,hyp,evidence,m),payload=payload,hypothesis=hyp.to_dict(),evidence=evidence,entry=mode)
sub='F[C@H](Cl)CCO';cev=fx['_donor_evidence'](sub,'S_C_3','S_O_1','single','double')
prod=cev['bound_inputs']['product_identity'];cs=fx['_states'](sub,prod,'[H][H]')
ch=fx['_hyp'](cs,[(sub,1)],[(prod,1),('[H][H]',1)],group='r8-independent-chiral')
for label,raw in [('clean',sub),('unknown_r',sub+' |r|')]:
 payload=cs[sub].to_dict();payload['structure_smiles_raw']=raw
 for mode in ['restore','direct']:
  capture('chiral_'+label+'_'+mode,lambda p=payload,m=mode:run_chain(p,sub,cs,ch,cev,m),payload=payload,hypothesis=ch.to_dict(),evidence=cev,entry=mode)
 if label=='unknown_r':capture('chiral_unknown_r_writer',lambda:writer(payload,'chiral_r'),payload=payload,entry='writer')
# The original R7 tail CN-only control, independently split from newly rejected chiral case.
legacy=dict(states);legacy['CCO']=build_chemical_state_from_cn_only('CCO')
lhyp=fx['_hyp'](legacy,[('CCO',1)],[('CC=O',1),('[H][H]',1)],group='r8-independent-cn-only')
for mode in ['restore','direct']:
 capture('CN_only_honest_unknown_'+mode,lambda m=mode:run_chain(legacy['CCO'].to_dict(),'CCO',legacy,lhyp,evidence,m),payload=legacy['CCO'].to_dict(),hypothesis=lhyp.to_dict(),evidence=evidence,entry=mode)
archived=build_chemical_state('CC=O','source_product',[{'record':'synthetic_archive'}],fidelity=archive_recovered_fidelity())
for mode in ['restore','direct']:
 capture('archive_absent_axes_'+mode,lambda m=mode:run_chain(archived.to_dict(),'CC=O',states,hyp,evidence,m),payload=archived.to_dict(),hypothesis=hyp.to_dict(),evidence=evidence,entry=mode)
# Already supported retained/removed forms: validate object restore, not just build roundtrip.
retained=['CCCCCC |Sg:n:1,2,3:3:ht:::|','C[C@H](Cl)[C@H](F)Cl |a:1, &1:3|','C[C@H](Cl)[C@H](F)Cl |&1:1, &2:3|','CC |^1:0,1|','CC |^1:0, ^2:1|','CC |^1:0 ^2:1|']
for i,s in enumerate(retained):
 def retained_restore(s=s):
  st=build_chemical_state(s,'raw_input'); restored=ChemicalState.from_dict(st.to_dict());validate_state_object(restored)
  return dict(state=st.to_dict(),restored=restored.to_dict(),same_identity=st.state_id==restored.state_id)
 capture('retained_restore_'+str(i),retained_restore,input=s)
# Scope is machine disclosure: field presence alone does not establish license use.
# Omitted-H2 hypothetical intentionally fails element accounting; no chemical truth claim.
for label,products in [('license_used',[('CC=O',1),('[H][H]',1)]),('no_uncovered_but_H2_omitted',[('CC=O',1)])]:
 shyp=fx['_hyp'](states,[('CCO',1)],products,group='r8-scope-'+label)
 capture('scope_'+label,lambda h=shyp:run_chain(states['CCO'].to_dict(),'CCO',states,h,evidence,'restore'),hypothesis=shyp.to_dict(),evidence=evidence,note='second case intentionally fails elemental closure; tests disclosure, not claimed reaction correctness')
