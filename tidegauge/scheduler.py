try:
    from collections.abc import Callable
except ImportError:  # pragma: no cover - CircuitPython compatibility
    class Callable:  # type: ignore[no-redef]
        def __class_getitem__(cls, _item):
            return cls


class MinuteScheduler:
    def __init__(self, *, now_s: Callable[[], int], interval_s: int = 60) -> None:
        self._now_s = now_s
        self._interval_s = interval_s
        self._next_due_s: int | None = None

    def is_due(self) -> bool:
        now = self._now_s()

        if self._next_due_s is None:
            self._next_due_s = now + self._interval_s
            return True

        if now < self._next_due_s:
            return False

        self._next_due_s = now + self._interval_s
        return True
