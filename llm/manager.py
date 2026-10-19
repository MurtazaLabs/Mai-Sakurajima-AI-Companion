# llm/manager.py

import logging
import re
import threading
import time
from typing import Iterator, Optional

from llm.providers.ollama import OllamaProvider
from llm.providers.openrouter import OpenRouterProvider
from app.config_loader import OPENROUTER_API_KEY, LLM_PROVIDER

logger = logging.getLogger("Mai.LLMManager")

# Regex patterns for secret redaction
_API_KEY_PATTERN = re.compile(r'sk-[a-zA-Z0-9]{32,}')
_JWT_PATTERN = re.compile(r'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+')
_API_KEY_GENERIC = re.compile(r'(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{16,}["\']?')

def _sanitize_log_message(msg: str) -> str:
    """Redact API keys, JWTs, and other secrets from log messages."""
    if not isinstance(msg, str):
        msg = str(msg)
    msg = _API_KEY_PATTERN.sub('[REDACTED_API_KEY]', msg)
    msg = _JWT_PATTERN.sub('[REDACTED_JWT]', msg)
    msg = _API_KEY_GENERIC.sub(r'\1=[REDACTED]', msg)
    return msg

# How long a positive/negative probe result is trusted before re-probing.
PROBE_TTL = 15.0
# Minimum cooldown after a real request failure before we try that provider again.
FAILURE_COOLDOWN = 30.0


