"""Local UI test double. Never connects to BACnet, MQTT or Home Assistant."""
import json,sys,time,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path('work/bacnet1/bacnet_reader').resolve()))
from phase3 import asset,ZONE_CAPABILITIES
from phase2 import utcnow,ActiveViews
views=ActiveViews();mode='normal';fail=False
rows=[]
for zone,prefix in [('Grande Salle','TEST_A'),('Petite Salle','TEST_B'),('Communs','TEST_C'),('Bureaux administratifs','TEST_D'),('ECS','TEST_ECS'),('Chaufferie','TEST_CH')]:
 for i,(name,val,units,kind) in enumerate([('Température',21.45,'degrees-celsius','analog-input'),('Consigne',20,'degrees-celsius','analog-value'),('Mode',7,None,'multi-state-value'),('Débit',29000,'cubic-meters-per-hour','analog-value'),('Pompe',0,None,'binary-output')]):
  key=f'{kind}_{len(rows)+1}';meta={'objectName':prefix+'_'+name,'description':'Point de test simulé','units':units,'statusFlags':[0,0,0,0],'reliability':'no-fault-detected','outOfService':0}
  if kind=='multi-state-value':meta['stateText']=['1','2','3','4','5','6','Texte CPO simulé'];meta['numberOfStates']=7
  rows.append({'key':key,'device_instance':130,'object_instance':len(rows)+1,'object_type':kind,'address':'SIMULATION','object_name':meta['objectName'],'description':meta['description'],'raw_value':val,'present_value':val,'display_value':'Texte CPO simulé' if i==2 else val,'mct_zone':zone,'mct_subsystem':'Ventilation / CTA' if i==3 else 'Chauffage','meter_candidate':i==3,'metadata':meta,'metadata_reads':{},'status_flags':[0,0,0,0],'state_text':meta.get('stateText'),'available':True,'in_object_list':True,'bacnet_units':units})
for i in range(55):
 r=dict(rows[0]);r.update(key=f'analog-value_{100+i}',object_type='analog-value',object_instance=100+i,object_name=f'TEST_A_Point_{i}');rows.append(r)
rows.append({'key':'event-enrollment_1','object_type':'event-enrollment','object_instance':1,'object_name':'Événement simulé','metadata':{'eventState':0,'notificationClass':1},'metadata_reads':{},'mct_zone':'BACnet technique'})
rows.append({'key':'notification-class_1','object_type':'notification-class','object_instance':1,'object_name':'URGENT','metadata':{'notificationClass':1,'priority':[1,2,3]},'metadata_reads':{},'mct_zone':'BACnet technique'})
rows.append({'key':'schedule_3','object_type':'schedule','object_instance':3,'object_name':'Horaire de test','metadata':{'weeklySchedule':[{'day-schedule':[{'time':'08:00:00.00','value':{'unsigned':1}},{'time':'18:00:00.00','value':{'unsigned':0}}]} for _ in range(7)],'exceptionSchedule':[]},'metadata_reads':{},'mct_zone':'Grande Salle'})
def snapshot():
 for r in rows:
  r['last_read']=utcnow();r['metadata_reads']={p:{'status':'read','last_success':utcnow()}for p in r['metadata']}
 data={'version':'0.5.0-phase3','preview':'APERÇU LOCAL — DONNÉES SIMULÉES, aucun accès au CPO','device':{'objectName':'SIMULATION','modelName':'Test local'},'device_instance':130,'read_only':True,'zone_capabilities':ZONE_CAPABILITIES,'zones':list(ZONE_CAPABILITIES),'objects':rows,'summary':{'object_count':len(rows),'available_values':85,'active_points':len(views.active()),'metadata_complete':True,'metadata_remaining':0,'metadata_interval':1800,'stale_after':180,'normal_interval':30,'active_interval':2,'read_timeout':15,'max_read_rate':20,'last_bacnet_success':utcnow(),'last_inventory':utcnow(),'mqtt_connected':True,'read_errors':0,'unsupported_properties':0,'backoff_seconds':0,'reads_per_second':8.5,'mean_read_ms':12,'poll_duration':30}}
 return data
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path.split('?')[0] in ['/api/inventory','/inventory.json']:
   if Path('work/preview-offline').exists():self.send_error(503);return
   mime,body='application/json',json.dumps(snapshot()).encode()
  elif self.path=='/api/test-heartbeat':mime,body='application/json',json.dumps({'active':list(views.active())}).encode()
  else:
   result=asset(self.path.split('?')[0])
   if not result:self.send_error(404);return
   mime,body=result
   if mime.startswith("text/html"):
    body=body.replace(b'</nav>',b'<a href="http://127.0.0.1:8767/">Commandes - simulation</a></nav>')
  self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
 def do_POST(self):
  if self.path!='/api/heartbeat':self.send_error(404);return
  data=json.loads(self.rfile.read(int(self.headers['Content-Length'])));views.heartbeat(data['client'],data['keys'],{r['key']for r in rows});Path('work/phase3-heartbeat.json').write_text(json.dumps(data));self.send_response(200);self.end_headers();self.wfile.write(b'{}')
 def log_message(self,*args):pass
ThreadingHTTPServer(('127.0.0.1',8766),Handler).serve_forever()
