"""Loopback-only demonstration; never imports a BACnet transport."""
import json, sys, time, threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE/'phase4-audit/bacnet_reader'))
from command_simulation import CommandSimulation, Policy
from demo_auth import Auth
auth = Auth(BASE/".simulation-private")
# Demonstration limits only, not commissioned building settings.
policies = {k: Policy(15,25,300) if k.startswith('heating') else Policy(1,100,300)
            for k in CommandSimulation.FEATURES}
engine = CommandSimulation(policies, time.monotonic)
lock = threading.Lock()
checkpoint = None

def snapshot():
    result = engine.snapshot()
    now = time.monotonic()
    for item in result['active'].values(): item['remaining'] = max(0,item['expires_at']-now)
    result.update(connected=engine.connected, safety_clear=engine.safety_clear)
    return result

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data, mime='application/json', cookie=None):
        body = data if isinstance(data,bytes) else json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Cache-Control','no-store')
        if cookie: self.send_header('Set-Cookie',cookie)
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path == '/': return self.reply(200,(BASE/'phase4-demo.html').read_bytes(),'text/html; charset=utf-8')
        if self.path == '/state':
            with lock:
                if not auth.valid(self.headers.get('Cookie')): return self.reply(401,{'error':'Connexion requise'})
                return self.reply(200,snapshot())
        self.reply(404,{'error':'Absent'})
    def do_POST(self):
        global engine
        if self.headers.get('Origin') != 'http://127.0.0.1:8767' or self.headers.get('Host') != '127.0.0.1:8767':
            return self.reply(403,{'error':'Origine refusée'})
        if self.path not in ('/command','/login','/logout','/password'): return self.reply(404,{'error':'Absent'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0 < length < 2048: raise ValueError('Requête invalide')
            data=json.loads(self.rfile.read(length))
            with lock:
                if self.path=='/login':
                    token=auth.login(data.get('password'))
                    if not token:return self.reply(401,{'error':'Mot de passe incorrect ou trop de tentatives. Réessayer après une minute.'})
                    return self.reply(200,{},cookie=f'mct_demo={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=900')
                if self.path=='/logout':
                    auth.logout(self.headers.get('Cookie'))
                    return self.reply(200,{},cookie='mct_demo=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                if not auth.valid(self.headers.get('Cookie')):return self.reply(401,{'error':'Connexion requise'})
                if self.path=='/password':
                    auth.change_password(data.get('old'),data.get('new'),data.get('confirmation'))
                    return self.reply(200,{},cookie='mct_demo=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                action=data['action']
                if action=='start': engine.start(data['feature'],data['value'],data['duration'])
                elif action=='stop': engine.stop(data['feature'])
                elif action=='interlocks': engine.interlocks(connected=data['connected'],safety_clear=data['safety_clear'])
                elif action=='restart':
                    saved=engine.snapshot()
                    old=engine.journal.copy()
                    connected,safe=engine.connected,engine.safety_clear
                    engine=CommandSimulation(policies,time.monotonic,saved)
                    engine.journal=old+engine.journal
                    engine.interlocks(connected=connected,safety_clear=safe)
                else: raise ValueError('Action inconnue')
                self.reply(200,snapshot())
        except (ValueError,KeyError,TypeError) as exc: self.reply(400,{'error':str(exc)})
    def log_message(self,*args): pass

def timer():
    while True:
        with lock: engine.tick()
        time.sleep(.2)
if __name__=='__main__':
    threading.Thread(target=timer,daemon=True).start()
    ThreadingHTTPServer(('127.0.0.1',8767),Handler).serve_forever()
