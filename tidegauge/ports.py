from typing import Protocol


class UltrasonicSensorPort(Protocol):
    def read_distance_m(self) -> float:
        """Return measured distance from sensor to water surface in meters."""


class RadioPort(Protocol):
    def send(self, payload: bytes) -> None:
        """Send a binary payload over radio transport."""


class ClockPort(Protocol):
    def now_s(self) -> int:
        """Return current monotonic/runtime seconds."""


class SleepPort(Protocol):
    def sleep_s(self, seconds: int) -> None:
        """Suspend execution for a number of seconds."""
