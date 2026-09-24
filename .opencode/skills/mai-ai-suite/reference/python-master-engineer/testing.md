# Testing Intelligence Reference

---

## Core Principle

Untested code is a liability, not an asset. Testability is a design property — if code is hard
to test, the design is wrong. Fix the design, then write the tests.

---

## What to Test (always ask this first)

For any function or class, identify:

```
HAPPY PATH    → Does it produce correct output for valid input?
EDGE CASES    → Empty, None, zero, negative, very large, single-item
FAILURE CASES → What exceptions should it raise, and when?
BOUNDARIES    → At and around the limits of acceptable input
SIDE EFFECTS  → Does it mutate state, write to DB, emit events correctly?
```

---

## Test Structure

Always follow **Arrange → Act → Assert**:

```python
def test_something():
    # Arrange — set up the state
    user = User(id=1, email="test@example.com")
    repo = MockUserRepository()
    repo.save(user)

    # Act — call the thing under test
    result = repo.find_by_email("test@example.com")

    # Assert — verify the outcome
    assert result is not None
    assert result.id == 1
    assert result.email == "test@example.com"
```

---

## Unit Tests

Test a single function or class in isolation. Mock everything external.

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Basic unit test
def test_clean_text_strips_whitespace():
    assert clean_text("  hello  ") == "hello"

def test_clean_text_raises_on_empty():
    with pytest.raises(ValueError, match="cannot be empty"):
        clean_text("")

# Async unit test
@pytest.mark.asyncio
async def test_llm_generate_returns_string():
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="hello"))]
    )
    result = await generate_response(mock_client, "test prompt")
    assert isinstance(result, str)
    assert len(result) > 0
```

---

## Parametrized Tests (test many cases cleanly)

```python
@pytest.mark.parametrize("input,expected", [
    ("hello world", "Hello World"),
    ("", ""),
    ("already Title", "Already Title"),
    ("UPPER", "Upper"),
])
def test_title_case(input, expected):
    assert to_title_case(input) == expected

# Edge cases for numeric functions
@pytest.mark.parametrize("value,should_raise", [
    (5, False),
    (0, True),
    (-1, True),
    (1000, False),
    (None, True),
])
def test_validate_quantity(value, should_raise):
    if should_raise:
        with pytest.raises((ValueError, TypeError)):
            validate_quantity(value)
    else:
        assert validate_quantity(value) == value
```

---

## Fixtures (reusable setup)

```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_llm():
    client = AsyncMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="mock response"))]
    )
    return client

@pytest.fixture
def sample_user():
    return User(id=1, name="Murtaza", email="m@example.com", active=True)

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db

# Use fixtures in tests
async def test_service_uses_llm(mock_llm, sample_user):
    service = ChatService(llm=mock_llm)
    response = await service.respond(sample_user, "hello")
    mock_llm.chat.completions.create.assert_called_once()
    assert response is not None
```

---

## Mocking External Dependencies

**Mock HTTP calls**
```python
from unittest.mock import patch, AsyncMock
import aiohttp

async def test_fetch_does_not_call_real_api():
    mock_response = AsyncMock()
    mock_response.json.return_value = {"result": "ok"}
    mock_response.status = 200

    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.get.return_value\
            .__aenter__.return_value = mock_response
        result = await fetch_data("https://api.example.com/data")

    assert result == {"result": "ok"}
```

**Mock file system**
```python
from unittest.mock import mock_open, patch

def test_read_config_parses_correctly():
    fake_content = '{"model": "qwen2.5:3b", "temperature": 0.7}'
    with patch("builtins.open", mock_open(read_data=fake_content)):
        config = read_config("config.json")
    assert config["model"] == "qwen2.5:3b"
```

**Mock environment variables**
```python
def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("API_KEY", "test-key")
    settings = Settings()
    assert settings.llm_model == "test-model"
    assert settings.api_key == "test-key"
```

---

## Integration Tests

Test multiple components working together. Use real implementations where possible.

```python
@pytest.fixture
def real_db():
    # Use SQLite in-memory for integration tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)

async def test_user_service_creates_and_retrieves(real_db):
    repo = SQLUserRepository(real_db)
    service = UserService(repo)

    user = await service.create_user(CreateUserRequest(
        name="Murtaza",
        email="m@example.com"
    ))

    retrieved = await service.get_user(user.id)
    assert retrieved.email == "m@example.com"
```

---

## AI / Agent Testing Patterns

```python
# Test that LLM is called with correct parameters
async def test_prompt_format(mock_llm):
    service = LLMService(mock_llm, model="qwen2.5:3b")
    await service.ask("test question")

    call_args = mock_llm.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]

    assert any(m["role"] == "system" for m in messages)
    assert messages[-1]["role"] == "user"
    assert "test question" in messages[-1]["content"]

# Test fallback behavior when LLM fails
async def test_llm_fallback_on_timeout(mock_llm):
    mock_llm.chat.completions.create.side_effect = asyncio.TimeoutError()
    service = LLMService(mock_llm, fallback="I couldn't respond right now.")

    result = await service.ask("anything")
    assert result == "I couldn't respond right now."

# Test retry logic
async def test_retries_on_rate_limit(mock_llm):
    from openai import RateLimitError
    mock_llm.chat.completions.create.side_effect = [
        RateLimitError("rate limited", response=MagicMock(), body={}),
        RateLimitError("rate limited", response=MagicMock(), body={}),
        MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))]),
    ]
    result = await service_with_retry.ask("question")
    assert result == "ok"
    assert mock_llm.chat.completions.create.call_count == 3
```

---

## Test Coverage Targets

| Layer | Minimum Target | Why |
|-------|---------------|-----|
| Business logic / domain rules | 90%+ | Core value — must not regress |
| Service layer | 80%+ | Orchestration logic is failure-prone |
| Repository / data layer | 70%+ | I/O has edge cases |
| API / route handlers | 60%+ | Covered partly by integration tests |
| Utilities / helpers | 85%+ | Often reused, changes propagate |
| Infrastructure / wiring | 40%+ | Hard to test, but key paths matter |

---

## Pytest Configuration (recommend adding to project)

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--tb=short --strict-markers -q"

[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/migrations/*"]

[tool.coverage.report]
fail_under = 70
show_missing = true
```

```bash
# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Run only fast unit tests (skip integration)
pytest -m "not integration"

# Run and stop on first failure
pytest -x
```