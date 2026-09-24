import logging

logger = logging.getLogger(__name__)


class ToolManager:

    def __init__(self, tool_registry=None):
        self.tool_registry = tool_registry

    def setup(self, brain=None, memory=None, executor=None,
              reasoning_engine=None, belief_engine=None,
              knowledge_retriever=None, graph_manager=None,
              graph_reasoning=None, obsidian_writer=None):
        if self.tool_registry is None:
            return
        try:
            from agency.tools import register_builtin_tools
            register_builtin_tools(
                registry=self.tool_registry,
                brain=brain,
                memory=memory if memory and hasattr(memory, 'store') else None,
                executor=executor if executor and hasattr(executor, 'run') else None,
                reasoning_engine=reasoning_engine,
                belief_engine=belief_engine,
                knowledge_retriever=knowledge_retriever,
                graph_manager=graph_manager,
                graph_reasoning=graph_reasoning,
                obsidian_writer=obsidian_writer,
            )
        except Exception as e:
            logger.warning("[ToolManager] Setup skipped: %s", e)

    def definitions_for_prompt(self):
        if self.tool_registry is None:
            return None
        try:
            return self.tool_registry.tool_definitions_for_llm()
        except Exception as e:
            logger.warning("ToolManager definitions_for_prompt failed: %s", e)
            return None

    def validate(self, action):
        if self.tool_registry is None:
            return False
        try:
            tool = self.tool_registry.get(action.get("type", ""))
            return tool is not None
        except Exception as e:
            logger.warning("ToolManager validate failed: %s", e)
            return False

    def is_available(self):
        return self.tool_registry is not None
