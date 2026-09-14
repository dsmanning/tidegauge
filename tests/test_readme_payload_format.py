from pathlib import Path


def test_readme_documents_resilience_deployment_requirements():
    text = Path('README.md').read_text()
    assert 'bash scripts/compile_firmware.sh' in text
    assert '64 KB' in text
    assert '26 bytes' in text
    assert '8 seconds' in text
    assert 'docs/reliability-validation.md' in text
    assert 'homeassistant/tide_gauge_freshness.yaml' in text


def test_readme_documents_current_ten_byte_payload() -> None:
    content = Path("README.md").read_text(encoding="utf-8")

    assert "Normal uplinks on FPort 1 retain the 10-byte payload:" in content
    assert "Bytes `6-7`: `distance_stddev_mm`" in content
    assert "Bytes `8-9`: `temperature_centi_c`" in content
    assert "invalid sentinel" in content
