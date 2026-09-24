# core/tasks.py
import time
import uuid
from threading import RLock


class TaskManager:
    def __init__(self):

        self.tasks = []

        # 🔒 thread safety
        self.lock = RLock()

    # ➕ create task
    def add(
        self,
        description,
        priority=0.5,
        category="general",
        importance=0.5,
        emotional_weight=0.5,
        metadata=None
    ):

        if metadata is None:
            metadata = {}

        task = {
            "id": str(uuid.uuid4()),

            "description": description,

            "status": "pending",

            # ⚡ execution priority
            "priority": round(priority, 2),

            # 🧠 emotional relevance
            "importance": round(importance, 2),

            "emotional_weight": round(
                emotional_weight,
                2
            ),

            "category": category,

            "created_at": time.time(),

            "updated_at": time.time(),

            "completed_at": None,

            "metadata": metadata
        }

        with self.lock:
            self.tasks.append(task)

        return task

    # 📋 get all tasks
    def get_all(self):

        with self.lock:
            return list(self.tasks)

    # ⏳ get pending tasks
    def get_pending(self):

        with self.lock:

            pending = [
                t for t in self.tasks
                if t["status"] == "pending"
            ]

        # 🧠 smart sorting
        pending.sort(
            key=lambda x: (
                x["priority"] * 0.5 +
                x["importance"] * 0.3 +
                x["emotional_weight"] * 0.2
            ),
            reverse=True
        )

        return pending

    # 🔍 find task by id
    def get_task(self, task_id):

        with self.lock:

            for task in self.tasks:

                if task["id"] == task_id:
                    return task

        return None

    # ✅ complete task
    def complete(self, task_id):

        with self.lock:

            task = self.get_task(task_id)

            if not task:
                return False

            task["status"] = "completed"

            task["completed_at"] = time.time()

            task["updated_at"] = time.time()

            return True

    # ❌ cancel task
    def cancel(self, task_id):

        with self.lock:

            task = self.get_task(task_id)

            if not task:
                return False

            task["status"] = "cancelled"

            task["updated_at"] = time.time()

            return True

    # 🧠 update task metadata
    def update_metadata(
        self,
        task_id,
        key,
        value
    ):

        with self.lock:

            task = self.get_task(task_id)

            if not task:
                return False

            task["metadata"][key] = value

            task["updated_at"] = time.time()

            return True

    # ⚡ dynamic emotional updates
    def update_emotional_weight(
        self,
        task_id,
        value
    ):

        with self.lock:

            task = self.get_task(task_id)

            if not task:
                return False

            task["emotional_weight"] = round(
                max(0.0, min(1.0, value)),
                2
            )

            task["updated_at"] = time.time()

            return True

    # 🧠 dynamic importance updates
    def update_importance(
        self,
        task_id,
        value
    ):

        with self.lock:

            task = self.get_task(task_id)

            if not task:
                return False

            task["importance"] = round(
                max(0.0, min(1.0, value)),
                2
            )

            task["updated_at"] = time.time()

            return True

    # 🗑️ remove completed tasks
    def clear_completed(self):

        with self.lock:

            before = len(self.tasks)

            self.tasks = [
                t for t in self.tasks
                if t["status"] != "completed"
            ]

            return before - len(self.tasks)

    # 📊 lightweight stats
    def stats(self):

        with self.lock:

            total = len(self.tasks)

            pending = len([
                t for t in self.tasks
                if t["status"] == "pending"
            ])

            completed = len([
                t for t in self.tasks
                if t["status"] == "completed"
            ])

            cancelled = len([
                t for t in self.tasks
                if t["status"] == "cancelled"
            ])

        return {
            "total": total,
            "pending": pending,
            "completed": completed,
            "cancelled": cancelled
        }