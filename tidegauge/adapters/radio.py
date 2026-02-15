from typing import Protocol


class RadioSendError(RuntimeError):
    """Raised when radio transmission fails."""


class LoRaClient(Protocol):
    def send(self, payload: bytes) -> bool:
        """Send payload and return success state."""


class Rfm95RadioAdapter:
    def __init__(self, *, client: LoRaClient) -> None:
        self._client = client

    def send(self, payload: bytes) -> None:
        try:
            sent = self._client.send(payload)
        except Exception as exc:
            raise RadioSendError(str(exc)) from exc

        if not sent:
            raise RadioSendError("Radio client reported send failure")
