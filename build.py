"""
Build a single-file, windowed executable using PyInstaller.

Usage:
    python build.py

Output:
    dist/InvisibleChat.exe
"""

import os
import subprocess
import sys
from pathlib import Path


def build_executable():
    here = Path(__file__).parent
    src_main = here / "src" / "main.py"
    name = "InvisibleChat"

    cmd = [
       sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", name,
    "--paths", str(here / "src"),   
    str(src_main),
    ]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)


if __name__ == "__main__":
    build_executable()
