"""Preparation only: exact identity checks never authorize a write."""
FEATURES = {
 'heating_large': {'candidate': ('analog-value_29','Rad_BlocA_PcmTmpAmbMin'), 'observations': [('multi-state-value_4','Rad_BlocA_Mode')]},
 'heating_small': {'candidate': ('analog-value_19','Rad_BlocB_PcmTmpAmbMin'), 'observations': [('multi-state-value_6','Rad_BlocB_Mode')]},
 'quiet_large': {'candidate': None, 'observations': [('analog-value_84','TCGP1_VPuVExVmin'),('analog-value_73','TCGP1_DebPul'),('analog-value_74','TCGP1_DebRep')]},
 'haze_clear_large': {'candidate': None, 'observations': [('analog-output_14','TCGP1_ModVPu'),('analog-output_15','TCGP1_ModVEx'),('analog-value_73','TCGP1_DebPul'),('analog-value_74','TCGP1_DebRep')]},
}
def integration_report(inventory):
 report={'activation':'manual_only','real_writes_enabled':False,'features':{},'mutually_exclusive':['quiet_large','haze_clear_large']}
 for key,feature in FEATURES.items():
  refs=list(feature['observations'])+([feature['candidate']] if feature['candidate'] else [])
  checks=[]
  for object_key,name in refs:
   matches=[r for r in inventory.get('objects',[]) if r.get('key')==object_key]
   matched=(inventory.get('device_instance')==130 and len(matches)==1 and matches[0].get('device_instance')==130 and matches[0].get('object_name')==name and matches[0].get('in_object_list') is True)
   checks.append(dict(key=object_key,expected_name=name,matched=matched))
  report['features'][key]={'candidate':feature['candidate'],'identity_checks':checks,'allowed':False,'write_priority':None,'missing':['cpo_semantics','limits','reserved_priority','release','cpo_expiry','physical_validation']+([] if feature['candidate'] else ['request_point'])}
 return report
