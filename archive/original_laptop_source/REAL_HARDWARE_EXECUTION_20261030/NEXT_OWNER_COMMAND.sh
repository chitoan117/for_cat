# Paste this ONE read-only block into the already authenticated Jetson terminal.
# Source is not proof of the flashed/running image. No Serial or service mutation.
F=/home/toan/for_cat/evidence/full_hardware_integration_20261027_20261027T022005862030Z/stage/firmware/esp32
test -d "$F" || F=/home/toan/for_cat/esp32
printf '\nSOURCE_TREE_ONLY=%s\n' "$F"
grep -nE 'SERVO_SIGNAL|PUMP_CONTROL|DOG_WARNING_BUZZER|HX711_REFERENCE|servo (status|configure|arm YES)|pump (status|arm YES|on MS)|GPIO2 ACTIVE_LOW|default_envs|build_src_filter|PHYSICAL_ENABLE|OFF_LEVEL' "$F/include/current_hardware.h" "$F/platformio.ini" "$F/src/hx711_reference_diag.cpp" "$F/src/servo_bench.cpp" "$F/src/pump_bench.cpp" "$F/src/dog_buzzer_diagnostic.cpp"
printf 'SOURCE_READ_EXIT=%s\n' "$?"
systemctl --user show for-cat-esp32-bridge.service -p ExecStart -p MainPID
printf 'BRIDGE_SHOW_EXIT=%s\n' "$?"
journalctl --user -u for-cat-esp32-bridge.service -b -n 12 --no-pager -o cat
printf 'JOURNAL_EXIT=%s\n' "$?"
