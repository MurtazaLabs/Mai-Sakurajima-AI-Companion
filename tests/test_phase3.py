import time

from agency.goals import Goal, GoalManager
from core.emotion_goals import EmotionGoalEngine
from core.emotion_system import (
    EMOTION_PROFILES,
    EmotionHistory,
    EmotionTriggerLog,
    find_closest_profile,
)


class TestEmotionHistory:
    def test_init(self):
        h = EmotionHistory()
        assert h.count() == 0

    def test_record(self):
        h = EmotionHistory()
        h.record({"happy": 0.8, "lonely": 0.1})
        assert h.count() == 1

    def test_record_with_trigger(self):
        h = EmotionHistory()
        h.record({"happy": 0.8}, trigger={"type": "gratitude"})
        recent = h.recent()
        assert recent[0]["trigger"]["type"] == "gratitude"

    def test_recent_returns_ordered(self):
        h = EmotionHistory()
        h.record({"happy": 0.5})
        h.record({"happy": 0.8})
        recent = h.recent(2)
        assert recent[-1]["state"]["happy"] == 0.8

    def test_since(self):
        h = EmotionHistory()
        now = time.time()
        h.record({"happy": 0.5})
        time.sleep(0.01)
        h.record({"happy": 0.8})
        results = h.since(now)
        assert len(results) <= 2

    def test_max_entries(self):
        h = EmotionHistory(max_entries=10)
        for i in range(20):
            h.record({"happy": i / 20})
        assert h.count() == 10

    def test_stats_empty(self):
        h = EmotionHistory()
        s = h.stats()
        assert s["count"] == 0

    def test_stats(self):
        h = EmotionHistory()
        h.record({"happy": 0.5})
        s = h.stats()
        assert s["count"] == 1
        assert s["earliest"] > 0


class TestEmotionTriggerLog:
    def test_init(self):
        t = EmotionTriggerLog()
        assert t.count() == 0

    def test_record(self):
        t = EmotionTriggerLog()
        t.record("modify", "happy += 0.1", {"happy": 0.1}, {"happy": 0.6})
        assert t.count() == 1

    def test_recent(self):
        t = EmotionTriggerLog()
        t.record("modify", "test", {"h": 0.1}, {"h": 0.5})
        t.record("decay", "test", {"h": -0.05}, {"h": 0.45})
        recent = t.recent(2)
        assert len(recent) == 2
        assert recent[0]["type"] == "modify"

    def test_by_type(self):
        t = EmotionTriggerLog()
        t.record("modify", "a", {}, {})
        t.record("decay", "b", {}, {})
        t.record("modify", "c", {}, {})
        by_type = t.by_type("modify")
        assert len(by_type) == 2

    def test_max_entries(self):
        t = EmotionTriggerLog(max_entries=5)
        for i in range(10):
            t.record("test", str(i), {}, {})
        assert t.count() == 5


class TestEmotionProfiles:
    def test_profiles_exist(self):
        assert "neutral" in EMOTION_PROFILES
        assert "happy" in EMOTION_PROFILES
        assert len(EMOTION_PROFILES) >= 5

    def test_find_closest_profile_neutral(self):
        state = {"happy": 0.5, "lonely": 0.3, "annoyed": 0.1,
                 "affection": 0.3, "energy": 0.5, "stress": 0.2}
        assert find_closest_profile(state) == "neutral"

    def test_find_closest_profile_happy(self):
        state = {"happy": 0.9, "lonely": 0.1, "annoyed": 0.05,
                 "affection": 0.7, "energy": 0.8, "stress": 0.1}
        assert find_closest_profile(state) == "happy"

    def test_find_closest_profile_empty(self):
        assert find_closest_profile({}) == "neutral"

    def test_find_closest_profile_lonely(self):
        state = {"happy": 0.1, "lonely": 0.9, "annoyed": 0.2,
                 "affection": 0.1, "energy": 0.2, "stress": 0.5}
        assert find_closest_profile(state) == "lonely"


class TestGoalSubtasks:
    def test_goal_init_no_subtasks(self):
        g = Goal("test goal")
        assert g.subtasks == []
        assert g.progress() == 0.0

    def test_add_subtask(self):
        g = Goal("test")
        s = g.add_subtask("Step 1")
        assert s["description"] == "Step 1"
        assert s["completed"] is False
        assert len(g.subtasks) == 1

    def test_progress_with_subtasks(self):
        g = Goal("test")
        g.add_subtask("Step 1")
        g.add_subtask("Step 2")
        assert g.progress() == 0.0
        g.complete_subtask(g.subtasks[0]["id"])
        assert g.progress() == 0.5
        g.complete_subtask(g.subtasks[1]["id"])
        assert g.progress() == 1.0

    def test_complete_subtask_invalid_id(self):
        g = Goal("test")
        g.add_subtask("Step 1")
        assert g.complete_subtask("invalid") is False

    def test_to_dict_includes_subtasks(self):
        g = Goal("test")
        g.add_subtask("Step 1")
        d = g.to_dict()
        assert "subtasks" in d
        assert "progress" in d
        assert d["progress"] == 0.0

    def test_progress_completed_goal_no_subtasks(self):
        g = Goal("test")
        g.status = "completed"
        assert g.progress() == 1.0

    def test_add_subtask_updates_updated_at(self):
        g = Goal("test")
        old = g.updated_at
        g.add_subtask("Step")
        assert g.updated_at >= old


