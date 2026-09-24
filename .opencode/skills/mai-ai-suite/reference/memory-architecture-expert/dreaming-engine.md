# Dreaming Engine

## Trigger

Runs when idle conditions met:
- No user message for 5+ minutes
- 10+ new memories since last dream
- System resources: CPU < 20%, RAM < 60%

## Consolidation Cycle

```
1. Scan new memories since last dream
2. Score each memory for importance
3. Identify potential merges (duplicate detection)
4. Strengthen relationships between co-occurring entities
5. Detect contradictions between new and existing knowledge
6. Recalculate importance scores (decay old, boost reinforced)
7. Generate wiki links between related vault pages
8. Check vault health (index consistency, missing pages)
9. Update statistics
10. Generate dream summary → log to dream memory
```

## Responsibilities

| Task | Frequency | Cost |
|------|-----------|------|
| Memory dedup | Every cycle | Medium |
| Entity merging | Every cycle | Medium |
| Relationship strengthening | Every cycle | Low |
| Contradiction detection | Every 3 cycles | High |
| Importance recalculation | Every cycle | Low |
| Memory decay | Every cycle | Low |
| Index rebuilding | Every 10 cycles | Low |
| Health checks | Every cycle | Low |
| Gap detection | Every 5 cycles | Medium |
| Dream generation | Every cycle | Medium |

## Safety

- Never fabricate new facts
- Never delete information (mark as deprecated)
- Never resolve contradictions without user input
- Always log every change with before/after state
- Always verify merge correctness before applying