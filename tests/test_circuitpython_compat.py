from tidegauge.adapters.circuitpython_compat import (
    CircuitPythonTimeModule,
    create_machine_compat_module,
)


class FakeBoardModule:
    D6 = object()
    D7 = object()


class FakeDirection:
    INPUT = "input"
    OUTPUT = "output"


class FakeDigitalInOut:
    def __init__(self, pin: object) -> None:
        self.pin = pin
        self.direction: str | None = None
        self.value = False


class FakeDigitalioModule:
    Direction = FakeDirection
    DigitalInOut = FakeDigitalInOut


class FakeTimeModule:
    def __init__(self) -> None:
        self.sleep_calls: list[float] = []
        self._ns = 0
        self._s = 0.0

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)
        self._s += seconds
        self._ns += int(seconds * 1_000_000_000)

    def monotonic_ns(self) -> int:
        self._ns += 1_000
        return self._ns

    def monotonic(self) -> float:
        self._s += 0.1
        return self._s


def test_create_machine_compat_module_maps_pin_ids_to_board_d_pins() -> None:
    machine = create_machine_compat_module(
        board_module=FakeBoardModule,
        digitalio_module=FakeDigitalioModule,
    )

    trigger = machine.Pin(6, machine.Pin.OUT)
    echo = machine.Pin(7, machine.Pin.IN)
    trigger.value(1)
    trigger.value(0)

    assert trigger.value() == 0
    assert echo.value() == 0
    assert trigger._dio.direction == FakeDirection.OUTPUT
    assert echo._dio.direction == FakeDirection.INPUT


def test_circuitpython_time_module_adapts_us_and_seconds_interfaces() -> None:
    fake_time = FakeTimeModule()
    adapted = CircuitPythonTimeModule(time_module=fake_time)

    adapted.sleep_us(10)
    start = adapted.ticks_us()
    end = adapted.ticks_us()
    adapted.sleep(2)

    assert fake_time.sleep_calls[0] == 0.00001
    assert adapted.ticks_diff(end, start) > 0
    assert adapted.time() == int(fake_time.monotonic())
