import logging

from core.plugin_system import Plugin

logger = logging.getLogger("Mai.Plugin.Example")


class ExamplePlugin(Plugin):

    def __init__(self):
        super().__init__(name="ExamplePlugin", version="1.0.0", description="Example plugin that hooks into chat responses")

    def on_load(self, hooks, brain, event_bus):
        hooks.register("post_response", self.on_post_response, priority=0)
        hooks.register("pre_chat", self.on_pre_chat, priority=0)
        logger.info("Loaded — hooks registered")

    def on_unload(self):
        logger.info("Unloaded")

    def on_pre_chat(self, user_input, **kwargs):
        logger.info("Pre-chat: %s", user_input[:50])

    def on_post_response(self, message, response):
        logger.info("Post-response: %d chars", len(response))
