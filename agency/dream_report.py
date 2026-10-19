"""Dream report model and level→task catalog for the DreamEngine.

Extracted from ``agency.dreaming`` so the engine orchestrator stays small and
the task definitions are independently importable/testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DreamReport:
    level: int
    tasks_run: list[str] = field(default_factory=list)
    orphans_found: int = 0
    duplicates_merged: int = 0
    knowledge_merged: int = 0
    links_created: int = 0
    conversations_compressed: int = 0
    relationships_built: int = 0
    importance_recalculated: int = 0
    reflections_generated: int = 0
    knowledge_discovered: int = 0
    emotional_reflections: int = 0
    archived: int = 0
    graph_optimized: bool = False
    digest_created: bool = False
    contradictions_found: int = 0
    pages_split: int = 0
    patterns_discovered: int = 0
    experiences_reflected: int = 0
    errors: list[str] = field(default_factory=list)
    duration: float = 0.0


LEVEL_1_TASKS = ["orphans", "merge_duplicates", "merge_knowledge", "link_notes"]
LEVEL_2_TASKS = ["importance", "relationship_building", "conversation_compression"]
LEVEL_3_TASKS = ["reflections", "knowledge_discovery", "emotional_reflection", "contradictions"]
LEVEL_4_TASKS = ["archive_stale", "graph_optimization", "importance_full", "weekly_digest",
                "split_giant", "patterns"]
LEVEL_5_TASKS = ["experience_reflection"]

LEVEL_TASKS = {1: LEVEL_1_TASKS, 2: LEVEL_2_TASKS, 3: LEVEL_3_TASKS, 4: LEVEL_4_TASKS,
               5: LEVEL_5_TASKS}

LINK_CO_OCCUR_THRESHOLD = 5
ARCHIVE_DAYS = 90
ARCHIVE_IMPORTANCE = 0.2
INFERRED_CONFIDENCE = 0.8