class TestGoalManagerSubtasks:
    def setup_method(self):
        self.gm = GoalManager()

    def test_add_subtask(self):
        goal = self.gm.create("test goal")
        s = self.gm.add_subtask(goal.id, "Step 1")
        assert s is not None
        assert s["description"] == "Step 1"

    def test_add_subtask_invalid_goal(self):
        s = self.gm.add_subtask("invalid", "step")
        assert s is None

    def test_complete_subtask(self):
        goal = self.gm.create("test")
        sub = self.gm.add_subtask(goal.id, "Step")
        assert self.gm.complete_subtask(goal.id, sub["id"]) is True
        assert self.gm.goal_progress(goal.id) == 1.0

    def test_complete_subtask_invalid_goal(self):
        assert self.gm.complete_subtask("invalid", "sub") is False

    def test_goal_progress_invalid(self):
        assert self.gm.goal_progress("invalid") == 0.0

    def test_stats_includes_avg_progress(self):
        g1 = self.gm.create("goal 1")
        self.gm.add_subtask(g1.id, "Step A")
        self.gm.add_subtask(g1.id, "Step B")
        self.gm.complete_subtask(g1.id, g1.subtasks[0]["id"])
        stats = self.gm.stats()
        assert "avg_progress" in stats


class TestEmotionGoalEngine:
    def setup_method(self):
        self.engine = EmotionGoalEngine()

    def test_suggest_lonely(self):
        suggestions = self.engine.suggest({"lonely": 0.8, "happy": 0.2})
        assert len(suggestions) >= 1
        assert any("conversation" in s["description"].lower() for s in suggestions)

    def test_suggest_stressed(self):
        suggestions = self.engine.suggest({"stress": 0.9, "happy": 0.2})
        assert len(suggestions) >= 1

    def test_suggest_happy(self):
        suggestions = self.engine.suggest({"happy": 0.9, "lonely": 0.1})
        assert len(suggestions) >= 1

    def test_suggest_neutral(self):
        suggestions = self.engine.suggest({"happy": 0.5, "lonely": 0.3, "stress": 0.2})
        assert isinstance(suggestions, list)

    def test_suggest_and_create(self):
        gm = GoalManager()
        engine = EmotionGoalEngine(goal_manager=gm)
        created = engine.suggest_and_create({"lonely": 0.9, "happy": 0.1})
        assert len(created) >= 1
        assert created[0].status == "active"

    def test_suggest_and_create_dedup(self):
        gm = GoalManager()
        engine = EmotionGoalEngine(goal_manager=gm)
        engine.suggest_and_create({"lonely": 0.9})
        count1 = len(gm.list(status="active"))
        engine.suggest_and_create({"lonely": 0.9})
        count2 = len(gm.list(status="active"))
        assert count2 == count1

    def test_suggest_no_goal_manager(self):
        engine = EmotionGoalEngine(goal_manager=None)
        created = engine.suggest_and_create({"lonely": 0.9})
        assert created == []

    def test_reset(self):
        gm = GoalManager()
        engine = EmotionGoalEngine(goal_manager=gm)
        state = {"lonely": 0.9, "happy": 0.1, "stress": 0.2}
        engine.suggest_and_create(state)
        count1 = len(gm.list(status="active"))
        engine.reset()
        engine.suggest_and_create(state)
        count2 = len(gm.list(status="active"))
        assert count2 == count1


class TestEmotionIntegration:
    def test_emotion_has_history(self):
        from core.emotion import Emotion
        e = Emotion()
        e.update("thank you")
        assert e.history.count() >= 1

    def test_emotion_has_profile(self):
        from core.emotion import Emotion
        e = Emotion()
        name = e.profile_name()
        assert isinstance(name, str)
        assert name in e.available_profiles()

    def test_emotion_has_triggers(self):
        from core.emotion import Emotion
        e = Emotion()
        e.update("thank you")
        triggers = e.get_triggers()
        assert len(triggers) >= 0

    def test_push_profile(self):
        from core.emotion import Emotion
        e = Emotion()
        result = e.push_profile("happy")
        assert result is True
        assert e.state["happy"] >= 0.7

    def test_push_profile_invalid(self):
        from core.emotion import Emotion
        e = Emotion()
        result = e.push_profile("nonexistent")
        assert result is False

    def test_push_profile_records_history(self):
        from core.emotion import Emotion
        e = Emotion()
        before = e.history.count()
        e.push_profile("happy")
        assert e.history.count() >= before + 1
