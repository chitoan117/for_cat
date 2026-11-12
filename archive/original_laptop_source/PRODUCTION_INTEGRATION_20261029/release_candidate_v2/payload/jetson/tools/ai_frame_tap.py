"""Operator-supervised stdin adapter; no inference/camera/UART or feed TX."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.ai_frame_contract import StateTap,WriterLock,MAX_LINE
def main():
    p=argparse.ArgumentParser();p.add_argument('database');args=p.parse_args()
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    with WriterLock(args.database):
        tap=StateTap(args.database,boot);tap.disconnected()
        try:
            while True:
                line=sys.stdin.buffer.readline(MAX_LINE+1)
                if not line:break
                if not line.endswith(b'\n'):
                    while line and not line.endswith(b'\n'):line=sys.stdin.buffer.readline(MAX_LINE+1)
                    tap.rejected+=1;continue
                try:tap.accept(line.decode('utf-8').rstrip('\r\n'))
                except UnicodeError:tap.rejected+=1
        finally:tap.disconnected()
    print('AI_FRAME_TAP stopped storage_errors='+str(tap.storage_errors)+' rejected='+str(tap.rejected),file=sys.stderr)
if __name__=='__main__':main()
