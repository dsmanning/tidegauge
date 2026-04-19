from pathlib import Path


def test_readme_documents_current_ten_byte_payload() -> None:
    content = Path("README.md").read_text(encoding="utf-8")

    assert "Current uplink payload format is 10 bytes:" in content
    assert "Bytes `6-7`: `distance_stddev_mm`" in content
    assert "Bytes `8-9`: `temperature_centi_c`" in content
    assert "invalid sentinel" in content
