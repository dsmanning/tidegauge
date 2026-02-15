import shutil
from pathlib import Path


def runtime_files_to_deploy(*, project_root: Path) -> list[Path]:
    files: list[Path] = []
    main_path = project_root / "main.py"
    if main_path.exists():
        files.append(main_path)

    package_root = project_root / "tidegauge"
    for path in package_root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        files.append(path)

    return sorted(files)


def deploy_project_to_mount(*, project_root: Path, mount_point: Path) -> list[Path]:
    copied_paths: list[Path] = []
    for source in runtime_files_to_deploy(project_root=project_root):
        rel = source.relative_to(project_root)
        destination = mount_point / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied_paths.append(destination)
    return copied_paths


def default_serial_device() -> str:
    return "/dev/ttyACM0"
