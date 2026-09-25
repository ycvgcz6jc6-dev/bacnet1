import asyncio, json, logging, math, os, signal, socket, sys, threading, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path
import BAC0
import paho.mqtt.client as mqtt

VERSION='0.3.2-phase1'
LOCAL_IP=os.getenv('LOCAL_IP','192.168.0.39/24'); TARGET_IP=os.getenv('TARGET_IP','192.168.0.249')
BACNET_PORT=int(os.getenv('BACNET_PORT','47808')); DISCOVERY_INTERVAL=int(os.getenv('DISCOVERY_INTERVAL','60'))
METADATA_REFRESH=int(os.getenv('METADATA_REFRESH','1800')); POLL_DELAY=float(os.getenv('POLL_DELAY','0.02'))
READ_DEVICE_INFO=os.getenv('READ_DEVICE_INFO','true').lower() in ('1','true','yes'); LOG_LEVEL=os.getenv('LOG_LEVEL','INFO').upper()
logging.basicConfig(level=getattr(logging,LOG_LEVEL,logging.INFO),format='%(asctime)s | %(levelname)s | %(message)s'); log=logging.getLogger('BACnetReader')
running=True; bridge=None; metadata_cache={}; object_cache={}; cache_time={}; metadata_time={}
VALUE_TYPES={'analog-input','analog-output','analog-value','binary-input','binary-output','binary-value','multi-state-input','multi-state-output','multi-state-value'}
META_PROPS=('objectName','description','units','statusFlags','reliability','outOfService')
UNITS={'degrees-celsius':('°C','temperature'),'percent':('%',None),'percent-relative-humidity':('%','humidity'),'pascals':('Pa','pressure'),'kilopascals':('kPa','pressure'),'watts':('W','power'),'kilowatts':('kW','power'),'watt-hours':('Wh','energy'),'kilowatt-hours':('kWh','energy'),'cubic-meters-per-hour':('m³/h','volume_flow_rate'),'liters-per-second':('L/s','volume_flow_rate'),'seconds':('s','duration'),'minutes':('min','duration'),'hours':('h','duration')}
ZONE_RULES=[('Grande Salle',('bloca','bloc_a','salle_a','gp1','tcgp1')),('Petite Salle',('blocb','bloc_b','salle_b')),('Communs',('blocc','blocd','bloc_c','bloc_d','c_d')),('Bureaux administratifs',('blocext','bloc_ext','extension')),('ECS',('ecs','boil')),('Chaufferie',('chr','chau','chaud'))]
METER_HINTS=('mbus','m-bus','modbus','meter','compteur','kwh','mwh','energie','energy','gaz','gas','eau','water','volume','m3','pulse','index','power')

def stop_handler(*_):
 global running; running=False; log.info('Arrêt demandé.')
signal.signal(signal.SIGTERM,stop_handler); signal.signal(signal.SIGINT,stop_handler)

def test_ip_connectivity():
 try: socket.inet_aton(TARGET_IP); return True
 except OSError: log.error('Adresse cible invalide : %s',TARGET_IP); return False

async def read_property_safe(bacnet,address,obj,instance,prop):
 try: return await bacnet.read(f'{address} {obj} {instance} {prop}')
 except Exception as err: log.debug('Lecture impossible [%s %s %s %s]: %s',address,obj,instance,prop,err); return None

def text(v): return None if v is None else str(v)
def classify(name,description='',units=''):
 hay=f'{name} {description}'.lower().replace('-','_')
 zone='Technique BACnet'
 for label,needles in ZONE_RULES:
  if any(n in hay for n in needles): zone=label; break
 if any(n in hay for n in ('cta','vent','vpu','vex','debpul','debrep','prspul','prsrep')): subsystem='Ventilation / CTA'
 elif any(n in hay for n in ('ecs','boil')): subsystem='ECS'
 elif any(n in hay for n in ('tmp','temp','chr','rad','pompe','po','vanne')): subsystem='Chauffage'
 elif any(n in hay for n in ('alm','alarm','fire')): subsystem='Alarmes / sécurité'
 else: subsystem='BACnet'
 meter=any(n in hay for n in METER_HINTS) or str(units).lower() in ('kilowatt-hours','watt-hours')
 return zone,subsystem,meter

