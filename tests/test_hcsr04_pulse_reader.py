import pytest

from tidegauge.adapters.hcsr04 import Hcsr04PulseReader, UltrasonicTimeoutError


class FakeTimeModule:
    def __init__(self, *, tick_step_us: int = 100) -> None:
        self._now_us = 0
        self._tick_step_us = tick_step_us
        self.sleep_calls_us: list[int] = []

    def sleep_us(self, delay_us: int) -> None:
        self.sleep_calls_us.append(delay_us)
        self._now_us += delay_us

    def ticks_us(self) -> int:
        self._now_us += self._tick_step_us
        return self._now_us

    def ticks_diff(self, current: int, start: int) -> int:
        return current - start


class FakeTriggerPin:
    def __init__(self) -> None:
        self.writes: list[int] = []

    def value(self, new_value: int | None = None) -> int:
        if new_value is None:
            return self.writes[-1] if self.writes else 0
        self.writes.append(new_value)
        return new_value


class FakeEchoPin:
    def __init__(self, sequence: list[int], default: int = 0) -> None:
        self._sequence = sequence
        self._default = default

    def value(self) -> int:
        if self._sequence:
            return self._sequence.pop(0)
        return self._default


def test_hcsr04_pulse_reader_returns_echo_duration_us() -> None:
    trigger = FakeTriggerPin()
    echo = FakeEchoPin([0, 0, 1, 1, 1, 0], default=0)
    time_module = FakeTimeModule(tick_step_us=100)
    reader = Hcsr04PulseReader(
        trigger_pin=trigger,
        echo_pin=echo,
        time_module=time_module,
        timeout_us=2000,
    )

    duration_us = reader.read_echo_duration_us()

    assert duration_us > 0
    assert trigger.writes == [0, 1, 0]
    assert time_module.sleep_calls_us == [2, 10]


def test_hcsr04_pulse_reader_times_out_waiting_for_pulse_start() -> None:
    trigger = FakeTriggerPin()
    echo = FakeEchoPin([], default=0)
    time_module = FakeTimeModule(tick_step_us=200)
    reader = Hcsr04PulseReader(
        trigger_pin=trigger,
        echo_pin=echo,
        time_module=time_module,
        timeout_us=300,
    )

    with pytest.raises(UltrasonicTimeoutError, match="Timed out waiting for echo start"):
        reader.read_echo_duration_us()


def test_hcsr04_pulse_reader_times_out_waiting_for_pulse_end() -> None:
    trigger = FakeTriggerPin()
    echo = FakeEchoPin([0, 1], default=1)
    time_module = FakeTimeModule(tick_step_us=200)
    reader = Hcsr04PulseReader(
        trigger_pin=trigger,
        echo_pin=echo,
        time_module=time_module,
        timeout_us=300,
    )

    with pytest.raises(UltrasonicTimeoutError, match="Timed out waiting for echo end"):
        reader.read_echo_duration_us()
