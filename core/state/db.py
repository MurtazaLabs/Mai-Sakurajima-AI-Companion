# core/state/db.py
import json
import logging
import sqlite3
import threading
from pathlib import Path

logger = logging.getLogger("Mai.EvidenceDB")

class EvidenceDB:
    def __init__(self, db_dir: Path):
        self.db_path = db_dir / "relationship_evidence.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None
        self._lock = threading.RLock()
        self._available = False
        self._memory_fallback = []  # In-memory fallback when DB unavailable
        
        try:
            self._init_db()
            self._available = True
        except Exception as e:
            logger.warning("[EvidenceDB] Database initialization failed, using in-memory fallback: %s", e)
            self._available = False

    def _get_conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self._conn

    def log_evidence(self, ev_id: str, ts: float, ev_type: str, desc: str, impacts: dict, weight: float):
        evidence_record = {
            "evidence_id": ev_id,
            "timestamp": ts,
            "event_type": ev_type,
            "description": desc,
            "dimension_impacts": impacts,
            "weight": weight
        }
        
        if self._available:
            try:
                with self._lock:
                    conn = self._get_conn()
                    conn.execute(
                        "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?)",
                        (ev_id, ts, ev_type, desc, json.dumps(impacts), weight)
                    )
                    conn.commit()
            except Exception as e:
                logger.warning("[EvidenceDB] Database write failed, falling back to memory: %s", e)
                self._available = False
                self._memory_fallback.append(evidence_record)
        else:
            self._memory_fallback.append(evidence_record)

    def get_all_evidence(self) -> list:
        if self._available:
            try:
                with self._lock:
                    conn = self._get_conn()
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM evidence ORDER BY timestamp ASC")
                    rows = cursor.fetchall()

                    evidence_list = []
                    for r in rows:
                        evidence_list.append({
                            "evidence_id": r[0],
                            "timestamp": r[1],
                            "event_type": r[2],
                            "description": r[3],
                            "dimension_impacts": json.loads(r[4]),
                            "weight": r[5]
                        })
                    # Combine with any memory fallback entries
                    evidence_list.extend(self._memory_fallback)
                    return evidence_list
            except Exception as e:
                logger.warning("[EvidenceDB] Database read failed, using memory fallback: %s", e)
                self._available = False
                return self._memory_fallback.copy()
        else:
            return self._memory_fallback.copy()

    def is_available(self) -> bool:
        return self._available

    def __del__(self):
        self.close()

    def close(self):
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,
                timestamp REAL,
                event_type TEXT,
                description TEXT,
                dimension_impacts TEXT,
                weight REAL
            )
        """)
        conn.commit()
