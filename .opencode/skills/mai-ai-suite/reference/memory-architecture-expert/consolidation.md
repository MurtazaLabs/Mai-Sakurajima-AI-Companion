# Memory Consolidation

## Importance Scoring

```python
def importance_score(memory) -> float:
    score = 0.5  # baseline
    score += 0.1 * memory.user_marked_important  # user explicitly marked
    score += 0.05 * memory.emotional_intensity     # emotional content
    score += 0.05 * memory.surprise_factor         # unexpected information
    score += 0.02 * memory.relationship_impact     # affected relationship
    score += 0.02 * memory.goal_relevance          # related to active goal
    score += 0.01 * memory.recency                 # more recent = slightly higher
    return min(1.0, score)
```

## Decay Model

- High importance (>0.8): Decay 0.5% per day
- Medium importance (0.4-0.8): Decay 2% per day
- Low importance (<0.4): Decay 5% per day
- Reinforced: +0.1 on each confirmation (cap 0.99)
- Floor: 0.05 (never fully forgotten)

## Consolidation Triggers

| Trigger | What Happens |
|---------|-------------|
| Real-time | New memory scored and stored immediately |
| After conversation | Important memories reinforced, low-importance decayed |
| Dreaming cycle | Full consolidation: promote, decay, merge, dedup |
| Weekly deep | Full review: contradictions, gaps, optimization |

## Promotion to Long-term

Memory moves from episodic to semantic when:
- Same fact confirmed 3+ times
- Importance > 0.7
- User explicitly confirms
- Related to identity or relationship