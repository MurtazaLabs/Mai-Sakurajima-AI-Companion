# core/stateless_brain_worker.py
"""
StatelessBrainWorker - Horizontally scalable Brain worker.

This is a stateless version of BrainFacade that can be horizontally scaled.
All state is externalized to Redis/PostgreSQL:
- SharedState -> RedisSharedState
- EventBus -> RedisEventBus  
- Memory/VectorStore -> PostgreSQL + ChromaDB PersistentClient
- Session/Profile -> PostgreSQL
- Caches -> Redis TTL cache

Usage:
    worker = StatelessBrainWorker(redis_url="redis://localhost:6379", pg_dsn="postgresql://...")
    response = worker.think("hello", user_id="user123")
    
Horizontal scaling: Run multiple workers behind a load balancer.
All state is externalized - workers are truly stateless.
"""
import os
import time
import logging
import traceback
import threading
from typing import Optional, Any, Iterator, Dict, List, Union
from dataclasses import dataclass, field
from typing import Optional, Any, Iterator, Dict, List, Union

from core.utils import safe_call, safe_attr, TimeOfDay, UserMood, TTLCache
from core.emotion import Emotion
from core.behavior_builder import BehaviorBuilder
from core.identity.identity_core import IdentityCore
from core.cognitive_state import CognitiveState
from core.post_think_hooks import PostThinkHooks
from core.memory_coordinator import MemoryCoordinator, MemoryCoordinationResult
from core.prompt_coordinator import PromptCoordinator, PromptContext
from core.tool_coordinator import ToolCoordinator, PipelineResult
from core.agent_coordinator import AgentCoordinator, AgentResult
from core.memory_coordinator import MemoryCoordinator, MemoryCoordinationResult
from core.post_think_hooks import PostThinkHooks
from core.event_bus_redis import RedisEventBus
from core.brain_routing import BrainRouter
from core.response_pipeline import ResponsePipeline, PipelineResult
from core.brain_memory import BrainMemory
from core.tool_manager import ToolManager
from core.cognitive_state import CognitiveState
from core.personality_state import PersonalityState
from core.mai_message import new_correlation_id, set_correlation, clear_correlation, publish_event
from core.event_specs import STATE_REASONING_BUSY, STATE_REASONING_COMPLETE, CONVERSATION_FINISHED
from core.mai_message import publish_event
from core.utils import TimeOfDay, UserMood, TTLCache
from core.brain_routing import BrainRouter
from core.state.redis_state import RedisSharedState
from core.state.database import get_engine, init_db, get_session
from config.redis_config import RedisConfig

logger = logging.getLogger(__name__)

