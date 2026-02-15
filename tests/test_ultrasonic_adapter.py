from tidegauge.adapters.ultrasonic import UltrasonicDurationAdapter
from tidegauge.ultrasonic import echo_duration_us_to_distance_m


class FakeEchoDurationReader:
    def __init__(self, durations_us: list[int]) -> None:
        self._durations_us = durations_us

    def read_echo_duration_us(self) -> int:
        if not self._durations_us:
            raise RuntimeError("No echo durations remaining")
        return self._durations_us.pop(0)


def test_ultrasonic_duration_adapter_converts_echo_duration_to_distance() -> None:
    reader = FakeEchoDurationReader(durations_us=[5831])
    adapter = UltrasonicDurationAdapter(echo_reader=reader)

    distance_m = adapter.read_distance_m()

    assert distance_m == echo_duration_us_to_distance_m(5831)


def test_ultrasonic_duration_adapter_supports_multiple_reads() -> None:
    reader = FakeEchoDurationReader(durations_us=[5831, 2915])
    adapter = UltrasonicDurationAdapter(echo_reader=reader)

    first = adapter.read_distance_m()
    second = adapter.read_distance_m()

    assert first > second
