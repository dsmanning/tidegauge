from pathlib import Path


def test_arduino_config_template_exists() -> None:
    template_path = Path("arduino/ttn_otaa_lmic/config.example.h")
    assert template_path.exists()
    content = template_path.read_text(encoding="utf-8")

    assert "DEV_EUI_HEX" in content
    assert "APP_EUI_HEX" in content
    assert "APP_KEY_HEX" in content
    assert "US915_SUBBAND" in content
    assert "LORA_ADR_ENABLED" in content
    assert "LORA_UPLINK_TX_POWER_DBM" in content
    assert "RAPID_DIAGNOSTIC_MODE" in content
    assert "RAPID_DIAGNOSTIC_INTERVAL_S" in content
    assert "ULTRASONIC_SAMPLE_COUNT" in content
    assert "ULTRASONIC_POWER_ENABLE_PIN" in content
    assert "ULTRASONIC_POWER_SETTLE_MS" in content
    assert "ULTRASONIC_TIMEOUT_US" in content
    assert "IDLE_LOOP_SLEEP_MS" in content
    assert "DS18B20_DATA_PIN" in content
    assert "DS18B20_RESOLUTION_BITS" in content
    assert "SPEED_OF_SOUND_M_PER_US" in content
    assert "GEOMETRY_REFERENCE_M" in content
    assert "DATUM_OFFSET_M" in content
    assert "inline constexpr bool RAPID_DIAGNOSTIC_MODE = false;" in content
    assert "inline constexpr std::size_t ULTRASONIC_SAMPLE_COUNT = 64;" in content
    assert "WATCHDOG_TIMEOUT_MS" in content


def test_sketch_uses_external_config_header() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert '"config.h"' in content
    assert '"config.example.h"' in content
    assert "<OneWire.h>" in content
    assert "<DallasTemperature.h>" in content
    assert "SubbandFallback g_subband_fallback(tg_config::US915_SUBBAND)" in content
    assert "LMIC_setAdrMode" in content
    assert "LMIC_setDrTxpow" in content
    assert "LMIC_selectSubBand(initial_subband)" in content
    assert "DallasTemperature" in content
    assert "OneWire" in content
    assert "tg_config::DS18B20_DATA_PIN" in content
    assert "tg_config::DS18B20_RESOLUTION_BITS" in content
    assert "sensors.setResolution" in content
    assert "sensors.requestTemperatures();" in content
    assert "sensors.getTempCByIndex(0)" in content
    assert "tg_config::ULTRASONIC_SAMPLE_COUNT" in content
    assert "tg_config::ULTRASONIC_TIMEOUT_US" in content
    assert "tg_config::ULTRASONIC_POWER_ENABLE_PIN" in content
    assert "tg_config::ULTRASONIC_POWER_SETTLE_MS" in content
    assert "tg_config::IDLE_LOOP_SLEEP_MS" in content
    assert "distance_from_pulse_us" in content
    assert "if (tg_config::RAPID_DIAGNOSTIC_MODE)" in content
    assert 'Serial.print("DIAG: sample[' in content


def test_sketch_reports_ultrasonic_diagnostic_summary_fields() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert 'Serial.print("DIAG: samples_valid=");' in content
    assert 'Serial.print(" samples_timeout=");' in content
    assert 'Serial.print(" pulse_min_us=");' in content
    assert 'Serial.print(" pulse_max_us=");' in content
    assert 'Serial.print(" echo_high_stuck=");' in content
    assert 'Serial.print(" temperature_c=");' in content


def test_sketch_reports_ds18b20_bus_diagnostics() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert 'Serial.print("DS18B20: device_count=");' in content
    assert 'Serial.print(" DS18B20: address=");' in content
    assert "g_temperature_sensors.getDeviceCount()" in content
    assert "g_temperature_sensors.getAddress(" in content


def test_sketch_uses_jsn_compatible_trigger_pulse_width() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert "delayMicroseconds(20);" in content


def test_sketch_power_gates_sensor_when_configured_and_sleeps_in_idle_loop() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert "power_on_ultrasonic_sensor();" in content
    assert "power_off_ultrasonic_sensor();" in content
    assert "pinMode(HCSR04_POWER_ENABLE_PIN, OUTPUT);" in content
    assert "sleep_ms(tg_config::IDLE_LOOP_SLEEP_MS);" in content


def test_sketch_configures_adaptive_link_once_after_join() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert "static void configure_adaptive_lora_link()" in content
    assert "LMIC_setAdrMode(tg_config::LORA_ADR_ENABLED ? 1 : 0);" in content
    assert "LMIC_setLinkCheckMode(tg_config::LORA_ADR_ENABLED ? 1 : 0);" in content
    assert "LMIC_setDrTxpow(DR_SF10, tg_config::LORA_UPLINK_TX_POWER_DBM);" in content
    assert content.count("configure_adaptive_lora_link();") == 1

    joined_case = content.index("case EV_JOINED:")
    joined_end = content.index("case EV_JOIN_FAILED:")
    assert "configure_adaptive_lora_link();" in content[joined_case:joined_end]

    send_start = content.index("static void do_send(")
    send_end = content.index("void onEvent(")
    assert "LMIC_setDrTxpow" not in content[send_start:send_end]


