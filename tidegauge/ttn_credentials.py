try:
    from typing import Any, Callable
except ImportError:  # pragma: no cover - CircuitPython compatibility
    Any = object
    class Callable:  # type: ignore[no-redef]
        def __class_getitem__(cls, _item):
            return cls


class TtnCredentialsError(RuntimeError):
    """Raised when TTN credentials cannot be loaded safely."""


class TtnCredentials:
    def __init__(
        self,
        *,
        dev_eui: str | None = None,
        app_eui: str | None = None,
        app_key: str | None = None,
        dev_addr: str | None = None,
        nwk_skey: str | None = None,
        app_skey: str | None = None,
    ) -> None:
        self.dev_eui = dev_eui
        self.app_eui = app_eui
        self.app_key = app_key
        self.dev_addr = dev_addr
        self.nwk_skey = nwk_skey
        self.app_skey = app_skey


def _validate_required_value(*, data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise TtnCredentialsError(f"Missing TTN credential: {key}")
    return value


def _load_default_secrets() -> dict[str, object]:
    secrets_module = __import__("secrets")
    data = getattr(secrets_module, "secrets")
    if not isinstance(data, dict):
        raise TtnCredentialsError("CircuitPython secrets must be a mapping")
    return data


def load_ttn_credentials(
    *,
    secrets_provider: Callable[[], dict[str, object]] | None = None,
) -> TtnCredentials:
    provider = secrets_provider or _load_default_secrets
    try:
        data: Any = provider()
    except TtnCredentialsError:
        raise
    except Exception as exc:
        raise TtnCredentialsError("Unable to load CircuitPython secrets") from exc

    if not isinstance(data, dict):
        raise TtnCredentialsError("CircuitPython secrets must be a mapping")

    has_any_otaa = any(key in data for key in ("dev_eui", "app_eui", "app_key"))
    has_any_abp = any(key in data for key in ("dev_addr", "nwk_skey", "app_skey"))

    if has_any_otaa:
        return TtnCredentials(
            dev_eui=_validate_required_value(data=data, key="dev_eui"),
            app_eui=_validate_required_value(data=data, key="app_eui"),
            app_key=_validate_required_value(data=data, key="app_key"),
        )

    if has_any_abp:
        missing = [
            key for key in ("dev_addr", "nwk_skey", "app_skey") if key not in data
        ]
        if missing:
            raise TtnCredentialsError(
                "Missing TTN credentials: provide OTAA (dev_eui/app_eui/app_key) "
                "or ABP (dev_addr/nwk_skey/app_skey)"
            )
        return TtnCredentials(
            dev_addr=_validate_required_value(data=data, key="dev_addr"),
            nwk_skey=_validate_required_value(data=data, key="nwk_skey"),
            app_skey=_validate_required_value(data=data, key="app_skey"),
        )

    raise TtnCredentialsError(
        "Missing TTN credentials: provide OTAA (dev_eui/app_eui/app_key) "
        "or ABP (dev_addr/nwk_skey/app_skey)"
    )
