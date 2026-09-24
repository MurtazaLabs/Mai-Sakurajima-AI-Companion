import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestPerPersonRelationshipManager:

    def test_get_default(self):
        from core.state.per_person_relationship import PerPersonRelationshipManager
        with tempfile.TemporaryDirectory() as tmp:
            mgr = PerPersonRelationshipManager(tmp)
            rel = mgr.get("Alice")
            assert rel["trust"] == 0.5
            assert rel["comfort"] == 0.5
            assert rel["affection"] == 0.3
            assert rel["familiarity"] == 0.1

    def test_update_increases_familiarity(self):
        from core.state.per_person_relationship import PerPersonRelationshipManager
        with tempfile.TemporaryDirectory() as tmp:
            mgr = PerPersonRelationshipManager(tmp)
            rel = mgr.update("Bob", familiarity_delta=0.1)
            assert rel["familiarity"] == pytest.approx(0.2, abs=0.01)
            assert rel["trust"] == 0.5

    def test_update_clamps_values(self):
        from core.state.per_person_relationship import PerPersonRelationshipManager
        with tempfile.TemporaryDirectory() as tmp:
            mgr = PerPersonRelationshipManager(tmp)
            rel = mgr.update("Charlie", trust_delta=2.0)
            assert rel["trust"] == 1.0
            rel2 = mgr.update("Charlie", trust_delta=-2.0)
            assert rel2["trust"] == 0.0

    def test_persistence(self):
        from core.state.per_person_relationship import PerPersonRelationshipManager
        with tempfile.TemporaryDirectory() as tmp:
            mgr = PerPersonRelationshipManager(tmp)
            mgr.update("Dave", familiarity_delta=0.2)

            # Create a new manager reading same dir
            mgr2 = PerPersonRelationshipManager(tmp)
            rel = mgr2.get("Dave")
            assert rel["familiarity"] == pytest.approx(0.3, abs=0.01)

    def test_list_all(self):
        from core.state.per_person_relationship import PerPersonRelationshipManager
        with tempfile.TemporaryDirectory() as tmp:
            mgr = PerPersonRelationshipManager(tmp)
            mgr.update("Alice")
            mgr.update("Bob")
            assert len(mgr.list_all()) == 2

    def test_stats(self):
        from core.state.per_person_relationship import PerPersonRelationshipManager
        with tempfile.TemporaryDirectory() as tmp:
            mgr = PerPersonRelationshipManager(tmp)
            mgr.update("Alice")
            s = mgr.stats()
            assert s["total"] == 1

    def test_delete(self):
        from core.state.per_person_relationship import PerPersonRelationshipManager
        with tempfile.TemporaryDirectory() as tmp:
            mgr = PerPersonRelationshipManager(tmp)
            mgr.update("Eve")
            assert mgr.delete("Eve") is True
            assert mgr.delete("Eve") is False
            assert mgr.delete("Nobody") is False


class TestUserProfiles:

    def test_get_default(self):
        from core.identity.profiles import get_profile, delete_profile
        profile = get_profile("TestUser")
        assert profile["name"] == "TestUser"
        assert profile["interaction_count"] == 0
        assert profile["known_facts"] == []
        delete_profile("TestUser")

    def test_update_profile(self):
        from core.identity.profiles import get_profile, update_profile, delete_profile
        update_profile("TestUser", mood="happy")
        profile = get_profile("TestUser")
        assert profile["mood"] == "happy"
        assert profile["interaction_count"] == 1
        delete_profile("TestUser")

    def test_add_fact(self):
        from core.identity.profiles import get_profile, add_fact, delete_profile
        add_fact("TestUser", "likes anime")
        profile = get_profile("TestUser")
        assert "likes anime" in profile["known_facts"]
        delete_profile("TestUser")

    def test_add_preference(self):
        from core.identity.profiles import get_profile, add_preference, delete_profile
        add_preference("TestUser", "likes", "pizza")
        profile = get_profile("TestUser")
        assert "pizza" in profile["preferences"]["likes"]
        delete_profile("TestUser")

    def test_list_profiles(self):
        from core.identity.profiles import update_profile, list_profiles, delete_profile
        update_profile("UserA")
        update_profile("UserB")
        profiles = list_profiles()
        assert "UserA" in profiles
        assert "UserB" in profiles
        delete_profile("UserA")
        delete_profile("UserB")


