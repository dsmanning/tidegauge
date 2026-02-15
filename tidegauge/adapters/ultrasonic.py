try:
    from typing import Protocol
except ImportError:  # pragma: no cover - CircuitPython compatibility
    Protocol = object

from tidegauge.ultrasonic import echo_duration_us_to_distance_m


class EchoDurationReader(Protocol):
    def read_echo_duration_us(self) -> int:
        """Read HC-SR04 echo pulse duration in microseconds."""


class UltrasonicDurationAdapter:
    def __init__(self, *, echo_reader: EchoDurationReader) -> None:
        self._echo_reader = echo_reader

    def read_distance_m(self) -> float:
        echo_duration_us = self._echo_reader.read_echo_duration_us()
        return echo_duration_us_to_distance_m(echo_duration_us)
