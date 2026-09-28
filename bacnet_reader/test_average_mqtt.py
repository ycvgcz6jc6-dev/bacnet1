import unittest
from test_phase1 import reader
class AverageMQTTTests(unittest.TestCase):
 def bridge(self):
  b=object.__new__(reader.MQTTBridge);b.root='test';b.availability='test/availability';b.configs={};b.messages=[]
  def publish(topic,payload,retain=False):b.messages.append((topic,payload,retain));return True
  b.publish=publish
  return b
 def test_discovery_and_state(self):
  b=self.bridge();b.sensor(130,{},'average_test','Moyenne',21.5,{'source_count':2},unit='°C',device_class='temperature',available=True)
  cfg=b.messages[0][1]
  self.assertEqual(cfg['state_class'],'measurement');self.assertEqual(cfg['availability_mode'],'all')
  self.assertEqual(len(cfg['availability']),2);self.assertIn('expire_after',cfg)
  self.assertEqual(b.messages[-1][1],'21.5')
 def test_empty_mean_offline_without_fake_state(self):
  b=self.bridge();b.sensor(130,{},'average_test','Moyenne',None,{},available=False)
  self.assertEqual(b.messages[-1][1],'offline')
  self.assertFalse(any(t.endswith('/state') for t,p,r in b.messages))
 def test_legacy_discovery_unchanged(self):
  b=self.bridge();b.sensor(130,{},'old','Ancien',1)
  self.assertEqual(b.messages[0][1]['availability_topic'],'test/availability')
  self.assertNotIn('availability_mode',b.messages[0][1])
