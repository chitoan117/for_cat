# Windows ESP32-S3 detection — seller board NOT VERIFIED

Candidate: 44-pin dual Type-C ESP32-S3-WROOM-1/1U N16R8 board, CH343G bridge and native S3 port. Verify photos/markings/schematic before equating a connector with that description. No seller board was plugged in for this pack.

**Try the identified USB-to-UART / CH343G port first.** It usually offers UART0 ROM download/boot output and is less dependent on the application native-CDC configuration. The other Type-C may route native USB with different bootloader/runtime enumeration. Port labels, USB-C shape, COM number and antenna connector alone do not prove a board model.

With no sensors/servo/pump attached, compare Device Manager → Ports and USB devices **before/after** attaching one connector at a time. Open device Properties → Details → Hardware Ids; save FriendlyName/VID/PID/COM plus photo of the connector used. A bridge may appear as a WCH/USB-SERIAL/CH343 device; names vary. If no port appears, check known-good **data** cable, connector choice, power and drivers. Obtain any required driver only from the chip vendor or approved Windows update source; no automatic/random driver install.

From the project root in PowerShell:

```powershell
& .\.venv\Scripts\python.exe -m serial.tools.list_ports -v
Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match 'CH343|USB.SERIAL|COM[0-9]|Espressif' } | Format-Table Name,DeviceID -AutoSize
```

Record the **actual** COM port. Disconnect, verify disappearance, reconnect and rediscover; never assume COM3/ttyUSB0. Close all monitors before a serial probe. Use the `_hw_safe_uart` profile for the bridge, not the original native-CDC profile. See `ESP32_S3_FIRST_FLASH.md`; native-port bring-up is a separate optional check after bridge success and configuration review.
