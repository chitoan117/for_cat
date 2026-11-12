"""Local static release viewer only; no backend/sensor/actuation endpoints."""
import argparse,json
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('real','mock'),required=True)
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args();root=Path(__file__).resolve().parent/('web_'+args.mode)
    marker=json.loads((root/'forcat_build.json').read_text(encoding='utf-8'))
    if marker['mode']!=args.mode.upper():raise SystemExit('Wrong compiled artifact mode')
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):super().__init__(*a,directory=str(root),**kw)
        def do_GET(self):
            parsed=urlsplit(self.path)
            if parsed.path in ('/app','/kiosk','/'):
                self.path='/index.html'
            elif parsed.path.startswith('/flutter/'):
                self.path=parsed.path[len('/flutter'):]
            else:
                self.send_error(404,'Static offline demo: backend unavailable');return
            super().do_GET()
        def end_headers(self):
            self.send_header('Cache-Control','no-store');super().end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'OFFLINE STATIC {args.mode.upper()} at http://127.0.0.1:{server.server_address[1]}/app - no backend/hardware',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
