# Planning System

## Decomposition

```python
class Planner:
    async def decompose(self, goal: str, context: ReasoningContext) -> Plan:
        # Analyze goal complexity
        # Generate subtasks with dependencies
        # Estimate effort and priority per subtask
        # Return DAG of subtasks
```

## Subtask Types

| Type | Description | Example |
|------|-------------|---------|
| Direct | Answer immediately | "What's the weather?" |
| Retrieval | Search memory/knowledge | "What project did I start last week?" |
| Reasoning | Multi-step thought | "Should I learn Rust or Python?" |
| Tool | Execute tool call | "Send a reminder" |
| Planning | Sub-decompose | "Plan my learning path" |
| Reflection | Evaluate own output | "Did I answer correctly?" |

## Dynamic Replanning

Triggered when:
- Subtask execution fails
- New information contradicts assumptions
- User changes their mind mid-task
- Timeout exceeded

Replanning preserves completed subtasks and only re-plans the affected branch.

## Persistence

Plans are stored in the goal manager with:
- Created timestamp
- Last updated timestamp
- Completion percentage
- Subtask status list
- Dependency graph
- Execution history (for reflection)