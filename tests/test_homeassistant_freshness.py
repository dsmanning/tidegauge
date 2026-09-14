from pathlib import Path

import jinja2
import yaml


def test_freshness_distinguishes_packets_from_valid_measurements():
    config = yaml.safe_load(Path('homeassistant/tide_gauge_freshness.yaml').read_text())
    sensors = config['template'][0]['sensor']
    env = jinja2.Environment()
    env.globals['is_number'] = lambda value: isinstance(value, (int, float)) and not isinstance(value, bool)
    payload = {'received_at': '2026-09-14T21:11:00Z', 'uplink_message': {'decoded_payload': {'tide_height_m': None, 'temperature_c': 20}}}
    def render(index):
        return env.from_string(sensors[index]['state']).render(trigger={'payload_json': payload}, this={'state': '2026-09-14T10:38:00Z'}).strip()
    assert render(0) == '2026-09-14T21:11:00Z'
    assert render(1) == '2026-09-14T10:38:00Z'
    assert render(2) == '2026-09-14T21:11:00Z'
    payload['uplink_message']['decoded_payload']['tide_height_m'] = .42
    assert render(1) == '2026-09-14T21:11:00Z'
    payload['uplink_message'] = {}
    assert render(1) == '2026-09-14T10:38:00Z'


def test_freshness_expires_even_when_last_value_is_retained():
    config = yaml.safe_load(Path('homeassistant/tide_gauge_freshness.yaml').read_text())
    template = config['template'][1]['binary_sensor'][0]['state']
    env = jinja2.Environment()
    current = 1000
    timestamp = 701
    env.globals.update(now=lambda: current, as_timestamp=lambda value, default=0: value if isinstance(value, (int, float)) else default,
                       states=lambda entity: timestamp)
    assert env.from_string(template).render().strip() == 'False'
    current = 1001
    assert env.from_string(template).render().strip() == 'True'
    timestamp = 'unknown'
    assert env.from_string(template).render().strip() == 'True'
