"""M23 · Partner — presence policy, verified actions, mail, calendar, cycles.

The milestone's guarantees are all negative-shaped and easy to break: nothing
sends itself, nothing forbidden runs, no unverified action claims success, and
quiet mode initiates nothing. These tests pin those.
"""
import json
import threading
import time
from datetime import datetime

import pytest


def _at(hour, minute=0):
    """Today at a local wall-clock time (ritual windows are local hours)."""
    return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0).timestamp()


@pytest.fixture()
def doc_path(tmp_path):
    return tmp_path / "partner.json"


@pytest.fixture()
def store(doc_path):
    from core.atomic_document import AtomicDocument
    return AtomicDocument(doc_path, label="Partner", defaults={
        "version": 1, "presence": {"quiet_mode": False}, "rituals": {}, "drafts": {},
    })


@pytest.fixture()
def presence(store):
    from partner.presence import PresencePolicy
    return PresencePolicy(store=store)


@pytest.fixture()
def audit(tmp_path):
    from partner.audit import ActionAuditLog
    return ActionAuditLog(tmp_path / "audit.jsonl")


@pytest.fixture()
def actions(audit):
    from partner.actions import ActionPolicy, VerifiedActionEngine
    return VerifiedActionEngine(policy=ActionPolicy(), audit=audit)


@pytest.fixture()
def continuity(tmp_path):
    from agency.goals import GoalManager
    from continuity.engine import ContinuityEngine
    return ContinuityEngine(
        store_path=str(tmp_path / "continuity.json"),
        goal_manager=GoalManager(),
    )


@pytest.fixture()
def engine(tmp_path, doc_path):
    from partner.calendar import IcsCalendar
    from partner.engine import PartnerEngine
    return PartnerEngine(
        store_path=str(doc_path),
        audit_path=str(tmp_path / "audit.jsonl"),
        calendar=IcsCalendar(tmp_path / "calendar.ics"),
    )


class _FakeCognitive:

    def __init__(self, **state):
        self._state = {
            "active_task": "", "conversation_intent": "", "current_goal": "",
            "current_topic": "", "confidence": 0.5,
        }
        self._state.update(state)

    def get(self):
        return dict(self._state)


# ---------------------------------------------------------------------------
#  Presence policy
# ---------------------------------------------------------------------------

class TestPresence:

    def test_defaults_to_idle_and_not_quiet(self, presence):
        assert presence.activity == "idle"
        assert presence.quiet_mode is False

    def test_set_activity_rejects_unknown(self, presence):
        assert presence.set_activity("coding") is True
        assert presence.activity == "coding"
        assert presence.set_activity("vibing") is False
        assert presence.activity == "coding"

    def test_idle_allows_small_talk(self, presence):
        decision = presence.decide("small_talk", now=1_000_000)
        assert decision.allowed is True
        assert decision.reason == "allowed"

    def test_coding_suppresses_small_talk(self, presence):
        presence.set_activity("coding")
        decision = presence.decide("small_talk", now=1_000_000)
        assert decision.allowed is False
        assert decision.reason == "coding_suppresses_small_talk"
        assert "commitment_missed" in decision.detail["allowed"]

    def test_coding_still_allows_urgent(self, presence):
        presence.set_activity("coding")
        assert presence.decide("urgent", now=1_000_000).allowed is True

    def test_cooldown_defers_a_second_interruption(self, presence):
        presence.set_activity("coding")
        assert presence.decide("urgent", now=1_000_000).allowed is True
        second = presence.decide("urgent", now=1_000_010)
        assert second.allowed is False
        assert second.reason == "cooldown"
        assert second.deferred_until == 1_000_900

    def test_quiet_mode_suppresses_everything(self, presence):
        presence.set_quiet(True)
        for kind in ("urgent", "commitment_missed", "small_talk"):
            decision = presence.decide(kind, now=1_000_000)
            assert decision.allowed is False
            assert decision.reason == "quiet_mode"

    def test_quiet_mode_persists_across_instances(self, doc_path):
        from core.atomic_document import AtomicDocument
        from partner.presence import PresencePolicy
        first = PresencePolicy(store=AtomicDocument(doc_path))
        first.set_quiet(True)
        second = PresencePolicy(store=AtomicDocument(doc_path))
        assert second.quiet_mode is True

    def test_unknown_interruption_kind_is_denied(self, presence):
        assert presence.decide("nonsense", now=1_000_000).allowed is False

    def test_detect_activity_from_window_title(self, presence):
        assert presence.detect_activity(window_title="main.py - Visual Studio Code") == "coding"
        assert presence.detect_activity(window_title="Zoom Meeting") == "focus"
        assert presence.detect_activity(window_title="Budget.xlsx - Excel") == "working"
        assert presence.detect_activity(window_title="Steam") == "idle"

    def test_detect_activity_from_idle_time(self, presence):
        assert presence.detect_activity(idle_seconds=1200) == "away"

    def test_detect_activity_from_cognitive_task(self, presence):
        cognitive = _FakeCognitive(active_task="debug the voice pipeline")
        assert presence.detect_activity(cognitive_state=cognitive) == "coding"
        cognitive = _FakeCognitive(conversation_intent="chitchat")
        assert presence.detect_activity(cognitive_state=cognitive) == "conversation"

    def test_initiative_requires_trust(self, presence):
        presence.set_activity("idle")
        low = presence.should_initiate(trust=0.2, now=1_000_000)
        assert low.allowed is False
        assert low.reason == "trust_too_low"
        high = presence.should_initiate(trust=0.9, now=1_000_100)
        assert high.allowed is True

    def test_initiative_suppressed_in_focus(self, presence):
        presence.set_activity("focus")
        assert presence.should_initiate(trust=0.9, now=1_000_000).allowed is False

    def test_initiative_cooldown(self, presence):
        assert presence.should_initiate(trust=0.9, now=1_000_000).allowed is True
        second = presence.should_initiate(trust=0.9, now=1_000_100)
        assert second.allowed is False
        assert second.reason == "initiative_cooldown"

    def test_disagreement_is_earned_by_trust(self, presence):
        assert presence.may_disagree(0.2).allowed is False
        assert presence.may_disagree(0.8).allowed is True

    def test_ritual_windows(self, presence):
        assert presence.ritual_for(_at(9)) == "morning"
        assert presence.ritual_for(_at(12)) == "midday"
        assert presence.ritual_for(_at(19)) == "evening"
        assert presence.ritual_for(_at(23)) == "night"
        assert presence.ritual_for(_at(16)) is None

    def test_ritual_runs_once_per_day(self, presence):
        now = _at(9)
        assert presence.ritual_due("morning", now) is True
        presence.mark_ritual("morning", now)
        assert presence.ritual_due("morning", now) is False
        # Out of its window it is never due, even on a new day.
        assert presence.ritual_due("morning", _at(19)) is False


# ---------------------------------------------------------------------------
#  Audit trail
# ---------------------------------------------------------------------------