class TestMemorySpeakerTagging:

    def test_memory_store_accepts_speaker(self):
        from memory.memory import Memory
        mem = Memory()
        mem.tagger = MagicMock()
        mem.tagger.extract_tags.return_value = ["test"]
        mem.emotion = MagicMock()
        mem.emotion.analyze.return_value = {"type": "neutral", "intensity": 0.5}
        mem.rel_updater = MagicMock()
        mem.intel = MagicMock()
        mem.intel.process.return_value = MagicMock()
        mem.intel.process.return_value.score = 0.5
        mem.vector = MagicMock()
        mem.vector.add.return_value = "vec_123"
        mem.router = MagicMock()
        mem.router.route.return_value = {"routes": ["test"]}
        mem.writer = MagicMock()
        mem.event_bus = MagicMock()

        node = mem.store("I am excited about machine learning — it's important to me", "That's great!", speaker="Murtaza")
        assert node is not None

        # Verify speaker in short-term memory
        assert mem.short[-1]["speaker"] == "Murtaza"

        # Verify speaker in vector metadata
        call_kwargs = mem.vector.add.call_args[1]
        assert call_kwargs["metadata"]["speaker"] == "Murtaza"

        # Verify speaker in event
        event_msg = mem.event_bus.publish_message.call_args[0][0]
        assert event_msg.payload["speaker"] == "Murtaza"

    def test_memory_store_default_speaker(self):
        from memory.memory import Memory
        mem = Memory()
        mem.tagger = MagicMock()
        mem.tagger.extract_tags.return_value = ["test"]
        mem.emotion = MagicMock()
        mem.emotion.analyze.return_value = {"type": "neutral", "intensity": 0.5}
        mem.rel_updater = MagicMock()
        mem.intel = MagicMock()
        mem.intel.process.return_value = MagicMock()
        mem.intel.process.return_value.score = 0.5
        mem.vector = MagicMock()
        mem.vector.add.return_value = "vec_123"
        mem.router = MagicMock()
        mem.router.route.return_value = {"routes": ["test"]}
        mem.writer = MagicMock()
        mem.event_bus = MagicMock()

        node = mem.store("I am excited about machine learning — it's important to me", "That's great!")
        assert node is not None
        assert mem.short[-1]["speaker"] == "User"
        call_kwargs = mem.vector.add.call_args[1]
        assert call_kwargs["metadata"]["speaker"] == "User"


class TestRetrieverSpeakerFilter:

    def test_filter_by_speaker(self):
        from knowledge.retriever import AdvancedRetriever
        vector_store = MagicMock()
        vector_store.search.return_value = [
            {"text": "Hello from Alice", "score": 0.9, "metadata": {"speaker": "Alice"}},
            {"text": "Hello from Bob", "score": 0.8, "metadata": {"speaker": "Bob"}},
            {"text": "Hello from Alice again", "score": 0.7, "metadata": {"speaker": "Alice"}},
            {"text": "No speaker tag", "score": 0.6, "metadata": {}},
        ]

        retriever = AdvancedRetriever(vector_store=vector_store)
        results = retriever.retrieve("hello", speaker="Alice")
        # Alice's entries + legacy entry with no speaker tag
        assert len(results) == 3
        assert any("Alice" in r["content"] for r in results)

    def test_no_filter_when_speaker_none(self):
        from knowledge.retriever import AdvancedRetriever
        vector_store = MagicMock()
        vector_store.search.return_value = [
            {"text": "Hello from Alice", "score": 0.9, "metadata": {"speaker": "Alice"}},
            {"text": "Hello from Bob", "score": 0.8, "metadata": {"speaker": "Bob"}},
        ]

        retriever = AdvancedRetriever(vector_store=vector_store)
        results = retriever.retrieve("hello")
        assert len(results) == 2


class TestOSKernelSpeakerWiring:

    @patch("core.os_kernel.Attention")
    @patch("core.os_kernel.Cognition")
    @patch("core.os_kernel.IdleBehavior")
    @patch("core.os_kernel.Scheduler")
    @patch("core.os_kernel.Autonomy")
    @patch("core.os_kernel.WakeGenerator")
    @patch("core.os_kernel._get_identity")
    def test_kernel_passes_speaker_to_memory(self, mock_identity, mock_wg,
                                              mock_auto, mock_sched, mock_idle,
                                              mock_cog, mock_attn):
        from core.os_kernel import AIOSKernel
        brain = MagicMock()
        brain.emotion = MagicMock()
        brain.memory = MagicMock()
        brain.executor = MagicMock()
        brain.personality_state = MagicMock()
        voice = MagicMock()
        wake = MagicMock()
        stt = MagicMock()
        state = MagicMock()
        state.runtime.current_speaker_name = "Murtaza"
        state.runtime.known_user = True
        relationship_engine = MagicMock()

        kernel = AIOSKernel(
            brain=brain,
            voice=voice,
            wake=wake,
            stt=stt,
            state=state,
            relationship_engine=relationship_engine,
        )
        assert kernel.per_person_relationship is None

    @patch("core.os_kernel.Attention")
    @patch("core.os_kernel.Cognition")
    @patch("core.os_kernel.IdleBehavior")
    @patch("core.os_kernel.Scheduler")
    @patch("core.os_kernel.Autonomy")
    @patch("core.os_kernel.WakeGenerator")
    @patch("core.os_kernel._get_identity")
    def test_kernel_with_per_person_relationship(self, mock_identity, mock_wg,
                                                  mock_auto, mock_sched, mock_idle,
                                                  mock_cog, mock_attn):
        from core.os_kernel import AIOSKernel
        from core.state.per_person_relationship import PerPersonRelationshipManager
        with tempfile.TemporaryDirectory() as tmp:
            brain = MagicMock()
            brain.emotion = MagicMock()
            brain.memory = MagicMock()
            brain.executor = MagicMock()
            brain.personality_state = MagicMock()
            voice = MagicMock()
            wake = MagicMock()
            stt = MagicMock()
            state = MagicMock()
            state.runtime.current_speaker_name = "Murtaza"
            relationship_engine = MagicMock()
            per_rel = PerPersonRelationshipManager(tmp)

            kernel = AIOSKernel(
                brain=brain,
                voice=voice,
                wake=wake,
                stt=stt,
                state=state,
                relationship_engine=relationship_engine,
                per_person_relationship=per_rel,
            )
            assert kernel.per_person_relationship is per_rel
