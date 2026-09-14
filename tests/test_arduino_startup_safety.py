from pathlib import Path


def test_watchdog_covers_initialization_and_runtime_is_staged():
    text = Path('arduino/ttn_otaa_lmic/ttn_otaa_lmic.ino').read_text()
    setup = text[text.index('void setup()'):text.index('void loop()')]
    assert setup.index('watchdog_enable(') < setup.index('os_init()')
    assert setup.index('watchdog_enable(') < setup.index('while (!Serial')
    assert 'g_radio.service();' in text
    assert 'g_node.tick();' in text
    assert 'for (std::size_t i = 0; i < HCSR04_SAMPLE_COUNT' not in text
    assert 'LittleFSConfig(false)' in text
    assert 'static_assert(tg_config::US915_SUBBAND >= 1' in text
