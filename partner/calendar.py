# partner/calendar.py
"""Calendar — a local iCalendar (.ics) reader.

Local-first by design: Mai reads a synced export instead of holding OAuth
tokens for a cloud calendar. Only VEVENTs are needed (summary, start, end,
location), so this is a focused parser rather than a full RFC 5545 library.

Timezone handling is deliberately simple: ``TZID`` parameters are ignored and
floats are read as local time; a trailing ``Z`` is read as UTC. A missing file
is an empty calendar, never a failed boot.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_DATE_FORMATS = ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M", "%Y%m%d")


@dataclass
class CalendarEvent:
    uid: str = ""
    summary: str = ""
    start: float = 0.0
    end: float = 0.0
    location: str = ""

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "summary": self.summary,
            "start": self.start,
            "end": self.end,
            "location": self.location,
        }


class IcsCalendar:

    def __init__(self, path):
        self.path = Path(path)
        self.last_error = ""

    @property
    def available(self) -> bool:
        return self.path.exists()

    def events_between(self, start: float, end: float) -> list[CalendarEvent]:
        events = []
        for event in self._parse():
            event_end = event.end or event.start
            if event.start < end and event_end >= start:
                events.append(event)
        events.sort(key=lambda e: e.start)
        return events

    def upcoming(self, hours: float = 24, now: float | None = None) -> list[CalendarEvent]:
        import time
        now = time.time() if now is None else float(now)
        return self.events_between(now, now + float(hours) * 3600.0)

    def stats(self) -> dict:
        events = self._parse()
        return {
            "available": self.available,
            "path": str(self.path),
            "events": len(events),
            "last_error": self.last_error,
        }

    # -- parsing -----------------------------------------------------

    def _parse(self) -> list[CalendarEvent]:
        if not self.path.exists():
            return []
        try:
            text = self.path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self.last_error = str(exc)
            logger.warning("[Calendar] Cannot read %s: %s", self.path, exc)
            return []
        events = []
        for block in _vevent_blocks(text):
            event = _parse_block(block)
            if event is not None:
                events.append(event)
        events.sort(key=lambda e: e.start)
        return events


def _unfold(text: str) -> list[str]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    unfolded: list[str] = []
    for line in lines:
        if line[:1] in (" ", "\t") and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def _vevent_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in _unfold(text):
        stripped = line.strip()
        if stripped.upper() == "BEGIN:VEVENT":
            current = []
        elif stripped.upper() == "END:VEVENT":
            if current is not None:
                blocks.append(current)
            current = None
        elif current is not None and stripped:
            current.append(stripped)
    return blocks


def _parse_block(lines: list[str]) -> CalendarEvent | None:
    fields: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        name_part, value = line.split(":", 1)
        name = name_part.split(";", 1)[0].upper()
        fields[name] = value.strip()
    start = _parse_datetime(fields.get("DTSTART", ""))
    if not start:
        return None
    return CalendarEvent(
        uid=fields.get("UID", ""),
        summary=_unescape(fields.get("SUMMARY", "")),
        start=start,
        end=_parse_datetime(fields.get("DTEND", "")) or start,
        location=_unescape(fields.get("LOCATION", "")),
    )


def _parse_datetime(value: str) -> float:
    value = str(value or "").strip()
    if not value:
        return 0.0
    is_utc = value.endswith("Z")
    if is_utc:
        value = value[:-1]
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if is_utc:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    logger.debug("[Calendar] Unparseable date: %r", value)
    return 0.0


def _unescape(value: str) -> str:
    return (
        str(value or "")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\n", " ")
        .strip()
    )