def normalized_value(obj_type,value):
 if value is None:return None
 if obj_type.startswith('binary-'):
  s=str(value).lower()
  return 'ON' if s in ('active','1','true') else ('OFF' if s in ('inactive','0','false') else None)
 try:
  n=float(value)
  if not math.isfinite(n):return None
  return int(n) if obj_type.startswith('multi-state-') else round(n,4)
 except (TypeError,ValueError): return str(value) if obj_type.startswith('multi-state-') else None

class OfflineBridge:
 def sensor(self,*args,**kwargs): return False
 def close(self): pass

async def mqtt_worker():
 global bridge
 while running:
  try:
   bridge=await asyncio.to_thread(MQTTBridge)
   return
  except Exception as err:
   log.warning('MQTT indisponible (%s) ; BACnet continue en lecture seule.',type(err).__name__)
  for _ in range(15):
   if not running:return
   await asyncio.sleep(1)

class MQTTBridge:
 def __init__(self):
  req=urllib.request.Request('http://supervisor/services/mqtt',headers={'Authorization':'Bearer '+os.environ['SUPERVISOR_TOKEN']})
  with urllib.request.urlopen(req,timeout=10) as response: result=json.load(response)
  if result.get('result')!='ok': raise RuntimeError('Service MQTT indisponible')
  svc=result['data']; self.root='bacnet_reader/'+TARGET_IP.replace('.','_'); self.availability=self.root+'/availability'; self.connected=threading.Event(); self.configs={}
  self.client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='bacnet_reader_'+TARGET_IP.replace('.','_'),protocol=mqtt.MQTTv5)
  self.client.username_pw_set(svc['username'],svc['password']);
  if svc.get('ssl'): self.client.tls_set()
  self.client.will_set(self.availability,'offline',qos=1,retain=True); self.client.on_connect=self.on_connect; self.client.on_disconnect=self.on_disconnect; self.client.reconnect_delay_set(1,60); self.client.max_queued_messages_set(2000); self.client.connect_async(svc['host'],int(svc['port']),60); self.client.loop_start()
 def on_connect(self,client,userdata,flags,reason_code,properties):
  if reason_code.is_failure: log.error('Connexion MQTT refusée : %s',reason_code); return
  self.configs.clear(); self.connected.set(); client.publish(self.availability,'online',qos=1,retain=True); log.info('MQTT connecté.')
 def on_disconnect(self,*_): self.connected.clear()
 def publish(self,topic,payload,retain=False):
  if not self.connected.is_set(): return False
  if isinstance(payload,dict): payload=json.dumps(payload,ensure_ascii=False,allow_nan=False)
  return self.client.publish(topic,payload,qos=1,retain=retain).rc==mqtt.MQTT_ERR_SUCCESS
 def device(self,device_id,info): return {'identifiers':[f'bacnet_reader_{TARGET_IP}_{device_id}'],'name':info.get('objectName') or f'CPO {device_id}','manufacturer':info.get('vendorName') or 'BACnet','model':info.get('modelName') or 'BACnet/IP','sw_version':info.get('firmwareRevision') or 'unknown'}
 def sensor(self,device_id,info,key,name,value,attrs=None,binary=False,unit=None,device_class=None,diagnostic=False):
  component='binary_sensor' if binary else 'sensor'; unique=f"bacnet_{TARGET_IP.replace('.','_')}_{device_id}_{key}"; topic=f'{self.root}/{device_id}/{key}'
  cfg={'name':name,'unique_id':unique,'state_topic':topic+'/state','device':self.device(device_id,info),'availability_topic':self.availability,'expire_after':max(180,DISCOVERY_INTERVAL*3),'origin':{'name':'BACnet Reader','sw_version':VERSION}}
  if binary: cfg.update(payload_on='ON',payload_off='OFF')
  if unit: cfg['unit_of_measurement']=unit; cfg['state_class']='measurement' if device_class not in ('energy','duration') else 'total_increasing' if device_class=='energy' else 'measurement'
  if device_class: cfg['device_class']=device_class
  if diagnostic: cfg['entity_category']='diagnostic'
  if attrs is not None: cfg['json_attributes_topic']=topic+'/attributes'
  ct=f'homeassistant/{component}/{unique}/config'
  if self.configs.get(ct)!=cfg and self.publish(ct,cfg,True): self.configs[ct]=cfg
  if attrs is not None:self.publish(topic+'/attributes',attrs,True)
  return self.publish(topic+'/state',str(value))
 def close(self):
  if self.connected.is_set(): self.client.publish(self.availability,'offline',qos=1,retain=True).wait_for_publish(timeout=3)
  self.client.disconnect(); self.client.loop_stop()

