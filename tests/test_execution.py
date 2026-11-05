import time
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
#  TaskExecutor tests
# ---------------------------------------------------------------------------

class TestTaskExecutorInit:

    def test_init_sets_defaults(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        assert executor.last_action is None
        assert executor.history == []
        assert executor.queue_running is True

    def test_blocked_commands_loaded(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        assert len(executor.blocked_commands) > 0

    def test_allowed_actions_loaded(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        assert "open_app" in executor.allowed_actions
        assert "run_command" in executor.allowed_actions


class TestTaskExecutorRun:

    def test_run_invalid_task_format(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor.run("not a dict")
        assert result["success"] is False
        assert result["output"] == "invalid_task_format"

    def test_run_missing_action_type(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor.run({"content": "hello"})
        assert result["success"] is False
        assert result["output"] == "missing_action_type"

    def test_run_unauthorized_action(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor.run({"type": "hack", "content": "system"})
        assert result["success"] is False
        assert "unauthorized_action" in result["output"]

    def test_run_unknown_action_type(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        # "speak" is in allowed_actions but has no handler -> hits unknown_task
        result = executor.run({"type": "speak", "content": "hello"})
        assert result["success"] is False
        assert "unknown_task" in result["output"]

    def test_run_adds_timestamp_and_duration(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch.object(executor, "open_app", return_value=executor._result(True, "ok", 0)):
            result = executor.run({"type": "open_app", "content": "calc"})
        assert "timestamp" in result
        assert result["duration"] >= 0
        assert result["success"] is True

    def test_run_stores_history(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch.object(executor, "open_app", return_value=executor._result(True, "ok", 0)):
            executor.run({"type": "open_app", "content": "calc", "id": "1"})
        assert len(executor.history) == 1
        assert executor.history[0]["task_id"] == "1"

    def test_run_history_respects_limit(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        executor.history_limit = 3
        with patch.object(executor, "open_app", return_value=executor._result(True, "ok", 0)):
            for i in range(5):
                executor.run({"type": "open_app", "content": f"app{i}", "id": str(i)})
        assert len(executor.history) == 3

    def test_run_catches_action_exception(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch.object(executor, "open_app", side_effect=RuntimeError("boom")):
            result = executor.run({"type": "open_app", "content": "calc"})
        assert result["success"] is False
        assert "task_failed" in result["output"]


class TestTaskExecutorOpenApp:

    def test_open_app_no_app_name(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor.open_app("")
        assert result["success"] is False
        assert result["output"] == "no_app_specified"

    def test_open_app_on_windows(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.os.name", "nt"):
            with patch("execution.handlers.os.startfile", create=True) as mock_start:
                result = executor.open_app("notepad")
        assert result["success"] is True
        assert "opened:notepad" in result["output"]
        mock_start.assert_called_once_with("notepad")

    def test_open_app_on_posix(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.os.name", "posix"):
            with patch("execution.handlers.subprocess.Popen") as mock_popen:
                mock_proc = MagicMock()
                mock_popen.return_value = mock_proc
                result = executor.open_app("gedit")
        assert result["success"] is True
        mock_popen.assert_called_once_with(["gedit"])

    def test_open_app_exception_returns_error(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor(allowed_apps=["nonexistent", "notepad"])
        with patch("execution.handlers.os.name", "nt"):
            with patch("execution.handlers.os.startfile", create=True, side_effect=FileNotFoundError("not found")):
                result = executor.open_app("nonexistent")
        assert result["success"] is False

    def test_open_app_resolves_known_path_on_windows(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor(allowed_apps=["chrome", "notepad"])
        with patch("execution.handlers.os.name", "nt"):
            with patch("execution.handlers.os.startfile", create=True, side_effect=[FileNotFoundError("no bare name"), None]) as mock_start:
                with patch("execution.handlers.os.path.isfile", return_value=True):
                    result = executor.open_app("chrome")
        assert result["success"] is True
        assert mock_start.call_count == 2
        final_call = mock_start.call_args[0][0]
        assert final_call.lower().endswith("chrome.exe")

    def test_open_app_unresolvable_reports_not_found(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor(allowed_apps=["chrome", "notepad"])
        with patch("execution.handlers.os.name", "nt"):
            with patch("execution.handlers.os.startfile", create=True, side_effect=FileNotFoundError("no browser")):
                with patch("execution.handlers.os.path.isfile", return_value=False):
                    result = executor.open_app("chrome")
        assert result["success"] is False
        assert "app_not_found" in result["output"]

    def test_open_app_bare_name_windows_single_call(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.os.name", "nt"):
            with patch("execution.handlers.os.startfile", create=True) as mock_start:
                result = executor.open_app("notepad")
        assert result["success"] is True
        mock_start.assert_called_once_with("notepad")


class TestTaskExecutorOpenUrl:

    def test_open_url_no_url(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor.open_url("")
        assert result["success"] is False
        assert result["output"] == "no_url_provided"

    def test_open_url_adds_https(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.webbrowser.open") as mock_web:
            result = executor.open_url("google.com")
        assert result["success"] is True
        mock_web.assert_called_once_with("https://google.com")

    def test_open_url_preserves_https(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.webbrowser.open") as mock_web:
            result = executor.open_url("https://example.com")
        assert result["success"] is True
        mock_web.assert_called_once_with("https://example.com")

    def test_open_url_exception(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.webbrowser.open", side_effect=RuntimeError("browser fail")):
            result = executor.open_url("https://example.com")
        assert result["success"] is False


class TestTaskExecutorSearch:

    def test_search_no_query(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor.search("")
        assert result["success"] is False
        assert result["output"] == "no_search_query"

    def test_search_opens_search_url(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.urllib.parse.quote", return_value="hello+world"):
            with patch("execution.handlers.webbrowser.open") as mock_web:
                result = executor.search("hello world")
        assert result["success"] is True
        assert "hello world" in result["output"]
        mock_web.assert_called_once()

    def test_search_exception(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.webbrowser.open", side_effect=RuntimeError("fail")):
            result = executor.search("query")
        assert result["success"] is False


class TestTaskExecutorRunCommand:

    def test_run_command_no_command(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor.run_command("")
        assert result["success"] is False
        assert result["output"] == "no_command_provided"

    def test_run_command_blocked(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor.run_command("rm -rf /")
        assert result["success"] is False
        assert result["output"] == "blocked_dangerous_command"

    def test_run_command_success(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "done"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            result = executor.run_command("echo hello")
        assert result["success"] is True
        assert result["output"] == "done"

    def test_run_command_failure(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "error occurred"
            mock_run.return_value = mock_result
            result = executor.run_command("bad command")
        assert result["success"] is False
        assert "error occurred" in result["output"]

    def test_run_command_timeout(self):
        import subprocess

        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
            result = executor.run_command("sleep 100")
        assert result["success"] is False
        assert result["output"] == "command_timeout"

    def test_run_command_exception(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.subprocess.run", side_effect=FileNotFoundError("no file")):
            result = executor.run_command("nonexistent")
        assert result["success"] is False

    def test_run_command_truncates_output(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        executor.max_output = 10
        with patch("execution.handlers.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "a" * 100
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            result = executor.run_command("echo long")
        assert len(result["output"]) <= 10


class TestTaskExecutorRunAsyncCommand:

    def test_run_async_no_command(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor.run_async_command("")
        assert result["success"] is False
        assert result["output"] == "no_command_provided"

    def test_run_async_starts_thread(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.threading.Thread") as mock_thread:
            result = executor.run_async_command("notepad")
        assert result["success"] is True
        assert "async_started" in result["output"]
        mock_thread.assert_called_once()


class TestTaskExecutorTypeText:

    def test_type_text_no_text(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor.type_text("")
        assert result["success"] is False
        assert result["output"] == "no_text_provided"

    def test_type_text_no_pyautogui(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch("execution.handlers.pyautogui", None):
            result = executor.type_text("hello")
        assert result["success"] is False
        assert result["output"] == "pyautogui_not_available"

    def test_type_text_success(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        mock_pyautogui = MagicMock()
        with patch("execution.handlers.pyautogui", mock_pyautogui):
            result = executor.type_text("hello world")
        assert result["success"] is True
        assert result["output"] == "typed_successfully"
        mock_pyautogui.write.assert_called_once_with("hello world", interval=executor.typing_interval)

    def test_type_text_exception(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        mock_pyautogui = MagicMock()
        mock_pyautogui.write.side_effect = RuntimeError("type fail")
        with patch("execution.handlers.pyautogui", mock_pyautogui):
            result = executor.type_text("hello")
        assert result["success"] is False


class TestTaskExecutorQuickAction:

    def test_quick_action_none_text(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        assert executor.quick_action("") is None
        assert executor.quick_action(None) is None

    def test_quick_action_open_youtube(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch.object(executor, "open_url") as mock_open:
            executor.quick_action("open youtube")
        mock_open.assert_called_once()

    def test_quick_action_open_google(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch.object(executor, "open_url") as mock_open:
            executor.quick_action("open google")
        mock_open.assert_called_once()

    def test_quick_action_open_code(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch.object(executor, "open_app") as mock_open:
            executor.quick_action("open code")
        mock_open.assert_called_once()

    def test_quick_action_search(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch.object(executor, "search") as mock_search:
            executor.quick_action("search python tutorial")
        mock_search.assert_called_once_with("python tutorial")

    def test_quick_action_type(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch.object(executor, "type_text") as mock_type:
            executor.quick_action("type hello world")
        mock_type.assert_called_once_with("hello world")

    def test_quick_action_no_match(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor.quick_action("do something random")
        assert result is None


class TestTaskExecutorQueue:

    def test_queue_task_invalid(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor.queue_task("not dict")
        assert result["success"] is False
        assert result["output"] == "invalid_queue_task"

    def test_queue_task_valid(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor.queue_task({"type": "open_app", "content": "calc"})
        assert result["success"] is True
        assert result["output"] == "task_queued"
        assert executor.task_queue.qsize() == 1

    def test_stop_queue(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        executor.stop_queue()
        assert executor.queue_running is False


class TestTaskExecutorResult:

    def test_result_structure(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor._result(True, "ok", 1.5)
        assert result == {"success": True, "output": "ok", "duration": 1.5}

    def test_result_boolean_coercion(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        result = executor._result(1, "ok", 0)
        assert result["success"] is True


class TestTaskExecutorStats:

    def test_stats_returns_counts(self):
        from execution.task_executor import TaskExecutor
        executor = TaskExecutor()
        with patch.object(executor, "open_app", return_value=executor._result(True, "ok", 0)):
            executor.run({"type": "open_app", "content": "a"})
            executor.run({"type": "open_app", "content": "b"})
        with patch.object(executor, "open_app", return_value=executor._result(False, "fail", 0)):
            executor.run({"type": "open_app", "content": "c"})
        stats = executor.stats()
        assert stats["total"] == 3
        assert stats["success"] == 2
        assert stats["failed"] == 1


# ---------------------------------------------------------------------------
#  SafeExecutor tests
# ---------------------------------------------------------------------------

class TestSafeExecutorInit:

    def test_init_creates_with_executor(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor, mode="safe")
        assert se.executor is executor
        assert se.mode == "safe"
        assert se.cooldown >= 0

    def test_permissions_by_mode(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor)
        assert "run_command" in se.permissions["admin"]
        assert "run_command" not in se.permissions["safe"]
        assert "type_text" in se.permissions["advanced"]
        assert "type_text" not in se.permissions["safe"]


class TestSafeExecutorRun:

    def test_run_invalid_action(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor)
        assert se.run(None) == "[Invalid action]"
        assert se.run({}) == "[Invalid action]"

    def test_run_speak_passthrough(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor)
        result = se.run({"type": "speak", "content": "hello"})
        assert result == "hello"

    def test_run_cooldown_active(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor)
        se.last_action_time = time.time()
        se.cooldown = 10
        result = se.run({"type": "open_app", "content": "calc"})
        assert "cooldown" in result

    def test_run_blocked_permission(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor, mode="safe")
        result = se.run({"type": "run_command", "command": "echo hi"})
        assert "Blocked" in result
        assert "not allowed" in result

    def test_run_low_confidence_cancelled(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor, mode="admin")
        se.min_confidence = 0.8
        result = se.run({"type": "open_app", "content": "calc", "confidence": 0.3})
        assert "Cancelled" in result

    def test_run_validation_fails_url(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor, mode="safe")
        result = se.run({"type": "open_url", "url": "ftp://bad.com"})
        assert "Blocked" in result

    def test_run_validation_fails_blocked_command(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor, mode="admin")
        result = se.run({"type": "run_command", "command": "rm -rf /"})
        assert "Blocked" in result

    def test_run_success_delegates_to_executor(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        executor.run.return_value = {"success": True, "output": "ok"}
        se = SafeExecutor(executor, mode="safe")
        se.last_action_time = 0
        result = se.run({"type": "open_app", "content": "calc"})
        assert result["success"] is True
        executor.run.assert_called_once_with({"type": "open_app", "content": "calc"})

    def test_run_executor_exception_returns_error(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        executor.run.side_effect = RuntimeError("executor fail")
        se = SafeExecutor(executor, mode="admin")
        se.last_action_time = 0
        result = se.run({"type": "open_app", "content": "calc"})
        assert "Execution error" in result

    def test_run_admin_command_confirmation_declined(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor, mode="admin")
        se.last_action_time = 0
        result = se.run({"type": "run_command", "command": "echo safe"})
        # In headless mode, confirmation is auto-declined
        assert "cancelled" in result


class TestSafeExecutorConfirm:
    """The hardcoded always-False _confirm() stub became an injectable gate
    (default fail-closed); interactive surfaces supply their own confirm_fn."""

    def _willing_executor(self):
        executor = MagicMock()
        executor.run.return_value = {"success": True, "output": "ok"}
        return executor

    def test_run_admin_command_confirmation_declined(self):
        from execution.safe_executor import SafeExecutor
        se = SafeExecutor(self._willing_executor(), mode="admin")
        se.last_action_time = 0
        result = se.run({"type": "run_command", "command": "echo safe"})
        assert "cancelled" in result

    def test_confirm_fn_allows_execution(self):
        from execution.safe_executor import SafeExecutor
        executor = self._willing_executor()
        confirm_calls = []

        def confirm(action):
            confirm_calls.append(action)
            return True

        se = SafeExecutor(executor, mode="admin", confirm_fn=confirm)
        se.last_action_time = 0
        result = se.run({"type": "run_command", "command": "echo safe"})
        assert result == {"success": True, "output": "ok"}
        assert len(confirm_calls) == 1

    def test_confirm_fn_decline_blocks(self):
        from execution.safe_executor import SafeExecutor
        executor = self._willing_executor()
        se = SafeExecutor(executor, mode="admin", confirm_fn=lambda a: False)
        se.last_action_time = 0
        result = se.run({"type": "run_command", "command": "echo safe"})
        assert "cancelled" in result
        executor.run.assert_not_called()

    def test_confirm_fn_exception_fails_closed(self):
        from execution.safe_executor import SafeExecutor
        executor = self._willing_executor()

        def confirm(action):
            raise RuntimeError("UI exploded")

        se = SafeExecutor(executor, mode="admin", confirm_fn=confirm)
        se.last_action_time = 0
        result = se.run({"type": "run_command", "command": "echo safe"})
        assert "cancelled" in result
        executor.run.assert_not_called()


class TestSafeExecutorValidate:

    def test_validate_valid_url(self):
        from execution.safe_executor import SafeExecutor
        se = SafeExecutor.__new__(SafeExecutor)
        valid, reason = se._validate({"type": "open_url", "url": "https://example.com"})
        assert valid is True

    def test_validate_valid_url_from_content(self):
        from execution.safe_executor import SafeExecutor
        se = SafeExecutor.__new__(SafeExecutor)
        valid, reason = se._validate({"type": "open_url", "content": "https://example.com"})
        assert valid is True

    def test_validate_blocked_command_from_content(self):
        from execution.safe_executor import SafeExecutor
        se = SafeExecutor.__new__(SafeExecutor)
        se.blocked_commands = ["rm -rf", "shutdown"]
        valid, reason = se._validate({"type": "run_command", "content": "shutdown now"})
        assert valid is False
        assert "dangerous_command" in reason

    def test_validate_invalid_url(self):
        from execution.safe_executor import SafeExecutor
        se = SafeExecutor.__new__(SafeExecutor)
        valid, reason = se._validate({"type": "open_url", "url": "javascript:alert(1)"})
        assert valid is False
        assert reason == "invalid_url"

    def test_validate_safe_command(self):
        from execution.safe_executor import SafeExecutor
        se = SafeExecutor.__new__(SafeExecutor)
        se.blocked_commands = ["rm -rf", "shutdown"]
        valid, reason = se._validate({"type": "run_command", "command": "echo hello"})
        assert valid is True

    def test_validate_blocked_command(self):
        from execution.safe_executor import SafeExecutor
        se = SafeExecutor.__new__(SafeExecutor)
        se.blocked_commands = ["rm -rf", "shutdown"]
        valid, reason = se._validate({"type": "run_command", "command": "shutdown now"})
        assert valid is False
        assert "dangerous_command" in reason

    def test_validate_other_action_types_pass(self):
        from execution.safe_executor import SafeExecutor
        se = SafeExecutor.__new__(SafeExecutor)
        valid, reason = se._validate({"type": "search", "query": "python"})
        assert valid is True


class TestSafeExecutorCooldown:

    def test_cooldown_ready_when_elapsed_passed(self):
        from execution.safe_executor import SafeExecutor
        se = SafeExecutor.__new__(SafeExecutor)
        se.cooldown = 1.0
        se.last_action_time = 0
        assert se._cooldown_ready() is True

    def test_cooldown_not_ready(self):
        from execution.safe_executor import SafeExecutor
        se = SafeExecutor.__new__(SafeExecutor)
        se.cooldown = 10
        se.last_action_time = time.time()
        assert se._cooldown_ready() is False


class TestSafeExecutorSetMode:

    def test_set_mode_valid(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor)
        result = se.set_mode("advanced")
        assert se.mode == "advanced"
        assert "Mode switched" in result

    def test_set_mode_invalid(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor)
        result = se.set_mode("god")
        assert result == "[Invalid mode]"
        assert se.mode != "god"


class TestSafeExecutorStats:

    def test_stats_returns_counts(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor, mode="admin")
        se._log({"type": "test"}, "success")
        se._log({"type": "test"}, "blocked_permission")
        se._log({"type": "test"}, "error:fail")
        stats = se.stats()
        assert stats["total"] == 3
        assert stats["success"] == 1
        assert stats["blocked"] == 1
        assert stats["errors"] == 1
        assert stats["mode"] == "admin"


class TestSafeExecutorLog:

    def test_log_appends_to_history(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor, mode="safe")
        se._log({"type": "test"}, "success")
        assert len(se.history) == 1
        assert se.history[0]["status"] == "success"
        assert se.history[0]["mode"] == "safe"

    def test_log_caps_at_1000(self):
        from execution.safe_executor import SafeExecutor
        executor = MagicMock()
        se = SafeExecutor(executor)
        for i in range(1005):
            se._log({"type": "t"}, str(i))
        assert len(se.history) <= 1000
        assert se.history[-1]["status"] == "1004"


class TestFileSystemSandbox:

    def test_sandbox_active_by_default(self):
        from execution.handlers import _CLIPBOARD_SANDBOX_DIRS, _path_allowed
        assert _CLIPBOARD_SANDBOX_DIRS, "sandbox must be configured by default"
        assert _path_allowed(".") is True
        assert _path_allowed(str(_CLIPBOARD_SANDBOX_DIRS[0])) is True

    def test_path_outside_sandbox_blocked(self):
        from execution.handlers import _path_allowed
        foreign = r"C:\Windows\System32\evil.exe"
        assert _path_allowed(foreign) is False

    def test_configure_sandbox_restricts(self):
        from execution.handlers import _CLIPBOARD_SANDBOX_DIRS, _configure_sandbox, _path_allowed
        defaults = list(_CLIPBOARD_SANDBOX_DIRS)
        _configure_sandbox(r"C:\only\here")
        try:
            assert _path_allowed(r"C:\only\here\a.txt") is True
            assert _path_allowed(r"C:\somewhere\else\a.txt") is False
        finally:
            _configure_sandbox(*defaults)
            assert _path_allowed(r"C:\Windows\evil.exe") is False


def test_task_executor_result_delegates_to_shared_helper():
    """_result keeps the method shape for callers but one shared helper lives
    in execution.handlers (audit Oct 25 2026, finding 6)."""
    from execution.task_executor import TaskExecutor

    out = TaskExecutor._result(object(), True, "ok", 1.5)
    assert out == {"success": True, "output": "ok", "duration": 1.5}
    assert isinstance(out["duration"], float)
