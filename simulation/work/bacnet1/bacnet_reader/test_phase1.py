import asyncio
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

# Transport doubles: these tests never contact the CPO or a broker.
for name in ('BAC0', 'paho', 'paho.mqtt', 'paho.mqtt.client'):
    sys.modules[name] = types.ModuleType(name)
spec = importlib.util.spec_from_file_location('reader', Path(__file__).with_name('bacnet_reader.py'))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

class PhaseOneTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        reader.running = True
        reader.read_gate = None
        reader.metadata_cache.clear()
        reader.metadata_time.clear()
        reader.object_cache.clear()
        reader.cache_time.clear()

    async def test_bacnet_runs_when_mqtt_service_fails(self):
        calls = []
        class Context:
            async def __aenter__(self):
                calls.append('bacnet_started')
                return self
            async def __aexit__(self, *args): pass
        async def cycle(bacnet):
            calls.append('inventory')
            await asyncio.sleep(0)
            reader.running = False
        with patch.dict(reader.os.environ, {'PHASE2_ENABLED': 'false'}), patch.object(reader.BAC0, 'start', return_value=Context(), create=True), patch.object(reader, 'MQTTBridge', side_effect=RuntimeError('offline')), patch.object(reader, 'discovery_cycle', cycle):
            await asyncio.wait_for(reader.main(), 3)
        self.assertEqual(calls, ['bacnet_started', 'inventory'])

    async def test_inventory_saved_without_mqtt_and_keeps_non_value_objects(self):
        class Bacnet:
            async def read(self, query):
                prop = query.split()[-1]
                return {'objectList': [('analog-input', 1), ('schedule', 2)], 'objectName': 'Test', 'presentValue': 21.5}.get(prop)
        reader.bridge = reader.OfflineBridge()
        with tempfile.TemporaryDirectory() as directory, patch.object(reader, 'Path', side_effect=lambda _: Path(directory)/'inventory.json'):
            await reader.inventory_objects(Bacnet(), '192.168.0.249', 130)
            data = reader.json.loads((Path(directory)/'inventory.json').read_text())
        self.assertEqual(data['summary']['object_count'], 2)
        self.assertEqual(data['summary']['values_read'], 1)
        self.assertEqual(data['summary']['published'], 0)
        self.assertEqual(data['objects'][1]['object_type'], 'schedule')
        self.assertTrue(all(x['read_only'] for x in data['objects']))

    async def test_metadata_expires_and_is_cached_before_expiry(self):
        class Bacnet:
            calls = 0
            async def read(self, query):
                self.calls += 1
                return 'updated'
        bacnet = Bacnet()
        with patch.object(reader.time, 'monotonic', return_value=10):
            await reader.object_metadata(bacnet, 'target', 130, 'analog-input', 1)
        count = bacnet.calls
        with patch.object(reader.time, 'monotonic', return_value=11):
            await reader.object_metadata(bacnet, 'target', 130, 'analog-input', 1)
        self.assertEqual(bacnet.calls, count)
        with patch.object(reader.time, 'monotonic', return_value=1811):
            await reader.object_metadata(bacnet, 'target', 130, 'analog-input', 1)
        self.assertEqual(bacnet.calls, count*2)

    def test_binary_unknown_stays_unknown(self):
        self.assertIsNone(reader.normalized_value('binary-output', 'unconfirmed'))
        self.assertEqual(reader.normalized_value('multi-state-value', 7), 7)

if __name__ == '__main__': unittest.main()
