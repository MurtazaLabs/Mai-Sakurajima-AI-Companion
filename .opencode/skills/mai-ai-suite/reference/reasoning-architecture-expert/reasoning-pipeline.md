# Reasoning Pipeline

## Stage Interfaces

```python
@dataclass
class ReasoningInput:
    message: str
    conversation_id: str
    user_id: str
    timestamp: float
    intent: Intent | None = None

@dataclass
class ReasoningContext:
    conversation_history: list[Message]
    memories: list[MemoryObject]
    world_model: WorldModelState
    user_preferences: UserPreferences
    goals: list[Goal]
    active_plan: Plan | None = None

@dataclass  
class ReasoningOutput:
    response: str
    confidence: float
    tool_calls: list[ToolCall]
    memory_updates: list[MemoryUpdate]
    reflection: ReflectionResult | None
```

## Stage Flow

```
Input → IntentClassifier → ContextRetriever → MemoryRetriever
  → WorldModelUpdater → Planner → ToolSelector
  → Executor → Observer → Reflector → MemoryUpdater
  → ResponseGenerator → Output
```

## Modular Design

Each stage is a class implementing `ReasoningStage`:
```python
class ReasoningStage(ABC):
    async def process(self, 
        input: ReasoningInput, 
        context: ReasoningContext
    ) -> tuple[ReasoningInput, ReasoningContext]:
        ...
```

Stages can be added, removed, or reordered via configuration. No stage has hard dependencies on other stages' internals.