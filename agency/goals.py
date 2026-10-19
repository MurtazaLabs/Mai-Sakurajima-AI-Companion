import logging
import threading
import time
import uuid

logger = logging.getLogger(__name__)


class Goal:

    def __init__(self, description, priority="normal", context=None, goal_id=None):
        self.id = goal_id or str(uuid.uuid4())
        self.description = str(description).strip()
        self.priority = priority if priority in ("high", "normal", "low") else "normal"
        self.status = "pending"
        self.context = dict(context or {})
        self.created_at = time.time()
        self.updated_at = time.time()
        self.completed_at = 0.0
        self.turn_count = 0
        self.subtasks = []

    def add_subtask(self, description):
        subtask = {
            "id": str(uuid.uuid4()),
            "description": str(description).strip(),
            "completed": False,
            "created_at": time.time(),
        }
        self.subtasks.append(subtask)
        self.updated_at = time.time()
        return subtask

    def complete_subtask(self, subtask_id):
        for s in self.subtasks:
            if s["id"] == subtask_id and not s["completed"]:
                s["completed"] = True
                self.updated_at = time.time()
                return True
        return False

    def auto_advance(self):
        if self.status == "completed":
            return None
        for s in self.subtasks:
            if not s["completed"]:
                return None
        self.status = "completed"
        self.completed_at = time.time()
        self.updated_at = time.time()
        return self

    def progress(self):
        if not self.subtasks:
            return 1.0 if self.status == "completed" else 0.0
        done = sum(1 for s in self.subtasks if s["completed"])
        return done / len(self.subtasks)

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "context": dict(self.context),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "turn_count": self.turn_count,
            "subtasks": list(self.subtasks),
            "progress": round(self.progress(), 3),
        }


