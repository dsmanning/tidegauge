from __future__ import annotations

from pathlib import Path


def test_rapid_diagnostic_mode_disabled_for_lora_transmit_build() -> None:
    config_path = Path(__file__).resolve().parents[1] / "arduino" / "ttn_otaa_lmic" / "config.h"
    content = config_path.read_text(encoding="utf-8")
    assert "inline constexpr bool RAPID_DIAGNOSTIC_MODE = false;" in content


def test_geometry_reference_uses_70cm_reference_height() -> None:
    config_path = Path(__file__).resolve().parents[1] / "arduino" / "ttn_otaa_lmic" / "config.h"
    content = config_path.read_text(encoding="utf-8")
    assert "inline constexpr float GEOMETRY_REFERENCE_M = 1.500f;" in content


def test_ultrasonic_power_enable_uses_d10_gpio10() -> None:
    config_path = Path(__file__).resolve().parents[1] / "arduino" / "ttn_otaa_lmic" / "config.h"
    content = config_path.read_text(encoding="utf-8")
    assert "inline constexpr int ULTRASONIC_POWER_ENABLE_PIN = 10;" in content


def test_ultrasonic_power_settle_time_is_one_second() -> None:
    config_path = Path(__file__).resolve().parents[1] / "arduino" / "ttn_otaa_lmic" / "config.h"
    content = config_path.read_text(encoding="utf-8")
    assert "inline constexpr std::uint32_t ULTRASONIC_POWER_SETTLE_MS = 2000;" in content


def test_ultrasonic_sample_count_is_sixty_four_for_diagnostic_burst() -> None:
    config_path = Path(__file__).resolve().parents[1] / "arduino" / "ttn_otaa_lmic" / "config.h"
    content = config_path.read_text(encoding="utf-8")
    assert "inline constexpr std::size_t ULTRASONIC_SAMPLE_COUNT = 64;" in content


def test_lora_uplink_power_is_reduced_for_energy_savings() -> None:
    config_path = Path(__file__).resolve().parents[1] / "arduino" / "ttn_otaa_lmic" / "config.h"
    content = config_path.read_text(encoding="utf-8")
    assert "inline constexpr bool LORA_ADR_ENABLED = true;" in content
    assert "inline constexpr std::int8_t LORA_UPLINK_TX_POWER_DBM = 10;" in content


def test_ds18b20_uses_d9_and_10_bit_resolution() -> None:
    config_path = Path(__file__).resolve().parents[1] / "arduino" / "ttn_otaa_lmic" / "config.h"
    content = config_path.read_text(encoding="utf-8")
    assert "inline constexpr int DS18B20_DATA_PIN = 9;" in content
    assert "inline constexpr std::uint8_t DS18B20_RESOLUTION_BITS = 10;" in content
