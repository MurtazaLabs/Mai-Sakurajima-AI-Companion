# Interruptions

## Detection

Interruption is detected when:
1. VAD detects speech_start while TTS is actively playing
2. Audio capture receives signal > silence threshold during TTS playback

## Flow

```
VAD: SPEECH_START during TTS playback
  → TTS.stop()  (immediate)
  → AudioPlayback.stop() (flush buffer)
  → LLM.cancel() (cancel pending generation)
  → ConversationManager.reset()
  → VAD continues listening normally
  → User finishes speaking
  → Normal pipeline resumes
```

## After Interruption

Mai should acknowledge the interruption naturally:
- If user continued the same topic: continue from current context
- If user changed topic: switch context, forget interrupted response
- If user asked a question about the interruption: address it

## Safety

- Interruption handler runs on VAD thread (no latency)
- TTS.stop() must be thread-safe
- Audio buffer flush must be <10ms
- LLM cancellation propagates through the reasoning pipeline
- If cancellation fails (model doesn't support), TTS stops anyway — user gets visual response