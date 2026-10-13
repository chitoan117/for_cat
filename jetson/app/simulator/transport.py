"""Inert serial protocol digital twin; deliberate terminal results only."""

from app.serial_link.protocol import Command, FeedCode, Frame, decode, encode
from app.simulator.controller import (FeedSensors, FeedState, SimulatedFeedController,
                                      SimulatedWaterController)


class SimulatedEsp32Transport:
    def __init__(self, sensors: FeedSensors | None = None, target_grams: float = 10):
        self.sensors = sensors or FeedSensors(monotonic_seconds=0, epoch_seconds=100000,
                                               date_key=20260930, rtc_valid=True,
                                               food_available=True, scale_valid=True,
                                               servo_valid=True)
        self.target_grams = target_grams
        self.feed = SimulatedFeedController()
        self.feed.tick(self.sensors)
        self.water = SimulatedWaterController()
        self.online = True
        self.results: dict[int, FeedCode] = {}
        self.reasons: dict[int, str | None] = {}
        self.received_feed_commands = 0

    def advance(self, *, seconds: float, weight_grams: float | None = None,
                servo_closed: bool | None = None) -> None:
        self.sensors.monotonic_seconds += seconds
        self.sensors.epoch_seconds += int(seconds)
        if weight_grams is not None:
            self.sensors.weight_grams = weight_grams
        if servo_closed is not None:
            self.sensors.servo_closed = servo_closed
        self.feed.tick(self.sensors)
        if self.feed.id is not None:
            code = {FeedState.COMPLETE: FeedCode.SUCCESS, FeedState.REJECTED: FeedCode.REJECTED,
                    FeedState.FAULT: FeedCode.ERROR}.get(self.feed.state, FeedCode.PENDING)
            self.results[self.feed.id] = code
            self.reasons[self.feed.id] = self.feed.reason

    def exchange(self, request: bytes) -> bytes:
        if not self.online:
            raise ConnectionError("SIMULATED serial disconnect")
        frame = decode(request)
        if frame.payload:
            response = Frame(frame.request_id, Command.NACK, b"\x06")
        elif frame.command == Command.PING:
            response = Frame(frame.request_id, Command.ACK, bytes([Command.PING]))
        elif frame.command == Command.GET_STATUS:
            response = Frame(frame.request_id, Command.SYSTEM_STATUS, b"\x01")
        elif frame.command == Command.FEED_REQUEST:
            if frame.request_id in self.results:
                response = Frame(frame.request_id, Command.ACK, bytes([Command.FEED_REQUEST]))
            elif len(self.results) >= 10000:
                response = Frame(frame.request_id, Command.NACK, b"\x04")
            elif not self.feed.request(frame.request_id, self.target_grams, self.sensors):
                response = Frame(frame.request_id, Command.NACK, b"\x04")
            else:
                self.received_feed_commands += 1
                self.results[frame.request_id] = (
                    FeedCode.REJECTED if self.feed.state == FeedState.REJECTED else FeedCode.PENDING
                )
                self.reasons[frame.request_id] = self.feed.reason
                response = Frame(frame.request_id, Command.ACK, bytes([Command.FEED_REQUEST]))
        elif frame.command == Command.FEED_STATUS:
            response = (Frame(frame.request_id, Command.FEED_STATUS, bytes([self.results[frame.request_id]]))
                        if frame.request_id in self.results else
                        Frame(frame.request_id, Command.NACK, b"\x05"))
        else:
            response = Frame(frame.request_id, Command.NACK, b"\x03")
        return encode(response)
