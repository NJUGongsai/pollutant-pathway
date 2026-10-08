"""R7 independent synthetic C1/C3/C4/C5/C6 evidence; no assets/models."""
import copy, hashlib, json, runpy, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from rdkit import Chem, rdBase
from pathway_v43.pollutant.chemstate import ChemicalState, build_chemical_state, build_chemical_state_from_cn_only, strict_identity_of
from pathway_v43.pollutant.store import PollutantPathwayStore
from pathway_v43.pollutant.audit import audit_hypothesis, decide_admission, center_evidence_from_donor_diagnostic
fx=runpy.run_path(str(ROOT/'tests/test_ppv1_r7_chem.py'))
HEAD='858dd94c7c6c8fc387940242403d67b6b36b5313'
def emit(case,**kw):
 print(json.dumps(dict(case=case,**kw),ensure_ascii=False,sort_keys=True,default=str))
def capture(case,f,**meta):
 try: emit(case,ok=True,result=f(),**meta)
 except Exception as e: emit(case,ok=False,exception=type(e).__name__,message=str(e),detail=getattr(e,'detail',{}),**meta)
def audit(states,hyp,ev):
 a=audit_hypothesis(hyp,states={st.state_id:st for st in states.values()},context=fx['_aerobic_context'](),center_evidence=ev)
 return dict(states={k:v.to_dict() for k,v in states.items()},hypothesis=hyp.to_dict(),center_evidence=ev,audit=a.to_dict(),admission=decide_admission(a))
