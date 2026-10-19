# core/event_specs.py
"""Semantic event catalog — the single source of truth for every event.

Phase 4 (Event Fabric incremental migration) moves the legacy ad-hoc
``(topic, dict)`` publish sites onto the ``MaiMessage`` envelope and semantic
topic names (``data.*``). This module declares every migrated event type once —
topic constant, publisher(s), payload keys, priority — and seeds the
:class:`EventRegistry` so the bus can validate + authorize + version-gate
semantic publishes.

The catalog lives here (one file) so the capabilities matrix has a single
source. Per-subsystem modules (e.g. ``voice.events``) re-export the constants
they publish so existing import sites keep working.

See ``docs/event-fabric-architecture.md`` → Phase 4.
"""
from __future__ import annotations

from core.event_registry import EventRegistry, EventSpec, RetryPolicy

# ── Voice ──────────────────────────────────────────────────────────

VOICE_STARTED = "data.voice.started"
VOICE_STOPPED = "data.voice.stopped"
VOICE_STATE_CHANGED = "data.voice.state_changed"
VOICE_LISTENING_STARTED = "data.voice.listening_started"
VOICE_RECORDING_COMPLETED = "data.voice.recording_completed"
VOICE_SPEAKER_IDENTIFIED = "data.voice.speaker_identified"
VOICE_TRANSCRIPTION_COMPLETED = "data.voice.transcription_completed"
VOICE_WAKE_DETECTED = "data.voice.wake_detected"
VOICE_WAKE_FOUND = "data.voice.wake_found"
VOICE_RETURNED = "data.voice.returned"
VOICE_ERROR = "data.voice.error"

# ── Memory / conversation ──────────────────────────────────────────

MEMORY_EXTRACTED = "data.memory.extracted"
MEMORY_STORED = "data.memory.stored"
MEMORY_CONSOLIDATED = "data.memory.consolidated"
MEMORY_LIFECYCLE = "data.memory.lifecycle"
CONVERSATION_FINISHED = "data.conversation.finished"

# ── Reasoning / learning ───────────────────────────────────────────

REASONING_COMPLETED = "data.reasoning.completed"
REFLECTION_GENERATED = "data.reflection.generated"
LEARNING_GENERALIZED = "data.learning.generalized"
BEHAVIOR_ADJUSTED = "data.behavior.adjusted"

# ── Agency / goals / tools / dreams ────────────────────────────────

GOAL_CREATED = "data.goal.created"
GOAL_COMPLETED = "data.goal.completed"
GOAL_COMPLETED_REFLECTION = "data.goal.completed_reflection"
GOAL_CANCELLED = "data.goal.cancelled"
GOAL_AUTO_COMPLETED = "data.goal.auto_completed"
GOAL_TURNS_INCREMENTED = "data.goal.turns_incremented"
AGENT_STEP = "data.agent.step"
AGENT_COMPLETED = "data.agent.completed"
TOOL_REGISTERED = "data.tool.registered"
TOOL_CALLED = "data.tool.called"
WORLD_ENTITY_ADDED = "data.world.entity_added"
EVOLUTION_ADJUSTED = "data.evolution.adjusted"
PREFERENCE_EVOLVED = "data.preference.evolved"
EXPERIENCE_RECORDED = "data.experience.recorded"
PROCEDURAL_LEARNED = "data.procedural.learned"
DREAM_COMPLETED = "data.dream.completed"
DREAM_STARTED = "data.dream.started"
DREAM_ENDED = "data.dream.ended"

# ── Emotion / cognition ────────────────────────────────────────────

EMOTION_CHANGED = "data.emotion.changed"
EMOTION_PROFILE_PUSHED = "data.emotion.profile_pushed"
EMOTION_GOAL_SUGGESTED = "data.emotion.goal_suggested"
SCHEDULER_TASK_COMPLETED = "data.scheduler.task_completed"
HEALTH_ERROR = "data.health.error"

# ── Knowledge ──────────────────────────────────────────────────────

GRAPH_UPDATED = "data.graph.updated"
BELIEF_UPDATED = "data.belief.updated"
BELIEF_GRAPH_SYNCED = "data.belief.graph_synced"
KNOWLEDGE_BUILD_COMPLETED = "data.knowledge.build_completed"
RETRIEVER_RESULTS = "data.retriever.results"
INDEXER_COMPLETED = "data.indexer.completed"
INDEXER_CHUNKS_INDEXED = "data.indexer.chunks_indexed"

# ── State bus (UI projection — Phase 5 Reactive UI) ────────────────
# state.* carries authoritative runtime truth. The UI (desktop, avatar,
# dock, notification center) subscribes EXCLUSIVELY to state.* via the
# StreamManager / WSBridge boundary. data.* remains the fabric record for
# subsystem-to-subsystem communication.

