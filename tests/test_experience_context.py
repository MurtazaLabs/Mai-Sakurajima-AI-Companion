# M12 · Experience-in-speech — relevance-gated surfacing, human-readable
# format, and prompt guidance for shared moments.

from core.memory_coordinator import MemoryCoordinator, _dice_score, _tokenize
from memory.experience import ExperienceStore


def _reflected_store():
    store = ExperienceStore()
    exp = store.record_event(
        "I missed the deadline today and felt terrible about it",
        significance=0.9,
    )
    store.mark_reflected(
        exp.id,
        meaning="Missed deadlines hit her hard",
        lessons=["Being there when things fall behind matters"],
        growth="Mai stays close when plans slip",
    )
    return store


class TestDiceScoring:

    def test_identical_texts_score_one(self):
        assert _dice_score("the best night", "the best night") == 1.0

    def test_disjoint_texts_score_zero(self):
        assert _dice_score("this song is amazing", "missed the deadline") == 0.0

    def test_partial_overlap(self):
        score = _dice_score(
            "I missed the deadline today",
            "I missed the deadline today and felt terrible about it",
        )
        assert 0.5 < score < 0.9

    def test_stopwords_only_query_scores_zero(self):
        assert _dice_score("the it and", "the best night") == 0.0

    def test_tokenize_removes_stopwords_and_case(self):
        tokens = _tokenize("That Night was AMAZING!")
        assert tokens == ["night", "amazing"]


class TestRelevanceSelection:

    def _coord(self):
        return MemoryCoordinator(memory=None, experience_store=_reflected_store())

    def test_related_query_selects_experience(self):
        text = self._coord().experience_context(
            user_input="I missed the deadline again"
        )
        assert "missed the deadline today" in text

    def test_unrelated_query_injects_nothing(self):
        text = self._coord().experience_context(
            user_input="this song is amazing"
        )
        assert text == ""

    def test_related_older_beats_unrelated_newer(self):
        store = ExperienceStore()
        old = store.record_event("the best night of my life", significance=0.9)
        store.mark_reflected(old.id, meaning="nights together matter",
                             lessons=["presence matters"])
        new = store.record_event("the stock market rally", significance=0.9)
        store.mark_reflected(new.id, meaning="markets move",
                             lessons=["money comes and goes"])
        coord = MemoryCoordinator(memory=None, experience_store=store)
        text = coord.experience_context(user_input="thinking about that night")
        assert "best night" in text
        assert "stock market" not in text

    def test_higher_relevance_ranks_first(self):
        store = ExperienceStore()
        a = store.record_event("deadline at work tomorrow", significance=0.9)
        store.mark_reflected(a.id, meaning="work deadlines matter",
                             lessons=["plan ahead"])
        b = store.record_event("deadline panic last month", significance=0.9)
        store.mark_reflected(b.id, meaning="deadline panic lingers",
                             lessons=["breathe first"])
        coord = MemoryCoordinator(memory=None, experience_store=store)
        text = coord.experience_context(
            user_input="my deadline at work is tomorrow"
        )
        assert text.index("deadline at work") < text.index("deadline panic")

    def test_limit_respected_on_matches(self):
        store = ExperienceStore()
        for i in range(5):
            e = store.record_event(f"deadline day number {i}", significance=0.9)
            store.mark_reflected(e.id, meaning="m", lessons=["l"])
        coord = MemoryCoordinator(memory=None, experience_store=store)
        text = coord.experience_context(user_input="deadline day", limit=2)
        assert text.count("- ") == 2

    def test_before_think_wires_relevance(self):
        coord = self._coord()
        related = coord.before_think("I missed the deadline again")
        assert "missed the deadline today" in related["experiences"]
        unrelated = coord.before_think("hello there friend")
        assert unrelated["experiences"] == ""


class TestLegacyPath:

    def test_no_user_input_keeps_newest_first(self):
        store = ExperienceStore()
        a = store.record_event("older shared night", significance=0.9)
        store.mark_reflected(a.id, meaning="m", lessons=["l"])
        a.timestamp = 1000.0
        b = store.record_event("newer shared night", significance=0.9)
        store.mark_reflected(b.id, meaning="m", lessons=["l"])
        b.timestamp = 2000.0
        coord = MemoryCoordinator(memory=None, experience_store=store)
        text = coord.experience_context()
        assert text.index("newer shared night") < text.index("older shared night")

    def test_caps_still_apply(self):
        coord = MemoryCoordinator(memory=None, experience_store=_reflected_store())
        text = coord.experience_context(user_input="missed the deadline", max_chars=40)
        assert len(text) <= 40


class TestNoMachineryFormat:

    def test_no_scores_or_metadata_in_lines(self):
        text = _reflected_store()
        coord = MemoryCoordinator(memory=None, experience_store=text)
        out = coord.experience_context(user_input="missed the deadline")
        assert "(significance" not in out
        assert "[experience]" not in out
        assert out.startswith("- ")

    def test_lesson_rendered_naturally(self):
        coord = MemoryCoordinator(memory=None, experience_store=_reflected_store())
        out = coord.experience_context(user_input="missed the deadline")
        assert "what it taught me:" in out
        assert "lesson:" not in out


class TestPromptGuidance:

    def test_section_includes_character_instruction(self):
        from prompt.builder import PromptBuilder
        coord = MemoryCoordinator(memory=None, experience_store=_reflected_store())
        out = coord.experience_context(user_input="missed the deadline")
        system = PromptBuilder().build_system(experiences=out)
        assert "EXPERIENTIAL MEMORIES" in system
        assert "Shared moments with the user" in system
        assert "never announcing the memory" in system

    def test_section_absent_without_experiences(self):
        from prompt.builder import PromptBuilder
        system = PromptBuilder().build_system(experiences="")
        assert "EXPERIENTIAL MEMORIES" not in system
