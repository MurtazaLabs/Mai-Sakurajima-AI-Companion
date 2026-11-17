# Local LLM Plan — llama.cpp / GGUF + Switchable Providers

Status: **BUILD COMPLETE (steps 1–5), INSTALL PENDING (step 6)** — updated
2026-11-13. Provider, cloud voice, switcher, API/UI and the server launcher all
exist and are tested; no model and no llama-server are installed yet, so
`VOICE_STACK=local` / `LLM_PROVIDER=openrouter` remain the shipped defaults and
nothing changed for a user who never touches the switches. See §12 for what was
built and §13 for what is still open.
Every number in §2 was measured against a live server; every number in §4 is an
estimate until the Stheno install runs.
Date: 2026-11-13
Owner: Syed Murtaza / Mai AI Suite
Related: `future-vision-roadmap.md` (M15 Scheduler, M20 GPU window),
`stt-kyutai-replacement-plan.md` (the backend-replacement precedent)

---

## 1. Motivation

Mai currently runs entirely on OpenRouter (`LLM_PROVIDER=openrouter`). Three
problems with that:

- **Privacy**: the system prompt carries retrieved memories, relationship state
  and journal content. Every one of those leaves the machine on every turn.
- **Availability**: no network or no key = no Mai. The local failover in
  `llm/manager.py` points at an Ollama install that does not exist.
- **Latency**: the free-model router has a history of 400-retry backoffs
  (8-14 s per call, Oct 9 log). A local model removes that class of outage.

A local GGUF model solves all three. It also introduces a hard constraint that
shapes this whole plan: **4 GB of VRAM shared with a 2.3 GB STT model** (§4).

---

## 2. Ground truth (measured 2026-11-13)

### 2.1 The server that exists today

| Fact | Value |
|---|---|
| Binary | `E:\rika documentation agent\.tools\llama\llama-server.exe`, build `b12212-d78f4255b` |
| Endpoint | `http://127.0.0.1:8080` (OpenAI-compatible `/v1`) |
| Chat model | `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`, alias `local-chat-model` |
| Flags | `--ctx-size 4096 --parallel 1 --flash-attn on --n-gpu-layers 99 --no-webui --device CUDA0` |
| Second server | `:8081` `Qwen3-Embedding-0.6B-Q8_0.gguf`, `--embedding`, `n-gpu-layers 0` (CPU) |
| Owner | the **rika documentation agent** project — not Mai |
| `/health` | `200 {"status":"ok"}` — usable as the probe target |
| `/v1/completions` | 404 (chat-completions only; Mai only uses chat) |
| Chat template caps | `supports_tool_calls: true`, `supports_system_role: true` |

This instance is **for development only**. It belongs to another project, on
another project's port, and it will restart on someone else's schedule.

### 2.2 Latency and quality, measured on that instance

| Metric | Qwen3-4B local | OpenRouter free router |
|---|---|---|
| Streaming TTFT | **0.42–0.49 s** | multi-second; 8–14 s on retry ladders |
| Decode | **~25–37 tok/s** | network-bound |
| 51-token reply, end to end | **2.33 s** | typically 3–10 s |
| Envelope JSON (`ThoughtPacket`) | parsed first try, correct keys | works |
| Action JSON (`open_app`) | exact: `{"type":"open_app","content":"chrome"}` | works |
| Cost / offline | free, works offline | key + network required |

Quality probes (4B, deliberately weak prompts):

| Probe | Result |
|---|---|
| "open chrome" against the action contract | exact JSON |
| Casual chat | in character |
| Weather opinion, weak prompt | **"As an AI assistant…"** — broke character |
| "search the web for llama.cpp benchmarks" | **refused** an action it should emit |
| "no emoji" instruction | still emitted emoji |
| Identity prompt | in-character but factually muddled |

Conclusion: 4B **can** hold the machine contracts (JSON, actions), and is
**not reliable** on negative constraints. Mai's real prompt already carries
`prompt/character.py`'s "Never mention being an AI", which is stronger than the
probe prompt — but a 4B loses these fights more often than the cloud models, and
**emoji are a TTS problem, not a cosmetic one**.

### 2.3 Prompt size (ctx budgeting)

Built through the real `PromptOrchestrator` (stub brain, `evaluation/runner.py`):

- System prompt alone: **4,938 chars ≈ 1.2–1.5k tokens**, before memory blocks,
  experiential memories, history or the reply.

