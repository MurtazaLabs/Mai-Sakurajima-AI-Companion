# Conversation Management

## Turn-Taking States

```
LISTENING → (speech_start) → RECEIVING → (speech_end) → PROCESSING
  ↑                                                         │
  │                                                   (response ready)
  │                                                         ↓
  └───────────────────────── LISTENING ←── SPEAKING ←── RESPONDING
                                  │
                             (interruption)
                                  ↓
                            LISTENING (immediate)
```

## Pause Detection

- Natural pause: 500ms of silence after speech
- Thinking pause: 1-2s silence (user is thinking)
- Completion pause: 3s+ silence (user finished)
- Silence threshold: user-configurable (default: 500ms / 2000ms / 3000ms)

## Timeout

- No speech detected for 30s → return to idle
- Partial utterance with >5s mid-sentence pause → prompt "were you still talking?"
- Conversation timeout configurable in settings

## Voice-Thread Safety

- Conversation manager runs on main event loop
- Audio processing runs on dedicated thread
- LLM/reasoning runs on worker threads
- State synchronization via asyncio.Queue
- Never hold locks across thread boundaries