class TestAudit:

    def test_append_and_recent_order(self, audit):
        audit.append({"id": "1", "status": "succeeded", "tier": "safe"})
        audit.append({"id": "2", "status": "failed", "tier": "safe"})
        recent = audit.recent(2)
        assert [r["id"] for r in recent] == ["2", "1"]

    def test_stats_by_status_and_tier(self, audit):
        audit.append({"id": "1", "status": "succeeded", "tier": "safe"})
        audit.append({"id": "2", "status": "unverified", "tier": "safe"})
        audit.append({"id": "3", "status": "denied", "tier": "forbidden"})
        stats = audit.stats()
        assert stats["total"] == 3
        assert stats["by_status"]["succeeded"] == 1
        assert stats["by_tier"]["forbidden"] == 1

    def test_query_filters(self, audit):
        audit.append({"id": "1", "action_type": "read_file", "status": "succeeded", "tier": "read_only"})
        audit.append({"id": "2", "action_type": "run_shell", "status": "denied", "tier": "forbidden"})
        assert [r["id"] for r in audit.query(action_type="run_shell")] == ["2"]
        assert [r["id"] for r in audit.query(status="denied")] == ["2"]

    def test_torn_line_is_skipped(self, audit, tmp_path):
        audit.append({"id": "1", "status": "succeeded", "tier": "safe"})
        with open(audit.path, "a", encoding="utf-8") as handle:
            handle.write('{"id": "2", "status": "succ')
        assert [r["id"] for r in audit.recent(5)] == ["1"]


# ---------------------------------------------------------------------------
#  Action policy + verified actions
# ---------------------------------------------------------------------------

class TestActionPolicy:

    def test_default_tiers(self):
        from partner.actions import ActionPolicy
        policy = ActionPolicy()
        assert policy.tier_of("read_file") == "read_only"
        assert policy.tier_of("checkpoint_save") == "safe"
        assert policy.tier_of("send_email") == "needs_approval"
        assert policy.tier_of("run_shell") == "forbidden"

    def test_unknown_action_fails_closed(self):
        from partner.actions import ActionPolicy
        assert ActionPolicy().tier_of("brand_new_thing") == "needs_approval"

    def test_register_rejects_unknown_tier(self):
        from partner.actions import ActionPolicy
        with pytest.raises(ValueError):
            ActionPolicy().register("x", "totally_allowed")


class TestVerifiedActions:

    def test_read_only_action_runs_and_reports_no_verifier(self, actions):
        record = actions.execute("read_file", executor=lambda: {"content": "hi"})
        assert record["status"] == "succeeded"
        assert record["verified"] is None
        assert record["verification"] == "no_verifier_registered"
        assert record["result"] == {"content": "hi"}

    def test_verifier_true_marks_verified(self, actions):
        actions.register_verifier("checkpoint_save", lambda result: (True, "checkpoint exists"))
        record = actions.execute("checkpoint_save", executor=lambda: "saved")
        assert record["status"] == "succeeded"
        assert record["verified"] is True
        assert record["verification"] == "checkpoint exists"

    def test_verifier_false_is_unverified_not_succeeded(self, actions):
        actions.register_verifier("checkpoint_save", lambda result: False)
        record = actions.execute("checkpoint_save", executor=lambda: "saved")
        assert record["status"] == "unverified"
        assert record["verified"] is False

    def test_verifier_exception_is_unverified(self, actions):
        def boom(_result):
            raise RuntimeError("checker broke")
        actions.register_verifier("checkpoint_save", boom)
        record = actions.execute("checkpoint_save", executor=lambda: "saved")
        assert record["status"] == "unverified"
        assert "checker broke" in record["verification"]

    def test_forbidden_action_never_runs(self, actions):
        ran = []
        record = actions.execute("run_shell", executor=lambda: ran.append(1))
        assert record["status"] == "denied"
        assert ran == []
        assert record["error"] == "forbidden_action"

    def test_approval_is_required_before_running(self, actions):
        ran = []
        record = actions.execute("send_email", executor=lambda: ran.append(1))
        assert record["status"] == "pending_approval"
        assert ran == []
        assert actions.stats()["pending_approval"] == 1

    def test_approve_runs_the_pending_action(self, actions):
        record = actions.execute("send_email", description="reply", executor=lambda: "sent")
        approved = actions.approve(record["id"])
        assert approved["status"] == "succeeded"
        assert approved["approved_by"] == "user"
        assert actions.stats()["pending_approval"] == 0

    def test_approving_unknown_id_returns_none(self, actions):
        assert actions.approve("act_missing") is None

    def test_failed_precondition_blocks_execution(self, actions):
        ran = []
        record = actions.execute(
            "checkpoint_save",
            precondition=lambda: (False, "no continuity"),
            executor=lambda: ran.append(1),
        )
        assert record["status"] == "blocked"
        assert ran == []
        assert "no continuity" in record["error"]

    def test_executor_exception_is_honest_failure(self, actions):
        def boom():
            raise ValueError("disk full")
        record = actions.execute("checkpoint_save", executor=boom)
        assert record["status"] == "failed"
        assert "disk full" in record["error"]

    def test_missing_executor_is_a_failure(self, actions):
        assert actions.execute("checkpoint_save")["status"] == "failed"

    def test_secrets_are_redacted_in_the_audit(self, actions):
        actions.execute("read_file", params={"password": "hunter2", "path": "a.txt"},
                        executor=lambda: "ok")
        record = actions.recent(1)[0]
        assert record["params"]["password"] == "[redacted]"
        assert record["params"]["path"] == "a.txt"

    def test_every_outcome_is_audited(self, actions):
        actions.execute("read_file", executor=lambda: "ok")
        actions.execute("run_shell", executor=lambda: "nope")
        assert actions.stats()["total"] == 2


# ---------------------------------------------------------------------------
#  Mail
# ---------------------------------------------------------------------------

