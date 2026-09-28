import asyncio
import json
import unittest
from unittest.mock import patch
from pathlib import Path
from test_phase1 import reader
from phase2 import Supervisor
from phase3 import ASSETS, asset, ZONE_CAPABILITIES

class PhaseThreeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        reader.object_cache.clear()
        reader.metadata_cache.clear()
        self.s = Supervisor(reader)

    async def request(self, path, method='GET', peer='172.30.32.2', payload=b''):
        incoming = asyncio.StreamReader()
        incoming.feed_data(f'{method} {path} HTTP/1.1\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n'.encode()+payload)
        incoming.feed_eof()
        class Output:
            data=b''
            def get_extra_info(self,n):return (peer,1234)
            def write(self,b):self.data+=b
            async def drain(self):pass
            def close(self):pass
            async def wait_closed(self):pass
        out=Output()
        await self.s.http(incoming,out)
        return out.data

    async def test_all_assets_served_and_legacy_console_preserved(self):
        for path in ASSETS:
            response=await self.request(path)
            self.assertTrue(response.startswith(b'HTTP/1.1 200'),path)
        response=await self.request('/technical')
        self.assertEqual(response.split(b'\r\n\r\n',1)[1],Path(__file__).with_name('mct.html').read_bytes())

    async def test_no_write_route_or_filesystem_traversal(self):
        for path in ['/api/write','/api/command','/api/control','/api/schedule','/api/ack','/','/assets/../phase2.py','/../run.sh']:
            response=await self.request(path,'POST',payload=b'{}')
            self.assertTrue(response.startswith(b'HTTP/1.1 404'),path)
        for path in ['/../run.sh','/assets/../phase2.py','/assets/%2e%2e/phase2.py','/phase2.py']:
            self.assertIsNone(asset(path))
            self.assertTrue((await self.request(path)).startswith(b'HTTP/1.1 404'))

    async def test_assets_and_inventory_require_ingress(self):
        for path in ['/', '/inventory.json','/assets/batiment.jpg']:
            self.assertTrue((await self.request(path,peer='192.168.0.10')).startswith(b'HTTP/1.1 403'))

    def test_control_capabilities_always_disabled(self):
        self.assertEqual({k for k,v in ZONE_CAPABILITIES.items() if v['control_ready']},{'Grande Salle','Petite Salle'})
        self.assertTrue(all(not v['control_enabled'] and not v['write_enabled'] for v in ZONE_CAPABILITIES.values()))

    def test_metrics_expire_and_preserve_configured_stale_limit(self):
        self.s.gate.measurements.extend([(10,200),(69,100)])
        with patch('phase2.time.monotonic',return_value=70):
            self.assertEqual(self.s.gate.metrics(),{'reads_per_second':.02,'mean_read_ms':100})
        self.s.stale=600
        self.assertEqual(self.s.snapshot()['summary']['stale_after'],600)

if __name__=='__main__':unittest.main()
