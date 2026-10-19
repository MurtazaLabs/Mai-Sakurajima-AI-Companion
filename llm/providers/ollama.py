# llm/providers/ollama.py

import asyncio
import json
import logging
import re
import threading
import time
from typing import Iterator, Optional, AsyncIterator

from llm.http_client import HTTPClientFactory
from app.config_loader import (
    LLM_MODEL,
    LLM_RETRY_COUNT,
    LLM_TEMPERATURE,
    LLM_MAX_CONTEXT,
    LLM_TIMEOUT,
)

logger = logging.getLogger("Mai.OllamaProvider")


class OllamaProvider:

    IMAGE_EXTENSIONS = re.compile(
        r'\b\w+\.(png|jpg|jpeg|gif|bmp|webp|svg|tiff|ico)\b',
        re.IGNORECASE
    )

    def __init__(
        self,
        model: str = LLM_MODEL,
        base_url: str = "http://localhost:11434",
        temperature: Optional[float] = None,
        context_window: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> None:

        self.model = model
        self.base_url = base_url.rstrip("/")

        self.temperature = (
            temperature if temperature is not None
            else LLM_TEMPERATURE
        )

        self.context_window = (
            context_window if context_window is not None else LLM_MAX_CONTEXT
        )

        self.timeout = timeout if timeout is not None else LLM_TIMEOUT
        self.max_tokens = 8192

        self._cancel_event = threading.Event()

# Pooled HTTP client
        self._http = HTTPClientFactory.get_client(
            base_url=self.base_url,
            max_connections=50,
            max_keepalive=10,
            keepalive_expiry=30.0,
            timeout=self.timeout,
        )

        # Backward compatibility: expose a _session object with get/post methods
        # that tests can mock. This mimics requests.Session interface.
        class _SessionCompat:
            def __init__(self, http_client, base_url: str):
                self._http = http_client
                self._base_url = base_url.rstrip("/")
            
            def get(self, url, **kwargs):
                # Construct full URL for test compatibility (tests expect full URLs)
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

    def _headers(self) -> dict:
        return {"Content-Type": "application/json"}

    def _options(self) -> dict:
        return {
            "temperature": self.temperature,
            "num_ctx": self.context_window,
            "num_predict": self.max_tokens,
        }

    def _build_messages(
        self,
        system: str,
        user: str,
        history: Optional[list] = None,
    ) -> list:

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        if user:
            messages.append({"role": "user", "content": user})
        return messages

    def _chat_payload(
        self,
        messages: list,
        stream: bool = False,
    ) -> dict:

        return {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            # Top-level /api/chat field (boolean|string): false suppresses
            # thinking output so voice replies don't wait on reasoning.
            "think": False,
            "options": self._options(),
        }

    def _check_image_error(self, content: str) -> Optional[str]:
        if "does not support image" in content.lower():
            return "I can't read or analyze images — I'm a text-only assistant."
        return None

    def _has_image_reference(self, text: str) -> bool:
        return bool(self.IMAGE_EXTENSIONS.search(text))

    # ==================================================
    # SYNC INTERFACE
    # ==================================================

    def is_alive(self) -> bool:
        try:
            resp = self._session.get(f"{self.base_url}/api/tags", timeout=2.0)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("[Ollama] is_alive check failed: %s", e)
            return False

    async def ais_alive(self) -> bool:
        try:
            resp = await self._session.aget(f"{self.base_url}/api/tags", timeout=2.0)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("[Ollama] async is_alive check failed: %s", e)
            return False

    def generate(
        self,
        system: str,
        user: str,
        history: Optional[list] = None,
        retries: int = None,
    ) -> str:

        if retries is None:
            retries = LLM_RETRY_COUNT

        if self._has_image_reference(system + user):
            logger.info("Detected image reference in prompt")
            return "I can't read or analyze images — I'm a text-only assistant."

        messages = self._build_messages(system, user, history)
        payload = self._chat_payload(messages)

        for attempt in range(retries):
            try:
                start = time.time()

                try:
                    resp = self._session.post(
                        f"{self.base_url}/api/chat",
                        headers=self._headers(),
                        json=payload,
                        timeout=self.timeout,
                    )
                except Exception as e:
                    logger.error("Attempt %s/%s failed: %s", attempt + 1, retries, e)
                    if attempt < retries - 1:
                        time.sleep(min(2 ** attempt, 8))
                    continue

                try:
                    resp.raise_for_status()
                    data = resp.json()
                    content: str = data["message"]["content"].strip()

                    latency = round(time.time() - start, 2)
                    logger.info("Response in %ss", latency)

                    image_msg = self._check_image_error(content)
                    if image_msg:
                        return image_msg

                    return content
                finally:
                    resp.close()

            except Exception as e:
                logger.error("Attempt %s/%s failed: %s", attempt + 1, retries, e)

                if attempt < retries - 1:
                    time.sleep(min(2 ** attempt, 8))

        raise RuntimeError("Ollama generation failed after all retries")

    def stream(
        self,
        system: str,
        user: str,
        history: Optional[list] = None,
    ) -> Iterator[str]:

        self._cancel_event.clear()

        if self._has_image_reference(system + user):
            yield "I can't read or analyze images — I'm a text-only assistant."
            return

        messages = self._build_messages(system, user, history)
        payload = self._chat_payload(messages, stream=True)

        try:
            start = time.time()
            resp = self._session.post(
                f"{self.base_url}/api/chat",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
            try:
                resp.raise_for_status()

                buffer = ""

                for line in resp.iter_lines(decode_unicode=True):
                    if self._cancel_event.is_set():
                        logger.info("Stream cancelled")
                        return

                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")

                        if not content:
                            continue

                        buffer += content

                        while self._has_sentence(buffer):
                            sentence, buffer = self._extract_sentence(buffer)
                            if sentence:
                                yield sentence

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logger.error("Stream chunk error: %s", e)

                if buffer.strip():
                    yield buffer.strip()

                latency = round(time.time() - start, 2)
                logger.info("Stream finished in %ss", latency)
            finally:
                resp.close()

        except Exception as e:
            logger.error("Stream error: %s", e)
            yield "…something went wrong."

    def cancel_stream(self) -> None:
        self._cancel_event.set()

    def generate_with_tools(
        self,
        system: str,
        user: str,
        history: Optional[list] = None,
    ) -> str:

        original = self.temperature
        try:
            self.temperature = 0.2
            return self.generate(system, user, history)
        except Exception as e:
            logger.error("[Ollama] generate_with_tools failed: %s", e)
            return None
        finally:
            self.temperature = original

    def generate_json(
        self,
        system: str,
        user: str,
        history: Optional[list] = None,
    ) -> str:

        prompt = system + "\n\nReturn ONLY valid JSON."
        return self.generate(prompt, user, history)

    # ==================================================
    # ASYNC INTERFACE
    # ==================================================

    async def agenerate(
        self,
        system: str,
        user: str,
        history: Optional[list] = None,
        retries: int = None,
    ) -> str:

        if retries is None:
            retries = LLM_RETRY_COUNT

        if self._has_image_reference(system + user):
            logger.info("Detected image reference in prompt")
            return "I can't read or analyze images — I'm a text-only assistant."

        messages = self._build_messages(system, user, history)
        payload = self._chat_payload(messages)

        for attempt in range(retries):
            try:
                start = time.time()

                try:
                    resp = await self._session.apost(
                        "/api/chat",
                        headers=self._headers(),
                        json=payload,
                        timeout=self.timeout,
                    )
                except Exception as e:
                    logger.error("Async attempt %s/%s failed: %s", attempt + 1, retries, e)
                    if attempt < retries - 1:
                        await asyncio.sleep(min(2 ** attempt, 8))
                    continue

                try:
                    resp.raise_for_status()
                    data = resp.json()
                    content: str = data["message"]["content"].strip()

                    latency = round(time.time() - start, 2)
                    logger.info("Async response in %ss", latency)

                    image_msg = self._check_image_error(content)
                    if image_msg:
                        return image_msg

                    return content
                finally:
                    resp.close()

            except Exception as e:
                logger.error("Async attempt %s/%s failed: %s", attempt + 1, retries, e)

                if attempt < retries - 1:
                    await asyncio.sleep(min(2 ** attempt, 8))

        raise RuntimeError("Ollama async generation failed after all retries")

    async def astream(
        self,
        system: str,
        user: str,
        history: Optional[list] = None,
    ) -> AsyncIterator[str]:

        self._cancel_event.clear()

        if self._has_image_reference(system + user):
            yield "I can't read or analyze images — I'm a text-only assistant."
            return

        messages = self._build_messages(system, user, history)
        payload = self._chat_payload(messages, stream=True)

        try:
            start = time.time()
            resp = await self._session.apost(
                f"{self.base_url}/api/chat",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
            try:
                resp.raise_for_status()

                buffer = ""

                async for line in resp.aiter_lines(decode_unicode=True):
                    if self._cancel_event.is_set():
                        logger.info("Stream cancelled")
                        return

                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")

                        if not content:
                            continue

                        buffer += content

                        while self._has_sentence(buffer):
                            sentence, buffer = self._extract_sentence(buffer)
                            if sentence:
                                yield sentence

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logger.error("Async stream chunk error: %s", e)

                if buffer.strip():
                    yield buffer.strip()

                latency = round(time.time() - start, 2)
                logger.info("Async stream finished in %ss", latency)
            finally:
                resp.close()

        except Exception as e:
            logger.error("Async stream error: %s", e)
            yield "…something went wrong."

    async def acancel_stream(self) -> None:
        self._cancel_event.set()

    async def agenerate_with_tools(
        self,
        system: str,
        user: str,
        history: Optional[list] = None,
    ) -> str:

        original = self.temperature
        try:
            self.temperature = 0.2
            return await self.agenerate(system, user, history)
        except Exception as e:
            logger.error("[Ollama] async generate_with_tools failed: %s", e)
            return None
        finally:
            self.temperature = original

    async def agenerate_json(
        self,
        system: str,
        user: str,
        history: Optional[list] = None,
    ) -> str:

        prompt = system + "\n\nReturn ONLY valid JSON."
        return await self.agenerate(prompt, user, history)

    def _has_sentence(self, text: str) -> bool:
        endings = [". ", "? ", "! ", "\n"]
        return any(ending in text for ending in endings)

    def _extract_sentence(self, text: str):
        endings = [". ", "? ", "! ", "\n"]
        indexes = [text.find(e) for e in endings if text.find(e) != -1]
        if not indexes:
            return None, text
        index = min(indexes)
        sentence = text[:index + 1].strip()
        remaining = text[index + 1:].strip()
        return sentence, remaining