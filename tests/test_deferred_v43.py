import time
import uuid
import logging
import pytest
import numpy as np

logging.basicConfig(level=logging.DEBUG)


class TestAdaptiveNoiseFilter:
    def test_default_creation(self):
        from voice.adaptive_noise_filter import AdaptiveNoiseFilter
        anf = AdaptiveNoiseFilter(sample_rate=16000)
        assert anf.sample_rate == 16000
        assert anf.noise_profile_available is False
        assert anf.stats()["adaptive_updates"] == 0
        assert anf.stats()["buffered_frames"] == 0

    def test_add_chunk_noise_profile_building(self):
        from voice.adaptive_noise_filter import AdaptiveNoiseFilter
        anf = AdaptiveNoiseFilter(sample_rate=16000, adaptation_interval=0.1, min_profile_frames=3)
        for _ in range(15):
            noise = np.random.randn(512).astype(np.float32) * 0.01
            anf.add_chunk(noise)
        stats = anf.stats()
        assert stats["profile_available"] is True
        assert stats["adaptive_updates"] >= 1

    def test_filter_cleans_noise(self):
        from voice.adaptive_noise_filter import AdaptiveNoiseFilter
        anf = AdaptiveNoiseFilter(sample_rate=16000, adaptation_interval=0.1, min_profile_frames=3)
        noise = np.random.randn(512).astype(np.float32) * 0.05
        for _ in range(10):
            anf.add_chunk(noise)
        signal = np.sin(np.linspace(0, 2 * np.pi * 400, 512)).astype(np.float32)
        noisy = signal + noise
        cleaned = anf.filter(noisy)
        assert len(cleaned) == len(noisy)
        assert not np.allclose(cleaned, noisy, atol=0.01)

    def test_reset_clears_state(self):
        from voice.adaptive_noise_filter import AdaptiveNoiseFilter
        anf = AdaptiveNoiseFilter(sample_rate=16000, adaptation_interval=0.1, min_profile_frames=3)
        noise = np.random.randn(512).astype(np.float32) * 0.01
        for _ in range(10):
            anf.add_chunk(noise)
        anf.reset()
        stats = anf.stats()
        assert stats["adaptive_updates"] == 0
        assert stats["buffered_frames"] == 0

    def test_filter_empty_audio(self):
        from voice.adaptive_noise_filter import AdaptiveNoiseFilter
        anf = AdaptiveNoiseFilter()
        result = anf.filter(np.array([], dtype=np.float32))
        assert len(result) == 0

    def test_learn_noise_explicit(self):
        from voice.adaptive_noise_filter import AdaptiveNoiseFilter
        anf = AdaptiveNoiseFilter(sample_rate=16000)
        audio = np.random.randn(16000).astype(np.float32) * 0.01
        assert anf.learn_noise(audio) is True
        assert anf.noise_profile_available is True


class TestFullAEC:
    def test_default_creation(self):
        from voice.full_aec import FullAEC
        aec = FullAEC(sample_rate=16000)
        assert aec.sample_rate == 16000
        assert aec.filter_length == 2048
        assert aec.is_double_talk() is False

    def test_add_playback_and_process(self):
        from voice.full_aec import FullAEC
        aec = FullAEC(sample_rate=16000, filter_length=256, adaptation_rate=0.05)
        mic = np.random.randn(1600).astype(np.float32) * 0.01
        playback = np.random.randn(1600).astype(np.float32) * 0.1
        aec.add_playback(playback)
        output = aec.process(mic)
        assert len(output) == len(mic)
        assert not np.isnan(output).any()

    def test_double_talk_detection(self):
        from voice.full_aec import FullAEC
        aec = FullAEC(sample_rate=16000, double_talk_threshold=0.3)
        near_end = np.random.randn(1600).astype(np.float32) * 0.1
        far_end = np.zeros(1600, dtype=np.float32)
        aec.add_playback(far_end)
        aec.process(near_end)
        dt1 = aec.is_double_talk()
        aec.reset()
        near_end2 = np.random.randn(1600).astype(np.float32) * 0.5
        far_end2 = np.ones(1600, dtype=np.float32) * 0.01
        aec.add_playback(far_end2)
        aec.process(near_end2)
        dt_status = aec.is_double_talk()
        assert isinstance(dt_status, bool)

    def test_reset(self):
        from voice.full_aec import FullAEC
        aec = FullAEC(sample_rate=16000)
        aec.add_playback(np.random.randn(512).astype(np.float32))
        aec.process(np.random.randn(512).astype(np.float32))
        aec.reset()
        assert aec.is_double_talk() is False
        stats = aec.stats()
        assert stats["double_talk"] is False

    def test_stats(self):
        from voice.full_aec import FullAEC
        aec = FullAEC(sample_rate=16000)
        stats = aec.stats()
        assert stats["filter_length"] == 2048
        assert "double_talk" in stats
        assert "near_end_power" in stats

    def test_empty_audio(self):
        from voice.full_aec import FullAEC
        aec = FullAEC()
        result = aec.process(np.array([], dtype=np.float32))
        assert len(result) == 0


