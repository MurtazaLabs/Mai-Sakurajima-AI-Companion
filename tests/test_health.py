import time

from observability.health import HealthRegistry


class TestHealthRegistry:

    def make(self):
        return HealthRegistry(stall_timeout=0.1)

    def test_register_and_status(self):
        hr = self.make()
        hr.register("test_component")
        assert "test_component" in hr
        status = hr.status("test_component")
        assert status["status"] == "ok"

    def test_unknown_status(self):
        hr = self.make()
        status = hr.status("nonexistent")
        assert status["status"] == "unknown"

    def test_heartbeat_updates_timestamp(self):
        hr = self.make()
        hr.register("comp")
        before = hr.status("comp")["last_heartbeat"]
        time.sleep(0.01)
        hr.heartbeat("comp")
        after = hr.status("comp")["last_heartbeat"]
        assert after > before

    def test_report_error(self):
        hr = self.make()
        hr.register("comp")
        hr.report_error("comp", "something broke")
        status = hr.status("comp")
        assert status["status"] == "error"
        assert status["error_count"] == 1

    def test_resolve_clears_error(self):
        hr = self.make()
        hr.register("comp")
        hr.report_error("comp", "boom")
        hr.resolve("comp")
        assert hr.status("comp")["status"] == "ok"

    def test_stalled_detected(self):
        hr = self.make()
        hr.register("comp")
        hr.heartbeat("comp")
        hr.heartbeat("comp")
        time.sleep(0.15)
        hr.check_stalled()
        assert hr.status("comp")["status"] == "stalled"

    def test_single_heartbeat_never_stalled(self):
        hr = self.make()
        hr.register("comp")
        hr.heartbeat("comp")
        time.sleep(0.15)
        hr.check_stalled()
        assert hr.status("comp")["status"] == "ok"

    def test_heartbeat_count_increments(self):
        hr = self.make()
        hr.heartbeat("comp")
        hr.heartbeat("comp")
        assert hr._components["comp"]["heartbeat_count"] == 2

    def test_stats_summary(self):
        hr = self.make()
        hr.register("a")
        hr.register("b")
        hr.report_error("b", "err")
        hr.register("c")
        hr.check_stalled()
        stats = hr.stats()
        assert stats["summary"]["total"] == 3
        assert stats["summary"]["ok"] >= 1
        assert stats["summary"]["error"] == 1

    def test_unregister_removes(self):
        hr = self.make()
        hr.register("comp")
        assert "comp" in hr
        hr.unregister("comp")
        assert "comp" not in hr

    def test_heartbeat_auto_registers(self):
        hr = self.make()
        hr.heartbeat("auto_comp")
        assert "auto_comp" in hr
        assert hr.status("auto_comp")["status"] == "ok"

    def test_error_publishes_event(self):
        from unittest.mock import MagicMock
        bus = MagicMock()
        hr = HealthRegistry(event_bus=bus, stall_timeout=0.1)
        hr.register("comp")
        hr.report_error("comp", "fail")
        bus.publish_message.assert_called_once()
        msg = bus.publish_message.call_args[0][0]
        assert msg.type == "data.health.error"
        assert msg.payload["name"] == "comp"

    def test_error_capped_at_50(self):
        hr = self.make()
        hr.register("comp")
        for i in range(55):
            hr.report_error("comp", f"error_{i}")
        status = hr.status("comp")
        assert status["error_count"] == 55
        assert len(hr._components["comp"]["errors"]) == 50

    def test_heartbeat_all_refreshes_stale_components(self):
        hr = self.make()
        hr.register("a")
        hr.register("b")
        hr.heartbeat("a")
        hr.heartbeat("a")
        hr.report_error("b", "boom")
        time.sleep(0.15)
        hr.check_stalled()
        assert hr.status("a")["status"] == "stalled"
        hr.heartbeat_all()
        assert hr.status("a")["status"] == "ok"
        assert hr.status("b")["status"] == "ok"
        assert hr.status("a")["last_heartbeat"] == hr.status("b")["last_heartbeat"]

    def test_heartbeat_all_no_components_noop(self):
        hr = self.make()
        hr.heartbeat_all()
        assert hr.status("missing")["status"] == "unknown"
