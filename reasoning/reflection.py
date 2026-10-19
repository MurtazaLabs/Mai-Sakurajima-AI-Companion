# reasoning/reflection.py
import logging
import threading
import time

logger = logging.getLogger(__name__)


class Reflection:

    def __init__(self, period, summary, patterns=None, topics=None, confidence=0.5):
        self.period = str(period)
        self.summary = str(summary)
        self.patterns = list(patterns or [])
        self.topics = list(topics or [])
        self.confidence = max(0.0, min(1.0, float(confidence)))
        self.timestamp = time.time()

    def to_dict(self):
        return {
            "period": self.period,
            "summary": self.summary,
            "patterns": list(self.patterns),
            "topics": list(self.topics),
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


class ReflectionEngine:

    def __init__(self, journal=None, event_bus=None, enforce_cadence=False,
                 daily_interval=86400.0, weekly_interval=604800.0,
                 monthly_interval=2592000.0):
        self.journal = journal
        self.event_bus = event_bus
        self._lock = threading.RLock()
        self._last_daily = 0.0
        self._last_weekly = 0.0
        self._last_monthly = 0.0
        self.enforce_cadence = bool(enforce_cadence)
        self.daily_interval = daily_interval
        self.weekly_interval = weekly_interval
        self.monthly_interval = monthly_interval

    def due(self, period):
        """True when a reflection for ``period`` is now due, so automated
        loops (e.g. PostThinkHooks on every turn) do not re-fire it every
        cycle (R-7).  When cadence is disabled every call is due, preserving
        the legacy always-run behaviour for direct callers/tests."""
        if not self.enforce_cadence:
            return True
        last = {
            "daily": self._last_daily,
            "weekly": self._last_weekly,
            "monthly": self._last_monthly,
        }.get(str(period).lower(), 0.0)
        interval = {
            "daily": self.daily_interval,
            "weekly": self.weekly_interval,
            "monthly": self.monthly_interval,
        }.get(str(period).lower(), 0.0)
        return (time.time() - last) >= interval

    def daily_reflection(self, memories=None, thoughts=None, force=False):
        if not force and not self.due("daily"):
            logger.debug("[Reflection] daily cascade skipped (cadence: no t due)")
            return None
        memories = memories or []
        thoughts = thoughts or []

        topics = self._extract_topics(memories, thoughts)
        patterns = self._detect_patterns(topics)
        summary = self._build_summary("daily", topics, patterns)

        reflection = Reflection(
            period="daily",
            summary=summary,
            patterns=patterns,
            topics=topics,
        )

        with self._lock:
            self._last_daily = time.time()

        if self.event_bus:
            from core.event_specs import REFLECTION_GENERATED
            from core.mai_message import publish_event
            publish_event(self.event_bus, REFLECTION_GENERATED, reflection.to_dict(), source="reasoning")

        return reflection

    def weekly_reflection(self, memories=None, thoughts=None, force=False):
        if not force and not self.due("weekly"):
            logger.debug("[Reflection] weekly cascade skipped (cadence: not due)")
            return None
        memories = memories or []
        thoughts = thoughts or []

        topics = self._extract_topics(memories, thoughts)
        patterns = self._detect_patterns(topics)
        patterns.append("aggregated over 7-day window")
        summary = self._build_summary("weekly", topics, patterns)

        reflection = Reflection(
            period="weekly",
            summary=summary,
            patterns=patterns,
            topics=topics,
        )

        with self._lock:
            self._last_weekly = time.time()

        if self.event_bus:
            from core.event_specs import REFLECTION_GENERATED
            from core.mai_message import publish_event
            publish_event(self.event_bus, REFLECTION_GENERATED, reflection.to_dict(), source="reasoning")

        return reflection

    def monthly_reflection(self, memories=None, thoughts=None, force=False):
        if not force and not self.due("monthly"):
            logger.debug("[Reflection] monthly cascade skipped (cadence: not due)")
            return None
        memories = memories or []
        thoughts = thoughts or []

        topics = self._extract_topics(memories, thoughts)
        patterns = self._detect_patterns(topics)
        patterns.append("long-term trend analysis")
        summary = self._build_summary("monthly", topics, patterns)

        reflection = Reflection(
            period="monthly",
            summary=summary,
            patterns=patterns,
            topics=topics,
        )

        with self._lock:
            self._last_monthly = time.time()

        if self.event_bus:
            from core.event_specs import REFLECTION_GENERATED
            from core.mai_message import publish_event
            publish_event(self.event_bus, REFLECTION_GENERATED, reflection.to_dict(), source="reasoning")

        return reflection

    def _extract_topics(self, memories, thoughts):
        topics = {}

        for mem in memories:
            text = ""
            if isinstance(mem, dict):
                text = mem.get("text", mem.get("content", ""))
                tags = mem.get("tags", [])
                for tag in tags:
                    topics[str(tag)] = topics.get(str(tag), 0) + 1
            else:
                text = str(mem)

            words = str(text).lower().split()
            for w in words:
                if len(w) > 4:
                    topics[w] = topics.get(w, 0) + 1

        for thought in thoughts:
            if isinstance(thought, dict):
                query = thought.get("query", "")
                for w in str(query).lower().split():
                    if len(w) > 4:
                        topics[w] = topics.get(w, 0) + 1

        sorted_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)
        return [t for t, c in sorted_topics[:10]]

    def _detect_patterns(self, topics):
        patterns = []
        if len(topics) >= 3:
            patterns.append(f"User frequently discusses {', '.join(topics[:3])}")
        if len(topics) >= 5:
            patterns.append("Wide range of topics indicates varied interests")
        return patterns

    def _build_summary(self, period, topics, patterns):
        parts = [f"{period.capitalize()} reflection:"]

        if topics:
            parts.append(f"Main topics: {', '.join(topics[:5])}.")
        else:
            parts.append("No significant topics identified.")

        if patterns:
            parts.append(" ".join(patterns))

        return " ".join(parts)
