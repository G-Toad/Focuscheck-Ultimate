"""Build and exercise a current-source package entirely in disposable paths."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _powershell() -> str:
    executable = shutil.which("powershell") or shutil.which("pwsh")
    if not executable:
        raise RuntimeError("PowerShell is required for package build verification")
    return executable


def _run(command: list[str], *, timeout: int) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}\n{output}")
    return output


def main() -> int:
    powershell = _powershell()
    with tempfile.TemporaryDirectory(prefix="focuscheck-package-build-") as temp_dir:
        temp = Path(temp_dir)
        package = temp / "package"
        install = temp / "install"
        data = temp / "data"

        build_output = _run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "tools/build_package.ps1"),
                "-OutputDir",
                str(package),
            ],
            timeout=150,
        )
        required = (package / "FocusCheck.exe", package / "FocusCheckSupervisor.exe")
        missing = [str(path.name) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(f"package build omitted required artifacts: {', '.join(missing)}")

        promotion_output = _run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "tools/promote_package.ps1"),
                "-PackageDir",
                str(package),
                "-InstallDir",
                str(install),
                "-Version",
                "verification",
            ],
            timeout=30,
        )
        validation_output = _run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "tools/validate_package.ps1"),
                "-PackageDir",
                str(install),
            ],
            timeout=30,
        )
        supervisor_output = _run(
            [
                sys.executable,
                str(ROOT / "tools/packaged_supervisor_selftest.py"),
                "--package-dir",
                str(install),
                "--data-dir",
                str(data),
                "--timeout",
                "35",
            ],
            timeout=55,
        )
        print(build_output, end="")
        print(promotion_output, end="")
        print(validation_output, end="")
        print(supervisor_output, end="")
        print(f"package_build_selftest_passed package={package} install={install}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"package_build_selftest_failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
