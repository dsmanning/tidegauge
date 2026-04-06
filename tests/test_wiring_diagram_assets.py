from pathlib import Path


def test_wiring_diagram_assets_exist_and_include_expected_labels() -> None:
    svg_path = Path("docs/wiring_diagram.svg")
    pdf_path = Path("docs/wiring_diagram.pdf")

    assert svg_path.exists()
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0

    content = svg_path.read_text(encoding="utf-8")
    assert "HC-SR04" in content
    assert "DS18B20" in content
    assert "D5 / ECHO" in content
    assert "D6 / TRIG" in content
    assert "D9 / DS18B20 DATA" in content
    assert "D10 / SENSOR PWR EN" in content
    assert "A0 / BAT ADC" in content
    assert "resistor-symbol" in content
    assert "transistor-npn" in content
    assert "wire-jump" in content
    assert "junction-dot" in content
    assert "NET_TRIG" in content
    assert "NET_ECHO" in content
    assert "NET_1WIRE" in content
    assert "NET_PWR_EN" in content
    assert "NET_BAT_SENSE" in content
