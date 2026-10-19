# Mai_ai/observability/tracer.py
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


class CognitiveAuditor:
    """
    A high-fidelity auditing engine that records the internal reasoning steps,
    latent emotional shifts, tool execution paths, and latencies of the Brain.
    """

    _EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    _PHONE_RE = re.compile(r"(?<!\d)\+?[\d(][\d\s().-]{7,}\d(?!\d)")
    _IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
    _API_KEY_RE = re.compile(r"\b(sk|pk|key|token|api)[_-]?[\w-]{12,}\b", re.IGNORECASE)
    _UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")

    def __init__(self, log_dir="logs/cognitive_audit", redact_pii=True):
        self.log_dir = log_dir
        self.redact_pii = redact_pii
        self.lock = Lock()
        self._ensure_log_directory()
        self.active_audits = {}

    def _ensure_log_directory(self):
        """Creates the audit log directory if it doesn't exist."""
        try:
            os.makedirs(self.log_dir, exist_ok=True)
        except Exception as e:
            logger.exception("Cognitive auditor failed to create log directory: %s", e)

    def begin_cycle(self, user_input: str) -> str:
        """
        Initializes a new audit transaction trail for a single user turn.
        Returns a unique dynamic transaction ID (tx_id).
        """
        tx_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        with self.lock:
            self.active_audits[tx_id] = {
                "transaction_id": tx_id,
                "timestamp": timestamp,
                "metrics": {
                    "start_time": time.time(),
                    "end_time": None,
                    "total_latency_ms": 0.0
                },
                "inputs": {
                    "user_raw": user_input
                },
                "cognitive_steps": [],
                "metadata": {}
            }
        return tx_id

    def log_step(self, tx_id: str, stage_name: str, snapshot_data: dict):
        """
        Appends a discrete milestone to the tracking trail 
        (e.g., 'memory_recall', 'emotion_sync', 'system_prompt_compiled').
        """
        if not tx_id:
            return

        with self.lock:
            if tx_id not in self.active_audits:
                return
            
            step_entry = {
                "step": stage_name,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "elapsed_since_start_ms": (time.time() - self.active_audits[tx_id]["metrics"]["start_time"]) * 1000,
                "snapshot": snapshot_data
            }
            self.active_audits[tx_id]["cognitive_steps"].append(step_entry)

    def log_metadata(self, tx_id: str, key: str, value: Any):
        """Attaches extra state metadata safely to the cycle tracking trail."""
        if not tx_id:
            return

        with self.lock:
            if tx_id in self.active_audits:
                self.active_audits[tx_id]["metadata"][key] = value

    def complete_cycle(self, tx_id: str, final_output: str) -> dict:
        """
        Closes out the running transaction, computes latency, and flushes
        the structured evaluation file straight to the local storage disk.
        """
        if not tx_id:
            return {}

        with self.lock:
            audit_trail = self.active_audits.pop(tx_id, None)

        if not audit_trail:
            return {}

        # Finalize latency metrics
        end_time = time.time()
        audit_trail["metrics"]["end_time"] = end_time
        audit_trail["metrics"]["total_latency_ms"] = (end_time - audit_trail["metrics"]["start_time"]) * 1000
        audit_trail["outputs"] = {"mai_raw": final_output}

        # Flush output cleanly straight to JSON file
        self._flush_to_disk(audit_trail)
        return audit_trail

    def _redact_text(self, text: str) -> str:
        """Mask PII (emails, phones, IPs, API keys, UUIDs) in a string.

        Applied before anything touches disk so raw user/Mai input is never
        persisted in plaintext (S-3)."""
        if not text:
            return ""
        text = self._EMAIL_RE.sub("[REDACTED_EMAIL]", text)
        text = self._IP_RE.sub("[REDACTED_IP]", text)
        text = self._API_KEY_RE.sub("[REDACTED_KEY]", text)
        text = self._UUID_RE.sub("[REDACTED_UUID]", text)
        text = self._PHONE_RE.sub("[REDACTED_PHONE]", text)
        return text

    def _redact_trail(self, trail: dict) -> dict:
        """Return a copy of an audit trail with raw text fields redacted."""
        redacted = dict(trail)
        inputs = dict(redacted.get("inputs", {}))
        outputs = dict(redacted.get("outputs", {}))
        inputs = {k: self._redact_text(v) if isinstance(v, str) else v
                  for k, v in inputs.items()}
        outputs = {k: self._redact_text(v) if isinstance(v, str) else v
                   for k, v in outputs.items()}
        redacted["inputs"] = inputs
        redacted["outputs"] = outputs
        redacted["cognitive_steps"] = [
            dict(step,
                 snapshot=self._redact_snapshot(step.get("snapshot", {})))
            for step in redacted.get("cognitive_steps", [])
        ]
        return redacted

    def _redact_snapshot(self, snapshot) -> Any:
        if isinstance(snapshot, dict):
            return {k: self._redact_snapshot(v) for k, v in snapshot.items()}
        if isinstance(snapshot, list):
            return [self._redact_snapshot(v) for v in snapshot]
        if isinstance(snapshot, str):
            return self._redact_text(snapshot)
        return snapshot

    def _flush_to_disk(self, audit_trail: dict):
        """Writes the completed execution audit trail to an isolated JSON file."""
        try:
            # Format filename neatly: logs/cognitive_audit/2026-06-05_txUuid.json
            date_prefix = datetime.utcnow().strftime("%Y-%m-%d")
            safe_tid = re.sub(r'[^\w\-.]', '_', str(audit_trail['transaction_id']))
            filename = f"{date_prefix}_{safe_tid}.json"
            filepath = os.path.join(self.log_dir, filename)

            payload = self._redact_trail(audit_trail) if self.redact_pii else audit_trail
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.exception("Cognitive auditor flush error: %s", e)