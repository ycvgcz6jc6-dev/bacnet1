"""Password and expiring sessions for the loopback simulation server."""
import hashlib, hmac, json, os, secrets, time
from http.cookies import SimpleCookie
from pathlib import Path
class Auth:
    def __init__(self, folder):
        self.folder=Path(folder); self.folder.mkdir(mode=0o700,exist_ok=True)
        config=self.folder/'password.json'
        if not config.exists():
            password=secrets.token_urlsafe(18); salt=secrets.token_hex(16)
            digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),300000).hex()
            for name,text in [('password.json',json.dumps(dict(salt=salt,digest=digest))),('Mot-de-passe-simulation.txt',password+'\n')]:
                fd=os.open(self.folder/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,'w') as f:f.write(text)
        self.config=json.loads(config.read_text()); self.sessions={}; self.failures=[]
    def login(self,password):
        now=time.monotonic(); self.failures=[t for t in self.failures if now-t<60]
        if len(self.failures)>=5:return None
        if not isinstance(password,str) or len(password)>256:return None
        digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(self.config['salt']),300000).hex()
        if not hmac.compare_digest(digest,self.config['digest']):self.failures.append(now); return None
        token=secrets.token_urlsafe(32); self.sessions[token]=now+900; self.failures=[]; return token
    def token(self,header):
        cookie=SimpleCookie()
        try:cookie.load(header or ''); return cookie['mct_demo'].value if 'mct_demo' in cookie else None
        except Exception:return None
    def valid(self,header):
        now=time.monotonic(); self.sessions={k:v for k,v in self.sessions.items() if v>now}
        return self.sessions.get(self.token(header),0)>now
    def logout(self,header):self.sessions.pop(self.token(header),None)
    def change_password(self, old, new, confirmation):
        if not isinstance(new,str) or not 12 <= len(new) <= 256:
            raise ValueError('Le nouveau mot de passe doit contenir entre 12 et 256 caractères.')
        if new != confirmation: raise ValueError('Les nouveaux mots de passe ne correspondent pas.')
        if new == old: raise ValueError('Choisissez un mot de passe différent.')
        token=self.login(old)
        if token is None: raise ValueError('Ancien mot de passe incorrect ou trop de tentatives.')
        self.sessions.pop(token,None)
        salt=secrets.token_hex(16)
        config=dict(salt=salt,digest=hashlib.pbkdf2_hmac('sha256',new.encode(),bytes.fromhex(salt),300000).hex())
        temporary=self.folder/('password-'+secrets.token_hex(8)+'.tmp')
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:
            json.dump(config,f);f.flush();os.fsync(f.fileno())
        os.replace(temporary,self.folder/'password.json')
        self.config=config;self.sessions.clear()
        # Never store the new password in clear text. Preserve the initial file.
