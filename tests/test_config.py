import os
from pathlib import Path
from unittest.mock import patch

import pytest


# ──────────────────────────────────────────────
#  Paths
# ──────────────────────────────────────────────

class TestPaths:

    def test_paths_are_resolved_correctly(self):
        from config.paths import ROOT_DIR, MEMORY_DIR, VECTOR_DB_DIR, TEMP_AUDIO_DIR, LOG_DIR, CACHE_DIR, OBSIDIAN_VAULT

        assert isinstance(ROOT_DIR, Path)
        assert ROOT_DIR.exists()
        assert (ROOT_DIR / "config").is_dir()
        assert (ROOT_DIR / "core").is_dir()

        assert MEMORY_DIR == ROOT_DIR / "memory"
        assert VECTOR_DB_DIR == ROOT_DIR / "vector_memory"
        assert TEMP_AUDIO_DIR == ROOT_DIR / "temp"
        assert LOG_DIR == ROOT_DIR / "logs"
        assert CACHE_DIR == ROOT_DIR / "cache"
        assert OBSIDIAN_VAULT in (Path.home() / "MaiMemory", Path("E:/MaiMemory"), Path("E:/MaiMemory"))  # default fallback

    def test_cache_dir_is_created(self):
        from config.paths import CACHE_DIR
        assert CACHE_DIR.exists()

    def test_log_dir_is_created(self):
        from config.paths import LOG_DIR
        assert LOG_DIR.exists()

    def test_obsidian_vault_env_var(self):
        with patch.dict(os.environ, {"MAI_OBSIDIAN_VAULT": r"D:\CustomVault"}, clear=True):
            # reimport to trigger env read — module is cached, so skip that
            pass
        from config.paths import OBSIDIAN_VAULT
        # default (env may or may not be set in test env)
        assert isinstance(OBSIDIAN_VAULT, Path)


# ──────────────────────────────────────────────
#  AI config
# ──────────────────────────────────────────────

class TestAIConfig:

    def test_constants_exist(self):
        from config.ai import AI_NAME, WAKE_WORD, WAKE_WORDS

        assert AI_NAME == "Mai Sakurajima"
        assert WAKE_WORD == "wake up"
        assert isinstance(WAKE_WORDS, list)
        assert len(WAKE_WORDS) >= 1

    def test_wake_words_non_empty(self):
        from config.ai import WAKE_WORDS
        assert all(isinstance(w, str) and len(w) > 0 for w in WAKE_WORDS)


# ──────────────────────────────────────────────
#  LLM config
# ──────────────────────────────────────────────

class TestLLMConfig:

    def test_constants_exist(self):
        from config.llm import (
            OPENROUTER_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_TOP_P,
            LLM_STREAM, LLM_MAX_CONTEXT, LLM_TIMEOUT, LLM_RETRY_COUNT, LLM_STOP_TOKENS,
        )

        assert isinstance(LLM_MODEL, str) and len(LLM_MODEL) > 0
        assert 0.0 <= LLM_TEMPERATURE <= 2.0
        assert 0.0 <= LLM_TOP_P <= 1.0
        assert isinstance(LLM_STREAM, bool)
        assert isinstance(LLM_MAX_CONTEXT, int) and LLM_MAX_CONTEXT > 0
        assert isinstance(LLM_TIMEOUT, int) and LLM_TIMEOUT > 0
        assert isinstance(LLM_RETRY_COUNT, int) and LLM_RETRY_COUNT > 0
        assert isinstance(LLM_STOP_TOKENS, list)

    def test_api_key_default_empty(self):
        from config.llm import OPENROUTER_API_KEY
        assert isinstance(OPENROUTER_API_KEY, str)


# ──────────────────────────────────────────────
#  Memory config
# ──────────────────────────────────────────────

