"""Desktop application shell tests (run_daemon, app window, tray, startup)."""
import socket


class TestPortProbe:
    def test_port_in_use_true_when_bound(self):
        from run_daemon import _port_in_use
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
        try:
            assert _port_in_use("127.0.0.1", port) is True
        finally:
            s.close()

    def test_port_in_use_false_on_free_port(self):
        from run_daemon import _port_in_use
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        assert _port_in_use("127.0.0.1", port) is False


class TestAppWindow:
    def test_url_points_at_desktop_page(self):
        from native.app_window import AppWindow
        w = AppWindow(host="127.0.0.1", port=8000)
        assert w.url == "http://127.0.0.1:8000/desktop"

    def test_ssl_scheme(self):
        from native.app_window import AppWindow
        assert AppWindow(ssl=True).url.startswith("https://")

    def test_unavailable_without_pywebview(self, monkeypatch):
        import native.app_window as aw
        monkeypatch.setattr(aw, "_HAS_WEBVIEW", False)
        assert aw.AppWindow().start() is False

    def test_closing_handler_hides_and_cancels(self, monkeypatch):
        import native.app_window as aw
        calls = []

        class FakeWin:
            def hide(self):
                calls.append("hide")

        w = aw.AppWindow()
        w._window = FakeWin()
        result = w._on_closing()
        assert calls == ["hide"]
        assert result is False  # destroy cancelled


class TestTrayOpen:
    def test_open_prefers_callback(self, monkeypatch):
        import native.tray as tray_mod
        called = []
        monkeypatch.setattr(tray_mod.webbrowser, "open",
                            lambda *a, **k: called.append("browser"))
        t = tray_mod.TrayDaemon(on_open=lambda: called.append("window"))
        t._action_open()
        assert called == ["window"]

    def test_open_falls_back_to_browser(self, monkeypatch):
        import native.tray as tray_mod
        called = []
        monkeypatch.setattr(tray_mod.webbrowser, "open",
                            lambda url: called.append(url))
        t = tray_mod.TrayDaemon(host="127.0.0.1", port=9000)
        t._action_open()
        assert called and "9000" in called[0]

    def test_callback_failure_falls_back_to_browser(self, monkeypatch):
        import native.tray as tray_mod
        called = []
        monkeypatch.setattr(tray_mod.webbrowser, "open",
                            lambda url: called.append(url))

        def boom():
            raise RuntimeError("window gone")

        t = tray_mod.TrayDaemon(host="127.0.0.1", port=9001, on_open=boom)
        t._action_open()
        assert called and "9001" in called[0]


class TestStartup:
    def test_default_exe_references_run_daemon(self):
        from native.startup import StartupManager
        exe = StartupManager._default_exe()
        assert "run_daemon.py" in exe

    def test_default_exe_prefers_pythonw(self):
        import sys
        from pathlib import Path

        from native.startup import StartupManager
        pythonw = Path(sys.executable).parent / "pythonw.exe"
        exe = StartupManager._default_exe()
        if pythonw.exists():
            assert "pythonw" in exe


class TestMaiAPIWiring:
    def test_app_and_kernel_attributes_exist(self):
        from api.server import MaiAPI
        m = MaiAPI()
        assert m.app is None
        assert m.kernel is None

    def test_bootstrap_stores_kernel(self, monkeypatch):
        from api.server import MaiAPI

        class FakeApp:
            kernel = "kernel-obj"

        monkeypatch.setattr("run.bootstrap_system",
                            lambda: {"app": FakeApp()})
        m = MaiAPI()
        ok = m.bootstrap()
        assert ok is True
        assert m.app is not None
        assert m.kernel == "kernel-obj"
