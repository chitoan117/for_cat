from pathlib import Path
import importlib.util,json,time
spec=importlib.util.spec_from_file_location('migration',Path(__file__).with_name('deploy_firmware.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.service('stop','for-cat-esp32-bridge.service')
try:
    with m.open_serial(m.UART) as s:
        s.write(b'0\njetson_ping\nmode\n')
        end=time.monotonic()+4;data=bytearray()
        while time.monotonic()<end:
            data.extend(s.read(4096))
        (m.R/'probe_uart_raw.bin').write_bytes(data)
        print(json.dumps({'received_bytes':len(data),'complete_lines':data.count(b'\n'),'prefix':data[:240].decode('utf8',errors='replace')}),flush=True)
finally:
    m.queue('0')
    m.service('start','for-cat-esp32-bridge.service')