At `--ctx-size 4096` that leaves ~2.5k tokens for memory + history + reply —
tight. 8192 is the realistic minimum. Note llama.cpp **divides** `--ctx-size`
across `--parallel` slots.

### 2.4 VRAM, measured

- llama-server (4B Q4_K_M, ctx 4096) alone: **3,283 MiB used of 4,096** → 653 MiB free.
- Kyutai STT (bf16 1B) when resident: **~2.3 GB**.
- Kokoro TTS: **CPU only** — `voice/kokoro_tts.py` has no CUDA path. Moving TTS
  to a cloud provider frees **zero** VRAM.

---

## 3. Decisions locked (user, 2026-11-13)

| # | Decision |
|---|---|
| D1 | **Partial CPU offload** for the local LLM (GPU holds what fits, CPU holds the rest) |
| D2 | **Voice moves to ElevenLabs** |
| D3 | **Mai owns its llama-server**: own install, own port, no dependence on the rika instance |
| D4 | Local model: ~~Stheno 8B Q5_K_M~~ → ~~`qikuanz/Spark-X2.5-4B:Q4_K_M`~~ → **`Qwen3-4B-Instruct-2507-Q4_K_M`** (user override, 2026-11-14 — Spark deleted, stronger in-character voice; see §15). Supersedes D1: a 4B quant fits the card fully, so no partial CPU offload |
| D5 | **Build everything first, install the model/server last** |
| D6 | Two UI switches: LLM provider (openrouter / ollama / llama.cpp) and voice stack (ElevenLabs / Kyutai STT) |

### Consequence of D1 + D4 + D2 (the important one)

ElevenLabs is a **TTS** vendor, and TTS is already on CPU. The 2.3 GB that
Stheno needs is held by **Kyutai STT**. So the voice switch must move **STT**,
not just TTS. ElevenLabs sells that too:

- **Scribe v2** (batch accuracy) / **Scribe v2 Realtime** (~150 ms, 90+ languages).
- EightLabs TTS: **`eleven_flash_v2_5`** (~100 ms model latency, cheapest
  real-time tier) or `eleven_multilingual_v2` (quality, ~2× price).

Intended reading of D6:

| Voice stack | STT | TTS | VRAM |
|---|---|---|---|
| **Cloud** | ElevenLabs Scribe | ElevenLabs Flash v2.5 | **0 GB** |
| **Local** | Kyutai | Kokoro | **2.3 GB** |

This is still an open question for the user — see §10 Q1.

---

## 4. Hardware budget (the constraint that shapes everything)

Machine: **Dell Precision 7540, i7-9850H 6C/12T @ 2.6 GHz, DDR4, 15.8 GB RAM**,
Quadro T1000 **4 GB**, E: 76 GB free.

| Item | Size |
|---|---|
| Stheno 8B Q5_K_M weights (superseded) | ≈ **5.6 GB** *(estimate from bits-per-weight)* |
| KV cache @ 8192 ctx (L3-8B, 8 KV heads) | ≈ **1.07 GB** *(estimate)* |
| Total demand | ≈ **6.7 GB** |
| Usable VRAM (4 GB − desktop compositor) | ≈ **3.0–3.5 GB** |
| ⇒ share that must live on CPU | **≈ 45–55 % of layers** |

**Superseded by measurement (2026-11-13).** A 4B Q4_K_M does not need the CPU at
all — Qwen3-4B-Instruct-2507 Q4_K_M, full offload (`-ngl 99`), streaming TTFT
from a warm server, one bench prompt per cell:

| ctx / parallel | VRAM | TTFT | tok/s |
|---|---|---|---|
| 4096 / 1 | 3,097 MiB | 0.269 s | 29.2 |
| **8192 / 2** | **3,673 MiB** | **0.270 s** | **28.5** |
| 16384 / 2 | 3,911 MiB | 0.317 s | 25.5 |

8192/2 is the lock: same speed as the single-slot config, 4,096 tokens per slot
matches `LLM_MAX_CONTEXT=4096`, and 420 MiB of headroom remains for the desktop.
The 5–8 tok/s partial-offload estimate below no longer applies; it is kept only
as the record of why the original plan chose CPU offload.

Two further notes:

- **Spark-X2.5's chat template defaults `enable_thinking=true`.** Thinking costs
  seconds per spoken turn, so the launcher passes `--jinja --reasoning off`
  (`--chat-template-kwargs` is deprecated in b12212 and measured 3× slower).
