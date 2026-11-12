# M3 physical observations — reported evidence, not reconstructed transcripts

Source: user's explicit hardware results supplied during this pass. Machine record: `evidence/M3_REAL_HARDWARE_FACTS.json`. Agent did not access/flash/capture on Jetson. Dates, binary SHA256, full serial hex/CRC numerical values and reconnect raw receipt were not supplied; fields remain null, not calculated and presented as observations. MAC/serial/person identifiers omitted.

| Physical step | Result | Evidence strength |
| --- | --- | --- |
| Nano2GB boot/environment | Reported observed: Ubuntu18.04.6/L4T32.7.6/Python3.6.9; CUDA10.2/cuDNN8.2.1/TRT8.2.1.8/OpenCV4.8.0/cuda count1 | User-reported actual environment; full modern backend not running |
| S3 ROM identity | ESP32-S3 revv0.2,40MHz crystal,16MB flash | User-reported esptool physical verification |
| PSRAM | **NOT DETECTED** | Overrides seller N16R8/8MB advertising; current software uses no PSRAM |
| USB enumeration | PASS,1a86:55d3 USB Single Serial,cdc_acm,/dev/ttyACM0,dialout/pyserial3.5 | User-reported physical detection |
| Flash/reset | PASS,esptool3.3.3 --no-stub, factory0x0,397312B/hash data verified/hard reset | User-reported; original image SHA256 absent |
| PING | PASS,id100→100,ACK,payload01,CRC RX==calculated | Reported properties; raw hex/numerical CRC absent |
| GET_STATUS | PASS,id101→101,SYSTEM_STATUS,payload01,CRC RX==calculated | Reported properties; raw hex/numerical CRC absent |
| Request ID / CRC | PASS for supplied initial probe | Not inferred from host vectors |
| Unplug | PASS,/dev/ttyACM0 disappears | Node disappearance observed; failed-probe/API OFFLINE log not supplied |
| Reconnect enumeration | PASS,/dev/ttyACM0 reappears | User-reported actual node recovery |
| Post-reconnect protocol | **USER-REPORTED PASS** | Operation reported OK; no stored correlated PING/GET_STATUS transcript |
| Webcam720pMJPG | PASS,300 frames,0 failures,10.008s,29.97FPS | User-reported physical OpenCV test;1080p30 only advertised |

M3 is now **physical-core validated with user-reported reconnect**, not “no hardware observed.” Formal dated evidence closeout remains pending the exact post-reconnect probe/CRC/ID and image reference per existing gate. We do not strengthen “operation OK” into invented frames or automatically award full M3. Host baseline remains historically M2; current stage is real M3 closeout / M4 sensor-only preparation. M4 sensors/actuators are NOT TESTED/PENDING.

Next minimal closeout from project `jetson/` with system Python3.6:

```sh
python3 -m bringup.devices
python3 -m bringup.serial_probe --device /dev/ttyACM0 --count 3 --save ../evidence/serial/UNIQUE_connected.json
# Physically unplug; repeat against the old observed node with a different save path: expect FAIL.
# Reconnect, re-enumerate actual node, then repeat with UNIQUE_reconnected.json: require actual matched IDs/CRC.
```

Replace UNIQUE with timestamped names; no overwrites, no FEED_REQUEST. Preserve supplied original observations/receipt separately; new diagnostics have different image hashes/sizes and ASCII mode, so these binary probes must use HW_SAFE_UART image, not a sensor diagnostic image.
