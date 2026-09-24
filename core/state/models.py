# core/state/models.py
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column, String, Float, DateTime, Text, JSON, Index, ForeignKey, Boolean, Integer
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from enum import Enum


class ConversationPhase(str, Enum):
    IDLE = "IDLE"
    WAKE_DETECTED = "WAKE_DETECTED"
    GREETING = "GREETING"
    IDENTIFYING_SPEAKER = "IDENTIFYING_SPEAKER"
    CONFIRMING_SPEAKER = "CONFIRMING_SPEAKER"
    ASKING_NAME = "ASKING_NAME"
    REGISTERING_SPEAKER = "REGISTERING_SPEAKER"
    CONVERSATION = "CONVERSATION"
    PROCESSING_RESPONSE = "PROCESSING_RESPONSE"
    CLEANUP = "CLEANUP"


class KernelMode(str, Enum):
    FOREGROUND = "foreground"
    BACKGROUND = "background"


# Pydantic models for in-memory state
class EmotionState(BaseModel):
    happy: float = 0.5
    sad: float = 0.1
    angry: float = 0.1
    anxious: float = 0.1
    neutral: float = 0.2
    lonely: float = 0.1
    annoyed: float = 0.1
    affection: float = 0.3
    energy: float = 0.5
    stress: float = 0.0
    jealousy: float = 0.0


class RelationshipValues(BaseModel):
    trust: float = 0.5
    comfort: float = 0.5
    respect: float = 0.5
    affection: float = 0.1
    familiarity: float = 0.1


class GoalState(BaseModel):
    active_goals: List[Dict[str, Any]] = Field(default_factory=list)
    completed_goals: List[Dict[str, Any]] = Field(default_factory=list)


class AttentionState(BaseModel):
    current_focus: str = ""
    attention_level: float = 0.5


class RuntimeStateFields(BaseModel):
    is_thinking: bool = False
    last_interaction_time: float = 0.0
    current_session_turns: int = 0
    current_speaker_name: str = ""
    known_user: bool = False
    speaker_confidence: float = 0.0


Base = declarative_base()


class EvidenceModel(Base):
    """SQLAlchemy model for relationship evidence."""
    __tablename__ = "evidence"
    
    evidence_id = Column(String(36), primary_key=True, default=lambda: f"ev_{uuid.uuid4().hex[:8]}")
    timestamp = Column(Float, nullable=False, default=lambda: datetime.utcnow().timestamp())
    event_type = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    dimension_impacts = Column(JSON, nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_evidence_timestamp", "timestamp"),
        Index("ix_evidence_event_type", "event_type"),
    )


class ProfileModel(Base):
    """SQLAlchemy model for user profiles."""
    __tablename__ = "profiles"
    
    profile_id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    display_name = Column(String(100), nullable=True)
    preferences = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sessions = relationship("SessionModel", back_populates="profile", cascade="all, delete-orphan")


class SessionModel(Base):
    """SQLAlchemy model for user sessions."""
    __tablename__ = "sessions"
    
    session_id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    profile_id = Column(String(36), ForeignKey("profiles.profile_id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    session_metadata = Column(JSON, default={})
    
    profile = relationship("ProfileModel", back_populates="sessions")
    
    __table_args__ = (
        Index("ix_sessions_expires_at", "expires_at"),
        Index("ix_sessions_profile_id", "profile_id"),
    )


class MemoryNodeModel(Base):
    """SQLAlchemy model for memory nodes (vector store metadata)."""
    __tablename__ = "memory_nodes"
    
    node_id = Column(String(64), primary_key=True)
    content = Column(Text, nullable=False)
    memory_type = Column(String(50), nullable=False, index=True)
    importance = Column(Float, default=0.5)
    emotion = Column(JSON, default={})
    tags = Column(JSON, default=[])
    speaker = Column(String(50))
    user_id = Column(String(36), index=True)
    vector_id = Column(String(64))
    source = Column(String(255))
    timestamp = Column(Float, default=lambda: datetime.utcnow().timestamp())
    access_count = Column(Float, default=0)
    schema_version = Column(Integer, default=1)
    
    __table_args__ = (
        Index("ix_memory_nodes_memory_type", "memory_type"),
        Index("ix_memory_nodes_user_id", "user_id"),
        Index("ix_memory_nodes_timestamp", "timestamp"),
    )


class RelationshipEvidenceModel(Base):
    """SQLAlchemy model for relationship evidence (PostgreSQL version of EvidenceDB)."""
    __tablename__ = "relationship_evidence"
    
    evidence_id = Column(String(36), primary_key=True, default=lambda: f"ev_{uuid.uuid4().hex[:8]}")
    timestamp = Column(Float, nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    dimension_impacts = Column(JSON, nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_relationship_evidence_timestamp", "timestamp"),
    )


class SharedStateModel(Base):
    """SQLAlchemy model for shared state persistence."""
    __tablename__ = "shared_state"
    
    id = Column(String(36), primary_key=True, default=lambda: "singleton")
    emotion = Column(JSON, nullable=False, default={})
    relationship_scores = Column(JSON, nullable=False, default={})
    goals = Column(JSON, nullable=False, default={})
    attention = Column(JSON, nullable=False, default={})
    runtime = Column(JSON, nullable=False, default={})
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        if "id" not in kwargs:
            kwargs["id"] = "singleton"
        super().__init__(**kwargs)


# Import all models for Alembic
__all__ = [
    "Base",
    "EvidenceModel",
    "ProfileModel", 
    "SessionModel",
    "MemoryNodeModel",
    "RelationshipEvidenceModel",
    "SharedStateModel",
    # Pydantic models
    "EmotionState",
    "RelationshipValues",
    "GoalState",
    "AttentionState",
    "RuntimeStateFields",
]