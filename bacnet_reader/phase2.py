"""Read-only MCT supervision. No BACnet write or command subscription exists here."""
import asyncio
import json
import math
import os
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
try:
    from bacpypes3.apdu import ErrorRejectAbortNack as BACnetError
except ImportError:
    class BACnetError(BaseException):
        """Transport double base for dependency-free tests."""

TECHNICAL = {
    'structured-view': ('nodeType', 'nodeSubtype', 'subordinateList', 'subordinateAnnotations', 'represents'),
    'schedule': ('presentValue', 'effectivePeriod', 'weeklySchedule', 'exceptionSchedule', 'scheduleDefault', 'listOfObjectPropertyReferences', 'priorityForWriting'),
    'notification-class': ('notificationClass', 'priority', 'ackRequired', 'recipientList'),
    'event-enrollment': ('eventType', 'eventParameters', 'objectPropertyReference', 'eventState', 'eventEnable', 'ackedTransitions', 'notifyType', 'notificationClass', 'eventTimeStamps'),
}
ZONES = ('Grande Salle', 'Petite Salle', 'Communs', 'Bureaux administratifs', 'CTA', 'ECS', 'Chaufferie', 'Comptages', 'Alarmes', 'BACnet technique')
QUALITY = ('statusFlags', 'reliability', 'outOfService')


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def serial(value):
    """Keep BACnet structures machine-readable, or explicitly expose raw text."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (tuple, list)):
        return [serial(x) for x in value]
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    try:
        from bacpypes3.constructeddata import Sequence
        from bacpypes3.json.util import sequence_to_json, taglist_to_json_list
        if isinstance(value, Sequence):
            return serial(sequence_to_json(value))
        if getattr(value, 'tagList', None) is not None:
            return {'bacnet_tags': serial(taglist_to_json_list(value.tagList))}
    except (ImportError, TypeError, ValueError, AttributeError):
        pass
    return str(value)


def display_value(kind, raw, metadata):
    """Only controller-provided labels are interpreted; indexes are one-based."""
    if kind.startswith('multi-state-'):
        try:
            number = float(raw)
            labels = metadata.get('stateText')
            if number.is_integer() and isinstance(labels, list) and 1 <= number <= len(labels):
                label = labels[int(number)-1]
                if label:
                    return str(label)
        except (TypeError, ValueError):
            pass
    if kind.startswith('binary-'):
        prop = {'active': 'activeText', '1': 'activeText', 'true': 'activeText',
                'inactive': 'inactiveText', '0': 'inactiveText', 'false': 'inactiveText'}.get(str(raw).lower())
        if prop and metadata.get(prop):
            return str(metadata[prop])
    return raw


def properties_for(kind):
    props = ['objectName', 'description']
    if kind.startswith(('analog-', 'binary-', 'multi-state-')):
        props.extend(QUALITY)
    if kind.startswith('analog-'):
        props.append('units')
    if kind.startswith('binary-'):
        props.extend(('activeText', 'inactiveText'))
    if kind.startswith('multi-state-'):
        props.extend(('numberOfStates', 'stateText'))
    props.extend(TECHNICAL.get(kind, ()))
    return props


class ReadGate:
    """One outstanding request; throughput limit and transport-error backoff."""
    def __init__(self, reader, rate=20, timeout=15):
        self.reader = reader
        self.rate = rate
        self.timeout = timeout
        self.lock = asyncio.Lock()
        self.next_request = 0
        self.failures = 0
        self.errors = 0
        self.unsupported = 0
        self.successes = 0
        self.last_success = None
        self.backoff_until = 0
        self.last_error = None

    async def read(self, bacnet, address, kind, instance, prop):
        async with self.lock:
            await asyncio.sleep(max(0, self.next_request-time.monotonic(), self.backoff_until-time.monotonic()))
            if not self.reader.running:
                return None
            started = time.monotonic()
            try:
                query = f'{address} {kind} {instance} {prop}'
                # BAC0.read synthesizes True/False text when binary labels are absent.
                # The underlying ReadProperty preserves missing properties as errors.
                if hasattr(bacnet, 'build_rp_request'):
                    args = bacnet.build_rp_request(query.split())
                    request = bacnet.this_application.app.read_property(*args)
                else:
                    request = bacnet.read(query)  # transport doubles used in tests
                result = await asyncio.wait_for(request, self.timeout)
                if result is None:
                    raise ValueError('empty BACnet response')
                self.successes += 1
                self.last_success = utcnow()
                self.failures = 0
                self.last_error = None
                # Slow controllers reduce the request rate even with successful reads.
                self.next_request = time.monotonic()+max(1/self.rate, min(2, (time.monotonic()-started)/2))
                return result
            except (Exception, BACnetError) as error:
                message = (type(error).__name__+' '+str(getattr(error, 'reason', error))).lower().replace('-', '').replace('_', '').replace(' ', '')
                optional = any(s in message for s in ('unknownproperty', 'unknownobject', 'propertyisnotanarray'))
                if optional:
                    self.unsupported += 1
                else:
                    self.errors += 1
                    self.failures += 1
                    self.backoff_until = time.monotonic()+min(60, 2**min(self.failures, 6))
                self.last_error = type(error).__name__
                self.next_request = time.monotonic()+1/self.rate
                return None


class ActiveViews:
    def __init__(self, timeout=15):
        self.timeout = timeout
        self.clients = {}

    def heartbeat(self, client, keys, known, now=None):
        now = time.monotonic() if now is None else now
        self.active(now)
        if not isinstance(client, str) or not 1 <= len(client) <= 100:
            raise ValueError('invalid client')
        if not isinstance(keys, list) or len(keys) > 40 or any(not isinstance(k, str) for k in keys):
            raise ValueError('invalid visible points')
        if client not in self.clients and len(self.clients) >= 32:
            raise ValueError('too many clients')
        if keys:
            self.clients[client] = (now, set(keys) & known)
        else:
            self.clients.pop(client, None)

    def active(self, now=None):
        now = time.monotonic() if now is None else now
        expired = [key for key, (stamp, _) in self.clients.items() if now-stamp >= self.timeout]
        for key in expired:
            self.clients.pop(key, None)
        return set().union(*(keys for _, keys in self.clients.values())) if self.clients else set()


class Supervisor:
    def __init__(self, reader):
        self.r = reader
        self.normal = float(os.getenv('NORMAL_INTERVAL', '30'))
        self.fast = float(os.getenv('ACTIVE_INTERVAL', '2'))
        self.stale = float(os.getenv('STALE_AFTER', '180'))
        self.views = ActiveViews(float(os.getenv('ACTIVE_TIMEOUT', '15')))
        self.gate = ReadGate(reader, float(os.getenv('MAX_READ_RATE', '20')), float(os.getenv('READ_TIMEOUT', '15')))
        self.records = {}
        self.due = {}
        self.last_good = {}
        self.last_attempt = {}
        self.device_id = int(os.getenv('TARGET_DEVICE_ID', '130'))
        self.address = reader.TARGET_IP + (f':{reader.BACNET_PORT}' if reader.BACNET_PORT != 47808 else '')
        self.info = {}
        self.meta_queue = deque()
        self.meta_cycle_started = 0
        self.metadata_complete = False
        self.last_inventory = None
        self.next_discovery = 0
        self.last_saved = 0
        self.steps = 0
        self.server = None
        self.poll_started = time.monotonic()
        self.poll_duration = 0
        self.sweep_remaining = set()
        self.published = 0

    def seed(self):
        self.info = self.r.metadata_cache.get((self.device_id, 'device'), {})
        for kind, instance in self.r.object_cache.get(self.device_id, []):
            key = f'{kind}_{instance}'
            if key in self.records:
                self.records[key]['in_object_list'] = True
                continue
            meta = dict(self.r.metadata_cache.get((self.device_id, kind, instance), {}))
            self.records[key] = {'key': key, 'device_instance': self.device_id, 'object_type': kind,
                'object_instance': instance, 'address': self.address, 'read_only': True,
                'metadata': meta, 'metadata_reads': {}, 'present_value': None, 'value': None,
                'last_read': None, 'last_attempt': None, 'read_error': None, 'in_object_list': True}
            self.due[key] = 0
        self.schedule_metadata()
        self.sweep_remaining = {key for key, rec in self.records.items() if rec['object_type'] in self.r.VALUE_TYPES and rec['in_object_list']}

    def schedule_metadata(self):
        self.meta_queue = deque((key, prop) for key, rec in self.records.items()
                                if rec['in_object_list'] for prop in properties_for(rec['object_type']))
        self.meta_cycle_started = time.monotonic()
        self.metadata_complete = False

    def attributes(self, rec):
        meta = rec['metadata']
        zone, subsystem, candidate = self.r.classify(meta.get('objectName', ''), meta.get('description', ''), meta.get('units', ''))
        candidate = candidate or meta.get('units') in {'megawatt-hours', 'cubic-meters', 'liters', 'cubic-meters-per-hour', 'liters-per-second', 'watts', 'kilowatts'}
        # Existing classification remains visible as a proposal, not verified room semantics.
        raw = rec['present_value']
        result = {k: v for k, v in rec.items() if k not in ('metadata',)}
        result.update(object_name=meta.get('objectName', rec['key']), description=meta.get('description'),
            bacnet_units=meta.get('units'), mct_zone=zone, mct_subsystem=subsystem,
            classification_source='name/description heuristic; unvalidated', meter_candidate=candidate,
            meter_evidence=[str(meta.get('units', '')), str(meta.get('objectName', '')), str(meta.get('description', ''))] if candidate else [],
            raw_value=raw, display_value=display_value(rec['object_type'], raw, meta),
            status_flags=meta.get('statusFlags'), reliability=meta.get('reliability'),
            out_of_service=meta.get('outOfService'), number_of_states=meta.get('numberOfStates'),
            state_text=meta.get('stateText'), active_text=meta.get('activeText'), inactive_text=meta.get('inactiveText'),
            available=rec['key'] in self.last_good and time.monotonic()-self.last_good[rec['key']]<self.stale and rec['in_object_list'])
        return result

    def publish(self, rec):
        if rec['value'] is None:
            return False
        attrs = self.attributes(rec)
        if not attrs['available']:
            return False
        kind = rec['object_type']
        unit, device_class = self.r.UNITS.get(rec['metadata'].get('units'), (None, None))
        state = attrs['display_value'] if kind.startswith('multi-state-') else rec['value']
        friendly = attrs['object_name'] if attrs['mct_zone']=='Technique BACnet' else attrs['mct_zone']+' · '+attrs['object_name']
        try:
            return self.r.bridge.sensor(self.device_id, self.info, rec['key'], friendly, state, attrs,
                binary=kind.startswith('binary-'), unit=unit, device_class=device_class)
        except Exception as error:
            self.r.log.warning('Publication MQTT différée (%s).', type(error).__name__)
            return False

    async def read_value(self, bacnet, key):
        rec = self.records[key]
        rec['last_attempt'] = utcnow()
        self.last_attempt[key] = time.monotonic()
        raw = await self.r.read_property_safe(bacnet, self.address, rec['object_type'], rec['object_instance'], 'presentValue')
        value = self.r.normalized_value(rec['object_type'], raw)
        if raw is not None and value is not None:
            rec.update(present_value=serial(raw), value=value, last_read=utcnow(), read_error=None)
            self.last_good[key] = time.monotonic()
            if self.publish(rec):
                self.published += 1
        else:
            rec['read_error'] = self.gate.last_error or 'invalid-value'
        self.due[key] = time.monotonic() + (self.fast if key in self.views.active() and not self.gate.failures else self.normal)
        self.sweep_remaining.discard(key)
        if not self.sweep_remaining:
            self.poll_duration = round(time.monotonic()-self.poll_started, 2)
            self.poll_started = time.monotonic()
            self.sweep_remaining = {k for k, r in self.records.items() if r['object_type'] in self.r.VALUE_TYPES and r['in_object_list']}

    async def read_metadata(self, bacnet):
        key, prop = self.meta_queue.popleft()
        rec = self.records[key]
        value = await self.r.read_property_safe(bacnet, self.address, rec['object_type'], rec['object_instance'], prop)
        status = {'attempted_at': utcnow(), 'status': 'read' if value is not None else 'unavailable'}
        if value is not None:
            rec['metadata'][prop] = str(value) if prop in ('units', 'reliability', 'objectName', 'description', 'activeText', 'inactiveText', 'nodeType') else serial(value)
            status['last_success'] = status['attempted_at']
        else:
            previous = rec['metadata_reads'].get(prop, {})
            if previous.get('last_success'):
                status['last_success'] = previous['last_success']
            status['error'] = self.gate.last_error
        rec['metadata_reads'][prop] = status
        if not self.meta_queue:
            self.metadata_complete = True
            self.last_inventory = utcnow()
            self.r.log.info('Phase 2 : collecte enrichie terminée pour %s objets.', len(self.records))

    def next_value(self, now):
        active = self.views.active(now)
        candidates = []
        for key, rec in self.records.items():
            if rec['object_type'] not in self.r.VALUE_TYPES or not rec['in_object_list']:
                continue
            interval = self.fast if key in active and not self.gate.failures and not rec['read_error'] else self.normal
            deadline = min(self.due.get(key, 0), self.last_attempt.get(key, -1e9)+interval)
            if deadline <= now:
                candidates.append((deadline, key))
        return min(candidates)[1] if candidates else None

    def snapshot(self):
        objects = []
        for rec in self.records.values():
            objects.append(dict(self.attributes(rec), metadata=rec['metadata']))
        active = self.views.active()
        zones = {}
        for rec in objects:
            zones[rec['mct_zone']] = zones.get(rec['mct_zone'], 0)+1
        return {'version': self.r.VERSION, 'updated_at': utcnow(), 'device': self.info,
            'device_instance': self.device_id, 'read_only': True, 'zones': ZONES,
            'summary': {'object_count': len(objects), 'values_read': len(self.last_good),
                'available_values': sum(x['available'] for x in objects),
                'zones': zones, 'published': self.published,
                'meter_candidates': [{'type': x['object_type'], 'instance': x['object_instance'], 'name': x['object_name'], 'units': x['bacnet_units']} for x in objects if x['meter_candidate']],
                'metadata_complete': self.metadata_complete, 'metadata_remaining': len(self.meta_queue),
                'last_inventory': self.last_inventory, 'last_bacnet_success': self.gate.last_success,
                'read_errors': self.gate.errors, 'unsupported_properties': self.gate.unsupported,
                'mqtt_connected': bool(getattr(self.r.bridge, 'connected', None) and self.r.bridge.connected.is_set()),
                'active_points': len(active), 'active_clients': len(self.views.clients),
                'normal_interval': self.normal, 'active_interval': self.fast,
                'metadata_interval': self.r.METADATA_REFRESH, 'read_timeout': self.gate.timeout,
                'max_read_rate': self.gate.rate, 'backoff_seconds': max(0, round(self.gate.backoff_until-time.monotonic(), 1))},
            'objects': objects}

    def save(self):
        payload = self.snapshot()
        path = Path('/data/inventory.json')
        try:
            tmp = path.with_suffix('.tmp')
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
            tmp.replace(path)
        except OSError:
            self.r.log.warning('Enregistrement de l’inventaire impossible.')
        self.last_saved = time.monotonic()
        for key, label, value in [('read_errors', 'Erreurs de lecture', self.gate.errors),
                ('object_count', 'Objets BACnet', len(self.records)), ('values_read', 'Valeurs lues', len(self.last_good)),
                ('metadata_remaining', 'Métadonnées restantes', len(self.meta_queue)),
                ('active_points', 'Points visibles', len(self.views.active()))]:
            try:
                self.r.bridge.sensor(self.device_id, self.info, key, label, value, diagnostic=True)
            except Exception:
                pass
        try:
            self.r.bridge.sensor(self.device_id, self.info, 'poll_duration', 'Durée de lecture', self.poll_duration, unit='s', device_class='duration', diagnostic=True)
            if self.gate.last_success:
                self.r.bridge.sensor(self.device_id, self.info, 'last_update', 'Dernière lecture', self.gate.last_success, device_class='timestamp', diagnostic=True)
        except Exception:
            pass

    async def run(self, bacnet):
        self.seed()
        try:
            self.server = await asyncio.start_server(self.http, '0.0.0.0', 8098, limit=16384)
            self.r.log.info('Interface MCT disponible via Ingress, READ ONLY.')
        except OSError as error:
            self.r.log.error('Interface indisponible (%s) ; lectures BACnet maintenues.', type(error).__name__)
        try:
            while self.r.running:
                now = time.monotonic()
                if not self.records and now >= self.next_discovery:
                    try:
                        found = await asyncio.wait_for(bacnet.who_is(address=self.address, timeout=5), 15)
                        for device in found or []:
                            address, device_id = self.r.normalize_discovered_device(device)
                            if address and address.split(':')[0] == self.r.TARGET_IP and device_id == self.device_id:
                                await self.r.inspect_device(bacnet, address, device_id)
                                await self.r.get_object_list(bacnet, address, device_id)
                                self.seed()
                                break
                    except Exception as error:
                        self.r.log.warning('Découverte CPO différée (%s).', type(error).__name__)
                    self.next_discovery = time.monotonic()+60
                if self.records and not self.meta_queue and now-self.meta_cycle_started >= self.r.METADATA_REFRESH:
                    self.info = await self.r.device_metadata(bacnet, self.address, self.device_id)
                    previous_time = self.r.cache_time.get(self.device_id)
                    objects = await self.r.get_object_list(bacnet, self.address, self.device_id, force=True)
                    if self.r.cache_time.get(self.device_id) != previous_time:
                        current = {f'{kind}_{instance}' for kind, instance in objects}
                        for key, rec in self.records.items():
                            rec['in_object_list'] = key in current
                        self.seed()
                    else:
                        self.schedule_metadata()
                key = self.next_value(now)
                # Every fourth operation services metadata, even with a busy active view.
                if self.meta_queue and (key is None or self.steps % 4 == 0):
                    await self.read_metadata(bacnet)
                elif key:
                    await self.read_value(bacnet, key)
                else:
                    await asyncio.sleep(.1)
                self.steps += 1
                if time.monotonic()-self.last_saved >= 10:
                    self.save()
        finally:
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            self.save()

    async def http(self, incoming, outgoing):
        status, mime, body = '400 Bad Request', 'text/plain; charset=utf-8', b'Bad request'
        try:
            peer = outgoing.get_extra_info('peername')
            if not peer or peer[0] != '172.30.32.2':
                status, body = '403 Forbidden', b'Ingress only'
            else:
                header = await asyncio.wait_for(incoming.readuntil(b'\r\n\r\n'), 5)
                lines = header.decode('iso-8859-1').split('\r\n')
                method, target, _ = lines[0].split(' ')
                headers = dict(line.lower().split(':', 1) for line in lines[1:] if ':' in line)
                length = int(headers.get('content-length', '0'))
                if length < 0 or length > 16384 or 'transfer-encoding' in headers:
                    raise ValueError('request too large')
                path = urlsplit(target).path
                if method == 'GET' and path == '/':
                    body = Path(__file__).with_name('mct.html').read_bytes()
                    status, mime = '200 OK', 'text/html; charset=utf-8'
                elif method == 'GET' and path in ('/api/inventory', '/inventory.json'):
                    body = json.dumps(self.snapshot(), ensure_ascii=False, allow_nan=False).encode()
                    status, mime = '200 OK', 'application/json; charset=utf-8'
                elif method == 'POST' and path == '/api/heartbeat' and headers.get('content-type', '').strip().startswith('application/json'):
                    data = json.loads(await asyncio.wait_for(incoming.readexactly(length), 5))
                    if not isinstance(data, dict):
                        raise ValueError('invalid heartbeat')
                    known = {key for key, rec in self.records.items() if rec['object_type'] in self.r.VALUE_TYPES and rec['in_object_list']}
                    self.views.heartbeat(data.get('client'), data.get('keys'), known)
                    status, mime, body = '200 OK', 'application/json', b'{"read_only":true}'
                else:
                    status, body = '404 Not Found', b'Not found'
        except (ValueError, OSError, asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            pass
        try:
            outgoing.write((f'HTTP/1.1 {status}\r\nContent-Type: {mime}\r\nContent-Length: {len(body)}\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n').encode()+body)
            await outgoing.drain()
        finally:
            outgoing.close()
            await outgoing.wait_closed()
