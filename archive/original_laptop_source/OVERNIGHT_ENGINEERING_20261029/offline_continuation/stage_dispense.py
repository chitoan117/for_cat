import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def main():
    records=json.loads((HERE/'SOURCE_BASELINE.json').read_text())
    for name in ('dispense_bench.h','servo_bench.h'):
        source=ROOT/'HARDWARE_PHYSICAL_BRINGUP_20261029/firmware/include/m4'/name
        rel='firmware/include/m4/'+name;target=HERE/'candidate'/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(source.read_bytes())
        records[rel]={'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    (HERE/'SOURCE_BASELINE.json').write_text(json.dumps(records,indent=2)+'\n')
if __name__=='__main__':main()
