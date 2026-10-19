"""Plugin sandbox hardening (bug-audit sprint Oct 19 2026).

Verifies:
- Path containment uses structural relative_to checks: parent traversal,
  sibling prefix directories (e.g. <root>_backup/), and absolute escapes are
  all rejected; legitimate in-root paths still resolve.
- eval_code is disabled by default (MAI_PLUGIN_ALLOW_EVAL opt-in), needs the
  EXEC_EVAL permission, and its restricted globals neither expose os/pathlib
  nor keep the getattr/setattr/type escape hatches.
"""
import pytest

from plugins.sandbox import Permission, PluginSandbox


def _sandbox(tmp_path, perms=None):
    return PluginSandbox(
        plugin_name="test",
        permissions=perms or {Permission.FS_READ, Permission.FS_WRITE},
        fs_root=tmp_path / "root",
    )


class TestPathContainment:

    def test_legitimate_path_resolves(self, tmp_path):
        sb = _sandbox(tmp_path)
        resolved = sb.resolve_path("sub/file.txt")
        assert resolved == (sb.fs_root / "sub" / "file.txt").resolve()

    def test_parent_traversal_rejected(self, tmp_path):
        sb = _sandbox(tmp_path)
        with pytest.raises(PermissionError):
            sb.resolve_path("../escape")

    def test_sibling_prefix_directory_rejected(self, tmp_path):
        sibling = tmp_path / "root_backup"
        sibling.mkdir(parents=True, exist_ok=True)
        (sibling / "secret.txt").write_text("stage payload", encoding="utf-8")
        sb = _sandbox(tmp_path)
        with pytest.raises(PermissionError):
            sb.resolve_path("../root_backup/secret.txt")

    def test_absolute_escape_rejected(self, tmp_path):
        sb = _sandbox(tmp_path)
        esc = tmp_path / "outside.txt"
        esc.write_text("x", encoding="utf-8")
        with pytest.raises(PermissionError):
            sb.resolve_path(str(esc))

    def test_symlink_escape_rejected(self, tmp_path):
        import os
        esc_dir = tmp_path / "elsewhere"
        esc_dir.mkdir(parents=True, exist_ok=True)
        (esc_dir / "secret.txt").write_text("payload", encoding="utf-8")
        sb = _sandbox(tmp_path)
        link = sb.fs_root / "outlink.txt"
        link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(esc_dir / "secret.txt"), str(link))
        with pytest.raises(PermissionError):
            sb.resolve_path("outlink.txt")


class TestEvalGate:

    def test_eval_requires_permission(self, tmp_path, monkeypatch):
        monkeypatch.delenv("MAI_PLUGIN_ALLOW_EVAL", raising=False)
        sb = _sandbox(tmp_path, perms=set())
        with pytest.raises(PermissionError):
            sb.eval_code("1 + 1")

    def test_eval_disabled_by_default(self, tmp_path, monkeypatch):
        monkeypatch.delenv("MAI_PLUGIN_ALLOW_EVAL", raising=False)
        sb = _sandbox(tmp_path, perms={Permission.EXEC_EVAL})
        with pytest.raises(PermissionError):
            sb.eval_code("1 + 1")

    def test_eval_opt_in_runs_trusted_code(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAI_PLUGIN_ALLOW_EVAL", "1")
        sb = _sandbox(tmp_path, perms={Permission.EXEC_EVAL})
        assert sb.eval_code("[x for x in range(3)]") is None

    def test_eval_os_import_blocked(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAI_PLUGIN_ALLOW_EVAL", "1")
        sb = _sandbox(tmp_path, perms={Permission.EXEC_EVAL})
        with pytest.raises(RuntimeError):
            sb.eval_code("import os")

    def test_eval_escape_hatches_absent(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAI_PLUGIN_ALLOW_EVAL", "1")
        sb = _sandbox(tmp_path, perms={Permission.EXEC_EVAL})
        for snippet in ("type(1)", "getattr", "setattr"):
            with pytest.raises(RuntimeError):
                sb.eval_code(snippet)
