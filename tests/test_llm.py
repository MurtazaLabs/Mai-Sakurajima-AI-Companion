import json
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
#  OllamaProvider tests
# ---------------------------------------------------------------------------

class TestOllamaProviderIsAlive:

    def test_is_alive_returns_true_on_200(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="test-model", base_url="http://localhost:11434")
        with patch.object(provider._session, "get") as mock_get:
            mock_get.return_value.status_code = 200
            assert provider.is_alive() is True
            mock_get.assert_called_once_with(
                "http://localhost:11434/api/tags", timeout=2
            )

    def test_is_alive_returns_false_on_non_200(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider()
        with patch.object(provider._session, "get") as mock_get:
            mock_get.return_value.status_code = 503
            assert provider.is_alive() is False

    def test_is_alive_returns_false_on_exception(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider()
        with patch.object(provider._session, "get") as mock_get:
            mock_get.side_effect = ConnectionError("refused")
            assert provider.is_alive() is False


class TestOllamaProviderGenerate:

    def test_generate_returns_text_on_success(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="test-model", base_url="http://localhost:11434")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": " Hello world "}
        }
        with patch.object(provider._session, "post", return_value=mock_response):
            result = provider.generate("You are a bot", "Hi")
        assert result == "Hello world"

    def test_generate_image_reference_returns_blocked_message(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider()
        result = provider.generate("", "check this photo.png")
        assert "can't read" in result

    def test_generate_retries_on_failure_then_raises(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="test-model", base_url="http://localhost:11434")
        with patch.object(provider._session, "post") as mock_post:
            mock_post.side_effect = ConnectionError("server down")
            with pytest.raises(RuntimeError, match="Ollama generation failed"):
                provider.generate("system", "user", retries=2)
        assert mock_post.call_count == 2

    def test_generate_succeeds_on_retry(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="test-model", base_url="http://localhost:11434")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "ok"}}
        with patch.object(provider._session, "post") as mock_post:
            mock_post.side_effect = [ConnectionError("fail"), mock_response]
            result = provider.generate("system", "user", retries=2)
        assert result == "ok"
        assert mock_post.call_count == 2

    def test_generate_image_error_in_response(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="test-model", base_url="http://localhost:11434")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "model does not support image"}
        }
        with patch.object(provider._session, "post", return_value=mock_response):
            result = provider.generate("system", "user")
        assert result == "I can't read or analyze images — I'm a text-only assistant."

    def test_generate_respects_temperature_context_window(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(
            model="m", base_url="http://localhost:11434",
            temperature=0.7, context_window=4096, timeout=30,
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "ok"}}
        with patch.object(provider._session, "post", return_value=mock_response) as mock_post:
            provider.generate("sys", "usr")

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["model"] == "m"
        assert payload["options"]["temperature"] == 0.7
        assert payload["options"]["num_ctx"] == 4096
        assert payload["options"]["num_predict"] == 8192


class TestOllamaProviderStream:

    def test_stream_yields_sentences(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="test-model", base_url="http://localhost:11434")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            '{"message": {"content": "Hello"}}',
            '{"message": {"content": " world. "}}',
            '{"message": {"content": "How are"}}',
            '{"message": {"content": " you?"}}',
        ]
        with patch.object(provider._session, "post", return_value=mock_response):
            chunks = list(provider.stream("sys", "user"))
        assert len(chunks) >= 1
        assert any("Hello world" in c for c in chunks)

    def test_stream_image_reference_returns_blocked(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider()
        chunks = list(provider.stream("", "image.jpg in prompt"))
        assert chunks == ["I can't read or analyze images — I'm a text-only assistant."]

    def test_stream_on_error_yields_fallback(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="test-model", base_url="http://localhost:11434")
        with patch.object(provider._session, "post", side_effect=ConnectionError("fail")):
            chunks = list(provider.stream("sys", "user"))
        assert chunks == ["…something went wrong."]

    def test_stream_cancel_stops_yielding(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="test-model", base_url="http://localhost:11434")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            '{"message": {"content": "Hello"}}',
        ]

        def raise_cancel(*a, **kw):
            provider._cancel_event.set()
            return mock_response

        with patch.object(provider._session, "post", side_effect=raise_cancel):
            chunks = list(provider.stream("sys", "user"))
        assert len(chunks) == 0

    def test_stream_skips_empty_lines_and_bad_json(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="test-model", base_url="http://localhost:11434")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            "",
            "not-json",
            '{"message": {"content": "Hi"}}',
        ]
        with patch.object(provider._session, "post", return_value=mock_response):
            chunks = list(provider.stream("sys", "user"))
        assert len(chunks) >= 1


