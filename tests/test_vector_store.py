from memory.vector_store import VectorStore


class TestVectorStoreMetadataWhere:

    def test_single_filter_stays_flat(self):
        where = VectorStore._build_metadata_where({"source": "a.md"})
        assert where == {"source": {"$eq": "a.md"}}

    def test_multi_filter_wrapped_in_and(self):
        where = VectorStore._build_metadata_where(
            {"source": "a.md", "memory_type": "knowledge"}
        )
        assert where == {
            "$and": [
                {"source": {"$eq": "a.md"}},
                {"memory_type": {"$eq": "knowledge"}},
            ]
        }

    def test_multi_filter_has_single_top_level_operator(self):
        where = VectorStore._build_metadata_where(
            {"source": "a.md", "memory_type": "knowledge", "doc_type": "text"}
        )
        assert len(where) == 1
        assert "$and" in where
        assert len(where["$and"]) == 3

    def test_empty_filters_builds_empty_dict(self):
        where = VectorStore._build_metadata_where({})
        assert where == {}


class TestCapCheckThrottle:
    """enforce_cap is O(n) (full collection get) — throttle to every 50th add."""

    def test_runs_only_every_50th_add(self):
        vs = object.__new__(VectorStore)
        calls = []
        vs.enforce_cap = lambda *a, **k: calls.append(1) or 0
        for _ in range(49):
            vs._maybe_enforce_cap()
        assert calls == []
        vs._maybe_enforce_cap()
        assert len(calls) == 1
