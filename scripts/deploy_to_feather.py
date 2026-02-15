#!/usr/bin/env python3
import sys

from tidegauge.deploy_cli import run_deploy_cli


if __name__ == "__main__":
    raise SystemExit(run_deploy_cli(argv=sys.argv[1:]))