- **`--parallel 1` is a latency trap.** Mai calls the LLM from background
  threads too: `agency/dream_tasks.py` (×5), `core/state/relationship.py`,
  `core/cognition.py`, `knowledge/extractor.py`,
  `knowledge/vault_post_processor.py`. A dream task queues in front of a voice
  reply. Mitigation: `--parallel 2 --ctx-size 8192` (4096 per slot), or route
  background work to cloud.

---

## 5. Architecture

### 5.1 LLM provider — additive, no refactor

`LLMManager` is hardwired to two providers (`_openrouter_available`,
`_ollama_available`, `order = ("ollama","openrouter")`) and ~10 tests mock
`manager.ollama`. `OllamaProvider` cannot be reused: it speaks `/api/chat`,
llama.cpp speaks `/v1/chat/completions`.

- New file `llm/providers/openai_compat.py` — llama.cpp client: `/v1/chat/completions`,
  SSE streaming, `/health` probe, same method surface as `OllamaProvider`
  (`is_alive`, `generate`, `stream`, `generate_with_tools`, `stats`), plus the
  mid-stream failure behaviour `_stream_with_failover` already expects.
- `llm/manager.py` — keep `self.ollama` untouched; add `self.llamacpp`
  (constructed only when selected), `_llamacpp_available`,
  `_mark_llamacpp_dead`, one ordering branch, and `select_provider(name)` +
  `providers_status()` for the UI.
