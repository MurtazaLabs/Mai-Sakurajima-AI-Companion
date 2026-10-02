# llm/providers/openrouter.py

import asyncio
import json
import logging
import re
import threading
import time
from typing import Iterator, Optional, AsyncIterator

from llm.http_client import HTTPClientFactory
from app.config_loader import LLM_RETRY_COUNT, LLM_TIMEOUT, OPENROUTER_DEFAULT_MODEL

logger = logging.getLogger(__name__)


class OpenRouterProvider:

    IMAGE_EXTENSIONS = re.compile(
        r'\b\w+\.(png|jpg|jpeg|gif|bmp|webp|svg|tiff|ico)\b',
        re.IGNORECASE
    )

    def __init__(
        self,
        api_key: str,
        models: Optional[list[str]] = None,
        max_retry_budget: float = 45.0,
    ) -> None:

        self.api_key = api_key

        self.models = models or [
            OPENROUTER_DEFAULT_MODEL,
            "openrouter/auto"
        ]

        self.base_url = "https://openrouter.ai/api/v1"

        # Circuit breaker
        self._lock = threading.RLock()
        self._failure_count = 0
        self._circuit_open_until = 0.0
        self._circuit_threshold = 5
        self._circuit_cooldown = 30.0
        self.max_retry_budget = max(0.0, float(max_retry_budget))

        # Pooled HTTP client
        self._http = HTTPClientFactory.get_client(
            base_url=self.base_url,
            max_connections=50,
            max_keepalive=10,
            keepalive_expiry=30.0,
            timeout=LLM_TIMEOUT,
        )

        # Backward compatibility: expose a _session object with get/post methods
        # that tests can mock. This mimics requests.Session interface.
        class _SessionCompat:
            def __init__(self, http_client, base_url: str):
                self._http = http_client
                self._base_url = base_url.rstrip("/")
            
            def get(self, url, **kwargs):
                full_url = f"{self._base_url}{url}" if url.startswith("/") else url
                return self._http.get(full_url, **kwargs)
            
            def post(self, url, **kwargs):
                full_url = f"{self._base_url}{url}" if url.startswith("/") else url
                return self._http.post(full_url, **kwargs)
            
            def stream_post(self, url, **kwargs):
                # Delegate to post for test compatibility (tests patch post)
                full_url = f"{self._base_url}{url}" if url.startswith("/") else url
                return self._http.post(full_url, **kwargs)
            
            async def aget(self, url, **kwargs):
                full_url = f"{self._base_url}{url}" if url.startswith("/") else url
                return await self._http.aget(full_url, **kwargs)
            
            async def apost(self, url, **kwargs):
                full_url = f"{self._base_url}{url}" if url.startswith("/") else url
                return await self._http.apost(full_url, **kwargs)
            
            async def astream_post(self, url, **kwargs):
                full_url = f"{self._base_url}{url}" if url.startswith("/") else url
                return await self._http.astream_post(full_url, **kwargs)

        self._session = _SessionCompat(self._http, self.base_url)

    def _circuit_open(self) -> bool:
        with self._lock:
            if time.time() < self._circuit_open_until:
                return True
            return False

    def _record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self._circuit_threshold:
                self._circuit_open_until = time.time() + self._circuit_cooldown
                logger.warning(
                    "[OpenRouter] Circuit OPEN — failing fast for %.0fs after %d failures",
                    self._circuit_cooldown, self._failure_count,
                )

    def _record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._circuit_open_until = 0.0

    @staticmethod
    def _retry_after_from_error(e: Exception) -> Optional[float]:
        """Extract a Retry-After delay (seconds) from an HTTP 429/503 error."""
        resp = getattr(e, "response", None)
        if resp is None:
            return None
        status = getattr(resp, "status_code", None)
        if status not in (429, 503):
            return None
        raw = resp.headers.get("Retry-After") if hasattr(resp, "headers") else None
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def is_alive(self) -> bool:
        try:
            resp = self._session.get("/models", headers=self._headers(), timeout=5.0)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("[OpenRouter] is_alive check failed: %s", e)
            return False

    async def ais_alive(self) -> bool:
        try:
            resp = await self._session.aget("/models", headers=self._headers(), timeout=5.0)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("[OpenRouter] async is_alive check failed: %s", e)
            return False

    def _has_image_reference(self, text: str) -> bool:
        return bool(self.IMAGE_EXTENSIONS.search(text))

    def _build_messages(
        self,
        system: str = "",
        user: str = "",
        history: Optional[list] = None,
    ) -> list:

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        if user:
            messages.append({"role": "user", "content": user})
        elif system and not user and not history:
            messages.append({"role": "user", "content": system})
        return messages

    # ==================================================
    # SYNC INTERFACE
    # ==================================================

    def generate(
        self,
        system: str = "",
        user: str = "",
        history: Optional[list] = None,
        simple: bool = False,
    ) -> str:

        last_error: Optional[Exception] = None

        combined = system + user
        if self._has_image_reference(combined):
            logger.info("[OpenRouter] Detected image reference in prompt")
            return "I can't read or analyze images — I'm a text-only assistant."

        messages = self._build_messages(system, user, history)

        if self._circuit_open():
            logger.warning("[OpenRouter] Circuit open — skipping request")
            raise RuntimeError("OpenRouter circuit breaker open")

        models_to_try = self.models[:1] if simple else self.models
        max_attempts = max(1, int(LLM_RETRY_COUNT))
        deadline = time.monotonic() + self.max_retry_budget
        budget_hit = False

        def budget_exhausted() -> bool:
            if self.max_retry_budget <= 0:
                return False
            if time.monotonic() >= deadline:
                logger.warning("[OpenRouter] Retry budget exhausted — aborting request")
                return True
            return False

        for model in models_to_try:
            if budget_hit:
                break
            logger.info("[OpenRouter] Using model: %s", model)

            payload = {"model": model, "messages": messages}

            for attempt in range(max_attempts):
                if budget_exhausted():
                    # Stop retrying, but fall through to the shared error
                    # handling below: a failure that already has a graceful
                    # answer (e.g. the image block) must still get it instead
                    # of an opaque budget exception.
                    budget_hit = True
                    break

                try:
                    resp = self._session.post(
                        "/chat/completions",
                        headers=self._headers(),
                        json=payload,
                        timeout=LLM_TIMEOUT,
                    )
                    try:
                        resp.raise_for_status()
                        data = resp.json()
                        content: str = data["choices"][0]["message"]["content"]

                        if "does not support image" in content.lower():
                            logger.warning("Model returned image support error: %s", model)
                            raise ValueError(content)

                        self._record_success()
                        return content
                    finally:
                        resp.close()

                except Exception as e:
                    last_error = e
                    logger.warning(
                        "%s attempt %d/%d failed: %s",
                        model, attempt + 1, max_attempts, e
                    )

                    if attempt < max_attempts - 1:
                        remaining = 0.0
                        if self.max_retry_budget > 0:
                            remaining = max(0.0, deadline - time.monotonic())
                        retry_after = self._retry_after_from_error(e)
                        if retry_after is not None:
                            delay = min(retry_after, 30)
                            logger.info("[OpenRouter] Retry-After: backing off %.1fs", delay)
                            if delay <= remaining:
                                time.sleep(delay)
                            else:
                                logger.info("[OpenRouter] Retry-After %.1fs exceeds budget — aborting", delay)
                        else:
                            delay = min(2 ** attempt, 8)
                            if delay <= remaining:
                                time.sleep(delay)

            logger.info("Failing over from %s", model)

        if last_error is None:
            last_error = RuntimeError("All OpenRouter models failed without raising an exception")
        self._record_failure()

        error_msg = str(last_error).lower()
        if "image" in error_msg or "does not support" in error_msg:
            return "I can't read or analyze images — I'm a text-only assistant."
        if budget_hit:
            raise RuntimeError("OpenRouter retry budget exhausted") from last_error
        raise last_error

    def stream(
        self,
        system: str = "",
        user: str = "",
        history: Optional[list] = None,
    ) -> Iterator[str]:

        if self._circuit_open():
            logger.warning("[OpenRouter] Circuit open — skipping stream")
            yield "I'm sorry, I can't respond right now."
            return

        combined = system + user
        if self._has_image_reference(combined):
            yield "I can't read or analyze images — I'm a text-only assistant."
            return

        messages = self._build_messages(system, user, history)

        headers = self._headers()
        payload = {
            "model": self.models[0],
            "messages": messages,
            "stream": True,
        }

        try:
            resp = self._session.post(
                "/chat/completions",
                headers=headers,
                json=payload,
                timeout=LLM_TIMEOUT + 30,
            )
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8", errors="replace")
                if decoded.startswith("data: "):
                    data_str = decoded[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        pass
            self._record_success()
        except Exception as e:
            logger.warning("[OpenRouter] Stream failed: %s", e)
            self._record_failure()
            yield "I'm sorry, something went wrong."

    # ==================================================
    # ASYNC INTERFACE
    # ==================================================

    async def agenerate(
        self,
        system: str = "",
        user: str = "",
        history: Optional[list] = None,
        simple: bool = False,
    ) -> str:

        last_error: Optional[Exception] = None

        combined = system + user
        if self._has_image_reference(combined):
            logger.info("[OpenRouter] Detected image reference in prompt")
            return "I can't read or analyze images — I'm a text-only assistant."

        messages = self._build_messages(system, user, history)

        if self._circuit_open():
            logger.warning("[OpenRouter] Circuit open — skipping request")
            raise RuntimeError("OpenRouter circuit breaker open")

        models_to_try = self.models[:1] if simple else self.models
        max_attempts = max(1, int(LLM_RETRY_COUNT))
        deadline = time.monotonic() + self.max_retry_budget

        def budget_exhausted() -> bool:
            if self.max_retry_budget <= 0:
                return False
            if time.monotonic() >= deadline:
                logger.warning("[OpenRouter] Retry budget exhausted — aborting request")
                return True
            return False

        for model in models_to_try:
            logger.info("[OpenRouter] Using model: %s", model)

            payload = {"model": model, "messages": messages}

            for attempt in range(max_attempts):
                if budget_exhausted():
                    raise RuntimeError("OpenRouter retry budget exhausted") from last_error

                try:
                    resp = await self._session.apost(
                        "/chat/completions",
                        headers=self._headers(),
                        json=payload,
                        timeout=LLM_TIMEOUT,
                    )
                    try:
                        resp.raise_for_status()
                        data = resp.json()
                        content: str = data["choices"][0]["message"]["content"]

                        if "does not support image" in content.lower():
                            logger.warning("Model returned image support error: %s", model)
                            raise ValueError(content)

                        self._record_success()
                        return content
                    finally:
                        resp.close()

                except Exception as e:
                    last_error = e
                    logger.warning(
                        "%s attempt %d/%d failed: %s",
                        model, attempt + 1, max_attempts, e
                    )

                    if attempt < max_attempts - 1:
                        remaining = 0.0
                        if self.max_retry_budget > 0:
                            remaining = max(0.0, deadline - time.monotonic())
                        retry_after = self._retry_after_from_error(e)
                        if retry_after is not None:
                            delay = min(retry_after, 30)
                            logger.info("[OpenRouter] Retry-After: backing off %.1fs", delay)
                            if delay <= remaining:
                                await asyncio.sleep(delay)
                            else:
                                logger.info("[OpenRouter] Retry-After %.1fs exceeds budget — aborting", delay)
                        else:
                            delay = min(2 ** attempt, 8)
                            if delay <= remaining:
                                await asyncio.sleep(delay)

            logger.info("Failing over from %s", model)

        if last_error is None:
            last_error = RuntimeError("All OpenRouter models failed without raising an exception")
        self._record_failure()

        error_msg = str(last_error).lower()
        if "image" in error_msg or "does not support" in error_msg:
            return "I can't read or analyze images — I'm a text-only assistant."
        raise last_error

    async def astream(
        self,
        system: str = "",
        user: str = "",
        history: Optional[list] = None,
    ) -> AsyncIterator[str]:

        import asyncio

        if self._circuit_open():
            logger.warning("[OpenRouter] Circuit open — skipping stream")
            yield "I'm sorry, I can't respond right now."
            return

        combined = system + user
        if self._has_image_reference(combined):
            yield "I can't read or analyze images — I'm a text-only assistant."
            return

        messages = self._build_messages(system, user, history)

        headers = self._headers()
        payload = {
            "model": self.models[0],
            "messages": messages,
            "stream": True,
        }

        try:
            resp = await self._session.apost(
                "/chat/completions",
                headers=headers,
                json=payload,
                timeout=LLM_TIMEOUT + 30,
            )
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        pass
            self._record_success()
        except Exception as e:
            logger.warning("[OpenRouter] Async stream failed: %s", e)
            self._record_failure()
            yield "I'm sorry, something went wrong."