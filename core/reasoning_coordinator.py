import logging

logger = logging.getLogger(__name__)


class ReasoningCoordinator:

    def __init__(self, reasoning_engine=None, thought_journal=None, agent=None):
        self.reasoning_engine = reasoning_engine
        self.thought_journal = thought_journal
        self.agent = agent

    def is_analytical(self, user_input):
        if not self.reasoning_engine:
            return False
        t = user_input.lower().strip()
        analytical_starters = ("why", "how", "what do you think", "analyze",
                               "explain", "should i", "is it a good idea")
        for starter in analytical_starters:
            if t.startswith(starter):
                return True
        return False

    def is_complex(self, user_input):
        if not self.agent and not self.reasoning_engine:
            return False
        t = user_input.lower().strip()
        complex_patterns = ["research", "investigate", "find out", "look into",
                            "multi-step", "do several", "in order to"]
        for pat in complex_patterns:
            if pat in t:
                return True
        return False

    def reason(self, query):
        if not self.reasoning_engine:
            return None
        try:
            trace = self.reasoning_engine.reason(query)
            if trace and trace.conclusion:
                logger.info("[REASONING] confidence=%.2f, steps=%d", trace.confidence, len(trace.reasoning_steps))
                if self.thought_journal:
                    self.thought_journal.store(trace.to_dict())
                return trace
        except Exception as e:
            logger.error("[REASONING ERROR] %s", e)
        return None

    def delegate(self, user_input):
        if not self.agent:
            return None
        try:
            result = self.agent.run(user_input)
            if result and result.get("success"):
                conclusion = result.get("result", {})
                if isinstance(conclusion, dict):
                    return conclusion.get("conclusion", str(conclusion))
                return str(conclusion)
        except Exception as e:
            logger.error("[AGENT ERROR] %s", e)
        return None