class TestMail:

    def test_null_mailbox_is_empty_and_unavailable(self):
        from partner.mail import NullMailbox
        mailbox = NullMailbox()
        assert mailbox.available is False
        assert mailbox.list_recent() == []

    def test_draft_requires_recipient_and_subject(self, store):
        from partner.mail import Outbox
        outbox = Outbox(store)
        with pytest.raises(ValueError):
            outbox.draft("", "Subject", "Body")
        with pytest.raises(ValueError):
            outbox.draft("a@b.c", "", "Body")

    def test_draft_starts_needing_approval(self, store):
        from partner.mail import Outbox
        draft = Outbox(store).draft("a@b.c", "Hi", "Body", reason="reply to Alice")
        assert draft["status"] == "needs_approval"
        assert draft["sent"] is False

    def test_send_refuses_without_a_transport(self, store):
        from partner.mail import Outbox
        outbox = Outbox(store)
        draft = outbox.draft("a@b.c", "Hi", "Body")
        outbox.approve(draft["id"])
        result = outbox.send(draft["id"])
        assert result["sent"] is False
        assert "no SMTP transport" in result["reason"]

    def test_send_refuses_an_unapproved_draft(self, store):
        from partner.mail import Outbox
        outbox = Outbox(store)
        draft = outbox.draft("a@b.c", "Hi", "Body")
        assert outbox.send(draft["id"])["sent"] is False

    def test_reject_and_stats(self, store):
        from partner.mail import Outbox
        outbox = Outbox(store)
        a = outbox.draft("a@b.c", "A", "Body")
        outbox.approve(a["id"])
        b = outbox.draft("a@b.c", "B", "Body")
        outbox.reject(b["id"])
        stats = outbox.stats()
        assert stats["approved"] == 1
        assert stats["rejected"] == 1

    def test_imap_reader_is_readonly_and_parses_messages(self):
        from partner.mail import ImapMailbox

        class FakeConnection:
            def __init__(self):
                self.readonly = None
                self.criteria = None
                self.logged_out = False

            def login(self, user, password):
                return "OK", [b""]

            def select(self, folder, readonly=False):
                self.readonly = readonly
                return "OK", [b"2"]

            def search(self, charset, criteria):
                self.criteria = criteria
                return "OK", [b"1 2"]

            def fetch(self, uid, parts):
                raw = (
                    b"Subject: Hello there\r\nFrom: Alice <alice@example.com>\r\n"
                    b"Date: Mon, 1 Jan 2026 10:00:00 +0000\r\n\r\nBody text here"
                )
                return "OK", [(b'%s (FLAGS (\\Seen) BODY[] {90}' % uid, raw)]

            def logout(self):
                self.logged_out = True
                return "BYE", []

        connection = FakeConnection()
        mailbox = ImapMailbox("imap.example.com", "me", "secret",
                              conn_factory=lambda: connection)
        messages = mailbox.list_recent(limit=2, unread_only=True)
        assert connection.readonly is True
        assert connection.criteria == "UNSEEN"
        assert connection.logged_out is True
        assert len(messages) == 2
        assert messages[0].subject == "Hello there"
        assert "Alice" in messages[0].sender
        assert messages[0].snippet == "Body text here"
        assert messages[0].unread is False  # \Seen present in the FETCH metadata

    def test_imap_failure_is_reported_not_raised(self):
        from partner.mail import ImapMailbox

        class Broken:
            def login(self, user, password):
                raise OSError("connection refused")

            def logout(self):
                pass

        mailbox = ImapMailbox("imap.example.com", "me", "secret", conn_factory=Broken)
        assert mailbox.list_recent() == []
        assert "connection refused" in mailbox.last_error


# ---------------------------------------------------------------------------
#  Calendar
# ---------------------------------------------------------------------------

def _ics(events: str) -> str:
    return "BEGIN:VCALENDAR\n" + events + "END:VCALENDAR\n"


class TestCalendar:

    def test_missing_file_is_an_empty_calendar(self, tmp_path):
        from partner.calendar import IcsCalendar
        calendar = IcsCalendar(tmp_path / "missing.ics")
        assert calendar.available is False
        assert calendar.upcoming() == []

    def test_parses_and_filters_upcoming(self, tmp_path):
        from partner.calendar import IcsCalendar
        start = _at(9)
        end = start + 3600
        path = tmp_path / "calendar.ics"
        path.write_text(_ics(
            "BEGIN:VEVENT\nUID:e1\n"
            f"DTSTART:{datetime.fromtimestamp(start).strftime('%Y%m%dT%H%M%S')}\n"
            f"DTEND:{datetime.fromtimestamp(end).strftime('%Y%m%dT%H%M%S')}\n"
            "SUMMARY:Team sync\nLOCATION:Room 1\nEND:VEVENT\n"
        ), encoding="utf-8")
        calendar = IcsCalendar(path)
        events = calendar.upcoming(hours=2, now=start - 1800)
        assert len(events) == 1
        assert events[0].summary == "Team sync"
        assert events[0].location == "Room 1"
        # Outside the window it is not listed.
        assert calendar.upcoming(hours=1, now=start - 7200) == []

    def test_folded_lines_and_escapes(self, tmp_path):
        from partner.calendar import IcsCalendar
        path = tmp_path / "calendar.ics"
        path.write_text(_ics(
            "BEGIN:VEVENT\nUID:e2\nDTSTART:20260101T090000\n"
            "SUMMARY:A\\, B and a very lo\n ng title\nEND:VEVENT\n"
        ), encoding="utf-8")
        events = IcsCalendar(path).events_between(0, 4_000_000_000)
        assert events[0].summary == "A, B and a very long title"

    def test_utc_timestamps(self, tmp_path):
        from partner.calendar import IcsCalendar
        path = tmp_path / "calendar.ics"
        path.write_text(_ics(
            "BEGIN:VEVENT\nUID:e3\nDTSTART:20260101T120000Z\nSUMMARY:UTC event\nEND:VEVENT\n"
        ), encoding="utf-8")
        event = IcsCalendar(path).events_between(0, 4_000_000_000)[0]
        from datetime import timezone
        assert event.start == datetime(2026, 1, 1, 12, tzinfo=timezone.utc).timestamp()


# ---------------------------------------------------------------------------
#  Idle work cycles
# ---------------------------------------------------------------------------

class TestCycles:

    def _cycle(self, continuity, presence, actions, **kwargs):
        from partner.cycles import IdleWorkCycle
        return IdleWorkCycle(continuity=continuity, presence=presence,
                             actions=actions, **kwargs)

    def test_candidates_cover_backlog_kinds(self, continuity, presence, actions):
        project = continuity.projects.create("Ship M23", next_checkpoint="write cycles")
        continuity.commitments.add("send report", due_in_hours=1)
        continuity.checkpoints.save("research-job", step=2)
        cycle = self._cycle(continuity, presence, actions)
        kinds = {item["kind"] for item in cycle.candidates(now=time.time() + 7200)}
        assert kinds == {"project", "commitment", "resume"}
        assert project.id in [item["id"] for item in cycle.candidates()]

    def test_quiet_mode_skips_the_cycle(self, continuity, presence, actions):
        presence.set_quiet(True)
        result = self._cycle(continuity, presence, actions).run(now=1_000_000)
        assert result["ran"] is False
        assert result["reason"] == "quiet_mode"

    def test_non_idle_activity_skips_the_cycle(self, continuity, presence, actions):
        presence.set_activity("coding")
        result = self._cycle(continuity, presence, actions).run(now=1_000_000)
        assert result["ran"] is False
        assert result["reason"] == "activity_coding"

    def test_cooldown_between_cycles(self, continuity, presence, actions):
        continuity.projects.create("Work", next_checkpoint="step")
        cycle = self._cycle(continuity, presence, actions, interval=3600)
        assert cycle.run(now=1_000_000)["ran"] is True
        second = cycle.run(now=1_000_100)
        assert second["ran"] is False
        assert second["reason"] == "cooldown"

    def test_cycle_plans_and_verifies_checkpoints(self, continuity, presence, actions):
        continuity.projects.create("Work", next_checkpoint="write tests")
        cycle = self._cycle(continuity, presence, actions)
        result = cycle.run(now=1_000_000)
        assert result["ran"] is True
        assert result["planned"] == 1
        record = result["records"][0]
        assert record["status"] == "succeeded"
        assert record["verified"] is True
        task_id = record["result"]["checkpoint_task"]
        assert continuity.checkpoints.get(task_id) is not None
        assert record["cycle_id"] == result["cycle_id"]

    def test_nothing_to_do_is_not_a_failure(self, continuity, presence, actions):
        result = self._cycle(continuity, presence, actions).run(now=1_000_000)
        assert result["ran"] is True
        assert result["reason"] == "nothing_to_do"

    def test_missing_continuity_is_reported(self, presence, actions):
        result = self._cycle(None, presence, actions).run(now=1_000_000)
        assert result["ran"] is True and result["reason"] == "nothing_to_do"


