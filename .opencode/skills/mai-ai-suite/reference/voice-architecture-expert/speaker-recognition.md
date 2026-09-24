# Speaker Recognition

## Approach

| Task | Library | Model | Accuracy |
|------|---------|-------|----------|
| Speaker embedding | SpeechBrain | ecapa-tdnn | 95%+ |
| Speaker diarization | Pyannote | pyannote-audio | 90%+ |
| Speaker identification | Resemblyzer | vocoder-based | 85%+ |

## Speaker Profiles

```python
@dataclass
class SpeakerProfile:
    id: str
    name: str
    embedding: np.ndarray  # 512-dim ECAPA embedding
    first_seen: datetime
    last_seen: datetime
    conversation_count: int
    average_confidence: float
```

## Profile Management

- New speaker: create profile with first embedding
- Known speaker: update embedding (running average), update last_seen
- Unknown: label as "Unknown" until user provides name
- Profiles stored in MemoryState, synced to vault

## Integration

Speaker recognition runs in parallel with STT. When STT produces a transcript segment, speaker recognition identifies who spoke it. The speaker tag is attached to the utterance for memory and relationship tracking.