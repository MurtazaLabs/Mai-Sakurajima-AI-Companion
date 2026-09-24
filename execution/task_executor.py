# Mai_ai/execution/task_executor.py
import time
import queue
import logging
import threading

logger = logging.getLogger(__name__)

from app.config_loader import Settings
from execution.handlers import SystemActions, CommandActions, DesktopActions


class TaskExecutor:

    def __init__(self, allowed_apps=None):

        # Handlers
        self._system = SystemActions(allowed_apps=allowed_apps)
        self._commands = CommandActions(
            blocked_commands=Settings.EXECUTOR_BLOCKED_COMMANDS,
            command_timeout=Settings.EXECUTOR_COMMAND_TIMEOUT,
            max_output=Settings.EXECUTOR_MAX_OUTPUT,
        )
        self._desktop = DesktopActions(
            typing_delay=Settings.EXECUTOR_TYPING_DELAY,
            typing_interval=Settings.EXECUTOR_TYPING_INTERVAL,
        )

        # ==================================================
        # 🧠 EXECUTION STATE
        # ==================================================

        self.last_action = None

        self.history = []

        # ==================================================
        # 🧠 THREAD SAFETY
        # ==================================================

        self.lock = threading.RLock()

        # ==================================================
        # 🧠 SECURITY
        # ==================================================

        self.allowed_actions = set(

            Settings.EXECUTOR_ALLOWED_ACTIONS
        )

        # ==================================================
        # 🧠 EXECUTION SETTINGS
        # ==================================================

        self.history_limit = (
            Settings.EXECUTOR_HISTORY_LIMIT
        )

        self.queue_timeout = (
            Settings.EXECUTOR_QUEUE_TIMEOUT
        )

        # ==================================================
        # 🧠 ACTION QUEUE
        # ==================================================

        self.task_queue = queue.Queue()

        self.queue_running = True

        self.worker_thread = threading.Thread(

            target=self._queue_loop,

            daemon=True,

            name="ExecutorQueueThread"
        )

        self.worker_thread.start()

    # ==================================================
    # 🧠 MAIN EXECUTION ENTRY
    # ==================================================

    def run(self, task):

        start = time.time()

        # ==================================================
        # ✅ TASK VALIDATION
        # ==================================================

        if not isinstance(task, dict):

            return self._result(
                success=False,
                output="invalid_task_format",
                duration=0
            )

        action_type = str(
            task.get("type", "")
        ).strip()

        content = task.get("content")

        task_id = task.get("id")

        if not action_type:

            return self._result(
                success=False,
                output="missing_action_type",
                duration=0
            )

        if action_type not in self.allowed_actions:

            return self._result(
                success=False,
                output=f"unauthorized_action:{action_type}",
                duration=0
            )

        # ==================================================
        # 🧠 ACTION ROUTING
        # ==================================================

        try:

            if action_type == "open_app":

                result = self.open_app(content)

            elif action_type == "open_url":

                result = self.open_url(content)

            elif action_type == "type_text":

                result = self.type_text(content)

            elif action_type == "run_command":

                result = self.run_command(content)

            elif action_type == "search":

                result = self.search(content)

            else:

                result = self._result(
                    success=False,
                    output=f"unknown_task:{action_type}",
                    duration=0
                )

        except Exception as e:

            result = self._result(
                success=False,
                output=f"task_failed:{str(e)}",
                duration=0
            )

        # ==================================================
        # 🧠 METADATA
        # ==================================================

        result["task_id"] = task_id

        result["timestamp"] = time.time()

        result["duration"] = round(
            time.time() - start,
            2
        )

        # ==================================================
        # 🧠 HISTORY STORAGE
        # ==================================================

        with self.lock:

            self.history.append(result)

            if (
                len(self.history)
                >
                self.history_limit
            ):

                self.history.pop(0)

        return result

    # ==================================================
    # 🖥️ SYSTEM ACTIONS (delegated)
    # ==================================================

    def open_app(self, app_name):
        result = self._system.open_app(app_name)
        self.last_action = self._system.last_action
        return result

    def open_url(self, url):
        result = self._system.open_url(url)
        self.last_action = self._system.last_action
        return result

    def search(self, query):
        result = self._system.search(query)
        self.last_action = self._system.last_action
        return result

    # ==================================================
    # 💻 COMMAND ACTIONS (delegated)
    # ==================================================

    def run_command(self, command, timeout=None):
        result = self._commands.run_command(command, timeout)
        self.last_action = self._commands.last_action
        return result

    def run_async_command(self, command):
        return self._commands.run_async_command(command)

    # ==================================================
    # ⌨️ DESKTOP ACTIONS (delegated)
    # ==================================================

    def type_text(self, text):
        result = self._desktop.type_text(text)
        self.last_action = self._desktop.last_action
        return result

    # ==================================================
    # 🧠 TASK QUEUE
    # ==================================================

    def queue_task(self, task):

        if not isinstance(task, dict):

            return self._result(
                success=False,
                output="invalid_queue_task",
                duration=0
            )

        self.task_queue.put(task)

        return self._result(
            success=True,
            output="task_queued",
            duration=0
        )

    # ==================================================
    # 🔄 QUEUE LOOP
    # ==================================================

    def _queue_loop(self):

        while self.queue_running:

            try:

                task = self.task_queue.get(

                    timeout=self.queue_timeout
                )

                try:

                    self.run(task)

                finally:

                    self.task_queue.task_done()

            except queue.Empty:

                continue

            except Exception as e:

                logger.error(
                    f"[QUEUE ERROR] {e}"
                )

    # ==================================================
    # 🛑 STOP QUEUE
    # ==================================================

    def stop_queue(self):

        self.queue_running = False

    # ==================================================
    # 🧠 BACKWARD-COMPATIBLE PROPERTIES
    # ==================================================

    @property
    def blocked_commands(self):
        return self._commands.blocked_commands

    @property
    def max_output(self):
        return self._commands.max_output

    @max_output.setter
    def max_output(self, value):
        self._commands.max_output = value

    @property
    def typing_interval(self):
        return self._desktop.typing_interval

    @property
    def running_processes(self):
        return self._commands.running_processes

    # ==================================================
    # 🧠 QUICK ACTIONS
    # ==================================================

    def quick_action(self, text):

        if not text:
            return None

        t = str(text).lower()

        if "open youtube" in t:

            return self.open_url(
                Settings.DEFAULT_YOUTUBE_URL
            )

        if "open google" in t:

            return self.open_url(
                Settings.DEFAULT_GOOGLE_URL
            )

        if "open code" in t:

            return self.open_app(
                Settings.DEFAULT_CODE_EDITOR
            )

        if t.startswith("search"):

            query = t[len("search"):].strip()

            return self.search(query)

        if t.startswith("type"):

            content = t[len("type"):].strip()

            return self.type_text(
                content
            )

        return None

    # ==================================================
    # 📦 RESULT OBJECT
    # ==================================================

    def _result(

        self,

        success,

        output,

        duration
    ):

        return {

            "success": bool(success),

            "output": str(output),

            "duration": float(duration)
        }

    # ==================================================
    # 📊 STATS
    # ==================================================

    def stats(self):

        with self.lock:

            total = len(self.history)

            success = len([

                h for h in self.history

                if h.get("success")
            ])

            failed = total - success

            return {

                "total": total,

                "success": success,

                "failed": failed,

                "queued_tasks":
                    self.task_queue.qsize(),

                "queue_running":
                    self.queue_running
            }
