from typing import Protocol


class UltrasonicTimeoutError(RuntimeError):
    """Raised when an HC-SR04 echo pulse does not arrive in time."""


class TriggerPin(Protocol):
    def value(self, new_value: int | None = None) -> int:
        """Read or write pin value."""


class EchoPin(Protocol):
    def value(self) -> int:
        """Read pin value."""


class TimeModule(Protocol):
    def sleep_us(self, delay_us: int) -> None:
        """Sleep for microseconds."""

    def ticks_us(self) -> int:
        """Return monotonic microseconds."""

    def ticks_diff(self, current: int, start: int) -> int:
        """Return elapsed microseconds with wrap handling."""


class Hcsr04PulseReader:
    def __init__(
        self,
        *,
        trigger_pin: TriggerPin,
        echo_pin: EchoPin,
        time_module: TimeModule,
        timeout_us: int = 30_000,
    ) -> None:
        self._trigger_pin = trigger_pin
        self._echo_pin = echo_pin
        self._time = time_module
        self._timeout_us = timeout_us

    def read_echo_duration_us(self) -> int:
        self._trigger_pin.value(0)
        self._time.sleep_us(2)
        self._trigger_pin.value(1)
        self._time.sleep_us(10)
        self._trigger_pin.value(0)

        wait_start_us = self._time.ticks_us()
        while self._echo_pin.value() == 0:
            if self._elapsed_since(wait_start_us) > self._timeout_us:
                raise UltrasonicTimeoutError("Timed out waiting for echo start")

        pulse_start_us = self._time.ticks_us()
        while self._echo_pin.value() == 1:
            if self._elapsed_since(pulse_start_us) > self._timeout_us:
                raise UltrasonicTimeoutError("Timed out waiting for echo end")

        pulse_end_us = self._time.ticks_us()
        return self._time.ticks_diff(pulse_end_us, pulse_start_us)

    def _elapsed_since(self, start_us: int) -> int:
        now_us = self._time.ticks_us()
        return self._time.ticks_diff(now_us, start_us)
