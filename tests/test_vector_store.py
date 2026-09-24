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
