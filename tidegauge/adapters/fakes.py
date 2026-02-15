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
