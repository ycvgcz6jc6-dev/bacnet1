import asyncio
import importlib.util
import pathlib
import tempfile
from unittest.mock import AsyncMock, patch
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Keep BAC0's optional log directory inside a temporary test directory.
with tempfile.TemporaryDirectory() as logdir, patch('os.path.expanduser', return_value=logdir):
    spec = importlib.util.spec_from_file_location('reader', ROOT/'bacnet_reader/bacnet_reader.py')
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
from bacpypes3.apdu import IAmRequest
from bacpypes3.pdu import Address


def iam(ip='192.168.0.249', device_id=123):
    return IAmRequest(iAmDeviceIdentifier=('device', device_id),
                      maxAPDULengthAccepted=1024, segmentationSupported='noSegmentation',
                      vendorID=17, source=Address(ip))


def test_configuration_loads():
    c = yaml.safe_load((ROOT/'bacnet_reader/config.yaml').read_text())
    assert c['url'] == 'https://github.com/ycvgcz6jc6-dev/bacnet1'
    assert c['version'] == '0.1.1'
    assert c['host_network'] is True
    assert c['arch'] == ['amd64', 'aarch64']


def test_real_iam_and_zero_instance():
    assert reader.normalize_discovered_device(iam(device_id=0)) == ('192.168.0.249', 0)
    assert reader.normalize_discovered_device({'address': '192.168.0.249', 'device_id': 0}) == ('192.168.0.249', 0)
    assert reader.normalize_discovered_device({'address': Address('192.168.0.249'), 'object_instance': ('device', 123)}) == ('192.168.0.249', 123)


def test_discovery_consumes_iam_response():
    bacnet = AsyncMock()
    bacnet.who_is.return_value = [iam()]
    with patch.object(reader, 'inspect_device', new_callable=AsyncMock) as inspect, patch.object(reader, 'inventory_objects', new_callable=AsyncMock) as inventory:
        asyncio.run(reader.discovery_cycle(bacnet))
        bacnet.who_is.assert_awaited_once_with(address='*', timeout=3)
        inspect.assert_awaited_once_with(bacnet, '192.168.0.249', 123)
        inventory.assert_awaited_once_with(bacnet, '192.168.0.249', 123)


def test_directed_fallback_uses_configured_port():
    bacnet = AsyncMock()
    bacnet.who_is.side_effect = [[], [iam('192.168.0.249:47809')]]
    with patch.object(reader, 'BACNET_PORT', 47809), patch.object(reader, 'inspect_device', new_callable=AsyncMock), patch.object(reader, 'inventory_objects', new_callable=AsyncMock) as inventory:
        asyncio.run(reader.discovery_cycle(bacnet))
        assert bacnet.who_is.await_args.kwargs == {'address': '192.168.0.249:47809', 'timeout': 3}
        inventory.assert_awaited_once_with(bacnet, '192.168.0.249:47809', 123)


def test_main_applies_port():
    bacnet = AsyncMock()
    with patch.object(reader, 'running', False), patch.object(reader, 'BACNET_PORT', 47809), patch.object(reader.BAC0, 'start', return_value=bacnet) as start:
        asyncio.run(reader.main())
        start.assert_called_once_with(ip=reader.LOCAL_IP, port=47809)


def test_inventory_only_reads_properties():
    bacnet = AsyncMock()
    bacnet.read.side_effect = [[('analogInput', 1)], 'Temperature', 21.5, 'degreesCelsius']
    asyncio.run(reader.inventory_objects(bacnet, '192.168.0.249', 123))
    assert [c.args[0] for c in bacnet.read.await_args_list] == [
        '192.168.0.249 device 123 objectList', '192.168.0.249 analogInput 1 objectName',
        '192.168.0.249 analogInput 1 presentValue', '192.168.0.249 analogInput 1 units']
    assert not bacnet.write.called
