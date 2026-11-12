const http = require('node:http');
const net = require('node:net');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, 'web_real');
const backend = { hostname: '192.168.1.6', port: 8000 };
const types = {'.html':'text/html; charset=utf-8','.js':'application/javascript','.json':'application/json','.wasm':'application/wasm','.ttf':'font/ttf','.otf':'font/otf','.png':'image/png','.svg':'image/svg+xml'};
let blockedWrites = 0;
const server = http.createServer((req,res) => {
  if (!['GET','HEAD'].includes(req.method)) {
    blockedWrites++; console.log('BLOCKED_WRITE',req.method,req.url);
    res.writeHead(405);res.end('Read-only UI preview');return;
  }
  if (req.url.startsWith('/api/')) {
    const p=http.request({...backend,path:req.url,method:req.method,headers:{...req.headers,host:'192.168.1.6:8000'}},up=>{
      res.writeHead(up.statusCode,{...up.headers,'cache-control':'no-store'});up.pipe(res);
    });
    p.on('error',()=>{if(!res.headersSent)res.writeHead(502);res.end('Backend unavailable');});p.end();return;
  }
  const url = new URL(req.url,'http://127.0.0.1:8766');
  if(url.pathname==='/'){res.writeHead(302,{location:'/app'});res.end();return;}
  const relative = ['/app','/app/'].includes(url.pathname)?'index.html':decodeURIComponent(url.pathname).replace(/^\/flutter\//,'');
  const file = path.resolve(root,relative);
  if (!file.startsWith(root+path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {res.writeHead(404);res.end();return;}
  res.writeHead(200,{'content-type':types[path.extname(file)]||'application/octet-stream','cache-control':'no-store'});
  if(req.method==='HEAD')res.end();else fs.createReadStream(file).pipe(res);
});
server.on('upgrade',(req,socket,head)=>{
  if(req.url!=='/api/ws/state'){socket.end('HTTP/1.1 403 Forbidden\r\n\r\n');return;}
  const upstream=net.connect(8000,'192.168.1.6',()=>{
    const headers={...req.headers,host:'192.168.1.6:8000'};
    upstream.write(`GET ${req.url} HTTP/1.1\r\n`+Object.entries(headers).map(([k,v])=>`${k}: ${v}\r\n`).join('')+'\r\n');
    if(head.length)upstream.write(head);socket.pipe(upstream);upstream.pipe(socket);
  });
  upstream.on('error',()=>socket.destroy());socket.on('error',()=>upstream.destroy());socket.on('close',()=>upstream.destroy());
});
server.listen(8766,'127.0.0.1',()=>console.log('Read-only UI preview http://127.0.0.1:8766/app; actuator/schedule writes blocked'));
process.on('SIGINT',()=>{console.log('Preview closed; blocked write requests:',blockedWrites);server.close(()=>process.exit(0));setTimeout(()=>process.exit(0),1000);});