- Config (`config/llm.py`, re-exported via `config/settings.py`):
  `LLAMACPP_BASE_URL` (default `http://127.0.0.1:8082` — 8080/8081 belong to
  the rika project), `LLAMACPP_MODEL`, `LLAMACPP_API_KEY` (blank),
  `LLAMACPP_NGL`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`,
  `ELEVENLABS_TTS_MODEL`, `ELEVENLABS_STT_MODEL`.
- `LLM_PROVIDER` values: `openrouter` (default, unchanged) | `ollama` |
  `llamacpp`. Default stays cloud so nothing regresses for anyone who never
  touches the switch.

### 5.2 Voice stack — reuse the existing seams

- `voice/elevenlabs_tts.py` — `eleven_flash_v2_5`, request **PCM output** and
  feed raw frames to `StreamPlayer` (MP3 would need a decoder and costs latency).
  Same `generate(text, emotion=)` surface `KokoroTTS` exposes.
- `voice/elevenlabs_stt.py` — same contract as `KyutaiSTT`: lazy load,
  `transcribe()`, `stats()`, `.model`, `.sample_rate`, `TranscriptionUnavailable`,
  **permanent fallback** to a working backend on any failure.
- No caller changes: `voice_manager.stt`, `app.tts`, `app.voice._tts_engine`
  and `app.voice_renderer` (built by `create_renderer(name, tts=...)`) are the
  only injection points.

### 5.3 The two switches = the manual Model Scheduler

This is roadmap M15 arriving early, in manual form.

- `voice/stack_switcher.py` — swaps `voice_manager.stt`, `app.tts`,
  `app.voice._tts_engine`, `app.voice_renderer`; **drops Kyutai and its CUDA
  memory** (`del` + `gc.collect()` + `torch.cuda.empty_cache()`), otherwise the
  2.3 GB never returns. Refuses while listening or speaking.
- API: `GET /api/system/providers` (status of all three LLM providers + current
  voice stack), `POST /api/system/llm/provider`,
  `POST /api/system/voice/stack`. All behind `api_auth_required`.
- UI: two controls on the existing settings page.
- **`core/config_manager.py` cannot do this.** A `_SAFE_KEYS` write only
  persists and applies on restart; these buttons must call real switch methods.
- Ollama remains uninstalled — the button reports "not installed" rather than
  pretending.

---

## 6. Build order (code first, per D5)

| Step | Deliverable | Validated against |
|---|---|---|
| 1 | `openai_compat.py` + manager branch + config keys + tests | the running rika server (`:8080`, `local-chat-model`) |
| 2 | `elevenlabs_tts.py` + `elevenlabs_stt.py` + mocked-HTTP tests | fakes; the real key only at validation |
| 3 | `stack_switcher.py` + swap/unload tests | mocked CUDA calls |
| 4 | API routes + UI controls + auth | route tests |
| 5 | `scripts/run_llama_server.ps1` — Mai-owned, port 8082, `-ngl` as a parameter | dry run (server not started) |
| 6 | **Install only now**: Stheno 8B Q5_K_M → `-ngl` sweep (16/20/24/28) → lock the number | real measurements |

---

## 7. Install order (after the build)

1. Put a 4B Q4_K_M GGUF in `models/` (current: `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`); verify a downloaded file's sha256 — a size-only check once passed on a file with 110 zero-filled 16 MB blocks.
2. Start the Mai-owned server on **8082**: `--ctx-size 8192 --parallel 2 --flash-attn on --n-gpu-layers <sweep> --alias <name> --jinja --reasoning off --no-webui` (the launcher defaults cover this; `$ModelPath` and `-Alias` are the only two knobs).
3. Sweep `-ngl` (a 4B fits on the card; `-ngl 99` is expected to win), record tok/s, VRAM headroom and KV fit at 8192.
4. Lock the values in `.env`; `LLAMACPP_MODEL` must equal the `--alias` (`qwen3-4b` today).
5. Run the M9 evaluation (`scripts/run_m9_evaluation.py --mode real`) against
   local vs cloud and compare rubric scores.

---

## 8. Gates

| Gate | Pass condition |
|---|---|
| Regression | full suite green with `LLM_PROVIDER` unset (2,045 at time of writing) |
| Provider | 20-turn text session on llama.cpp: TTFT p50 ≤ 1.0 s, zero envelope leaks, action JSON correct on ≥ 8/10 tool requests |
| Voice switch | cloud → local toggle frees **≥ 2.0 GB VRAM** (nvidia-smi before/after); first audio ≤ 1.5 s after the first sentence |
| Local 8B | measured **≥ 6 tok/s** at the locked `-ngl`; M9 rubric `review_required=False` |
| Failover | killing the llama-server mid-session degrades to cloud within one turn, no hang, no empty reply |

---

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **45–55 % CPU offload may measure under 6 tok/s** — local voice becomes a luxury tier, not the default | Decide after the sweep; the switch makes "local for text, cloud for voice" a legitimate outcome |
| R2 | **Cost**: Flash v2.5 ≈ $0.30/1k chars → a 200-char line ≈ $0.06, 1,000 lines ≈ $60; Multilingual v2 ≈ 2× | Default to Flash; show usage in `/api/system/providers` |
| R3 | **Two cloud vendors = two keys, two failure modes** (OpenRouter + ElevenLabs) | Each needs its own failover path; voice must degrade to Kokoro, never to silence |
| R4 | **Privacy flip is user-visible** — cloud voice sends your speech and her replies to ElevenLabs | The button is the privacy switch; label it that way |
| R5 | **Toggling mid-turn thrashes VRAM** | Switcher refuses while listening or speaking |
| R6 | **Thinking model monologue** — Spark defaults to `enable_thinking`, which spends seconds before the first token | `--reasoning off` in the launcher (measured 3× tok/s vs `--chat-template-kwargs`) |
| R7 | **`--parallel 1` blocks voice behind background work** | `--parallel 2 --ctx-size 8192`, or background jobs to cloud |
| R8 | **Kyutai VRAM not released on switch** — Python/torch keeps the cache | Explicit `del` + `gc.collect()` + `torch.cuda.empty_cache()`, asserted by test |

---

## 10. Open questions

| # | Question | Default if unanswered |
|---|---|---|
| Q1 | Cloud voice = ElevenLabs TTS **+ Scribe STT** (frees 2.3 GB), or ElevenLabs TTS only with STT staying Kyutai (local input, but Stheno then keeps only ~30 % of layers on GPU)? | **Taken: TTS + Scribe** — the build ships both, switchable, so TTS-only is one line away if wanted |
| Q2 | Emoji / "as an AI" output filter in scope for step 2, or separate? | **Taken: emoji stripped in the TTS layer only.** The "as an AI" boundary stays a prompt/ThoughtPacket concern (M11) |
| Q3 | ElevenLabs key available at step-2 validation time? | **Answered 2026-11-13** — key supplied. It is permission-scoped (no `user_read`/`models_read`/`voices_read` ⇒ 401 on those endpoints) and on the **free tier**: library voices are refused over the API (Rachel → `402 paid_plan_required`), premade voices work. Shipped voice is therefore **Bella** (`EXAVITQu4vr4xnSDxMaL`), and `ELEVENLABS_STT_MODEL` moved to `scribe_v2` |

---

## 11. Decisions log

- 2026-11-13 — **Plan created.** Ground truth from the running rika llama.cpp
  instance: Qwen3-4B-Instruct-2507 Q4_K_M, ctx 4096, 4B gives 0.42–0.49 s TTFT
  and ~25–37 tok/s on this card; envelope and action JSON both parse.
  Measured 3,283 MiB VRAM for the LLM alone, so Kyutai (2.3 GB) and an 8B model
  cannot coexist — which is why the voice switch must move **STT**, and why the
  buttons are the manual form of M15.
- 2026-11-13 — User locked D1–D6 (§3): partial CPU offload, ElevenLabs voice,
  Mai-owned server on its own port, Stheno 8B Q5_K_M, build-then-install, two
  provider switches.
- 2026-11-13 — **Steps 1–5 built** (§12). Decisions taken during the build:
  Q1 answered *TTS + Scribe*; Q2 answered *emoji stripped at the TTS boundary*;
  `LLAMACPP_MODEL` defaults to the server alias (`stheno`), so the two must agree;
  `ELEVENLABS_STT_MODEL` defaults to `scribe_v1` because the model list cannot be
  verified without a key (Q3) — check `GET /v1/models` at validation time;
  emoji stripping lives in `ElevenLabsTTS` only, Kokoro behaviour is unchanged;
  the switcher replaces **six** injection points (app/stt, voice_manager/stt,
  wake_detector/stt, kernel/stt, app/tts + voice.tts, voice_renderer/tts) because
  missing one leaves the old model alive and the VRAM unreleased.
- Not yet decided: Q3 above, and the `-ngl` lock value (needs step 6).

---

## 12. Build record (2026-11-13, steps 1–5)

All of it is additive; nothing changed for a user who never touches a switch.

### Step 1 — LLM provider

| File | Change |
|---|---|
| `llm/providers/openai_compat.py` | **new.** `/v1/chat/completions` + real SSE streaming, `/health` probe with `/v1/models` fallback, `generate_with_tools`, `cancel_stream`, `stats`. Yields **raw deltas** (no sentence bucketing) and **raises** so `_stream_with_failover` can move providers; permanent 4xx are not retried |
| `llm/http_client.py` | `stream_lines()` — `post()` buffers the body, so first-token latency needs `client.stream()`. (Ollama's "stream" is therefore buffered; left alone) |
| `config/llm.py`, `config/settings.py` | `LLAMACPP_BASE_URL` (default `http://127.0.0.1:8082`), `LLAMACPP_MODEL` (`stheno`), `LLAMACPP_API_KEY` |
| `llm/manager.py` | `_provider` normalisation (`openrouter`/`ollama`/`llamacpp`), lazy `_ensure_llamacpp()`, probe extension, llamacpp-first branch in `generate()`, priority in `stream()`, `_mark_llamacpp_dead` + cooldown, `select_provider(probe=)`, `providers_status(probe=)`, `PROVIDERS` |

