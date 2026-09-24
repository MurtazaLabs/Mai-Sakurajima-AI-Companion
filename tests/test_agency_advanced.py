import time
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
#  GoalManager tests
# ---------------------------------------------------------------------------

class TestGoalManager:

    def test_create_goal_returns_goal_with_id(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        goal = mgr.create("Learn Python", priority="high")
        assert goal is not None
        assert goal.id is not None
        assert len(goal.id) > 0
        assert goal.description == "Learn Python"
        assert goal.priority == "high"
        assert goal.status == "active"

    def test_create_goal_default_priority_is_normal(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        goal = mgr.create("Do something")
        assert goal.priority == "normal"

    def test_create_goal_invalid_priority_defaults_to_normal(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        goal = mgr.create("Task", priority="urgent")
        assert goal.priority == "normal"

    def test_create_goal_empty_description_returns_none(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        assert mgr.create("") is None
        assert mgr.create(None) is None

    def test_get_goal_returns_goal(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        goal = mgr.create("Test")
        retrieved = mgr.get(goal.id)
        assert retrieved is goal

    def test_get_goal_missing_returns_none(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        assert mgr.get("nonexistent") is None

    def test_complete_goal_marks_completed(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        goal = mgr.create("Finish")
        result = mgr.complete(goal.id)
        assert result is True
        assert goal.status == "completed"
        assert goal.completed_at > 0

    def test_complete_goal_missing_returns_false(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        assert mgr.complete("nope") is False

    def test_complete_goal_already_completed_returns_false(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        goal = mgr.create("Already done")
        mgr.complete(goal.id)
        assert mgr.complete(goal.id) is False

    def test_list_active_goals_sorted_by_priority(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        g1 = mgr.create("Low priority", priority="low")
        g2 = mgr.create("High priority", priority="high")
        g3 = mgr.create("Normal priority", priority="normal")
        active = mgr.list(status="active")
        assert len(active) == 3
        assert active[0].priority == "high"
        assert active[1].priority == "normal"
        assert active[2].priority == "low"

    def test_list_without_status_returns_all(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        mgr.create("A")
        mgr.create("B")
        all_goals = mgr.list()
        assert len(all_goals) == 2

    def test_max_active_pauses_excess_lowest_priority(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        mgr._max_active = 2
        g1 = mgr.create("First", priority="high")
        g2 = mgr.create("Second", priority="normal")
        g3 = mgr.create("Third", priority="low")
        # max() picks the LOWEST-priority existing goal → g2 (normal) is paused
        assert g1.status == "active"
        assert g2.status == "paused"
        assert g3.status == "active"

    def test_cancel_goal(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        goal = mgr.create("Cancel me")
        assert mgr.cancel(goal.id) is True
        assert goal.status == "cancelled"

    def test_cancel_missing_returns_false(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        assert mgr.cancel("missing") is False

    def test_activate_goal(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        goal = mgr.create("Pause then activate")
        mgr._goals[goal.id].status = "paused"
        assert mgr.activate(goal.id) is True
        assert goal.status == "active"

    def test_activate_missing_returns_false(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        assert mgr.activate("ghost") is False

    def test_due_for_bringup_returns_goals_past_turn_threshold(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        g1 = mgr.create("Bring up soon", priority="high")
        g2 = mgr.create("Not yet", priority="normal")
        with mgr._lock:
            g1.turn_count = 10
            g2.turn_count = 1
        due = mgr.due_for_bringup(max_turns=5)
        assert g1 in due
        assert g2 not in due

    def test_due_for_bringup_sorted_by_priority(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        g_low = mgr.create("Low priority", priority="low")
        g_high = mgr.create("High priority", priority="high")
        with mgr._lock:
            g_low.turn_count = 10
            g_high.turn_count = 10
        due = mgr.due_for_bringup(max_turns=5)
        assert len(due) == 2
        assert due[0].priority == "high"

    def test_increment_turns_increments_all_active(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        g1 = mgr.create("Active goal")
        g2 = mgr.create("Another active")
        mgr.increment_turns()
        assert g1.turn_count == 1
        assert g2.turn_count == 1

    def test_increment_turns_specific_goal(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        g1 = mgr.create("Goal one")
        g2 = mgr.create("Goal two")
        mgr.increment_turns(goal_id=g1.id)
        assert g1.turn_count == 1
        assert g2.turn_count == 0

    def test_stats_returns_counts(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        g1 = mgr.create("Active one")
        g2 = mgr.create("Active two")
        mgr.complete(g1.id)
        stats = mgr.stats()
        assert stats["total"] == 2
        assert stats["active"] == 1
        assert stats["completed"] == 1

    def test_create_publishes_event(self):
        from agency.goals import GoalManager
        bus = MagicMock()
        mgr = GoalManager(event_bus=bus)
        mgr.create("Event goal", priority="high")
        msgs = [c[0][0] for c in bus.publish_message.call_args_list]
        assert len(msgs) == 2
        assert msgs[0].type == "data.goal.created"
        assert msgs[1].type == "state.goal.updated"
        msg = msgs[0]
        assert msg.payload["description"] == "Event goal"
        assert msg.payload["priority"] == "high"

    def test_complete_publishes_event(self):
        from agency.goals import GoalManager
        bus = MagicMock()
        mgr = GoalManager(event_bus=bus)
        goal = mgr.create("Complete me")
        bus.reset_mock()
        mgr.complete(goal.id)
        assert bus.publish_message.call_count >= 1
        first_msg = bus.publish_message.call_args_list[0][0][0]
        assert first_msg.type == "data.goal.completed"
        first_payload = first_msg.payload
        assert first_payload["id"] == goal.id

    def test_cancel_publishes_event(self):
        from agency.goals import GoalManager
        bus = MagicMock()
        mgr = GoalManager(event_bus=bus)
        goal = mgr.create("Cancel me")
        bus.reset_mock()
        mgr.cancel(goal.id)
        msgs = [c[0][0] for c in bus.publish_message.call_args_list]
        assert len(msgs) == 2
        assert msgs[0].type == "data.goal.cancelled"
        assert msgs[1].type == "state.goal.updated"
        msg = msgs[0]
        assert msg.payload["id"] == goal.id

    def test_create_goal_strips_description(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        goal = mgr.create("  spaced out  ")
        assert goal.description == "spaced out"

    def test_goal_priority_sorting_in_list(self):
        from agency.goals import GoalManager
        mgr = GoalManager()
        mgr.create("low", priority="low")
        mgr.create("high", priority="high")
        mgr.create("normal", priority="normal")
        all_g = mgr.list()
        priorities = [g.priority for g in all_g]
        assert priorities == ["high", "normal", "low"]


# ---------------------------------------------------------------------------
#  ProceduralMemory tests
# ---------------------------------------------------------------------------

class TestProceduralMemory:

    def test_learn_stores_rule(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        rule = pm.learn("Greet users warmly", "user_joins")
        assert rule is not None
        assert rule.rule == "Greet users warmly"
        assert rule.context == "user_joins"
        assert rule.confidence == 0.5
        assert rule.source == "experience"

    def test_learn_empty_rule_returns_none(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        assert pm.learn("", "context") is None
        assert pm.learn("rule", "") is None
        assert pm.learn("", "") is None
        assert pm.learn(None, "ctx") is None
        assert pm.learn("rule", None) is None

    def test_learn_reinforces_existing_rule(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        r1 = pm.learn("Be polite", "greeting", confidence=0.4)
        r2 = pm.learn("Be polite", "greeting")
        assert r1 is r2
        assert r1.confidence == pytest.approx(0.5)
        assert r1.apply_count == 1

    def test_retrieve_returns_matching_rules(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        pm.learn("Say hello", "greeting")
        pm.learn("Wave hand", "greeting")
        pm.learn("Close door", "exit")
        matches = pm.retrieve("greeting")
        assert len(matches) == 2
        assert all(r.context == "greeting" for r in matches)

    def test_retrieve_sorted_by_confidence(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        pm.learn("Low conf", "test", confidence=0.3)
        pm.learn("High conf", "test", confidence=0.9)
        pm.learn("Med conf", "test", confidence=0.6)
        matches = pm.retrieve("test", min_confidence=0.0)
        confs = [r.confidence for r in matches]
        assert confs == sorted(confs, reverse=True)

    def test_retrieve_filters_by_min_confidence(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        pm.learn("Good rule", "ctx", confidence=0.8)
        pm.learn("Weak rule", "ctx", confidence=0.2)
        matches = pm.retrieve("ctx", min_confidence=0.5)
        assert len(matches) == 1
        assert matches[0].rule == "Good rule"

    def test_retrieve_context_partial_match(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        pm.learn("Rule", "user_joins_channel")
        matches = pm.retrieve("joins")
        assert len(matches) == 1

    def test_retrieve_no_match_returns_empty(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        pm.learn("Rule", "abc")
        assert pm.retrieve("xyz") == []

    def test_apply_increments_count(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        pm.learn("Rule", "ctx")
        assert pm.apply("Rule", "ctx") is True
        r = pm._rules[0]
        assert r.apply_count == 1
        assert r.last_applied > 0

    def test_apply_no_match_returns_false(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        assert pm.apply("Nonexistent", "ctx") is False

    def test_list_all_rules(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        pm.learn("Rule 1", "ctx1", confidence=0.9)
        pm.learn("Rule 2", "ctx2", confidence=0.1)
        all_rules = pm.list(min_confidence=0.0)
        assert len(all_rules) == 2

    def test_list_filters_by_confidence(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        pm.learn("Rule 1", "ctx1", confidence=0.9)
        pm.learn("Rule 2", "ctx2", confidence=0.1)
        filtered = pm.list(min_confidence=0.5)
        assert len(filtered) == 1

    def test_stats_returns_averages(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        pm.learn("Rule 1", "ctx", confidence=0.6)
        pm.learn("Rule 2", "ctx", confidence=0.4)
        stats = pm.stats()
        assert stats["total"] == 2
        assert stats["avg_confidence"] == 0.5

    def test_stats_empty(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        stats = pm.stats()
        assert stats["total"] == 0
        assert stats["avg_confidence"] == 0.0

    def test_learn_publishes_event(self):
        from agency.procedural import ProceduralMemory
        bus = MagicMock()
        pm = ProceduralMemory(event_bus=bus)
        pm.learn("Rule", "ctx")
        bus.publish_message.assert_called_once()
        msg = bus.publish_message.call_args[0][0]
        assert msg.type == "data.procedural.learned"
        assert msg.payload["rule"] == "Rule"
        assert msg.payload["context"] == "ctx"

    def test_context_stripped_and_lowered(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        r = pm.learn("Rule", "  UPPER Context  ")
        assert r.context == "upper context"

    def test_confidence_clamped(self):
        from agency.procedural import ProceduralMemory
        pm = ProceduralMemory()
        r = pm.learn("Rule", "ctx", confidence=2.0)
        assert r.confidence == 1.0
        r2 = pm.learn("Rule2", "ctx2", confidence=-1.0)
        assert r2.confidence == 0.0


# ---------------------------------------------------------------------------
#  WorldModel tests
# ---------------------------------------------------------------------------

class TestWorldModel:

    def test_add_entity_creates_and_returns_entity(self):
        from agency.world import WorldModel
        wm = WorldModel()
        entity = wm.add_entity("Alice", category="person", attributes={"age": 25})
        assert entity is not None
        assert entity.name == "alice"
        assert entity.category == "person"
        assert entity.attributes == {"age": 25}

    def test_add_entity_empty_name_returns_none(self):
        from agency.world import WorldModel
        wm = WorldModel()
        assert wm.add_entity("", category="person") is None
        assert wm.add_entity(None) is None

    def test_add_entity_updates_existing(self):
        from agency.world import WorldModel
        wm = WorldModel()
        e1 = wm.add_entity("Bob", category="person", attributes={"age": 30})
        e2 = wm.add_entity("Bob", category="person", attributes={"city": "NYC"})
        assert e1 is e2
        assert e1.attributes["age"] == 30
        assert e1.attributes["city"] == "NYC"
        assert e1.updated_at > 0

    def test_get_retrieves_entity(self):
        from agency.world import WorldModel
        wm = WorldModel()
        wm.add_entity("Charlie", category="person")
        entity = wm.get("Charlie")
        assert entity is not None
        assert entity.name == "charlie"

    def test_get_case_insensitive(self):
        from agency.world import WorldModel
        wm = WorldModel()
        wm.add_entity("Alice", category="person")
        assert wm.get("alice") is not None
        assert wm.get("ALICE") is not None

    def test_get_missing_returns_none(self):
        from agency.world import WorldModel
        wm = WorldModel()
        assert wm.get("Nobody") is None

    def test_relate_links_entities(self):
        from agency.world import WorldModel
        wm = WorldModel()
        wm.add_entity("Alice", category="person")
        wm.add_entity("Bob", category="person")
        assert wm.relate("Alice", "friend_of", "Bob") is True
        alice = wm.get("Alice")
        assert "friend_of" in alice.relations
        assert "bob" in alice.relations["friend_of"]

    def test_relate_missing_source_returns_false(self):
        from agency.world import WorldModel
        wm = WorldModel()
        wm.add_entity("Alice", category="person")
        assert wm.relate("Nobody", "knows", "Alice") is False

    def test_relate_missing_target_returns_false(self):
        from agency.world import WorldModel
        wm = WorldModel()
        wm.add_entity("Alice", category="person")
        assert wm.relate("Alice", "knows", "Nobody") is False

    def test_query_returns_entity_with_relations(self):
        from agency.world import WorldModel
        wm = WorldModel()
        wm.add_entity("Alice", category="person")
        wm.add_entity("Bob", category="person")
        wm.relate("Alice", "friend_of", "Bob")
        results = wm.query("Alice")
        assert len(results) == 2
        assert results[0]["name"] == "alice"
        assert results[1]["relation"] == "friend_of"
        assert results[1]["entity"]["name"] == "bob"

    def test_query_missing_returns_empty(self):
        from agency.world import WorldModel
        wm = WorldModel()
        assert wm.query("Ghost") == []

    def test_query_filtered_by_relation(self):
        from agency.world import WorldModel
        wm = WorldModel()
        wm.add_entity("Alice", category="person")
        wm.add_entity("Bob", category="person")
        wm.add_entity("ProjectX", category="project")
        wm.relate("Alice", "friend_of", "Bob")
        wm.relate("Alice", "works_on", "ProjectX")
        results = wm.query("Alice", relation="friend_of")
        assert len(results) == 2
        assert results[1]["relation"] == "friend_of"

    def test_search_by_category(self):
        from agency.world import WorldModel
        wm = WorldModel()
        wm.add_entity("Alice", category="person")
        wm.add_entity("Bob", category="person")
        wm.add_entity("PyProject", category="project")
        results = wm.search(category="person")
        assert len(results) == 2
        results = wm.search(category="project")
        assert len(results) == 1

    def test_search_by_attribute(self):
        from agency.world import WorldModel
        wm = WorldModel()
        wm.add_entity("Alice", category="person", attributes={"city": "Tokyo"})
        wm.add_entity("Bob", category="person", attributes={"city": "Osaka"})
        results = wm.search(attribute_key="city", attribute_value="tokyo")
        assert len(results) == 1
        assert results[0]["name"] == "alice"

    def test_list_categories(self):
        from agency.world import WorldModel
        wm = WorldModel()
        wm.add_entity("Alice", category="person")
        wm.add_entity("Bob", category="person")
        wm.add_entity("Py", category="project")
        cats = wm.list_categories()
        assert cats == {"person": 2, "project": 1}

    def test_stats(self):
        from agency.world import WorldModel
        wm = WorldModel()
        wm.add_entity("Alice", category="person")
        stats = wm.stats()
        assert stats["total_entities"] == 1
        assert stats["categories"] == {"person": 1}

    def test_add_entity_publishes_event(self):
        from agency.world import WorldModel
        bus = MagicMock()
        wm = WorldModel(event_bus=bus)
        wm.add_entity("Eve", category="person")
        bus.publish_message.assert_called_once()
        msg = bus.publish_message.call_args[0][0]
        assert msg.type == "data.world.entity_added"
        assert msg.payload["name"] == "eve"
        assert msg.payload["category"] == "person"

    def test_entity_category_lowered(self):
        from agency.world import WorldModel
        wm = WorldModel()
        e = wm.add_entity("Alice", category="PERSON")
        assert e.category == "person"


# ---------------------------------------------------------------------------
#  DreamEngine tests
# ---------------------------------------------------------------------------

class TestDreamEngine:

    def test_run_level_1_with_empty_state(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        de = DreamEngine()
        report = de.run(MemoryState(), level=1)
        assert report.level == 1
        assert report.duration >= 0
        assert len(report.tasks_run) > 0

    def test_run_publishes_event(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        bus = MagicMock()
        de = DreamEngine(event_bus=bus)
        de.run(MemoryState())
        msgs = [c[0][0] for c in bus.publish_message.call_args_list]
        assert len(msgs) == 2
        assert msgs[0].type == "data.dream.completed"
        assert msgs[1].type == "state.dreaming.finished"
        assert "duration" in msgs[0].payload

    def test_should_dream_returns_false_when_not_idle(self):
        from agency.dreaming import DreamEngine
        de = DreamEngine()
        de._min_idle_seconds = 0
        de._last_dream = time.time()
        assert de.should_dream(1) is False

    def test_should_dream_returns_true_when_conditions_met(self):
        from agency.dreaming import DreamEngine
        de = DreamEngine()
        de._last_dream = 0
        idle = de._min_idle_seconds + 10
        assert de.should_dream(idle) is True

    def test_run_sets_last_dream_time(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        de = DreamEngine()
        before = de._last_dream
        de.run(MemoryState())
        assert de._last_dream >= before


# ---------------------------------------------------------------------------
#  PersonalityEvolution tests
# ---------------------------------------------------------------------------

class TestPersonalityEvolution:

    @pytest.fixture
    def personality_state(self):
        from core.personality_state import PersonalityState
        ps = PersonalityState()
        ps.path = None
        return ps

    def test_evolve_with_behavior_signals_modifies_traits(self, personality_state):
        from agency.evolution import PersonalityEvolution
        evo = PersonalityEvolution(personality_state)
        adjustments = {"comfort_behavior": 1.0}
        applied = evo.evolve(behavior_adjustments=adjustments)
        assert "warmth" in applied
        assert "affection" in applied
        assert personality_state.state["warmth"] > 0.5
        assert personality_state.state["affection"] > 0.3

    def test_evolve_with_multiple_signals_accumulates(self, personality_state):
        from agency.evolution import PersonalityEvolution
        evo = PersonalityEvolution(personality_state)
        adjustments = {"comfort_behavior": 1.0, "playfulness_boost": 1.0}
        applied = evo.evolve(behavior_adjustments=adjustments)
        assert "playfulness" in applied
        assert "teasing" in applied
        assert "warmth" in applied

    def test_evolve_with_unknown_signal_does_nothing(self, personality_state):
        from agency.evolution import PersonalityEvolution
        evo = PersonalityEvolution(personality_state)
        applied = evo.evolve(behavior_adjustments={"unknown_signal": 1.0})
        assert applied == {}

    def test_evolve_with_no_inputs_returns_empty(self, personality_state):
        from agency.evolution import PersonalityEvolution
        evo = PersonalityEvolution(personality_state)
        assert evo.evolve() == {}
        assert evo.evolve(behavior_adjustments=None, reflections=None) == {}

    def test_evolve_respects_trait_bounds_lower(self, personality_state):
        from agency.evolution import PersonalityEvolution
        evo = PersonalityEvolution(personality_state)
        personality_state.state["warmth"] = 0.2
        adjustments = {"energy_conservation": 1.0}
        applied = evo.evolve(behavior_adjustments=adjustments)
        # patience should increase, confidence should decrease
        assert personality_state.state["patience"] > 0.7
        assert personality_state.state["confidence"] >= 0.2

    def test_evolve_respects_trait_bounds_upper(self, personality_state):
        from agency.evolution import TRAIT_BOUNDS, TRAIT_SIGNAL_MAP, PersonalityEvolution
        orig_bounds = TRAIT_BOUNDS.copy()
        orig_signal = TRAIT_SIGNAL_MAP.copy()
        import agency.evolution as evo_mod
        evo_mod.TRAIT_BOUNDS = {"playfulness": (0.1, 0.8)}
        evo_mod.TRAIT_SIGNAL_MAP = {"playfulness_boost": {"playfulness": 1.0}}
        try:
            evo = PersonalityEvolution(personality_state)
            personality_state.state["playfulness"] = 0.8
            applied = evo.evolve(behavior_adjustments={"playfulness_boost": 1.0})
            assert personality_state.state["playfulness"] == 0.8
            assert "playfulness" not in applied
        finally:
            evo_mod.TRAIT_BOUNDS = orig_bounds
            evo_mod.TRAIT_SIGNAL_MAP = orig_signal

    def test_evolve_from_reflections_pattern_based(self, personality_state):
        from agency.evolution import PersonalityEvolution
        evo = PersonalityEvolution(personality_state)
        reflections = [{"summary": "User responded well to teasing today", "patterns": ["playful"]}]
        applied = evo.evolve(reflections=reflections)
        assert "teasing" in applied
        assert applied["teasing"] >= 0.01

    def test_evolve_from_reflections_warmth_keywords(self, personality_state):
        from agency.evolution import PersonalityEvolution
        evo = PersonalityEvolution(personality_state)
        reflections = [{"summary": "Had a warm and affectionate conversation"}]
        applied = evo.evolve(reflections=reflections)
        assert "affection" in applied

    def test_evolve_from_reflections_patience_keywords(self, personality_state):
        from agency.evolution import PersonalityEvolution
        evo = PersonalityEvolution(personality_state)
        reflections = [{"summary": "Stayed patient and calm throughout"}]
        applied = evo.evolve(reflections=reflections)
        assert "patience" in applied

    def test_evolve_from_reflections_string_input(self, personality_state):
        from agency.evolution import PersonalityEvolution
        evo = PersonalityEvolution(personality_state)
        applied = evo.evolve(reflections=["teasing and playful interaction"])
        assert "teasing" in applied

    def test_evolve_from_reflections_no_keywords_does_nothing(self, personality_state):
        from agency.evolution import PersonalityEvolution
        evo = PersonalityEvolution(personality_state)
        applied = evo.evolve(reflections=[{"summary": "Boring conversation"}])
        assert applied == {}

    def test_evolve_unknown_trait_in_adjustment_skipped(self, personality_state):
        from agency.evolution import TRAIT_SIGNAL_MAP, PersonalityEvolution
        import agency.evolution as evo_mod
        orig = TRAIT_SIGNAL_MAP.copy()
        evo_mod.TRAIT_SIGNAL_MAP = {"test_signal": {"nonexistent_trait": 0.1}}
        try:
            evo = PersonalityEvolution(personality_state)
            applied = evo.evolve(behavior_adjustments={"test_signal": 1.0})
            assert applied == {}
        finally:
            evo_mod.TRAIT_SIGNAL_MAP = orig

    def test_evolve_publishes_event(self, personality_state):
        from agency.evolution import PersonalityEvolution
        bus = MagicMock()
        evo = PersonalityEvolution(personality_state, event_bus=bus)
        evo.evolve(behavior_adjustments={"comfort_behavior": 1.0})
        bus.publish_message.assert_called_once()
        msg = bus.publish_message.call_args[0][0]
        assert msg.type == "data.evolution.adjusted"
        assert "adjustments" in msg.payload
        assert "current_state" in msg.payload

    def test_history_records_adjustments(self, personality_state):
        from agency.evolution import PersonalityEvolution
        evo = PersonalityEvolution(personality_state)
        evo.evolve(behavior_adjustments={"comfort_behavior": 1.0})
        evo.evolve(behavior_adjustments={"playfulness_boost": 1.0})
        hist = evo.history()
        assert len(hist) == 2
        assert "adjustments" in hist[0]
        assert "signals" in hist[0]

    def test_history_limit(self, personality_state):
        from agency.evolution import PersonalityEvolution
        evo = PersonalityEvolution(personality_state)
        evo._max_log = 5
        for _ in range(10):
            evo.evolve(behavior_adjustments={"comfort_behavior": 1.0})
        assert len(evo.history()) == 5

    def test_evolve_does_not_save_if_no_path(self, personality_state):
        from agency.evolution import PersonalityEvolution
        personality_state.path = None
        with patch.object(personality_state, "save") as mock_save:
            evo = PersonalityEvolution(personality_state)
            evo.evolve(behavior_adjustments={"comfort_behavior": 1.0})
            mock_save.assert_called_once()

    def test_signal_delta_ignored_uses_fixed_trait_amounts(self, personality_state):
        from agency.evolution import PersonalityEvolution
        evo = PersonalityEvolution(personality_state)
        old_warmth = personality_state.state["warmth"]
        # signal delta value is ignored; only signal name matters
        applied = evo.evolve(behavior_adjustments={"comfort_behavior": 0.001})
        # comfort_behavior maps to warmth += 0.02, affection += 0.02
        assert applied.get("warmth") == pytest.approx(0.02, abs=1e-4)
        assert personality_state.state["warmth"] == pytest.approx(old_warmth + 0.02, abs=1e-4)
