import unittest
from datetime import datetime,timezone,timedelta
from zone_averages import calculate
class AverageTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime.now(timezone.utc);self.g=[dict(id='test',name='Test',zone='Zone',unit='degrees-celsius',sources={'analog-input_1':'A','analog-input_2':'B'})]
  self.rows=[dict(key='analog-input_'+str(i),device_instance=130,object_type='analog-input',in_object_list=True,present_value=v,last_read=self.now.isoformat(),metadata=dict(objectName=n,units='degrees-celsius',statusFlags=[0,0,0,0],reliability='no-fault-detected',outOfService=0),metadata_reads={p:dict(status='read',last_success=self.now.isoformat()) for p in ('units','statusFlags','reliability','outOfService')}) for i,n,v in [(1,'A',10),(2,'B',20)]]
 def calc(self):return calculate(self.rows,self.g,now=self.now)[0]
 def test_mean(self):self.assertEqual(self.calc()['value'],15);self.assertEqual(self.calc()['source_count'],2)
 def test_stale_excluded(self):
  self.rows[1]['last_read']=(self.now-timedelta(seconds=181)).isoformat();r=self.calc();self.assertEqual(r['value'],10);self.assertEqual(r['coverage'],'partial')
 def test_no_sources_unavailable(self):
  self.rows=[];self.assertIsNone(self.calc()['value']);self.assertFalse(self.calc()['available'])
 def test_bad_quality_excluded(self):
  self.rows[0]['metadata']['statusFlags']=[1,0,0,0];self.rows[1]['metadata']['outOfService']=1;self.assertFalse(self.calc()['available'])
 def test_units_and_identity(self):
  self.rows[0]['metadata']['units']='percent';self.rows[1]['metadata']['objectName']='Changed';self.assertFalse(self.calc()['available'])
 def test_non_numeric_and_future(self):
  self.rows[0]['present_value']=float('nan');self.rows[1]['last_read']=(self.now+timedelta(seconds=1)).isoformat();self.assertFalse(self.calc()['available'])
 def test_unknown_quality(self):
  for r in self.rows:r['metadata_reads']={}
  self.assertFalse(self.calc()['available'])
 def test_duplicate_not_double_counted(self):
  self.rows.append(dict(self.rows[0]));self.assertEqual(self.calc()['value'],20)
