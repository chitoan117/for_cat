"""Bounded database waits; durable event retries never reopen the UART."""
from contextlib import closing
from pathlib import Path
import json,os,sqlite3,time,uuid

class BridgeStorage:
 def __init__(self,db_path,timeout=.05):
  self.db_path=Path(db_path);self.timeout=timeout;self.errors=0;self.last_error=None
  self.spool=self.db_path.parent/'bridge_event_outbox'
  self.spool.mkdir(mode=0o700,exist_ok=True)
 def latest(self,body):
  try:
   with closing(sqlite3.connect(str(self.db_path),timeout=self.timeout)) as db:
    db.execute('INSERT INTO esp32_latest(id,body) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',(body,));db.commit()
   return True
  except sqlite3.Error as exc:self.errors+=1;self.last_error=str(exc);return False
 def event(self,kind,at,body):
  try:
   with closing(sqlite3.connect(str(self.db_path),timeout=self.timeout)) as db:
    db.execute('INSERT INTO esp32_events(kind,occurred_at,body) VALUES(?,?,?)',(kind,at,body));db.commit()
   return True
  except sqlite3.Error as exc:
   self.errors+=1;self.last_error=str(exc)
   event={'id':uuid.uuid4().hex,'kind':kind,'occurred_at':at,'body':body}
   target=self.spool/(str(time.time_ns())+'_'+event['id']+'.json');temp=target.with_suffix('.tmp')
   with temp.open('x',encoding='utf8') as f:
    json.dump(event,f,separators=(',',':'));f.flush();os.fsync(f.fileno())
   os.replace(temp,target)
   return False
 def flush(self,limit=4):
  written=0
  for p in sorted(self.spool.glob('*.json'))[:limit]:
   try:
    event=json.loads(p.read_text(encoding='utf8'))
    with closing(sqlite3.connect(str(self.db_path),timeout=self.timeout)) as db:
     db.execute('CREATE TABLE IF NOT EXISTS bridge_event_delivery(id TEXT PRIMARY KEY)')
     inserted=db.execute('INSERT OR IGNORE INTO bridge_event_delivery(id) VALUES(?)',(event['id'],)).rowcount
     if inserted:db.execute('INSERT INTO esp32_events(kind,occurred_at,body) VALUES(?,?,?)',(event['kind'],event['occurred_at'],event['body']))
     db.commit()
    p.unlink();written+=1
   except sqlite3.Error as exc:self.errors+=1;self.last_error=str(exc);break
   except (OSError,ValueError,KeyError) as exc:self.errors+=1;self.last_error=str(exc);break
  return written