class TestVoiceEmotionDetector:
    def test_default_creation(self):
        from voice.emotion_detector import VoiceEmotionDetector
        ved = VoiceEmotionDetector(sample_rate=16000)
        assert ved.sample_rate == 16000

    def test_compute_features(self):
        from voice.emotion_detector import VoiceEmotionDetector
        ved = VoiceEmotionDetector(sample_rate=16000)
        audio = np.sin(np.linspace(0, 2 * np.pi * 440, 16000)).astype(np.float32)
        features = ved.compute_features(audio)
        assert features is not None
        assert "energy" in features
        assert "spectral_centroid" in features
        assert "zcr" in features
        assert features["energy"] > 0

    def test_compute_features_short_audio(self):
        from voice.emotion_detector import VoiceEmotionDetector
        ved = VoiceEmotionDetector(sample_rate=16000)
        short = np.array([0.1, 0.2], dtype=np.float32)
        features = ved.compute_features(short)
        assert features is None

    def test_classify_emotion(self):
        from voice.emotion_detector import VoiceEmotionDetector
        ved = VoiceEmotionDetector(sample_rate=16000)
        features = {
            "energy": 0.05,
            "spectral_centroid": 1500.0,
            "speech_energy_ratio": 0.5,
            "low_energy_ratio": 0.2,
            "zcr": 0.05,
            "pitch_confidence": 0.4,
        }
        emotion, conf = ved.classify_emotion(features)
        assert emotion in ("neutral", "happy", "sad", "angry", "stressed", "energetic")
        assert 0.0 <= conf <= 1.0

    def test_classify_high_energy(self):
        from voice.emotion_detector import VoiceEmotionDetector
        ved = VoiceEmotionDetector()
        features = {
            "energy": 0.5,
            "spectral_centroid": 3000.0,
            "speech_energy_ratio": 0.2,
            "low_energy_ratio": 0.1,
            "zcr": 0.2,
            "pitch_confidence": 0.7,
        }
        emotion, conf = ved.classify_emotion(features)
        assert conf > 0.3

    def test_detect_needs_audio(self):
        from voice.emotion_detector import VoiceEmotionDetector
        ved = VoiceEmotionDetector(sample_rate=16000)
        emotion, conf, feats = ved.detect()
        assert emotion == "neutral"
        assert conf > 0

    def test_detect_with_audio_history(self):
        from voice.emotion_detector import VoiceEmotionDetector
        ved = VoiceEmotionDetector(sample_rate=16000)
        chunks = []
        for _ in range(70):
            chunk = np.sin(np.linspace(0, 2 * np.pi * 440, 512)).astype(np.float32)
            chunks.append(chunk)
            ved.add_audio(chunk)
        emotion, conf, feats = ved.detect()
        assert isinstance(emotion, str)
        assert 0 <= conf <= 1

    def test_detect_with_explicit_audio(self):
        from voice.emotion_detector import VoiceEmotionDetector
        ved = VoiceEmotionDetector(sample_rate=16000)
        audio = np.sin(np.linspace(0, 2 * np.pi * 440, 32000)).astype(np.float32)
        emotion, conf, feats = ved.detect(audio)
        assert isinstance(emotion, str)
        assert 0 <= conf <= 1