# ---------------------------------------------------------------------------
#  Partner engine
# ---------------------------------------------------------------------------

class TestPartnerEngine:

    def test_briefing_composes_presence_continuity_and_drafts(self, tmp_path, doc_path, continuity):
        from partner.calendar import IcsCalendar
        from partner.engine import PartnerEngine
        start = _at(19)
        ics = tmp_path / "calendar.ics"
        ics.write_text(_ics(
            "BEGIN:VEVENT\nUID:e1\n"
            f"DTSTART:{datetime.fromtimestamp(start).strftime('%Y%m%dT%H%M%S')}\n"
            "SUMMARY:Dinner\nEND:VEVENT\n"
        ), encoding="utf-8")
        engine = PartnerEngine(
            store_path=str(doc_path), audit_path=str(tmp_path / "audit.jsonl"),
            continuity=continuity, calendar=IcsCalendar(ics),
        )
        continuity.projects.create("Ship M23", next_checkpoint="briefing")
        engine.draft_mail("a@b.c", "Hi", "Body")

        text = engine.briefing(now=start)
        assert "PARTNER BRIEF" in text
        assert "evening" in text
        assert "Ship M23" in text
        assert "Dinner" in text
        assert "Drafts awaiting approval: 1" in text

    def test_briefing_without_continuity_still_works(self, engine):
        assert "PARTNER BRIEF" in engine.briefing(now=_at(9))

    def test_maybe_brief_fires_once_per_window(self, engine):
        now = _at(9)
        first = engine.maybe_brief(now=now)
        assert first["briefed"] is True
        assert first["ritual"] == "morning"
        assert "PARTNER BRIEF" in first["text"]
        second = engine.maybe_brief(now=now + 60)
        assert second["briefed"] is False
        assert second["reason"] == "already_briefed_today"

    def test_maybe_brief_outside_any_window(self, engine):
        result = engine.maybe_brief(now=_at(16))
        assert result == {"briefed": False, "reason": "no_ritual_window"}

    def test_quiet_mode_suppresses_the_ritual(self, engine):
        engine.set_quiet(True)
        result = engine.maybe_brief(now=_at(9))
        assert result["briefed"] is False
        assert result["reason"] == "quiet_mode"

    def test_quiet_mode_publishes_state(self, tmp_path, doc_path):
        from core.event_bus import EventBus
        from core.event_specs import STATE_PARTNER_UPDATED, register_event_specs
        from partner.calendar import IcsCalendar
        from partner.engine import PartnerEngine

        bus = EventBus()
        register_event_specs(bus)
        seen = []
        bus.subscribe(STATE_PARTNER_UPDATED, lambda payload: seen.append(payload))
        engine = PartnerEngine(
            store_path=str(doc_path), audit_path=str(tmp_path / "audit.jsonl"),
            event_bus=bus, calendar=IcsCalendar(tmp_path / "calendar.ics"),
        )
        engine.set_quiet(True)
        assert seen and seen[-1]["quiet_mode"] is True

    def test_tick_reports_brief_and_cycle(self, engine):
        result = engine.tick(now=_at(9))
        assert set(result) == {"brief", "cycle", "checked_at"}
        assert result["brief"]["briefed"] is True
        assert result["cycle"]["ran"] is True

    def test_status_exposes_every_component(self, engine):
        status = engine.status()
        for key in ("presence", "trust", "actions", "outbox", "mail", "calendar", "cycles"):
            assert key in status
        assert status["mail"]["available"] is False
        assert status["trust"] == 0.5

    def test_refresh_activity_keeps_an_explicit_setting(self, engine):
        engine.set_activity("coding")
        # A tick with no signal must not downgrade the deliberate setting.
        assert engine.tick(now=_at(9))["brief"]["briefed"] is True
        assert engine.presence.activity == "coding"
        # Real evidence still wins.
        assert engine.refresh_activity(window_title="Budget.xlsx - Excel") == "working"
        assert engine.presence.activity == "working"

    def test_initiative_is_gated_by_trust(self, engine):
        assert engine.initiate(now=1_000_000)["allowed"] is False  # trust 0.5 < 0.6
        assert engine.may_disagree()["allowed"] is False


class _FakeRelationship:
    trust = 0.85


class _FakeSharedState:
    def __init__(self):
        import threading
        self.lock = threading.RLock()
        self.relationship_scores = _FakeRelationship()


class TestTrustWiring:

    def test_trust_reads_shared_state(self, tmp_path, doc_path):
        from partner.calendar import IcsCalendar
        from partner.engine import PartnerEngine
        engine = PartnerEngine(
            store_path=str(doc_path), audit_path=str(tmp_path / "audit.jsonl"),
            shared_state=_FakeSharedState(), calendar=IcsCalendar(tmp_path / "c.ics"),
        )
        assert engine.trust() == 0.85
        assert engine.initiate(now=1_000_000)["allowed"] is True


# ---------------------------------------------------------------------------
#  Tools
# ---------------------------------------------------------------------------

class TestPartnerTools:

    def _registry(self, engine):
        from agency.registry import ToolRegistry
        from partner.tools import register_partner_tools
        registry = ToolRegistry()
        assert register_partner_tools(registry, engine) == 7
        return registry

    def test_tools_registered(self, engine):
        registry = self._registry(engine)
        for name in ("partner_status", "presence_set", "partner_briefing",
                     "mail_summary", "mail_draft", "calendar_upcoming"):
            assert registry.get(name) is not None

    def test_presence_set_tool(self, engine):
        registry = self._registry(engine)
        result = registry.call("presence_set", quiet_mode=True, activity="coding")
        assert result["success"] is True
        assert result["result"]["changed"] == {"quiet_mode": True, "activity": "coding"}
        bad = registry.call("presence_set", activity="vibing")
        assert bad["result"].get("error")

    def test_mail_summary_reports_unconfigured_mailbox(self, engine):
        registry = self._registry(engine)
        result = registry.call("mail_summary")
        assert result["result"]["available"] is False
        assert "MAI_MAIL_IMAP_HOST" in result["result"]["note"]

    def test_mail_draft_tool_never_sends(self, engine):
        registry = self._registry(engine)
        result = registry.call("mail_draft", to="a@b.c", subject="Hi", body="Body")
        draft = result["result"]["draft"]
        assert draft["status"] == "needs_approval"
        assert "nothing is sent" in result["result"]["note"]

    def test_calendar_and_briefing_tools(self, engine):
        registry = self._registry(engine)
        assert registry.call("calendar_upcoming")["result"]["count"] == 0
        assert "PARTNER BRIEF" in registry.call("partner_briefing")["result"]["text"]

    def test_noop_without_an_engine(self):
        from agency.registry import ToolRegistry
        from partner.tools import register_partner_tools
        assert register_partner_tools(ToolRegistry(), None) == 0


# ---------------------------------------------------------------------------
#  Wiring
# ---------------------------------------------------------------------------

