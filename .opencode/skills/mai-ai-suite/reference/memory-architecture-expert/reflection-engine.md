# Reflection Engine

## Trigger

After meaningful conversations:
- Conversation with emotional content
- New goal established or completed
- Significant update to relationship
- User explicitly asks for reflection
- After every 10th conversation (periodic)

## Process

```python
async def reflect(conversation, context):
    patterns = await identify_patterns(conversation, context.history)
    insights = await generate_insights(conversation, context.memory_state)
    contradictions = await detect_contradictions(insights, context.memory_state)
    themes = await recognize_themes(conversation, context.memory_state)
    beliefs = await update_beliefs(insights, context.memory_state)
    questions = await suggest_future_questions(gaps=themes.unknowns)
    
    return ReflectionResult(
        patterns=patterns,
        insights=insights, 
        contradictions=contradictions,
        themes=themes,
        beliefs=beliefs,
        questions=questions,
    )
```

## Output

Each reflection produces a `ReflectionObject`:
- Trigger (what caused it)
- Patterns discovered
- Insights generated
- Belief updates
- Questions for future exploration
- Timestamp

Reflections are stored in reflective memory and used during future reasoning to improve understanding.