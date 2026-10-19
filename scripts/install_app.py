"""Install the Mai desktop app: desktop shortcut + optional launch-at-login.

Usage:
    python scripts/install_app.py              # create the Desktop shortcut
    python scripts/install_app.py --startup    # shortcut + launch at login
    python scripts/install_app.py --remove     # remove shortcut
    python scripts/install_app.py --remove --uninstall-startup
"""
import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SHORTCUT_PATH = Path.home() / "Desktop" / "Mai AI.lnk"


def _python_bin() -> Path:
    python = Path(sys.executable)
    pythonw = python.parent / "pythonw.exe"
    return pythonw if pythonw.exists() else python


def _has_mai_deps(python_bin: Path) -> bool:
    """True if this interpreter can see Mai's core runtime stack."""
    probe = (
        "import importlib.util as u, sys; "
        "sys.exit(0 if all(u.find_spec(m) for m in "
        "['fastapi', 'pystray', 'kokoro', 'webview']) else 1)"
    )
    try:
        r = subprocess.run([str(python_bin), "-c", probe],
                           capture_output=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def create_shortcut(python_bin: Path) -> bool:
    try:
        import win32com.client
    except ImportError:
        print("pywin32 is required: pip install pywin32")
        return False
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        sc = shell.CreateShortCut(str(SHORTCUT_PATH))
        sc.Targetpath = str(python_bin)
        sc.Arguments = f'"{PROJECT_ROOT / "run_daemon.py"}"'
        sc.WorkingDirectory = str(PROJECT_ROOT)
        sc.Description = "Mai AI desktop companion"
        sc.save()
        print(f"Shortcut created: {SHORTCUT_PATH}")
        return True
    except Exception as e:
        print(f"Shortcut failed: {e}")
        return False


def remove_shortcut() -> bool:
    if SHORTCUT_PATH.exists():
        SHORTCUT_PATH.unlink()
        print(f"Shortcut removed: {SHORTCUT_PATH}")
        return True
    print("No shortcut found")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Mai desktop app")
    parser.add_argument("--startup", action="store_true",
                        help="Also launch Mai at Windows login")
    parser.add_argument("--remove", action="store_true",
                        help="Remove the desktop shortcut")
    parser.add_argument("--uninstall-startup", action="store_true",
                        help="Remove Mai from Windows login")
    parser.add_argument("--force", action="store_true",
                        help="Install even if the interpreter is missing Mai dependencies")
    args = parser.parse_args()

    python_bin = _python_bin()
    if not args.remove and not _has_mai_deps(python_bin):
        print(f"ERROR: {python_bin} is missing Mai's runtime packages")
        print("(need fastapi, pystray, kokoro, webview - this is usually base")
        print(" Python instead of the mai_env environment).")
        print("Run this script from the mai_env environment, e.g.:")
        print(r"  E:\Mai_ai\mai_env\Scripts\python.exe scripts\install_app.py --startup")
        if not args.force:
            return 2
        print("--force: continuing anyway")

    print(f"Interpreter: {python_bin}")

    ok = True
    if args.remove:
        ok = remove_shortcut()
    else:
        ok = create_shortcut(python_bin)

    if args.uninstall_startup:
        from native.startup import StartupManager
        ok = StartupManager().unregister() and ok
    elif args.startup:
        from native.startup import StartupManager
        sm = StartupManager()
        ok = sm.register() and ok
        if ok:
            print(f"Launch-at-login registered: {sm.executable_path}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