STATE_VOICE_LISTENING = "state.voice.listening"
STATE_VOICE_SPEAKING = "state.voice.speaking"
STATE_VOICE_IDLE = "state.voice.idle"
STATE_VOICE_WAKE = "state.voice.wake"
STATE_EMOTION_CHANGED = "state.emotion.changed"
STATE_MEMORY_UPDATED = "state.memory.updated"
STATE_REASONING_BUSY = "state.reasoning.busy"
STATE_REASONING_COMPLETE = "state.reasoning.complete"
STATE_REASONING_REFLECTION = "state.reasoning.reflection"
STATE_DREAMING_STARTED = "state.dreaming.started"
STATE_DREAMING_FINISHED = "state.dreaming.finished"
STATE_KNOWLEDGE_UPDATED = "state.knowledge.updated"
STATE_BELIEF_UPDATED = "state.belief.updated"
STATE_GOAL_UPDATED = "state.goal.updated"
STATE_AGENT_COMPLETED = "state.agent.completed"
STATE_NEEDS_UPDATED = "state.needs.updated"
STATE_MONOLOGUE_GENERATED = "state.monologue.generated"

# Retrieval and tool-execution projections.
#
# The UI subscribes exclusively to `state.*`. Retrieval and tool activity were
# previously observable only as post-hoc `data.*` facts
# (`data.retriever.results`, `data.tool.called`), which cannot express "MAI is
# retrieving right now" — the distinction a live entity interface needs to
# show progress rather than a retrospective count.
#
# These payloads are deliberately minimal: retrieval carries a result count and
# never the query text; tool events carry the registry tool name, success, and
# duration, never arguments, results, or error strings.
STATE_RETRIEVAL_STARTED = "state.retrieval.started"
STATE_RETRIEVAL_COMPLETED = "state.retrieval.completed"
STATE_TOOL_STARTED = "state.tool.started"
STATE_TOOL_COMPLETED = "state.tool.completed"


# ── Catalog ────────────────────────────────────────────────────────


def _spec(name: str, publisher: str, description: str = "",
          payload_keys: tuple = (), priority: str = "normal",
          other_publishers: tuple = ()) -> EventSpec:
    pubs = (publisher,) + other_publishers
    return EventSpec(
        name=name,
        version=1,
        description=description,
        publisher=publisher,
        publishers=pubs,
        priority=priority,
        retry=RetryPolicy.NEVER,
        payload_keys=tuple(payload_keys),
    )


