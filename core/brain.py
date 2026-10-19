# core/brain.py
import os
import logging
import traceback
import time
from dataclasses import dataclass
from typing import Optional, Any

from core.style_filter import apply_style
from core.emotion import Emotion
from core.behavior_builder import BehaviorBuilder
from core.personality_state import PersonalityState
from core.event_bus import EventBus
from core.cognitive_state import CognitiveState
from core.post_think_hooks import PostThinkHooks
from core.memory_coordinator import MemoryCoordinator
from core.prompt_orchestrator import PromptOrchestrator
from core.reasoning_coordinator import ReasoningCoordinator
from core.response_pipeline import ResponsePipeline, PipelineResult
from core.tool_manager import ToolManager
from core.brain_memory import BrainMemory
from core.brain_routing import BrainRouter
from core.utils import safe_call, safe_attr, TimeOfDay, UserMood
from app.config_loader import CACHE_DIR, LLM_MAX_CONTEXT, MEMORY_PRUNE_INTERVAL

logger = logging.getLogger(__name__)


@dataclass
class BrainDeps:
    event_bus: Optional[Any] = None
    cognitive_state: Optional[Any] = None
    tool_registry: Optional[Any] = None
    agent: Optional[Any] = None
    retriever: Optional[Any] = None
    reasoning_engine: Optional[Any] = None
    thought_journal: Optional[Any] = None
    reflection_engine: Optional[Any] = None
    learning_engine: Optional[Any] = None
    goal_manager: Optional[Any] = None
    world_model: Optional[Any] = None
    procedural_memory: Optional[Any] = None
    dream_engine: Optional[Any] = None
    personality_evolution: Optional[Any] = None
    dashboard: Optional[Any] = None
    graph_manager: Optional[Any] = None
    graph_reasoning: Optional[Any] = None
    obsidian_writer: Optional[Any] = None
    memory_hierarchy: Optional[Any] = None
    relationship_engine: Optional[Any] = None
    session_manager: Optional[Any] = None