Measured live against the rika instance on `:8080`: `is_alive` True, streaming
**TTFT 0.438 s**, 10 chunks, `stats()` correct.

### Step 2 — Voice backends

| File | Change |
|---|---|
| `voice/elevenlabs_tts.py` | **new.** `generate(text, path, emotion=)` — the exact `KokoroTTS` contract both call sites inspect. Requests `pcm_24000` (no decoder, no extra latency), writes 24 kHz WAV. Emotion → `voice_settings.stability`. Emoji stripped before the request (Q2). **Any failure falls back to Kokoro permanently** |
| `voice/elevenlabs_stt.py` | **new.** FasterWhisperSTT surface (`transcribe`/`stats`/`.model`/`.sample_rate`); WAV upload to `/v1/speech-to-text`; no key **or** any runtime failure → permanent `FasterWhisperSTT` fallback (CPU, no VRAM) |
| `config/voice.py`, `config/settings.py` | `VOICE_STACK` (`local`), `ELEVENLABS_API_KEY`, `_VOICE_ID`, `_TTS_MODEL` (`eleven_flash_v2_5`), `_STT_MODEL` (`scribe_v1`), `_OUTPUT_FORMAT` (`pcm_24000`), `_TIMEOUT` |
| `voice/kokoro_tts.py`, `voice/stt.py`, `voice/stt_kyutai.py` | `stack = "local"` marker |

### Step 3 — Switcher

`voice/stack_switcher.py` (**new**) — `resolve_stack()` (config override > env,
cloud refused without a key), `build_stt/build_tts` (single source used by both
boot and switch), `VoiceStackSwitcher.switch()`:
refuses `unknown_stack` / `no_api_key` / `busy` (speaking); swaps six injection
points; closes the outgoing cloud client; `del` + `gc.collect()` +
`torch.cuda.empty_cache()`; reports `vram_freed_mb` from `mem_get_info()`
before/after; persists `VOICE_STACK`.

