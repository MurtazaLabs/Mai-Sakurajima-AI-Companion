"""PyInstaller build script for Mai AI daemon.

Usage:
    python scripts/build_daemon.py

Produces:
    dist/mai-daemon/  (one-folder bundle)
    dist/mai-daemon.exe  (one-file, if --onefile)

Run from project root so PyInstaller can resolve all imports.
"""
import os
import sys
import shutil
from pathlib import Path

try:
    import PyInstaller.__main__ as pyi
except ImportError:
    print("PyInstaller not installed. Run: pip install pyinstaller")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_DIR = PROJECT_ROOT / "mai-daemon.spec"

EXCLUDES = [
    "tkinter", "PyQt5", "PySide2", "PyQt6", "PySide6",
    "matplotlib", "scipy", "pandas", "notebook",
    "jupyter", "jedi", "ipython", "tensorflow", "torch",
    "uvicorn.logging", "uvicorn.loops.uvloop",
]

HIDDEN_IMPORTS = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "fastapi",
    "pydantic",
    "starlette",
    "pystray",
    "PIL",
    "plyer",
    "keyboard",
    "pyperclip",
    "yaml",
    "watchdog",
    "webview",
    "native",
    "native.tray",
    "native.app_window",
    "native.hotkeys",
    "native.notifier",
    "native.startup",
    "native.watchdog",
]

DATA_DIRS = [
    "api/static",
    "plugins",
]

COLLECT_ALL = [
    "uvicorn",
    "fastapi",
    "starlette",
    "pydantic",
    "yaml",
    "webview",
]


def main():
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    args = [
        "--name=mai-daemon",
        "--noconsole",
        "--clean",
        "--noconfirm",
    ]

    for ex in EXCLUDES:
        args.append(f"--exclude-module={ex}")
    for imp in HIDDEN_IMPORTS:
        args.append(f"--hidden-import={imp}")
    for coll in COLLECT_ALL:
        args.append(f"--collect-all={coll}")
    for data_dir in DATA_DIRS:
        src = PROJECT_ROOT / data_dir
        if src.exists():
            args.append(f"--add-data={src}{os.pathsep}{data_dir}")

    args.append(str(PROJECT_ROOT / "run_daemon.py"))

    print(f"[Build] PyInstaller args: {' '.join(args)}")
    pyi.run(args)

    print(f"[Build] Done. Binary at {DIST_DIR / 'mai-daemon' / 'run_daemon.exe'}")
    print(f"[Build] Run: {DIST_DIR / 'mai-daemon' / 'run_daemon.exe'}")


if __name__ == "__main__":
    main()
