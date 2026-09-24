# Self Reflection

## Reflection Triggers

| Mode | Trigger | Depth | Token Cost |
|------|---------|-------|-----------|
| Inline | After each response | Shallow | ~50 tokens |
| Periodic | Every N responses (N=5) | Medium | ~200 tokens |
| Background | Dream cycle | Deep | ~1000 tokens |
| On failure | Tool/plan error | Diagnostic | ~300 tokens |
| On uncertainty | Confidence < threshold | Medium | ~200 tokens |

## Inline Reflection

```python
async def inline_reflect(self, input, output, context):
    # Quick checks:
    # 1. Did I answer the question?
    # 2. Is my confidence appropriate?
    # 3. Should any part become a memory?
    # 4. Did I miss anything obvious?
    if issues := self.check(output):
        self.correct(output, issues, context)
        self.log_reflection("inline", issues)
```

## Deep Reflection (Background)

During dreaming cycles, review:
- Recent conversations for improvement opportunities
- Pattern of tool selection (over-reliance on one tool?)
- Context management decisions (useful context dropped?)
- Memory retrieval quality (relevant memories missed?)
- Long-term consistency (contradictions over time?)

## Feedback Integration

Reflection results are stored as `ReflectionObject` in memory. The reasoning pipeline reads recent reflections to adjust behavior. Reflections have a confidence score and decay over time.