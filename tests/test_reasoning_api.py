from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.routes_reasoning import _public_reflection, _public_thought
from api.server import _require_auth, app


def test_public_thought_drops_private_monologue_fields():
    result = _public_thought({
        "id": "trace-1",
        "query": "What do you think?",
        "thought": "private reasoning",
        "decision": "private decision",
        "speech_plan": {"tone": "private"},
        "response": "private response",
        "conclusion": "A safe conclusion",
        "reasoning_steps": ["Reviewed the available context"],
        "retrieved_evidence": [{"content": "A fact"}],
        "known_facts": ["Known fact"],
        "unknowns": ["Unknown"],
        "confidence": 0.8,
        "timestamp": 1710000000,
    })

    assert result["query"] == "What do you think?"
    assert result["conclusion"] == "A safe conclusion"
    assert result["reasoning_steps"] == ["Reviewed the available context"]
    assert "thought" not in result
    assert "speech_plan" not in result
    assert "response" not in result


def test_public_reflection_normalizes_safe_fields():
    result = _public_reflection({
        "period": "daily",
        "summary": "A reflection",
        "patterns": ["pattern"],
        "topics": ["topic"],
        "confidence": 0.6,
        "timestamp": 1710000000,
        "private": "hidden",
    })

    assert result == {
        "period": "daily",
        "summary": "A reflection",
        "patterns": ["pattern"],
        "topics": ["topic"],
        "confidence": 0.6,
        "timestamp": 1710000000,
    }


def test_reasoning_routes_use_auth_dependency():
    def deny():
        raise HTTPException(status_code=401, detail="denied")

    app.dependency_overrides[_require_auth] = deny
    try:
        with TestClient(app) as client:
            response = client.get("/api/reasoning/thoughts")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(_require_auth, None)
