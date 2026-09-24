import os

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
# Default to a free model to avoid 402 Payment Required errors
# Only stealth/space-bunny-alpha is currently free on OpenRouter
OPENROUTER_DEFAULT_MODEL = os.environ.get("OPENROUTER_DEFAULT_MODEL", "stealth/space-bunny-alpha")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:3b-instruct-q4_k_m")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
LLM_TOP_P = float(os.environ.get("LLM_TOP_P", "0.85"))
LLM_STREAM = os.environ.get("LLM_STREAM", "True").lower() == "true"
LLM_MAX_CONTEXT = int(os.environ.get("LLM_MAX_CONTEXT", "4096"))
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "120"))
LLM_RETRY_COUNT = int(os.environ.get("LLM_RETRY_COUNT", "3"))
LLM_STOP_TOKENS = os.environ.get("LLM_STOP_TOKENS", "").split(",") if os.environ.get("LLM_STOP_TOKENS") else []