"""Regressions for the "she doesn't remember me" fixes.

Each test pins one root cause that made memory unreadable: frontmatter
importance dropped on replay, the retriever reading the wrong result key,
the 0.65 similarity floor, the pipeline discarding its computed score, flat
semantic importance, no user-identity prompt block, recall replaying Mai's
own denials, and the duplicated timeline rows.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

ENTRY_DOC = """
---
id: aaaa1111
timestamp: 2026-07-15 08:25:56
importance: 0.73
emotion: joy
intensity: 0.8
tags: ['coding']
---

## 🌸 08:25:56

### 👤 User
I use Python for my project

### 🌸 Mai
That tracks.

### 👥 Related Entities
[[python]]

---

id: bbbb2222
timestamp: 2026-07-15 08:26:06
importance: 0.34
emotion: neutral
intensity: 0.3
tags: []
---

## 🌸 08:26:06

### 👤 User
how are you

### 🌸 Mai
Fine.
"""


class TestEntryFrontmatterMerge:
    def test_entries_keep_their_frontmatter_importance(self, tmp_path):
        from knowledge.obsidian_reader import ObsidianReader
        reader = ObsidianReader(vault_path=str(tmp_path))
        entries = reader._extract_entries(ENTRY_DOC)
        assert [e["importance"] for e in entries] == [0.73, 0.34]
        assert entries[0]["tags"] == ["coding"]
        assert entries[0]["emotion"] == "joy"
        assert entries[0]["id"] == "aaaa1111"
        assert entries[1]["user"] == "how are you"

    def test_frontmatter_without_an_entry_is_skipped(self, tmp_path):
        from knowledge.obsidian_reader import ObsidianReader
        reader = ObsidianReader(vault_path=str(tmp_path))
        assert reader._extract_entries("---\nimportance: 0.9\n---\n") == []


IDENTITY_DOC = """
# User Identity

- [name] My name is Murtaza — 2026-11-15
- [name] My name is Mai Sakurajima — 2026-10-19
- [age] I am 20 years old — 2026-09-03
- [work] I work as a software engineer — 2026-09-03
- [general] for me — 2026-09-24

_Updated: 2026-11-15_
"""


class TestUserProfile:
    def test_identity_bullets_parse_into_facts(self, tmp_path):
        from knowledge.obsidian_reader import ObsidianReader
        reader = ObsidianReader(vault_path=str(tmp_path))
        parsed = reader._parse_markdown(IDENTITY_DOC)
        assert len(parsed["facts"]) == 5
        assert parsed["facts"][0] == {
            "category": "name",
            "fact": "My name is Murtaza",
            "timestamp": "2026-11-15",
        }

    def test_profile_drops_assistant_lines_and_chitchat(self, tmp_path):
        from knowledge.obsidian_reader import ObsidianReader
        reader = ObsidianReader(vault_path=str(tmp_path))
        profile = reader._parse_markdown(IDENTITY_DOC)["profile"]
        assert "My name is Murtaza" in profile
        assert "20 years old" in profile
        assert "software engineer" in profile
        assert "Sakurajima" not in profile
        assert "for me" not in profile

    def test_profile_is_bounded(self, tmp_path):
        from knowledge.obsidian_reader import ObsidianReader
        reader = ObsidianReader(vault_path=str(tmp_path))
        doc = "# User Identity\n\n" + "\n".join(
            f"- [background] fact number {i} about my life — 2026-10-02" for i in range(40)
        )
        profile = reader._parse_markdown(doc)["profile"]
        assert len(profile.splitlines()) <= reader._PROFILE_MAX_LINES
        assert len(profile) <= reader._PROFILE_MAX_CHARS

    def test_preferences_file_has_no_profile(self, tmp_path):
        from knowledge.obsidian_reader import ObsidianReader
        reader = ObsidianReader(vault_path=str(tmp_path))
        parsed = reader._parse_markdown("# Preferences\n\n## Likes\n\n- coffee — 2026-11-15\n")
        assert parsed.get("profile") is None

    def test_profile_reaches_the_system_prompt(self):
        from core.prompt_builder import build_system_prompt
        system = build_system_prompt(user_profile="- My name is Murtaza")
        assert "USER PROFILE" in system
        assert "My name is Murtaza" in system


class TestRetrieverResultKey:
    def test_similarity_key_is_used_as_score(self):
        from knowledge.retriever import AdvancedRetriever
        store = MagicMock()
        store.search.return_value = [{"text": "I work as a software engineer", "similarity": 0.62}]
        retriever = AdvancedRetriever(vector_store=store, rerank_enabled=False)
        results = retriever.retrieve("what is my job", top_k=1)
        assert results and results[0]["score"] == 0.62

    def test_threshold_was_lowered_to_the_measured_floor(self):
        from app.config_loader import MEMORY_SIMILARITY_THRESHOLD
        assert MEMORY_SIMILARITY_THRESHOLD <= 0.5


class TestPipelineImportance:
    def test_vector_metadata_uses_computed_importance(self):
        from memory.pipeline import MemoryPipeline
        store = MagicMock()
        store.add.return_value = "vid-1"
        intelligence = MagicMock()
        intelligence.process.return_value = SimpleNamespace(
            tags=["work"], emotion={"type": "neutral"}, importance=0.82,
        )
        pipeline = MemoryPipeline(vector_store=store, intelligence=intelligence)
        pipeline.store("I work as a software engineer", "Noted.")
        metadata = store.add.call_args.kwargs["metadata"]
        assert metadata["importance"] == 0.82

    def test_semantic_importance_is_carried(self):
        from memory.hierarchy import MemoryHierarchy
        mh = MemoryHierarchy()
        code = mh.store_semantic("job", "I work as a software engineer",
                                 confidence=0.6, importance=0.9)
        assert code.importance == 0.9


class TestRecallUserHalf:
    def test_mai_half_is_dropped(self):
        from memory.memory import _user_half
        text = "\nUSER:\ndo you remember me\n\nAI:\nI don't have anything stored from before\n"
        assert _user_half(text) == "do you remember me"

    def test_plain_text_is_untouched(self):
        from memory.memory import _user_half
        assert _user_half("I am 20 years old") == "I am 20 years old"


class TestTimelineDedupe:
    def test_same_turn_appears_once(self):
        from api.routes_memory import MemoryMixin

        class Api(MemoryMixin):
            _ready = True
            brain = SimpleNamespace(
                memory=SimpleNamespace(short=[{
                    "user": "I work as a software engineer",
                    "timestamp": 100.0,
                    "speaker": "Murtaza",
                    "tags": [],
                }])
            )
            memory_hierarchy = MagicMock()
            memory_hierarchy.to_dict.return_value = {
                "episodic": [{
                    "content": "I work as a software engineer",
                    "timestamp": 99.5,
                }],
                "semantic": [{
                    "content": "something else entirely",
                    "timestamp": 50.0,
                }],
            }

        timeline = Api().memory_timeline(limit=10)["timeline"]
        contents = [row["content"] for row in timeline]
        assert contents.count("I work as a software engineer") == 1
        assert "something else entirely" in contents
