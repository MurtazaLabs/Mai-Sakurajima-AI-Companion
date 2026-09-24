import logging

from core.plugin_system import Plugin

logger = logging.getLogger("Mai.Plugin.SystemMonitor")


class SystemMonitorPlugin(Plugin):

    def __init__(self):
        super().__init__(
            name="SystemMonitorPlugin",
            version="1.0.0",
            description="Reports CPU, memory, and disk usage",
        )

    def on_load(self, hooks, brain, event_bus):
        hooks.register("pre_chat", self.on_pre_chat, priority=5)
        logger.info("Loaded")

    def on_unload(self):
        logger.info("Unloaded")

    def on_pre_chat(self, user_input, **kwargs):
        text = user_input.lower().strip()
        if text in ("system", "sysinfo", "system status", "status"):
            return self._report()
        return None

    def _report(self):
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(".")
        return (
            f"System status:\n"
            f"  CPU:    {cpu:.1f}%\n"
            f"  Memory: {mem.percent:.1f}% ({mem.used // 1048576}MB / {mem.total // 1048576}MB)\n"
            f"  Disk:   {disk.percent:.1f}% ({disk.used // 1073741824}GB / {disk.total // 1073741824}GB)"
        )