class TestWiring:

    def test_state_topic_reaches_the_ui_stream(self):
        from api.stream_manager import STREAM_TOPICS
        from core.event_specs import STATE_PARTNER_UPDATED
        assert STATE_PARTNER_UPDATED in STREAM_TOPICS

    def test_catalog_authorizes_only_the_partner_publisher(self):
        from core.event_registry import EventRegistry
        from core.event_specs import VERTEX_SPECS
        registry = EventRegistry()
        registry.register_many(VERTEX_SPECS)
        assert registry.can_publish("partner", "state.partner.updated") is True
        assert registry.can_publish("voice", "state.partner.updated") is False

    def test_scheduler_registers_the_partner_tick(self):
        from core.scheduler import Scheduler

        class Kernel:
            pass

        scheduler = Scheduler(kernel=Kernel())
        names = [task["name"] for task in scheduler.tasks]
        assert "partner_tick" in names

    def test_settings_expose_partner_intervals(self):
        from config.partner import PARTNER_TICK_INTERVAL, PARTNER_IDLE_CYCLE_INTERVAL
        assert PARTNER_TICK_INTERVAL > 0
        assert PARTNER_IDLE_CYCLE_INTERVAL > 0


# ---------------------------------------------------------------------------
#  Pending approvals surviving a restart
# ---------------------------------------------------------------------------

def _durable_engine(tmp_path, name="pending.json"):
    """A verified-action engine backed by its own atomic document."""
    from core.atomic_document import AtomicDocument
    from partner.actions import VerifiedActionEngine
    from partner.audit import ActionAuditLog

    path = tmp_path / name
    store = AtomicDocument(path, label="Pending", defaults={"version": 1, "pending_actions": {}})
    audit = ActionAuditLog(tmp_path / "audit.jsonl")
    engine = VerifiedActionEngine(audit=audit, store=store)
    return engine, path


class TestPendingApprovalsSurviveRestart:

    def test_pending_action_is_listed_by_a_fresh_engine(self, tmp_path):
        engine, path = _durable_engine(tmp_path)
        record = engine.execute("send_email", description="reply",
                                params={"to": "a@b.c"}, executor=lambda: "sent")

        restarted, _ = _durable_engine(tmp_path)
        pending = restarted.pending()
        assert [p["id"] for p in pending] == [record["id"]]
        assert pending[0]["action_type"] == "send_email"
        assert pending[0]["params"] == {"to": "a@b.c"}
        assert pending[0]["restored"] is True
        # No factory registered yet: visible, rejectable, not silently runnable.
        assert pending[0]["resumable"] is False
        assert restarted.stats()["pending_durable"] is True

    def test_rejected_restored_action_is_audited(self, tmp_path):
        engine, _path = _durable_engine(tmp_path)
        record = engine.execute("send_email", executor=lambda: "sent")

        restarted, _ = _durable_engine(tmp_path)
        rejected = restarted.reject(record["id"], reason="stale after reboot")
        assert rejected["status"] == "rejected"
        assert rejected["restored"] is True
        assert rejected["error"] == "stale after reboot"
        assert restarted.pending() == []

    def test_approval_without_a_factory_is_an_honest_failure(self, tmp_path):
        engine, _path = _durable_engine(tmp_path)
        record = engine.execute("send_email", executor=lambda: "sent")

        restarted, _ = _durable_engine(tmp_path)
        approved = restarted.approve(record["id"])
        assert approved["status"] == "failed"
        assert approved["error"] == "no_executor_after_restart"
        assert approved["restored"] is True

    def test_factory_rebuilds_the_executor_after_restart(self, tmp_path):
        engine, _path = _durable_engine(tmp_path)
        record = engine.execute("send_email", description="reply",
                                params={"to": "a@b.c"}, executor=lambda: "sent")

        restarted, _ = _durable_engine(tmp_path)
        seen = []
        restarted.register_executor_factory(
            "send_email", lambda entry: lambda: seen.append(entry["params"]) or "sent",
        )
        assert restarted.pending()[0]["resumable"] is True

        approved = restarted.approve(record["id"], approver="api")
        assert approved["status"] == "succeeded"
        assert approved["approved_by"] == "api"
        assert seen == [{"to": "a@b.c"}]
        assert restarted.pending() == []

    def test_factory_can_supply_a_precondition(self, tmp_path):
        engine, _path = _durable_engine(tmp_path)
        record = engine.execute("send_email", executor=lambda: "sent")

        restarted, _ = _durable_engine(tmp_path)
        restarted.register_executor_factory(
            "send_email",
            lambda entry: (lambda: "sent", lambda: (False, "inbox unavailable")),
        )
        approved = restarted.approve(record["id"])
        assert approved["status"] == "blocked"
        assert "inbox unavailable" in approved["error"]

    def test_factory_that_raises_is_reported(self, tmp_path):
        engine, _path = _durable_engine(tmp_path)
        record = engine.execute("send_email", executor=lambda: "sent")

        restarted, _ = _durable_engine(tmp_path)

        def boom(entry):
            raise RuntimeError("no mail service")

        restarted.register_executor_factory("send_email", boom)
        approved = restarted.approve(record["id"])
        assert approved["status"] == "failed"
        assert "executor_factory_failed" in approved["error"]

    def test_factory_returning_nothing_is_reported(self, tmp_path):
        engine, _path = _durable_engine(tmp_path)
        record = engine.execute("send_email", executor=lambda: "sent")
        restarted, _ = _durable_engine(tmp_path)
        restarted.register_executor_factory("send_email", lambda entry: None)
        assert restarted.approve(record["id"])["error"] == "executor_factory_returned_nothing"

    def test_resolution_removes_the_entry_from_disk(self, tmp_path):
        engine, _path = _durable_engine(tmp_path)
        first = engine.execute("send_email", executor=lambda: "sent")
        second = engine.execute("open_app", executor=lambda: "opened")

        restarted, _ = _durable_engine(tmp_path)
        restarted.reject(first["id"])
        restarted.register_executor_factory("open_app", lambda entry: lambda: "opened")
        restarted.approve(second["id"])

        third, _ = _durable_engine(tmp_path)
        assert third.pending() == []

    def test_a_second_approval_cannot_run_twice(self, tmp_path):
        engine, _path = _durable_engine(tmp_path)
        record = engine.execute("send_email", executor=lambda: "sent")
        restarted, _ = _durable_engine(tmp_path)
        restarted.register_executor_factory("send_email", lambda entry: lambda: "sent")
        assert restarted.approve(record["id"])["status"] == "succeeded"
        assert restarted.approve(record["id"]) is None

    def test_secret_params_are_redacted_on_disk(self, tmp_path):
        engine, path = _durable_engine(tmp_path)
        engine.execute("send_email",
                       params={"to": "a@b.c", "password": "hunter2"},
                       executor=lambda: "sent")
        assert "hunter2" not in path.read_text(encoding="utf-8")
        restarted, _ = _durable_engine(tmp_path)
        assert restarted.pending()[0]["params"]["password"] == "[redacted]"

    def test_memory_only_engine_does_not_persist(self, actions, tmp_path):
        actions.execute("send_email", executor=lambda: "sent")
        assert actions.stats()["pending_durable"] is False
        assert list(tmp_path.glob("*.json")) == []

    def test_corrupt_pending_section_does_not_break_startup(self, tmp_path):
        _engine, path = _durable_engine(tmp_path)
        path.write_text(json.dumps({"version": 1, "pending_actions": [1, 2, 3]}), encoding="utf-8")
        restarted, _ = _durable_engine(tmp_path)
        assert restarted.pending() == []

    def test_pending_entries_never_expose_preconditions(self, tmp_path):
        engine, _path = _durable_engine(tmp_path)
        engine.execute("send_email", executor=lambda: "sent")
        restarted, _ = _durable_engine(tmp_path)
        assert "precondition" not in restarted.pending()[0]

    def test_partner_engine_persists_pending_actions(self, tmp_path, doc_path):
        from partner.calendar import IcsCalendar
        from partner.engine import PartnerEngine

        first = PartnerEngine(
            store_path=str(doc_path), audit_path=str(tmp_path / "audit.jsonl"),
            calendar=IcsCalendar(tmp_path / "calendar.ics"),
        )
        record = first.actions.execute("send_email", description="reply",
                                       executor=lambda: "sent")
        assert json.loads(doc_path.read_text(encoding="utf-8"))["pending_actions"]

        restarted = PartnerEngine(
            store_path=str(doc_path), audit_path=str(tmp_path / "audit.jsonl"),
            calendar=IcsCalendar(tmp_path / "calendar.ics"),
        )
        pending = restarted.actions.pending()
        assert [p["id"] for p in pending] == [record["id"]]
        assert restarted.status()["actions"]["pending_approval"] == 1