### Step 4 — API + UI

`GET /api/system/providers`, `POST /api/system/llm/provider`,
`POST /api/system/voice/stack` (all behind `_require_auth`, thin wrappers over
`SystemMixin`). `LLM_PROVIDER` is persisted on a successful switch; a persisted
value is restored at boot with `probe=False` (no network before the first
request). `api/static/js/system.js` gains a **Models & Voice** section whose
buttons call those routes — the rows are deliberately excluded from the generic
config list, which only persists and waits for a restart.

### Step 5 — Server launcher

`scripts/run_llama_server.ps1` — port **8082**, `--ctx-size 8192 --parallel 2
--flash-attn on --no-webui --alias stheno`, `-NGpuLayers` as a parameter for the
sweep, `-DryRun` prints the exact command and what is missing. Dry run on this
machine correctly reports the missing binary and model.

### Gate

`tests/test_voice_stacks.py` (30) + `tests/test_llm.py` (+19) +
`tests/test_stt_kyutai.py` (1 rewritten into 2 behavioural ones).
Full suite **2,095 passed, 0 failures** — the only 2 red tests are the
pre-existing `test_horizontal_scaling` Redis cases, which now run because a real
Redis answers on `localhost:6379` and expose a separate state-sharing bug (out of
scope here). Both defaults unchanged: `LLM_PROVIDER=openrouter`,
`VOICE_STACK=local`.

---

## 13. Still open

1. ~~**Stheno install (step 6)**~~ → ~~**Spark install**~~ → **Qwen3-4B-Instruct-2507** live (§14 measured Spark, §15 swapped the model).
2. ~~**ElevenLabs key (Q3)**~~ — answered; real calls validated (§14).
3. ~~**ElevenLabs VRAM gate**~~ — **PASSED: 2,510 MB freed** on a real
   Kyutai→cloud switch (`free 409 → 2,919 MiB of 4,096`).
4. **M9 evaluation** — local vs cloud rubric comparison (§7 step 5). Local done
   (§14); cloud comparison not run.

---

## 14. Install record (2026-11-13, step 6)

### Model

| Field | Value |
|---|---|
| Repo / file | `qikuanz/Spark-X2.5-4B` → `Spark-X2.5-4B-Q4_K_M.gguf` |
| Bytes | **2,600,224,352** |
| SHA-256 | `adfcfa19a4ed6a5985da8bf565fe15f8e1a7e131d79bae2d19d48d1c40109428` — **verified MATCH** |
| Chat template | **embedded in the GGUF** (4,647 chars, `enable_thinking` defaults true). The sidecar `models/spark-chat-template.jinja` was redundant and is deleted |

Downloading it was the only real trouble. `hf_hub_download` wrote **zero bytes in
seven minutes with zero disk I/O** — hf_xet stalls silently on this machine's
intermittent DNS resets. An earlier parallel-seek writer passed its own
`assert got == total` on a preallocated file while leaving **110 zero-filled
16 MB blocks**. `scripts/fetch_spark.ps1` replaces both: 78 × 32 MB range
requests into separate `.part` files (self-verifying sizes, resumable, retried),
then assemble and gate on the final SHA-256. Chunks 0 and 1 failed until stale
part files were cleared — the retry loop then completed.

### Server

llama.cpp **b12212** (CUDA 12.4) in `tools/llama/`, launched by
`scripts/run_llama_server.ps1` on **port 8082**
(`-Detach` for daily use — foreground dies with its terminal, which is how the
first launch here vanished; detached it logs to `logs/llama-server.log`):

```
--model models/Spark-X2.5-4B-Q4_K_M.gguf --alias spark --host 127.0.0.1 --port 8082
--ctx-size 8192 --parallel 2 --n-gpu-layers 99 --flash-attn on --no-webui
--jinja --reasoning off
```

- `--jinja` picks up the embedded template; `--reasoning off` keeps Spark's
  default `enable_thinking` from spending seconds before the first token.
- `--parallel 2` splits 8192 into **4,096 per slot**, matching
  `LLM_MAX_CONTEXT=4096`.
- Load time **37.5 s** (2.6 GB). Resident **3,135 MiB of 4,096** (theory: 3,673
  MiB for the larger Qwen3 file).
