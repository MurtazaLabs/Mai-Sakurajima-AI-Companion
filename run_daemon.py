"""Mai AI desktop entry point — launches the daemon with a desktop window.

Usage:
    python run_daemon.py                    # daemon + desktop window (close hides to tray)
    python run_daemon.py --no-window        # background only (tray + browser)
    pythonw run_daemon.py                   # same, no console (used by shortcut/startup)
    python run_daemon.py --install-startup  # register launch-at-login, then exit
    python run_daemon.py --uninstall-startup  # remove launch-at-login, then exit
"""
import argparse
import socket
import sys


def _port_in_use(host: str, port: int) -> bool:
    """True if something is already listening (Mai likely already running)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Mai AI desktop daemon")
    parser.add_argument("--no-window", action="store_true",
                        help="Run without the desktop window (tray only)")
    parser.add_argument("--install-startup", action="store_true",
                        help="Register Mai to launch at Windows login, then exit")
    parser.add_argument("--uninstall-startup", action="store_true",
                        help="Remove Mai from Windows login, then exit")
    args = parser.parse_args()

    if args.install_startup or args.uninstall_startup:
        from native.startup import StartupManager
        sm = StartupManager()
        ok = sm.register() if args.install_startup else sm.unregister()
        print("OK" if ok else "FAILED")
        return 0 if ok else 1

    from app.config_loader import API_PORT
    host = "127.0.0.1"  # the desktop window always targets loopback
    port = int(API_PORT or 8000)

    if _port_in_use(host, port):
        # Already running — focus it in the browser instead of a second boot
        import webbrowser
        webbrowser.open(f"http://{host}:{port}/desktop")
        return 0

    from run import run_daemon_mode
    run_daemon_mode(window=not args.no_window)
    return 0


if __name__ == "__main__":
    sys.exit(main())