class GoalManager:

    def __init__(self, event_bus=None, brain_graph=None, emotion=None, learning_engine=None):
        self._lock = threading.RLock()
        self._goals = {}
        self.event_bus = event_bus
        self.brain_graph = brain_graph
        self.emotion = emotion
        self._learning_engine = learning_engine
        self._max_active = 5

    def _adjusted_priority(self, priority):
        if not self.emotion:
            return priority
        try:
            mult = self.emotion.influence("goal_priority")
            value = {"low": 0, "normal": 1, "high": 2}
            rev = {0: "low", 1: "normal", 2: "high"}
            base = value.get(priority, 1)
            adjusted = base * mult
            if adjusted >= 1.5:
                return "high"
            elif adjusted < 0.7:
                return "low"
            return "normal"
        except Exception as e:
            logger.warning("[Goals] priority adjustment: %s", e)
            return priority

    def _insert_goal(self, goal):
        """Shared insert path: enforces the max-active cap (pausing the
        lowest-priority excess goal) and publishes creation events.

        Used by ``create()`` and ``check_goals()`` so belief-derived goals
        get identical cap enforcement and event fan-out (A-7)."""
        with self._lock:
            active = [g for g in self._goals.values() if g.status == "active"]
            if len(active) >= self._max_active:
                lowest = max(active, key=lambda g: ("high", "normal", "low").index(g.priority) if g.priority in ("high", "normal", "low") else 1)
                lowest.status = "paused"
                logger.info("[Goals] Paused excess goal: %s", lowest.description[:40])
            goal.status = "active"
            self._goals[goal.id] = goal
        if self.brain_graph:
            self.brain_graph.add_goal_node(
                goal_id=goal.id,
                description=goal.description,
                priority=goal.priority,
                status=goal.status,
                context=goal.context,
            )
        if self.event_bus:
            from core.event_specs import GOAL_CREATED, STATE_GOAL_UPDATED
            from core.mai_message import publish_event
            publish_event(self.event_bus, GOAL_CREATED, goal.to_dict(), source="agency")
            publish_event(self.event_bus, STATE_GOAL_UPDATED, goal.to_dict(), source="agency")
        return goal

    def create(self, description, priority="normal", context=None):
        if not description:
            return None
        priority = self._adjusted_priority(priority)
        goal = Goal(description, priority=priority, context=context)
        return self._insert_goal(goal)

    def get(self, goal_id):
        with self._lock:
            return self._goals.get(goal_id)

    def list(self, status=None):
        with self._lock:
            goals = list(self._goals.values())
            if status:
                goals = [g for g in goals if g.status == status]
            goals.sort(key=lambda g: ("high", "normal", "low").index(g.priority) if g.priority in ("high", "normal", "low") else 1)
            return goals

    def complete(self, goal_id):
        with self._lock:
            goal = self._goals.get(goal_id)
            if not goal or goal.status == "completed":
                return False
            goal.status = "completed"
            goal.completed_at = time.time()
            goal.updated_at = time.time()
        if self.brain_graph:
            self.brain_graph.update_goal_node(goal_id, status="completed")
        if self.event_bus:
            from core.event_specs import GOAL_COMPLETED, STATE_GOAL_UPDATED
            from core.mai_message import publish_event
            publish_event(self.event_bus, GOAL_COMPLETED, goal.to_dict(), source="agency")
            publish_event(self.event_bus, STATE_GOAL_UPDATED, goal.to_dict(), source="agency")
        self._trigger_completion_reflection(goal)
        if self._learning_engine:
            try:
                self._learning_engine.adjust_behavior([f"Completed goal: {goal.description}"])
            except Exception as e:
                logger.warning("[Goals] adjust_behavior: %s", e)
        return True

    def _trigger_completion_reflection(self, goal):
        if not self.event_bus:
            return
        try:
            from core.event_specs import GOAL_COMPLETED_REFLECTION
            from core.mai_message import publish_event
            publish_event(self.event_bus, GOAL_COMPLETED_REFLECTION, {
                "description": goal.description,
                "priority": goal.priority,
                "progress": goal.progress(),
                "subtask_count": len(goal.subtasks),
                "turn_count": goal.turn_count,
            }, source="agency")
        except Exception as e:
            logger.debug("[Goals] Completion reflection: %s", e)

    def activate(self, goal_id):
        with self._lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return False
            goal.status = "active"
            goal.updated_at = time.time()
        return True

    def cancel(self, goal_id):
        with self._lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return False
            goal.status = "cancelled"
            goal.updated_at = time.time()
        if self.event_bus:
            from core.event_specs import GOAL_CANCELLED, STATE_GOAL_UPDATED
            from core.mai_message import publish_event
            publish_event(self.event_bus, GOAL_CANCELLED, goal.to_dict(), source="agency")
            publish_event(self.event_bus, STATE_GOAL_UPDATED, goal.to_dict(), source="agency")
        return True

    def due_for_bringup(self, max_turns=5):
        with self._lock:
            active = [g for g in self._goals.values() if g.status == "active"]
            due = [g for g in active if g.turn_count >= max_turns]
            due.sort(key=lambda g: ("high", "normal", "low").index(g.priority) if g.priority in ("high", "normal", "low") else 1)
            return due

    def increment_turns(self, goal_id=None):
        with self._lock:
            if goal_id:
                goal = self._goals.get(goal_id)
                if goal:
                    goal.turn_count += 1
                    goal.updated_at = time.time()
                    if self.brain_graph:
                        self.brain_graph.update_goal_node(goal_id, turn_count=goal.turn_count)
            else:
                for g in self._goals.values():
                    if g.status == "active":
                        g.turn_count += 1

    def add_subtask(self, goal_id, description):
        with self._lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return None
            subtask = goal.add_subtask(description)
            goal.updated_at = time.time()
        if self.brain_graph:
            self.brain_graph.update_goal_node(goal_id, progress=goal.progress())
        return subtask

    def complete_subtask(self, goal_id, subtask_id):
        with self._lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return False
            result = goal.complete_subtask(subtask_id)
            if result:
                goal.updated_at = time.time()
                completed_goal = goal.auto_advance()
                if completed_goal and self.event_bus:
                    from core.event_specs import GOAL_AUTO_COMPLETED, STATE_GOAL_UPDATED
                    from core.mai_message import publish_event
                    publish_event(self.event_bus, GOAL_AUTO_COMPLETED, goal.to_dict(), source="agency")
                    publish_event(self.event_bus, STATE_GOAL_UPDATED, goal.to_dict(), source="agency")
                    self._trigger_completion_reflection(goal)
        if result and self.brain_graph:
            self.brain_graph.update_goal_node(goal_id, progress=goal.progress())
        return result

    def goal_progress(self, goal_id):
        with self._lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return 0.0
            return goal.progress()

    def check_goals(self, beliefs):
        if not beliefs:
            return {"created": 0, "adjusted": 0, "details": []}
        results = {"created": 0, "adjusted": 0, "details": []}
        with self._lock:
            # Check ALL goals (not just active) to prevent duplicates
            all_descriptions = {g.description.lower() for g in self._goals.values()}
            active = [g for g in self._goals.values() if g.status == "active"]
            pending_create = []
            for b in beliefs:
                topic = b.get("topic", "").lower().strip()
                obj = b.get("object", "").strip()
                predicate = b.get("predicate", "").strip()
                if not topic or not obj:
                    continue
                desc = f"Learn more about {topic}"
                if desc.lower() in all_descriptions:
                    continue
                pending_create.append(
                    Goal(description=desc, priority="low",
                         context={"source": "belief_check", "topic": topic, "predicate": predicate, "object": obj})
                )
        # Route through the shared insert path: cap enforcement + events (A-7)
        for goal in pending_create:
            self._insert_goal(goal)
            results["created"] += 1
            results["details"].append({"action": "created", "goal": goal.description})
        with self._lock:
            active = [g for g in self._goals.values() if g.status == "active"]
            for b in beliefs:
                topic = b.get("topic", "").lower().strip()
                if not topic:
                    continue
                for g in active:
                    if topic in g.description.lower():
                        g.priority = self._adjusted_priority("normal")
                        g.updated_at = time.time()
                        if self.brain_graph:
                            self.brain_graph.update_goal_node(g.id, progress=g.progress())
                        if self.event_bus:
                            from core.event_specs import STATE_GOAL_UPDATED
                            from core.mai_message import publish_event
                            publish_event(self.event_bus, STATE_GOAL_UPDATED, g.to_dict(), source="agency")
                        results["adjusted"] += 1
                        results["details"].append({"action": "boosted", "goal": g.description})
        return results

    def stats(self):
        with self._lock:
            total = len(self._goals)
            active = sum(1 for g in self._goals.values() if g.status == "active")
            completed = sum(1 for g in self._goals.values() if g.status == "completed")
            pending = sum(1 for g in self._goals.values() if g.status == "pending")
            avg_progress = 0.0
            active_goals = [g for g in self._goals.values() if g.status == "active"]
            if active_goals:
                avg_progress = round(sum(g.progress() for g in active_goals) / len(active_goals), 3)
            detail = []
            for g in active_goals:
                detail.append({
                    "description": g.description[:50],
                    "priority": g.priority,
                    "progress": round(g.progress(), 3),
                    "subtask_count": len(g.subtasks),
                    "done_subtasks": sum(1 for s in g.subtasks if s["completed"]),
                    "turn_count": g.turn_count,
                })
            return {
                "total": total,
                "active": active,
                "completed": completed,
                "pending": pending,
                "avg_progress": avg_progress,
                "goals": detail,
            }
