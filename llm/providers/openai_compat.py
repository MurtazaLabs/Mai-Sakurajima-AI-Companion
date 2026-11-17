# llm/providers/openai_compat.py

"""OpenAI-compatible chat provider (llama.cpp ``llama-server``, LM Studio, vLLM).

llama.cpp serves ``/v1/chat/completions`` with SSE streaming and ``/health``;
it does **not** implement Ollama's ``/api/chat``, so ``OllamaProvider`` cannot
be reused (plan: docs/Mai_documentation/03-Features/llamacpp-local-llm-plan.md).

Deliberate differences from ``OllamaProvider``:
- ``stream()`` yields raw content deltas instead of sentence buckets — the
  downstream pipeline (``RealtimeVoice.speak_stream``) already aggregates by
  sentence, so bucketing here would only add latency.
- ``stream()`` **raises** on failure instead of yielding an apology string, so
  ``LLMManager._stream_with_failover`` can move to the next provider.
- Permanent HTTP client errors (4xx) are not retried — retrying the same
  request cannot fix them.
"""
import json
import logging
import threading
import time
from collections.abc import Iterator

from app.config_loader import (
    LLAMACPP_API_KEY,
    LLAMACPP_BASE_URL,
    LLAMACPP_MODEL,
    LLM_MAX_CONTEXT,
    LLM_RETRY_COUNT,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    LLM_TOP_P,
)
from llm.http_client import HTTPClientFactory

logger = logging.getLogger("Mai.OpenAICompat")

# 4xx responses that retrying the identical request can never fix.
_PERMANENT_STATUS = (400, 401, 403, 404, 422)


def _status_code(exc: Exception) -> int | None:
    resp = getattr(exc, "response", None)
    return getattr(resp, "status_code", None)


class OpenAICompatProvider:

    def __init__(
        self,
        model: str = LLAMACPP_MODEL,
        base_url: str = LLAMACPP_BASE_URL,
        api_key: str = LLAMACPP_API_KEY,
        temperature: float | None = None,
        context_window: int | None = None,
        timeout: int | None = None,
    ) -> None:

        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.temperature = temperature if temperature is not None else LLM_TEMPERATURE
        self.context_window = (
            context_window if context_window is not None else LLM_MAX_CONTEXT
        )
        self.timeout = timeout if timeout is not None else LLM_TIMEOUT

        self._cancel_event = threading.Event()
        self._http = HTTPClientFactory.get_client(
            base_url=self.base_url,
            max_connections=50,
            max_keepalive=10,
            keepalive_expiry=30.0,
            timeout=self.timeout,
        )

        self._calls = 0
        self._last_latency = 0.0

    # ---------------- helpers ----------------

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_messages(
        self,
        system: str,
        user: str,
        history: list | None = None,
    ) -> list:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        if user:
            messages.append({"role": "user", "content": user})
        return messages

    def _payload(self, messages: list, stream: bool = False, temperature: float | None = None) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "temperature": self.temperature if temperature is None else temperature,
            "top_p": LLM_TOP_P,
        }

    # ---------------- sync interface ----------------

    def is_alive(self) -> bool:
        """llama.cpp exposes /health; fall back to /v1/models for other servers."""
        try:
            resp = self._http.get(f"{self.base_url}/health", timeout=2.0)
            if resp.status_code == 200:
                return True
            if resp.status_code != 404:
                return False
            resp = self._http.get(f"{self.base_url}/v1/models", timeout=2.0)
            return resp.status_code == 200
        except Exception as e:
            logger.debug("[OpenAICompat] is_alive check failed: %s", e)
            return False

    def generate(
        self,
        system: str,
        user: str,
        history: list | None = None,
        retries: int | None = None,
    ) -> str:

        if retries is None:
            retries = LLM_RETRY_COUNT

        messages = self._build_messages(system, user, history)
        payload = self._payload(messages)

        for attempt in range(retries):
            start = time.time()
            try:
                resp = self._http.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=self._headers(),
                    json=payload,
                    timeout=self.timeout,
                )
            except Exception as e:
                logger.warning(
                    "[OpenAICompat] attempt %s/%s failed: %s", attempt + 1, retries, e
                )
                if attempt < retries - 1:
                    time.sleep(min(2 ** attempt, 8))
                continue

            status = resp.status_code
            if status >= 400:
                permanent = status in _PERMANENT_STATUS
                logger.warning(
                    "[OpenAICompat] HTTP %s from %s%s",
                    status,
                    self.base_url,
                    " (not retrying)" if permanent else "",
                )
                if permanent:
                    raise RuntimeError(f"OpenAICompat HTTP {status}")
                if attempt < retries - 1:
                    time.sleep(min(2 ** attempt, 8))
                continue

            data = resp.json()
            content = (data["choices"][0]["message"]["content"] or "").strip()
            self._calls += 1
            self._last_latency = round(time.time() - start, 2)
            logger.info(
                "[OpenAICompat] response in %ss (%s tok/s)",
                self._last_latency,
                round(data.get("timings", {}).get("predicted_per_second", 0), 1),
            )
            return content

        raise RuntimeError("OpenAICompat generation failed after all retries")

    def stream(
        self,
        system: str,
        user: str,
        history: list | None = None,
    ) -> Iterator[str]:

        self._cancel_event.clear()
        messages = self._build_messages(system, user, history)
        payload = self._payload(messages, stream=True)

        start = time.time()
        first_token_at = None
        for line in self._http.stream_lines(
            f"{self.base_url}/v1/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        ):
            if self._cancel_event.is_set():
                logger.info("[OpenAICompat] stream cancelled")
                return
            if not line:
                continue
            if not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices") or [{}]
            delta = (choices[0].get("delta") or {}).get("content")
            if not delta:
                continue
            if first_token_at is None:
                first_token_at = time.time() - start
                logger.info("[OpenAICompat] first token in %.2fs", first_token_at)
            yield delta

        self._calls += 1
        self._last_latency = round(time.time() - start, 2)
        logger.info("[OpenAICompat] stream finished in %ss", self._last_latency)

    def cancel_stream(self) -> None:
        self._cancel_event.set()

    def generate_with_tools(
        self,
        system: str,
        user: str,
        history: list | None = None,
    ) -> str:
        """Tool/JSON turns want determinism, not personality."""
        try:
            messages = self._build_messages(system, user, history)
            payload = self._payload(messages, temperature=0.2)
            resp = self._http.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"OpenAICompat HTTP {resp.status_code}")
            data = resp.json()
            self._calls += 1
            return (data["choices"][0]["message"]["content"] or "").strip()
        except Exception as e:
            logger.error("[OpenAICompat] generate_with_tools failed: %s", e)
            return None

    def stats(self) -> dict:
        return {
            "provider": "llamacpp",
            "model": self.model,
            "base_url": self.base_url,
            "calls": self._calls,
            "last_latency_seconds": self._last_latency,
            "available": self.is_alive(),
        }
