import pytest

from tidegauge.ttn_credentials import TtnCredentialsError, load_ttn_credentials


def test_load_ttn_credentials_reads_required_fields() -> None:
    credentials = load_ttn_credentials(
        secrets_provider=lambda: {
            "dev_eui": "0011223344556677",
            "app_eui": "8899AABBCCDDEEFF",
            "app_key": "00112233445566778899AABBCCDDEEFF",
        }
    )

    assert credentials.dev_eui == "0011223344556677"
    assert credentials.app_eui == "8899AABBCCDDEEFF"
    assert credentials.app_key == "00112233445566778899AABBCCDDEEFF"


def test_load_ttn_credentials_accepts_abp_equivalent_fields() -> None:
    credentials = load_ttn_credentials(
        secrets_provider=lambda: {
            "dev_addr": "26011BEE",
            "nwk_skey": "00112233445566778899AABBCCDDEEFF",
            "app_skey": "FFEEDDCCBBAA99887766554433221100",
        }
    )

    assert credentials.dev_addr == "26011BEE"
    assert credentials.nwk_skey == "00112233445566778899AABBCCDDEEFF"
    assert credentials.app_skey == "FFEEDDCCBBAA99887766554433221100"


def test_load_ttn_credentials_raises_when_secrets_provider_fails() -> None:
    def missing_secrets() -> dict[str, str]:
        raise ImportError("No module named secrets")

    with pytest.raises(TtnCredentialsError, match="Unable to load CircuitPython secrets"):
        load_ttn_credentials(secrets_provider=missing_secrets)


def test_load_ttn_credentials_raises_when_required_field_is_missing() -> None:
    with pytest.raises(TtnCredentialsError, match="Missing TTN credential: app_key"):
        load_ttn_credentials(
            secrets_provider=lambda: {
                "dev_eui": "0011223344556677",
                "app_eui": "8899AABBCCDDEEFF",
            }
        )

    with pytest.raises(
        TtnCredentialsError,
        match="Missing TTN credentials: provide OTAA",
    ):
        load_ttn_credentials(
            secrets_provider=lambda: {
                "dev_addr": "26011BEE",
                "nwk_skey": "00112233445566778899AABBCCDDEEFF",
            }
        )


def test_load_ttn_credentials_raises_when_provider_does_not_return_dict() -> None:
    with pytest.raises(TtnCredentialsError, match="secrets must be a mapping"):
        load_ttn_credentials(secrets_provider=lambda: None)  # type: ignore[arg-type]
