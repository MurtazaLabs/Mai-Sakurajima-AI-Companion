# Testing Strategy

> Overview of the Mai AI test suite, behavior harness, evaluation framework, and testing conventions.

---

## Test Suite Overview (Nov 2026)

| Metric | Value |
|--------|-------|
| **Total tests** | 2,035 collected; 2,033 passing + 2 skipped, 0 failures (live-verified Nov 8 2026 under mai_env, 3m05s) |
| **Test modules** | 77 `test_*.py` (88 py files under `tests/`, 23,658 lines) |
| **Coverage** | Core subsystems well-covered; api/, knowledge/ improving |
| **Framework** | pytest with asyncio, fixtures, parametrize |
| **Interpreter** | `mai_env/` is the real runtime (voice stack: kokoro, faster-whisper, speechbrain, webview, pystray…) — base Python only runs a wounded subset |

> The 2 skips are environment-gated: `tests/test_doc_system.py` requires the developer-local OpenCode/Obsidian config and is **not** a documentation validator.

## Test Organization

```
tests/
├── conftest.py              # shared fixtures, async event loop
├── test_*.py                # subsystem test files (77 modules)
│   ├── test_brain.py        # + TestBrainNoResponseCache, stream-guard, think_stream action path
│   ├── test_desktop_app.py  # M14: AppWindow, tray, autostart, single-instance, MaiAPI wiring
│   ├── test_voice_gating.py # Phase 0: utterance VAD gate + diarization full-clip
│   ├── test_sandbox.py      # path containment, symlink escape, eval lockdown
│   ├── test_web_scraper.py  # explicit-intent, SSRF guard, connected-peer check
│   ├── test_auth_oidc.py    # OIDC/SAML, cookies, redirect allowlist
│   ├── test_rate_limiter.py / test_scheduler.py / test_vad.py / test_vector_store.py
│   └── test_llm.py          # OpenRouter sanitization, retry budget, provider preference, failover
├── behavior/                # M7+ character behavioral harness
│   ├── harness.py           # ScenarioDriver, virtual clock, causal traces
│   ├── fixtures.py          # deterministic ThoughtPacket fixtures
│   ├── test_causal_trace.py
│   ├── test_character_behavior.py
│   ├── test_conflict_resolution.py
│   └── test_renderer_parity.py
└── evaluation/              # M9 real-world evaluation (in evaluation/ package)
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
- Required: 0 failures, 1,900+ passing
- Behavior harness runs in stub mode (fast, deterministic)
- Real-mode evaluation runs on schedule / manual trigger

> Gate numbers per milestone are tracked in [[01-Architecture/10-Status & Debt]]. Latest verified gate: **2,033 passed / 2 skipped (2,035 collected), Nov 8 2026**.

---

## Wiki Links

**Related:** [[01-Architecture/10-Status & Debt]] — test counts per M-gate • [[01-Architecture/03-Core Brain Kernel & State]] — core test focus • [[04-Development/Deployment Guide]] — CI/CD