VERTEX_SPECS: list[EventSpec] = [
    # Voice
    _spec(VOICE_STARTED, "voice", "Voice subsystem started",
          payload_keys=("state",)),
    _spec(VOICE_STOPPED, "voice", "Voice subsystem stopped",
          payload_keys=("state",)),
    _spec(VOICE_STATE_CHANGED, "voice", "Voice runtime state changed",
          payload_keys=("old_state", "new_state"), priority="high"),
    _spec(VOICE_LISTENING_STARTED, "voice", "Microphone listening session began",
          payload_keys=("wake_required",)),
    _spec(VOICE_RECORDING_COMPLETED, "voice", "Audio recording finished",
          payload_keys=("audio_length", "duration")),
    _spec(VOICE_SPEAKER_IDENTIFIED, "voice", "Speaker recognized from audio",
          payload_keys=("speaker", "confidence")),
    _spec(VOICE_TRANSCRIPTION_COMPLETED, "voice", "Speech-to-text produced text",
          payload_keys=("text", "text_length", "audio_length", "duration")),
    _spec(VOICE_WAKE_DETECTED, "voice", "Wake word detected",
          payload_keys=("wake_word", "text")),
    _spec(VOICE_WAKE_FOUND, "voice", "Wake word found in idle listening",
          payload_keys=("text", "audio_length")),
    _spec(VOICE_RETURNED, "voice", "Conversation turn returned to idle",
          payload_keys=("text", "speaker", "wake_detected", "duration")),
    _spec(VOICE_ERROR, "voice", "Voice pipeline error",
          payload_keys=("type", "message")),
    # Memory / conversation
    _spec(MEMORY_EXTRACTED, "memory", "Memory extracted from a turn",
          payload_keys=("memory_id", "kind", "score")),
    _spec(MEMORY_STORED, "memory", "Memory persisted to store",
          payload_keys=("memory_id", "kind", "score")),
    _spec(MEMORY_CONSOLIDATED, "memory", "Memory consolidation cycle ran",
          payload_keys=("merged", "decayed", "new_relations")),
    _spec(MEMORY_LIFECYCLE, "memory", "Memory lifecycle event",
          payload_keys=("event", "memory_id")),
    _spec(CONVERSATION_FINISHED, "cognition",
          "Conversation turn completed and persisted",
          payload_keys=("text", "response", "memory_id"),
          other_publishers=("memory", "brain")),
    # Reasoning / learning
    _spec(REASONING_COMPLETED, "reasoning", "Reasoning cycle produced a result",
          payload_keys=("query", "conclusion", "confidence")),
    _spec(REFLECTION_GENERATED, "reasoning", "Reflection on a past event produced",
          payload_keys=("topic", "insight"),
          other_publishers=("cognition",)),
    _spec(LEARNING_GENERALIZED, "reasoning", "Learned pattern generalized",
          payload_keys=("pattern", "from", "to")),
    _spec(BEHAVIOR_ADJUSTED, "reasoning", "Agent behavior adjusted after reflection",
          payload_keys=("adjustments",),
          other_publishers=("cognition",)),
    # Agency / goals / tools / dreams
    _spec(GOAL_CREATED, "agency", "A goal was created",
          payload_keys=("id", "name", "category", "status")),
    _spec(GOAL_COMPLETED, "agency", "A goal reached completion",
          payload_keys=("id", "name", "category", "status")),
    _spec(GOAL_COMPLETED_REFLECTION, "agency", "Reflection emitted on goal completion",
          payload_keys=("id", "name", "reflection")),
    _spec(GOAL_CANCELLED, "agency", "A goal was cancelled",
          payload_keys=("id", "name", "status")),
    _spec(GOAL_AUTO_COMPLETED, "agency", "A goal auto-completed by guardrail",
          payload_keys=("id", "name", "category")),
    _spec(GOAL_TURNS_INCREMENTED, "agency", "A goal's progress turns incremented",
          payload_keys=("goal_id", "turns"), other_publishers=("cognition",)),
    _spec(AGENT_STEP, "agency", "Agent executed one tool step",
          payload_keys=("step", "tool", "query")),
    _spec(AGENT_COMPLETED, "agency", "Agent finished a task",
          payload_keys=("summary", "steps", "duration")),
    _spec(TOOL_REGISTERED, "agency", "A tool registered in the registry",
          payload_keys=("name",)),
    _spec(TOOL_CALLED, "agency", "A tool was invoked",
          payload_keys=("name", "success", "arguments")),
    _spec(WORLD_ENTITY_ADDED, "agency", "World model entity discovered",
          payload_keys=("name", "category")),
    _spec(EVOLUTION_ADJUSTED, "agency", "Personality traits adjusted",
          payload_keys=("traits",)),
    _spec(PREFERENCE_EVOLVED, "agency", "Evidence-based preference evolved",
          payload_keys=("changes",)),
    _spec(EXPERIENCE_RECORDED, "agency", "An emotional experience was recorded",
          payload_keys=("id", "significance")),
    _spec(PROCEDURAL_LEARNED, "agency", "A procedural memory was recorded",
          payload_keys=("skill", "steps")),
    _spec(DREAM_COMPLETED, "agency", "Dreaming cycle finished",
          payload_keys=("summary", "level", "tasks", "duration")),
    _spec(DREAM_STARTED, "agency", "Dreaming cycle began",
          payload_keys=("level",)),
    _spec(DREAM_ENDED, "agency", "Dreaming cycle ended",
          payload_keys=("level",)),
    # Emotion / cognition
    _spec(EMOTION_CHANGED, "cognition", "Dominant emotion changed",
          payload_keys=("type", "valence", "arousal", "confidence"), priority="high"),
    _spec(EMOTION_PROFILE_PUSHED, "cognition", "Emotion profile snapshot pushed",
          payload_keys=("profile",)),
    _spec(EMOTION_GOAL_SUGGESTED, "cognition", "Emotion-driven goal suggestion",
          payload_keys=("goal", "emotion", "reason")),
    _spec(SCHEDULER_TASK_COMPLETED, "scheduler", "Scheduled task ran",
          payload_keys=("task_id", "name", "success")),
    _spec(HEALTH_ERROR, "health", "Component reported a health error",
          payload_keys=("name", "status"), priority="high"),
    # Knowledge
    _spec(GRAPH_UPDATED, "knowledge", "Knowledge graph changed",
          payload_keys=("nodes", "edges", "entities"), other_publishers=("cognition",)),
    _spec(BELIEF_UPDATED, "knowledge", "A belief was created or strengthened",
          payload_keys=("belief_id", "topic", "strength")),
    _spec(BELIEF_GRAPH_SYNCED, "cognition", "Beliefs synced into the graph",
          payload_keys=("count",)),
    _spec(KNOWLEDGE_BUILD_COMPLETED, "knowledge", "Knowledge base build finished",
          payload_keys=("docs", "chunks", "memories")),
    _spec(RETRIEVER_RESULTS, "knowledge", "Retriever produced ranked results",
          payload_keys=("query", "count", "sources")),
    _spec(INDEXER_COMPLETED, "knowledge", "Indexer pass finished",
          payload_keys=("file", "chunks")),
    _spec(INDEXER_CHUNKS_INDEXED, "knowledge", "Chunks indexed for a document",
          payload_keys=("file", "count")),
    # State bus — UI projections (Phase 5). Priority "high" so UI renders
    # truth before lower-priority background traffic.
    _spec(STATE_VOICE_LISTENING, "voice", "Voice pipeline listening for input",
          payload_keys=("wake_required",), priority="high"),
    _spec(STATE_VOICE_SPEAKING, "voice", "Voice pipeline speaking (TTS active)",
          payload_keys=("text", "speaker"), priority="high"),
    _spec(STATE_VOICE_IDLE, "voice", "Voice pipeline returned to idle",
          payload_keys=(), priority="high"),
    _spec(STATE_VOICE_WAKE, "voice", "Wake word triggered listening",
          payload_keys=("wake_word", "text"), priority="high"),
    _spec(STATE_EMOTION_CHANGED, "cognition", "Dominant emotion changed (UI truth)",
          payload_keys=("dominant", "profile", "state"), priority="high"),
    _spec(STATE_MEMORY_UPDATED, "memory", "Memory persisted or consolidated (UI truth)",
          payload_keys=("kind", "node_id", "vector_count", "consolidated"), priority="high"),
    _spec(STATE_REASONING_BUSY, "cognition", "Reasoning turn started (UI truth)",
          payload_keys=(), priority="high"),
    _spec(STATE_REASONING_COMPLETE, "cognition", "Reasoning turn completed (UI truth)",
          payload_keys=("response", "mode", "user_input"), priority="high"),
    _spec(STATE_REASONING_REFLECTION, "cognition", "Background reflection produced (UI truth)",
          payload_keys=("summary", "topics", "patterns"), priority="high"),
    _spec(STATE_DREAMING_STARTED, "agency", "Dreaming cycle began (UI truth)",
          payload_keys=("level",), priority="high"),
    _spec(STATE_DREAMING_FINISHED, "agency", "Dreaming cycle finished (UI truth)",
          payload_keys=("level", "tasks", "duration"), priority="high"),
    _spec(STATE_KNOWLEDGE_UPDATED, "knowledge", "Knowledge graph changed (UI truth)",
          payload_keys=("entities_added", "relations_added"), priority="high"),
    _spec(STATE_BELIEF_UPDATED, "knowledge", "Belief set changed (UI truth)",
          payload_keys=("count",), priority="high"),
    _spec(STATE_GOAL_UPDATED, "agency", "Goal lifecycle change (UI truth)",
          payload_keys=("event", "id", "name", "priority"), priority="high"),
    _spec(STATE_AGENT_COMPLETED, "agency", "Agent task completed (UI truth)",
          payload_keys=("task", "steps", "success"), priority="high"),
    _spec(STATE_NEEDS_UPDATED, "cognition", "Psychological needs updated (UI truth)",
          payload_keys=("needs", "triggered", "unmet"), priority="high"),
    _spec(STATE_MONOLOGUE_GENERATED, "cognition", "Internal monologue packet produced (UI truth)",
          payload_keys=("thought", "decision", "speech_plan", "response"), priority="high"),
    _spec(STATE_RETRIEVAL_STARTED, "memory", "Memory retrieval began (UI truth)",
          payload_keys=(), priority="normal"),
    _spec(STATE_RETRIEVAL_COMPLETED, "memory", "Memory retrieval finished (UI truth)",
          payload_keys=("count",), priority="normal"),
    _spec(STATE_TOOL_STARTED, "agency", "Tool execution began (UI truth)",
          payload_keys=("name",), priority="normal"),
    _spec(STATE_TOOL_COMPLETED, "agency", "Tool execution finished (UI truth)",
          payload_keys=("name", "success", "duration"), priority="normal"),
]


def register_event_specs(bus, replace: bool = False) -> int:
    """Seed an EventBus registry with the full semantic event catalog."""
    registry = getattr(bus, "registry", None)
    if isinstance(registry, EventRegistry):
        return registry.register_many(VERTEX_SPECS)
    if hasattr(bus, "register_spec"):
        for spec in VERTEX_SPECS:
            bus.register_spec(spec, replace=replace)
        return len(VERTEX_SPECS)
    raise TypeError("Expected an EventBus or EventRegistry")