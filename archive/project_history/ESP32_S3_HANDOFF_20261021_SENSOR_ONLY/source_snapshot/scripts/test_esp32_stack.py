"""Bidirectional process E2E: real firmware parsers and real Jetson stack, no board."""
import argparse
import itertools
import json
from pathlib import Path
import random
import struct
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "jetson")]
from app.serial_link.protocol import Command, Frame, FrameStreamDecoder, ProtocolError, crc16, decode, encode
from app.serial_link.real_transport import RealEsp32SerialTransport
from app.serial_link.link_manager import LinkManager
from app.status import LinkState
from bringup.sensor_monitor import parse_report
from scripts.esp32_virtual_transport import FirmwareDevice, ProcessSerialPort, factory

OPTIONS = None


def repair_crc(raw):
    return bytes(raw[:-2]) + struct.pack("<H", crc16(bytes(raw[2:-2])))


class StackE2E(unittest.TestCase):
    def setUp(self):
        self.folder = Path(OPTIONS.output) / self._testMethodName
        self.folder.mkdir()
        self.devices = []
        self.dev = self.device(OPTIONS.protocol, "protocol")

    def tearDown(self):
        for dev in self.devices:
            try:
                if dev.proc.poll() is None:
                    stats = dev.stats()
                    self.assertEqual(stats["actuator_gpio_touches"], 0)
                    self.assertFalse(stats["servo_enabled"] or stats["pump_enabled"])
                    (self.folder / (str(self.devices.index(dev)) + ".bounds.json")).write_text(json.dumps(stats), encoding="utf-8")
            finally:
                dev.close()

    def device(self, binary, name):
        dev = FirmwareDevice(binary, self.folder / (name + ".nvs"))
        self.devices.append(dev)
        return dev

    def link(self, dev=None, **fault):
        transport = RealEsp32SerialTransport("VIRTUAL_PROCESS_ONLY", timeout=0.04, startup_delay=0,
                                            serial_factory=factory(dev or self.dev, **fault))
        self.addCleanup(transport.close)
        return LinkManager(transport)

    def raw(self, data, settle=0):
        output = self.dev.feed(data)
        if settle:
            output += self.dev.tick(settle)
        return FrameStreamDecoder().feed(output, 0)

    def ascii(self, dev, text="status", advance=2):
        data = dev.feed((text + "\n").encode("ascii"), advance)
        return [parse_report(line) for line in data.splitlines() if line.startswith(b"{")]

    def weight(self, dev, value):
        dev.fault("hx", value)
        dev.tick(2)

    def calibrate(self, dev, tare=100, loaded=1100):
        self.ascii(dev, "tare 2")
        self.weight(dev, tare)
        self.weight(dev, tare)
        self.ascii(dev, "cal 50 2")
        self.weight(dev, loaded)
        self.weight(dev, loaded)
        self.weight(dev, (tare + loaded) // 2)
        self.assertAlmostEqual(self.ascii(dev)[-1]["grams"], 25)

    def test_command_matrix_safe_mode(self):
        link = self.link()
        self.assertEqual(link.state, LinkState.UNCONFIGURED)
        self.assertEqual(link.exchange(1, Command.PING), Frame(1, Command.ACK, b"\x01"))
        self.assertEqual(link.exchange(2, Command.GET_STATUS), Frame(2, Command.SYSTEM_STATUS, b"\x01"))
        self.assertEqual(link.exchange(3, Command.FEED_REQUEST).payload, b"\x03")
        self.assertEqual(link.exchange(3, Command.FEED_STATUS).payload, b"\x02")
        self.assertEqual(link.state, LinkState.ONLINE)
        self.assertEqual(self.dev.stats()["nvs_writes"], 0)

    def test_duplicate_replay_and_full_cache(self):
        link = self.link()
        for identifier in range(1, 17):
            self.assertEqual(link.exchange(identifier, Command.FEED_REQUEST).command, Command.ACK)
        self.assertEqual(link.exchange(17, Command.FEED_REQUEST), Frame(17, Command.NACK, b"\x04"))
        self.assertEqual(link.exchange(1, Command.FEED_REQUEST).command, Command.ACK)
        self.assertEqual(link.exchange(1, Command.FEED_STATUS).payload, b"\x02")
        self.assertEqual(self.dev.stats()["nvs_writes"], 0)

    def test_invalid_commands_payload_limits_and_ids(self):
        for command, payload, reason in ((255, b"", 3), (1, b"x", 6), (2, bytes(256), 6), (5, b"", 3), (6, b"", 3), (7, b"", 3)):
            reply = self.raw(encode(Frame(80, command, payload)))
            self.assertEqual(reply[-1], Frame(80, Command.NACK, bytes([reason])))
        self.assertEqual(self.raw(encode(Frame(0, Command.FEED_REQUEST)))[-1].payload, b"\x06")
        huge = bytearray(encode(Frame(81, Command.PING)))
        huge[8:10] = struct.pack("<H", 257)
        self.assertEqual(self.raw(bytes(huge))[-1], Frame(81, Command.NACK, b"\x01"))

    def test_malformed_frames_recover_after_partial_deadline(self):
        valid = encode(Frame(51, Command.PING))
        crc = bytearray(valid); crc[-1] ^= 1
        version = bytearray(valid); version[2] = 2
        for bad in (b"\x00\x5a" + valid[2:], bytes(crc), bytes(version), valid[:6], valid[:8] + b"\xff\xff", valid[1:], valid[:5] + valid[4:]):
            self.dev.feed(bad)
            self.dev.tick(251)
            result = self.raw(encode(Frame(52, Command.PING)))
            self.assertEqual(result[-1], Frame(52, Command.ACK, b"\x01"))

    def test_back_to_back_random_chunks_and_reordered_ids(self):
        data = b"".join(encode(Frame(n, Command.PING)) for n in (7, 3, 8, 2))
        randomizer = random.Random(20261018)
        response = b""
        while data:
            count = randomizer.randint(1, 9)
            response += self.dev.feed(data[:count])
            data = data[count:]
        frames = FrameStreamDecoder().feed(response, 0)
        self.assertEqual([frame.request_id for frame in frames], [7, 3, 8, 2])
        for chunk in (1, 2, 7, 64):
            self.assertEqual(self.link(chunk=chunk).exchange(99, Command.PING).payload, b"\x01")

    def test_partial_frame_timeout_across_u32_clock_wrap(self):
        raw = encode(Frame(60, Command.PING))
        self.dev.rpc(5, struct.pack("<I", 0xfffffff0))
        self.dev.feed(raw[:6])
        self.dev.rpc(5, struct.pack("<I", 16))
        self.assertEqual(self.raw(raw[6:])[-1], Frame(60, Command.ACK, b"\x01"))

    def test_wire_faults_have_declared_nack_timeout_and_recovery(self):
        for transform in (lambda b: b[:-1], lambda b: b[1:], lambda b: b[:5] + b[4:], lambda b: b[:10] + bytes([b[10] ^ 8]) + b[11:]):
            link = self.link(tx=transform)
            try:
                reply = link.exchange(111, Command.PING)
                self.assertEqual(reply.command, Command.NACK)
            except TimeoutError:
                self.assertEqual(link.state, LinkState.OFFLINE)
            self.dev.tick(251)
            self.assertEqual(self.link().exchange(112, Command.PING).command, Command.ACK)

    def test_response_crc_degrades_then_recovers(self):
        def corrupt(raw):
            return raw[:-1] + bytes([raw[-1] ^ 1])
        link = self.link(rx=corrupt)
        with self.assertRaises(ProtocolError):
            link.exchange(1, Command.PING)
        self.assertEqual(link.state, LinkState.DEGRADED)
        link.transport._factory = factory(self.dev)
        self.assertEqual(link.exchange(2, Command.PING).command, Command.ACK)
        self.assertEqual(link.state, LinkState.ONLINE)

    def test_unexpected_ack_nack_and_status_rejected(self):
        invalid = ((Command.GET_STATUS, Command.ACK, b"\x02"), (Command.PING, Command.ACK, b"\x03"),
                   (Command.PING, Command.NACK, b"\x00"), (Command.GET_STATUS, Command.SYSTEM_STATUS, b"\x00"),
                   (Command.FEED_STATUS, Command.FEED_STATUS, b"\xff"))
        for request, kind, payload in invalid:
            link = self.link(rx=lambda raw, k=kind, p=payload: encode(Frame(decode(raw).request_id, k, p)))
            with self.assertRaises(ProtocolError):
                link.exchange(9, request)
            self.assertEqual(link.state, LinkState.DEGRADED)
            link.transport._port.rx = lambda raw: raw
            self.assertEqual(link.exchange(10, Command.PING).command, Command.ACK)
            self.assertEqual(link.state, LinkState.ONLINE)

    def test_serial_silence_disconnect_and_late_reply(self):
        for fault in ({"silence": True}, {"disconnect": True}, {"delay": 0.08}):
            link = self.link(**fault)
            with self.assertRaises((TimeoutError, ConnectionError)):
                link.exchange(21, Command.PING)
            self.assertEqual(link.state, LinkState.OFFLINE)
        time.sleep(0.09)
        self.assertEqual(self.link().exchange(22, Command.GET_STATUS), Frame(22, Command.SYSTEM_STATUS, b"\x01"))

    def test_reboot_during_partial_frame_and_request(self):
        self.dev.feed(encode(Frame(4, Command.GET_STATUS))[:7])
        self.dev.restart()
        link = self.link()
        self.assertEqual(link.exchange(5, Command.PING).command, Command.ACK)
        self.assertEqual(link.exchange(6, Command.FEED_REQUEST).command, Command.ACK)
        self.dev.close()
        with self.assertRaises(ConnectionError):
            link.exchange(7, Command.GET_STATUS)
        self.assertEqual(link.state, LinkState.OFFLINE)
        self.dev.start()
        self.assertEqual(link.exchange(6, Command.FEED_STATUS), Frame(6, Command.NACK, b"\x05"))
        self.assertEqual(link.state, LinkState.ONLINE)

    def test_jetson_restart_retains_only_safe_device_results(self):
        first = self.link(); first.exchange(12, Command.FEED_REQUEST); first.transport.close()
        second = self.link()
        self.assertEqual(second.exchange(12, Command.FEED_REQUEST).command, Command.ACK)
        self.assertEqual(second.exchange(12, Command.FEED_STATUS).payload, b"\x02")
        self.assertEqual(self.dev.stats()["nvs_writes"], 0)

    def test_wrong_firmware_mode_times_out_without_poisoning(self):
        ascii_device = self.device(OPTIONS.ascii, "wrongmode")
        link = self.link(ascii_device)
        with self.assertRaises(TimeoutError):
            link.exchange(1, Command.PING)
        self.assertEqual(link.state, LinkState.OFFLINE)
        self.assertEqual(self.link().exchange(2, Command.PING).command, Command.ACK)

    def test_api_eventstore_blocks_physical_feed_path(self):
        from fastapi.testclient import TestClient
        from app.config import HardwareConfig
        from app.main import create_app
        transport = self.link().transport
        app = create_app(db_path=self.folder / "api.sqlite", transport=transport,
                         hardware=HardwareConfig(esp32_transport="SERIAL", esp32_serial_device="VIRTUAL_ONLY"))
        with TestClient(app) as client:
            self.assertTrue(client.get("/api/v1/status").json()["esp32_online"])
            result = client.post("/api/v1/feed/manual").json()
            self.assertEqual(result["state"], "REJECTED")
            self.assertFalse(app.state.pipeline.status()["automatic_feed_authorized"])
            self.assertEqual(self.dev.stats()["nvs_writes"], 0)
            self.assertEqual(self.link().exchange(result["request_id"], Command.FEED_STATUS).payload, b"\x05")

    def test_bounds_and_bad_backend_read(self):
        with self.assertRaises(ValueError):
            self.dev.rpc(1, bytes(8193))
        stream = b"".join(encode(Frame(i, Command.PING)) for i in range(150))
        self.assertEqual(len(self.raw(stream)), 150)
        class BadPort(ProcessSerialPort):
            def read(self, count):
                return bytes(count + 1)
        transport = RealEsp32SerialTransport("VIRTUAL_ONLY", startup_delay=0, timeout=0.02,
                                            serial_factory=lambda **kw: BadPort(self.dev, **kw))
        self.addCleanup(transport.close)
        with self.assertRaises(ProtocolError):
            transport.exchange(encode(Frame(8, Command.PING)))

    def test_python_stream_fuzz_seeded_bounded_resynchronization(self):
        parser = FrameStreamDecoder(); rng = random.Random(20261018)
        for i in range(1000):
            bad = bytearray(encode(Frame(i, Command.PING))); bad[-1] ^= 1
            parser.feed(rng.randbytes(rng.randrange(30)) + bad, i)
            frames = parser.feed(encode(Frame(100000 + i, Command.PING)), i + 0.5)
            self.assertTrue(any(frame.request_id == 100000 + i for frame in frames))
            self.assertLessEqual(len(parser.buffer), 512)

    def test_connecting_pending_bounds_and_version_mismatch(self):
        observed = []
        transport = RealEsp32SerialTransport("VIRTUAL_ONLY", startup_delay=0, timeout=0.04,
                    serial_factory=lambda **kw: (observed.append(link.state) or ProcessSerialPort(self.dev, **kw)))
        self.addCleanup(transport.close)
        link = LinkManager(transport, max_pending=2)
        link.exchange(1, Command.PING)
        self.assertEqual(observed, [LinkState.CONNECTING])
        link.mark_pending(1); link.mark_pending(2)
        with self.assertRaises(OverflowError): link.mark_pending(3)
        bad = self.link(tx=lambda raw: raw[:2] + b"\x02" + raw[3:])
        self.assertEqual(bad.exchange(8, Command.PING).payload, b"\x02")
        self.assertEqual(bad.state, LinkState.DEGRADED)
        with self.assertRaises(ProtocolError):
            FrameStreamDecoder().feed(bytes(8193), 0)

    def test_concurrent_requests_remain_serialized_and_bounded(self):
        from concurrent.futures import ThreadPoolExecutor
        link = self.link()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda i: link.exchange(i, Command.PING).request_id, range(1000, 1032)))
        self.assertEqual(sorted(results), list(range(1000, 1032)))
        self.assertEqual(link.stats()["received"], 32)

    def test_future_installed_zero_is_valid_not_absence(self):
        dev = self.device(OPTIONS.ascii, "futurezero")
        self.calibrate(dev); self.weight(dev, 100)
        row = self.ascii(dev)[-1]
        self.assertEqual(row["grams"], 0)
        self.assertTrue(row["weight"]["valid"])
        self.assertEqual(row["weight"]["quality"], "VALID")
        self.assertIsNone(row["consumed_grams"])

    def test_absent_loadcell_no_gpio_no_fake_zero(self):
        dev = self.device(OPTIONS.absent, "absent")
        self.weight(dev, 0)
        row = self.ascii(dev)[-1]
        self.assertFalse(row["hx711_installed"])
        self.assertEqual(row["weight"]["quality"], "NOT_INSTALLED")
        self.assertIsNone(row["grams"])
        self.assertIsNone(row["consumed_grams"])
        self.assertEqual(dev.stats()["hx_gpio_touches"], 0)

    def test_sensor_failure_matrix_and_recovery(self):
        dev = self.device(OPTIONS.ascii, "sensors")
        self.calibrate(dev)
        for value in (-8388608, 8388607):
            self.weight(dev, value)
            self.assertIsNone(self.ascii(dev)[-1]["grams"])
        dev.tick(600); self.assertEqual(self.ascii(dev)[-1]["weight_health"], "NOT_CONNECTED")
        for name, role in (("food", "approach"), ("water", "water")):
            self.ascii(dev, "echo-" + role + "-3v3 CONFIRM")
            dev.fault(name + "_missing", 1); dev.tick(800)
            self.assertEqual(self.ascii(dev)[-1][role + "_health"], "NOT_CONNECTED")
            dev.fault(name + "_missing", 0); dev.fault(name + "_stuck", 1); dev.tick(800)
            self.assertEqual(self.ascii(dev)[-1][role + "_health"], "FAULT")
            dev.fault(name + "_stuck", 0)
        dev.fault("rtc_missing", 1); dev.tick(1100); self.assertIsNone(self.ascii(dev)[-1]["rtc_epoch"])
        dev.fault("rtc_missing", 0); dev.fault("rtc_invalid", 1); dev.tick(1100)
        self.assertIsNone(self.ascii(dev)[-1]["rtc_epoch"])
        dev.fault("oled", 0); dev.tick(1200); self.assertEqual(self.ascii(dev)[-1]["oled_health"], "FAULT")
        dev.fault("button", 1); dev.tick(1600); dev.fault("button", 0); dev.tick(100)
        for _ in range(3):
            dev.fault("button", 1); dev.tick(5); dev.fault("button", 0); dev.tick(5)
        self.assertEqual(dev.stats()["actuator_gpio_touches"], 0)

    def test_calibration_water_geometry_and_legacy_rejection_orderings_save_restart(self):
        for index, order in enumerate(itertools.permutations(("cal", "food", "water"))):
            dev = self.device(OPTIONS.ascii, "order" + str(index))
            for action in order:
                if action == "cal": self.calibrate(dev)
                else:
                    self.ascii(dev, action + "-geometry 5 50")
                    if action == "food":
                        row = self.ascii(dev)[-1]
                        self.assertIsNone(row["food_percent"])
                        self.assertEqual(row["food_health"], "NOT_CONFIGURED")
            self.weight(dev, 600); self.assertEqual(self.ascii(dev)[-1]["grams"], 25)
            self.ascii(dev, "save YES"); dev.restart(); self.weight(dev, 600)
            self.assertEqual(self.ascii(dev)[-1]["grams"], 25)
            self.ascii(dev, "load"); self.weight(dev, 600)
            self.assertEqual(self.ascii(dev)[-1]["grams"], 25)

    def test_unsaved_defaults_repeated_tare_and_calibration(self):
        dev = self.device(OPTIONS.ascii, "unsaved")
        self.calibrate(dev); dev.restart(); self.weight(dev, 600)
        self.assertIsNone(self.ascii(dev)[-1]["grams"])
        self.calibrate(dev)
        self.ascii(dev, "tare 2"); self.weight(dev, 200); self.weight(dev, 200)
        self.ascii(dev, "water-geometry 6 50"); self.weight(dev, 600)
        self.assertIsNone(self.ascii(dev)[-1]["grams"])
        self.ascii(dev, "cal 50 2"); self.weight(dev, 1200); self.weight(dev, 1200); self.weight(dev, 700)
        self.assertEqual(self.ascii(dev)[-1]["grams"], 25)

    def test_nvs_failure_corruption_and_old_schema_are_whole_record(self):
        for fault in ("nvs_write", "nvs_short", "nvs_corrupt", "nvs_old", "nvs_read"):
            dev = self.device(OPTIONS.ascii, fault)
            # Keep an actual configured geometry after tare invalidates the scale
            # factor, so the short-write fault reaches NVS rather than save gating.
            self.calibrate(dev); self.ascii(dev, "water-geometry 5 50"); self.ascii(dev, "save YES")
            if fault in ("nvs_write", "nvs_short"):
                dev.fault(fault, 1); self.ascii(dev, "tare 1"); self.weight(dev, 500); self.ascii(dev, "save YES")
            else:
                dev.fault(fault, 1)
            if fault == "nvs_read":
                self.ascii(dev, "load"); self.weight(dev, 600); self.assertIsNone(self.ascii(dev)[-1]["grams"])
            dev.restart(); self.weight(dev, 600)
            actual = self.ascii(dev)[-1]["grams"]
            self.assertEqual(actual, 25 if fault in ("nvs_write", "nvs_read") else None)

    def test_reset_during_nvs_commit_before_after_and_torn(self):
        for stage in (1, 2, 3):
            dev = self.device(OPTIONS.ascii, "crash" + str(stage))
            self.calibrate(dev); self.ascii(dev, "save YES")
            self.calibrate(dev, tare=200, loaded=2200)
            dev.fault("nvs_crash", stage)
            with self.assertRaises(ConnectionError): self.ascii(dev, "save YES")
            dev.restart(); self.weight(dev, 1100)
            self.assertEqual(self.ascii(dev)[-1]["grams"], 22.5 if stage == 2 else 50)

    def test_reset_during_calibration_config_sensor_and_publication(self):
        dev = self.device(OPTIONS.ascii, "resetstates")
        self.ascii(dev, "tare 2"); self.weight(dev, 100); dev.restart()
        self.weight(dev, 100); self.assertIsNone(self.ascii(dev)[-1]["grams"])
        self.ascii(dev, "food-geometry 5 50"); dev.restart()
        self.assertIsNone(self.ascii(dev)[-1]["food_percent"])
        self.ascii(dev, "echo-approach-3v3 CONFIRM"); dev.tick(500); dev.restart()
        row = self.ascii(dev)[-1]; self.assertFalse(row["approach_echo_ack"])
        transcript = dev.feed(b"status\n"); self.assertTrue(transcript.startswith(b"{"))
        dev.restart(); self.assertIsNone(self.ascii(dev)[-1]["grams"])


def main():
    global OPTIONS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True); parser.add_argument("--ascii", required=True)
    parser.add_argument("--absent", required=True); parser.add_argument("--output", required=True)
    OPTIONS = parser.parse_args()
    Path(OPTIONS.output).mkdir()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StackE2E)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {"scope": "SOFTWARE_ONLY_PROCESS_E2E", "named_cases": result.testsRun,
               "failures": len(result.failures), "errors": len(result.errors),
               "python_parser_fuzz_iterations": 1000, "python_parser_fuzz_seed": 20261018,
                "physical_validation": "NOT_TESTED", "load_cell": "EXPLICIT_INSTALLED_AND_ABSENT_SOFTWARE_FIXTURES",
               "result": "PASS" if result.wasSuccessful() else "FAIL"}
    (Path(OPTIONS.output) / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
