# Discord Integration — Product Plan & Architecture

> **Date:** 2026-07-22 | **Author:** AI Product Manager + Integration Specialist | **Status:** Approved — ready for implementation

---

## 1. Task Classification

| Field | Value |
|-------|-------|
| Type | Feature design + third-party integration |
| Complexity | Medium |
| Priority | P2 — dependent on deployment model decision |
| Primary Specialist | AI Product Manager — feature definition, requirements |
| Supporting Specialist | Integration / API Ecosystem Specialist — Discord bot architecture, connection design |

---

## 2. Specialist Assignment

| Specialist | Reason | Role |
|------------|--------|------|
| AI Product Manager | New feature requiring product discovery, requirements, and implementation planning | Define the feature, evaluate impact |
| Integration / API Ecosystem Specialist | Third-party Discord integration via discord.py, bot lifecycle, event handling | Technical design |

---

## 3. Product Discovery

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRODUCT DISCOVERY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Problem:** Mai is tied to the local machine. When the user is away from home (work, travel, phone), she's unreachable. The companion AI loses value if it only exists in one physical location.

**Target User:** The developer and primary user. Want Mai available wherever they are, same personality, same memory, same continuity.

**Pain Point:** Today the only interface is the web UI (localhost:8000) or voice. Neither works remotely without exposing the API to the network, which requires HTTPS + JWT first.

**Desired Outcome:** Mai feels always-on and accessible. Whether at home on desktop, on the go via phone, or at work via browser, the user has a consistent channel to the same Mai instance.

### Idea Evaluation

| Dimension | Assessment |
|-----------|------------|
| Value | High — turns Mai from a local-only app into an always-available companion. Single biggest UX improvement available. |
| Feasibility | High — Discord's bot API is mature, discord.py is well-documented, and Mai already has a clean REST chat endpoint. |
| Complexity | Medium — the bot itself is ~200 lines. The complexity is in auth, rate limits, message history formatting, and deployment. |
| Risk | Low — Discord bot runs alongside the existing API. If it crashes, Mai still works locally. No data exposure risk since Discord handles transport. |
| Dependencies | Deployment model decision (cloud vs. local tunnel), HTTPS + JWT if exposing without tunnel, new dependency discord.py |

**Recommendation: BUILD** — High value, low risk, clear implementation path.

---

## 4. AI Feature Impact

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 AI FEATURE IMPACT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Feature:** Discord Chat Integration

