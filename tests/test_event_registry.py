"""Tests for the Event Registry (event type declarations)."""
import pytest

from core.event_registry import (
    DEAD_LETTER,
    EXPONENTIAL,
    IMMEDIATE,
    EventRegistry,
    EventSpec,
    RetryPolicy,
    namespace_of,
)


def spec(name, **kw):
    return EventSpec(name=name, **kw)


class TestNamespace:

    def test_control_data_state(self):
        assert namespace_of("control.speech.stop") == "control"
        assert namespace_of("data.memory.search") == "data"
        assert namespace_of("state.memory.stored") == "state"

    def test_legacy_default(self):
        assert namespace_of("conversation.finished") == "legacy"
        assert namespace_of("") == "legacy"


class TestEventSpec:

    def test_defaults(self):
        s = spec("control.x")
        assert s.version == 1
        assert s.retry is RetryPolicy.NEVER
        assert s.priority == "normal"
        assert s.versions == (1,)

    def test_retry_policy_coercion(self):
        assert spec("a", retry="exponential").retry is RetryPolicy.EXPONENTIAL
        assert spec("b", retry="bogus").retry is RetryPolicy.NEVER
        assert spec("c", retry=IMMEDIATE).retry is RetryPolicy.IMMEDIATE

    def test_supported_versions(self):
        s = spec("a", version=2, supported_versions=(1, 2))
        assert s.versions == (1, 2)


class TestEventRegistry:

    def setup_method(self):
        self.registry = EventRegistry()

    def test_register_and_get(self):
        self.registry.register(spec("control.memory.store", publisher="brain"))
        s = self.registry.get("control.memory.store")
        assert s is not None
        assert s.publisher == "brain"
        assert self.registry.has("control.memory.store")
        assert not self.registry.has("missing")

    def test_duplicate_identical_register_is_idempotent(self):
        self.registry.register(spec("a"))
        self.registry.register(spec("a"))
        assert len(self.registry.all_events()) == 1

    def test_conflicting_register_raises(self):
        self.registry.register(spec("a", version=1))
        with pytest.raises(ValueError):
            self.registry.register(spec("a", version=2))

    def test_replace_allows_override(self):
        self.registry.register(spec("a", version=1))
        self.registry.register(spec("a", version=2), replace=True)
        assert self.registry.get("a").version == 2

    def test_type_check(self):
        with pytest.raises(TypeError):
            self.registry.register("not a spec")
        with pytest.raises(ValueError):
            self.registry.register(spec(""))

    def test_register_many(self):
        n = self.registry.register_many([
            spec("a"), spec("b"), spec("c"),
        ])
        assert n == 3
        assert len(self.registry.all_events()) == 3

    def test_version_support(self):
        self.registry.register(spec("a", version=2, supported_versions=(1, 2)))
        assert self.registry.supports_version("a", 1)
        assert self.registry.supports_version("a", 2)
        assert not self.registry.supports_version("a", 3)
        assert not self.registry.supports_version("missing", 1)

    def test_retry_policy_lookup(self):
        self.registry.register(spec("a", retry=DEAD_LETTER, max_attempts=5))
        policy, attempts = self.registry.retry_policy("a")
        assert policy is RetryPolicy.DEAD_LETTER
        assert attempts == 5
        policy, attempts = self.registry.retry_policy("unregistered")
        assert policy is RetryPolicy.NEVER
        assert attempts == 1

    def test_capabilities_matrix(self):
        self.registry.register(spec(
            "control.speech.speak", publisher="voice", consumers=["kernel"],
            retry=EXPONENTIAL, priority="high",
        ))
        rows = self.registry.capabilities_matrix()
        assert len(rows) == 1
        row = rows[0]
        assert row["name"] == "control.speech.speak"
        assert row["publisher"] == "voice"
        assert row["consumers"] == ["kernel"]
        assert row["namespace"] == "control"
        assert row["retry"] == "exponential"
        assert row["priority"] == "high"
        assert row["max_attempts"] == 1

    def test_summary(self):
        self.registry.register_many([
            spec("control.a", publisher="x"),
            spec("data.b", publisher="x"),
            spec("state.c", publisher="y"),
        ])
        s = self.registry.summary()
        assert s["total"] == 3
        assert s["namespaces"] == {"control": 1, "data": 1, "state": 1}
        assert s["publishers"] == ["x", "y"]

    def test_all_events_sorted(self):
        self.registry.register_many([spec("b"), spec("a"), spec("c")])
        names = [s.name for s in self.registry.all_events()]
        assert names == ["a", "b", "c"]

    def test_allowed_publishers_from_publishers_wins(self):
        s = spec("a", publisher="brain", publishers=("memory", "voice"))
        assert s.allowed_publishers == ("memory", "voice")

    def test_allowed_publishers_single_fallback(self):
        assert spec("a", publisher="brain").allowed_publishers == ("brain",)
        assert spec("a").allowed_publishers == ()

    def test_can_publish_open_when_undeclared(self):
        self.registry.register(spec("a"))
        assert self.registry.can_publish("anyone", "a")
        assert self.registry.can_publish("anyone", "missing")

    def test_can_publish_enforces_declared(self):
        self.registry.register(spec("a", publishers=("memory", "voice")))
        assert self.registry.can_publish("memory", "a")
        assert self.registry.can_publish("voice", "a")
        assert not self.registry.can_publish("brain", "a")
        assert not self.registry.can_publish("", "a")

    def test_capabilities_matrix_new_columns(self):
        self.registry.register(spec(
            "data.big", publishers=("memory",), consumers=["kernel"],
            compressed=True,
        ))
        row = self.registry.capabilities_matrix()[0]
        assert row["publishers"] == ["memory"]
        assert row["compressed"] is True

    def test_to_markdown(self):
        self.registry.register_many([
            spec("control.a", publisher="brain", consumers=["kernel"],
                 description="Command A"),
            spec("data.b", publishers=("memory", "voice"), compressed=True,
                 description="Big payload"),
        ])
        md = self.registry.to_markdown()
        assert "Do not edit by hand" in md
        assert "control.a" in md
        assert "data.b" in md
        assert "brain" in md
        assert "Command A" in md
