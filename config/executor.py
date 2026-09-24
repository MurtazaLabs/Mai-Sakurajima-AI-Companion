EXECUTOR_MODE = "safe"
EXECUTOR_TIMEOUT = 15
EXECUTOR_COMMAND_TIMEOUT = 15
EXECUTOR_MAX_OUTPUT = 4000
EXECUTOR_COOLDOWN = 1.5
EXECUTOR_MIN_CONFIDENCE = 0.8
EXECUTOR_ENABLE_QUEUE = True
EXECUTOR_QUEUE_TIMEOUT = 1
EXECUTOR_QUEUE_WORKER_TIMEOUT = 1
EXECUTOR_ASYNC_ENABLED = True
EXECUTOR_HISTORY_LIMIT = 1000
EXECUTOR_TYPING_INTERVAL = 0.02
EXECUTOR_TYPING_DELAY = 0.5
EXECUTOR_ALLOWED_ACTIONS = [
    "open_app", "open_url", "type_text", "run_command", "search", "speak"
]
EXECUTOR_BLOCKED_COMMANDS = [
    "rm -rf", "shutdown", "reboot", "format", "mkfs",
    "del /f", "taskkill /f", ":(){:|:&};:", "reg delete", "diskpart"
]
SEARCH_ENGINE_URL = "https://www.google.com/search?q="
DEFAULT_YOUTUBE_URL = "https://youtube.com"
DEFAULT_GOOGLE_URL = "https://google.com"
DEFAULT_CODE_EDITOR = "code"
