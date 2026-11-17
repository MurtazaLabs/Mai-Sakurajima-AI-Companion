# continuity/tools.py
"""Tool surface of the Continuity Engine.

Small, flat tools over the engine — the LLM can open a project, record what it
decided, promise something with a due window, and checkpoint long work without
having to know anything about internal stores.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _guard(name, handler):
    def wrapped(**kwargs):
        try:
            return handler(**kwargs)
        except ValueError as exc:
            return {"error": str(exc), "tool": name}
        except Exception as exc:
            logger.error("[Continuity] tool %s failed: %s", name, exc)
            return {"error": str(exc), "tool": name}
    return wrapped


def register_continuity_tools(registry, continuity):
    """Register continuity tools on a ToolRegistry (no-op when unavailable)."""
    if registry is None or continuity is None:
        return 0

    engine = continuity

    def _status():
        snapshot = engine.snapshot()
        return {
            "projects": snapshot["projects"],
            "goals": snapshot["goals"],
            "commitments": snapshot["commitments"],
            "checkpoints": snapshot["checkpoints"],
            "focus": snapshot["focus"],
        }

    def _project_open(project_name, summary="", deadline=None, dependencies=None):
        project = engine.projects.create(
            name=project_name, summary=summary, deadline=deadline, dependencies=dependencies,
        )
        if project is None:
            return {"error": "project name is required"}
        return engine.projects.describe(project, include_details=True)

    def _project_update(project_id, status=None, summary=None, next_checkpoint=None,
                        decision=None, question=None, resolve_question=None,
                        blocker=None, clear_blocker=None, step=None, done_step=None):
        project = engine.projects.get(project_id)
        if project is None:
            return {"error": f"unknown project: {project_id}"}

        fields = {}
        if status is not None:
            fields["status"] = status
        if summary is not None:
            fields["summary"] = summary
        if next_checkpoint is not None:
            fields["next_checkpoint"] = next_checkpoint
        if fields:
            if fields.get("status") == "completed":
                engine.projects.complete(project_id)
                fields.pop("status", None)
            if fields:
                engine.projects.update(project_id, **fields)

        if decision:
            engine.projects.record_decision(project_id, decision)
        if question:
            engine.projects.raise_question(project_id, question)
        if blocker:
            engine.projects.add_blocker(project_id, blocker)
        if resolve_question:
            engine.projects.resolve_question(project_id, resolve_question)
        if clear_blocker:
            engine.projects.clear_blocker(project_id, clear_blocker)
        if step:
            engine.projects.add_step(project_id, step)
        if done_step:
            engine.projects.complete_step(project_id, done_step)

        project = engine.projects.get(project_id)
        return engine.projects.describe(project, include_details=True) if project else {"error": "project vanished"}

    def _commitment_add(promise, due_in_hours=None, due_at=None, project_id=None):
        commitment = engine.commitments.add(
            promise=promise,
            due_in_hours=due_in_hours,
            due_at=due_at,
            project_id=project_id,
        )
        if commitment is None:
            return {"error": "promise text is required"}
        return commitment.to_dict()

    def _commitment_resolve(commitment_id, outcome):
        commitment = engine.commitments.resolve(commitment_id, outcome)
        if commitment is None:
            return {"error": f"unknown commitment: {commitment_id}"}
        return commitment.to_dict()

    def _checkpoint(action, task_id, step=None, note="", state=None):
        action = str(action or "").strip().lower()
        if action == "save":
            checkpoint = engine.checkpoints.save(
                task_id=task_id,
                step=step or 0,
                note=note,
                state=state,
            )
            return checkpoint.to_dict() if checkpoint else {"error": "task_id is required"}
        if action == "resume":
            resumed = engine.checkpoints.resume(task_id)
            return resumed or {"error": f"no checkpoint for task: {task_id}"}
        if action == "clear":
            return {"cleared": engine.checkpoints.clear(task_id)}
        return {"error": f"unknown checkpoint action: {action!r} (use save/resume/clear)"}

    registry.register(
        name="continuity_status",
        description="Get what is currently ongoing: projects with progress and blockers, active goals, due and missed commitments, and resumable checkpoints.",
        handler=_guard("continuity_status", _status),
        parameters={},
        category="continuity",
    )

    registry.register(
        name="project_open",
        description="Open a tracked project (goal, status, decisions, blockers, next checkpoint). Creates the backing goal automatically.",
        handler=_guard("project_open", _project_open),
        parameters={
            "project_name": {"type": "string", "description": "Project name"},
            "summary": {"type": "string", "description": "What the project is for"},
            "deadline": {"type": "string", "description": "Optional deadline: ISO date/datetime or relative like 'in 2d'"},
            "dependencies": {"type": "array", "description": "Optional list of things this waits on"},
        },
        category="continuity",
    )

    registry.register(
        name="project_update",
        description="Update a project: status, summary, next checkpoint, record a decision/question/blocker, resolve or clear one, or add/complete a step (progress comes from the goal).",
        handler=_guard("project_update", _project_update),
        parameters={
            "project_id": {"type": "string", "description": "Project id"},
            "status": {"type": "string", "description": "active | paused | blocked | completed | abandoned"},
            "summary": {"type": "string", "description": "Replacement summary"},
            "next_checkpoint": {"type": "string", "description": "Where the work resumes next"},
            "decision": {"type": "string", "description": "A decision taken"},
            "question": {"type": "string", "description": "An open question"},
            "resolve_question": {"type": "string", "description": "Id of an open question to resolve"},
            "blocker": {"type": "string", "description": "A blocker"},
            "clear_blocker": {"type": "string", "description": "Id of a blocker to clear"},
            "step": {"type": "string", "description": "A new step (subtask) to add"},
            "done_step": {"type": "string", "description": "Description of a step to mark complete"},
        },
        category="continuity",
    )

    registry.register(
        name="commitment_add",
        description="Record a promise with a due window, so it is checked later and reported honestly if missed.",
        handler=_guard("commitment_add", _commitment_add),
        parameters={
            "promise": {"type": "string", "description": "What was promised"},
            "due_in_hours": {"type": "number", "description": "Hours from now until due"},
            "due_at": {"type": "string", "description": "Absolute due time (ISO or epoch); alternative to due_in_hours"},
            "project_id": {"type": "string", "description": "Optional project this belongs to"},
        },
        category="continuity",
    )

    registry.register(
        name="commitment_resolve",
        description="Close a commitment as kept, missed, or cancelled.",
        handler=_guard("commitment_resolve", _commitment_resolve),
        parameters={
            "commitment_id": {"type": "string", "description": "Commitment id"},
            "outcome": {"type": "string", "description": "kept | missed | cancelled"},
        },
        category="continuity",
    )

    registry.register(
        name="checkpoint",
        description="Save, resume, or clear a resumable checkpoint for a long task so interrupted work continues instead of restarting.",
        handler=_guard("checkpoint", _checkpoint),
        parameters={
            "action": {"type": "string", "description": "save | resume | clear"},
            "task_id": {"type": "string", "description": "Stable task identifier"},
            "step": {"type": "number", "description": "Step reached (save only)"},
            "note": {"type": "string", "description": "What to do next"},
            "state": {"type": "object", "description": "Arbitrary resumable state"},
        },
        category="continuity",
    )

    return 6
