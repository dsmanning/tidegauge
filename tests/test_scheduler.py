from tidegauge.scheduler import MinuteScheduler


class FakeClock:
    def __init__(self) -> None:
        self.now_s = 0

    def now(self) -> int:
        return self.now_s


def test_minute_scheduler_runs_immediately_then_every_60_seconds() -> None:
    clock = FakeClock()
    scheduler = MinuteScheduler(now_s=clock.now, interval_s=60)

    assert scheduler.is_due() is True
    assert scheduler.is_due() is False

    clock.now_s = 59
    assert scheduler.is_due() is False

    clock.now_s = 60
    assert scheduler.is_due() is True

    clock.now_s = 119
    assert scheduler.is_due() is False

    clock.now_s = 120
    assert scheduler.is_due() is True