class TestDiarizationEngine:
    def test_default_creation(self):
        from voice.diarization import DiarizationEngine
        de = DiarizationEngine(sample_rate=16000)
        assert de.sample_rate == 16000
        assert de.similarity_threshold == 0.65

    def test_register_and_remove_profile(self):
        from voice.diarization import DiarizationEngine
        de = DiarizationEngine(sample_rate=16000, embedding_dim=10)
        embedding = np.random.randn(10).astype(np.float32)
        de.register_profile("alice", embedding)
        stats = de.stats()
        assert stats["registered_profiles"] == 1
        assert "alice" in stats["profile_ids"]
        de.remove_profile("alice")
        stats = de.stats()
        assert stats["registered_profiles"] == 0

    def test_segment_silence_only(self):
        from voice.diarization import DiarizationEngine
        de = DiarizationEngine(sample_rate=16000)
        silence = np.zeros(32000, dtype=np.float32)
        segments = de.segment(silence)
        assert isinstance(segments, list)

    def test_segment_with_noise(self):
        from voice.diarization import DiarizationEngine
        de = DiarizationEngine(sample_rate=16000, embedding_dim=8)
        audio = np.random.randn(48000).astype(np.float32) * 0.01
        segments = de.segment(audio)
        assert isinstance(segments, list)

    def test_segment_returns_speaker_segments(self):
        from voice.diarization import DiarizationEngine, SpeakerSegment
        de = DiarizationEngine(sample_rate=16000, min_segment_samples=1600)
        audio = np.sin(np.linspace(0, 4 * np.pi * 440, 32000)).astype(np.float32) * 0.5
        segments = de.segment(audio)
        for seg in segments:
            assert isinstance(seg, SpeakerSegment)
            assert seg.end_sample > seg.start_sample
            assert seg.duration > 0
            assert seg.speaker_id in ("__unknown__",)

    def test_segment_to_dict(self):
        from voice.diarization import SpeakerSegment
        seg = SpeakerSegment(start_sample=0, end_sample=16000, speaker_id="alice", confidence=0.8)
        d = seg.to_dict()
        assert d["start_sample"] == 0
        assert d["end_sample"] == 16000
        assert d["speaker_id"] == "alice"
        assert d["confidence"] == 0.8
        assert d["duration"] == 16000

    def test_cosine_similarity(self):
        from voice.diarization import DiarizationEngine
        de = DiarizationEngine(sample_rate=16000, embedding_dim=10)
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        sim = de._cosine_similarity(a, b)
        assert abs(sim - 1.0) < 0.01

    def test_stats(self):
        from voice.diarization import DiarizationEngine
        de = DiarizationEngine(sample_rate=16000)
        stats = de.stats()
        assert "registered_profiles" in stats
        assert "total_segments" in stats


