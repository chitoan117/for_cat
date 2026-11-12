"""Deterministic SQL failure at event insert; temporary DB, mock transport only."""
import json,sqlite3,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'candidate/backend'))
from app.api.routes import FeedService
from app.serial_link.mock_transport import MockEsp32Transport
from app.serial_link.protocol import FeedCode
from app.storage.event_store import SQLiteEventStore
from app.storage.repositories import RecordRepository
def main():
    label=sys.argv[1];out=ROOT/'evidence'/label
    if out.exists():raise ValueError('NEW probe label required')
    out.mkdir()
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'synthetic.sqlite3';store=SQLiteEventStore(path);repo=RecordRepository(path);t=MockEsp32Transport();service=FeedService(t,store,records=repo)
        ack=service.request_feed('SYNTHETIC_SQL_FAILURE');t.complete_feed(ack.request_id,FeedCode.SUCCESS)
        db=sqlite3.connect(path)
        try:
            with db:db.execute('CREATE TRIGGER fail_terminal BEFORE INSERT ON events WHEN INSTR(NEW.body,\'"SUCCESS"\')>0 BEGIN SELECT RAISE(ABORT,\'SYNTHETIC_EVENT_FAILURE\'); END')
        finally:db.close()
        error=None
        try:service.status()
        except sqlite3.Error as e:error=str(e)
        result={'source':'SIMULATED','error':error,'ledger_state':repo.find_feed(request_id=ack.request_id)[1],
            'terminal_records':repo.count('feeding'),'success_events':sum(x.state=='SUCCESS' for x in store.list()),'physical_pass':False}
        repo.close();store.close()
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