class LLMManager:

    def __init__(self) -> None:

        self._lock = threading.RLock()
        self._openrouter_available = False
        self._ollama_available = False
        self._probe_at = 0.0
        self._openrouter_cooldown_until = 0.0
        self._ollama_cooldown_until = 0.0

        # Provider preference: "ollama" = local first (OpenRouter fallback),
        # anything else = OpenRouter first (default). Normalized here so
        # tests can patch llm.manager.LLM_PROVIDER with any casing.
        provider = (LLM_PROVIDER or "openrouter").strip().lower()
        if provider not in ("openrouter", "ollama"):
            logger.warning(
                "[LLMManager] Unknown LLM_PROVIDER %r — defaulting to openrouter",
                LLM_PROVIDER,
            )
            provider = "openrouter"
        self._prefer_ollama = provider == "ollama"

        self.ollama = OllamaProvider()

        self.openrouter = OpenRouterProvider(
            api_key=OPENROUTER_API_KEY
        )

    # ---------------- availability probing (cached + circuit breaker) ----------------

    def _probe(self, force: bool = False) -> None:
        """Refresh cached availability at most once per PROBE_TTL window.

        Probe decisions are snapshotted under the lock, but the network I/O
        itself runs OUTSIDE the lock so a slow provider handshake can never
        serialize (block) concurrent ``generate()``/``stream()`` calls.
        """
        now = time.monotonic()
        with self._lock:
            if not force and now < self._probe_at:
                return
            self._probe_at = now + PROBE_TTL
            probe_openrouter = now >= self._openrouter_cooldown_until
            probe_ollama = now >= self._ollama_cooldown_until
            current_openrouter = self._openrouter_available
            current_ollama = self._ollama_available

        # ── network I/O outside the lock ────────────────────────────────
        if probe_openrouter:
            try:
                openrouter_ok = self.openrouter.is_alive()
            except Exception as e:
                logger.debug("[LLMManager] OpenRouter probe failed: %s", e)
                openrouter_ok = False
        else:
            # OpenRouter in failure cooldown — treat as unavailable.
            openrouter_ok = False

        ollama_ok = current_ollama
        if probe_ollama and (not openrouter_ok or self._prefer_ollama):
            try:
                ollama_ok = self.ollama.is_alive()
            except Exception as e:
                logger.debug("[LLMManager] Ollama probe failed: %s", e)
                ollama_ok = False

        with self._lock:
            self._openrouter_available = openrouter_ok
            self._ollama_available = ollama_ok

    def _mark_openrouter_dead(self) -> None:
        with self._lock:
            self._openrouter_available = False
            self._openrouter_cooldown_until = time.monotonic() + FAILURE_COOLDOWN

    def _mark_ollama_dead(self) -> None:
        with self._lock:
            self._ollama_available = False
            self._ollama_cooldown_until = time.monotonic() + FAILURE_COOLDOWN

    def is_available(self) -> bool:

        self._probe()
        with self._lock:
            return self._openrouter_available or self._ollama_available

    @staticmethod
    def _is_simple_query(user: str) -> bool:
        word_count = len(user.split())
        return word_count <= 4 and len(user) <= 30

    def generate(
        self,
        system: str = "",
        user: str = "",
        history: Optional[list] = None,
    ) -> str:

        self._probe()

        with self._lock:
            openrouter_ok = self._openrouter_available
            prefer_ollama = self._prefer_ollama

        # Attempt order: preferred provider first, the other second.
        order = ("ollama", "openrouter") if prefer_ollama else ("openrouter", "ollama")

        for name in order:
            if name == "openrouter":

                if not openrouter_ok:
                    if not prefer_ollama:
                        logger.info(
                            "OpenRouter unreachable. "
                            "Switching to offline failover (Ollama)."
                        )
                    continue

                simple = self._is_simple_query(user)
                try:
                    response = self.openrouter.generate(
                        system, user, history, simple=simple,
                    )
                    return response
                except Exception as e:
                    self._mark_openrouter_dead()
                    if prefer_ollama:
                        logger.warning(
                            "OpenRouter failed: %s.", _sanitize_log_message(str(e))
                        )
                    else:
                        logger.warning(
                            "OpenRouter failed: %s. Switching to offline failover (Ollama).",
                            _sanitize_log_message(str(e)),
                        )

            else:

                if prefer_ollama:
                    # Use the cached probe (kept fresh while Ollama is the
                    # preferred provider) — a stale-false cache must not cost
                    # a 2s dead-host timeout on every voice turn.
                    with self._lock:
                        ollama_ok = self._ollama_available
                    if not ollama_ok:
                        logger.info(
                            "Ollama unavailable (cached). Falling back to OpenRouter."
                        )
                        continue
                    try:
                        return self.ollama.generate(system, user, history)
                    except Exception as e:
                        self._mark_ollama_dead()
                        logger.warning(
                            "Ollama failed: %s. Falling back to OpenRouter.",
                            _sanitize_log_message(str(e)),
                        )
                else:
                    try:
                        if self.ollama.is_alive():
                            return self.ollama.generate(
                                system, user, history
                            )
                    except Exception as e:
                        self._mark_ollama_dead()
                        if openrouter_ok:
                            logger.warning("Ollama failover failed: %s", _sanitize_log_message(str(e)))

        logger.error(
            "Both OpenRouter and Ollama are unreachable — using fallback text"
        )
        return self._fallback_text(system, user)

    @staticmethod
    def _fallback_text(system: str = "", user: str = "") -> str:
        return "I'm sorry, I can't respond right now — my language model is unavailable."

    def generate_with_tools(
        self,
        system: str,
        user_input: str,
    ) -> str:

        return self.generate(
            system=system,
            user=user_input,
        )

    def stream(
        self,
        system: str = "",
        user: str = "",
        history: Optional[list] = None,
    ) -> Iterator[str]:

        self._probe()

        with self._lock:
            openrouter_ok = self._openrouter_available

        priority = []
        if self._prefer_ollama:
            if hasattr(self.ollama, "stream"):
                priority.append(("ollama", self.ollama))
            if openrouter_ok and hasattr(self.openrouter, "stream"):
                priority.append(("openrouter", self.openrouter))
        else:
            if openrouter_ok and hasattr(self.openrouter, "stream"):
                priority.append(("openrouter", self.openrouter))
            if hasattr(self.ollama, "stream"):
                priority.append(("ollama", self.ollama))

        if not priority:
            try:
                response = self.generate(system=system, user=user, history=history)
            except ConnectionError:
                response = self._fallback_text(system, user)
            return iter([response])

        return self._stream_with_failover(system, user, history, priority)

    def _mark_dead(self, name: str) -> None:
        if name == "openrouter":
            self._mark_openrouter_dead()
        else:
            self._mark_ollama_dead()

    def _stream_with_failover(
        self,
        system: str,
        user: str,
        history: Optional[list],
        priority: list,
    ) -> Iterator[str]:
        """Yield chunks from the first working provider; on a mid-stream
        failure mark it dead and restart the request on the next provider
        (P-2).  Falls back to a single non-streamed generate() chunk when
        every provider fails mid-stream."""
        for name, provider in priority:
            try:
                gen = provider.stream(system, user, history)
            except Exception as e:
                self._mark_dead(name)
                logger.warning(
                    "[LLMManager] %s stream failed to start: %s. Failing over.", name, _sanitize_log_message(str(e))
                )
                continue
            while True:
                try:
                    chunk = next(gen)
                    yield chunk
                except StopIteration:
                    return
                except Exception as e:
                    self._mark_dead(name)
                    logger.warning(
                        "[LLMManager] %s stream failed mid-iteration: %s. Failing over.", name, _sanitize_log_message(str(e))
                    )
                    break
        try:
            response = self.generate(system=system, user=user, history=history)
        except ConnectionError:
            response = self._fallback_text(system, user)
        if response:
            yield response