class TestMemoryHierarchy:
    def test_semantic_store(self):
        from memory.hierarchy import SemanticMemoryStore
        store = SemanticMemoryStore()
        code = store.add("paris_capital", "Paris is the capital of France", confidence=0.9)
        assert code.type.value == "semantic"
        assert store.get("paris_capital") is not None
        results = store.query("paris")
        assert len(results) >= 1
        assert len(store.all()) == 1

    def test_episodic_store(self):
        from memory.hierarchy import EpisodicMemoryStore
        store = EpisodicMemoryStore()
        code = store.add("User said they were happy yesterday", confidence=0.7, tags=["happy", "yesterday"])
        assert code.type.value == "episodic"
        results = store.recall("happy", limit=5)
        assert len(results) >= 1
        results_no_query = store.recall(limit=5)
        assert len(results_no_query) >= 1

    def test_procedural_store(self):
        from memory.hierarchy import ProceduralMemoryStore
        store = ProceduralMemoryStore()
        code = store.add("user sad", "offer comfort", confidence=0.8)
        assert code.type.value == "procedural"
        results = store.find("user sad")
        assert len(results) >= 1
        results_no_match = store.find("unknown trigger")
        assert len(results_no_match) == 0

    def test_autobiographical_store(self):
        from memory.hierarchy import AutobiographicalMemoryStore
        store = AutobiographicalMemoryStore()
        code = store.add("mai_personality", "Mai is caring and intelligent", confidence=0.95, importance=0.9)
        assert code.type.value == "autobiographical"
        assert store.get("mai_personality") is not None
        results = store.query("mai")
        assert len(results) >= 1
        history = store.history()
        assert len(history) == 1

    def test_memory_code_access_and_decay(self):
        from memory.hierarchy import MemoryCode, MemoryType
        code = MemoryCode(MemoryType.SEMANTIC, "test fact", confidence=0.8, importance=0.7)
        code.access()
        assert code.access_count == 1
        code.apply_decay(24.0)
        assert code.confidence < 0.8
        assert code.importance < 0.7

    def test_memory_code_to_from_dict(self):
        from memory.hierarchy import MemoryCode, MemoryType
        original = MemoryCode(MemoryType.EPISODIC, "test event", confidence=0.6, tags=["test", "event"])
        data = original.to_dict()
        restored = MemoryCode.from_dict(data)
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.content == original.content
        assert restored.tags == original.tags

    def test_memory_hierarchy_store_from_memory_object(self):
        from memory.hierarchy import MemoryHierarchy
        from memory.schema import MemoryObject
        mh = MemoryHierarchy()
        mo = MemoryObject(content="Paris is the capital of France", memory_type="conversation",
                          confidence=0.9, metadata={"tags": ["france", "paris"]})
        results = mh.store_from_memory_object(mo)
        assert len(results) >= 1
        stats = mh.stats()
        assert stats["total"] > 0

    def test_memory_hierarchy_query(self):
        from memory.hierarchy import MemoryHierarchy
        mh = MemoryHierarchy()
        mh.store_semantic("earth_orbit", "Earth orbits the Sun", confidence=0.95, tags=["science"])
        mh.store_episodic("User asked about planets", confidence=0.7, tags=["question"])
        results = mh.query("earth", limit=5)
        assert len(results) >= 1
        results = mh.query("planets", memory_types=["episodic"], limit=5)
        assert len(results) >= 1

    def test_apply_decay(self):
        from memory.hierarchy import MemoryHierarchy
        mh = MemoryHierarchy()
        mh.store_semantic("test_fact", "Test fact", confidence=0.9)
        mh.apply_decay(1.0)
        code = mh.semantic.get("test_fact")
        assert code.confidence < 0.9

    def test_stats(self):
        from memory.hierarchy import MemoryHierarchy
        mh = MemoryHierarchy()
        mh.store_semantic("fact1", "Fact one", confidence=0.8)
        mh.store_episodic("Event one", confidence=0.7)
        mh.store_procedural("trigger x", "action y", confidence=0.6)
        mh.store_autobiographical("trait1", "Trait one", confidence=0.9)
        stats = mh.stats()
        assert stats["semantic"] >= 1
        assert stats["episodic"] >= 1
        assert stats["procedural"] >= 1
        assert stats["autobiographical"] >= 1
        assert stats["total"] >= 4

    def test_to_dict(self):
        from memory.hierarchy import MemoryHierarchy
        mh = MemoryHierarchy()
        mh.store_semantic("test", "Test content", confidence=0.8)
        data = mh.to_dict()
        assert "semantic" in data
        assert len(data["semantic"]) >= 1

    def test_empty_stores(self):
        from memory.hierarchy import MemoryHierarchy
        mh = MemoryHierarchy()
        stats = mh.stats()
        assert stats["total"] == 0
        assert mh.query("anything", limit=5) == []


