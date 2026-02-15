from pathlib import Path

from tidegauge.deploy_cli import run_deploy_cli, run_serial_device_cli


class RecordingDeploy:
    def __init__(self) -> None:
        self.calls: list[dict[str, Path]] = []

    def __call__(self, *, project_root: Path, mount_point: Path) -> list[Path]:
        self.calls.append({"project_root": project_root, "mount_point": mount_point})
        return [mount_point / "main.py"]


def test_run_deploy_cli_parses_mount_and_calls_deploy(tmp_path: Path) -> None:
    deploy = RecordingDeploy()
    project_root = tmp_path / "project"
    mount = tmp_path / "mount"
    project_root.mkdir()
    mount.mkdir()

    exit_code = run_deploy_cli(
        argv=["--project-root", str(project_root), "--mount-point", str(mount)],
        deploy_fn=deploy,
    )

    assert exit_code == 0
    assert len(deploy.calls) == 1
    assert deploy.calls[0]["project_root"] == project_root
    assert deploy.calls[0]["mount_point"] == mount


def test_run_serial_device_cli_prints_default_device() -> None:
    outputs: list[str] = []

    exit_code = run_serial_device_cli(output_fn=outputs.append)

    assert exit_code == 0
    assert outputs == ["/dev/ttyACM0"]
