from tidegauge.adapters.fakes import FakeClockPort, FakeSleepPort
from tidegauge.ports import ClockPort, SleepPort


def read_time(clock: ClockPort) -> int:
    return clock.now_s()


def do_sleep(sleeper: SleepPort, seconds: int) -> None:
    sleeper.sleep_s(seconds)


def test_fake_clock_port_returns_progressive_times() -> None:
    clock = FakeClockPort(times_s=[100, 101, 102])

    assert read_time(clock) == 100
    assert read_time(clock) == 101
    assert read_time(clock) == 102


def test_fake_sleep_port_records_sleep_calls() -> None:
    sleeper = FakeSleepPort()

    do_sleep(sleeper, 1)
    do_sleep(sleeper, 60)

    assert sleeper.sleep_calls_s == [1, 60]
