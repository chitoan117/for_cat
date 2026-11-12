"""Publish honest camera-unavailable state while detector cannot run."""
from pathlib import Path
from contextlib import closing
import json,sqlite3,sys,time

def publish(db_path,reason,boot_id=None):
    assert reason in ('CAMERA_NOT_FOUND','CAMERA_BUSY')
    state={'health':'DISCONNECTED','classification':'UNKNOWN','confidence':None,
      'source':'EXISTING_CPP_TENSORRT_STDOUT','host_boot_id':boot_id or Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
      'updated_monotonic_ms':int(time.monotonic()*1000),'last_observation_at':None,
      'actuator_execution':False,'reason':reason}
    with closing(sqlite3.connect(str(db_path),timeout=.5)) as db:
        db.execute('CREATE TABLE IF NOT EXISTS ai_latest(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL)')
        db.execute('INSERT OR REPLACE INTO ai_latest VALUES(1,?)',(json.dumps(state,separators=(',',':')),));db.commit()
    return state

if __name__=='__main__':
    try:publish(sys.argv[1],sys.argv[2])
    except (OSError,sqlite3.Error) as exc:print('Camera health state unavailable: '+str(exc),file=sys.stderr)
