/**
 * Visual state adapter — the only sanctioned bridge between backend events and
 * the MAI entity.
 *
 * Contract (v4.0 §25, §33, §34):
 *
 *   Backend -> API/Event -> THIS ADAPTER -> entity state -> visual behaviour
 *
 * Three rules this module enforces, because they are what keeps a companion
 * interface honest:
 *
 *   1. **Never invent a value.** A field the backend does not report stays
 *      `null`. It is never defaulted to a plausible number, and `null` is
 *      meaningfully different from `false` — "unknown" is not "idle".
 *   2. **Never animate a state nobody published.** The entity renders this
 *      object; it does not run its own timers to look busy.
 *   3. **Never get stuck.** Activity flags are driven by start/complete pairs
 *      with a decay guard, so a dropped completion event degrades to idle
 *      instead of leaving the entity permanently "thinking".
 *
 * The adapter is deliberately free of Three.js, GSAP, and the DOM so it can be
 * unit tested under Node and reused by every workspace.
 */

/** Entity state machine (v4.0 §7). */
export const EntityMode = {
  IDLE: "idle",
  LISTENING: "listening",
  THINKING: "thinking",
  MEMORY_RETRIEVAL: "memory_retrieval",
  REASONING: "reasoning",
  TOOL_EXECUTION: "tool_execution",
  SPEAKING: "speaking",
  DEGRADED: "degraded",
  OFFLINE: "offline",
};

/** Backend topics this adapter consumes. */
export const Topics = {
  VOICE_LISTENING: "state.voice.listening",
  VOICE_SPEAKING: "state.voice.speaking",
  VOICE_IDLE: "state.voice.idle",
  VOICE_WAKE: "state.voice.wake",
  EMOTION_CHANGED: "state.emotion.changed",
  REASONING_BUSY: "state.reasoning.busy",
  REASONING_COMPLETE: "state.reasoning.complete",
  RETRIEVAL_STARTED: "state.retrieval.started",
  RETRIEVAL_COMPLETED: "state.retrieval.completed",
  TOOL_STARTED: "state.tool.started",
  TOOL_COMPLETED: "state.tool.completed",
  GOAL_UPDATED: "state.goal.updated",
  DREAMING_STARTED: "state.dreaming.started",
  DREAMING_FINISHED: "state.dreaming.finished",
};

/**
 * How long an activity flag survives without its completion event.
 * Retrieval and tool calls are fast; anything longer than this is a dropped
 * event, not real work.
 */
export const ACTIVITY_TIMEOUT_MS = 15000;

/**
 * The initial contract. Every field is unknown (`null`) except the two that
 * have a defensible starting value: the cognitive loop is not running before
 * the first event arrives, and connectivity is genuinely unknown until the
 * health endpoint answers.
 */
export function initialState() {
  return {
    presence: null,
    cognitiveState: "idle",
    emotion: null,
    // v4.0 lists `energy` in the contract, but no backend field reports it.
    // It stays null until a real source exists rather than being animated as
    // a decorative number. See ADR "Entity state provenance".
    energy: null,
    voiceState: null,
    connection: "unknown",
    memoryActivity: null,
    memoryCount: null,
    toolActivity: null,
    activeTool: null,
    goalActivity: null,
    lastEventAt: null,
  };
}

function withEvent(state, patch, now) {
  return { ...state, ...patch, lastEventAt: now };
}

/**
 * Apply one backend event.
 *
 * Returns a new state object; the input is never mutated so a workspace can
 * diff cheaply. Unrecognised topics are ignored rather than guessed at.
 *
 * @param {object} state  current state (from `initialState()` or a prior call)
 * @param {string} topic  backend event topic
 * @param {object} payload event payload
 * @param {object} [options]
 * @param {number} [options.now] injectable clock for deterministic tests
 * @returns {object} next state
 */
export function applyEvent(state, topic, payload = {}, options = {}) {
  const now = options.now ?? Date.now();
  const data = payload && typeof payload === "object" ? payload : {};

  switch (topic) {
    /* ── Voice ─────────────────────────────────────────────────────────── */
    case Topics.VOICE_LISTENING:
    case Topics.VOICE_WAKE:
      return withEvent(state, { voiceState: "listening" }, now);
    case Topics.VOICE_SPEAKING:
      return withEvent(state, { voiceState: "speaking" }, now);
    case Topics.VOICE_IDLE:
      return withEvent(state, { voiceState: "idle" }, now);

    /* ── Emotion ───────────────────────────────────────────────────────── */
    case Topics.EMOTION_CHANGED: {
      // The backend reports the dominant emotion. Absent a name we report
      // `null` rather than defaulting to a mood.
      const name = data.emotion || data.name || data.dominant || null;
      return withEvent(state, { emotion: name }, now);
    }

    /* ── Reasoning ─────────────────────────────────────────────────────── */
    case Topics.REASONING_BUSY:
      return withEvent(state, { cognitiveState: "busy" }, now);
    case Topics.REASONING_COMPLETE:
      return withEvent(state, { cognitiveState: "idle" }, now);

    /* ── Memory retrieval ──────────────────────────────────────────────── */
    case Topics.RETRIEVAL_STARTED:
      return withEvent(state, { memoryActivity: true, memoryCount: null }, now);
    case Topics.RETRIEVAL_COMPLETED:
      return withEvent(
        state,
        { memoryActivity: false, memoryCount: countOrNull(data.count) },
        now,
      );

    /* ── Tool execution ────────────────────────────────────────────────── */
    case Topics.TOOL_STARTED:
      return withEvent(state, { toolActivity: true, activeTool: data.name ?? null }, now);
    case Topics.TOOL_COMPLETED:
      return withEvent(state, { toolActivity: false, activeTool: null }, now);

    /* ── Goals ─────────────────────────────────────────────────────────── */
    case Topics.GOAL_UPDATED:
      return withEvent(state, { goalActivity: true }, now);

    /* ── Dreaming is background cognition; it is not a user-facing mode ── */
    case Topics.DREAMING_STARTED:
    case Topics.DREAMING_FINISHED:
      return state;

    default:
      return state;
  }
}

