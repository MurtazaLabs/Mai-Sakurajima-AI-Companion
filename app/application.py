import logging

logger = logging.getLogger("Mai")


class AIApplication:

    def __init__(self):
        self.boot_start = 0.0
        self.event_bus = None
        self.health_registry = None
        self.shared_state = None
        self.llm = None
        self.relationship_engine = None
        self.knowledge_graph = None
        self.brain_graph = None
        self.belief_engine = None
        self.attention_system = None
        self.memory_hierarchy = None
        self.raw_memory = None
        self.memory_pipeline = None
        self.memory = None
        self.vector_store = None
        self.graph_manager = None
        self.cognitive_graph = None
        self.graph_reflection = None
        self.graph_reasoning = None
        self.obsidian_writer = None
        self.retriever = None
        self.thought_journal = None
        self.reasoning_engine = None
        self.reflection_engine = None
        self.learning_engine = None
        self.tool_registry = None
        self.agent = None
        self.goal_manager = None
        self.procedural_memory = None
        self.world_model = None
        self.dream_engine = None
        self.executor = None
        self.safe_executor = None
        self.brain = None
        self.personality_evolution = None
        self.tts = None
        self.voice = None
        self.stt = None
        self.adaptive_noise = None
        self.full_aec = None
        self.emotion_detector = None
        self.diarization = None
        self.voice_manager = None
        self.wake = None
        self.speaker_manager = None
        self.per_person_relationship = None
        self.kernel = None
        self.knowledge_builder = None
        self.plugin_loader = None
        self.hook_registry = None
        self.write_journal = None
        self.event_inspector = None
        self.directory_watcher = None
        self.identity = None
        self.needs_engine = None
        self.model_lifecycle = None

        # Internal — cleared after build
        self._extractor = None
        self._consolidation = None

        # Service registry for debugging and introspection
        self._services = {}

        # System Orchestrator (Phase 3) — created lazily on first lifecycle call
        self.orchestrator = None

    def register(self, name, obj):
        self._services[name] = obj

    def get(self, name):
        return self._services.get(name)

    @property
    def services(self):
        return dict(self._services)

    def health(self):
        if self.health_registry is None:
            return {"status": "unavailable", "components": {}, "summary": {"total": 0, "ok": 0, "warn": 0, "error": 0, "stalled": 0}}
        return self.health_registry.stats()

    SERVICE_ATTRS = [
        "event_bus", "health_registry", "shared_state", "llm", "relationship_engine",
        "knowledge_graph", "brain_graph", "belief_engine", "attention_system",
        "memory_hierarchy", "raw_memory", "memory_pipeline", "memory", "vector_store",
        "retriever", "graph_manager", "cognitive_graph", "graph_reflection",
        "graph_reasoning", "obsidian_writer", "thought_journal", "reasoning_engine",
        "reflection_engine", "learning_engine", "tool_registry", "agent", "goal_manager",
        "procedural_memory", "world_model", "dream_engine", "executor", "safe_executor",
        "brain", "personality_evolution", "tts", "voice", "stt", "adaptive_noise",
        "full_aec", "emotion_detector", "diarization", "voice_manager", "wake",
        "speaker_manager", "per_person_relationship", "kernel", "knowledge_builder",
        "plugin_loader", "hook_registry", "write_journal", "event_inspector",
        "directory_watcher", "identity", "model_lifecycle",
    ]

    @property
    def service_metadata(self):
        metas = []
        for attr_name in self.SERVICE_ATTRS:
            val = getattr(self, attr_name, None)
            if val is not None and hasattr(val, "_service_meta"):
                metas.append(val._service_meta)
        return sorted(metas, key=lambda m: m.layer)

    def _get_orchestrator(self):
        if self.orchestrator is None:
            from app.orchestrator import SystemOrchestrator
            journal_dir = None
            try:
                from config.paths import LOG_DIR
                journal_dir = LOG_DIR / "orchestrator"
            except Exception:
                pass
            self.orchestrator = SystemOrchestrator(app=self, journal_dir=journal_dir)
            self.orchestrator.register_app_services()
        return self.orchestrator

    def initialize(self):
        return self._get_orchestrator().initialize()

    def start(self):
        return self._get_orchestrator().start()

    def wait(self):
        return self._get_orchestrator().wait()

    def shutdown(self):
        return self._get_orchestrator().shutdown()
