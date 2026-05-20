#!/usr/bin/env python3
"""Build a Windows executable for Mo's Void using PyInstaller."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
ENTRY_FILE = REPO_ROOT / "mos_void.py"


def main() -> int:
    pyinstaller = shutil.which("pyinstaller")
    if pyinstaller is None:
        print("PyInstaller is not installed.")
        print("Install it with: python -m pip install pyinstaller")
        return 1

    command = [
        pyinstaller,
        "--onefile",
        "--name",
        "mos-void",
        str(ENTRY_FILE),
    ]
    print("Running:", " ".join(command))
    result = subprocess.run(command, cwd=REPO_ROOT, check=False)

    if result.returncode != 0:
        return result.returncode

    exe_path = REPO_ROOT / "dist" / "mos-void.exe"
    print(f"Build complete. Expected executable path: {exe_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