function countOrNull(value) {
  return Number.isFinite(value) ? value : null;
}

/**
 * Fold a batch of events in order.
 */
export function applyEvents(state, events, options = {}) {
  return (events || []).reduce(
    (current, event) => applyEvent(current, event?.topic, event?.payload ?? {}, options),
    state,
  );
}

/**
 * Connection is owned by the health check and the SSE transport, not by a
 * backend topic, so it is set explicitly rather than inferred.
 */
export function setConnection(state, connection) {
  const allowed = ["connected", "degraded", "offline", "unknown"];
  const value = allowed.includes(connection) ? connection : "unknown";
  return { ...state, connection: value, lastEventAt: Date.now() };
}

/**
 * Decay activity flags that never received their completion event.
 *
 * Call from a timer or before each render. Returns the same object when
 * nothing changed so consumers can skip re-rendering.
 */
export function decayStaleActivity(state, options = {}) {
  const now = options.now ?? Date.now();
  const timeout = options.timeoutMs ?? ACTIVITY_TIMEOUT_MS;
  if (state.lastEventAt === null) return state;
  if (now - state.lastEventAt < timeout) return state;

  const stale = {};
  if (state.memoryActivity === true) {
    stale.memoryActivity = false;
    stale.memoryCount = null;
  }
  if (state.toolActivity === true) {
    stale.toolActivity = false;
    stale.activeTool = null;
  }
  if (Object.keys(stale).length === 0) return state;
  return { ...state, ...stale };
}

/**
 * Map the contract onto a single entity mode.
 *
 * Precedence is deliberate: availability beats activity, activity beats
 * cognition. A user must never be shown "thinking" while the system is
 * actually offline, and speech is the most visible thing MAI can do.
 */
export function deriveMode(state) {
  if (!state) return EntityMode.IDLE;

  if (state.connection === "offline") return EntityMode.OFFLINE;
  if (state.connection === "degraded") return EntityMode.DEGRADED;

  if (state.voiceState === "speaking") return EntityMode.SPEAKING;
  if (state.voiceState === "listening") return EntityMode.LISTENING;

  if (state.toolActivity === true) return EntityMode.TOOL_EXECUTION;
  if (state.memoryActivity === true) return EntityMode.MEMORY_RETRIEVAL;

  if (state.cognitiveState === "busy") return EntityMode.REASONING;

  return EntityMode.IDLE;
}

/**
 * True when the entity has received no backend signal at all, so the
 * interface can show a neutral presence rather than an invented mood.
 */
export function isUninitialised(state) {
  return !state || state.lastEventAt === null;
}

/**
 * A compact, log-safe projection. Useful for debugging and for asserting in
 * tests that no private content crossed the boundary.
 */
export function toProjection(state) {
  return {
    mode: deriveMode(state),
    emotion: state?.emotion ?? null,
    energy: state?.energy ?? null,
    voice: state?.voiceState ?? null,
    connection: state?.connection ?? "unknown",
    memoryActive: state?.memoryActivity ?? null,
    memoryCount: state?.memoryCount ?? null,
    toolActive: state?.toolActivity ?? null,
    goalActive: state?.goalActivity ?? null,
  };
}

/**
 * Subscribe to an EventBus-compatible object. Returns an unsubscribe function.
 *
 * Only `state.*` topics are accepted. `data.*` topics carry private payloads
 * and are not part of the presentation contract.
 */
export function bindToEventBus(bus, onChange, options = {}) {
  if (!bus || typeof bus.on !== "function") return () => {};
  const allowed = new Set(Object.values(Topics));
  const unsubscribes = [];

  for (const topic of allowed) {
    const off = bus.on(topic, event => {
      const next = applyEvent(current, topic, event?.detail ?? event?.payload ?? {}, options);
      current = next;
      onChange?.(next, topic);
    });
    if (typeof off === "function") unsubscribes.push(off);
  }

  let current = options.initialState ?? initialState();
  return () => unsubscribes.forEach(off => { try { off(); } catch { /* already detached */ } });
}
