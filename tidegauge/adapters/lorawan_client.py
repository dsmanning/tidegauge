try:
    from typing import Protocol
except ImportError:  # pragma: no cover - CircuitPython compatibility
    Protocol = object


class LoRaWanDriver(Protocol):
    def join(self) -> None:
        """Join the LoRaWAN network."""

    def send(self, payload: bytes) -> bool:
        """Send payload and return success."""


class LoRaWanClientAdapter:
    def __init__(self, *, driver: LoRaWanDriver) -> None:
        self._driver = driver
        self._is_joined = False

    def send(self, payload: bytes) -> bool:
        if not self._is_joined:
            self._driver.join()
            self._is_joined = True

        return self._driver.send(payload)
