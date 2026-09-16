from pathlib import Path


def test_offline_firmware_script_is_local_and_uploads_after_compile() -> None:
    script = Path("scripts/install_firmware_offline.sh").read_text(encoding="utf-8")

    assert "arduino-cli compile" in script
    assert "arduino-cli upload" in script
    assert "rp2040:rp2040:adafruit_feather_rfm" in script
    assert "config.h" in script
    assert "--verify" in script
    assert "curl" not in script
    assert "apt" not in script


def test_offline_firmware_script_defaults_to_usb_serial_device() -> None:
    script = Path("scripts/install_firmware_offline.sh").read_text(encoding="utf-8")

    assert 'PORT="${PORT:-/dev/ttyACM0}"' in script
    assert 'ROOT_DIR=' in script
