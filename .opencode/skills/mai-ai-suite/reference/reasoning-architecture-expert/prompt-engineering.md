# Prompt Engineering

## Design Principles

1. **Minimal** — every word serves a purpose. Remove fluff.
2. **Modular** — prompts are composed from reusable fragments, not monolithic.
3. **Token efficient** — optimize for intent density per token.
4. **Maintainable** — prompts are in version-controlled files, not inline strings.
5. **Debuggable** — each prompt fragment logs its inclusion and token count.

## Prompt Architecture

```python
class PromptBuilder:
    def __init__(self):
        self.fragments: dict[str, PromptFragment] = {}
    
    def add(self, key: str, fragment: PromptFragment):
        self.fragments[key] = fragment
    
    def build(self, keys: list[str], context: ReasoningContext) -> str:
        selected = [self.fragments[k] for k in keys]
        return "\n\n".join(f.render(context) for f in selected)
```

## Prompt Types

| Type | Purpose | Max Tokens | Fragments |
|------|---------|-----------|-----------|
| System | Core identity, capabilities | 500 | identity, capabilities, guidelines |
| Reasoning | Thought process guidance | 300 | chain_of_thought, reflection, tool_use |
| Tool | Tool descriptions, schemas | 400 | tool_list, selection_rules, fallback |
| Memory | Memory retrieval instructions | 200 | retrieval_strategy, relevance_criteria |
| Reflection | Self-evaluation criteria | 200 | quality_checks, improvement_suggestions |

## Token Efficiency Checklist

- [ ] Each fragment has a clear single purpose
- [ ] No duplicate instructions across fragments
- [ ] Examples are minimal (1 per case, not 3)
- [ ] Instructions are affirmative (do) not negative (don't)
- [ ] Format instructions are minimal (model handles structure)
- [ ] Context is pre-filtered, not left to model to ignore