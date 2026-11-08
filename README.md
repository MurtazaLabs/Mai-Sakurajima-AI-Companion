# Mai — AI Companion

A local-first, single-user AI companion inspired by Mai Sakurajima, built as a modular Python platform rather than a chatbot. Mai has persistent memory, a stable character, emotional and relationship continuity, real-time voice conversation, and an agent/tool layer, all running on your own machine.

> **Status:** active development. The core platform, character layer (M0–M13), and desktop app (M14) are working and in daily use. Roadmap items M15–M26 have not started. See [What works today](#what-works-today) for an honest breakdown.

> **Fan project notice:** this is an independent, non-commercial project inspired by a fictional character. It is not affiliated with or endorsed by the character's original creators or publishers. See [`docs/Mai_documentation/03-Features/Character Rename PRD.md`](docs/Mai_documentation/03-Features/Character%20Rename%20PRD.md) for the naming and trademark plan.

---

## Features

- **Character and relationship layer:** four canon volumes (identity, speech and emotion, relationships, conflict rules), an emotion and needs engine, relationship dynamics that evolve across conversations, and a behavioral test harness that guards against character drift.
- **Long-term memory:** a unified memory pipeline backed by ChromaDB (with SQLite/JSON fallback), importance scoring, decay and consolidation, and relevance-gated recall of past experiences.
- **Knowledge graph and beliefs:** a three-layer graph (entities, typed brain graph, versioned beliefs) compiled into an Obsidian-compatible vault, so you can read and browse what Mai remembers.
- **Voice:** wake word via STT phrase matching, Silero VAD, faster-whisper STT, Kokoro TTS, sentence-level streaming, and barge-in interruption.
- **Agency:** 16 built-in tools, a multi-step agent loop, goals with auto-advance, procedural memory, a world model, and a dreaming/reflection cycle.
- **Interfaces:** FastAPI server (REST, SSE, WebSocket), a web UI, a Windows desktop app (pywebview, tray, global hotkeys), and a signed plugin system.
- **Operations:** JWT auth, rate limiting, auto-generated dev HTTPS, Prometheus `/metrics`, health registry, Docker deployment, and GitHub Actions CI.

## What works today

| Area | Status |
|------|--------|
| Text conversation, memory, knowledge graph, character layer | Working |
| REST / SSE / WebSocket API and web UI | Working |
| Voice loop (wake, VAD, STT, TTS, barge-in) | Working, with known latency limits |
| Windows desktop app (tray, hotkeys, autostart) | Working |
| Docker deployment | Working (no voice; single replica) |
| Echo cancellation | Partial: the AEC module exists but isn't fed playback audio; the mic is muted while Mai speaks |
| Kyutai STT | Opt-in; slower than the real-time target on a 4 GB GPU |
| openWakeWord | Installed, not wired; no "hey mai" model yet |
| Discord | Prototype only |
| Cloud sync, WhatsApp, entity web interface, Java client | Not started |

The authoritative, code-verified status lives in [`docs/Mai_documentation/00-Overview/CURRENT_STATE.md`](docs/Mai_documentation/00-Overview/CURRENT_STATE.md).

## Architecture at a glance

```
run.py | run_daemon.py | uvicorn api.server:app
        └── ApplicationBuilder.build()   (8 phases)
              Infrastructure → Cognition → Memory → Knowledge
              → Reasoning → Agency → Voice → Runtime
                    └── AIApplication (DI container)
                          └── AIOSKernel (conversation state machine)
                                └── Brain.think() / think_stream()
```

A single `Brain.think()` turn runs parallel retrieval (vector, beliefs, graph, attention), assembles a prompt (character, emotion, context, identity overlay, experiences), calls the LLM, then runs post-think hooks (relationship updates, reflection, beliefs, goals, learning). Subsystems communicate through a central event bus carrying `data.*` and `state.*` messages.

| Package | Role |
|---------|------|
| `core/` | Brain facade, OS kernel, event fabric, emotion, identity canon |
| `memory/` | Memory pipeline, vector store, experience store, preference evolution |
| `knowledge/` | Entity graph, beliefs, retriever, vault writers |
| `voice/` | Wake, VAD, STT, TTS, interruption, speaker ID |
| `agency/` | Tools, agent loop, goals, world model, dreaming |
| `llm/` | Provider manager (OpenRouter, Ollama) with failover |
| `api/` | FastAPI server, auth, SSE/WebSocket, static web UI |
| `native/` | Tray, hotkeys, notifier, desktop window |
| `plugins/` | Manifest, lifecycle, signing, sandbox, marketplace client |
| `app/`, `config/` | Builders, validation, environment-backed settings |
| `observability/`, `monitoring/` | Health registry, tracing, metrics |
| `evaluation/`, `tests/` | Real-world evaluation harness, behavior and unit tests |

Full details are in [`docs/Mai_documentation/01-Architecture/`](docs/Mai_documentation/01-Architecture/01-System%20Overview.md).

## Getting started

### Requirements

- Python 3.10
- Windows is the primary supported platform (the desktop app and voice stack are developed there). The API and text chat should run elsewhere; Docker is the recommended server option.
- An LLM provider: OpenRouter (cloud, default) or a local Ollama install. Set `LLM_PROVIDER` to choose a preference.
- Optional: a CUDA GPU for faster STT/TTS. The project is developed against a 4 GB card.

### Install

```bash
git clone https://github.com/MurtazaLabs/Mai-Sakurajima-AI-Companion.git
cd Mai-Sakurajima-AI-Companion

python -m venv mai_env
mai_env\Scripts\activate        # Windows
# source mai_env/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

Create a `.env` file in the repository root. Settings are environment-backed constants re-exported through `config/settings.py`, so check that file for the full list of keys, including your LLM provider credentials.

### Run

```bash
# Interactive CLI with the full kernel (text and voice)
python run.py

# REST API only (no kernel loop, no microphone)
python run.py --mode api

# Custom bind address and port
API_HOST=0.0.0.0 API_PORT=8080 python run.py --mode api

# Windows desktop app (tray icon, hotkeys, pywebview window)
python run_daemon.py
```

By default the web UI and API are served on port `8000`. Authentication is off on loopback and automatically enforced when you bind to a non-loopback host.

### Docker

```bash
docker compose build
docker compose up -d
docker compose logs -f
```

Data is persisted in `./data`, `./vector_memory`, `./memory`, `./cache`, and `./logs`. The container runs a single replica without voice devices. See the [Deployment Guide](docs/Mai_documentation/04-Development/Deployment%20Guide.md) for the production hardening checklist.

### Tests

```bash
pytest
```

The suite has roughly 2,000 tests, including the character behavior harness in `tests/behavior/`.

## Memory vault

Mai writes what she remembers as Markdown into an Obsidian-compatible vault, by default at `~/MaiMemory` (override with `MAI_OBSIDIAN_VAULT`). Open it in Obsidian to browse entities, relationships, and conversation records. The compiled vault folders have a single writer, so avoid editing generated files by hand.

## Documentation

The full project documentation is an Obsidian vault in [`docs/Mai_documentation`](docs/Mai_documentation/00-Overview/README.md). Good places to start:

- [Current State](docs/Mai_documentation/00-Overview/CURRENT_STATE.md): what Mai actually is and can do today
- [Project Charter](docs/Mai_documentation/00-Overview/Project%20Charter.md): engineering philosophy and rules
- [System Overview](docs/Mai_documentation/01-Architecture/01-System%20Overview.md): architecture and persistence map
- [Status & Debt](docs/Mai_documentation/01-Architecture/10-Status%20%26%20Debt.md): maturity and technical debt register
- [Future Vision Roadmap](docs/Mai_documentation/03-Features/future-vision-roadmap.md): milestones M15–M26

## Roadmap

Near-term priorities, in order:

1. **M15:** model scheduler and TTS bake-off (one model resident at a time within the VRAM budget)
2. **Voice latency and echo:** feed playback audio to the AEC and re-measure STT
3. **Wake word:** a custom "hey mai" model with openWakeWord
4. **M21:** Continuity Engine (projects, commitments, checkpoints)
5. **M24–M26:** Discord, then WhatsApp via the official platform
6. **Entity web interface** and a Java desktop client

## Security

Mai can control your computer (open apps, type, read the clipboard, access a sandboxed filesystem). These actions are allowlisted and filtered, but you should treat any network-exposed deployment accordingly: keep auth enabled, restrict CORS and trusted hosts, and only install signed plugins. To report a vulnerability, please open a private security advisory on GitHub rather than a public issue.

## Contributing

Contributions are welcome. Before opening a pull request, please read [`AGENTS.md`](AGENTS.md) and the [Project Charter](docs/Mai_documentation/00-Overview/Project%20Charter.md), run the test suite, and update [`CURRENT_STATE.md`](docs/Mai_documentation/00-Overview/CURRENT_STATE.md) if your change affects what Mai can do.

## License

No license has been chosen yet. Until one is added, all rights are reserved by the author. <!-- TODO: add a LICENSE file (e.g. MIT, Apache-2.0, or AGPL-3.0) and update this section. -->
