# Vault Compilation Reference

> Complete reference for the Obsidian vault compilation pipeline — `knowledge/obsidian_writer.py`, `knowledge/state_dumper.py`, `knowledge/memory_writer.py`, `knowledge/vault_compiler.py`, `knowledge/graph_exporter.py`, `knowledge/vault_janitor.py`.

---

## Overview

The vault is the **human-readable character memory** — an Obsidian-compatible markdown vault that represents Mai's compiled knowledge, relationships, and conversation history.

**Architecture:** [[01-Architecture/05-Knowledge Graph & Vault]]

---

## Single-Writer Principle

| Writer | Owns | Notes |
|--------|------|-------|
| `StateDumper` / `VaultCompiler` | **Compiled folders**: identity, preferences, relationship, knowledge, projects, people, places, dreams, statistics | structured facts; `first_met` from vault, real turn counts |
| `MemoryWriter` | **Raw growth folders**: conversation, archive, important | per-turn records; cross-day dedup; reinforcement counters |

**Critical invariant:** Raw writes targeting compiler-owned folders are **redirected** to `conversation/` (dual-writer clobber fix, Aug 2026).

---

## Components

### ObsidianWriter (`knowledge/obsidian_writer.py`)

Orchestrating facade — coordinates three sub-writers:

| Sub-writer | File | Role |
|------------|------|------|
| `GraphExporter` | `graph_exporter.py` | exports KnowledgeGraph entities → `graph/*.md` |
| `StateDumper` | `state_dumper.py` | compiles structured state → compiled folders |
| `MemoryWriter` | `memory_writer.py` | writes raw conversation records → growth folders |

Entry point: `ObsidianWriter.write_all()` — called by scheduler (daily) + on shutdown.

---

### GraphExporter (`knowledge/graph_exporter.py`)

Exports KnowledgeGraph entities to `graph/{safe_name}.md`:

```markdown
---
entity: "Project: Mai AI"
type: "project"
confidence: 0.95
tags: [ai, companion, python]
first_seen: "2026-07-15"
---

# Project: Mai AI

**Type:** project
**Confidence:** 0.95

## Relations
- **uses** → Technology: Python
- **uses** → Technology: ChromaDB
- **has_part** → Module: core
```

- Only exports entities with confidence ≥ 0.25 (junk gate)
- Wiki-links to related entities (only if target note exists)
- Thread-safe counter (RLock on export stats)

### StateDumper (`knowledge/state_dumper.py`)

Compiles structured state to markdown:

| Folder | Content | Key Methods |
|--------|---------|-------------|
| `identity/` | Canonical identity, traits, values, boundaries | `_dump_identity()` |
| `preferences/` | Likes/dislikes (canon + evolved overlay) | `_dump_preferences()` |
| `relationship/` | Trust, affection, closeness, respect, familiarity | `_dump_relationship()` |
| `knowledge/` | Beliefs, facts, project summaries | `_dump_knowledge()` |
| `projects/` | Active projects with progress | `_dump_projects()` |
| `people/` | Person profiles with per-person relationship | `_dump_people()` |
| `places/` | Place profiles | `_dump_places()` |
| `dreams/` | Dream reports with insights | `_dump_dreams()` |
| `statistics/` | Aggregate stats (turns, memories, etc.) | `_dump_statistics()` |

**Key fixes (Aug 2026):**
- `first_met` from earliest `YYYY-MM-DD.md` conversation filename (or frontmatter timestamp) — not "today"
- `total_conversations`/`total_messages` from real `### 👤 User` headers — not inflated `interaction_count`

### MemoryWriter (`knowledge/memory_writer.py`)

Writes raw conversation turns to growth folders:

| Folder | Purpose |
|--------|---------|
| `conversation/` | daily `YYYY-MM-DD.md` — chronological turns |
| `archive/` | older conversations (rotated) |
| `important/` | flagged important turns |

**Format per turn:**
```markdown
### 👤 User
{user_text}

### 🤖 Mai
{ai_text}

**Reinforcement:** 3
**Tags:** #topic1 #topic2
**Links:** [[Entity1]] [[Entity2]]
```

**Key fixes (Aug 2026):**
- **Cross-day dedup:** `_dedup_hit_anywhere()` scans entire growth folder for existing `### 👤 User\n{user}\n` — duplicates bump `Reinforcement` in place
- **Wiki-link filtering:** `_link_target_exists()` checks `graph/{safe}.md` before emitting `[[link]]` — only resolvable links written
- **Quote preservation:** `_bump_reinforcement()` captures original quote char (`"` or `'`) and preserves it

---

### VaultCompiler (`knowledge/vault_compiler.py`)

High-level compilation orchestrator:
- Runs full compilation pipeline
- Handles migrations (`vault_migrator.py`)
- Post-processing (`vault_post_processor.py`)
- Schema validation (`vault_schema.py`)

---

## Vault Integrity Tooling

| Tool | File | Purpose |
|------|------|---------|
| `VaultJanitor` | `vault_janitor.py` | sweeps junk entities + orphan notes (dry-run default) |
| `LinkIntegrity` | `link_integrity.py` | validates all wiki-links resolve |
| `VaultMigrator` | `vault_migrator.py` | versioned vault migrations |
| `VaultPostProcessor` | `vault_post_processor.py` | post-compilation cleanup |
| `VaultLogger` | `vault_logger.py` | structured vault write logs |

### VaultJanitor — Junk Sweep

- `JUNK_TOKENS` + `_STOPWORD_RE` define junk patterns
- Skips single chars, matches 2-char tokens against junk list
- **Protects living entities** — checks `living_by_lower` before name-junk check
- CLI: `scripts/sweep_graph_junk.py --apply`

---

## Events

- Publishes `state.knowledge.updated` after graph/doc updates
- `data.graph.updated` for subsystem consumers

---

## Known Issues

- Three-layer graph abstraction (D-3)
- Triple belief storage drift (D-1)
- `memory/` imports `knowledge/` (D-2)

---

## Wiki Links

**Architecture:** [[01-Architecture/05-Knowledge Graph & Vault]] • [[01-Architecture/04-Memory Subsystem]] — MemoryWriter integration  
**Related:** [[02-Subsystems/Memory Pipeline]] — store path • [[02-Subsystems/Knowledge Graph]] — graph detail • [[03-Features/Native OS Bridge Architecture]] — daemon vault access