- The server warns *"chat template supports preserving reasoning, it is enabled
  by default"*. With `--reasoning off` nothing is emitted to preserve, so it is
  left alone.

### `-ngl` sweep (ctx 8192, parallel 2, warm second request)

| ngl | VRAM | TTFT | tok/s |
|---|---|---|---|
| **99 (locked)** | 3,135 MiB | **0.40 s** | **22.1** |
| 20 | 1,863 MiB | 0.92 s | 4.4 |

Full offload is **5×** faster and fits. Partial offload confirmed redundant —
D1 is fully superseded.

### Latency at Mai's real prompt size

The first measurement looked like a disaster (**35.9 s TTFT, 0.5 tok/s**). It was
not the model: the server log showed `prompt eval time = 35852 ms / 27 tokens`
— one-time CUDA warmup on the first request after load. Warm, the same prompt is
**0.40–0.49 s TTFT / 18.8–22.1 tok/s**. `scripts/sweep_llama.ps1` now discards a
warmup pass so it cannot report that artifact again.

The number that actually governs a voice turn is **prompt eval, 143.6 tok/s**
(1,669 tokens = 11.6 s). M9 recorded Mai's real system prompt at **8,069 chars
on turn 0**, ~2k tokens, so:

| Turn | Prompt | TTFT before first token |
|---|---|---|
| first of a session | ~8,000 chars (~2k tok) | **~12 s** |
| later turns | ~7,600 chars | ~11 s minus whatever the slot cache reuses |
| after memory context empties | ~2,500 chars (~620 tok) | **~3.5 s** |

Generation itself is fine (`speak_stream` emits per sentence, so audio follows
the first sentence). The cost is cold context. Options not taken: shrinking the
character prompt, or `--ctx-size 4096 --parallel 1` (halves nothing here — the
prompt is prompt-bound, and parallel 1 queues background dream tasks in front of
voice).

### Provider + VRAM

- `OpenAICompatProvider` against this server: `is_alive` true, `generate` 0.62 s,
  `stream` TTFT 0.126 s / 26.8 tok/s, `select_provider("llamacpp")` → `spark`,
  `providers_status` reports all three providers correctly.
- **The two switches cannot both be local on this card**: llama-server 3,135 MiB
  + Kyutai 2.3 GB > 4,096 MiB. The usable combination is
  `LLM_PROVIDER=llamacpp` + `VOICE_STACK=cloud` (2,510 MB freed by the switch,
  measured). Shipped defaults are unchanged (`openrouter` + `local`).
- **This machine now runs that combination** (`.env`, 2026-11-14):
  `LLM_PROVIDER=llamacpp`, `VOICE_STACK=cloud` with the ElevenLabs key already
  present. Verified through the real code: `Settings.LLM_PROVIDER=llamacpp`,
  `resolve_stack()=cloud`, `build_tts→ElevenLabsTTS`,
  `build_stt→ElevenLabsSTT`, and `LLMManager.generate()` answering from the
  local server. `STT_BACKEND=kyutai` is kept — it is the backend the **local**
  stack builds, so switching back to `VOICE_STACK=local` still works.
  Consequence: Mai needs `scripts/run_llama_server.ps1` running; without it the
  llama.cpp provider fails over to OpenRouter.

### Cloud voice (ElevenLabs, real key)

- Key is permission-scoped (no `user_read`/`models_read`/`voices_read` ⇒ 401 on
  those endpoints) and **free tier**: library voices are refused over the API
  (Rachel ⇒ `402 paid_plan_required`); premade voices work. Shipped voice is
  **Bella** `EXAVITQu4vr4xnSDxMaL`.
- TTS: 2.93 s of audio in **2.06 s**, peak 0.933, 0 failures.
- STT: `scribe_v2` (v1 heard "Hello Mai", v2 heard "Hello, Mai."), **RTF 0.311**.

### Gates

| Gate | Result |
|---|---|
| Model integrity | SHA-256 matches published hash |
| Local 8B → 4B speed (≥ 6 tok/s) | **22.1 tok/s**, pass |
| `-ngl` lock | 99, full offload |
| Voice switch (≥ 2.0 GB freed) | **2,510 MB**, pass |
| M9 rubric on local LLM | **4.67/5** — see §14.1 |

### 14.1 M9 on Spark (real mode, praise scenario, 5 turns)

`LLM_PROVIDER=llamacpp` → the real `Brain` against this server
(`docs/evaluation/session-praise-real-1794595381/`):