class TestOllamaProviderGenerateWithTools:

    def test_generate_with_tools_lowers_temperature(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="m", base_url="http://localhost:11434", temperature=0.7)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "result"}}
        with patch.object(provider._session, "post", return_value=mock_response):
            provider.generate_with_tools("sys", "usr")
        assert provider.temperature == 0.7

    def test_generate_with_tools_restores_temperature_on_error(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="m", base_url="http://localhost:11434", temperature=0.5)
        original = provider.temperature
        with patch.object(provider._session, "post", side_effect=RuntimeError("boom")):
            result = provider.generate_with_tools("sys", "usr")
        assert provider.temperature == original
        assert provider.temperature == 0.5
        assert result is None


class TestOllamaProviderGenerateJSON:

    def test_generate_json_appends_json_instruction(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="m", base_url="http://localhost:11434")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": '{"key": "val"}'}}
        with patch.object(provider._session, "post", return_value=mock_response) as mock_post:
            result = provider.generate_json("Return data", "get it")
        assert result == '{"key": "val"}'
        sent_system = mock_post.call_args[1]["json"]["messages"][0]["content"]
        assert "Return ONLY valid JSON" in sent_system


class TestOllamaProviderSentenceUtils:

    def test_has_sentence_detects_endings(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider()
        assert provider._has_sentence("Hello. ") is True
        assert provider._has_sentence("Hi? ") is True
        assert provider._has_sentence("Wow! ") is True
        assert provider._has_sentence("Hey\n") is True
        assert provider._has_sentence("Hello") is False

    def test_extract_sentence_splits_correctly(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider()
        sentence, remaining = provider._extract_sentence("Hello world. Next part.")
        assert sentence == "Hello world."
        assert remaining == "Next part."

    def test_extract_sentence_no_ending(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider()
        sentence, remaining = provider._extract_sentence("No ending")
        assert sentence is None
        assert remaining == "No ending"


# ---------------------------------------------------------------------------
#  OpenRouterProvider tests
# ---------------------------------------------------------------------------

class TestOpenRouterProviderIsAlive:

    def test_is_alive_returns_true_on_200(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test")
        with patch.object(provider._session, "get") as mock_get:
            mock_get.return_value.status_code = 200
            assert provider.is_alive() is True

    def test_is_alive_returns_false_on_exception(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test")
        with patch.object(provider._session, "get") as mock_get:
            mock_get.side_effect = TimeoutError("timeout")
            assert provider.is_alive() is False


class TestOpenRouterProviderGenerate:

    def _make_or_provider(self, api_key="sk-test", models=None, **kwargs):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key=api_key, models=models, **kwargs)
        return provider

    def test_generate_returns_content_on_success(self):
        provider = self._make_or_provider()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello from OR"}}]
        }
        with patch.object(provider._session, "post", return_value=mock_response):
            result = provider.generate("You are a bot", "Hi")
        assert result == "Hello from OR"

    def test_generate_image_reference_returns_blocked(self):
        provider = self._make_or_provider()
        result = provider.generate("", "look at cat.png")
        assert "can't read" in result

    def test_generate_tries_all_models_then_raises(self):
        provider = self._make_or_provider(models=["m1", "m2"])
        with patch.object(provider._session, "post") as mock_post:
            mock_post.side_effect = ConnectionError("fail")
            with pytest.raises(ConnectionError):
                provider.generate("sys", "usr")
        assert mock_post.call_count == 6  # 2 models * 3 retries

    def test_generate_fallbacks_to_next_model_after_retries(self):
        provider = self._make_or_provider(models=["m1", "m2"])
        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        with patch.object(provider._session, "post") as mock_post:
            mock_post.side_effect = [ConnectionError("fail")] * 3 + [mock_ok]
            result = provider.generate("sys", "usr")
        assert result == "ok"

    def test_generate_retry_budget_bounds_backoff(self):
        """A 30s Retry-After must not be honoured once the global budget is
        exhausted — the request aborts fast instead of sleeping minutes
        (P-4)."""
        provider = self._make_or_provider(models=["m1", "m2"],
                                         max_retry_budget=1.0)

        def _fail(*a, **k):
            e = RuntimeError("rate limited")
            resp = MagicMock()
            resp.status_code = 429
            resp.headers = {"Retry-After": "30"}
            e.response = resp
            raise e

        with patch.object(provider._session, "post", side_effect=_fail) as mock_post:
            with patch("time.monotonic", side_effect=[0, 0, 0, 5, 5, 5, 5, 5, 5]):
                # After the first attempt, time.monotonic jumps past the
                # deadline so every subsequent iteration gates on the budget.
                with pytest.raises(RuntimeError, match="exhausted"):
                    provider.generate("sys", "usr")
        # Budget forces fast abort — only a small bounded number of HTTP
        # calls, never the full 3 models x 3 attempts x 30s wait.
        assert mock_post.call_count <= 3

    def test_generate_retry_budget_allows_normal_short_retries(self):
        """Small budgets still permit quick retries — only the long
        Retry-After sleeps are skipped."""
        provider = self._make_or_provider(models=["m1"],
                                          max_retry_budget=1.0)
        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        with patch.object(provider._session, "post") as mock_post:
            with patch("time.monotonic", side_effect=[0, 0, 0, 0.5, 0.6]):
                mock_post.side_effect = [RuntimeError("fail"), mock_ok]
                result = provider.generate("sys", "usr")
        assert result == "ok"

    def test_generate_image_error_in_response_fallsback_to_blocked(self):
        provider = self._make_or_provider(models=["m1"])
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "model does not support image"}}]
        }
        # The retry backoff sleeps between attempts; the fallback must not
        # depend on wall-clock time, which made this test flaky on a loaded
        # machine (the deadline expired and the error escaped instead).
        with patch.object(provider._session, "post", return_value=mock_response):
            with patch("llm.providers.openrouter.time.sleep"):
                result = provider.generate("sys", "usr")
        assert "can't read" in result

    def test_generate_image_error_survives_exhausted_retry_budget(self):
        """Regression: budget exhaustion used to raise out of generate(),
        replacing the graceful image block with a budget exception whenever the
        machine was slow enough to blow the 45s deadline."""
        provider = self._make_or_provider(models=["m1"], max_retry_budget=1.0)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "model does not support image"}}]
        }
        with patch.object(provider._session, "post", return_value=mock_response):
            with patch("time.monotonic", side_effect=[0, 0, 0, 5, 5, 5, 5, 5, 5, 5, 5, 5]):
                with patch("llm.providers.openrouter.time.sleep"):
                    result = provider.generate("sys", "usr")
        assert "can't read" in result

    def test_generate_empty_user_uses_system_as_user(self):
        provider = self._make_or_provider()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "reply"}}]
        }
        with patch.object(provider._session, "post", return_value=mock_response) as mock_post:
            provider.generate("just this text")
        messages = mock_post.call_args[1]["json"]["messages"]
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "just this text"


