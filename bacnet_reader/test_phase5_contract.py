import unittest
from phase5_contract import FEATURES,integration_report
class ContractTests(unittest.TestCase):
 def inventory(self):
  refs=set()
  for f in FEATURES.values():
   refs.update(f['observations'])
   if f['candidate']:refs.add(f['candidate'])
  return dict(device_instance=130,objects=[dict(key=k,object_name=n,device_instance=130,in_object_list=True) for k,n in refs])
 def test_match_never_authorizes(self):
  r=integration_report(self.inventory());self.assertEqual(r['activation'],'manual_only');self.assertFalse(r['real_writes_enabled'])
  for f in r['features'].values():
   self.assertTrue(all(c['matched'] for c in f['identity_checks']));self.assertFalse(f['allowed']);self.assertIsNone(f['write_priority'])
 def test_wrong_identity_rejected(self):
  for mode in ['name','duplicate','missing','device','removed']:
   inv=self.inventory();first=inv['objects'][0];key=first['key']
   if mode=='name':first['object_name']='unknown'
   if mode=='duplicate':inv['objects'].append(dict(first))
   if mode=='missing':inv['objects'].pop(0)
   if mode=='device':inv['device_instance']=131
   if mode=='removed':first['in_object_list']=False
   checks=[c for f in integration_report(inv)['features'].values() for c in f['identity_checks'] if c['key']==key]
   self.assertTrue(checks);self.assertFalse(any(c['matched'] for c in checks))
 def test_no_invented_ventilation_command(self):
  for name in ['quiet_large','haze_clear_large']:self.assertIsNone(FEATURES[name]['candidate'])
 def test_report_detached(self):
  r=integration_report({});r['features']['quiet_large']['identity_checks'].clear()
  self.assertTrue(integration_report({})['features']['quiet_large']['identity_checks'])
