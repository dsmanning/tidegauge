import json
import os
import subprocess
import sys
from pathlib import Path


def test_build_script_selects_filesystem_and_pins_region_for_c_and_cpp(tmp_path):
    fake = tmp_path / 'arduino-cli'
    fake.write_text('#!/usr/bin/env python3\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n')
    fake.chmod(0o755)
    result = subprocess.run(['bash', 'scripts/compile_firmware.sh', '--output-dir', '/tmp/firmware-test'],
                            env={**os.environ, 'PATH': str(tmp_path) + ':' + os.environ['PATH']},
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    args = json.loads(result.stdout)
    assert 'rp2040:rp2040:adafruit_feather_rfm:flash=8388608_65536' in args
    for language in ('c', 'cpp'):
        value = next(arg for arg in args if arg.startswith(f'compiler.{language}.extra_flags='))
        assert '-DARDUINO_LMIC_PROJECT_CONFIG_H_SUPPRESS' in value
        assert '-DCFG_us915=1' in value
        assert '-DCFG_sx1276_radio=1' in value
    assert args[-2:] == ['--output-dir', '/tmp/firmware-test']


def test_site_specific_checks_skip_when_secret_config_is_absent(tmp_path):
    folder = tmp_path / 'tests'
    folder.mkdir()
    check = folder / 'test_arduino_runtime_config.py'
    check.write_text(Path('tests/test_arduino_runtime_config.py').read_text())
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', str(check)],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
    assert '7 skipped' in result.stdout
