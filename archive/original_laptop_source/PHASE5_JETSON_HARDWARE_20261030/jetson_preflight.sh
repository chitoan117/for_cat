#!/bin/sh
# Read-only host/service/USB/log/file audit. Never opens a tty or camera.
export LC_ALL=C
run() {
    printf '\nUTC=%s\n' "$(date -u +%FT%TZ)"
    printf 'COMMAND'; printf ' %s' "$@"; printf '\n'
    "$@"
    rc=$?
    printf '\nEXIT_CODE=%s\n' "$rc"
}
run date -u +%FT%TZ
run hostname
run id
run uname -a
run cat /etc/os-release
run cat /proc/sys/kernel/random/boot_id
run uptime
run g++ --version
run gcc --version
run python3 --version
run pkg-config --modversion json-c sqlite3
run free -m
run swapon --show
run df -h /home/toan/for_cat /tmp
run systemctl --user show for-cat-ai.service for-cat-api.service for-cat-esp32-bridge.service -p Id -p MainPID -p ActiveState -p SubState -p FragmentPath -p ExecMainStartTimestamp -p ExecMainStatus
for unit in for-cat-ai.service for-cat-api.service for-cat-esp32-bridge.service; do
    run systemctl --user is-active "$unit"
    pid=$(systemctl --user show "$unit" -p MainPID --value)
    case "$pid" in ''|0|*[!0-9]*) ;; *)
        run ps -p "$pid" -o user,pid,ppid,comm,pcpu,pmem,etime
        run readlink "/proc/$pid/exe"
        ;;
    esac
done
run lsusb
run ls -l /dev/serial/by-id
run readlink -f /dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00
run udevadm info --query=property --name=/dev/ttyACM0
run fuser -v /dev/ttyACM0
run ss -ltn
run journalctl --user -u for-cat-esp32-bridge.service -n 60 --no-pager -o short-iso
run journalctl --user -u for-cat-ai.service -n 25 --no-pager -o short-iso
run journalctl --user -u for-cat-api.service -n 25 --no-pager -o short-iso
run cat /home/toan/for_cat/hardware_diag_candidate_20261029/web_hardware/native_arm64_gcc75_r1_20261029_171958/result.json
run stat -c '%n %s bytes' /home/toan/for_cat/hardware_diag_candidate_20261029/artifacts/diag_four_ultrasonic/firmware.bin
run sha256sum /home/toan/for_cat/hardware_diag_candidate_20261029/artifacts/diag_four_ultrasonic/firmware.bin
exit 0
