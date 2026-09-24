# Knowledge Graph Reference

> Complete reference for the three-layer graph architecture — `knowledge/graph.py`, `knowledge/brain_graph.py`, `knowledge/cognitive_graph.py`, `knowledge/graph_manager.py`.

---

## Overview

Three-layer graph architecture (known debt D-3 — collapse to 2 layers proposed):

| Layer | File | Class | Role |
|-------|------|-------|------|
| 1 | `graph.py` | `KnowledgeGraph` | atomic in-memory entity/relation store; `query()` O(relations×depth) |
| 2 | `brain_graph.py` | `BrainGraph` | facade over 7+ typed node types; bridges all stores |
| 3 | `cognitive_graph.py` | `CognitiveGraph` | cognitive dimension; `import_beliefs()` |

**Architecture:** [[01-Architecture/05-Knowledge Graph & Vault]]

---

## Layer 1: KnowledgeGraph (`knowledge/graph.py`)

Atomic entity/relation store:

- **Entities:** `(id, type, name, properties, confidence, source, timestamp)`
- **Relations:** `(source_id, target_id, relation_type, properties, confidence)`
- **Query:** `query(entity_id, depth, relation_types)` — breadth-first traversal
- **Index:** by name (lowercase), by type, by source
- **Thread-safety:** RLock on all mutating operations
- **Cache:** `TTLCache` on `get_entity()` (TTL 300s, max 1024 entries) — invalidated on `add_entity()`/`remove_entity()`

**Methods:**
- `add_entity(type, name, properties, confidence, source)` → entity_id
- `add_relation(source_id, target_id, relation_type, properties, confidence)`
- `get_entity(entity_id)` → entity
- `find_by_name(name, type=None)` → [entity]
- `query(entity_id, depth=2, relation_types=None)` → subgraph

---

## Layer 2: BrainGraph (`knowledge/brain_graph.py`)

Facade over 7+ typed node types, bridges all stores:

### Node Types (7+)

| Type | Source | Description |
|------|--------|-------------|
| `person` | MemoryWriter, conversations | people Mai knows |
| `place` | MemoryWriter, conversations | locations |
| `project` | StateDumper, goals | active projects |
| `technology` | KB, conversations | tools, languages, frameworks |
| `event` | MemoryWriter, dreams | significant events |
| `skill` | StateDumper, procedural | capabilities |
| `media` | KB, conversations | books, movies, games |
| `organization` | KB, conversations | companies, groups |
| `relationship` | StateDumper | per-person relationship |
| `interest` | StateDumper | topics of interest |
| `character` | Canon | canon entities |

### Bridge Methods

| Method | Bridges To |
|--------|------------|
| `get_person(name)` | MemoryWriter vault, StateDumper people/ |
| `get_project(name)` | StateDumper projects/, GoalManager |
| `get_technology(name)` | KB, MemoryWriter |
| `import_beliefs()` | BeliefEngine → belief nodes |
| `import_experiences()` | ExperienceStore → experience nodes |

### Dashboard Integration

- Node-type breakdown in dashboard (`api/routes_dashboard.py`)
- Category counts, recent entities

---

## Layer 3: CognitiveGraph (`knowledge/cognitive_graph.py`)

Cognitive dimension — adds semantic/cognitive layers:

- `import_beliefs()` — creates cognitive belief nodes from BeliefEngine
- Cognitive relations: `implies`, `contradicts`, `supports`, `generalizes`
- Used by reasoning engine for inference

---

## GraphManager (`knowledge/graph_manager.py`)

Orchestration layer:

- **Junk gate:** refuses `unknown` entities with confidence < 0.25 (fallback extractor tier)
- Coordinates GraphExporter → vault `graph/*.md`
- Entity deduplication (fuzzy name matching)
- Relation inference (heuristic + LLM)

---

## Belief Engine (`knowledge/belief_engine.py`)

Beliefs with confidence, source, updates:

- `add_belief(content, confidence, source, metadata)`
- `update_belief(belief_id, confidence_delta, evidence)`
- `get_beliefs(topic, min_confidence)` → filtered
- **Cache:** `TTLCache` on `get_belief()` and `query()` (TTL 300s, max 1024) — invalidated on `_merge()`, `contradict()`, `_evict_if_needed()`
- **Triple storage drift (D-1):** `_beliefs` dict, BrainGraph belief nodes, CognitiveGraph.import_beliefs() — independent copies

---

## Retrieval Integration

`AdvancedRetriever` uses KG as one of 4 parallel sources:

- Entity traversal from query entities
- Relation hopping (depth 2)
- Confidence-weighted scoring
- Merged with vector, beliefs, attention

---

## Vault Export (`GraphExporter` → `knowledge/graph_exporter.py`)

Exports entities to `graph/{safe_name}.md` with:
- Frontmatter: entity, type, confidence, tags, first_seen
- Relations as wiki-links (only if target note exists)
- Thread-safe counter (RLock)

---

## Junk Detection & Janitor

- `GraphManager` gate: confidence < 0.25 → refused
- `VaultJanitor` (`vault_janitor.py`): sweeps junk entities + orphan notes
- CLI: `scripts/sweep_graph_junk.py --apply`
- Protects living entities (checks `living_by_lower` before name-junk check)

---

## Known Issues

- **D-1:** Triple belief storage drift (P0-class)
- **D-2:** `memory/` imports `knowledge/` (layer breach)
- **D-3:** Three-layer overlap — collapse to 2 layers proposed

---

## Wiki Links

**Architecture:** [[01-Architecture/05-Knowledge Graph & Vault]] • [[01-Architecture/09-Events & Data Flow]] — KG events  
**Related:** [[02-Subsystems/Vault Compilation]] — GraphExporter • [[02-Subsystems/Memory Pipeline]] — entity extraction • [[02-Subsystems/Identity & Canon]] — canon entities