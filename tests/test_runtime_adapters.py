from tidegauge.adapters.runtime import SystemClockAdapter, SystemSleepAdapter


class FakeTimeModule:
    def __init__(self) -> None:
        self.now_value = 0.0
        self.sleep_calls: list[float] = []

    def time(self) -> float:
        return self.now_value

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)


def test_system_clock_adapter_returns_int_seconds() -> None:
    fake_time = FakeTimeModule()
    fake_time.now_value = 123.9
    clock = SystemClockAdapter(time_module=fake_time)

    assert clock.now_s() == 123


def test_system_sleep_adapter_delegates_sleep_seconds() -> None:
    fake_time = FakeTimeModule()
    sleeper = SystemSleepAdapter(time_module=fake_time)

    sleeper.sleep_s(2)
    sleeper.sleep_s(1)

    assert fake_time.sleep_calls == [2, 1]
