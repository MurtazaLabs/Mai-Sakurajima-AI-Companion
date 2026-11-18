"""Phase 1 — sandboxed file tools, executor policy, approval tier."""
import pytest

from execution import handlers
from execution.file_tools import FileTools


@pytest.fixture()
def tools(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    return FileTools(tmp_path / "workspace", extra_read_roots=[vault]), vault


def test_workspace_write_read_roundtrip(tools):
    file_tools, _vault = tools
    written = file_tools.write("notes/a.txt", "hello")
    assert written["ok"] is True
    read = file_tools.read("notes/a.txt")
    assert read["ok"] is True and read["text"] == "hello"


def test_traversal_is_refused(tools):
    file_tools, _vault = tools
    assert file_tools.write("../escape.txt", "x")["ok"] is False
    assert file_tools.read("../../etc/passwd")["ok"] is False


def test_absolute_outside_sandbox_is_refused(tools, tmp_path):
    file_tools, _vault = tools
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    result = file_tools.read(str(outside))
    assert result["ok"] is False
    assert "sandbox" in result["error"]


def test_vault_read_is_allowed_but_write_is_not(tools):
    file_tools, vault = tools
    target = vault / "research" / "note.md"
    target.parent.mkdir()
    target.write_text("artifact", encoding="utf-8")
    assert file_tools.read(str(target))["ok"] is True
    assert file_tools.writable(str(target)) is False
    assert file_tools.write(str(target), "overwrite")["ok"] is False


def test_create_refuses_overwrite(tools):
    file_tools, _vault = tools
    assert file_tools.create("one.txt", "first")["ok"] is True
    result = file_tools.create("one.txt", "second")
    assert result["ok"] is False and result["error"] == "file_exists"
    assert file_tools.read("one.txt")["text"] == "first"


def test_size_caps(tools):
    file_tools, _vault = tools
    assert file_tools.write("big.txt", "x" * 20_001)["ok"] is False
    file_tools.write("long.txt", "y" * 100)
    read = file_tools.read("long.txt", max_chars=10)
    assert read["chars"] == 10 and read["truncated"] is True


def test_list_dir_entries(tools):
    file_tools, _vault = tools
    file_tools.write("a.txt", "a")
    file_tools.write("sub/b.txt", "b")
    listing = file_tools.list("")
    names = {entry["name"] for entry in listing["entries"]}
    assert {"a.txt", "sub"} <= names


class _Recorder:
    def __init__(self):
        self.tools = {}

    def register(self, name, description, handler, parameters=None, category="general"):
        self.tools[name] = handler


class _ApprovalPartner:
    def __init__(self):
        self.requests = []

    def request_file(self, path, content, reason=""):
        self.requests.append((path, content))
        return {"status": "pending_approval", "id": "act_1"}


def test_tool_surface_executes_inside_and_requests_approval_outside(tmp_path):
    from agency.tools import register_file_tools

    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    outside.mkdir()
    file_tools = FileTools(workspace)
    partner = _ApprovalPartner()
    registry = _Recorder()
    assert register_file_tools(registry, file_tools, partner) == 4

    result = registry.tools["write_file"](path=str(outside / "x.txt"), content="hi")
    assert result["status"] == "needs_approval"
    assert partner.requests and not (outside / "x.txt").exists()

    inside = registry.tools["write_file"](path="draft.txt", content="hi")
    assert inside["ok"] is True
    assert registry.tools["read_file"](path="draft.txt")["text"] == "hi"
    assert registry.tools["list_dir"]()["ok"] is True


def test_safe_executor_modes_gate_file_actions():
    from execution.safe_executor import SafeExecutor

    class _Executor:
        def run(self, action):
            return {"success": True, "output": action["type"], "duration": 0.0}

    safe = SafeExecutor(_Executor(), mode="safe")
    safe.cooldown = 0
    blocked = safe.run({"type": "write_file", "path": "x.txt", "content": "x"})
    assert isinstance(blocked, str) and "not allowed" in blocked
    read_ok = safe.run({"type": "read_file", "path": "x.txt"})
    assert read_ok["success"] is True

    advanced = SafeExecutor(_Executor(), mode="advanced")
    advanced.cooldown = 0
    write_ok = advanced.run({"type": "write_file", "path": "x.txt", "content": "x"})
    assert write_ok["success"] is True
    assert advanced.run({"type": "write_file", "path": "", "content": "x"}).startswith("[Blocked")


def test_task_executor_dispatches_file_actions(tmp_path, monkeypatch):
    from execution.task_executor import TaskExecutor

    original = list(handlers._CLIPBOARD_SANDBOX_DIRS)
    handlers._configure_sandbox(str(tmp_path))
    executor = TaskExecutor()
    try:
        created = executor.run({"type": "create_file", "path": str(tmp_path / "x.txt"), "content": "data"})
        assert created["success"] is True
        again = executor.run({"type": "create_file", "path": str(tmp_path / "x.txt"), "content": "data"})
        assert again["success"] is False and again["output"] == "file_exists"
        read = executor.run({"type": "read_file", "path": str(tmp_path / "x.txt")})
        assert read["success"] is True and read["output"] == "data"
        listing = executor.run({"type": "list_dir", "path": str(tmp_path)})
        assert listing["success"] is True
    finally:
        handlers._configure_sandbox(*original)