def test_sketch_logs_adaptive_lora_parameters_for_each_uplink() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert 'Serial.print(" lora_dr=");' in content
    assert "Serial.print(static_cast<unsigned>(LMIC.datarate));" in content
    assert 'Serial.print(" lora_tx_power_dbm=");' in content
    assert "Serial.print(static_cast<int>(LMIC.adrTxPow));" in content


def test_sketch_does_not_include_temporary_join_diagnostics() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert "CFG: subband=" not in content
    assert "CFG: eui_checksum=0x" not in content
    assert "eui_checksum(" not in content


def test_sketch_does_not_include_experimental_watchdog_sleep_path() -> None:
    sketch_path = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino")
    content = sketch_path.read_text(encoding="utf-8")

    assert "watchdog_enable_caused_reboot()" not in content
    assert "enter_watchdog_deep_sleep(" not in content
    assert "restore_lmic_session_from_retained_state()" not in content
    assert "LMIC_setSession" not in content
    assert "LMIC_getSessionKeys" not in content


def test_sketch_reports_watchdog_reset_cause_and_uses_recovery_backoff() -> None:
    content = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino").read_text(encoding="utf-8")
    assert "watchdog_caused_reboot()" in content
    assert "backoff_seconds(g_recovery_failures)" in content


def test_successful_join_cancels_a_pending_delayed_recovery() -> None:
    content = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino").read_text(encoding="utf-8")
    joined_case = content.index("case EV_JOINED:")
    joined_end = content.index("case EV_JOIN_FAILED:")
    joined = content[joined_case:joined_end]
    assert "os_clearCallback(&join_restart_job);" in joined
    assert "g_join_restart_scheduled = false;" in joined


def test_sketch_uses_independent_sampling_and_transmit_jobs() -> None:
    content = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino").read_text(encoding="utf-8")
    assert "static osjob_t samplejob;" in content
    assert "os_setTimedCallback(&samplejob" in content
    assert "static void try_send(osjob_t *j)" in content
    tx_case = content[content.index("case EV_TXCOMPLETE:"):content.index("case EV_JOIN_TXCOMPLETE:")]
    assert "schedule_next_measurement();" not in tx_case


def test_sampling_starts_before_join_but_transmission_waits_for_join() -> None:
    content = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino").read_text(encoding="utf-8")
    setup = content[content.index("void setup() {"):content.index("void loop() {")]
    try_send = content[content.index("static void try_send"):content.index("static void do_send")]
    joined_case = content[content.index("case EV_JOINED:"):content.index("case EV_JOIN_FAILED:")]

    assert setup.index("do_send(&samplejob);") < setup.index("LMIC_startJoining();")
    assert "if (!g_network_joined)" in try_send
    assert "g_network_joined = true;" in joined_case
    assert "try_send(&sendjob);" in joined_case


def test_measurement_cadence_is_anchored_when_capture_begins() -> None:
    content = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino").read_text(encoding="utf-8")
    capture_start = content.index("static void do_send")
    capture = content[capture_start:content.index("void onEvent", capture_start)]

    assert capture.index("g_measurement_scheduler.mark_sampled") < capture.index("power_on_ultrasonic_sensor();")


def test_blocking_capture_is_skipped_during_active_join_receive_windows() -> None:
    content = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino").read_text(encoding="utf-8")
    capture_start = content.index("static void do_send")
    capture = content[capture_start:content.index("void onEvent", capture_start)]

    guard = capture.index("power_on_ultrasonic_sensor();")
    assert "g_join_in_progress" in capture[:guard]
    assert "schedule_next_measurement();" in capture[:guard]


def test_watchdog_timeout_stays_within_rp2040_limit() -> None:
    config = Path("arduino/ttn_otaa_lmic/config.example.h").read_text(encoding="utf-8")
    assert "inline constexpr std::uint32_t WATCHDOG_TIMEOUT_MS = 8000;" in config


def test_watchdog_is_serviced_during_bounded_ultrasonic_capture() -> None:
    content = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino").read_text(encoding="utf-8")
    loop_start = content.index("for (std::size_t i = 0; i < HCSR04_SAMPLE_COUNT; ++i)")
    sample_loop = content[loop_start:content.index("if (tg_config::RAPID_DIAGNOSTIC_MODE)", loop_start)]

    assert "pulseIn(HCSR04_ECHO_PIN, HIGH, HCSR04_TIMEOUT_US)" in sample_loop
    assert "watchdog_update();" in sample_loop


def test_watchdog_is_serviced_around_temperature_conversion() -> None:
    content = Path("arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino").read_text(encoding="utf-8")
    request_start = content.index("g_temperature_sensors.requestTemperatures();")
    request_end = content.index("if (temperature_c == DEVICE_DISCONNECTED_C)", request_start)
    temperature_block = content[request_start:request_end]

    assert "watchdog_update();" in temperature_block
