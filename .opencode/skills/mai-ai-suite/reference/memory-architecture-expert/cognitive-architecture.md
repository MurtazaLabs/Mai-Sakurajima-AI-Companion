# Cognitive Architecture

## Pipeline

```
Conversation
  → Working Memory (current session)
  → Memory Extractor (entities, relationships, facts)
  → Knowledge Graph (structured entities + relations)
  → Relationship Engine (trust, closeness, history)
  → MemoryState (central runtime object)
  → Reasoning (context-aware thought)
  → Reflection (post-conversation cognitive processing)
  → Dream Engine (idle-time maintenance)
  → Vault Compiler (incremental markdown generation)
  → Obsidian Vault (human-readable view)
```

## Subsystem Boundaries

| Subsystem | Owns | Does Not Own |
|-----------|------|--------------|
| Working Memory | Current conversation context | Long-term storage |
| Episodic Memory | Specific events with timestamps | General facts |
| Semantic Memory | General knowledge, facts | Event-specific details |
| Identity Memory | Self-characteristics, preferences | External entities |
| Relationship Memory | Trust, closeness, interaction history | Facts about the world |
| Emotional Memory | Emotion-tagged events | Raw event data |
| Procedural Memory | Skills, workflows, learned behaviors | Declarative knowledge |
| Dream Memory | Hypotheses, synthesized ideas | Verified facts |
| Reflective Memory | Insights, patterns, discoveries | Raw data |
| World Model | Environment, situation understanding | Relationship-specific data |

## Data Flow Principles

- Data flows one direction: Conversation → MemoryState → Vault
- No subsystem writes directly to another subsystem's storage
- MemoryState is the integration point — all subsystems read from it
- The vault is read-only for human browsing, never the runtime database