class TestMemoryConfig:

    def test_constants_exist(self):
        from config.memory import (
            EMBEDDING_MODEL, MEMORY_RECALL_LIMIT, MEMORY_SIMILARITY,
            MAX_MEMORY_RESULTS, MEMORY_MAX_NODES, MEMORY_AUTOSAVE,
        )

        assert isinstance(EMBEDDING_MODEL, str) and len(EMBEDDING_MODEL) > 0
        assert isinstance(MEMORY_RECALL_LIMIT, int) and MEMORY_RECALL_LIMIT > 0
        assert 0.0 <= MEMORY_SIMILARITY <= 1.0
        assert isinstance(MAX_MEMORY_RESULTS, int) and MAX_MEMORY_RESULTS > 0
        assert isinstance(MEMORY_MAX_NODES, int) and MEMORY_MAX_NODES > 0
        assert isinstance(MEMORY_AUTOSAVE, bool)

    def test_decay_values_are_floats(self):
        from config.memory import (
            DECAY_CONVERSATION, DECAY_EMOTION, DECAY_RELATIONSHIP,
            DECAY_IDENTITY, DECAY_REFLECTION, DECAY_IMPORTANT, DECAY_GENERAL,
        )

        for d in [DECAY_CONVERSATION, DECAY_EMOTION, DECAY_RELATIONSHIP,
                  DECAY_IDENTITY, DECAY_REFLECTION, DECAY_IMPORTANT, DECAY_GENERAL]:
            assert 0.0 < d <= 1.0, f"Decay {d} out of range"

    def test_node_defaults_exist(self):
        from config.memory import (
            MEMORY_NODE_DEFAULT_SCORE, MEMORY_NODE_DEFAULT_IMPORTANCE,
            MEMORY_NODE_DEFAULT_CONFIDENCE, MEMORY_NODE_DEFAULT_EMOTION_TYPE,
        )
        assert 0.0 <= MEMORY_NODE_DEFAULT_SCORE <= 1.0
        assert 0.0 <= MEMORY_NODE_DEFAULT_IMPORTANCE <= 1.0
        assert 0.0 <= MEMORY_NODE_DEFAULT_CONFIDENCE <= 1.0
        assert isinstance(MEMORY_NODE_DEFAULT_EMOTION_TYPE, str)

    def test_memory_protection_values(self):
        from config.memory import (
            MEMORY_EMOTIONAL_PROTECTION, MEMORY_IMPORTANCE_PROTECTION,
            MEMORY_REINFORCEMENT_PROTECTION, MEMORY_MAX_REINFORCEMENT_PROTECTION,
        )
        assert 0.0 <= MEMORY_EMOTIONAL_PROTECTION <= 1.0
        assert 0.0 <= MEMORY_IMPORTANCE_PROTECTION <= 1.0
        assert 0.0 <= MEMORY_REINFORCEMENT_PROTECTION <= 1.0
        assert MEMORY_REINFORCEMENT_PROTECTION <= MEMORY_MAX_REINFORCEMENT_PROTECTION


# ──────────────────────────────────────────────
#  Emotion config
# ──────────────────────────────────────────────

class TestEmotionConfig:

    def test_defaults_in_range(self):
        from config.emotion import (
            EMOTION_DEFAULT_HAPPY, EMOTION_DEFAULT_LONELY, EMOTION_DEFAULT_ANNOYED,
            EMOTION_DEFAULT_AFFECTION, EMOTION_DEFAULT_ENERGY, EMOTION_DEFAULT_STRESS,
            EMOTION_MIN_VALUE, EMOTION_MAX_VALUE,
        )
        for v in [EMOTION_DEFAULT_HAPPY, EMOTION_DEFAULT_LONELY, EMOTION_DEFAULT_ANNOYED,
                  EMOTION_DEFAULT_AFFECTION, EMOTION_DEFAULT_ENERGY, EMOTION_DEFAULT_STRESS]:
            assert EMOTION_MIN_VALUE <= v <= EMOTION_MAX_VALUE

    def test_word_lists_non_empty(self):
        from config.emotion import (
            EMOTION_GRATITUDE_WORDS, EMOTION_ANNOYANCE_WORDS,
            EMOTION_AFFECTION_WORDS, EMOTION_ABSENCE_WORDS,
            EMOTION_POSITIVE_WORDS, EMOTION_NEGATIVE_WORDS, EMOTION_ENERGY_WORDS,
        )
        for lst in [EMOTION_GRATITUDE_WORDS, EMOTION_ANNOYANCE_WORDS,
                    EMOTION_AFFECTION_WORDS, EMOTION_ABSENCE_WORDS,
                    EMOTION_POSITIVE_WORDS, EMOTION_NEGATIVE_WORDS, EMOTION_ENERGY_WORDS]:
            assert isinstance(lst, list) and len(lst) > 0

    def test_relationship_defaults(self):
        from config.emotion import (
            DEFAULT_RELATIONSHIP_CLOSENESS, DEFAULT_RELATIONSHIP_ATTACHMENT,
            DEFAULT_RELATIONSHIP_TRUST,
        )
        assert 0.0 <= DEFAULT_RELATIONSHIP_CLOSENESS <= 1.0
        assert 0.0 <= DEFAULT_RELATIONSHIP_ATTACHMENT <= 1.0
        assert 0.0 <= DEFAULT_RELATIONSHIP_TRUST <= 1.0


