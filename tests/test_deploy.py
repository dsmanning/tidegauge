from pathlib import Path

from tidegauge.deploy import (
    default_serial_device,
    deploy_project_to_mount,
    runtime_files_to_deploy,
)


def test_runtime_files_to_deploy_includes_main_and_package_sources(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('main')")
    pkg = tmp_path / "tidegauge"
    pkg.mkdir()
    (pkg / "a.py").write_text("a = 1")
    (pkg / "b.py").write_text("b = 2")
    (pkg / "__pycache__").mkdir()
    (pkg / "__pycache__" / "ignored.pyc").write_text("x")

    files = runtime_files_to_deploy(project_root=tmp_path)
    rel = [str(path.relative_to(tmp_path)) for path in files]

    assert "main.py" in rel
    assert "tidegauge/a.py" in rel
    assert "tidegauge/b.py" in rel
    assert "tidegauge/__pycache__/ignored.pyc" not in rel


def test_deploy_project_to_mount_copies_runtime_files(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    mount = tmp_path / "mount"
    mount.mkdir()

    (source / "main.py").write_text("print('main')")
    pkg = source / "tidegauge"
    pkg.mkdir()
    (pkg / "alpha.py").write_text("alpha = 1")

    copied = deploy_project_to_mount(project_root=source, mount_point=mount)
    copied_rel = [str(path.relative_to(mount)) for path in copied]

    assert "code.py" in copied_rel
    assert "main.py" in copied_rel
    assert "tidegauge/alpha.py" in copied_rel
    assert (mount / "code.py").read_text() == "from main import main\n\nmain()\n"
    assert (mount / "main.py").read_text() == "print('main')"
    assert (mount / "tidegauge" / "alpha.py").read_text() == "alpha = 1"


def test_default_serial_device_returns_ttyacm0() -> None:
    assert default_serial_device() == "/dev/ttyACM0"
