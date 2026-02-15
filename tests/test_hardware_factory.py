from tidegauge.hardware import HardwareConfig, build_runtime_dependencies


class FakeTimeModule:
    def __init__(self) -> None:
        self.now_s_value = 0.0
        self._ticks_us = 0
        self.sleep_calls: list[float] = []
        self.sleep_us_calls: list[int] = []

    def time(self) -> float:
        return self.now_s_value

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)

    def sleep_us(self, delay_us: int) -> None:
        self.sleep_us_calls.append(delay_us)
        self._ticks_us += delay_us

    def ticks_us(self) -> int:
        self._ticks_us += 100
        return self._ticks_us

    def ticks_diff(self, current: int, start: int) -> int:
        return current - start


class FakeMachineModule:
    class Pin:
        IN = 0
        OUT = 1
        _instances: dict[int, "FakeMachineModule.Pin"] = {}
        _input_sequences: dict[int, list[int]] = {}

        def __init__(self, pin_id: int, mode: int) -> None:
            self.pin_id = pin_id
            self.mode = mode
            self.writes: list[int] = []
            FakeMachineModule.Pin._instances[pin_id] = self

        def value(self, new_value: int | None = None) -> int:
            if new_value is not None:
                self.writes.append(new_value)
                return new_value

            if self.mode == FakeMachineModule.Pin.IN:
                sequence = FakeMachineModule.Pin._input_sequences.get(self.pin_id, [])
                if sequence:
                    return sequence.pop(0)
                return 0

            if self.writes:
                return self.writes[-1]
            return 0


class FakeLoRaClient:
    def __init__(self) -> None:
        self.sent_payloads: list[bytes] = []

    def send(self, payload: bytes) -> bool:
        self.sent_payloads.append(payload)
        return True


def test_build_runtime_dependencies_wires_sensor_and_radio() -> None:
    fake_time = FakeTimeModule()
    FakeMachineModule.Pin._instances = {}
    FakeMachineModule.Pin._input_sequences = {7: [0, 0, 1, 1, 0]}
    fake_client = FakeLoRaClient()

    deps = build_runtime_dependencies(
        machine_module=FakeMachineModule,
        time_module=fake_time,
        lora_client=fake_client,
        config=HardwareConfig(trigger_pin_id=6, echo_pin_id=7),
    )

    distance_m = deps.sensor.read_distance_m()
    deps.radio.send(b"\x01\x02")

    assert distance_m > 0
    assert fake_client.sent_payloads == [b"\x01\x02"]
    assert FakeMachineModule.Pin._instances[6].writes == [0, 1, 0]


def test_build_runtime_dependencies_wires_scheduler_clock_and_sleeper() -> None:
    fake_time = FakeTimeModule()
    FakeMachineModule.Pin._instances = {}
    FakeMachineModule.Pin._input_sequences = {}
    fake_client = FakeLoRaClient()

    deps = build_runtime_dependencies(
        machine_module=FakeMachineModule,
        time_module=fake_time,
        lora_client=fake_client,
        config=HardwareConfig(trigger_pin_id=6, echo_pin_id=7, measurement_interval_s=60),
    )

    fake_time.now_s_value = 0
    assert deps.scheduler.is_due() is True
    assert deps.scheduler.is_due() is False

    fake_time.now_s_value = 60
    assert deps.scheduler.is_due() is True

    deps.sleeper.sleep_s(2)
    assert fake_time.sleep_calls == [2]
