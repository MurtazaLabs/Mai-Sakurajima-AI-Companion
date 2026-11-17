import os

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
# Default to a free-model router to avoid 402 Payment Required errors.
# `or` is load-bearing: a bare os.environ.get() with no default returned
# None when the env var was unset, so every request went out as
# model:"None" -> 400 x3 retries -> failover (8-14s per call, Oct 9 log).
OPENROUTER_DEFAULT_MODEL = os.environ.get("OPENROUTER_DEFAULT_MODEL") or "openrouter/free"
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:3b-instruct-q4_k_m")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
LLM_TOP_P = float(os.environ.get("LLM_TOP_P", "0.85"))
LLM_STREAM = os.environ.get("LLM_STREAM", "True").lower() == "true"
LLM_MAX_CONTEXT = int(os.environ.get("LLM_MAX_CONTEXT", "4096"))
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "120"))
LLM_RETRY_COUNT = int(os.environ.get("LLM_RETRY_COUNT", "3"))
LLM_STOP_TOKENS = os.environ.get("LLM_STOP_TOKENS", "").split(",") if os.environ.get("LLM_STOP_TOKENS") else []
# Provider preference for LLMManager: "openrouter" (default — cloud first,
# Ollama failover), "ollama" (local first, OpenRouter fallback) or "llamacpp"
# (llama.cpp llama-server first, OpenRouter fallback). Switchable at runtime
# via LLMManager.select_provider() / POST /api/system/llm/provider.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openrouter")

# llama.cpp (llama-server) — OpenAI-compatible /v1. Mai owns this instance on
# its own port: 8080/8081 belong to another project on this machine.
# LLAMACPP_MODEL must match the server's --alias.
LLAMACPP_BASE_URL = os.environ.get("LLAMACPP_BASE_URL", "http://127.0.0.1:8082")
LLAMACPP_MODEL = os.environ.get("LLAMACPP_MODEL", "spark")
LLAMACPP_API_KEY = os.environ.get("LLAMACPP_API_KEY", "")