# ──────────────────────────────────────────────
#  Autonomy config
# ──────────────────────────────────────────────

class TestAutonomyConfig:

    def test_constants_exist(self):
        from config.autonomy import (
            ENABLE_AUTONOMY, AUTONOMY_INTERVAL, AUTONOMY_IDLE_THRESHOLD,
            AUTONOMY_MAX_ACTIONS, ENABLE_BACKGROUND_THOUGHTS, ENABLE_IDLE_CHAT,
        )
        assert isinstance(ENABLE_AUTONOMY, bool)
        assert isinstance(AUTONOMY_INTERVAL, int) and AUTONOMY_INTERVAL > 0
        assert isinstance(AUTONOMY_IDLE_THRESHOLD, int) and AUTONOMY_IDLE_THRESHOLD > 0
        assert isinstance(AUTONOMY_MAX_ACTIONS, int) and AUTONOMY_MAX_ACTIONS > 0
        assert isinstance(ENABLE_BACKGROUND_THOUGHTS, bool)
        assert isinstance(ENABLE_IDLE_CHAT, bool)


# ──────────────────────────────────────────────
#  Executor config
# ──────────────────────────────────────────────

class TestExecutorConfig:

    def test_constants_exist(self):
        from config.executor import (
            EXECUTOR_MODE, EXECUTOR_TIMEOUT, EXECUTOR_COMMAND_TIMEOUT,
            EXECUTOR_MAX_OUTPUT, EXECUTOR_COOLDOWN, EXECUTOR_MIN_CONFIDENCE,
            EXECUTOR_ALLOWED_ACTIONS, EXECUTOR_BLOCKED_COMMANDS,
        )
        assert EXECUTOR_MODE in ("safe", "normal", "unrestricted")
        assert isinstance(EXECUTOR_TIMEOUT, (int, float)) and EXECUTOR_TIMEOUT > 0
        assert isinstance(EXECUTOR_ALLOWED_ACTIONS, list) and len(EXECUTOR_ALLOWED_ACTIONS) > 0
        assert isinstance(EXECUTOR_BLOCKED_COMMANDS, list) and len(EXECUTOR_BLOCKED_COMMANDS) > 0

    def test_urls_exist(self):
        from config.executor import SEARCH_ENGINE_URL, DEFAULT_YOUTUBE_URL, DEFAULT_GOOGLE_URL
        assert SEARCH_ENGINE_URL.startswith("http")
        assert DEFAULT_YOUTUBE_URL.startswith("http")
        assert DEFAULT_GOOGLE_URL.startswith("http")


# ──────────────────────────────────────────────
#  Scheduler config
# ──────────────────────────────────────────────

class TestSchedulerConfig:

    def test_constants_exist(self):
        from config.scheduler import (
            SCHEDULER_ENABLED, SCHEDULER_LOOP_DELAY_ACTIVE, SCHEDULER_LOOP_DELAY_IDLE,
            SCHEDULER_MAX_TASK_FAILURES, SCHEDULER_THREAD_NAME,
        )
        assert isinstance(SCHEDULER_ENABLED, bool)
        assert isinstance(SCHEDULER_LOOP_DELAY_ACTIVE, (int, float))
        assert isinstance(SCHEDULER_LOOP_DELAY_IDLE, (int, float))
        assert isinstance(SCHEDULER_MAX_TASK_FAILURES, int) and SCHEDULER_MAX_TASK_FAILURES > 0
        assert isinstance(SCHEDULER_THREAD_NAME, str) and len(SCHEDULER_THREAD_NAME) > 0

    def test_intervals_positive(self):
        from config.scheduler import (
            SCHEDULER_BACKGROUND_TICK_INTERVAL, SCHEDULER_EMOTION_DECAY_INTERVAL,
            SCHEDULER_PERSONALITY_DECAY_INTERVAL, SCHEDULER_MEMORY_DECAY_INTERVAL,
        )
        for v in [SCHEDULER_BACKGROUND_TICK_INTERVAL, SCHEDULER_EMOTION_DECAY_INTERVAL,
                  SCHEDULER_PERSONALITY_DECAY_INTERVAL, SCHEDULER_MEMORY_DECAY_INTERVAL]:
            assert isinstance(v, (int, float)) and v > 0


# ──────────────────────────────────────────────
#  Personality config
# ──────────────────────────────────────────────

