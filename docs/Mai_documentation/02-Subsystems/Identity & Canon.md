# Identity & Canon Reference

> Complete reference for the character identity system — `core/identity/`, canon volumes, `IdentityCore`, `PreferenceEvolution`, `ExperienceStore`.

---

## Overview

The character layer (M0–M13) is built on a **canon book** + **read-only projections** + **evolved overlays**. The canon never mutates; evolution happens via overlays.

**Architecture:** [[01-Architecture/03-Core Brain Kernel & State]] • [[01-Architecture/10-Status & Debt]] (M-series gates)

---

## Canon Book (Volumes I–IV)

Located at `core/identity/character/`:

| Volume | File | Content |
|--------|------|---------|
| I | `volume-01-identity.md` | Core identity, name, origin, purpose |
| II | `volume-02-speech.md` | Speech patterns, vocabulary, pacing, humor, honorifics |
| III | `volume-03-relationships.md` | Relationship philosophy, trust tiers, boundaries, intimacy |
| IV | `volume-04-rule-resolution.md` | **7-tier conflict priority** (see below) |

**Registration:** `core/identity/canonical.py` — loads volumes, registers keys, drift-checked by `TestCanonDrift`.

---

## 7-Tier Conflict Resolution (Volume IV)

Priority order (higher tier governs *expression*, never *feeling*):

1. **Boundaries & Safety** (Vol I, absolute)
2. **Core Values**
3. **Relationship Preservation** (Vol III)
4. **Emotional Honesty** (Vol II)
5. **Independence & Self-Respect**
6. **Playfulness & Humor**
7. **Surface Expression**

**Principles:**
- Ties resolve to relationship + honesty
- Restraint default at low trust
- Warmth earned via closeness

**Access:** `IdentityCore.get_conflict_resolution()` — read-only projection (not yet promoted into prompts).

---

## IdentityCore (`core/identity/identity_core.py`)

Central read-only projection layer:

| Method | Returns | Notes |
|--------|---------|-------|
| `get_current_identity()` | `dict` | canon + evolved overlay (deepcopy) |
| `get_preferences()` | `dict` | `{"likes": [...], "dislikes": [...], "neutral": [...]}` — overlay-aware |
| `get_conflict_resolution()` | `dict` | Volume IV rules (canon policy) |
| `attach_preference_overlay()` | `None` | snapshot evolved prefs as read-only overlay |

**Critical invariant:** `attach_preference_overlay()` takes a **read-only snapshot** — evolved preferences never mutate canon. Canonical `core/identity/preferences.py` stays pristine.

---

## Preference Evolution (`agency/preference_evolution.py`)

**Evidence-based preference learning:**

| Parameter | Value |
|-----------|-------|
| Evidence window | N ≥ 3 occurrences |
| Cadence | weekly (≥1 day clamped) |
| Direction flip | effective-list comparison (canon + overlay) |
| Decision trail | `{timestamp, topic, before, after, reason}` |
| Persistence | JSONL + `revert()` support |
| Events | publishes `PREFERENCE_EVOLVED` |
| Callback | `on_change` → refreshes identity overlay |

**Overlay shape:** `overlay_map()` — single source of `{"topic": {"list": [...]}}` for `IdentityCore.attach_preference_overlay()`.

**Fixed (M8):** Production bug where `evolved_preferences()` returned wrong shape → `AttributeError` on `get_preferences()`.

---

## Experience System (`memory/experience.py`)

### EmotionExperience

```python
@dataclass
class EmotionExperience:
    event: str              # raw turn text
    meaning: str            # filled at dream L5 reflection
    emotion: str            # emotion name at ingest
    relationship_impact: float
    reflection: str         # filled at dream L5
    lessons: str            # filled at dream L5
    growth: str             # filled at dream L5
    significance: float     # 0–1
    timestamp: float
```

### ExperienceStore

- JSONL append-only (RLock)
- `record(experience)` — **md5 replay dedup** (identical text recorded once; `stats()["deduped"]`)
- `mark_reflected(id)` — fills meaning/lessons/growth (lazy, at dream L5)
- Cheap fields at ingest; reflection/lessons/growth filled later

### Integration

1. **Store:** Charged turns (emotion intensity ≥ 0.6) recorded at `_store_impl()` — one JSONL append
2. **MemoryObject:** `emotion_experience` field carries link (additive, backward compatible)
3. **Dreaming:** Level-5 task `experience_reflection` — LLM reflection over significant unreflected experiences; knowledge entry per revisit; `DreamReport.experiences_reflected` metric
4. **Retrieval:** `MemoryCoordinator.experience_context()` — Dice-relevance gate ≥ 0.10 (M12), injects reflected experiences into prompt only when relevant
5. **Prompt:** `prompt/context.py` — EXPERIENTIAL MEMORIES section with character instruction: *"refer to it the way Mai would remember it: lightly, never announcing the memory itself, its scores, or this list"*

---

## Behavioral Validation (M7)

**Harness:** `tests/behavior/` — `ScenarioDriver` with virtual clock, causal traces, deterministic ThoughtPacket fixtures.

**6 Scenarios (all green):**
1. Baseline consistency (5 unrelated turns, ±0.10 bands)
2. Praise → recognition (invisible machinery)
3. Jealousy across trust tiers (low=0.0 exact below gate 0.40)
4. Reassurance → monotone jealousy decay ≤60% by turn 4
5. Preference emergence (N≥3 → overlay, trail, `PREFERENCE_EVOLVED`)
6. Experience → L5 dream → reflection + knowledge entry

**Renderer parity:** Same packet+style+prosody through KokoroRenderer / StubRenderer / duck-typed third — semantic identity only.

**Trace isolation:** `causal_trace`/`deltas`/`snapshot`/`mechanisms` absent from `prompt/` + `core/prompt_builder.py`.

---

## M-Series Gates (Character Layer)

| Gate | Scope | Key Files |
|------|-------|-----------|
| M0 | Canon volumes I–IV | `core/identity/character/` |
| M1 | Identity core | `identity_core.py`, `canonical.py` |
| M2 | Relationship engine | `core/state/relationship.py` |
| M3 | Needs engine | `core/needs_engine.py` |
| M4 | Emotion system | `core/emotion.py`, `emotion_system.py` |
| M5 | Greeting-first | `core/os_kernel.py` (greeting_first=) |
| M6 | Experience + preference evolution | `experience.py`, `preference_evolution.py` |
| M7 | Behavioral validation | `tests/behavior/` |
| M8 | Consumers (pref/experience in prompt) | `memory_coordinator.py`, `prompt_orchestrator.py` |
| M9 | Real-world evaluation | `evaluation/` |
| M10 | Relationship on chat path | `core/state/relationship.py` (deterministic deltas) |
| M11 | ThoughtPacket leak guard | `reasoning/thought_packet.py` |
| M12 | Experience in speech | `memory_coordinator.experience_context()` |
| M13 | Conflict coherence | Volume IV, `identity_core.get_conflict_resolution()` |

---

## Wiki Links

**Architecture:** [[01-Architecture/03-Core Brain Kernel & State]] • [[01-Architecture/10-Status & Debt]] — M-series gates  
**Related:** [[01-Architecture/04-Memory Subsystem]] — experience store • [[01-Architecture/06-Agency Reasoning LLM & Execution]] — preference evolution • [[02-Subsystems/Memory Pipeline]] — experience recording • [[02-Subsystems/Event System]] — PREFERENCE_EVOLVED event