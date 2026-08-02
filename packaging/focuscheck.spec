# -*- mode: python ; coding: utf-8 -*-
"""Reproducible PyInstaller definition for the supervised FocusCheck app."""

from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPEC).parent.parent
datas = []
assets = ROOT / "focuscheck" / "assets"
if assets.exists():
    datas.append((str(assets), "focuscheck/assets"))
hiddenimports = collect_submodules("focuscheck")

a = Analysis([str(ROOT / "main.py")], pathex=[str(ROOT)], binaries=[], datas=datas,
             hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
             runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="FocusCheck",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
          console=False)

# Package the watchdog alongside the child so installed builds retain the
# canonical supervised startup path. The frozen supervisor launches the
# sibling FocusCheck.exe rather than recursively launching itself.
supervisor = Analysis([str(ROOT / "focuscheck_supervisor.py")], pathex=[str(ROOT)], binaries=[], datas=[],
                      hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
                      excludes=[], noarchive=False)
supervisor_pyz = PYZ(supervisor.pure)
supervisor_exe = EXE(supervisor_pyz, supervisor.scripts, supervisor.binaries, supervisor.datas, [],
                     name="FocusCheckSupervisor", debug=False, bootloader_ignore_signals=False,
                     strip=False, upx=True, console=False)
