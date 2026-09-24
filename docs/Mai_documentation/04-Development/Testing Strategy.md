# Testing Strategy

> Overview of the Mai AI test suite, behavior harness, evaluation framework, and testing conventions.

---

## Test Suite Overview (Aug 2026)

| Metric | Value |
|--------|-------|
| **Total tests** | 1,821+ passing |
| **Test files** | 55 (incl. `tests/behavior/`) |
| **Coverage** | Core subsystems well-covered; api/, knowledge/ improving |
| **Framework** | pytest with asyncio, fixtures, parametrize |

## Test Organization

```
tests/
├── conftest.py              # shared fixtures, async event loop
├── test_*.py                # subsystem test files (40+)
├── behavior/                # M7+ character behavioral harness
│   ├── harness.py           # ScenarioDriver, virtual clock, causal traces
│   ├── fixtures.py          # deterministic ThoughtPacket fixtures
│   ├── test_causal_trace.py
│   ├── test_character_behavior.py
│   ├── test_conflict_resolution.py
│   └── test_renderer_parity.py
└── evaluation/              # M9 real-world evaluation
    ├── rubric.py            # 7-axis CharacterRubric
    ├── runner.py            # SessionRunner, FakeLLM, build_stub_brain()
    ├── scenarios.py         # seed scripts
    └── transcript.py        # SessionTranscript JSONL
```

## Key Test Categories

### 1. Unit / Integration Tests (per subsystem)

| Subsystem | Test File | Focus |
|-----------|-----------|-------|
| core | `test_core.py`, `test_brain.py`, `test_event_bus*.py` | Brain, kernel, event fabric, state |
| memory | `test_memory.py`, `test_experience.py` | pipeline, vector store, experience store |
| knowledge | `test_knowledge.py` (110KB!) | graph, vault, retriever, beliefs, janitor |
| voice | `test_voice.py`, `test_voice_tier3.py`, `test_voice_tier4.py` | pipeline, VAD, STT, TTS, interruption |
| agency | `test_agency.py`, `test_agency_advanced.py` | tools, agent, goals, dreaming, evolution |
| reasoning | `test_reasoning.py` | engine, journal, reflection, learning |
| api | `test_integration.py`, `test_observability.py` | REST, SSE, WS, health, auth |
| config | `test_config.py` | settings validation |
| native | `test_execution.py` | hotkeys, tray, clipboard, FS |

### 2. Behavior Harness (`tests/behavior/`) — M7+

**Purpose:** Prove the character layer (M0–M13) behaves like Mai without LLM calls.

**Components:**
- `ScenarioDriver` — runs scripted multi-turn conversations
- Virtual clock — patches `time.time` in `core.emotion` + `core.needs_engine`
- `causal_trace` per turn — relationship/needs/emotion deltas, ThoughtPacket, style, prosody, renderer, mechanisms
- Deterministic ThoughtPacket fixtures — LLM completely stubbed

**6 Scenarios (all green):**
1. Baseline consistency (5 unrelated turns, ±0.10 bands)
2. Praise → recognition (invisible machinery)
3. Jealousy across trust tiers (low=0.0 exact below gate 0.40)
4. Reassurance → monotone jealousy decay ≤60% by turn 4
5. Preference emergence (N≥3 → overlay, trail, `PREFERENCE_EVOLVED`)
6. Experience → L5 dream → reflection + knowledge entry

**Renderer parity:** Same packet+style+prosody through KokoroRenderer / StubRenderer / duck-typed third renderer — semantic identity only, acoustic realization differs.

**Trace isolation:** `causal_trace`/`deltas`/`snapshot`/`mechanisms` absent from `prompt/` + `core/prompt_builder.py`.

### 3. Evaluation Framework (`evaluation/`) — M9

**Purpose:** Unscripted LLM-driven sessions, persisted transcripts, mechanical rubric + human review.

**Modes:**
- **Stub mode** (CI) — `FakeLLM`, `build_stub_brain()` — real Brain/Emotion/Orchestrator on real-numeric stub state
- **Real mode** (`--mode real`) — full application + configured LLM

**Rubric (7 axes):**
1. Transcript quality
2. Emotion responsiveness (real valence engine verified moving)
3. Boundary consistency (no "as an AI", no mechanism keys)
4. Preference visibility
5. Experience visibility
6. Relationship trajectory (trust non-decreasing)
7. Repetition control

Unexercised/low (< 3) axes force `review_required=True` — human is the judge.

## Testing Conventions

### Fixtures (`conftest.py`)
- `event_loop` — session-scoped asyncio loop
- `temp_dir` — temporary directory for each test
- `mock_llm` — configurable FakeLLM responses
- `brain` — constructed Brain with stubbed deps

### Naming
- `test_<subsystem>_<feature>.py` — subsystem tests
- `Test<ClassName>` — class-based test groups
- `test_<scenario>_<expectation>` — descriptive test names

### Async Patterns
```python
# Async test with pytest-asyncio
async def test_async_operation():
    result = await some_async_call()
    assert result.success

# Thread-safe checks
def test_thread_safety():
    with ThreadPoolExecutor() as ex:
        futures = [ex.submit(op) for _ in range(10)]
        for f in futures:
            assert f.result().ok
```

### Mocking LLM
```python
# Use FakeLLM for deterministic tests
fake_llm = FakeLLM(responses=["response 1", "response 2"])
brain = build_stub_brain(llm=fake_llm)
```

## Running Tests

```bash
# All tests
pytest

# Specific subsystem
pytest tests/test_memory.py -v

# Behavior harness
pytest tests/behavior/ -v

# Evaluation (stub mode)
pytest tests/test_evaluation.py -v

# Real mode (requires LLM config)
python -m evaluation.runner --mode real --scenario praise --turns 5

# With coverage
pytest --cov=. --cov-report=html
```

## CI/CD Integration

- Tests run on every push via GitHub Actions
- Required: 0 failures, 1,800+ passing
- Behavior harness runs in stub mode (fast, deterministic)
- Real-mode evaluation runs on schedule / manual trigger

---

## Wiki Links

**Related:** [[01-Architecture/10-Status & Debt]] — test counts per M-gate • [[01-Architecture/03-Core Brain Kernel & State]] — core test focus • [[04-Development/Deployment Guide]] — CI/CD