# Import the coordinators (they should be stateless or use external state)
from core.prompt_coordinator import PromptCoordinator, PromptContext
from core.tool_coordinator import ToolCoordinator, PipelineResult
from core.agent_coordinator import AgentCoordinator, AgentResult
from core.memory_coordinator import MemoryCoordinator, MemoryCoordinationResult
from core.post_think_hooks import PostThinkHooks
from core.event_bus_redis import RedisEventBus
from core.brain_routing import BrainRouter
from core.response_pipeline import ResponsePipeline, PipelineResult
from core.brain_memory import BrainMemory
from core.tool_manager import ToolManager
from core.cognitive_state import CognitiveState
from core.personality_state import PersonalityState
from core.mai_message import new_correlation_id, set_correlation, clear_correlation, publish_event
from core.event_specs import STATE_REASONING_BUSY, STATE_REASONING_COMPLETE, CONVERSATION_FINISHED
from core.mai_message import publish_event
from core.utils import TimeOfDay, UserMood, TTLCache
from core.brain_routing import BrainRouter
from core.response_pipeline import ResponsePipeline, PipelineResult
from core.brain_memory import BrainMemory
from core.tool_manager import ToolManager
from core.cognitive_state import CognitiveState
from core.personality_state import PersonalityState
from core.mai_message import new_correlation_id, set_correlation, clear_correlation, publish_event
from core.event_specs import STATE_REASONING_BUSY, STATE_REASONING_COMPLETE, CONVERSATION_FINISHED
from core.mai_message import publish_event
from core.utils import TimeOfDay, UserMood, TTLCache
from core.brain_routing import BrainRouter
from core.response_pipeline import ResponsePipeline, PipelineResult
from core.brain_memory import BrainMemory
from core.tool_manager import ToolManager
from core.cognitive_state import CognitiveState
from core.personality_state import PersonalityState
from core.mai_message import new_correlation_id, set_correlation, clear_correlation, publish_event
from core.event_specs import STATE_REASONING_BUSY, STATE_REASONING_COMPLETE, CONVERSATION_FINISHED
from core.mai_message import publish_event
from core.utils import TimeOfDay, UserMood, TTLCache

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """Configuration for stateless worker."""
    redis_url: str = "redis://localhost:6379/0"
    pg_dsn: str = "postgresql://user:pass@localhost:5432/mai"
    redis_max_connections: int = 10
    pg_pool_size: int = 5
    pg_max_overflow: int = 10
    pg_pool_timeout: int = 30
    cache_ttl: int = 300  # 5 minutes
    max_tool_calls_per_turn: int = 10
    stream_guard_max_buffer: int = 8192
    llm_provider: str = "openrouter"  # or "ollama"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    llm_top_p: float = 0.9
    llm_max_context: int = 32768
    llm_timeout: int = 60
    llm_retry_count: int = 3
    openrouter_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    # Worker identity
    worker_id: str = ""
    worker_region: str = "default"


