import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent))
import phase2
from test_phase1 import reader

class PhaseTwoTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        reader.running=True
        reader.bridge=reader.OfflineBridge()
        reader.read_gate=None
        reader.metadata_cache.clear()
        reader.object_cache.clear()
        reader.object_cache[130]=[('multi-state-value',1),('binary-output',2),('schedule',3)]
        self.s=phase2.Supervisor(reader)
        self.s.seed()

    def test_only_controller_labels_one_based(self):
        meta={'stateText':['Mode A','Mode B']}
        self.assertEqual(phase2.display_value('multi-state-value',2,meta),'Mode B')
        for unknown in (0,3,1.5,None):
            self.assertEqual(phase2.display_value('multi-state-value',unknown,meta),unknown)
        self.assertEqual(phase2.display_value('binary-output','inactive',{}),'inactive')
        self.assertEqual(phase2.display_value('binary-output','inactive',{'inactiveText':'Texte CPO'}),'Texte CPO')

    def test_multiclient_heartbeat_expiry(self):
        v=phase2.ActiveViews(15)
        v.heartbeat('a',['x'],{'x','y'},0)
        v.heartbeat('b',['y'],{'x','y'},10)
        self.assertEqual(v.active(14),{'x','y'})
        self.assertEqual(v.active(15),{'y'})
        self.assertEqual(v.active(25),set())

    def test_heartbeat_cannot_request_uninventoried_object(self):
        self.s.views.heartbeat('a',['unlisted','schedule_3'],{'multi-state-value_1'},0)
        self.assertEqual(self.s.views.active(1),set())
        with self.assertRaises(ValueError):
            self.s.views.heartbeat('a',['x']*41,{'x'},1)

    def test_active_point_accelerates_and_background_is_serviced(self):
        self.s.last_good={'multi-state-value_1':100,'binary-output_2':100}
        self.s.last_attempt=dict(self.s.last_good)
        self.s.due={'multi-state-value_1':130,'binary-output_2':130}
        self.s.views.heartbeat('a',['multi-state-value_1'],set(self.s.records),100)
        self.assertEqual(self.s.next_value(102),'multi-state-value_1')
        self.s.due['multi-state-value_1']=132
        self.s.last_attempt['multi-state-value_1']=130
        self.assertEqual(self.s.next_value(130),'binary-output_2')

    async def test_failure_keeps_last_good_without_refreshing_age(self):
        key='multi-state-value_1'
        rec=self.s.records[key]
        class Bacnet:
            async def read(self,q): return 7
        await self.s.read_value(Bacnet(),key)
        stamp=rec['last_read']; good=self.s.last_good[key]
        class Broken:
            async def read(self,q): raise TimeoutError()
        await self.s.read_value(Broken(),key)
        self.assertEqual(rec['present_value'],7)
        self.assertEqual(rec['last_read'],stamp)
        self.assertEqual(self.s.last_good[key],good)
        with patch.object(phase2.time,'monotonic',return_value=good+181):
            self.assertFalse(self.s.attributes(rec)['available'])

    async def test_unknown_property_never_gets_synthesized_binary_label(self):
        class MissingProperty(phase2.BACnetError):
            @property
            def reason(self): return 'unknown-property'
        class App:
            async def read_property(self,*args): raise MissingProperty()
        class Bacnet:
            this_application=types.SimpleNamespace(app=App())
            def build_rp_request(self,args): return args[:4]
            async def read(self,q): raise AssertionError('BAC0 synthesized path called')
        result=await self.s.gate.read(Bacnet(),'target','binary-value',1,'activeText')
        self.assertIsNone(result)
        self.assertEqual(self.s.gate.unsupported,1)
        self.assertEqual(self.s.gate.failures,0)

    async def test_transport_timeout_has_backoff(self):
        self.s.gate.timeout=.01
        class Slow:
            async def read(self,q): await asyncio.sleep(1)
        self.assertIsNone(await self.s.gate.read(Slow(),'target','analog-value',1,'presentValue'))
        self.assertEqual(self.s.gate.errors,1)
        self.assertGreater(self.s.gate.backoff_until,phase2.time.monotonic())

    def test_technical_objects_and_raw_ids_remain_in_export(self):
        data=self.s.snapshot()
        self.assertEqual(len(data['objects']),3)
        self.assertEqual(data['objects'][2]['object_type'],'schedule')
        self.assertTrue(all(x['read_only'] for x in data['objects']))
        self.assertIn('weeklySchedule',phase2.properties_for('schedule'))
        self.assertIn('subordinateList',phase2.properties_for('structured-view'))
        self.assertIn('recipientList',phase2.properties_for('notification-class'))
        self.assertIn('eventParameters',phase2.properties_for('event-enrollment'))

    async def test_http_rejects_non_ingress_peer(self):
        class Output:
            data=b''
            def get_extra_info(self,n): return ('192.168.0.10',1234)
            def write(self,b): self.data+=b
            async def drain(self): pass
            def close(self): pass
            async def wait_closed(self): pass
        output=Output()
        await self.s.http(None,output)
        self.assertTrue(output.data.startswith(b'HTTP/1.1 403'))

    async def test_phase2_collects_and_polls_without_mqtt(self):
        class Bacnet:
            async def read(self,q):
                prop=q.split()[-1]
                if prop=='presentValue': return 1
                if prop=='stateText': return ['CPO label']
                if prop=='objectName': return 'Object test'
                raise RuntimeError('unknown-property')
        class Server:
            def close(self): pass
            async def wait_closed(self): pass
        self.s.gate.rate=10000
        reader.read_gate=self.s.gate
        with patch.object(phase2.asyncio,'start_server',return_value=Server()), patch.object(self.s,'save'):
            task=asyncio.create_task(self.s.run(Bacnet()))
            async def completed():
                while not self.s.metadata_complete or len(self.s.last_good)!=2:
                    await asyncio.sleep(.005)
                reader.running=False
            try:
                await asyncio.wait_for(completed(),2)
                await asyncio.wait_for(task,1)
            finally:
                reader.running=False
                if not task.done():
                    task.cancel()
                    try: await task
                    except asyncio.CancelledError: pass
                reader.read_gate=None
        self.assertEqual(self.s.records['multi-state-value_1']['metadata']['stateText'],['CPO label'])
        self.assertEqual(self.s.published,0)
        self.assertEqual(self.s.gate.errors,0)

if __name__=='__main__':unittest.main()