# ---------------------------------------------------------------------------
#  The approval-tier action the partner can actually perform
# ---------------------------------------------------------------------------

class TestPartnerWorkspace:

    def test_write_stays_inside_the_root(self, tmp_path):
        from partner.workspace import PartnerWorkspace
        workspace = PartnerWorkspace(tmp_path / "ws")
        result = workspace.write("notes/brief.md", "hello")
        assert result["path"] == "notes/brief.md"
        assert result["bytes"] == 5
        assert (tmp_path / "ws" / "notes" / "brief.md").read_text(encoding="utf-8") == "hello"

    def test_traversal_is_refused(self, tmp_path):
        from partner.workspace import PartnerWorkspace
        workspace = PartnerWorkspace(tmp_path / "ws")
        assert workspace.resolve("../escape.md")[0] is None
        assert workspace.resolve("notes/../../escape.md")[0] is None
        with pytest.raises(ValueError):
            workspace.write("../escape.md", "x")
        assert not (tmp_path / "escape.md").exists()

    def test_absolute_and_empty_paths_are_refused(self, tmp_path):
        from partner.workspace import PartnerWorkspace
        workspace = PartnerWorkspace(tmp_path / "ws")
        assert workspace.resolve("C:/Windows/x.md")[0] is None
        assert workspace.resolve("/etc/passwd")[0] is None
        assert workspace.resolve("")[0] is None

    def test_oversized_content_is_refused(self, tmp_path):
        from partner.workspace import MAX_CONTENT_CHARS, PartnerWorkspace
        workspace = PartnerWorkspace(tmp_path / "ws")
        with pytest.raises(ValueError):
            workspace.write("big.md", "x" * (MAX_CONTENT_CHARS + 1))

    def test_stats_counts_files(self, tmp_path):
        from partner.workspace import PartnerWorkspace
        workspace = PartnerWorkspace(tmp_path / "ws")
        workspace.write("a.md", "1")
        workspace.write("nested/b.md", "2")
        assert workspace.stats()["files"] == 2


class TestFileApprovalAction:

    def test_request_file_parks_and_writes_nothing(self, engine):
        record = engine.request_file("briefs/monday.md", "agenda")
        assert record["status"] == "pending_approval"
        assert record["action_type"] == "create_file"
        assert not engine.workspace.exists("briefs/monday.md")
        assert engine.actions.pending()[0]["resumable"] is True

    def test_approving_writes_and_verifies_the_file(self, engine):
        record = engine.request_file("briefs/monday.md", "agenda")
        approved = engine.actions.approve(record["id"])
        assert approved["status"] == "succeeded"
        assert approved["verified"] is True
        assert approved["verification"].endswith("bytes)")
        assert engine.workspace.exists("briefs/monday.md")

    def test_traversal_request_is_blocked_at_execution(self, engine):
        record = engine.request_file("../escape.md", "nope")
        assert record["status"] == "pending_approval"
        approved = engine.actions.approve(record["id"])
        assert approved["status"] == "blocked"
        assert "traversal" in approved["error"]

    def test_request_file_refuses_oversized_content(self, engine):
        from partner.workspace import MAX_CONTENT_CHARS
        with pytest.raises(ValueError):
            engine.request_file("big.md", "x" * (MAX_CONTENT_CHARS + 1))
        assert engine.actions.pending() == []

    def test_rejecting_a_file_request_writes_nothing(self, engine):
        record = engine.request_file("briefs/monday.md", "agenda")
        assert engine.actions.reject(record["id"], reason="not now")["status"] == "rejected"
        assert not engine.workspace.exists("briefs/monday.md")

    def test_file_write_survives_a_restart_and_runs(self, tmp_path, doc_path):
        from partner.calendar import IcsCalendar
        from partner.engine import PartnerEngine

        def build():
            return PartnerEngine(
                store_path=str(doc_path),
                audit_path=str(tmp_path / "audit.jsonl"),
                calendar=IcsCalendar(tmp_path / "calendar.ics"),
            )

        first = build()
        record = first.request_file("briefs/monday.md", "agenda for monday")

        restarted = build()
        pending = restarted.actions.pending()
        assert [p["id"] for p in pending] == [record["id"]]
        assert pending[0]["resumable"] is True
        assert pending[0]["params"]["content"] == "agenda for monday"

        approved = restarted.actions.approve(record["id"], approver="api")
        assert approved["status"] == "succeeded"
        assert approved["verified"] is True
        target = tmp_path / "partner_files" / "briefs" / "monday.md"
        assert target.read_text(encoding="utf-8") == "agenda for monday"

    def test_long_content_survives_persistence_intact(self, tmp_path, doc_path):
        """Audit strings are trimmed to 500 chars; persisted params must not be."""
        from partner.calendar import IcsCalendar
        from partner.engine import PartnerEngine

        def build():
            return PartnerEngine(
                store_path=str(doc_path),
                audit_path=str(tmp_path / "audit.jsonl"),
                calendar=IcsCalendar(tmp_path / "calendar.ics"),
            )

        body = "line\n" * 400  # 2000 chars
        first = build()
        record = first.request_file("notes/long.md", body)
        restarted = build()
        assert restarted.actions.pending()[0]["params"]["content"] == body
        assert restarted.actions.approve(record["id"])["status"] == "succeeded"
        saved = tmp_path / "partner_files" / "notes" / "long.md"
        assert saved.read_text(encoding="utf-8") == body

    def test_file_create_tool_parks_the_action(self, engine):
        from agency.registry import ToolRegistry
        from partner.tools import register_partner_tools

        registry = ToolRegistry()
        assert register_partner_tools(registry, engine) == 7

        call = registry.call("file_create", path="briefs/tool.md", content="from the model")
        assert call["success"] is True
        result = call["result"]
        assert result["approval"]["status"] == "pending_approval"
        assert result["approval"]["action_type"] == "create_file"
        assert "nothing is written" in result["note"]
        assert not engine.workspace.exists("briefs/tool.md")

    def test_file_create_tool_reports_sandbox_refusals(self, engine):
        from agency.registry import ToolRegistry
        from partner.tools import register_partner_tools

        registry = ToolRegistry()
        register_partner_tools(registry, engine)
        result = registry.call("file_create", path="../escape.md", content="x")["result"]
        # Parked like any approval request; the refusal happens on execution.
        assert result["approval"]["status"] == "pending_approval"
        assert engine.actions.approve(result["approval"]["id"])["status"] == "blocked"


