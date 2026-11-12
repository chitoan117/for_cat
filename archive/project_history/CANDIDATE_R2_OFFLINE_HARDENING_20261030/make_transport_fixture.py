import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    base=json.loads((ROOT/'fixtures/synthetic_wire.json').read_text())['report']
    def wire(up=70000):
        x=json.loads(json.dumps(base));x['monotonic_ms']=up
        for s in x['ultrasonic'].values():s.update(last_update=up,sample_age_ms=0,last_valid_update=up)
        x['weight']['sampled_at_ms']=up
        x['current_hardware'].update(pir_last_transition_ms=up-100,button_last_press_ms=up-40)
        return json.dumps(x,separators=(',',':'))+'\n'
    steps=[]
    def add(case,op,ms,data=None):
        v=dict(case=case,op=op,host_ms=ms)
        if data is not None:v['data']=data
        steps.append(v)
    add('restart_history_not_live','RESTORE_HISTORY',100000,wire().strip())
    add('connecting','CONNECT',100000)
    frame=wire();add('partial','RX',100001,frame[:100]);add('healthy_cat','RX',100002,frame[100:])
    add('duplicate_frozen','RX',103500,frame)
    add('progress_dog','RX',103600,wire(70001))
    add('out_of_order','RX',103700,wire(70000))
    add('recovered_none','RX',103800,wire(70002))
    add('host_clock_backwards','RX',103750,wire(70003))
    add('host_recovered','RX',104000,wire(70004))
    add('truncated_json','RX',104100,wire(70005)[:-10]+'\n')
    add('disconnect','DISCONNECT',104200)
    add('reconnect_waiting','CONNECT',104300)
    add('reconnect_fresh','RX',104400,wire(70006))
    add('partial_timeout','RX',104500,wire(70007)[:50]);add('timeout','TICK',108000)
    add('clear_partial','DISCONNECT',108100);add('reconnect2','CONNECT',108200)
    add('ai_unknown','RX',108300,wire(70008))
    add('wrong_host_boot','RX',108400,wire(70009))
    x=json.loads(wire(70010));x['current_hardware']['pump_armed']=True
    add('unsafe','RX',108500,json.dumps(x,separators=(',',':'))+'\n')
    add('unsafe_after_good','RX',108600,wire(70011))
    add('unsafe_after_reconnect','CONNECT',108700);add('unsafe_still_latched','RX',108800,wire(70012))
    (ROOT/'fixtures/transport_script.json').write_text(json.dumps({'source':'SIMULATED','physical_pass':False,'steps':steps},indent=2)+'\n')
    print('SIMULATED scripted transport steps='+str(len(steps)))
if __name__=='__main__':main()