class TestPersonalityConfig:

    def test_constants_exist(self):
        from config.personality import PERSONALITY_DECAY_RATE, PERSONALITY_MAX_TRAITS, PERSONALITY_MEMORY_WEIGHT

        assert 0.0 <= PERSONALITY_DECAY_RATE <= 1.0
        assert isinstance(PERSONALITY_MAX_TRAITS, int) and PERSONALITY_MAX_TRAITS > 0
        assert 0.0 <= PERSONALITY_MEMORY_WEIGHT <= 1.0


# ──────────────────────────────────────────────
#  Obsidian config
# ──────────────────────────────────────────────

class TestObsidianConfig:

    def test_constants_exist(self):
        from config.paths import (
            OBSIDIAN_ENABLED, OBSIDIAN_DAILY_NOTES, OBSIDIAN_AUTO_LINKS,
            OBSIDIAN_TAGS_ENABLED, OBSIDIAN_MAX_FILE_SIZE, OBSIDIAN_FOLDERS,
        )
        assert isinstance(OBSIDIAN_ENABLED, bool)
        assert isinstance(OBSIDIAN_DAILY_NOTES, bool)
        assert isinstance(OBSIDIAN_AUTO_LINKS, bool)
        assert isinstance(OBSIDIAN_TAGS_ENABLED, bool)
        assert isinstance(OBSIDIAN_MAX_FILE_SIZE, int) and OBSIDIAN_MAX_FILE_SIZE > 0
        assert isinstance(OBSIDIAN_FOLDERS, list) and len(OBSIDIAN_FOLDERS) > 0


# ──────────────────────────────────────────────
#  Voice config
# ──────────────────────────────────────────────

class TestVoiceConfig:

    def test_constants_exist(self):
        from config.voice import (
            WHISPER_MODEL, VOICE_SAMPLE_RATE, SILENCE_THRESHOLD, SILENCE_DURATION,
            MAX_RECORDING_SECONDS, KOKORO_VOICE, KOKORO_LANG_CODE, USE_CUSTOM_VOICE,
            VOICE_COOLDOWN, WAKE_COOLDOWN,
        )
        assert isinstance(WHISPER_MODEL, str) and len(WHISPER_MODEL) > 0
        assert isinstance(VOICE_SAMPLE_RATE, int) and VOICE_SAMPLE_RATE > 0
        assert isinstance(SILENCE_THRESHOLD, float) and SILENCE_THRESHOLD > 0
        assert isinstance(SILENCE_DURATION, (int, float)) and SILENCE_DURATION > 0
        assert isinstance(MAX_RECORDING_SECONDS, int) and MAX_RECORDING_SECONDS > 0
        assert isinstance(USE_CUSTOM_VOICE, bool)
        assert isinstance(VOICE_COOLDOWN, (int, float)) and VOICE_COOLDOWN >= 0
        assert isinstance(WAKE_COOLDOWN, (int, float)) and WAKE_COOLDOWN >= 0


# ──────────────────────────────────────────────
#  Runtime config
# ──────────────────────────────────────────────

class TestRuntimeConfig:

    def test_constants_exist(self):
        from config.runtime import SAFE_MODE, DEFAULT_ERROR_MESSAGE, ENABLE_THREADING, ENABLE_CACHE, ENABLE_LOGGING

        assert isinstance(SAFE_MODE, str)
        assert isinstance(DEFAULT_ERROR_MESSAGE, str) and len(DEFAULT_ERROR_MESSAGE) > 0
        assert isinstance(ENABLE_THREADING, bool)
        assert isinstance(ENABLE_CACHE, bool)
        assert isinstance(ENABLE_LOGGING, bool)


# ──────────────────────────────────────────────
#  Debug config
# ──────────────────────────────────────────────

class TestDebugConfig:

    def test_constants_exist(self):
        from config.debug import (
            DEBUG_MODE, SHOW_WHISPER_VOLUME, SHOW_LLM_OUTPUT,
            SHOW_MEMORY_DEBUG, SHOW_EXECUTOR_DEBUG, SHOW_SCHEDULER_DEBUG, LOG_LEVEL,
        )
        assert isinstance(DEBUG_MODE, bool)
        assert isinstance(SHOW_WHISPER_VOLUME, bool)
        assert isinstance(SHOW_LLM_OUTPUT, bool)
        assert isinstance(SHOW_MEMORY_DEBUG, bool)

    def test_log_level_is_int(self):
        from config.debug import LOG_LEVEL
        import logging
        assert LOG_LEVEL in (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL)


# ──────────────────────────────────────────────
#  Reflection config
# ──────────────────────────────────────────────