async def device_metadata(bacnet,address,device_id):
 key=(device_id,'device')
 if key in metadata_cache and time.monotonic()-metadata_time.get(key,0)<METADATA_REFRESH:return metadata_cache[key]
 info={}
 for prop in ('objectName','vendorName','modelName','firmwareRevision','applicationSoftwareVersion','description','location','vendorIdentifier','protocolVersion','protocolRevision'):
  v=await read_property_safe(bacnet,address,'device',device_id,prop)
  if v is not None:info[prop]=str(v)
 metadata_cache[key]=info; metadata_time[key]=time.monotonic(); return info

async def get_object_list(bacnet,address,device_id,force=False):
 now=time.monotonic()
 if not force and device_id in object_cache and now-cache_time.get(device_id,0)<METADATA_REFRESH:return object_cache[device_id]
 objs=await read_property_safe(bacnet,address,'device',device_id,'objectList')
 if objs is None:return object_cache.get(device_id,[])
 parsed=[]
 for obj in objs:
  try: parsed.append((str(obj[0]),int(obj[1])))
  except Exception: pass
 object_cache[device_id]=parsed; cache_time[device_id]=now; log.info('objectList mis en cache : %s objets.',len(parsed)); return parsed

async def object_metadata(bacnet,address,device_id,obj_type,obj_instance):
 key=(device_id,obj_type,obj_instance)
 if key in metadata_cache and time.monotonic()-metadata_time.get(key,0)<METADATA_REFRESH:return metadata_cache[key]
 meta={}
 props=['objectName','description','statusFlags','reliability','outOfService']
 if obj_type.startswith('analog-'):props.append('units')
 if obj_type.startswith('multi-state-'):props+=['numberOfStates','stateText']
 for prop in props:
  v=await read_property_safe(bacnet,address,obj_type,obj_instance,prop)
  if v is not None:meta[prop]=str(v) if prop!='stateText' else [str(x) for x in v]
 meta.setdefault('objectName',f'{obj_type} {obj_instance}'); zone,subsystem,meter=classify(meta['objectName'],meta.get('description',''),meta.get('units','')); meta.update(mct_zone=zone,mct_subsystem=subsystem,meter_candidate=meter)
 metadata_cache[key]=meta; metadata_time[key]=time.monotonic(); return meta