emit('metadata',expected_source_HEAD=HEAD,rdkit=rdBase.rdkitVersion,chemstate_schema=ChemicalState.__dataclass_fields__['schema_version'].default,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/pathway_v43/pollutant/chemstate.py',ROOT/'src/pathway_v43/pollutant/audit.py',ROOT/'src/pathway_v43/pollutant/store.py',ROOT/'tests/test_ppv1_r7_chem.py']})
ev=fx['_oxidation_evidence']()
base=fx['_states']('CCO','CC=O','[H][H]')
hyp=fx['_hyp'](base,[('CCO',1)],[('CC=O',1),('[H][H]',1)],group='C1-direct-restore')
capture('clean_factory_public_chain',lambda:audit(base,hyp,ev))
for label,key,field,value in [
 ('canonical_substrate_unknown_flag','CCO','smiles_isomeric','CCO |r|'),
 ('canonical_product_unknown_flag','CC=O','smiles_isomeric','CC=O |r|'),
 ('canonical_uncovered_H2_unknown_flag','[H][H]','smiles_isomeric','[H][H] |r|'),
 ('raw_substrate_unknown_flag','CCO','structure_smiles_raw','CCO |r|'),
 ('raw_product_unknown_flag','CC=O','structure_smiles_raw','CC=O |r|'),
 ('raw_uncovered_H2_unknown_flag','[H][H]','structure_smiles_raw','[H][H] |r|'),
 ('raw_uncovered_H2_different_molecule','[H][H]','structure_smiles_raw','CC=O'),
]:
 sts=copy.deepcopy(base)
 payload=copy.deepcopy(sts[key].to_dict());payload[field]=value
 capture('C1_'+label,lambda: audit(dict(sts,**{key:ChemicalState.from_dict(payload)}),hyp,ev),restored_payload=payload,mutation={'key':key,'field':field,'value':value})
 capture('factory_guard_'+label,lambda:build_chemical_state(value,'source_product').to_dict(),input=value)
 def store_control(payload=payload,label=label):
  store=PollutantPathwayStore(ROOT/(label+'.sqlite'))
  before=store.counts()
  try:
   store.put_state(payload)
   return {'accepted':True,'before':before,'after':store.counts()}
  except Exception as e:
   return {'accepted':False,'before':before,'after':store.counts(),'exception':type(e).__name__,'detail':getattr(e,'detail',{})}
  finally:store.conn.close()
 capture('store_first_use_'+label,store_control,restored_payload=payload)
# Retained-group semantics: writer/reparse snapshots; ids not compared by RDKit objects.
def mol_facts(m):
 return {'smiles':Chem.MolToSmiles(m),'cx':Chem.MolToCXSmiles(m),
 'sgroups':[{'type':g.GetProp('TYPE'),'atoms':list(g.GetAtoms()),'bonds':list(g.GetBonds()),'props':g.GetPropsAsDict()} for g in Chem.GetMolSubstanceGroups(m)],
 'stereo_groups':[{'type':str(g.GetGroupType()),'atoms':[a.GetIdx() for a in g.GetAtoms()]} for g in m.GetStereoGroups()],
 'radicals':[a.GetNumRadicalElectrons() for a in m.GetAtoms()]}
retained=[
 'CCCCCC |Sg:n:1,2,3:3:ht:::|',
 'CCCCCC |Sg:n:1,2,3:hello world:ht:::|',
 'CCCCCC |Sg:n:1,2,3:hello,world:ht:::|',
 'CCCCCC |Sg:n:1,2,3:hello&#32;world:ht:::|',
 'CCCCCC |Sg:n:1,2,3:3:ht:::, Sg:n:0:other group:ht:::|',
 'C[C@H](Cl)[C@H](F)Cl |a:1, &1:3|',
 'C[C@H](Cl)[C@H](F)Cl |&1:1, &2:3|',
 'CC |^1:0,1|',
 'CC |^1:0, ^2:1|',
 'CC |^1:0 ^2:1|',
]
def roundtrip_facts(structure):
 original=Chem.MolFromSmiles(structure)
 if original is None: raise ValueError('RDKit original parse failed')
 writer=Chem.MolToCXSmiles(original)
 reparsed=Chem.MolFromSmiles(writer)
 if reparsed is None: raise ValueError('writer reparse failed')
 facts=dict(original=mol_facts(original),writer=writer,reparsed=mol_facts(reparsed),
  canonical_writer_stable=writer==Chem.MolToCXSmiles(reparsed),
  radical_multiset_equal=sorted(mol_facts(original)['radicals'])==sorted(mol_facts(reparsed)['radicals']))
 try:
  first=build_chemical_state(structure,'raw_input')
  restored=build_chemical_state(first.smiles_isomeric,'source_product')
  bare=build_chemical_state(structure.split(' |')[0],'raw_input')
 except Exception as e:
  return dict(facts,guard_accepted=False,exception=type(e).__name__,detail=getattr(e,'detail',{}))
 return dict(facts,guard_accepted=True,
 state=first.to_dict(),restored_state=restored.to_dict(),bare_state=bare.to_dict(),
 same_identity=first.state_id==restored.state_id,different_from_bare=first.state_id!=bare.state_id,
 atom_indexed_snapshots_equal=mol_facts(original)==mol_facts(reparsed))
for i,s in enumerate(retained):capture('C3_retained_'+str(i),lambda s=s:roundtrip_facts(s),input=s)
removed=['CC |atomProp:0.note.hello world|','CO |SgD:0:note:a,b hello world::::|','C |$foo bar;$|']
for i,s in enumerate(removed):capture('C3_removed_'+str(i),lambda s=s:roundtrip_facts(s),input=s)
# unknown flags at registered content boundaries and legitimate DAT comma remain explicit.
for i,s in enumerate(['CC |atomProp:0.note.hello,r|','CO |SgD:0:note:hello::::,r|','CCCCCC |Sg:n:1,2,3:3:ht:::,r|','CO |SgD:0:note:a,b::::|']):
 capture('CX_boundary_'+str(i),lambda s=s:build_chemical_state(s,'raw_input').to_dict(),input=s)
# Same evidence / three initial graphs must remain partial, real H-equivalent controls retained.
organic_ev=fx['_methane_to_propanol_evidence']()
for co in ['CC=O','C1CO1','C=CO']:
 sts=fx['_states']('C','CCCO',co);h=fx['_hyp'](sts,[('C',1),(co,1)],[('CCCO',1)],group='r7-independent-'+co)
 capture('R6_01_'+co,lambda sts=sts,h=h:audit(sts,h,organic_ev))
# C6 failed execution must not parse tainted fields or leak verified.
r,edits,result=fx['_oxidation_inputs']()
cur={'smiles':r.smiles,'atom_id_map':dict(r.atom_id_map)}
for field in ['current','mapped','plain','target']:
 ci=copy.deepcopy(cur);rr=copy.deepcopy(result);target=rr['product_smiles']
 if field=='current':ci['smiles']+=' |r|'
 elif field=='mapped':rr['product_mapped_smiles']+=' |r|'
 elif field=='plain':rr['product_smiles']+=' |r|'
 else:target+=' |r|'
 def check(ci=ci,rr=rr,target=target):
  d=fx['_check'](ci,edits,rr,target)
  return {'diagnostic':d.to_dict(),'evidence':center_evidence_from_donor_diagnostic(d)}
 capture('C6_execution_success_'+field,check,inputs=dict(current=ci,result=rr,target=target,edits=edits))
 rr['ok']=False
 capture('C6_execution_failure_'+field,check,inputs=dict(current=ci,result=rr,target=target,edits=edits))

# Restored clean and same-graph alternate raw spelling controls.
for label,value in [('clean','CCO'),('same_graph_spelling','OCC'),('registered_metadata','CCO |atomProp:0.note.hello world|')]:
 sts=copy.deepcopy(base);pay=sts['CCO'].to_dict();pay['structure_smiles_raw']=value
 sts['CCO']=ChemicalState.from_dict(pay)
 capture('C1_restore_control_'+label,lambda sts=sts:audit(sts,hyp,ev),restored_payload=pay)
# Specified stereochemical representation retained in clean evidence; original r remains unregistered.
sub='F[C@H](Cl)CCO'
cev=fx['_donor_evidence'](sub,'S_C_3','S_O_1','single','double')
prod=cev['bound_inputs']['product_identity'];cs=fx['_states'](sub,prod,'[H][H]')
ch=fx['_hyp'](cs,[(sub,1)],[(prod,1),('[H][H]',1)],group='C1-chiral-raw')
capture('C1_chiral_clean_control',lambda:audit(cs,ch,cev))
pay=cs[sub].to_dict();pay['structure_smiles_raw']=sub+' |r|';cs[sub]=ChemicalState.from_dict(pay)
capture('C1_chiral_raw_unknown_flag',lambda:audit(cs,ch,cev),restored_payload=pay)

legacy_states=copy.deepcopy(base)
legacy_states['CCO']=ChemicalState.from_dict(build_chemical_state_from_cn_only('CCO').to_dict())
legacy_hyp=fx['_hyp'](legacy_states,[('CCO',1)],[('CC=O',1),('[H][H]',1)],group='C1-legacy-cn-only')
capture('C1_CN_only_honest_unknown_control',lambda:audit(legacy_states,legacy_hyp,ev))
