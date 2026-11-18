"""T4 · Silent Research + Artifacts.

Background research jobs that read the public web invisibly, write a structured
note into the vault, read it back, and report. Nothing here opens a browser
window and nothing acts outside the read-only tier.
"""
from research.engine import ResearchEngine
from research.models import ResearchJob
from research.store import ResearchStore

__all__ = ["ResearchEngine", "ResearchJob", "ResearchStore"]