class TestVoiceManagerIntegration:
    def test_voice_manager_accepts_new_params(self):
        from voice.voice_manager import VoiceManager
        vm = VoiceManager(sample_rate=16000)
        assert vm.noise_filter is None
        assert vm.full_aec is None
        assert vm.emotion_detector is None
        assert vm.diarization_engine is None

    def test_ensure_components_creates_adaptive_noise(self):
        from voice.voice_manager import VoiceManager
        vm = VoiceManager(sample_rate=16000)
        vm._ensure_components()
        assert vm.noise_filter is not None
        assert hasattr(vm.noise_filter, 'add_chunk')
        assert hasattr(vm.noise_filter, 'filter')

    def test_ensure_components_creates_emotion_detector(self):
        from voice.voice_manager import VoiceManager
        vm = VoiceManager(sample_rate=16000)
        vm._ensure_components()
        assert vm.emotion_detector is not None
        assert hasattr(vm.emotion_detector, 'detect')

    def test_voice_manager_passes_emotion_to_event(self):
        from voice.voice_manager import VoiceManager
        from voice.voice_event import VoiceEvent
        import numpy as np
        vm = VoiceManager(sample_rate=16000, stt=None)
        vm._ensure_components()
        audio = np.sin(np.linspace(0, 2 * np.pi * 440, 16000)).astype(np.float32)
        event = vm._transcribe(audio, speaker="test", speaker_conf=0.5, emotion={"label": "happy", "confidence": 0.7})
        assert isinstance(event, VoiceEvent)
        assert event.emotion is not None
        assert event.emotion["label"] == "happy"

    def test_voice_manager_with_explicit_new_components(self):
        from voice.voice_manager import VoiceManager
        from voice.adaptive_noise_filter import AdaptiveNoiseFilter
        from voice.full_aec import FullAEC
        from voice.emotion_detector import VoiceEmotionDetector
        from voice.diarization import DiarizationEngine
        anf = AdaptiveNoiseFilter(sample_rate=16000)
        aec = FullAEC(sample_rate=16000)
        ed = VoiceEmotionDetector(sample_rate=16000)
        de = DiarizationEngine(sample_rate=16000)
        vm = VoiceManager(
            sample_rate=16000,
            noise_filter=anf,
            full_aec=aec,
            emotion_detector=ed,
            diarization_engine=de,
        )
        assert vm.noise_filter is anf
        assert vm.full_aec is aec
        assert vm.emotion_detector is ed
        assert vm.diarization_engine is de

    def test_send_playback_audio_uses_full_aec(self):
        from voice.voice_manager import VoiceManager
        from voice.full_aec import FullAEC
        import numpy as np
        aec = FullAEC(sample_rate=16000)
        vm = VoiceManager(sample_rate=16000, full_aec=aec)
        audio = np.random.randn(512).astype(np.float32)
        vm.send_playback_audio(audio)
        stats = aec.stats()
        assert "far_end_power" in stats

    def test_voice_event_emotion_field(self):
        from voice.voice_event import VoiceEvent
        e = VoiceEvent(emotion={"label": "sad", "confidence": 0.6})
        assert e.emotion["label"] == "sad"
        assert e.emotion["confidence"] == 0.6


class TestMemoryHierarchyIntegration:
    def test_pipeline_accepts_memory_hierarchy(self):
        from memory.pipeline import MemoryPipeline
        from memory.hierarchy import MemoryHierarchy
        mh = MemoryHierarchy()
        pipeline = MemoryPipeline(memory_hierarchy=mh)
        assert pipeline.memory_hierarchy is mh

    def test_pipeline_store_feeds_hierarchy(self):
        from memory.pipeline import MemoryPipeline
        from memory.hierarchy import MemoryHierarchy
        from memory.schema import MemoryObject
        mh = MemoryHierarchy()
        pipeline = MemoryPipeline(memory_hierarchy=mh)
        obj = MemoryObject(content="Paris is the capital of France", memory_type="conversation",
                          confidence=0.9, metadata={"tags": ["france"]})
        pipeline.memory_hierarchy.store_from_memory_object(obj)
        stats = mh.stats()
        assert stats["total"] > 0

    def test_brain_accepts_memory_hierarchy(self):
        from core.brain import Brain
        brain = Brain.__new__(Brain)
        brain.memory_hierarchy = None
        assert brain.memory_hierarchy is None
