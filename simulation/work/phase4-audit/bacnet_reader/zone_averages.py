"""Explicit homogeneous source groups. No inferred ambient sensor semantics."""
import json, math
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_GROUPS = [
 {'id':'outside_temperature','name':'Extérieur · température moyenne','zone':'Extérieur','unit':'degrees-celsius','sources':{'analog-input_1':'TCPRCH__TmpBL'}},
 {'id':'large_extract_temperature','name':'Grande Salle · température moyenne extraction','zone':'Grande Salle','unit':'degrees-celsius','sources':{'analog-input_37':'TCGP1_TmpRep'}},
 {'id':'large_supply_temperature','name':'Grande Salle · température moyenne soufflage','zone':'Grande Salle','unit':'degrees-celsius','sources':{'analog-input_36':'TCGP1_TmpPul'}},
 {'id':'large_ambient_temperature','name':'Grande Salle · température moyenne ambiante','zone':'Grande Salle','unit':'degrees-celsius','sources':{}},
 {'id':'small_ambient_temperature','name':'Petite Salle · température moyenne ambiante','zone':'Petite Salle','unit':'degrees-celsius','sources':{}},
]

# Separate water circuits from air and separate supply from return.
for group_id, zone, supply, return_point in [
 ('large_heating', 'Grande Salle', ('analog-input_4','Rad_Rad_BlocA_TmpDep'), ('analog-input_5','Rad_Rad_BlocA_TmpRt')),
 ('small_heating', 'Petite Salle', ('analog-input_17','Rad_BlocB_TmpDep'), ('analog-input_9','Rad_BlocB_TmpRt')),
 ('common_heating', 'Communs', ('analog-input_6','Rad_BlocC_D_TmpDep'), ('analog-input_7','Rad_BlocC_D_TmpRt')),
 ('office_heating', 'Bureaux administratifs', ('analog-input_10','Rad_BlocExt_TmpDep'), ('analog-input_11','Rad_BlocExt_TmpRt')),
 ('plant_heating', 'Chaufferie', ('analog-input_2','TCPRCH__TmpDep'), ('analog-input_3','TCPRCH__TmpRt')),
 ('ecs_heating', 'ECS', ('analog-input_12','TCECS___TmpDep'), ('analog-input_13','TCECS___TmpRt')),
]:
 for direction, label, source in [('supply','départ',supply),('return','retour',return_point)]:
  DEFAULT_GROUPS.append(dict(id=group_id+'_'+direction, name=zone+' · température moyenne eau '+label,
                            zone=zone, unit='degrees-celsius', sources={source[0]:source[1]}))

def load_groups(path='/data/options.json'):
 try: raw=json.loads(Path(path).read_text()).get('average_groups_json','')
 except FileNotFoundError: raw=''
 groups=json.loads(raw) if raw else DEFAULT_GROUPS
 if not isinstance(groups,list):raise ValueError('Averages must be a list')
 seen=set()
 for g in groups:
  if not isinstance(g,dict) or not all(isinstance(g.get(k),str) and g[k] for k in ('id','name','zone','unit')):raise ValueError('Invalid group')
  if not g['id'].isascii() or not g['id'].replace('_','').isalnum() or g['id'] in seen:raise ValueError('Invalid or duplicate group id')
  seen.add(g['id'])
  if not isinstance(g.get('sources'),dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in g['sources'].items()):raise ValueError('Explicit source identity required')
 return groups

def calculate(records,groups,device_id=130,stale=180,metadata_age=1860,now=None):
 now=now or datetime.now(timezone.utc)
 def fresh(stamp,limit):
  try:return 0 <= (now-datetime.fromisoformat(stamp)).total_seconds() < limit
  except (ValueError,TypeError):return False
 result=[]
 for g in groups:
  included=[];excluded={};values=[]
  for key,name in g['sources'].items():
   matches=[r for r in records if r.get('key')==key];r=matches[0] if len(matches)==1 else {};m=r.get('metadata',{});reads=r.get('metadata_reads',{});v=r.get('present_value')
   reason=None
   if not r or r.get('device_instance')!=device_id or m.get('objectName')!=name or not r.get('in_object_list'):reason='identity_or_missing'
   elif r.get('object_type') not in ('analog-input','analog-value'):reason='not_numeric_measurement'
   elif m.get('units')!=g['unit']:reason='unit_mismatch'
   elif not fresh(r.get('last_read'),stale) or r.get('read_error'):reason='stale_or_error'
   elif not all(reads.get(p,{}).get('status')=='read' and fresh(reads[p].get('last_success'),metadata_age) for p in ('units','statusFlags','reliability','outOfService')):reason='quality_unknown'
   elif m.get('outOfService') not in (0,False) or m.get('reliability') not in ('no-fault-detected',0):reason='bad_quality'
   elif not isinstance(m.get('statusFlags'),list) or len(m['statusFlags'])!=4 or any(m['statusFlags']):reason='status_flags'
   elif isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):reason='non_numeric'
   if reason:excluded[key]=reason
   else:included.append(key);values.append(v)
  result.append(dict(key='average_'+g['id'],name=g['name'],zone=g['zone'],unit=g['unit'],value=sum(v/len(values) for v in values) if values else None,available=bool(values),source_count=len(values),configured_count=len(g['sources']),sources=included,excluded=excluded,coverage='complete' if values and not excluded else 'partial' if values else 'unavailable',method='arithmetic_mean',updated_at=now.isoformat()))
 return result
