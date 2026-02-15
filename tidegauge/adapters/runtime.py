import time
from typing import Protocol


class TimeModule(Protocol):
    def time(self) -> float:
        """Return current wall-clock seconds."""

    def sleep(self, seconds: float) -> None:
        """Sleep for the requested seconds."""


class SystemClockAdapter:
    def __init__(self, *, time_module: TimeModule = time) -> None:
        self._time_module = time_module

    def now_s(self) -> int:
        return int(self._time_module.time())


class SystemSleepAdapter:
    def __init__(self, *, time_module: TimeModule = time) -> None:
        self._time_module = time_module

    def sleep_s(self, seconds: int) -> None:
        self._time_module.sleep(seconds)
