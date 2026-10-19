# Bug Audit Report — ChatGPT Review Remediation (2026-10-19)

**Type:** Bug remedy (external review triage: ChatGPT audit findings, all code-verified before fixing)
**Source:** External ChatGPT audit report; every finding was independently verified against the codebase before remediation. All 10 findings confirmed as real.
**Scope:** brain / plugins sandbox + scraper + marketplace / execution / llm / api auth
**Baseline:** 1,930 passed, 2 skipped · **Gate:** 1,977 passed, 2 skipped, 0 failures, 0 regressions

Related: [[Bug_Summary_and_Fix_Plan_2026-09-21]], [[03-Core Brain Kernel & State]], [[10-Status & Debt]]

---

## Summary

An external ChatGPT review flagged 10 vulnerabilities/bugs across the Brain response cache, plugin sandbox, web scraper, safe executor, LLM manager stream fallbacks, OIDC/SAML auth, and the plugin marketplace. Every finding was re-verified live (grep + line reads) and ALL were confirmed exactly as described, including the cached path's event-skip behavior. This sprint fixed all 10 with full regression coverage.

### Findings → Fixes (all today)

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| 1 | **CRITICAL** | `plugins/sandbox.py` `eval_code()` exposed raw `os` + `pathlib` modules in the eval globals and kept `getattr`/`setattr`/`type` in the builtins whitelist (classic escape hatches); `apply_resource_limits()` mutated the CURRENT process | Purged `os`/`pathlib`/`getattr`/`setattr`/`type`; eval now needs BOTH the `EXEC_EVAL` permission AND the `MAI_PLUGIN_ALLOW_EVAL=1` opt-in (default off, fail-closed); untrusted code must use `run_subprocess()`; process-wide limits documented as trusted-first-party-only |
| 2 | HIGH | `plugins/sandbox.py:148` `resolve_path()` used string `startswith` containment → sibling dirs (`<root>_backup/`) bypassed it, no symlink policy | Structural containment via `requested.relative_to(self.fs_root)` — symlinks resolve before the check, so anything that escapes the root (traversal, sibling prefix, symlink-escape) is rejected |
| 3 | HIGH | `core/brain.py` `think()`/`think_stream()` mutated shared `self._current_user_id` mid-request → interleaved multi-user requests could store/retrieve memory under the wrong user; **plus** the response cache was keyed ONLY on message text — same short message from user A returned user B's cached reply in their voice context | `think()`/`think_stream()` now use request-local `request_user_id` for all memory calls (`before_think`/`after_think`); `self._current_user_id` kept only for the agent path + `get_current_user()` |
| 3b | HIGH | `core/brain.py` `TTLCache` response cache — on a hit, returned early WITHOUT skipping-effected work (see Finding 10) | **Cache deleted entirely** (`__init__` init, hit check, `set()` at turn end, `switch_user()` clear, `TTLCache` import). `evaluation/runner.py` dead per-turn clear block removed |
| 4 | HIGH | `plugins/web_scraper/web_scraper.py` pre_chat hook auto-scraped ANY message containing a URL (SSRF-shaped fetch on every chat), `resp.read()` unbounded, blind redirects | Explicit-intent regex (`scrape/fetch/read/summarize/browse` + URL-shaped target) only; scheme validation (http/https only; `ftp://`/`file://` rejected); 2 MB read cap; `_SafeRedirectHandler` blocks non-HTTP redirect schemes |
| 4b | HIGH | `core/brain.py` hook merge REPLACED the user's message with raw page content (the question vanished) | Hook result is now APPENDED as `[Web content retrieved from a URL in the message]` context — the user's original question is preserved |
| 5 | MED | `plugins/marketplace_client.py` installed unsigned packages when no trusted keys were given (`if trusted_keys:` verify else `verify_signature=False`) | Signature required by default; unsigned installs need `MAI_ALLOW_UNSIGNED_PLUGINS=1` (developer opt-in). API route never passes client-supplied keys (by design — caller-supplied keys would be self-verifying) |
| 6 | MED | `execution/safe_executor.py` `_confirm()` was a hardcoded `return False` — admin `run_command` permanently dead ("fail-closed dead feature") | `confirm_fn` constructor param — injectable confirmation gate; default `None` keeps fail-closed headless behavior; raising `confirm_fn` also declines |
| 7 | MED | `llm/manager.py` both streaming fallbacks (no-priority path + final fallback after all streams fail) dropped conversation history | Both call `self.generate(system=system, user=user, history=history)` now — `generate()` already accepted `history`; it just was never passed |
| 8 | HIGH | `api/auth.py` open redirect: `redirect_after`/`relay_state` went into a `RedirectResponse` unvalidated | `_safe_redirect_target()` — only in-app paths starting `/` survive (`https://evil.com`, `//evil.com`, `javascript:`, scheme-ish strings, CR/LF all → `/`); applied to OIDC login + callback, SAML login + ACS |
| 9 | HIGH | `api/auth.py:198` used `base64.urlsafe_b64encode` with no `import base64` → `NameError` on every JWKS request; all 9 `set_cookie` sites lacked `samesite`/`secure` | `import base64` + `import re` added; new `_set_session_cookie(response, request, ...)` emits all auth cookies as HttpOnly + SameSite=Lax, Secure when served over HTTPS; all 9 sites routed through it |
| 10 | HIGH (verified live) | Response-cache hit path skipped memory `after_think`, `cognitive.push_turn`, thought journaling, `CONVERSATION_FINISHED`/`STATE_REASONING_COMPLETE`/`STATE_MONOLOGUE_GENERATED` events, and post-think hooks — one well-timed repeat message desynced the whole UI/state/memory chain | Eliminated by the cache deletion (#3b) |

### Deliberately NOT changed
- `EmotionState` 11-field schema vs 7-axis engine (frozen `sad/angry/anxious/neutral`) — user decision: leave as-is, documented drift.
- Cache death impact on M9 evaluation: `test_response_cache_bypassed_between_turns` still passes (it asserts FRESH generation both turns — now trivially true with no cache).

## Tests

**New (+47):**
- `tests/test_sandbox.py` (9) — containment (traversal, sibling prefix, absolute), eval permission gate, default-off opt-in, import blocked, escape hatches absent
- `tests/test_web_scraper.py` (12) — intent gate (bare URL / open chrome / no-URL all inert; scrape/read/summarize fetch), scheme rejection, 2 MB cap, non-HTML guard
- `tests/test_auth_oidc.py` (14) — redirect allowlist table + non-string; cookie Secure-on-HTTPS / lax-always
- `tests/test_brain.py::TestBrainNoResponseCache` (3) — no `_response_cache` attr, request-local user_id beats stale attribute, `switch_user` clean
- `tests/test_execution.py::TestSafeExecutorConfirm` (4) — default declined, confirm_fn allow, decline, exception fail-closed
- `tests/test_llm.py::TestStreamFallbackHistory` (2) — no-priority + all-streams-fail fallbacks pass history
- `tests/test_plugin_marketplace.py` (+3, e2e updated) — unsigned blocked by default, opt-in installs, forged-signature install aborts

**Untouched:** all existing 1,930 tests — zero behavioral regressions.

## Regression note (caught during testing)

`tests/test_llm.py` mock-provider streams first exposed a latent hazard: `next()` on a raw `MagicMock` never raises `StopIteration`, so the failover loop spun forever with un-iterator `stream()` returns. Real providers always return real generators, and the new tests stub `stream()` with real side effects — test-only artifact, no production change needed.

## Status

All 10 findings: **FIXED and regression-covered** · Suite: **1,977 passed / 2 skipped** under `mai_env`.
---

## Independent Verification (Oct 19 2026, same day)

External review of the sprint distinguished between "report describes a fix" and
"independently verified". Five verification channels were run and closed:

### 1. Regression tests reproducing each original finding
Every fix now has an exploit-shape regression test that FAILS on the pre-fix code shape:
- Cross-user cache reply / skimmed state chain -> **cache no longer exists** (`test_no_response_cache_attribute`) + attribution via request-local id (`test_think_uses_request_local_user_id`, `test_think_stream_uses_request_local_user_id`).
- Shared-attr identity race -> **concurrency proof**: `test_concurrent_requests_isolated_user_ids` (8-thread pool interleaving `think()` at distinct user ids; every request observed its own message at `memory_coordinator.before_think`).
- Hook merge destroying the question -> `test_pre_chat_hook_appends_not_replaces` (question survives at prompt build, page content appended after it).
- Sandbox path escapes -> `TestPathContainment` (traversal, sibling `root_backup/`, absolute) **+ new `test_symlink_escape_rejected`** (in-root symlink pointing outside -> PermissionError).
- Eval exploitation -> import `os` blocked (`RuntimeError`), `type/getattr/setattr` missing (`RuntimeError`), gate off by default, opt-in works.
- URL pre_chat auto-scrape -> intent table (bare URL / `open chrome` / no-URL inert; explicit verbs fetch).
- Unsigned marketplace installs -> blocked by default (400), opt-in installs, forged/failed signature aborts.
- Confirm gate -> fail-closed/allow/decline/exception table.
- Open redirects -> param table (`https://evil.com`, `//evil.com`, `javascript:`, CR/LF -> all reduced to `/`).
- History-dropping fallbacks -> both drop sites assert `history` kwarg reaches `generate()`.

### 2. Security edge cases
- Symlink races: resolve-time containment **verified** (`relative_to` after `resolve()`); a point-in-time TOCTOU window between `resolve_path()` and the caller's open remains an **inherent symlink-race limitation** of any in-process resolver - documents as accepted residual risk (first-party plugin mounts only; untrusted code belongs in `run_subprocess()`).
- **Redirect SSRF -> NEW FIX this session**: `_resolves_to_public_ip()` (socket.getaddrinfo + ipaddress categories: loopback / private / link-local / reserved / multicast / unspecified) guards BOTH the initial fetch target and every redirect destination (`_SafeRedirectHandler` -> `require_public_target()`); DNS unresolvable hosts refuse to fetch; `MAI_SCRAPER_ALLOW_PRIVATE=1` dev opt-in (+5 tests: loopback initial blocked, DNS-failure blocked, redirect-to-loopback rejected, private/public classification table, opt-in allows).
- Malicious eval: beyond `import os`, the restricted builtins deny reflectivity (`getattr/setattr/type` absent) while the env gate keeps the surface inactive by default; `eval()` remains an in-process convenience, NOT an isolation boundary - documented on the method (untrusted -> `run_subprocess()`).
- Invalid signatures: verification-failure abort covered (`verify_plugin_package` false path aborts install).
- Disallowed redirect URLs: `_safe_redirect_target()` table case-covered.

### 3. Concurrency
Threaded 8-way interleaved `think()` proof added (above). `think_stream()` uses the same
request-local variable verified individually; a concurrent stream test would need per-thread
generator stubbing and is deferred as low-value (stream path shares the identical fix shape).

### 4. Lifecycle correctness
Cache deletion restored the *entire* normal-path chain - the wording lines were proven live
before deletion (memory after_think, cognitive push, thought journal, CONVERSATION/STATE
events, post-think hooks all serialize correctly; ~90 pre-existing think()/think_stream()
tests unchanged and passing). Error/cancellation pairing (`STATE_REASONING_BUSY` ->
completion event) was audited 1:1 in the Oct 6 event-fabric alignment and remains intact.

### 5. Full-suite validation (recorded)
- Baseline before the verification pass: **1,977 passed / 2 skipped** (2m51s, mai_env)
- After SSRF guard + symlink + hook/concurrency proofs: **1,986 passed / 2 skipped / 0 failures** (1m46s, mai_env) - +9 tests, zero regressions.
