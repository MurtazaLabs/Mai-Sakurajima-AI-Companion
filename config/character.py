CHARACTER_MONOLOGUE_ENABLED = True

# M5 · Greeting-first conversation experience.
# Greeting-first is the DEFAULT: on launch, Mai greets and opens the
# conversation once per session. Wake word remains a fully functional
# compatibility mode — the wake machinery is never removed.
GREETING_FIRST_ENABLED = True
# Seconds of boot settle before the launch greeting fires.
GREETING_FIRST_DELAY_SECONDS = 2.0

# M6 · Emotional experience + growth.
# Evidence threshold and cadence for preference evolution (overlay on the
# canonical likes/dislikes — never mutates them directly).
PREFERENCE_EVOLUTION_EVIDENCE_THRESHOLD = 3
PREFERENCE_EVOLUTION_CADENCE_DAYS = 7
# Dreaming revisits experiences with significance >= this value.
EXPERIENCE_DREAM_SIGNIFICANCE = 0.6

# M11/M12 follow-up · Bounded retry when the model emits an envelope without
# usable speech (the truncated-JSON artifact): one speech-only retry attempt
# before the honest empty reply. Never leaks machinery; strictly bounded.
CHAT_EMPTY_REPLY_RETRY = True
CHAT_EMPTY_REPLY_RETRY_SUFFIX = (
    "\n\n(Important: reply with your spoken words only — plain speech, "
    "no JSON envelope, no explanation, no commentary.)"
)