class TestBootLevelApprovals:

    @staticmethod
    def _boot(monkeypatch, tmp_path):
        """Run the real partner builder against a temp data dir."""
        from types import SimpleNamespace

        import app.builders.partner as partner_builder
        from agency.registry import ToolRegistry
        from core.event_bus import EventBus
        from core.event_specs import register_event_specs
        from observability.health import HealthRegistry

        monkeypatch.setattr(partner_builder, "ROOT_DIR", tmp_path)
        bus = EventBus()
        register_event_specs(bus)
        stub = SimpleNamespace(
            event_bus=bus,
            brain=SimpleNamespace(cognitive=None),
            shared_state=None,
            tool_registry=ToolRegistry(),
            health_registry=HealthRegistry(),
            continuity=None,
            kernel=None,
        )
        partner_builder.build(stub)
        return stub

    def test_parked_approval_is_approved_over_rest_after_a_restart(self, monkeypatch, tmp_path):
        from fastapi.testclient import TestClient

        from api.server import _require_auth, app as api_app, mai
        from partner.tools import register_partner_tools

        first = self._boot(monkeypatch, tmp_path)
        # The production trigger: a tool call parks the write.
        registry = first.tool_registry
        register_partner_tools(registry, first.partner)
        result = registry.call("file_create", path="briefs/monday.md", content="agenda")["result"]
        record_id = result["approval"]["id"]
        target = tmp_path / "data" / "partner_files" / "briefs" / "monday.md"
        assert not target.exists()

        # A new process boots from the same data dir.
        restarted = self._boot(monkeypatch, tmp_path)
        pending = restarted.partner.actions.pending()
        assert [p["id"] for p in pending] == [record_id]
        assert pending[0]["resumable"] is True

        previous, previous_brain = mai.partner, mai.brain
        mai.partner = restarted.partner
        api_app.dependency_overrides[_require_auth] = lambda: None
        try:
            client = TestClient(api_app)
            listed = client.get("/api/partner/approvals").json()
            assert [a["id"] for a in listed["actions"]] == [record_id]

            response = client.post(f"/api/partner/approvals/{record_id}/approve")
            assert response.status_code == 200
            approval = response.json()["approval"]
            assert approval["status"] == "succeeded"
            assert approval["verified"] is True
            assert client.get("/api/partner/approvals").json()["actions"] == []
        finally:
            api_app.dependency_overrides.pop(_require_auth, None)
            mai.partner = previous
            mai.brain = previous_brain

        assert target.read_text(encoding="utf-8") == "agenda"
        audit = (tmp_path / "data" / "partner_actions.jsonl").read_text(encoding="utf-8")
        assert "\"status\": \"succeeded\"" in audit

    def test_boot_registers_the_resumable_factory(self, monkeypatch, tmp_path):
        app_stub = self._boot(monkeypatch, tmp_path)
        actions = app_stub.partner.actions
        assert actions.stats()["verifiers"] == ["create_file", "cycle_plan"]
        assert actions.policy.tier_of("create_file") == "needs_approval"
        assert "workspace" in app_stub.partner.status()


# ---------------------------------------------------------------------------
#  Rejecting a pending approval
# ---------------------------------------------------------------------------

class TestRejectedApprovals:

    def test_reject_drops_the_pending_action_without_running_it(self, actions):
        ran = []
        record = actions.execute("send_email", description="reply",
                                 executor=lambda: ran.append(1))
        rejected = actions.reject(record["id"], reason="not now")
        assert rejected["status"] == "rejected"
        assert rejected["error"] == "not now"
        assert rejected["rejected_by"] == "user"
        assert ran == []
        assert actions.stats()["pending_approval"] == 0

    def test_reject_unknown_returns_none(self, actions):
        assert actions.reject("act_missing") is None

    def test_rejection_is_audited(self, actions):
        record = actions.execute("send_email", executor=lambda: "sent")
        actions.reject(record["id"])
        assert [r["status"] for r in actions.recent(1)] == ["rejected"]

    def test_rejected_action_cannot_then_be_approved(self, actions):
        record = actions.execute("send_email", executor=lambda: "sent")
        actions.reject(record["id"])
        assert actions.approve(record["id"]) is None


# ---------------------------------------------------------------------------
#  Kernel ritual speech
# ---------------------------------------------------------------------------

class _FakeVoice:

    def __init__(self):
        self.spoken = []
        self.spoken_event = threading.Event()

    def speak_stream(self, chunks):
        for chunk in chunks:
            self.spoken.append(chunk)
        self.spoken_event.set()

    def wait_until_done(self):
        return True

    def stop(self):
        pass


def _kernel(tmp_path, partner=None, bus=None, voice=None):
    from core.os_kernel import AIOSKernel
    from core.state.shared_state import SharedState

    class Brain:
        pass

    brain = Brain()
    brain.partner = partner
    brain.event_bus = bus
    state = SharedState(tmp_path / "state")
    return AIOSKernel(
        brain=brain,
        voice=voice if voice is not None else _FakeVoice(),
        state=state,
        relationship_engine=object(),
        event_bus=bus,
    )