| Dimension | Impact | Notes |
|-----------|--------|-------|
| Memory Impact | Low | Messages go through the same `/api/chat` pipeline as web UI. No new memory types needed. Existing conversation history works. |
| Agent Impact | Low | Same `Brain.think()` call. No new agents. |
| Prompt Impact | Low | Same prompts. May want a system prompt note re: Discord context (e.g., Mai knows she's chatting via Discord). |
| Database Impact | None | All state remains in vault/VectorStore as-is. |
| Cost Impact | Minimal | Same LLM calls as local chat. Discord API is free. One extra server process (lightweight polling). |
| UX Impact | Medium-high | Discord becomes a primary remote interface. Text-only by default (no voice in Discord). The user expects fast replies, emoji support, markdown rendering. |
| Cross-Cutting | Deployment | The Discord bot must stay connected 24/7. If Mai is a local-only app, the bot needs a tunnel (ngrok/Cloudflare) or Mai needs to run on a server. |

**Recommended Specialists:**
- [1st] integration-api-ecosystem-specialist → Design bot architecture
- [2nd] python-master-engineer → Implement bot + wire to API
- [3rd] devops-infrastructure-specialist → Deployment guidance

---

## 5. Technical Architecture

### Option A: Bot → API (Recommended)

```
Discord ──► Discord Bot (discord.py) ──HTTP──► Mai API /api/chat ──► Brain
                  │                              │
                  │                        [auth token]
                  │                              │
                  └──── relay response ──────────┘
```

**Pros:** Mai API already exists. No need to import Brain/database into the bot process. Clean separation. Bot can crash independently. Works with any deployment.

**Cons:** Slight latency overhead (local HTTP call). Requires auth token configuration.

### Option B: Bot → Brain (Direct, not recommended)

```
Discord ──► Discord Bot ──► Brain.think() (direct import)
```

**Pros:** No HTTP overhead. Single process.

**Cons:** Ties bot to Brain's lifecycle. Import complexity. Memory overhead of loading Brain twice if API is already running.

### Recommended: Option A

| Component | Technology | Details |
|-----------|------------|---------|
| Library | discord.py | Async, well-maintained, supports slash commands |
| Bot type | Prefix commands (!mai) + Slash commands | `!mai hello` or `/mai hello` |
| Auth | Bot token from Discord Developer Portal | Stored in .env or config/settings.py |
| API connection | httpx.AsyncClient | Persistent connection pool to local API |
| Message handling | Off-thread via asyncio | Discord bot event loop drives message processing |
| Rate limiting | Discord enforces its own; bot should respect API rate limits too | |
| Deployment | Sidecar process to the API | Separate process, can be started/stopped independently |

### Message Flow

1. User types `!mai hello` in Discord
2. Discord bot receives message via Gateway
3. Bot strips prefix, sends POST `/api/chat { message }` to local API
4. API returns `{ response, status }`
5. Bot posts response back to Discord channel (split if >2000 chars)
6. If API is down, bot responds "Mai is sleeping right now."

---

## 6. Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `gateways/discord_bot.py` | Single-file bot (created 2026-07-22) — connect, listen, relay |

### Modified Files

| File | Change |
|------|--------|
| `config/settings.py` | Add `DISCORD_BOT_TOKEN`, `DISCORD_PREFIX`, `DISCORD_ENABLED` |

---

## 7. Implementation

### Completed (2026-07-22)

- `discord.py` 2.7.1 installed in venv
- `gateways/discord_bot.py` created — single file, ~60 lines
  - Prefix command `!mai <message>`
  - Calls `POST /api/chat` via `urllib` (no extra deps)
  - Splits responses >2000 chars for Discord's limit
  - Handles API down, empty messages, errors
  - Config via env vars: `DISCORD_TOKEN`, `MAI_API_URL`, `MAI_API_TOKEN`, `DISCORD_PREFIX`

### Remaining Setup

1. Create Discord Application at https://discord.com/developers/applications
2. Create Bot, copy token
3. Set `DISCORD_TOKEN` env var
4. Add bot to server with Send Messages + Read Message History permissions
5. Run: `python -m gateways.discord_bot`

---

## 8. Recommendations

- **Build this.** It's the single highest-ROI feature available — minimal effort for always-on remote access to Mai.
- **Use Option A (bot → API).** Clean separation, independent lifecycle, works today without any changes to the core Brain.
- **Run the bot as a sidecar** — a separate terminal or systemd service. Don't embed it in the API process.
- **Tunnel insight:** The bot itself does NOT need a tunnel — it connects outbound to Discord's Gateway and calls `localhost:8000`. A tunnel is only needed for remote web UI / direct API access.
- **Defer voice** — Discord voice is possible but adds significant complexity (Voicevox/FFmpeg streaming). Start with text.
- **Add channel whitelist** — restrict which Discord channels the bot responds to, so it doesn't reply in every channel.

---

## 9. Project Assessment Summary

### Problems Identified

| # | Problem | Severity | Subsystem |
|---|---------|----------|-----------|
| 1 | Brain god class — 786 lines, 15+ dependencies, 10+ consumers. Single point of architectural risk. | 🟠 High | core/brain.py |
| 2 | VectorStore god class — 667 lines, single monolithic file for all vector operations. | 🟡 Medium | memory/vector_store.py |
| 3 | Test coverage thin — 27 test files for ~197 source files. Many subsystems (api/, knowledge/) have 0–1 test files. | 🟡 Medium | Global |
| 4 | Web UI is minimal — Basic chat interface, no PWA, no mobile responsiveness, no auth UI. | 🟡 Medium | api/static/ |
| 5 | No HTTPS — API serves over HTTP. Cannot expose to network safely. | 🟠 High | api/ |
| 6 | No JWT auth — Auth dependency exists but no login endpoint, no token issuance. | 🟡 Medium | api/ |
| 7 | No production monitoring — No structured logging pipeline, no metrics endpoint, no alerting. | 🟡 Medium | observability/ |
| 8 | Single-user — No multi-session support, memory/user profile isolation. | 🟡 Medium | Global |
| 9 | Documentation monolithic — 553KB single file. No browsable site, no search. | 🔵 Low | docs/ |
| 10 | Knowledge base enrichment not started — Semantic chunking, overlap unification pending. | 🔵 Low | knowledge/ |
| 11 | Performance not profiled — No cProfile/py-spy runs ever done. Bottlenecks unknown. | 🔵 Low | Global |
| 12 | Embedding cache has no model fingerprint — Model change silently serves stale embeddings. | 🔵 Low | memory/embedding_service.py |

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Brain god class causes regression | Medium | High — affects every subsystem | Extract ToolManager already done; extract cognition/reasoning/memory coordinator next |
| API exposed without HTTPS + JWT | Medium (if exposed) | Critical — data exposure | Add before any network exposure |
| Thin test coverage misses regression | Medium | Medium — bugs reach production | Add integration tests for api/ and knowledge/ |
| Single bottleneck blocks all progress | Low | High — Brain is single point of failure | Gradual extraction into focused coordinators |

### Recommendations (Project-Level)

**Immediate (This Week):**
- Don't touch code — code quality is clean. The project is at a natural inflection point.
- Profile the boot sequence + hot path — run `python -m cProfile run.py` and `/api/chat` to find top 5 bottlenecks before optimizing anything.
- Decide the target deployment model — local desktop app? network-accessible API? cloud service? This decision determines everything else.

**Next 30 Days — Production Hardening:**

| Priority | Item | Effort | Dependencies |
|----------|------|--------|-------------|
| P1 | HTTPS certs + JWT auth | 3–5 days | None |
| P1 | Rate limiting (done per-endpoint, add slowapi middleware) | 1 day | None |
| P1 | Security headers + CORS strict mode | 0.5 day | None |
| P1 | Multi-session / user profiles | 5–7 days | JWT auth |

**Next 60 Days — Feature Completeness:**

| Priority | Item | Effort | Dependencies |
|----------|------|--------|-------------|
| P2 | Knowledge base enrichment (semantic chunking) | 2–3 days | None |
| P2 | Performance optimization (profiling → async I/O → caching) | 3–5 days | Profiling first |
| P2 | Web UI upgrade (PWA, responsive, mobile-friendly) | 3–5 days | API hardening |
| P3 | Embedding model versioning | 1–2 days | None |

**Next 90 Days — Platform Maturity:**

| Priority | Item | Effort | Dependencies |
|----------|------|--------|-------------|
| P3 | Plugin ecosystem (marketplace, 5 core plugins) | 5–7 days | Plugin system exists |
| P3 | Documentation site (MkDocs) | 3–5 days | None |
| P4 | Brain god class decomposition | 3–5 days | None |
| P4 | Native OS bridge (daemon, system tray) | 4–6 weeks | Deployment model decision |

---

## 10. Next Steps

### Recommended Build Order

| Week | Focus | Deliverable |
|------|-------|-------------|
| WEEK 1 | Profile | Identify bottlenecks → Document baseline |
| WEEK 2-3 | Security | HTTPS + JWT auth → Rate limiting → Security headers |
| WEEK 3-4 | Multi-session | User profiles, memory scoping |
| WEEK 5 | Knowledge | Semantic chunking for better retrieval |
| WEEK 6 | Performance | Fix top 3 bottlenecks |
| WEEK 7 | Web UI | PWA upgrade (mobile-responsive, offline) |
| WEEK 8 | Plugins | Core plugins (weather, calendar, news) |
| WEEK 9-12 | Native OS Bridge | If desktop deployment |

### Key Decision Required

The single most important decision before continuing: **What is the target deployment?**

- **Local desktop companion** → Prioritize Native OS Bridge, system tray, offline mode, voice pipeline optimization
- **Network-accessible API** → Prioritize HTTPS, JWT auth, rate limiting, multi-session today
- **Cloud service** → Prioritize everything above + monitoring, backup/DR, cloud deployment pipeline

---

## Wiki Links

**Related:** [[01-Architecture/08-API Native & Surface]] — API surface detail • [[03-Features/Native OS Bridge Architecture]] — daemon architecture (deployment model dependency) • [[04-Development/Deployment Guide]] — HTTPS, JWT, production hardening • [[05-Reference/Complete Folder Structure]] — gateways/ folder detail