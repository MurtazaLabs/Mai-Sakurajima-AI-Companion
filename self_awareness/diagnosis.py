# self_awareness/diagnosis.py
"""Proactive self-diagnosis — findings, proposals, no fixes.

The boundary from the roadmap is enforced structurally: this module has no
write path to source, no component restart and no patch application. A finding
carries evidence and a ``proposal`` string; ``auto_apply`` is always False.
The user decides what happens next.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

BOUNDARY = "read_and_diagnose_only"
SEVERITIES = ("info", "warn", "error")


class SelfDiagnosis:

    def __init__(self, index=None, feeds=None, store_path=None, error_threshold=3):
        self.index = index
        self.feeds = feeds
        self.error_threshold = max(1, int(error_threshold))
        self.path = Path(store_path) if store_path else None
        self._lock = threading.RLock()
        self._last: dict = {}

    # -- analysis ----------------------------------------------------

    def analyze(self) -> dict:
        findings = []
        for check in (self._health_findings, self._error_findings, self._index_findings):
            try:
                findings.extend(check())
            except Exception as exc:
                logger.warning("[SelfDiagnosis] %s failed: %s", check.__name__, exc)
        counts = {severity: 0 for severity in SEVERITIES}
        for finding in findings:
            counts[finding["severity"]] = counts.get(finding["severity"], 0) + 1
        report = {
            "ran_at": time.time(),
            "findings": findings,
            "counts": counts,
            "healthy": not (counts["warn"] or counts["error"]),
            "boundary": BOUNDARY,
        }
        with self._lock:
            self._last = report
        self._append(report)
        logger.info(
            "[SelfDiagnosis] %d finding(s): %d error, %d warn",
            len(findings), counts["error"], counts["warn"],
        )
        return report

    def _health_findings(self) -> list[dict]:
        if self.feeds is None:
            return []
        health = self.feeds.health()
        findings = []
        for component in health.get("unhealthy") or []:
            status = str(component.get("status") or "unknown")
            severity = "warn" if status == "warn" else "error"
            name = component.get("name", "?")
            findings.append(self._finding(
                f"health:{name}",
                "health",
                severity,
                f"{name} is {status}",
                (
                    f"{name} reported {component.get('error_count', 0)} error(s); "
                    f"last heartbeat {component.get('uptime', '?')}s ago"
                ),
                (
                    f"Check {name}'s logs and its dependency, then restart that "
                    "component yourself — nothing is restarted automatically."
                ),
            ))
        return findings

    def _error_findings(self) -> list[dict]:
        if self.feeds is None:
            return []
        errors = self.feeds.recent_errors()
        findings = []
        for group in errors.get("groups") or []:
            count = int(group.get("count") or 0)
            if count < self.error_threshold:
                continue
            signature = str(group.get("signature") or "")
            digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:10]
            findings.append(self._finding(
                f"errors:{digest}",
                "errors",
                "warn",
                f"{count}× {signature[:90]}",
                str(group.get("examples", [""])[0])[:300],
                (
                    "This signature repeats in the log. Read the surrounding "
                    "traceback with self_read_code on the module named there; "
                    "propose a patch and wait for approval."
                ),
            ))
        return findings

    def _index_findings(self) -> list[dict]:
        if self.index is None:
            return []
        stats = self.index.stats()
        findings = []
        for path, error in sorted((stats.get("parse_errors") or {}).items()):
            findings.append(self._finding(
                f"code:{path}",
                "code",
                "error",
                f"{path} does not parse",
                str(error),
                (
                    "Fix the syntax error (or let the owning change finish); the "
                    "next index refresh picks it up. No patch is applied."
                ),
            ))
        if not stats.get("modules"):
            findings.append(self._finding(
                "index:empty",
                "index",
                "warn",
                "The own-code index is empty",
                f"root {stats.get('root', '?')} produced no modules",
                "Run a self index refresh so she can read her own code again.",
            ))
        elif stats.get("stale"):
            findings.append(self._finding(
                "index:stale",
                "index",
                "info",
                f"{stats['stale']} indexed file(s) changed since the last build",
                f"built_at {stats.get('built_at')}",
                "Refresh the code index (read-only).",
            ))
        return findings

    def _finding(self, key: str, kind: str, severity: str, title: str,
                 evidence: str, proposal: str) -> dict:
        return {
            "id": key,
            "kind": kind,
            "severity": severity,
            "title": title,
            "evidence": str(evidence or "")[:500],
            "proposal": str(proposal or "")[:500],
            "auto_apply": False,
            "observed_at": time.time(),
        }

    # -- persistence / reporting -------------------------------------

    def _append(self, report: dict) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(report, sort_keys=True) + "\n")
        except OSError as exc:
            logger.warning("[SelfDiagnosis] report append failed: %s", exc)

    def last(self) -> dict:
        with self._lock:
            return dict(self._last)

    def summary(self) -> dict:
        report = self.last()
        return {
            "ran_at": report.get("ran_at", 0.0),
            "findings": len(report.get("findings") or []),
            "counts": report.get("counts", {severity: 0 for severity in SEVERITIES}),
            "healthy": report.get("healthy", True),
        }

    def report_text(self) -> str:
        report = self.last() or (self.analyze() if self.index or self.feeds else {})
        findings = report.get("findings") or []
        if not findings:
            return "Self-diagnosis: nothing to report — health and logs look clean."
        lines = [f"Self-diagnosis: {len(findings)} finding(s) (read-only, no fixes applied):"]
        for finding in findings[:10]:
            lines.append(f"  [{finding['severity']}] {finding['title']}")
            if finding.get("proposal"):
                lines.append(f"      proposal: {finding['proposal']}")
        return "\n".join(lines)


__all__ = ["BOUNDARY", "SelfDiagnosis"]
