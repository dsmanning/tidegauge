import argparse
from pathlib import Path
from typing import Callable, Sequence

from tidegauge.deploy import default_serial_device, deploy_project_to_mount


def run_deploy_cli(
    *,
    argv: Sequence[str],
    deploy_fn: Callable[..., list[Path]] = deploy_project_to_mount,
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--mount-point", type=Path, required=True)
    args = parser.parse_args(argv)

    deploy_fn(project_root=args.project_root, mount_point=args.mount_point)
    return 0


def run_serial_device_cli(*, output_fn: Callable[[str], None] = print) -> int:
    output_fn(default_serial_device())
    return 0
