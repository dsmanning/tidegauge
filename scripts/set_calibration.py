#!/usr/bin/env python3
import sys

from tidegauge.calibration_cli import run_calibration_cli


if __name__ == "__main__":
    raise SystemExit(run_calibration_cli(argv=sys.argv[1:]))
