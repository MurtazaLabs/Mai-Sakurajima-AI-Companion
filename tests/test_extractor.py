class TestFastExtractor:

    def setup_method(self):
        from memory.extractor import FastExtractor
        self.extractor = FastExtractor()

    def test_extract_preference(self):
        results = self.extractor.extract("my favorite food is pizza")
        assert len(results) >= 1
        assert any(r.type == "preference" and "pizza" in r.value for r in results)

    def test_extract_like_preference(self):
        results = self.extractor.extract("I like programming")
        assert any(r.type == "preference" and "programming" in r.value for r in results)

    def test_extract_identity(self):
        results = self.extractor.extract("my name is Alex")
        assert any(r.type == "identity" and "Alex" in r.value for r in results)

    def test_extract_employment(self):
        results = self.extractor.extract("I work at Google")
        assert any(r.type == "employment" and "Google" in r.value for r in results)

    def test_extract_location(self):
        results = self.extractor.extract("I live in Pakistan")
        assert any(r.type == "location" and "Pakistan" in r.value for r in results)

    def test_extract_goal(self):
        results = self.extractor.extract("I want to learn Python")
        assert any(r.type == "goal" and "learn Python" in r.value for r in results)

    def test_extract_emotional_state(self):
        results = self.extractor.extract("I feel happy today")
        assert any(r.type == "emotional_state" and "happy" in r.value for r in results)

    def test_extract_empty_input(self):
        results = self.extractor.extract("")
        assert results == []

    def test_extract_none_input(self):
        results = self.extractor.extract(None)
        assert results == []

    def test_extract_no_match(self):
        results = self.extractor.extract("The weather is nice")
        assert results == []

    def test_extract_multiple_from_one_sentence(self):
        results = self.extractor.extract("my name is Alex and I live in Pakistan")
        types = [r.type for r in results]
        assert "identity" in types
        assert "location" in types

    def test_confidence_identity_high(self):
        results = self.extractor.extract("my name is Alex")
        for r in results:
            if r.type == "identity":
                assert r.confidence >= 0.7
