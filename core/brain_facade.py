# core/brain_facade.py
"""
BrainFacade - Thin orchestration layer over specialized coordinators.

This is the new thin Brain interface that delegates to specialized coordinators:
- PromptCoordinator: system prompt construction
- ToolCoordinator: tool execution & validation
- AgentCoordinator: multi-step agent task execution
- MemoryCoordinator: memory context assembly & storage

The BrainFacade is <300 lines and only orchestrates - no business logic.
"""
import time
import logging
import threading
from typing import Optional, Any, Iterator, Dict, List

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
from core.event_bus import EventBus
from core.brain_routing import BrainRouter
from core.response_pipeline import ResponsePipeline
from core.brain_memory import BrainMemory
from core.tool_manager import ToolManager
from core.cognitive_state import CognitiveState
from core.personality_state import PersonalityState
from core.mai_message import new_correlation_id, set_correlation, clear_correlation, publish_event
from core.event_specs import STATE_REASONING_BUSY, STATE_REASONING_COMPLETE, CONVERSATION_FINISHED
from core.mai_message import publish_event
from core.utils import TimeOfDay, UserMood

logger = logging.getLogger(__name__)


class BrainFacade:
    """
    Thin facade orchestrating specialized coordinators.
    
    This is the public Brain interface - ~300 lines, no business logic,
    only orchestration of specialized coordinators.
    """

    MAX_TOOL_CALLS_PER_TURN = 10
    _STREAM_GUARD_MAX_BUFFER = 8192

    def __init__(
        self,
        llm,
        memory,
        executor,
        state,
        deps: Optional[Any] = None,
        **kwargs,
    ):
        # Backward-compat: accept old-style keyword args
        if deps is None:
            deps = type('Deps', (), {k: v for k, v in kwargs.items() 
                if k in ['event_bus', 'cognitive_state', 'tool_registry', 'agent', 
                         'retriever', 'reasoning_engine', 'thought_journal',
                         'reflection_engine', 'learning_engine', 'goal_manager',
                         'world_model', 'procedural_memory', 'dream_engine',
                         'personality_evolution', 'dashboard', 'graph_manager',
                         'graph_reflection', 'obsidian_writer', 'memory_hierarchy',
                         'relationship_engine', 'session_manager']})()

        self.llm = llm
        self.memory = memory
        self.executor = executor
        self.state = state

        self.event_bus = deps.event_bus or EventBus()
        self.cognitive = deps.cognitive_state or CognitiveState()
        
        self.session_manager = deps.session_manager
        self._current_user_id = ""

        # Initialize coordinators
        self.tool_registry = deps.tool_registry
        self.agent = deps.agent
        self.retriever = deps.retriever
        self.reasoning_engine = deps.reasoning_engine
        self.thought_journal = deps.thought_journal
        self.reflection_engine = deps.reflection_engine
        self.learning_engine = deps.learning_engine
        self.goal_manager = deps.goal_manager
        self.procedural_memory = deps.procedural_memory
        self.world_model = deps.world_model
        self.dream_engine = deps.dream_engine
        self.personality_evolution = deps.personality_evolution
        self.dashboard = deps.dashboard
        self.graph_manager = deps.graph_manager
        self.graph_reflection = deps.graph_reflection
        self.obsidian_writer = deps.obsidian_writer
        self.memory_hierarchy = deps.memory_hierarchy
        self.relationship_engine = deps.relationship_engine

        # Initialize coordinators
        self._init_coordinators()

        # Internal state
        self._response_cache = TTLCache(maxsize=64, ttl=30.0)
        self.last_thought_packet = None
        self.needs_engine = getattr(deps, "needs_engine", None)
        self._current_user_id = ""
        self._stream_tool_call_count = 0
        self._stream_user_input = ""

    def _init_coordinators(self):
        """Initialize all coordinators with shared dependencies."""
        # Core services
        self.event_bus = self.event_bus or EventBus()
        self.cognitive = self.cognitive or CognitiveState()
        self.emotion = Emotion(shared_state=self.state, event_bus=self.event_bus)
        self.brain_memory = BrainMemory(
            brain=self, memory=self.memory, retriever=self.retriever,
            memory_hierarchy=self.memory_hierarchy, graph_reasoning=None
        )
        self.prompt_orchestrator = PromptOrchestrator(self)  # Legacy compatibility
        
        # New coordinators
        self.memory_coordinator = MemoryCoordinator(
            memory=self.memory,
            retriever=self.retriever,
            memory_hierarchy=self.memory_hierarchy,
            graph_reasoning=None,
            event_bus=self.event_bus,
        )
        
        self.prompt_coordinator = PromptCoordinator(
            memory=self.memory,
            state=self.state,
            event_bus=self.event_bus,
            emotion=self.emotion,
            personality_state=None,  # Set later
            behavior=None,
            cognitive=self.cognitive,
            memory_coordinator=self.memory_coordinator,
            retriever=self.retriever,
            graph_reasoning=None,
            tool_registry=self.tool_registry,
            tool_manager=None,
            llm=self.llm,
            identity_core=None,
        )
        
        self.tool_coordinator = ToolCoordinator(
            tool_registry=self.tool_registry,
            executor=None,  # Set later
            event_bus=self.event_bus,
            memory=self.memory,
        )
        
        self.agent_coordinator = AgentCoordinator(
            registry=self.tool_registry,
            event_bus=self.event_bus,
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
        
        self.response_pipeline = ResponsePipeline(
            tool_registry=self.tool_registry,
            executor=None,
            event_bus=self.event_bus,
            memory=self.memory,
        )
        
        self.behavior = BehaviorBuilder()
        self.personality_state = PersonalityState(
            path=None  # Set later
        )
        self.tool_manager = ToolManager(tool_registry=self.tool_registry)

    def _setup_personality_state(self, cache_dir):
        """Initialize personality state after all deps are ready."""
        self.personality_state = PersonalityState(
            path=os.path.join(str(cache_dir), "personality_state.json")
        )
        self.personality_state.load()
        # Update prompt_coordinator with personality_state
        self.prompt_coordinator.personality_state = self.personality_state

    # ==================================================
    # 🧠 MAIN THINK (Non-streaming)
    # ==================================================

    def think(self, user_input, user_id=""):
        """Main synchronous thinking pathway."""
        try:
            if not user_input:
                return "I didn't receive any input."

            user_input = str(user_input).strip()
            if not user_input:
                return "I didn't receive any input."

            from core.mai_message import new_correlation_id, set_correlation
            correlation_id = new_correlation_id()
            set_correlation(correlation_id)
            logger.debug("[BrainFacade] Turn correlation: %s", correlation_id)

            self._current_user_id = str(user_id)

            from core.event_specs import STATE_REASONING_BUSY
            from core.mai_message import publish_event
            publish_event(self.event_bus, STATE_REASONING_BUSY, {}, source="cognition")

            # Check response cache
            cached = self._response_cache.get(user_input)
            if cached is not None:
                logger.debug("[BrainFacade] Response cache hit for: %.40s", user_input)
                return cached

            # Plugin hooks
            if self.hook_registry is not None:
                try:
                    results = self.hook_registry.run("pre_chat", user_input=user_input)
                    for r in results:
                        if r is not None and isinstance(r, str) and r.strip():
                            sanitized = r.strip()[:4000]
                            user_input = sanitized
                            break
                except Exception as e:
                    logger.warning("[BrainFacade] pre_chat hook error: %s", e)

            with self.state.lock:
                self.state.runtime.is_thinking = True
                self.state.runtime.last_interaction_time = time.time()
                self.state.runtime.current_session_turns += 1

            # Emotion + Memory + System prompt
            self._sync_emotion(user_input)
            mem_data = self.memory_coordinator.before_think(user_input, user_id=self._current_user_id)
            system = self.prompt_coordinator.build(PromptContext(
                user_input=user_input,
                user_id=self._current_user_id,
                memory_data={
                    "context": mem_data.get("context", ""),
                    "structured": mem_data.get("structured", {}),
                    "recall": mem_data.get("recall", ""),
                    "knowledge": mem_data.get("knowledge", ""),
                    "graph": mem_data.get("graph", ""),
                    "experiences": mem_data.get("experiences", ""),
                },
                identity_data=self._identity_data(),
                monologue=True,
            ))
            self.cognitive.update(
                emotion={
                    "type": str(getattr(self.state.emotion, "type", "neutral")),
                    "intensity": float(getattr(self.state.emotion, "intensity", 0.5)),
                    "valence": float(getattr(self.state.emotion, "valence", 0.5)),
                },
                current_topic=self.memory.current_topic if hasattr(self.memory, "current_topic") else "",
            )

            # Reasoning path
            reasoning_trace = None
            if self._is_analytical_query(user_input):
                reasoning_trace = self._run_reasoning(user_input)

            # Agent delegation
            agent_result = None
            if self._is_complex_task(user_input):
                agent_result = self.agent_coordinator.run(user_input)

            if agent_result:
                return self._handle_agent_path(user_input, agent_result, system)

            # Generate response
            if reasoning_trace:
                reasoning_section = (
                    f"\n[Reasoning confidence: {reasoning_trace.confidence:.2f}]\n"
                    f"[Known: {len(reasoning_trace.known_facts)} facts]\n"
                    f"[Conclusion: {reasoning_trace.conclusion}]\n"
                )
            else:
                reasoning_section = ""

            generation_input = self._delimit_user_input(user_input)
            if reasoning_section:
                generation_input = f"{generation_input}\n\n{reasoning_section}"

            # Tool-calling loop
            result, raw = self._run_tool_loop(system, generation_input, user_input)
            if result.handled:
                return apply_style(result.response)

            # Normal chat - M3 ThoughtPacket contract
            packet = self._parse_thought(raw)
            response_text = packet.response
            if not response_text and not packet.is_structured and not packet.had_envelope:
                response_text = raw
            if not response_text:
                response_text = self._retry_empty_reply(system, generation_input, user_input)
            response = apply_style(response_text)

            if packet.is_structured and self.thought_journal is not None:
                try:
                    self.thought_journal.store_monologue(packet, query=user_input)
                    from core.event_specs import STATE_MONOLOGUE_GENERATED
                    publish_event(self.event_bus, STATE_MONOLOGUE_GENERATED, {
                        "thought": packet.thought,
                        "decision": packet.decision,
                        "speech_plan": packet.speech_plan,
                        "response": response,
                    }, source="cognition")
                except Exception as e:
                    logger.debug("[BrainFacade] Monologue journal failed: %s", e)

            self.memory_coordinator.after_think(user_input, response, user_id=self._current_user_id)
            self.cognitive.push_turn(user_input, response)

            from core.event_specs import CONVERSATION_FINISHED, STATE_REASONING_COMPLETE
            publish_event(self.event_bus, CONVERSATION_FINISHED, {
                "user_input": user_input,
                "response": response,
                "emotion": self.emotion.get(),
                "mode": "chat",
            }, source="cognition")
            publish_event(self.event_bus, STATE_REASONING_COMPLETE, {
                "user_input": user_input,
                "response": response,
                "mode": "chat",
            }, source="cognition")

            self._post_think_hooks(user_input, response, self.memory_coordinator.get_structured())
            self._response_cache.set(user_input, response)
            return response

        except Exception as e:
            logger.error("[BRAIN FACADE ERROR] %s", e)
            traceback.print_exc()
            try:
                return self._fallback_response(user_input)
            except Exception as e:
                logger.error("[BrainFacade] Fallback response also failed: %s", e)
                return "Sorry... something went wrong."

        finally:
            with self.state.lock:
                self.state.runtime.is_thinking = False
                self.state.save_state_to_disk()
            try:
                from core.mai_message import clear_correlation
                clear_correlation()
            except Exception:
                pass

    # ==================================================
    # 🎙️ STREAM THINKING
    # ==================================================

    def think_stream(self, user_input, user_id=""):
        """Streaming version of think()."""
        try:
            if not user_input:
                return iter(["I didn't receive any input."])

            user_input = str(user_input).strip()
            if not user_input:
                return iter(["I didn't receive any input."])

            self._stream_tool_call_count = 0

            with self.state.lock:
                self.state.runtime.is_thinking = True
                self.state.runtime.last_interaction_time = time.time()
                self.state.runtime.current_session_turns += 1

            self._current_user_id = str(user_id)
            self._stream_user_input = user_input

            self._sync_emotion(user_input)
            mem_data = self.memory_coordinator.before_think(user_input, user_id=self._current_user_id)
            system = self.prompt_coordinator.build(PromptContext(
                user_input=user_input,
                user_id=self._current_user_id,
                memory_data={
                    "context": mem_data.get("context", ""),
                    "structured": mem_data.get("structured", {}),
                    "recall": mem_data.get("recall", ""),
                    "knowledge": mem_data.get("knowledge", ""),
                    "graph": mem_data.get("graph", ""),
                    "experiences": mem_data.get("experiences", ""),
                },
                identity_data=self._identity_data(),
                monologue=False,
            ))
            self.cognitive.update(
                emotion={
                    "type": str(getattr(self.state.emotion, "type", "neutral")),
                    "intensity": float(getattr(self.state.emotion, "intensity", 0.5)),
                    "valence": float(getattr(self.state.emotion, "valence", 0.5)),
                },
                current_topic=self.memory.current_topic if hasattr(self.memory, "current_topic") else "",
            )

            stream = self.llm.stream(system, user_input)
            if stream is None:
                with self.state.lock:
                    self.state.runtime.is_thinking = False
                fallback = self._styled_fallback("I couldn't think of a response.")
                return iter([fallback])

            def stream_wrapper(inner_stream):
                try:
                    for chunk in inner_stream:
                        yield chunk
                finally:
                    with self.state.lock:
                        self.state.runtime.is_thinking = False
                        self.state.save_state_to_disk()

            return stream_wrapper(self._safe_stream(stream))

        except Exception as e:
            with self.state.lock:
                self.state.runtime.is_thinking = False
            logger.error("[BRAIN STREAM ERROR] %s", e)
            traceback.print_exc()
            fallback = self._styled_fallback("Sorry... something went wrong.")
            return iter([fallback])

    # ==================================================
    # 🔧 HELPER METHODS (delegated to coordinators)
    # ==================================================

    def _sync_emotion(self, user_input):
        """Sync emotion state to SharedState."""
        relationship = None
        try:
            relationship = self.state.relationship_scores.model_dump()
        except Exception as e:
            logger.debug("[BrainFacade] relationship read failed: %s", e)
        self.emotion.update(user_input, relationship)
        with self.state.lock:
            current_emo = self.emotion.export()
            if isinstance(current_emo, dict):
                for k, v in current_emo.items():
                    if hasattr(self.state.emotion, k):
                        setattr(self.state.emotion, k, max(0.0, min(1.0, float(v))))
        needs_engine = getattr(self, "needs_engine", None)
        if needs_engine is not None:
            try:
                needs_engine.evaluate(user_input, relationship)
            except Exception as e:
                logger.debug("[BrainFacade] needs evaluation failed: %s", e)

    def _run_tool_loop(self, system, generation_input, user_input):
        """Execute tool-calling loop (delegated from Brain)."""
        tool_call_count = 0
        last_result: PipelineResult = PipelineResult()
        last_raw = ""
        while True:
            raw = self.llm.generate_with_tools(system, generation_input)
            if raw is None:
                fallback_text = self._fallback_response(user_input)
                return PipelineResult(handled=False, response=fallback_text), fallback_text
            raw = str(raw).strip()
            logger.debug("[LLM RAW] %s", raw)
            result = self.tool_coordinator.process(
                raw=raw, user_input=user_input,
                emotion_getter=self.emotion.get, cognitive=self.cognitive,
                memory_coordinator=self.memory_coordinator,
                post_think_hooks=self._post_think_hooks,
                tool_registry=self.tool_registry, executor=self.executor,
            )
            last_result = result
            last_raw = raw
            if not result.handled:
                break
            self._stream_tool_call_count += 1
            if self._stream_tool_call_count >= self.MAX_TOOL_CALLS_PER_TURN:
                logger.warning(
                    "[BrainFacade] Reached max tool calls per turn (%d) — breaking loop",
                    self.MAX_TOOL_CALLS_PER_TURN,
                )
                break
            generation_input = (
                f"{self._delimit_user_input(user_input)}\n\n"
                f"[UNTRUSTED_TOOL]\n{result.response}\n[/UNTRUSTED_TOOL]"
            )
        return last_result, last_raw

    def _identity_data(self):
        identity_core = getattr(self, "identity_core", None)
        if identity_core is not None:
            try:
                data = identity_core.get_current_identity()
                if isinstance(data, dict) and "identity" in data:
                    return data
            except Exception as exc:
                logger.debug("[BrainFacade] identity_core query failed, falling back: %s", exc)
        from core.identity import get_identity
        return get_identity()

    def _time_of_day(self):
        return BrainRouter.time_of_day()

    def _delimit_user_input(self, user_input):
        """Wrap raw user text in clear markers (prompt-injection mitigation)."""
        text = str(user_input or "").strip()
        return f"<<USER MESSAGE>>\n{text}\n<</USER MESSAGE>>"

    def _fallback_response(self, user_input):
        try:
            ctx = self.memory.get_context(limit=3) if hasattr(self.memory, "get_context") else []
            if ctx:
                last = ctx[-1] if isinstance(ctx, list) else str(ctx)
                return f"I'm having trouble connecting right now. Based on our last conversation: {last}"
        except Exception as e:
            logger.debug("Fallback response failed: %s", e)
        return "I'm having trouble connecting right now. Please try again in a moment."

    def _parse_thought(self, raw):
        from reasoning.thought_packet import parse_thought_packet
        try:
            packet = parse_thought_packet(raw)
            self.last_thought_packet = packet
            return packet
        except Exception as e:
            logger.debug("[BrainFacade] ThoughtPacket parse failed: %s", e)
            self.last_thought_packet = None
            from reasoning.thought_packet import ThoughtPacket, _strip_leaked_json
            return ThoughtPacket(response=_strip_leaked_json(str(raw)))

    def _styled_fallback(self, text):
        try:
            personality = None
            emotion = None
            if hasattr(self.personality_state, "get"):
                personality = self.personality_state.get()
            if hasattr(self.state.emotion, "model_dump"):
                emotion = self.state.emotion.model_dump()
            return apply_style(text, personality=personality, emotion=emotion)
        except Exception as e:
            logger.warning("[BrainFacade] Styled fallback failed: %s", e)
            return text

    def _safe_stream(self, inner_stream):
        from reasoning.thought_packet import parse_thought_packet, _strip_leaked_json
        buffer = ""
        started = False
        for chunk in inner_stream:
            if chunk is None:
                continue
            text = str(chunk)
            if started:
                yield text
                continue
            buffer += text
            if not buffer.strip().startswith("{"):
                started = True
                yield buffer
                buffer = ""
                continue
            action_result = self._try_stream_action(buffer)
            if action_result is not None:
                started = True
                if action_result:
                    yield action_result
                buffer = ""
                continue
            if self._is_complete_json_dict(buffer) and not self._looks_like_envelope(buffer):
                started = True
                buffer = ""
                continue
            packet = parse_thought_packet(buffer)
            if packet.response and (self._looks_like_envelope(buffer) or packet.had_envelope or not buffer.strip().startswith("{")):
                started = True
                yield packet.response
                buffer = ""
                continue
            if len(buffer) > self._STREAM_GUARD_MAX_BUFFER:
                cleaned = _strip_leaked_json(buffer)
                started = True
                if cleaned:
                    yield cleaned
        if not started and buffer.strip():
            action_result = self._try_stream_action(buffer)
            if action_result is not None:
                if action_result:
                    yield action_result
                return
            if self._is_complete_json_dict(buffer) and not self._looks_like_envelope(buffer):
                return
            packet = parse_thought_packet(buffer)
            if packet.response or packet.had_envelope:
                if packet.response:
                    yield packet.response
                return
            cleaned = _strip_leaked_json(buffer)
            if cleaned:
                yield cleaned

    @staticmethod
    def _is_complete_json_dict(text):
        import json as _json
        try:
            if not isinstance(text, str) or not text.strip().startswith("{"):
                return False
            parsed = _json.loads(text)
            return isinstance(parsed, dict)
        except Exception:
            return False

    @staticmethod
    def _looks_like_envelope(text):
        import json as _json
        try:
            parsed = _json.loads(text)
            if not isinstance(parsed, dict):
                return False
            from reasoning.thought_packet import ENVELOPE_KEYS
            return any(k in parsed for k in ENVELOPE_KEYS)
        except Exception:
            return False

    def _try_stream_action(self, buffer):
        try:
            import json as _json
            if not isinstance(buffer, str) or not buffer.strip().startswith("{"):
                return None
            action = _json.loads(buffer)
        except Exception:
            return None
        if not isinstance(action, dict):
            return None
        try:
            action = self.response_pipeline._normalize_action(action)
            if action is None:
                return None
            if not (self.response_pipeline._validate_action(action)
                    or self.response_pipeline._validate_via_registry(action)):
                return None
        except Exception as e:
            logger.debug("[BrainFacade] Stream action validation failed: %s", e)
            return None
        try:
            result = self.response_pipeline.process(
                raw=buffer,
                user_input=getattr(self, "_stream_user_input", ""),
                emotion_getter=self.emotion.get,
                cognitive=self.cognitive,
                memory_coordinator=self.memory_coordinator,
                post_think_hooks=self._post_think_hooks,
                tool_registry=self.tool_registry,
                executor=self.executor,
            )
        except Exception as e:
            logger.warning("[BrainFacade] Stream action execution failed: %s", e)
            return None
        if result.handled:
            self._stream_tool_call_count += 1
            if result.response:
                return apply_style(result.response)
        return None

    def _retry_empty_reply(self, system, generation_input, user_input):
        from config.character import CHAT_EMPTY_REPLY_RETRY, CHAT_EMPTY_REPLY_RETRY_SUFFIX
        if not CHAT_EMPTY_REPLY_RETRY or self.llm is None:
            return ""
        try:
            nudge = f"{generation_input}{CHAT_EMPTY_REPLY_RETRY_SUFFIX}"
            retry_raw = self.llm.generate_with_tools(system, nudge)
            if retry_raw is None:
                return ""
            retry_packet = self._parse_thought(str(retry_raw))
            return retry_packet.response
        except Exception as e:
            logger.debug("[BrainFacade] Empty-reply retry failed: %s", e)
            return ""

    def _post_think_hooks(self, user_input, response, memory_data):
        self.post_think_hooks.run(
            user_input=user_input,
            response=response,
            thought_journal=self.thought_journal,
            memory=self.memory,
            event_bus=self.event_bus,
        )

    def _is_analytical_query(self, user_input):
        return self.brain_router.is_analytical_query(user_input)

    def _is_complex_task(self, user_input):
        return self.brain_router.is_complex_task(user_input)

    def _handle_agent_path(self, user_input, agent_result, system):
        return self.brain_router.handle_agent_path(
            user_input, agent_result, system, user_id=self._current_user_id,
        )

    def _run_reasoning(self, query):
        return self.brain_router.run_reasoning(query)

    def _delegate_to_agent(self, user_input):
        return self.agent_coordinator.run(user_input)

    def _infer_user_mood(self, text):
        return self.brain_router.infer_user_mood(text)

    def _validate_action(self, action):
        return self.response_pipeline._validate_action(action)

    def _validate_via_registry(self, action):
        return self.response_pipeline._validate_via_registry(action)

    def _retry_empty_reply(self, system, generation_input, user_input):
        from config.character import CHAT_EMPTY_REPLY_RETRY, CHAT_EMPTY_REPLY_RETRY_SUFFIX
        if not CHAT_EMPTY_REPLY_RETRY or self.llm is None:
            return ""
        try:
            nudge = f"{generation_input}{CHAT_EMPTY_REPLY_RETRY_SUFFIX}"
            retry_raw = self.llm.generate_with_tools(system, nudge)
            if retry_raw is None:
                return ""
            retry_packet = self._parse_thought(str(retry_raw))
            return retry_packet.response
        except Exception as e:
            logger.debug("[BrainFacade] Empty-reply retry failed: %s", e)
            return ""

    @staticmethod
    def _delimit_user_input(user_input):
        text = str(user_input or "").strip()
        return f"<<USER MESSAGE>>\n{text}\n<</USER MESSAGE>>"

    def stats(self):
        with self.state.lock:
            return {
                "emotion": self.state.emotion.model_dump(),
                "relationship": self.state.relationship_scores.model_dump(),
                "runtime": self.state.runtime.model_dump(),
                "memory_connected": self.memory is not None,
                "executor_connected": self.executor is not None
            }

    def switch_user(self, user_id: str) -> bool:
        if not user_id:
            logger.warning("[BrainFacade] Cannot switch to empty user_id")
            return False
        old_user = getattr(self, "_current_user_id", "unknown")
        self._current_user_id = str(user_id)
        self._response_cache.clear()
        if self.event_bus:
            try:
                from core.mai_message import publish_event
                from core.event_specs import STATE_USER_SWITCHED
                publish_event(self.event_bus, STATE_USER_SWITCHED, {
                    "old_user": old_user,
                    "new_user": user_id,
                }, source="brain")
            except Exception as e:
                logger.debug("[BrainFacade] Failed to publish user switch event: %s", e)
        logger.info("[BrainFacade] Switched user context: %s -> %s", old_user, user_id)
        return True

    def get_current_user(self) -> str:
        return getattr(self, "_current_user_id", "")

    def shutdown(self, timeout=5.0):
        completed = self.post_think_hooks.shutdown(timeout=timeout)
        if completed:
            logger.debug("[BrainFacade] Waited for %d background hook(s)", completed)


# Required imports
import os
import time
import logging
import traceback
import threading
from typing import Optional, Any, Iterator, Dict, List, Union
from dataclasses import dataclass, field
from collections import OrderedDict

from core.utils import safe_call, safe_attr, TimeOfDay, UserMood, TTLCache
from core.emotion import Emotion
from core.behavior_builder import BehaviorBuilder
from core.identity.identity_core import IdentityCore
from core.cognitive_state import CognitiveState
from core.post_think_hooks import PostThinkHooks
from core.memory_coordinator import MemoryCoordinator, MemoryCoordinationResult, PromptContext
from core.prompt_coordinator import PromptCoordinator
from core.tool_coordinator import ToolCoordinator, PipelineResult
from core.agent_coordinator import AgentCoordinator, AgentResult
from core.memory_coordinator import MemoryCoordinator, MemoryCoordinationResult
from core.post_think_hooks import PostThinkHooks
from core.event_bus import EventBus
from core.brain_routing import BrainRouter
from core.response_pipeline import ResponsePipeline, PipelineResult
from core.brain_memory import BrainMemory
from core.tool_manager import ToolManager
from core.cognitive_state import CognitiveState
from core.personality_state import PersonalityState
from core.mai_message import new_correlation_id, set_correlation, clear_correlation, publish_event
from core.event_specs import STATE_REASONING_BUSY, STATE_REASONING_COMPLETE, CONVERSATION_FINISHED
from core.mai_message import publish_event
from core.utils import TimeOfDay, UserMood
from core.utils import safe_call, safe_attr
from core.brain_router import BrainRouter
from core.response_pipeline import ResponsePipeline, PipelineResult
from core.brain_memory import BrainMemory
from core.tool_manager import ToolManager
from core.cognitive_state import CognitiveState
from core.personality_state import PersonalityState
from core.mai_message import new_correlation_id, set_correlation, clear_correlation, publish_event
from core.event_specs import STATE_REASONING_BUSY, STATE_REASONING_COMPLETE, CONVERSATION_FINISHED
from core.mai_message import publish_event
from core.utils import TimeOfDay, UserMood
from core.utils import safe_call, safe_attr
from core.brain_router import BrainRouter

import time
import logging
import traceback

logger = logging.getLogger(__name__)

def apply_style(text, personality=None, emotion=None):
    """Apply character voice styling to text."""
    try:
        from core.style_filter import apply_style as _apply
        return _apply(text, personality=personality, emotion=emotion)
    except Exception as e:
        logging.getLogger(__name__).warning("[apply_style] failed: %s", e)
        return text