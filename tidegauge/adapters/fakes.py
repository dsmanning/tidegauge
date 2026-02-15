from dataclasses import dataclass, field


@dataclass
class FakeUltrasonicSensorPort:
    readings_m: list[float]

    def read_distance_m(self) -> float:
        if not self.readings_m:
            raise RuntimeError("No sensor readings remaining")
        return self.readings_m.pop(0)


@dataclass
class FakeRadioPort:
    sent_payloads: list[bytes] = field(default_factory=list)

    def send(self, payload: bytes) -> None:
        self.sent_payloads.append(payload)


@dataclass
class FakeClockPort:
    times_s: list[int]

    def now_s(self) -> int:
        if not self.times_s:
            raise RuntimeError("No clock values remaining")
        return self.times_s.pop(0)


@dataclass
class FakeSleepPort:
    sleep_calls_s: list[int] = field(default_factory=list)

    def sleep_s(self, seconds: int) -> None:
        self.sleep_calls_s.append(seconds)