async def inventory_objects(bacnet,address,device_id):
 started=time.monotonic(); info=await device_metadata(bacnet,address,device_id); objects=await get_object_list(bacnet,address,device_id); records=[]; values_read=published=0; zones={}; meter_candidates=[]
 for obj_type,obj_instance in objects:
  if not running:return
  meta=await object_metadata(bacnet,address,device_id,obj_type,obj_instance); raw=await read_property_safe(bacnet,address,obj_type,obj_instance,'presentValue') if obj_type in VALUE_TYPES else None; value=normalized_value(obj_type,raw); stamp=datetime.now(timezone.utc).isoformat(); zone=meta['mct_zone']; zones[zone]=zones.get(zone,0)+1
  attrs={'device_instance':device_id,'object_type':obj_type,'object_instance':obj_instance,'object_name':meta['objectName'],'description':meta.get('description'),'bacnet_units':meta.get('units'),'status_flags':meta.get('statusFlags'),'reliability':meta.get('reliability'),'out_of_service':meta.get('outOfService'),'number_of_states':meta.get('numberOfStates'),'state_text':meta.get('stateText'),'mct_zone':zone,'mct_subsystem':meta['mct_subsystem'],'meter_candidate':meta['meter_candidate'],'address':address,'present_value':text(raw),'last_read':stamp,'read_only':True}
  records.append(dict(attrs,value=value))
  if meta['meter_candidate']:meter_candidates.append({'type':obj_type,'instance':obj_instance,'name':meta['objectName'],'units':meta.get('units')})
  if value is not None:
   values_read+=1; unit,dc=UNITS.get(meta.get('units'),(None,None)); friendly=f"{zone} · {meta['objectName']}" if zone!='Technique BACnet' else meta['objectName']
   if bridge.sensor(device_id,info,f'{obj_type}_{obj_instance}',friendly,value,attrs,binary=obj_type.startswith('binary-'),unit=unit,device_class=dc):published+=1
  await asyncio.sleep(POLL_DELAY)
 stamp=datetime.now(timezone.utc).isoformat(); duration=round(time.monotonic()-started,2)
 bridge.sensor(device_id,info,'last_update','Dernière lecture',stamp,device_class='timestamp',diagnostic=True); bridge.sensor(device_id,info,'values_read','Valeurs lues',values_read,diagnostic=True); bridge.sensor(device_id,info,'object_count','Objets BACnet',len(objects),diagnostic=True); bridge.sensor(device_id,info,'poll_duration','Durée de lecture',duration,unit='s',device_class='duration',diagnostic=True)
 payload={'version':VERSION,'updated_at':stamp,'device':info,'summary':{'object_count':len(objects),'values_read':values_read,'published':published,'zones':zones,'meter_candidates':meter_candidates},'objects':records}
 try:
  p=Path('/data/inventory.json'); tmp=p.with_suffix('.tmp'); tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8'); tmp.replace(p)
 except OSError:log.warning("Impossible d'enregistrer l'inventaire local.")
 log.info('Inventaire : %s objets, %s valeurs, %s publiées, %.2fs.',len(objects),values_read,published,duration); log.info('Classification MCT : %s',zones); log.info('Candidats comptage M-Bus/Modbus : %s',len(meter_candidates))

def normalize_discovered_device(device):
 try:
  if hasattr(device,'iAmDeviceIdentifier'):return str(device.pduSource),int(device.iAmDeviceIdentifier[1])
  if isinstance(device,(tuple,list)) and len(device)>=2:return str(device[0]),int(device[1])
  if isinstance(device,dict):
   a=device.get('address') or device.get('Address') or device.get('ip'); d=device.get('device_id') or device.get('deviceId') or device.get('instance')
   if a is not None and d is not None:return str(a),int(d)
 except Exception:pass
 return None,None

async def inspect_device(bacnet,address,device_id):
 info=await device_metadata(bacnet,address,device_id); log.info('Équipement BACnet : %s / Device %s / %s / %s',address,device_id,info.get('objectName'),info.get('modelName'))

async def discovery_cycle(bacnet):
 log.info('========== BACnet discovery ==========')
 try: discovered=await bacnet.who_is(address=f'{TARGET_IP}:{BACNET_PORT}',timeout=5)
 except Exception as err:log.warning('Who-Is : %s',err);return
 if not discovered:log.warning('Aucun équipement BACnet découvert.');return
 target=False
 for dev in discovered:
  address,device_id=normalize_discovered_device(dev)
  if address is None:continue
  await inspect_device(bacnet,address,device_id)
  if address.split(':')[0]==TARGET_IP:
   target=True; log.info('CIBLE BACnet TROUVÉE : %s',TARGET_IP); await inventory_objects(bacnet,address,device_id)
 if not target:log.warning("La cible %s n'a pas été identifiée.",TARGET_IP)

async def main():
 global bridge,running
 log.info('BACnet Reader %s démarré. MODE : READ ONLY',VERSION)
 if not test_ip_connectivity():sys.exit(1)
 bridge=OfflineBridge()
 mqtt_task=asyncio.create_task(mqtt_worker())
 try:
  async with BAC0.start(ip=LOCAL_IP,port=BACNET_PORT) as bacnet:
   while running:
    try:await discovery_cycle(bacnet)
    except Exception:log.exception('Erreur pendant le cycle de découverte.')
    for _ in range(DISCOVERY_INTERVAL):
     if not running:break
     await asyncio.sleep(1)
 except Exception:log.exception("Impossible d'initialiser BACnet/IP.");sys.exit(2)
 finally:
  running=False
  await mqtt_task
  if bridge is not None:await asyncio.to_thread(bridge.close)
if __name__=='__main__':asyncio.run(main())
