import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")

from core.event_bus import EventBus


@pytest.fixture(autouse=True)
def _mock_vector_store():
    with patch("memory.memory.VectorStore") as mock:
        mock.return_value.add.return_value = "mock_vector_id"
        yield mock


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def memory_manager():
    from memory.manager import MemoryManager
    from memory.memory import Memory
    from memory.pipeline import MemoryPipeline
    return MemoryManager(
        memory=Memory(
            obsidian_reader=MagicMock(),
            obsidian_writer=MagicMock(),
        ),
        pipeline=MemoryPipeline(event_bus=EventBus()),
        event_bus=EventBus(),
    )