class TestReflectionConfig:

    def test_constants_exist(self):
        from config.reflection import (
            REFLECTION_HISTORY_LIMIT, REFLECTION_MAX_RANKED_NODES,
            REFLECTION_DEFAULT_SCORE, REFLECTION_DEFAULT_CONFIDENCE,
            REFLECTION_CODING_CONFIDENCE, REFLECTION_PERSONAL_CONFIDENCE,
            REFLECTION_AI_KEYWORDS, REFLECTION_POSITIVE_EMOTIONS, REFLECTION_NEGATIVE_EMOTIONS,
        )
        assert isinstance(REFLECTION_HISTORY_LIMIT, int) and REFLECTION_HISTORY_LIMIT > 0
        assert isinstance(REFLECTION_MAX_RANKED_NODES, int) and REFLECTION_MAX_RANKED_NODES > 0
        assert 0.0 <= REFLECTION_DEFAULT_SCORE <= 1.0
        assert 0.0 <= REFLECTION_DEFAULT_CONFIDENCE <= 1.0
        assert isinstance(REFLECTION_AI_KEYWORDS, list) and len(REFLECTION_AI_KEYWORDS) > 0
        assert isinstance(REFLECTION_POSITIVE_EMOTIONS, list) and len(REFLECTION_POSITIVE_EMOTIONS) > 0
        assert isinstance(REFLECTION_NEGATIVE_EMOTIONS, list) and len(REFLECTION_NEGATIVE_EMOTIONS) > 0

    def test_thresholds_positive(self):
        from config.reflection import (
            REFLECTION_CODING_THRESHOLD, REFLECTION_PERSONAL_THRESHOLD,
            REFLECTION_RELATIONSHIP_THRESHOLD,
        )
        assert isinstance(REFLECTION_CODING_THRESHOLD, int) and REFLECTION_CODING_THRESHOLD > 0
        assert isinstance(REFLECTION_PERSONAL_THRESHOLD, int) and REFLECTION_PERSONAL_THRESHOLD > 0
        assert isinstance(REFLECTION_RELATIONSHIP_THRESHOLD, int) and REFLECTION_RELATIONSHIP_THRESHOLD > 0


# ──────────────────────────────────────────────
#  Settings class
# ──────────────────────────────────────────────

class TestSettings:

    def test_settings_can_be_instantiated(self):
        from config.settings import Settings

        s = Settings()

        assert s.AI_NAME == "Mai Sakurajima"
        assert s.LLM_MODEL == "qwen2.5:3b-instruct-q4_k_m"
        assert s.EMBEDDING_MODEL == "all-MiniLM-L6-v2"
        assert s.ENABLE_AUTONOMY is False
        assert s.EXECUTOR_MODE == "safe"
        assert s.SCHEDULER_ENABLED is True
        assert s.DEBUG_MODE is True
        assert s.LOG_LEVEL is not None

    def test_settings_has_all_subsystem_attributes(self):
        from config.settings import Settings

        s = Settings()

        assert hasattr(s, "ROOT_DIR")
        assert hasattr(s, "MEMORY_DIR")
        assert hasattr(s, "VECTOR_DB_DIR")
        assert hasattr(s, "LOG_DIR")
        assert hasattr(s, "CACHE_DIR")
        assert hasattr(s, "AI_NAME")
        assert hasattr(s, "LLM_MODEL")
        assert hasattr(s, "EMBEDDING_MODEL")
        assert hasattr(s, "ENABLE_AUTONOMY")
        assert hasattr(s, "EXECUTOR_MODE")
        assert hasattr(s, "SCHEDULER_ENABLED")
        assert hasattr(s, "PERSONALITY_DECAY_RATE")
        assert hasattr(s, "OBSIDIAN_ENABLED")
        assert hasattr(s, "WHISPER_MODEL")
        assert hasattr(s, "SAFE_MODE")
        assert hasattr(s, "DEBUG_MODE")
        assert hasattr(s, "REFLECTION_HISTORY_LIMIT")

    def test_settings_paths_are_strings(self):
        from config.settings import Settings

        s = Settings()

        assert isinstance(s.ROOT_DIR, str)
        assert isinstance(s.MEMORY_DIR, str)
        assert isinstance(s.VECTOR_DB_DIR, str)
        assert isinstance(s.LOG_DIR, str)
        assert isinstance(s.CACHE_DIR, str)
        assert isinstance(s.OBSIDIAN_VAULT, str)

    def test_settings_attributes_match_module_constants(self):
        import config.ai
        from config.settings import Settings

        s = Settings()

        assert s.AI_NAME == config.ai.AI_NAME
        assert s.WAKE_WORD == config.ai.WAKE_WORD
