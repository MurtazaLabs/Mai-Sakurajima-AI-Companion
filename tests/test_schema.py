class TestMemoryObject:

    def test_create_defaults(self):
        from memory.schema import MemoryObject
        obj = MemoryObject(content="hello")
        assert obj.content == "hello"
        assert obj.type == "conversation"
        assert obj.confidence == 0.5
        assert obj.importance == 0.5
        assert obj.version == 1
        assert obj.archived is False
        assert obj.consolidated is False
        assert obj.links == []

    def test_round_trip_to_dict(self):
        from memory.schema import MemoryObject
        obj = MemoryObject(
            content="test content",
            memory_type="fact",
            confidence=0.9,
            importance=0.8,
            metadata={"source": "user"},
            links=["id-1", "id-2"],
        )
        d = obj.to_dict()
        restored = MemoryObject.from_dict(d)
        assert restored.content == "test content"
        assert restored.type == "fact"
        assert restored.confidence == 0.9
        assert restored.importance == 0.8
        assert restored.metadata["source"] == "user"
        assert restored.links == ["id-1", "id-2"]
        assert restored.id == obj.id

    def test_from_dict_empty_returns_defaults(self):
        from memory.schema import MemoryObject
        obj = MemoryObject.from_dict({})
        assert obj.content == ""
        assert obj.type == "conversation"
        assert obj.confidence == 0.5

    def test_confidence_clamped(self):
        from memory.schema import MemoryObject
        obj = MemoryObject(content="x", confidence=2.0)
        assert obj.confidence == 1.0
        obj2 = MemoryObject(content="x", confidence=-1.0)
        assert obj2.confidence == 0.0

    def test_embeddings_optional(self):
        from memory.schema import MemoryObject
        obj = MemoryObject(content="x")
        assert obj.embeddings is None
        obj2 = MemoryObject(content="x", embeddings=[0.1, 0.2])
        assert obj2.embeddings == [0.1, 0.2]
