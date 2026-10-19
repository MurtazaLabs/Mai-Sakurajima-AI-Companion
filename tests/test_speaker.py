import os
import tempfile

import numpy as np
import soundfile as sf


def _synthetic_audio(path: str, duration: float = 2.0, sr: int = 16000):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = 0.5 * np.sin(2 * np.pi * 440 * t)
    sf.write(path, tone, sr)


def _synthetic_audio_b(path: str, duration: float = 2.0, sr: int = 16000):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = 0.5 * np.sin(2 * np.pi * 880 * t)
    sf.write(path, tone, sr)


class TestSpeakerProfile:

    def test_create_default(self):
        from voice.speaker.speaker_profile import SpeakerProfile
        p = SpeakerProfile(name="Test")
        assert p.name == "Test"
        assert p.id is not None
        assert p.created > 0
        assert p.last_seen > 0
        assert p.confidence == 0.0
        assert p.sample_count == 0
        assert p.embedding is None

    def test_roundtrip_dict(self):
        from voice.speaker.speaker_profile import SpeakerProfile
        p = SpeakerProfile(name="Alice", embedding=[0.1, 0.2, 0.3])
        d = p.to_dict()
        p2 = SpeakerProfile.from_dict(d)
        assert p2.name == "Alice"
        assert p2.embedding == [0.1, 0.2, 0.3]


class TestSpeakerDatabase:

    def test_save_and_load(self):
        from voice.speaker.speaker_database import SpeakerDatabase
        from voice.speaker.speaker_profile import SpeakerProfile
        with tempfile.TemporaryDirectory() as tmp:
            db = SpeakerDatabase(tmp)
            p = SpeakerProfile(name="Bob", embedding=[0.5, 0.6, 0.7])
            assert db.save(p) is True
            loaded = db.load("Bob")
            assert loaded is not None
            assert loaded.name == "Bob"
            assert loaded.embedding == [0.5, 0.6, 0.7]

    def test_load_missing(self):
        from voice.speaker.speaker_database import SpeakerDatabase
        with tempfile.TemporaryDirectory() as tmp:
            db = SpeakerDatabase(tmp)
            assert db.load("Nobody") is None

    def test_delete(self):
        from voice.speaker.speaker_database import SpeakerDatabase
        from voice.speaker.speaker_profile import SpeakerProfile
        with tempfile.TemporaryDirectory() as tmp:
            db = SpeakerDatabase(tmp)
            db.save(SpeakerProfile(name="Del"))
            assert db.load("Del") is not None
            assert db.delete("Del") is True
            assert db.load("Del") is None

    def test_list_all(self):
        from voice.speaker.speaker_database import SpeakerDatabase
        from voice.speaker.speaker_profile import SpeakerProfile
        with tempfile.TemporaryDirectory() as tmp:
            db = SpeakerDatabase(tmp)
            db.save(SpeakerProfile(name="A"))
            db.save(SpeakerProfile(name="B"))
            assert len(db.list_all()) == 2

    def test_count(self):
        from voice.speaker.speaker_database import SpeakerDatabase
        from voice.speaker.speaker_profile import SpeakerProfile
        with tempfile.TemporaryDirectory() as tmp:
            db = SpeakerDatabase(tmp)
            assert db.count() == 0
            db.save(SpeakerProfile(name="X"))
            assert db.count() == 1

    def test_search_exact_match(self):
        from voice.speaker.speaker_database import SpeakerDatabase
        from voice.speaker.speaker_profile import SpeakerProfile
        with tempfile.TemporaryDirectory() as tmp:
            db = SpeakerDatabase(tmp)
            db.save(SpeakerProfile(name="Alice", embedding=[1.0, 0.0, 0.0]))
            db.save(SpeakerProfile(name="Bob", embedding=[0.0, 1.0, 0.0]))
            profile, score = db.search([1.0, 0.0, 0.0], threshold=0.5)
            assert profile is not None
            assert profile.name == "Alice"
            assert score >= 0.99

    def test_search_no_match(self):
        from voice.speaker.speaker_database import SpeakerDatabase
        from voice.speaker.speaker_profile import SpeakerProfile
        with tempfile.TemporaryDirectory() as tmp:
            db = SpeakerDatabase(tmp)
            db.save(SpeakerProfile(name="Alice", embedding=[1.0, 0.0, 0.0]))
            profile, score = db.search([0.0, 1.0, 0.0], threshold=0.9)
            assert profile is None
            assert score < 0.1

    def test_search_empty_db(self):
        from voice.speaker.speaker_database import SpeakerDatabase
        with tempfile.TemporaryDirectory() as tmp:
            db = SpeakerDatabase(tmp)
            profile, score = db.search([1.0, 0.0, 0.0])
            assert profile is None
            assert score == 0.0


class TestSpeakerManager:

    def test_identify_no_profiles(self):
        from voice.speaker.speaker_manager import SpeakerManager
        with tempfile.TemporaryDirectory() as tmp:
            mgr = SpeakerManager(profiles_dir=tmp)
            profile, score = mgr.identify("nonexistent.wav")
            assert profile is None
            assert score == 0.0

    def test_register_without_encoder(self):
        from unittest.mock import patch

        from voice.speaker.speaker_manager import SpeakerManager
        with tempfile.TemporaryDirectory() as tmp:
            mgr = SpeakerManager(profiles_dir=tmp)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                _synthetic_audio(f.name)
                with patch.object(mgr.encoder, "embed", side_effect=RuntimeError("encoder down")):
                    result = mgr.register("Alice", f.name)
            os.unlink(f.name)
            assert result is None

    def test_stats_empty(self):
        from voice.speaker.speaker_manager import SpeakerManager
        with tempfile.TemporaryDirectory() as tmp:
            mgr = SpeakerManager(profiles_dir=tmp)
            s = mgr.stats()
            assert s["total_speakers"] == 0
            assert "ready" in s

    def test_delete_speaker(self):
        from voice.speaker.speaker_database import SpeakerDatabase
        from voice.speaker.speaker_manager import SpeakerManager
        from voice.speaker.speaker_profile import SpeakerProfile
        with tempfile.TemporaryDirectory() as tmp:
            db = SpeakerDatabase(tmp)
            db.save(SpeakerProfile(name="Bob"))
            mgr = SpeakerManager(profiles_dir=tmp)
            assert mgr.delete("Bob") is True
            assert mgr.delete("Nobody") is False


class TestCosineSimilarity:

    def test_identical(self):
        from voice.speaker.speaker_database import _cosine_similarity
        v = [1.0, 2.0, 3.0]
        assert _cosine_similarity(v, v) > 0.99

    def test_orthogonal(self):
        from voice.speaker.speaker_database import _cosine_similarity
        assert abs(_cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-10

    def test_empty(self):
        from voice.speaker.speaker_database import _cosine_similarity
        assert _cosine_similarity([], [1.0, 2.0]) == 0.0
        assert _cosine_similarity([1.0, 2.0], []) == 0.0
        assert _cosine_similarity([], []) == 0.0

    def test_zero_vector(self):
        from voice.speaker.speaker_database import _cosine_similarity
        assert _cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0