class TestKernelRitual:

    def test_briefing_is_spoken_when_presence_allows(self, tmp_path, engine):
        voice = _FakeVoice()
        kernel = _kernel(tmp_path, partner=engine, voice=voice)
        result = kernel._on_partner_briefing({"text": "Morning brief"})
        assert result == {"spoken": True, "reason": "ritual"}
        assert voice.spoken_event.wait(2.0)
        assert voice.spoken == ["Morning brief"]

    def test_coding_presence_withholds_the_briefing(self, tmp_path, engine):
        voice = _FakeVoice()
        kernel = _kernel(tmp_path, partner=engine, voice=voice)
        engine.presence.set_activity("coding")
        result = kernel._on_partner_briefing({"text": "Morning brief"})
        assert result == {"spoken": False, "reason": "coding_suppresses_ritual"}
        assert voice.spoken == []

    def test_quiet_mode_withholds_the_briefing(self, tmp_path, engine):
        voice = _FakeVoice()
        kernel = _kernel(tmp_path, partner=engine, voice=voice)
        engine.set_quiet(True)
        result = kernel._on_partner_briefing({"text": "Morning brief"})
        assert result == {"spoken": False, "reason": "quiet_mode"}
        assert voice.spoken == []

    def test_mid_conversation_briefing_is_deferred(self, tmp_path, engine):
        from core.state.models import ConversationPhase
        voice = _FakeVoice()
        kernel = _kernel(tmp_path, partner=engine, voice=voice)
        kernel._set_phase(ConversationPhase.CONVERSATION)
        assert kernel._on_partner_briefing({"text": "x"})["reason"] == "conversation_in_progress"
        assert voice.spoken == []

    def test_empty_briefing_is_ignored(self, tmp_path, engine):
        kernel = _kernel(tmp_path, partner=engine)
        assert kernel._on_partner_briefing({})["reason"] == "empty_briefing"

    def test_no_voice_reports_failure(self, tmp_path, engine):
        kernel = _kernel(tmp_path, partner=engine)
        kernel.voice = None
        assert kernel._speak_briefing("hello") is False

    def test_briefing_event_reaches_the_kernel(self, tmp_path):
        from core.event_bus import EventBus
        from core.event_specs import PARTNER_BRIEFING, register_event_specs
        from core.mai_message import publish_event

        bus = EventBus()
        register_event_specs(bus)
        voice = _FakeVoice()
        kernel = _kernel(tmp_path, partner=None, bus=bus, voice=voice)
        assert kernel.attach_partner_ritual(bus) is True
        publish_event(bus, PARTNER_BRIEFING, {"ritual": "morning", "text": "Brief"}, source="partner")
        assert voice.spoken_event.wait(2.0)
        assert voice.spoken == ["Brief"]

    def test_attach_is_idempotent(self, tmp_path):
        from core.event_bus import EventBus
        from core.event_specs import PARTNER_BRIEFING, register_event_specs
        from core.mai_message import publish_event

        bus = EventBus()
        register_event_specs(bus)
        voice = _FakeVoice()
        kernel = _kernel(tmp_path, bus=bus, voice=voice)
        assert kernel.attach_partner_ritual(bus) is True
        assert kernel.attach_partner_ritual(bus) is True  # no duplicate subscription

        publish_event(bus, PARTNER_BRIEFING, {"text": "Once"}, source="partner")
        assert voice.spoken_event.wait(2.0)
        time.sleep(0.2)  # give a duplicate subscription time to show up
        assert voice.spoken == ["Once"]

    def test_attach_without_a_bus_is_false(self, tmp_path):
        kernel = _kernel(tmp_path)
        assert kernel.attach_partner_ritual(None) is False


# ---------------------------------------------------------------------------
#  REST approvals
# ---------------------------------------------------------------------------

@pytest.fixture()
def api_client(engine):
    from fastapi.testclient import TestClient

    from api.server import _require_auth, app, mai

    previous = mai.partner
    previous_brain = mai.brain
    mai.partner = engine
    app.dependency_overrides[_require_auth] = lambda: None
    client = TestClient(app)
    try:
        yield client, engine
    finally:
        app.dependency_overrides.pop(_require_auth, None)
        mai.partner = previous
        mai.brain = previous_brain


class TestPartnerAPI:

    def test_approvals_list_pending_actions_and_drafts(self, api_client):
        client, engine = api_client
        engine.actions.execute("send_email", description="reply", executor=lambda: "sent")
        engine.draft_mail("a@b.c", "Hi", "Body")

        body = client.get("/api/partner/approvals").json()
        assert body["count"] == 2
        assert body["actions"][0]["action_type"] == "send_email"
        # Executors are closures and must never leave the process.
        assert "executor" not in body["actions"][0]
        assert body["drafts"][0]["to"] == "a@b.c"

    def test_approving_an_action_runs_it(self, api_client):
        client, engine = api_client
        record = engine.actions.execute("send_email", executor=lambda: "sent")

        response = client.post(f"/api/partner/approvals/{record['id']}/approve")
        assert response.status_code == 200
        body = response.json()
        assert body["kind"] == "action"
        assert body["approval"]["status"] == "succeeded"
        assert body["approval"]["approved_by"] == "api"
        assert client.get("/api/partner/approvals").json()["actions"] == []

    def test_rejecting_an_action_records_it(self, api_client):
        client, engine = api_client
        record = engine.actions.execute("send_email", executor=lambda: "sent")

        response = client.post(
            f"/api/partner/approvals/{record['id']}/reject",
            params={"reason": "not today"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["approval"]["status"] == "rejected"
        assert body["approval"]["error"] == "not today"
        assert client.get("/api/partner/approvals").json()["actions"] == []

    def test_unknown_approval_is_404(self, api_client):
        client, _engine = api_client
        assert client.post("/api/partner/approvals/act_nope/approve").status_code == 404
        assert client.post("/api/partner/approvals/act_nope/reject").status_code == 404

    def test_drafts_are_approvable_but_still_unsendable(self, api_client):
        client, engine = api_client
        draft = engine.draft_mail("a@b.c", "Hi", "Body")

        response = client.post(f"/api/partner/approvals/{draft['id']}/approve")
        body = response.json()
        assert body["kind"] == "draft"
        assert body["draft"]["status"] == "approved"
        assert "requires a transport" in body["note"]
        assert client.get("/api/partner/approvals").json()["drafts"] == []

    def test_draft_rejection(self, api_client):
        client, engine = api_client
        draft = engine.draft_mail("a@b.c", "Hi", "Body")
        body = client.post(f"/api/partner/approvals/{draft['id']}/reject").json()
        assert body["kind"] == "draft"
        assert body["draft"]["status"] == "rejected"

    def test_status_endpoint(self, api_client):
        client, _engine = api_client
        body = client.get("/api/partner/status").json()
        assert "presence" in body
        assert "actions" in body

    def test_partner_unavailable_is_reported(self, api_client):
        from api.server import mai
        client, _engine = api_client
        mai.partner = None
        mai.brain = None
        assert client.get("/api/partner/approvals").json() == {"error": "partner_unavailable"}

    def test_rest_approval_still_runs_after_a_restart(self, tmp_path, doc_path):
        """The whole point: a reboot must not turn the approval tier into a
        read-only museum of stale ids."""
        from fastapi.testclient import TestClient

        from api.server import _require_auth, app, mai
        from partner.calendar import IcsCalendar
        from partner.engine import PartnerEngine

        def build():
            return PartnerEngine(
                store_path=str(doc_path),
                audit_path=str(tmp_path / "audit.jsonl"),
                calendar=IcsCalendar(tmp_path / "calendar.ics"),
            )

        first = build()
        record = first.actions.execute(
            "send_email", description="reply", params={"to": "a@b.c"},
            executor=lambda: "sent",
        )

        restarted = build()
        restarted.actions.register_executor_factory(
            "send_email", lambda entry: lambda: "sent",
        )

        previous, previous_brain = mai.partner, mai.brain
        mai.partner = restarted
        app.dependency_overrides[_require_auth] = lambda: None
        try:
            client = TestClient(app)
            listed = client.get("/api/partner/approvals").json()
            assert [a["id"] for a in listed["actions"]] == [record["id"]]
            assert listed["actions"][0]["resumable"] is True

            response = client.post(f"/api/partner/approvals/{record['id']}/approve")
            assert response.status_code == 200
            assert response.json()["approval"]["status"] == "succeeded"
            assert client.get("/api/partner/approvals").json()["actions"] == []
        finally:
            app.dependency_overrides.pop(_require_auth, None)
            mai.partner = previous
            mai.brain = previous_brain
