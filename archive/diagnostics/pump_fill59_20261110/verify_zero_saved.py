from pathlib import Path
import sqlite3,json
r=Path('/home/toan/for_cat/evidence/pump_fill59_20261110')
with sqlite3.connect('/home/toan/for_cat/jetson/data/events.db') as db:
    row=db.execute("SELECT seq,body FROM esp32_events WHERE kind='hx_cal' ORDER BY seq DESC LIMIT 1").fetchone()
assert row,'No calibration acknowledgement'
ack=json.loads(row[1])
assert ack['operation']=='rezero' and ack['ok'] and ack['saved'],ack
assert abs(ack['tare_counts']-(-699593))<.001,ack
p=r/'owner_rezero_1794244611.json'
j=json.loads(p.read_text());j['save_ack']=True;j['save_ack_event_seq']=row[0];j['save_ack_body']=ack
p.write_text(json.dumps(j,indent=2))
print(json.dumps({'saved_nvs':True,'event_seq':row[0],'ack':ack}),flush=True)
