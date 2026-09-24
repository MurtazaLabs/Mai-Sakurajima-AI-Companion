# core/state/shared_state.py
import json
import threading
import logging
from pathlib import Path
from core.state.models import (
    EmotionState, RelationshipValues, GoalState, AttentionState, RuntimeStateFields
)
from core.state.db import EvidenceDB

logger = logging.getLogger("Mai.SharedState")

class SharedState:
    def __init__(self, persistence_dir: Path):
        self.lock = threading.RLock()
        self.state_dir = persistence_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the SQLite database for heavy log handling
        self.db = EvidenceDB(self.state_dir)
        
        # Clean, decoupled in-memory sub-states
        self.emotion = EmotionState()
        self.relationship_scores = RelationshipValues()
        self.goals = GoalState()
        self.attention = AttentionState()
        self.runtime = RuntimeStateFields()
        
        self.load_state_from_disk()

    def serialize(self) -> dict:
        with self.lock:
            return {
                "emotion": self.emotion.model_dump(),
                "relationship_scores": self.relationship_scores.model_dump(),
                "goals": self.goals.model_dump(),
                "attention": self.attention.model_dump(),
                "runtime": self.runtime.model_dump()
            }

    def save(self):
        self.save_state_to_disk()

    def save_state_to_disk(self):
        with self.lock:
            try:
                with open(self.state_dir / "master_state.json", "w", encoding="utf-8") as f:
                    json.dump(self.serialize(), f, indent=4)
            except Exception as e:
                logger.error("State Saving Failure: %s", str(e))

    def load_state_from_disk(self):
        with self.lock:
            target_path = self.state_dir / "master_state.json"
            if not target_path.exists():
                return
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "emotion" in data: self.emotion = EmotionState(**data["emotion"])
                if "relationship_scores" in data: self.relationship_scores = RelationshipValues(**data["relationship_scores"])
                if "goals" in data: self.goals = GoalState(**data["goals"])
                if "attention" in data: self.attention = AttentionState(**data["attention"])
                if "runtime" in data: self.runtime = RuntimeStateFields(**data["runtime"])
            except Exception as e:
                logger.error("Failed to recover state: %s", str(e))
