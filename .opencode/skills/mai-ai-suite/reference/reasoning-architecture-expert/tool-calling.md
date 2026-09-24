# Tool Calling

## Reasoning-Based Selection

```python
async def select_tool(self, query: str, context: ReasoningContext) -> ToolCall | None:
    # Step 1: Can I answer directly?
    if self.has_sufficient_confidence(query, context):
        return None  # Answer directly
    
    # Step 2: What information am I missing?
    missing = self.identify_information_gaps(query, context)
    
    # Step 3: Which tool fills the largest gap?
    candidates = self.rank_tools(missing, context)
    
    # Step 4: Select best tool considering cost/latency
    return self.select_best(candidates, context)
```

## Selection Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| Gap coverage | 35% | How much missing info does this tool provide? |
| Confidence lift | 25% | Expected increase in response confidence |
| Latency cost | 20% | Time cost relative to user patience |
| Historical success | 20% | How often this tool helped in similar situations |

## Tool Registry Interface

```python
class Tool:
    id: str
    name: str
    description: str
    parameters: list[Parameter]
    required_capabilities: list[str]
    estimated_latency: float
    success_rate: float
```

## Fallback Chain

```
Primary tool → fallback 1 → fallback 2 → direct answer with uncertainty
```

Each fallback is less specific but more reliable. Final fallback is always a direct answer acknowledging uncertainty.