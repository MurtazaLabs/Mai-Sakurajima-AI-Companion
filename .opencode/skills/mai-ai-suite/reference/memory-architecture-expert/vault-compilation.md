# Vault Compilation

## Canonical Structure

```
MaiMemory/
  conversations/    # Episodic: per-session summaries with links to entities
  identity/         # Self-description, personality traits, preferences
  preferences/      # Likes, dislikes, communication preferences
  knowledge/        # Semantic: general facts about world
  memories/         # Emphasized episodic memories (high importance)
  relationships/    # Per-person: trust, closeness, history
  reflections/      # Insights discovered by Mai
  dreams/           # Synthesized ideas, hypotheses
  statistics/       # Conversation counts, growth metrics
  graph/            # Entity index, relationship index
  index.md          # Master index of all pages
  log.md            # Chronological log of significant changes
  schema.md         # Documentation of vault structure
```

## Compiler Pipeline

```
MemoryState → DiffEngine → ChangeSet → PageRenderer → FileWriter
```

- DiffEngine: Compare current MemoryState with last known state
- ChangeSet: Only changed entities
- PageRenderer: Transform entities to markdown
- FileWriter: Write only changed pages

## Incremental Update Rules

- Only rewrite pages whose source data changed
- Preserve manual edits (track via page hash)
- Update index.md when pages are added/removed
- Append to log.md for significant changes
- Never rewrite the entire vault
- Run compiler after every conversation and after each dreaming cycle