class TestOpenRouterModelSanitization:
    """The failover list must never contain None/empty/duplicate entries —
    an env-less OPENROUTER_DEFAULT_MODEL used to ship model:"None" (400 x3
    with backoff, ~8s per call; live log 2026-10-09)."""

    def test_default_models_are_nonempty_strings(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test")
        assert provider.models
        assert all(isinstance(m, str) and m for m in provider.models)

    def test_none_empty_and_duplicate_entries_dropped(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test", models=[None, "", "  ", "m1", "m1"])
        assert provider.models == ["m1"]

    def test_all_bad_entries_falls_back_to_auto(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test", models=[None, ""])
        assert provider.models == ["openrouter/auto"]

    def test_permanent_400_fails_over_after_one_attempt(self):
        """A 400 for one model is permanent — one attempt, then fail over,
        never the full LLM_RETRY_COUNT backoff ladder."""
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test", models=["bad-model", "good-model"])
        calls = []

        def fake_post(url, **kwargs):
            calls.append(kwargs["json"]["model"])
            if kwargs["json"]["model"] == "bad-model":
                e = RuntimeError("Client error '400 Bad Request'")
                resp = MagicMock()
                resp.status_code = 400
                e.response = resp
                raise e
            ok = MagicMock()
            ok.status_code = 200
            ok.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
            return ok

        with patch.object(provider._session, "post", side_effect=fake_post):
            result = provider.generate("sys", "usr")
        assert result == "ok"
        assert calls == ["bad-model", "good-model"]

    def test_connection_error_still_retries_full_ladder(self):
        """Non-HTTP errors (no .response) keep the existing retry behavior."""
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test", models=["m1", "m2"])
        with patch.object(provider._session, "post") as mock_post:
            mock_post.side_effect = ConnectionError("fail")
            with pytest.raises(ConnectionError):
                provider.generate("sys", "usr")
        assert mock_post.call_count == 6  # 2 models * 3 retries


class TestOpenRouterProviderStream:

    def test_stream_returns_tokens_from_sse(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test")
        sse_lines = [
            b"data: " + json.dumps({"choices": [{"delta": {"content": "Hello"}}]}).encode(),
            b"data: " + json.dumps({"choices": [{"delta": {"content": " world"}}]}).encode(),
            b"data: [DONE]",
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = sse_lines
        with patch.object(provider._session, "post", return_value=mock_resp):
            chunks = list(provider.stream("sys", "usr"))
        assert chunks == ["Hello", " world"]

    def test_stream_circuit_open_returns_fallback(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test")
        provider._circuit_open_until = 9999999999.0
        chunks = list(provider.stream("sys", "usr"))
        assert len(chunks) == 1
        assert "sorry" in chunks[0].lower()

    def test_stream_image_reference_returns_blocked(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test")
        chunks = list(provider.stream("", "look at cat.png"))
        assert any("can't read" in c for c in chunks)


# ---------------------------------------------------------------------------
#  LLMManager tests
# ---------------------------------------------------------------------------

class TestLLMManagerIsAvailable:

    def test_available_when_openrouter_alive(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = True
        assert manager.is_available() is True
        manager.ollama.is_alive.assert_not_called()

    def test_available_when_only_ollama_alive(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = False
        manager.ollama.is_alive.return_value = True
        assert manager.is_available() is True

    def test_unavailable_when_both_dead(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = False
        manager.ollama.is_alive.return_value = False
        assert manager.is_available() is False


class TestLLMManagerGenerate:

    def test_generate_uses_openrouter_first(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = True
        manager.openrouter.generate.return_value = "or response"
        result = manager.generate("sys", "usr")
        assert result == "or response"
        manager.ollama.generate.assert_not_called()

    def test_generate_fallsback_to_ollama_on_openrouter_error(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = True
        manager.openrouter.generate.side_effect = RuntimeError("or fail")
        manager.ollama.is_alive.return_value = True
        manager.ollama.generate.return_value = "ollama response"
        result = manager.generate("sys", "usr")
        assert result == "ollama response"

    def test_generate_fallsback_when_openrouter_unreachable(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = False
        manager.ollama.is_alive.return_value = True
        manager.ollama.generate.return_value = "ollama ok"
        result = manager.generate("sys", "usr")
        assert result == "ollama ok"

    def test_generate_raises_when_both_unavailable(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = False
        manager.ollama.is_alive.return_value = False
        result = manager.generate("sys", "usr")
        assert "unavailable" in result

    def test_generate_passes_history(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = True
        manager.generate("sys", "usr", history=[{"role": "assistant", "content": "prev"}])
        manager.openrouter.generate.assert_called_once_with(
            "sys", "usr", [{"role": "assistant", "content": "prev"}], simple=True
        )

    def test_generate_with_tools_delegates_to_generate(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = True
        manager.openrouter.generate.return_value = "tool result"
        result = manager.generate_with_tools("sys", "usr")
        assert result == "tool result"


class TestLLMManagerStream:

    def test_stream_uses_openrouter_when_available(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = True
        manager.openrouter.stream.return_value = iter(["chunk1", "chunk2"])
        chunks = list(manager.stream("sys", "usr"))
        assert chunks == ["chunk1", "chunk2"]

    def test_stream_fallsback_to_ollama_on_openrouter_error(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = True
        manager.openrouter.stream.side_effect = RuntimeError("stream fail")
        manager.ollama.is_alive.return_value = True
        manager.ollama.stream.return_value = iter(["ollama chunk"])
        chunks = list(manager.stream("sys", "usr"))
        assert chunks == ["ollama chunk"]

    def test_stream_fallsback_to_generate_when_no_stream_method(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock(spec=["is_alive", "generate"])
        manager.ollama = MagicMock(spec=["is_alive", "generate"])
        manager.openrouter.is_alive.return_value = True
        manager.openrouter.generate.return_value = "generated fallback"
        manager.ollama.is_alive.return_value = True
        chunks = list(manager.stream("sys", "usr"))
        assert chunks == ["generated fallback"]

    def test_stream_returns_generate_when_both_no_stream(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock(spec=["is_alive", "generate"])
        manager.ollama = MagicMock(spec=["is_alive", "generate"])
        manager.openrouter.is_alive.return_value = True
        manager.openrouter.generate.return_value = "plain"
        manager.ollama.is_alive.return_value = True
        chunks = list(manager.stream("sys", "usr"))
        assert chunks == ["plain"]

    def test_stream_fallsback_to_ollama_when_openrouter_unreachable(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = False
        manager.ollama.is_alive.return_value = True
        manager.ollama.stream.return_value = iter(["c1"])
        chunks = list(manager.stream("sys", "usr"))
        assert chunks == ["c1"]

    def test_stream_failover_on_mid_iteration_error(self):
        """A provider that dies mid-stream must be marked dead and the
        request restarted on the next provider (P-2)."""
        from llm.manager import LLMManager

        def broken_gen():
            yield "partial"
            raise RuntimeError("mid-stream boom")

        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = True
        manager.openrouter.stream.return_value = broken_gen()
        manager.ollama.stream.return_value = iter(["ollama full"])
        chunks = list(manager.stream("sys", "usr"))
        assert chunks == ["partial", "ollama full"]
        assert manager._openrouter_available is False

    def test_stream_mid_iteration_failure_marks_ollama_dead_and_generates(self):
        """When the only streaming provider dies mid-stream, fall back to a
        single generate() chunk (honest, no duplicate partial)."""
        from llm.manager import LLMManager

        def broken_gen():
            yield "half"
            raise RuntimeError("boom")

        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.openrouter.is_alive.return_value = False
        manager.openrouter.stream.return_value = iter([])
        manager.ollama = MagicMock()
        manager.ollama.stream.return_value = broken_gen()
        manager.generate = MagicMock(return_value="fallback text")
        chunks = list(manager.stream("sys", "usr"))
        assert chunks == ["half", "fallback text"]
        assert manager._ollama_available is False


class TestOpenRouterProviderBuildMessages:

    def test_build_messages_with_system_user_history(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test")
        msgs = provider._build_messages("sys", "usr", [{"role": "assistant", "content": "prev"}])
        assert len(msgs) == 3
        assert msgs[0] == {"role": "system", "content": "sys"}
        assert msgs[1] == {"role": "assistant", "content": "prev"}
        assert msgs[2] == {"role": "user", "content": "usr"}

    def test_build_messages_no_history(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test")
        msgs = provider._build_messages("sys", "usr")
        assert len(msgs) == 2
        assert msgs[0] == {"role": "system", "content": "sys"}
        assert msgs[1] == {"role": "user", "content": "usr"}

    def test_build_messages_empty_user_uses_system_fallback(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test")
        msgs = provider._build_messages("only text")
        # system text is treated as both system and user when user/history empty
        assert len(msgs) == 2
        assert msgs[0] == {"role": "system", "content": "only text"}
        assert msgs[1] == {"role": "user", "content": "only text"}

    def test_build_messages_with_history_no_user(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test")
        msgs = provider._build_messages("sys", "", [{"role": "user", "content": "q"}])
        assert len(msgs) == 2
        assert msgs[0] == {"role": "system", "content": "sys"}

    def test_build_messages_empty_system_and_user_with_history(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test")
        msgs = provider._build_messages("", "", [{"role": "user", "content": "q"}])
        assert len(msgs) == 1

    def test_build_messages_empty_system_and_user_no_history(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test")
        msgs = provider._build_messages()
        assert len(msgs) == 0


class TestOllamaProviderBuildMessages:

    def test_build_messages_standard(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider()
        msgs = provider._build_messages("sys", "usr", [{"role": "assistant", "content": "a"}])
        assert len(msgs) == 3
        assert msgs[0] == {"role": "system", "content": "sys"}
        assert msgs[1] == {"role": "assistant", "content": "a"}
        assert msgs[2] == {"role": "user", "content": "usr"}

    def test_build_messages_no_history(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider()
        msgs = provider._build_messages("sys", "usr")
        assert len(msgs) == 2

    def test_build_messages_no_system(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider()
        msgs = provider._build_messages("", "usr")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"


class TestOllamaProviderHasImageReference:

    def test_detects_image_extensions(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider()
        assert provider._has_image_reference("photo.png") is True
        assert provider._has_image_reference("image.jpg") is True
        assert provider._has_image_reference("pic.JPEG") is True
        assert provider._has_image_reference("just text") is False
        assert provider._has_image_reference("file.txt") is False


class TestOpenRouterProviderHasImageReference:

    def test_detects_image_extensions(self):
        from llm.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(api_key="sk-test")
        assert provider._has_image_reference("cat.gif") is True
        assert provider._has_image_reference("document.svg") is True
        assert provider._has_image_reference("plain text") is False


class TestLLMManagerConstructor:

    def test_init_creates_providers(self):
        from llm.manager import LLMManager
        with patch("llm.manager.OllamaProvider") as mock_ollama_cls:
            with patch("llm.manager.OpenRouterProvider") as mock_or_cls:
                manager = LLMManager()
                assert isinstance(manager.ollama, MagicMock) or hasattr(manager, "ollama")
                mock_ollama_cls.assert_called_once()
                mock_or_cls.assert_called_once()


class TestLLMManagerCircuitBreaker:

    def test_is_available_caches_probe_within_ttl(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = False
        manager.ollama.is_alive.return_value = False
        assert manager.is_available() is False
        assert manager.is_available() is False
        manager.openrouter.is_alive.assert_called_once()
        manager.ollama.is_alive.assert_called_once()

    def test_generate_honors_failure_cooldown(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        manager.openrouter.is_alive.return_value = True
        manager.openrouter.generate.side_effect = RuntimeError("boom")
        manager.ollama.is_alive.return_value = True
        manager.ollama.generate.return_value = "ollama ok"
        assert manager.generate("sys", "usr") == "ollama ok"
        assert manager.generate("sys", "usr") == "ollama ok"
        # OpenRouter is tried exactly once, then held in cooldown
        manager.openrouter.generate.assert_called_once()


class TestOllamaThinkParam:

    def test_chat_payload_disables_thinking(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="qwen3:4b")
        payload = provider._chat_payload([{"role": "user", "content": "hi"}])
        assert payload["think"] is False

    def test_stream_payload_disables_thinking(self):
        from llm.providers.ollama import OllamaProvider
        provider = OllamaProvider(model="qwen3:4b")
        payload = provider._chat_payload(
            [{"role": "user", "content": "hi"}], stream=True
        )
        assert payload["think"] is False
        assert payload["stream"] is True


class TestLLMProviderPreference:

    def _make(self, provider):
        from llm.manager import LLMManager
        with patch("llm.manager.LLM_PROVIDER", provider):
            manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        return manager

    def test_default_is_openrouter(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        assert manager._prefer_ollama is False

    def test_unknown_value_defaults_to_openrouter(self):
        manager = self._make("banana")
        assert manager._prefer_ollama is False

    def test_value_is_normalized_case_insensitive(self):
        manager = self._make("  OLLAMA  ")
        assert manager._prefer_ollama is True

    def test_ollama_preferred_generate_uses_ollama_first(self):
        manager = self._make("ollama")
        manager.openrouter.is_alive.return_value = True
        manager.ollama.is_alive.return_value = True
        manager.ollama.generate.return_value = "local response"
        result = manager.generate("sys", "usr")
        assert result == "local response"
        manager.openrouter.generate.assert_not_called()

    def test_ollama_preferred_falls_back_when_ollama_down(self):
        manager = self._make("ollama")
        manager.openrouter.is_alive.return_value = True
        manager.ollama.is_alive.return_value = False
        manager.openrouter.generate.return_value = "cloud response"
        result = manager.generate("sys", "usr")
        assert result == "cloud response"
        manager.ollama.generate.assert_not_called()

    def test_ollama_preferred_falls_back_when_ollama_generate_fails(self):
        manager = self._make("ollama")
        manager.openrouter.is_alive.return_value = True
        manager.ollama.is_alive.return_value = True
        manager.ollama.generate.side_effect = RuntimeError("ollama fail")
        manager.openrouter.generate.return_value = "cloud response"
        result = manager.generate("sys", "usr")
        assert result == "cloud response"

    def test_probe_refreshes_ollama_when_preferred_even_if_openrouter_ok(self):
        manager = self._make("ollama")
        manager.openrouter.is_alive.return_value = True
        manager.ollama.is_alive.return_value = True
        manager._probe(force=True)
        assert manager._ollama_available is True

    def test_default_probe_skips_ollama_when_openrouter_ok(self):
        manager = self._make("openrouter")
        manager.openrouter.is_alive.return_value = True
        manager.ollama.is_alive.return_value = True
        manager._probe(force=True)
        assert manager._ollama_available is False

    def test_stream_prefers_ollama_when_configured(self):
        manager = self._make("ollama")
        manager.openrouter.is_alive.return_value = True
        manager.ollama.is_alive.return_value = True
        manager.ollama.stream.return_value = iter(["local chunk"])
        chunks = list(manager.stream("sys", "usr"))
        assert chunks == ["local chunk"]
        manager.openrouter.stream.assert_not_called()

    def test_stream_falls_back_to_openrouter_when_ollama_stream_fails(self):
        manager = self._make("ollama")
        manager.openrouter.is_alive.return_value = True
        manager.ollama.is_alive.return_value = True
        manager.ollama.stream.side_effect = RuntimeError("stream fail")
        manager.openrouter.stream.return_value = iter(["cloud chunk"])
        chunks = list(manager.stream("sys", "usr"))
        assert chunks == ["cloud chunk"]


class TestStreamFallbackHistory:
    """Streaming fallbacks must carry conversation history through to the
    non-streamed generate() they degrade to (bug-audit Oct 19, 2026)."""

    def _manager(self):
        from llm.manager import LLMManager
        manager = LLMManager()
        manager.openrouter = MagicMock()
        manager.ollama = MagicMock()
        # Keep the probe from re-deriving availability from the mocks.
        manager._probe = MagicMock()
        return manager

    HISTORY = [{"role": "user", "content": "previous turn"}]

    def test_no_priority_generate_passes_history(self):
        manager = self._manager()
        manager._openrouter_available = False
        del manager.ollama.stream  # no candidate providers -> no-priority path
        manager.generate = MagicMock(return_value="no-prio")
        chunks = list(manager.stream("sys", "u", history=self.HISTORY))
        assert chunks == ["no-prio"]
        assert manager.generate.call_args.kwargs["history"] == self.HISTORY

    def test_all_streams_fail_generate_passes_history(self):
        manager = self._manager()
        manager._openrouter_available = True
        manager.openrouter.stream.side_effect = RuntimeError("dead")
        manager.ollama.stream.side_effect = RuntimeError("dead")
        manager.generate = MagicMock(return_value="final-fallback")
        chunks = list(manager.stream("sys", "u", history=self.HISTORY))
        assert chunks == ["final-fallback"]
        assert manager.generate.call_args.kwargs["history"] == self.HISTORY