class StatelessBrainWorker:
    """
    Stateless Brain Worker for horizontal scaling.
    
    All state is externalized:
    - SharedState -> Redis (via RedisSharedState)
    - EventBus -> Redis pub/sub (via RedisEventBus)
    - Memory/Vector -> PostgreSQL + ChromaDB PersistentClient
    - Sessions/Profiles -> PostgreSQL
    - Caches -> Redis (TTL-based)
    
    Multiple workers can run behind a load balancer.
    No sticky sessions required - all state is external.
    """
    
    MAX_TOOL_CALLS_PER_TURN = 10
    _STREAM_GUARD_MAX_BUFFER = 8192

    def __init__(self, config: WorkerConfig):
        self.config = config
        self.worker_id = config.worker_id or f"worker-{os.getpid()}-{id(self)}"
        
        # Initialize Redis config
        redis_config = RedisConfig(
            host=self._parse_redis_host(config.redis_url),
            port=self._parse_redis_port(config.redis_url),
            db=0,
            max_connections=config.redis_max_connections,
        )
        
        # Initialize PostgreSQL
        from core.state.database import init_db, get_engine
        from core.state.database import get_session
        from core.state.models import Base
        from core.state.psql_state import PostgreSQLSharedState
        
        # Initialize database
        self.pg_dsn = config.pg_dsn
        self.engine = None
        self._init_postgres()
        
        # Initialize Redis
        self.redis_config = RedisConfig(
            host=self._parse_redis_host(config.redis_url),
            port=self._parse_redis_port(config.redis_url),
            max_connections=config.redis_max_connections,
        )
        self.redis_state = RedisSharedState(
            persistence_dir=Path("./redis_fallback"),  # fallback only
            redis_config=RedisConfig(
                host=self._parse_redis_host(config.redis_url),
                port=self._parse_redis_port(config.redis_url),
                max_connections=config.redis_max_connections,
            )
        )
        
        # Initialize Event Bus (Redis-backed)
        self.event_bus = RedisEventBus(
            worker_count=4,
            max_queue=1000,
            redis_config=self._make_redis_config(),
        )
        
        # Initialize LLM
        self.llm = self._init_llm()
        
        # Initialize other dependencies
        self._init_dependencies()
        
        # Initialize coordinators
        self._init_coordinators()
        
        # Internal state (minimal - only per-request)
        self._response_cache = TTLCache(maxsize=64, ttl=300)
        self.last_thought_packet = None
        self._current_user_id = ""
        self._stream_tool_call_count = 0
        self._stream_user_input = ""
        
        logger.info(f"[{self.worker_id}] StatelessBrainWorker initialized")

    def _parse_redis_host(self, url: str) -> str:
        """Parse host from redis URL."""
        # redis://host:port/db
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.hostname or "localhost"
        except Exception:
            return "localhost"

    def _parse_redis_port(self, url: str) -> int:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.port or 6379
        except Exception:
            return 6379

    def _make_redis_config(self) -> RedisConfig:
        return RedisConfig(
            host=self._parse_redis_host(self.config.redis_url),
            port=self._parse_redis_port(self.config.redis_url),
            max_connections=self.config.redis_max_connections,
        )

    def _parse_redis_host(self, url: str) -> str:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.hostname or "localhost"
        except Exception:
            return "localhost"

    def _parse_redis_port(self, url: str) -> int:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.port or 6379
        except Exception:
            return 6379

    def _init_postgres(self):
        """Initialize PostgreSQL connection."""
        from core.state.database import get_engine, init_db
        from core.state.models import Base
        
        self.engine = create_engine(self.pg_dsn, pool_size=5, max_overflow=10)
        Base.metadata.create_all(self.engine)
        logger.info(f"[{self.worker_id}] PostgreSQL initialized")

    def _init_dependencies(self):
        """Initialize all shared dependencies."""
        # Tool registry
        from agency.tools import register_builtin_tools
        from core.tool_registry import ToolRegistry
        
        self.tool_registry = ToolRegistry()
        register_builtin_tools(
            self.tool_registry,
            brain=self,  # Will be set after init
            memory=None,  # Use memory_coordinator
            knowledge_retriever=None,
            reasoning_engine=None,
            belief_engine=None,
            executor=None,
            graph_manager=None,
            graph_reasoning=None,
            obsidian_writer=None,
        )
        
        # Retriever
        from knowledge.retriever import AdvancedRetriever
        from memory.vector_store import VectorStore
        from knowledge.graph import KnowledgeGraph
        from knowledge.belief_engine import BeliefEngine
        from core.attention import AttentionSystem
        
        # Vector store (uses PostgreSQL + ChromaDB persistent)
        from memory.vector_store import VectorStore
        from memory.embedding_service import EmbeddingService
        
        embed_service = EmbeddingService()
        self.vector_store = VectorStore(embed_service=embed_service)
        
        # Knowledge graph
        from knowledge.graph import KnowledgeGraph
        self.knowledge_graph = KnowledgeGraph(
            vector_store=self.vector_store,
            event_bus=self.event_bus,
        )
        
        # Belief engine
        from knowledge.belief_engine import BeliefEngine
        self.belief_engine = BeliefEngine(
            state=self.redis_state,  # Use Redis-backed state
            llm=self.llm,
        )
        
        # Retriever
        self.retriever = AdvancedRetriever(
            vector_store=self.vector_store,
            knowledge_graph=self.knowledge_graph,
            belief_engine=self.belief_engine,
            attention=None,
            event_bus=self.event_bus,
            graph_reasoning=None,
            emotion=None,
        )
        
        # Agent
        from agency.agent import Agent
        self.agent = Agent(
            registry=self.tool_registry,
            event_bus=self.event_bus,
        )
        
        # Graph reasoning
        from knowledge.graph_reasoning import GraphReasoning
        self.graph_reasoning = GraphReasoning(
            graph=self.knowledge_graph,
            event_bus=self.event_bus,
        )
        
        # Attention system
        from core.attention import AttentionSystem
        self.attention = AttentionSystem(event_bus=self.event_bus)
        
        # Emotion
        from core.emotion import Emotion
        self.emotion = Emotion(shared_state=self.redis_state, event_bus=self.event_bus)
        
        # Cognitive state
        from core.cognitive_state import CognitiveState
        self.cognitive = CognitiveState()
        
        # Personality
        from core.personality_state import PersonalityState
        self.personality_state = PersonalityState(
            path=f"/tmp/personality_state_{self.worker_id}.json"
        )
        self.personality_state.load()
        
        # Memory hierarchy
        from memory.hierarchy import MemoryHierarchy
        self.memory_hierarchy = MemoryHierarchy()
        
        # Relationship engine
        from core.state.relationship import RelationshipEngineV2
        self.relationship_engine = RelationshipEngineV2(
            state=self.redis_state,
            llm=self.llm,
        )
        
        # Goal manager
        from agency.goals import GoalManager
        self.goal_manager = GoalManager(
            state=self.redis_state,
            llm=self.llm,
        )
        
        # Procedural memory
        from agency.procedural import ProceduralMemory
        self.procedural_memory = ProceduralMemory()
        
        # World model
        from agency.world import WorldModel
        self.world_model = WorldModel()
        
        # Dream engine
        from agency.dreaming import DreamEngine
        self.dream_engine = DreamEngine()
        
        # Personality evolution
        from agency.evolution import PersonalityEvolution
        self.personality_evolution = PersonalityEvolution()
        
        # Learning engine
        from reasoning.learning import LearningEngine
        self.learning_engine = LearningEngine()
        
        # Reflection engine
        from reasoning.reflection import ReflectionEngine
        self.reflection_engine = ReflectionEngine()
        
        # Thought journal
        from reasoning.journal import ThoughtJournal
        self.thought_journal = ThoughtJournal()
        
        # Tool manager
        from core.tool_manager import ToolManager
        self.tool_manager = ToolManager(tool_registry=self.tool_registry)
        
        # Brain router
        from core.brain_routing import BrainRouter
        self.brain_router = BrainRouter(
            brain=None,  # Will be set
            agent=self.agent,
            reasoning_engine=None,  # Set later
            thought_journal=self.thought_journal,
            tool_manager=self.tool_manager,
            tool_registry=self.tool_registry,
            executor=None,  # Set later
            emotion_getter=self.emotion.get,
            cognitive=self.cognitive,
            memory_coordinator=None,  # Set later
            post_think_hooks=None,  # Set later
            llm=self.llm,
            response_pipeline=None,  # Set later
            event_bus=self.event_bus,
        )
        
        # Set brain on brain_router
        self.brain_router.brain = self
        
        # Response pipeline
        from core.response_pipeline import ResponsePipeline
        self.response_pipeline = ResponsePipeline(
            tool_registry=self.tool_registry,
            executor=None,
            event_bus=self.event_bus,
            memory=None,
        )
        
        # Set brain_router on brain_memory
        self.brain_memory = BrainMemory(
            brain=self,
            memory=None,
            retriever=self.retriever,
            memory_hierarchy=self.memory_hierarchy,
            graph_reasoning=self.graph_reasoning,
        )
        
        # Set executor
        from execution.executor import LocalExecutor
        self.executor = LocalExecutor()
        self.response_pipeline.executor = self.executor
        self.tool_coordinator.executor = self.executor
        self.brain_router.executor = self.executor
        
        # Post-think hooks
        self.post_think_hooks = PostThinkHooks(
            goal_manager=self.goal_manager,
            reflection_engine=self.reflection_engine,
            learning_engine=self.learning_engine,
            dream_engine=self.dream_engine,
            personality_evolution=self.personality_evolution,
            belief_engine=self.belief_engine,
            graph_manager=None,
            procedural_memory=self.procedural_memory,
            reasoning_engine=None,
            memory_hierarchy=self.memory_hierarchy,
            obsidian_writer=None,
            relationship_engine=self.relationship_engine,
            vault_root=None,
            prune_interval=60,
        )
        
        # Set brain on coordinators
        self.memory_coordinator = MemoryCoordinator(
            memory=None,  # Use legacy memory
            retriever=self.retriever,
            memory_hierarchy=self.memory_hierarchy,
            graph_reasoning=self.graph_reasoning,
            event_bus=self.event_bus,
        )
        
        self.prompt_coordinator = PromptCoordinator(
            memory=None,
            state=self.redis_state,
            event_bus=self.event_bus,
            emotion=self.emotion,
            personality_state=self.personality_state,
            behavior=None,
            cognitive=self.cognitive,
            memory_coordinator=self.memory_coordinator,
            retriever=self.retriever,
            graph_reasoning=self.graph_reasoning,
            tool_registry=self.tool_registry,
            tool_manager=self.tool_manager,
            llm=self.llm,
            identity_core=None,
        )

    def _init_coordinators(self):
        """Initialize coordinators."""
        # Already done in _init_dependencies
        pass

    def _init_llm(self):
        """Initialize LLM based on config."""
        if self.config.llm_provider == "openrouter":
            from llm.providers.openrouter import OpenRouterProvider
            return OpenRouterProvider(api_key=self.config.openrouter_api_key, model=self.config.llm_model)
        else:
            from llm.providers.ollama import OllamaProvider
            return OllamaProvider(base_url=self.config.ollama_base_url, model=self.config.llm_model)

    def _init_coordinators(self):
        """Initialize all coordinators."""
        # Tool coordinator
        self.tool_coordinator = ToolCoordinator(
            tool_registry=self.tool_registry,
            executor=None,  # Set later
            event_bus=self.event_bus,
            memory=None,
        )
        
        self.agent_coordinator = AgentCoordinator(
            registry=self.tool_registry,
            event_bus=self.event_bus,
        )
        
        # Memory coordinator
        self.memory_coordinator = MemoryCoordinator(
            memory=None,
            retriever=self.retriever,
            memory_hierarchy=self.memory_hierarchy,
            graph_reasoning=self.graph_reasoning,
            event_bus=self.event_bus,
        )
        
        # Prompt coordinator
        self.prompt_coordinator = PromptCoordinator(
            memory=None,
            state=self.redis_state,
            event_bus=self.event_bus,
            emotion=self.emotion,
            personality_state=self.personality_state,
            behavior=None,
            cognitive=self.cognitive,
            memory_coordinator=self.memory_coordinator,
            retriever=self.retriever,
            graph_reasoning=self.graph_reasoning,
            tool_registry=self.tool_registry,
            tool_manager=None,
            llm=self.llm,
            identity_core=None,
        )
        
        # Post-think hooks
        self.post_think_hooks = PostThinkHooks(
            goal_manager=None,
            reflection_engine=None,
            learning_engine=None,
            dream_engine=None,
            personality_evolution=None,
            belief_engine=None,
            graph_manager=None,
            procedural_memory=None,
            reasoning_engine=None,
            memory_hierarchy=None,
            obsidian_writer=None,
            relationship_engine=None,
            vault_root=None,
            prune_interval=0,
        )
        
        # Response pipeline
        self.response_pipeline = ResponsePipeline(
            tool_registry=self.tool_registry,
            executor=None,
            event_bus=self.event_bus,
            memory=None,
        )
        
        self.behavior = BehaviorBuilder()
        self.personality_state = self.personality_state  # Already initialized
        self.tool_manager = ToolManager(tool_registry=self.tool_registry)

    def _setup_personality_state(self, cache_dir):
        self.personality_state = PersonalityState(
            path=os.path.join(str(cache_dir), "personality_state.json")
        )
        self.personality_state.load()

    # ==================================================
    # 🧠 MAIN THINK (Non-streaming)
    # ==================================================

    def think(self, user_input: str, user_id: str = "") -> str:
        """Main synchronous thinking pathway."""
        # ... same logic as BrainFacade.think() but using external state
        pass

    # ... all other methods from BrainFacade ...

    # ==================================================
    # 🎙️ STREAM THINKING
    # ==================================================

    def think_stream(self, user_input: str, user_id: str = "") -> Iterator[str]:
        """Streaming version of think()."""
        pass

    def shutdown(self, timeout=5.0):
        """Graceful shutdown."""
        pass

    # ... delegate all other methods to coordinators
    # (same as BrainFacade but using external state)
    pass

