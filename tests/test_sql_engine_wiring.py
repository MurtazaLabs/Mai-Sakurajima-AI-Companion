"""Phase 2c — alembic.ini + SQL engine wiring (app.database).

Verifies:
- alembic.ini exists and points at a complete migration environment
  (env.py, script.py.mako, versions/001_initial.py).
- ``alembic upgrade head`` creates the full initial schema; ``downgrade base``
  removes it.
- The infrastructure builder produces a working SQLAlchemy engine
  (POSTGRES_DSN -> DATABASE_URL -> sqlite:///{MEMORY_DIR}/mai.db).
- ``MAI_DB_AUTO_MIGRATE`` is strictly opt-in (default off) and, when enabled,
  actually migrates the configured database.
"""
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine

from app.builders import infrastructure

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_TABLES = {
    "alembic_version",
    "profiles",
    "sessions",
    "memory_nodes",
    "relationship_evidence",
    "shared_state",
    "evidence",
}


@pytest.fixture(autouse=True)
def _reset_db_singleton():
    """The engine is a process-wide singleton — reset around every test."""
    from core.state import database as db

    db.close_db()
    yield
    db.close_db()


@pytest.fixture
def sqlite_url(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'mai_test.db'}"
    monkeypatch.setattr("app.config_loader.DATABASE_URL", url)
    monkeypatch.setattr("app.config_loader.POSTGRES_DSN", "")
    return url


def _alembic_config() -> Config:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option(
        "script_location",
        str(PROJECT_ROOT / "core" / "state" / "alembic").replace("\\", "/"),
    )
    return cfg


def _tables(db_path: Path) -> set:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    finally:
        conn.close()
    return {row[0] for row in rows}


# ── Migration environment ─────────────────────────────────────────


def test_alembic_ini_present_and_script_location_valid():
    assert (PROJECT_ROOT / "alembic.ini").exists()
    script_dir = PROJECT_ROOT / "core" / "state" / "alembic"
    assert (script_dir / "env.py").exists()
    assert (script_dir / "script.py.mako").exists()
    assert (script_dir / "versions" / "001_initial.py").exists()


def test_upgrade_head_creates_full_schema(tmp_path, sqlite_url):
    command.upgrade(_alembic_config(), "head")
    assert EXPECTED_TABLES <= _tables(tmp_path / "mai_test.db")


def test_downgrade_base_removes_schema(tmp_path, sqlite_url):
    cfg = _alembic_config()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    assert _tables(tmp_path / "mai_test.db") <= {"alembic_version"}


# ── Builder wiring ────────────────────────────────────────────────


def test_builder_builds_working_sqlite_engine(sqlite_url):
    engine, url = infrastructure._build_database()
    assert url == sqlite_url
    assert isinstance(engine, Engine)
    with engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT 1").scalar() == 1


def test_builder_masks_credentials_in_urls(monkeypatch):
    monkeypatch.setattr(
        "app.config_loader.DATABASE_URL",
        "postgresql://user:secret@db.internal:5432/mai",
    )
    monkeypatch.setattr("app.config_loader.POSTGRES_DSN", "")
    masked = infrastructure._mask_url("postgresql://user:secret@db.internal:5432/mai")
    assert "secret" not in masked
    assert masked == "postgresql://***@db.internal:5432/mai"


# ── Auto-migrate gate ─────────────────────────────────────────────


def test_auto_migrate_default_off(sqlite_url, monkeypatch):
    monkeypatch.delenv("MAI_DB_AUTO_MIGRATE", raising=False)
    assert infrastructure._maybe_run_migrations() is False


def test_auto_migrate_opt_in_creates_schema(tmp_path, sqlite_url, monkeypatch):
    monkeypatch.setenv("MAI_DB_AUTO_MIGRATE", "true")
    assert infrastructure._maybe_run_migrations() is True
    assert EXPECTED_TABLES <= _tables(tmp_path / "mai_test.db")