| Axis | Result |
|---|---|
| Overall | **4.67 / 5** (identical to Qwen3-4B on the same scenario) |
| relationship_trajectory | trust **0.72 → 0.82**, monotone (Qwen3: 0.60 → 0.70) |
| boundary_consistency | pass — no self-disclosure, no mechanism leakage |
| repetition_control | pass |
| experience_visibility | unexercised (no reflected experience in the store) ⇒ `review_required=True` |

**The rubric does not measure voice.** Read side by side, Spark is visibly
weaker at staying in character than Qwen3-4B: turn 1 came back as
*"You're very welcome. I'm glad I could make a difference for you today — it's
always nice to hear that the help was meaningful."* — assistant register, not
Mai. Qwen3's answer to the same turn was *"Mm... you're welcome. You sounded
weighed down earlier — nice to see you feeling lighter now. ...that's all."*
Spark also stated a feeling outright (*"It makes me feel valued"*), which the
character prompt asks it not to do. Treat 4.67/5 as "the mechanics hold", not
"the character holds"; a human read is required before shipping Spark as the
default persona model.

**Bug found and fixed by this run:** Spark opened turn 4 with a roleplay stage
direction — `(with a warm smile) That's really sweet.` Both TTS backends would
have spoken the words "with a warm smile" aloud. No stage direction existed
anywhere in the prompt or the code. Fixed at both ends: one INTERACTION RULES
line in `prompt/character.py` ("write only the words you say — never stage
directions, *asterisk actions*, or (parenthetical asides)"), and a shared
`voice/speech_text.py::sanitize()` that strips emoji plus short
sentence-punctuation-free parenthetical asides, called from both
`ElevenLabsTTS._clean_text` and `KokoroTTS._enhance_text`. Prose parentheses
like `(which, as I said, took a while)` survive; `(smiling)` does not.
`*asterisk actions*` are deliberately not stripped — an asterisk pair is as
likely to be emphasis as an action, and none has been observed.

## 15. Model swap: Spark → Qwen3-4B-Instruct-2507 (2026-11-14)

User request: delete Spark, use the Qwen GGUF already present in the sibling
rika project.

| | Value |
|---|---|
| File | `models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf` (2,497,281,120 B) |
| Source | `E:\rika documentation agent\models\llm\` (copied, not downloaded — no sha256 gate run, the file was already local) |
| Alias | `qwen3-4b` (`--alias` default in the launcher, `LLAMACPP_MODEL` in `.env` — they must match) |
| Deleted | `models/Spark-X2.5-4B-Q4_K_M.gguf` |

Everything else is unchanged: port 8082, ctx 8192, `--parallel 2`, `-ngl 99`
(3,673 MiB at 4B Q4_K_M), `-Detach`. Measured earlier on this same GGUF:
0.270 s TTFT, 28.5 tok/s.

Verified through the real code after the swap: `LLMManager.provider=llamacpp`,
`providers.llamacpp={available: true, model: qwen3-4b}`, `generate()` answered in
0.67 s. `VOICE_STACK=cloud` unchanged, so runtime STT/TTS are still
`ElevenLabsSTT` (scribe_v2) / `ElevenLabsTTS`.

### System page fix found while verifying

`GET /api/system/plugins` returned **500** (`AttributeError: 'WeatherPlugin'
object has no attribute 'name'`). Manifest-style plugins (`plugins/<name>/` with
`manifest.json`) are plain classes carrying a `MANIFEST` dict, not `Plugin`
subclasses with `.name`/`.version`, but `PluginLoader.list()` assumed the latter.

Why the whole page died: Starlette's `ServerErrorMiddleware` answers an unhandled
exception with **plain-text** `Internal Server Error`, so `system.js`
`.json()` rejected inside `Promise.all` and the System space rendered only
`Error: ...`.

- `core/plugin_system.py` `list()` now falls back to `MANIFEST["name"]`,
  `MANIFEST["version"]` and the registry key.
- `api/static/js/system.js` fetches through `_json()` (each endpoint degrades to
  `null` instead of blanking the page) and creates its 15 s refresh timer once —
  it previously pushed a new interval on every `_init()`, which multiplies timers
  each time the page refreshes itself.
- Regression test:
  `tests/test_plugin_marketplace.py::test_list_reports_manifest_plugins_without_name_attr`.
- Verified live: 6 plugins listed, 10 sections rendered, no console errors;
  `POST /api/system/llm/provider` and `/api/system/voice/stack` both answer and
  persist.
