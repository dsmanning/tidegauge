try:
    from typing import Any
except ImportError:  # pragma: no cover - CircuitPython compatibility
    Any = object


def create_machine_compat_module(*, board_module: Any, digitalio_module: Any) -> Any:
    class Pin:
        IN = 0
        OUT = 1

        def __init__(self, pin_id: int, mode: int) -> None:
            pin_name = f"D{pin_id}"
            board_pin = getattr(board_module, pin_name)
            self._dio = digitalio_module.DigitalInOut(board_pin)
            if mode == self.OUT:
                self._dio.direction = digitalio_module.Direction.OUTPUT
            else:
                self._dio.direction = digitalio_module.Direction.INPUT

        def value(self, new_value: int | None = None) -> int:
            if new_value is not None:
                self._dio.value = bool(new_value)
            return int(bool(self._dio.value))

    class MachineCompatModule:
        pass

    MachineCompatModule.Pin = Pin
    return MachineCompatModule


class CircuitPythonTimeModule:
    def __init__(self, *, time_module: Any) -> None:
        self._time = time_module

    def sleep_us(self, delay_us: int) -> None:
        self._time.sleep(delay_us / 1_000_000)

    def ticks_us(self) -> int:
        if hasattr(self._time, "monotonic_ns"):
            return int(self._time.monotonic_ns() // 1_000)
        return int(self._time.monotonic() * 1_000_000)

    def ticks_diff(self, current: int, start: int) -> int:
        return current - start

    def time(self) -> int:
        return int(self._time.monotonic())

    def sleep(self, seconds: float) -> None:
        self._time.sleep(seconds)