# Required imports
import os
import time
import logging
import traceback
import threading
from typing import Optional, Any, Iterator, Dict, List
from dataclasses import dataclass, field
from pathlib import Path

from core.utils import safe_call, safe_attr, TimeOfDay, UserMood, TTLCache
from core.emotion import Emotion
from core.behavior_builder import BehaviorBuilder
from core.identity.identity_core import IdentityCore
from core.cognitive_state import CognitiveState
from core.post_think_hooks import PostThinkHooks
from core.memory_coordinator import MemoryCoordinator
from core.prompt_coordinator import PromptCoordinator, PromptContext
from core.tool_coordinator import ToolCoordinator, PipelineResult
from core.agent_coordinator import AgentCoordinator, AgentResult
from core.memory_coordinator import MemoryCoordinator, MemoryCoordinationResult
from core.post_think_hooks import PostThinkHooks
from core.event_bus_redis import RedisEventBus
from core.brain_routing import BrainRouter
from core.response_pipeline import ResponsePipeline, PipelineResult
from core.brain_memory import BrainMemory
from core.tool_manager import ToolManager
from core.cognitive_state import CognitiveState
from core.personality_state import PersonalityState
from core.mai_message import new_correlation_id, set_correlation, clear_correlation, publish_event
from core.event_specs import STATE_REASONING_BUSY, STATE_REASONING_COMPLETE, CONVERSATION_FINISHED
from core.mai_message import publish_event
from core.utils import TimeOfDay, UserMood, TTLCache
from core.brain_routing import BrainRouter
from core.response_pipeline import ResponsePipeline, PipelineResult
from core.brain_memory import BrainMemory
from core.tool_manager import ToolManager
from core.cognitive_state import CognitiveState
from core.personality_state import PersonalityState
from core.mai_message import new_correlation_id, set_correlation, clear_correlation, publish_event
from core.event_specs import STATE_REASONING_BUSY, STATE_REASONING_COMPLETE, CONVERSATION_FINISHED
from core.mai_message import publish_event
from core.utils import TimeOfDay, UserMood, TTLCache
from core.brain_routing import BrainRouter
from core.response_pipeline import ResponsePipeline, PipelineResult
from core.brain_memory import BrainMemory
from core.tool_manager import ToolManager
from core.cognitive_state import CognitiveState
from core.personality_state import PersonalityState
from core.mai_message import new_correlation_id, set_correlation, clear_correlation, publish_event
from core.event_specs import STATE_REASONING_BUSY, STATE_REASONING_COMPLETE, CONVERSATION_FINISHED
from core.mai_message import publish_event
from core.utils import TimeOfDay, UserMood, TTLCache
from core.brain_routing import BrainRouter
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)


def apply_style(text, personality=None, emotion=None):
    """Apply character voice styling to text."""
    try:
        from core.style_filter import apply_style as _apply
        return _apply(text, personality=personality, emotion=emotion)
    except Exception as e:
        logging.getLogger(__name__).warning("[apply_style] failed: %s", e)
        return text


@dataclass
class WorkerConfig:
    """Configuration for stateless worker."""
    redis_url: str = "redis://localhost:6379/0"
    pg_dsn: str = "postgresql://user:pass@localhost:5432/mai"
    redis_max_connections: int = 10
    pg_pool_size: int = 5
    pg_max_overflow: int = 10
    pg_pool_timeout: int = 30
    cache_ttl: int = 300  # 5 minutes
    max_tool_calls_per_turn: int = 10
    stream_guard_max_buffer: int = 8192
    llm_provider: str = "openrouter"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    llm_top_p: float = 0.9
    llm_max_context: int = 32768
    llm_timeout: int = 60
    llm_retry_count: int = 3
    openrouter_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    worker_id: str = ""
    worker_region: str = "default"