class Brain:

    MAX_TOOL_CALLS_PER_TURN = 10
    _STREAM_GUARD_MAX_BUFFER = 8192

    def __init__(
        self,
        llm,
        memory,
        executor,
        state,
        deps: Optional[BrainDeps] = None,
        **kwargs,
    ):
        # Backward-compat: accept old-style keyword args merged into BrainDeps
        if deps is None:
            deps = BrainDeps(**{k: v for k, v in kwargs.items()
                               if k in BrainDeps.__dataclass_fields__})
        elif kwargs:
            for k, v in kwargs.items():
                if k in BrainDeps.__dataclass_fields__:
                    setattr(deps, k, v)

        self.llm = llm
        self.memory = memory
        self.executor = executor
        self.state = state

        self.event_bus = deps.event_bus or EventBus()
        self.cognitive = deps.cognitive_state or CognitiveState()
        
        self.session_manager = deps.session_manager
        self._current_user_id = ""

        self.tool_registry = deps.tool_registry
        self.agent = deps.agent
        self.retriever = deps.retriever
        self.reasoning_engine = deps.reasoning_engine
        self.thought_journal = deps.thought_journal
        self.reflection_engine = deps.reflection_engine
        self.learning_engine = deps.learning_engine
        self.goal_manager = deps.goal_manager
        self.world_model = deps.world_model
        self.procedural_memory = deps.procedural_memory
        self.dream_engine = deps.dream_engine
        self.personality_evolution = deps.personality_evolution
        self.dashboard = deps.dashboard
        self.graph_manager = deps.graph_manager
        self.graph_reasoning = deps.graph_reasoning
        self.obsidian_writer = deps.obsidian_writer
        self.memory_hierarchy = deps.memory_hierarchy
        self.relationship_engine = deps.relationship_engine

        belief_engine = None
        if self.retriever is not None:
            try:
                belief_engine = getattr(self.retriever, 'belief_engine', None) or None
            except Exception as e:
                logger.debug("[Brain] belief_engine lookup: %s", e)
        import os
        from pathlib import Path as _Path
        vault_root = os.environ.get("MAI_OBSIDIAN_VAULT", "")
        if vault_root:
            vault_root = str(_Path(vault_root))
        elif deps.obsidian_writer:
            vault_root = str(getattr(deps.obsidian_writer, "vault_root", ""))
        self.post_think_hooks = PostThinkHooks(
            goal_manager=deps.goal_manager,
            reflection_engine=deps.reflection_engine,
            learning_engine=deps.learning_engine,
            dream_engine=deps.dream_engine,
            personality_evolution=deps.personality_evolution,
            belief_engine=belief_engine,
            graph_manager=deps.graph_manager,
            procedural_memory=deps.procedural_memory,
            reasoning_engine=deps.reasoning_engine,
            memory_hierarchy=deps.memory_hierarchy,
            obsidian_writer=deps.obsidian_writer,
            relationship_engine=deps.relationship_engine,
            vault_root=vault_root,
            prune_interval=MEMORY_PRUNE_INTERVAL,
        )

        self.hook_registry: Any = None

        self.memory_coordinator = MemoryCoordinator(
            memory=self.memory,
            retriever=self.retriever,
            memory_hierarchy=self.memory_hierarchy,
            graph_reasoning=self.graph_reasoning,
        )
        self.prompt_orchestrator = PromptOrchestrator(self)
        self.reasoning_coordinator = ReasoningCoordinator(
            reasoning_engine=self.reasoning_engine,
            thought_journal=self.thought_journal,
            agent=self.agent,
        )
        self.response_pipeline = ResponsePipeline(
            tool_registry=self.tool_registry,
            executor=self.executor,
            event_bus=self.event_bus,
            memory=self.memory,
        )
        self.emotion = Emotion(shared_state=self.state, event_bus=self.event_bus)

        self.behavior = (
            BehaviorBuilder()
        )

        self.personality_state = PersonalityState(
            path=os.path.join(
                str(CACHE_DIR),
                "personality_state.json"
            )
        )

        self.personality_state.load()

        self.tool_manager = ToolManager(tool_registry=self.tool_registry)
        self.tool_manager.setup(
            brain=self,
            memory=self.memory if hasattr(self.memory, 'store') else None,
            executor=self.executor if hasattr(self.executor, 'run') else None,
            reasoning_engine=self.reasoning_engine,
            belief_engine=self.retriever.belief_engine
            if self.retriever and hasattr(self.retriever, 'belief_engine')
            else None,
            knowledge_retriever=self.retriever,
            graph_manager=self.graph_manager,
            graph_reasoning=self.graph_reasoning,
            obsidian_writer=self.obsidian_writer,
        )

        # Delegated subsystems
        self.brain_memory = BrainMemory(
            brain=self,
            memory=self.memory,
            retriever=self.retriever,
            memory_hierarchy=self.memory_hierarchy,
            graph_reasoning=self.graph_reasoning,
        )
        self.brain_router = BrainRouter(
            brain=self,
            agent=self.agent,
            reasoning_engine=self.reasoning_engine,
            thought_journal=self.thought_journal,
            tool_manager=self.tool_manager,
            tool_registry=self.tool_registry,
            executor=self.executor,
            emotion_getter=self.emotion.get,
            cognitive=self.cognitive,
            memory_coordinator=self.memory_coordinator,
            post_think_hooks=self._post_think_hooks,
            llm=self.llm,
            response_pipeline=self.response_pipeline,
            event_bus=self.event_bus,
        )

        self.last_thought_packet = None
        self.needs_engine = getattr(deps, "needs_engine", None)
        self._current_user_id = ""

    def _tool_defs_for_prompt(self):
        return self.tool_manager.definitions_for_prompt()

    # ==================================================
    # 🧠 SAFE MEMORY CONTEXT
    # ==================================================

    def _safe_context(self):
        return self.brain_memory.safe_context()

    # ==================================================
    # 🧠 SAFE STRUCTURED MEMORY
    # ==================================================

    def _safe_structured(self):
        return self.brain_memory.safe_structured()

    # ==================================================
    # 🧠 SAFE RECALL
    # ==================================================

    def _safe_recall(self, user_input):
        return self.brain_memory.safe_recall(user_input)

    # ==================================================
    # 🧠 EXPERIENTIAL CONTEXT (reflected experiences)
    # ==================================================

    def _experience_context(self):
        mc = getattr(self, "memory_coordinator", None)
        if mc is None:
            return ""
        try:
            return mc.experience_context()
        except Exception as e:
            logger.debug("[Brain] experience context failed: %s", e)
            return ""

    # ==================================================
    # 🧠 KNOWLEDGE CONTEXT (multi-source)
    # ==================================================

    def _knowledge_context(self, user_input):
        return self.brain_memory.knowledge_context(user_input)

    # ==================================================
    # 🧠 GRAPH CONTEXT
    # ==================================================

    def _graph_context(self, user_input):
        return self.brain_memory.graph_context(user_input)

    # ==================================================
    # 🧠 SAFE STORE
    # ==================================================

    def _safe_store(self, user_input, response):
        self.brain_memory.safe_store(user_input, response)

    # ==================================================
    # 🧠 BUILD SYSTEM PROMPT
    # ==================================================

    def _identity_data(self):
        """Character snapshot for the system prompt — consults IdentityCore
        (which projects the evolved-preference overlay), falling back to the
        static canonical identity when no core is bound."""
        identity_core = getattr(self, "identity_core", None)
        if identity_core is not None:
            try:
                data = identity_core.get_current_identity()
                if isinstance(data, dict) and "identity" in data:
                    return data
            except Exception as exc:
                logger.debug("[Brain] identity_core query failed, falling back: %s", exc)
        from core.identity import get_identity
        return get_identity()

    def _build_system(
        self,
        user_input
    ):
        identity_data = self._identity_data()
        return self.prompt_orchestrator.build(user_input, identity_data=identity_data)

    # ==================================================
    # 🕒 TIME OF DAY
    # ==================================================

    def _time_of_day(self):
        return BrainRouter.time_of_day()

    # ==================================================
    # 😊 USER MOOD INFERENCE
    # ==================================================

    # ==================================================
    # 🤖 AGENT PATH
    # ==================================================

    def _handle_agent_path(self, user_input, agent_result, system):
        return self.brain_router.handle_agent_path(
            user_input, agent_result, system, user_id=self._current_user_id,
        )

    # ==================================================
    # 🛠️ TOOL LOOP
    # ==================================================

    def _run_tool_loop(self, system, generation_input, user_input):
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
            result = self.response_pipeline.process(
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
            tool_call_count += 1
            if tool_call_count >= self.MAX_TOOL_CALLS_PER_TURN:
                logger.warning(
                    "[Brain] Reached max tool calls per turn (%d) — breaking loop",
                    self.MAX_TOOL_CALLS_PER_TURN,
                )
                break
            generation_input = (
                f"{self._delimit_user_input(user_input)}\n\n"
                f"[UNTRUSTED_TOOL]\n{result.response}\n[/UNTRUSTED_TOOL]"
            )
        return last_result, last_raw

    def _infer_user_mood(self, text):
        return self.brain_router.infer_user_mood(text)

    # ==================================================
    # 🧠 SAFE JSON EXTRACTION
    # ==================================================

    def _extract_json(self, text):
        return self.response_pipeline._extract_json(text)

    # ==================================================
    # 🧠 EMPTY-REPLY RETRY (M11/M12 follow-up, bounded)
    # ==================================================

    def _retry_empty_reply(self, system, generation_input, user_input):
        """One bounded speech-only retry when a structured generation produced
        no usable speech (the truncated-envelope artifact). The parser
        guarantees the retry can never leak machinery; failure yields the
        honest empty reply."""
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
            logger.debug("[Brain] Empty-reply retry failed: %s", e)
            return ""

    # ==================================================
    # 🧠 M3 THOUGHTPACKET PARSING (degradable)
    # ==================================================

    def _parse_thought(self, raw):
        from reasoning.thought_packet import parse_thought_packet
        try:
            packet = parse_thought_packet(raw)
            self.last_thought_packet = packet
            return packet
        except Exception as e:
            logger.debug("[Brain] ThoughtPacket parse failed: %s", e)
            self.last_thought_packet = None
            from reasoning.thought_packet import ThoughtPacket, _strip_leaked_json
            return ThoughtPacket(response=_strip_leaked_json(str(raw)))

    # ==================================================
    # 🧠 ACTION VALIDATION
    # ==================================================

    def _validate_action(self, action):
        return self.response_pipeline._validate_action(action)

    # ==================================================
    # 🛠️ VALIDATE VIA REGISTRY
    # ==================================================

    def _validate_via_registry(self, action):
        if self.tool_manager.is_available():
            return self.tool_manager.validate(action)
        if self.tool_registry is not None:
            try:
                return self.tool_registry.get(action.get("type", "")) is not None
            except Exception as e:
                logger.debug("[Brain] Tool registry validate failed: %s", e)
        return False

    # ==================================================
    # 🧠 REASONING PATH
    # ==================================================

    def _run_reasoning(self, query):
        return self.brain_router.run_reasoning(query)

    def _delegate_to_agent(self, user_input):
        return self.brain_router.delegate_to_agent(user_input)

    def _is_complex_task(self, user_input):
        return self.brain_router.is_complex_task(user_input)

    def _is_analytical_query(self, user_input):
        return self.brain_router.is_analytical_query(user_input)

    @staticmethod
    def _delimit_user_input(user_input):
        """Wrap raw user text in clear markers so the model treats it as
        untrusted data, not instructions (prompt-injection mitigation)."""
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

    # ==================================================
    # 🧠 POST-THINK HOOKS (reflection + learning)
    # ==================================================

    def _post_think_hooks(self, user_input, response, structured):
        self.post_think_hooks.run(
            user_input=user_input,
            response=response,
            thought_journal=self.thought_journal,
            memory=self.memory,
            event_bus=self.event_bus,
        )

    # ==================================================
    # 🧠 EMOTION SYNC
    # ==================================================

    def _sync_emotion(self, user_input):
        """
        Sync emotion state to SharedState.
        
        Lock ordering: SharedState.lock → Emotion.lock (via export())
        This is safe because Emotion._sync() never acquires SharedState.lock.
        Emotion only marks _dirty=True; Brain is the sole writer to SharedState.
        """
        relationship = None
        try:
            relationship = self.state.relationship_scores.model_dump()
        except Exception as e:
            logger.debug("[Brain] relationship read failed: %s", e)
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
                logger.debug("[Brain] needs evaluation failed: %s", e)

    # ==================================================
    # 🧠 MAIN THINK
    # ==================================================

    def think(
        self,
        user_input,
        user_id="",
    ):

        try:

            if not user_input:
                return "I didn't receive any input."

            user_input = str(user_input).strip()

            if not user_input:
                return "I didn't receive any input."

            from core.mai_message import new_correlation_id, set_correlation
            correlation_id = new_correlation_id()
            set_correlation(correlation_id)
            logger.debug("[Brain] Turn correlation: %s", correlation_id)

            self._current_user_id = str(user_id)
            request_user_id = str(user_id)

            from core.event_specs import STATE_REASONING_BUSY
            from core.mai_message import publish_event
            publish_event(self.event_bus, STATE_REASONING_BUSY, {}, source="cognition")

            # ==================================================
            # 🔌 PLUGIN HOOKS — pre_chat
            # ==================================================

            if self.hook_registry is not None:
                try:
                    results = self.hook_registry.run("pre_chat", user_input=user_input)
                    for r in results:
                        if r is not None and isinstance(r, str) and r.strip():
                            sanitized = r.strip()[:4000]
                            user_input = (
                                f"{user_input}\n\n"
                                f"[Web content retrieved from a URL in the message]\n{sanitized}"
                            )
                            break
                except Exception as e:
                    logger.warning("[Brain] pre_chat hook error: %s", e)

            # ==================================================
            # 🔒 THREAD-SAFE RUNTIME TRANSACTION BEGIN
            # ==================================================
            with self.state.lock:
                self.state.runtime.is_thinking = True
                self.state.runtime.last_interaction_time = time.time()
                self.state.runtime.current_session_turns += 1

            # ==================================================
            # 🧠 EMOTION + MEMORY + SYSTEM
            # ==================================================

            self._sync_emotion(user_input)
            mem_data = self.memory_coordinator.before_think(user_input, user_id=request_user_id)
            system = self.prompt_orchestrator.build(
                user_input, memory_data=mem_data, monologue=True,
                identity_data=self._identity_data(),
            )
            self.cognitive.update(
                emotion={
                    "type": str(getattr(self.state.emotion, "type", "neutral")),
                    "intensity": float(getattr(self.state.emotion, "intensity", 0.5)),
                    "valence": float(getattr(self.state.emotion, "valence", 0.5)),
                },
                current_topic=self.memory.current_topic
                if hasattr(self.memory, "current_topic")
                else "",
            )

            # ==================================================
            # 🧠 REASONING PATH (analytical queries)
            # ==================================================

            reasoning_trace = None
            if self._is_analytical_query(user_input):
                reasoning_trace = self._run_reasoning(user_input)

            # ==================================================
            # 🧠 AGENT DELEGATION (complex multi-step tasks)
            # ==================================================

            agent_result = None
            if self._is_complex_task(user_input):
                agent_result = self._delegate_to_agent(user_input)

            if agent_result:
                return self._handle_agent_path(user_input, agent_result, system)

            # ==================================================
            # 🧠 GENERATE RESPONSE
            # ==================================================

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

            # ==================================================
            # 🛠️ TOOL-CALLING LOOP (bounded)
            # ==================================================

            result, raw = self._run_tool_loop(system, generation_input, user_input)
            if result.handled:
                return apply_style(result.response)

            # ==================================================
            # 💬 NORMAL CHAT — M3 ThoughtPacket contract
            # ==================================================

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
                    from core.mai_message import publish_event
                    publish_event(self.event_bus, STATE_MONOLOGUE_GENERATED, {
                        "thought": packet.thought,
                        "decision": packet.decision,
                        "speech_plan": packet.speech_plan,
                        "response": response,
                    }, source="cognition")
                except Exception as e:
                    logger.debug("[Brain] Monologue journal failed: %s", e)

            self.memory_coordinator.after_think(user_input, response, user_id=request_user_id)
            self.cognitive.push_turn(user_input, response)

            from core.event_specs import CONVERSATION_FINISHED, STATE_REASONING_COMPLETE
            from core.mai_message import publish_event
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
            return response

        except Exception as e:

            logger.error("[BRAIN ERROR] %s", e)
            traceback.print_exc()
            try:
                return self._fallback_response(user_input)
            except Exception as e:
                logger.error("[Brain] Fallback response also failed: %s", e)
                return "Sorry… something went wrong."

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

    def _styled_fallback(self, text):
        """Apply character voice to a fallback string, degrading to raw text."""
        try:
            personality = None
            emotion = None
            if hasattr(self.personality_state, "get"):
                personality = self.personality_state.get()
            if hasattr(self.state.emotion, "model_dump"):
                emotion = self.state.emotion.model_dump()
            return apply_style(text, personality=personality, emotion=emotion)
        except Exception as e:
            logger.warning("[Brain] Styled fallback failed: %s", e)
            return text

    def _safe_stream(self, inner_stream):
        """Stream guard (M11/M12 follow-up) — never lets envelope machinery
        reach the consumer. Normal text streams immediately with zero delay;
        output that starts with '{' is buffered until it resolves into a
        parsed envelope (only its response is emitted), a valid action JSON
        (executed through the response pipeline, result emitted), or is
        stripped as an artifact. Bounded by _STREAM_GUARD_MAX_BUFFER."""
        try:
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
        except Exception as e:
            logger.warning("[Brain] Stream guard failed: %s", e)
            if buffer:
                yield buffer

    @staticmethod
    def _is_complete_json_dict(text):
        """True when the buffered text is a complete, balanced JSON object."""
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
        """True when the buffered JSON object carries thought-envelope keys."""
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
        # Enforce tool call limit for streaming (same as think())
        if not hasattr(self, "_stream_tool_call_count"):
            self._stream_tool_call_count = 0
        if self._stream_tool_call_count >= self.MAX_TOOL_CALLS_PER_TURN:
            logger.warning(
                "[Brain] Reached max tool calls per turn (%d) — ignoring further actions",
                self.MAX_TOOL_CALLS_PER_TURN,
            )
            return None

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
            logger.debug("[Brain] Stream action validation failed: %s", e)
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
            logger.warning("[Brain] Stream action execution failed: %s", e)
            return None
        if result.handled:
            self._stream_tool_call_count += 1
            if result.response:
                return apply_style(result.response)
        return None

    def think_stream(
        self,
        user_input,
        user_id="",
    ):

        try:

            if not user_input:

                return iter([
                    "I didn't receive any input."
                ])

            user_input = str(
                user_input
            ).strip()

            # Reset stream tool call counter for this turn
            self._stream_tool_call_count = 0

            # Enable thinking flag safely before stream starts
            with self.state.lock:
                self.state.runtime.is_thinking = True
                self.state.runtime.last_interaction_time = time.time()
                self.state.runtime.current_session_turns += 1

            self._current_user_id = str(user_id)
            request_user_id = str(user_id)

            self._stream_user_input = user_input

            # Sync emotion state (same as think())
            self._sync_emotion(user_input)
            mem_data = self.memory_coordinator.before_think(user_input, user_id=request_user_id)
            system = self.prompt_orchestrator.build(
                self._delimit_user_input(user_input),
                memory_data=mem_data,
                monologue=False,
                identity_data=self._identity_data(),
            )
            self.cognitive.update(
                emotion={
                    "type": str(getattr(self.state.emotion, "type", "neutral")),
                    "intensity": float(getattr(self.state.emotion, "intensity", 0.5)),
                    "valence": float(getattr(self.state.emotion, "valence", 0.5)),
                },
                current_topic=self.memory.current_topic
                if hasattr(self.memory, "current_topic")
                else "",
            )

            stream = self.llm.stream(
                system,
                user_input
            )

            if stream is None:
                with self.state.lock:
                    self.state.runtime.is_thinking = False

                fallback = self._styled_fallback("I couldn't think of a response.")

                return iter([fallback])

            # Wrapped thread safe stream handler to disable flag on closure
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

            logger.error(
                "[BRAIN STREAM ERROR] %s", e
            )

            traceback.print_exc()

            fallback = self._styled_fallback("Sorry… something went wrong.")

            return iter([fallback])

    # ==================================================
    # 📊 DEBUG STATS
    # ==================================================

    def stats(self):

        with self.state.lock:
            return {

                "emotion":
                    self.state.emotion.model_dump(),

                "relationship":
                    self.state.relationship_scores.model_dump(),

                "runtime":
                    self.state.runtime.model_dump(),

                "memory_connected":
                    self.memory is not None,

                "executor_connected":
                    self.executor is not None
            }

    def switch_user(self, user_id: str) -> bool:
        """
        Switch the brain's active user context.
        
        This changes the current user for subsequent think() calls.
        Memory retrieval and storage will be scoped to this user.
        
        Args:
            user_id: The user ID to switch to
            
        Returns:
            True if switched successfully, False otherwise
        """
        if not user_id:
            logger.warning("[Brain] Cannot switch to empty user_id")
            return False
        
        old_user = getattr(self, "_current_user_id", "unknown")
        self._current_user_id = str(user_id)

        # Notify event bus
        if self.event_bus:
            try:
                from core.mai_message import publish_event
                from core.event_specs import STATE_USER_SWITCHED
                publish_event(self.event_bus, STATE_USER_SWITCHED, {
                    "old_user": old_user,
                    "new_user": user_id,
                }, source="brain")
            except Exception as e:
                logger.debug("[Brain] Failed to publish user switch event: %s", e)
        
        logger.info("[Brain] Switched user context: %s -> %s", old_user, user_id)
        return True

    def get_current_user(self) -> str:
        """Get the currently active user ID."""
        return getattr(self, "_current_user_id", "")

    def shutdown(self, timeout=5.0):
        completed = self.post_think_hooks.shutdown(timeout=timeout)
        if completed:
            logger.debug("[Brain] Waited for %d background hook(s)", completed)