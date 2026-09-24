# System Documentation Modes

Covers API, Database, Memory, Agent, Prompt, Tool, and Workflow documentation.

---

## API DOCUMENTATION MODE {#api}

### API_REFERENCE.md Template

```markdown
# API Reference

## Authentication
[How auth works for this API — N/A if none, e.g. local single-user systems]

## Endpoints

### `[METHOD] /path/to/endpoint`
**Purpose**: [what this does]

**Inputs**:
| Field | Type | Required | Description |
|-------|------|----------|--------------|
| [field] | [type] | [yes/no] | [description] |

**Outputs**:
```json
{
  "field": "type — description"
}
```

**Error Responses**:
| Code | Meaning | When It Happens |
|------|---------|-------------------|
| [code] | [meaning] | [trigger condition] |

**Usage Example**:
```python
# Concrete, runnable example
response = client.post("/path/to/endpoint", json={...})
```

**Dependencies**: [what this endpoint relies on internally]

[repeat per endpoint]

---
*Last updated: [date]*
```

For internal function-level APIs (not HTTP) — e.g., a `LLMManager.generate()` method other
modules call — use the same structure but replace "Endpoint" with the function signature and
"Authentication" with any required setup state.

---

## DATABASE DOCUMENTATION MODE {#database}

### DATABASE.md Template

```markdown
# Database Documentation

## Overview
**Type**: [SQLite/Postgres/etc.]
**Purpose**: [what this database stores and why]

## Tables

### `[table_name]`
**Purpose**: [what this table represents]

| Column | Type | Constraints | Description |
|--------|------|-------------|--------------|
| [col] | [type] | [PK/FK/NOT NULL/UNIQUE] | [description] |

**Indexes**: [list, with the query pattern each supports]
**Relationships**: [foreign keys, what they connect to]

[repeat per table]

## Data Flow
[How data enters this database, how it's read, by which components]

```
[Write Source] → [table] → [Read Consumer]
```

## Query Patterns
[Common queries and why they're shaped the way they are]

```sql
-- [Purpose of this query]
SELECT ...
```

## Migration Strategy
[How schema changes are made — tool used, or manual process if none]

## Known Risks
[Performance concerns, missing constraints, growth concerns — pull from
 python-codebase-architect or mai-ai-systems-auditor findings if available]

---
*Last updated: [date]*
```

---

## MEMORY SYSTEM DOCUMENTATION MODE {#memory}

This is one of the most valuable docs for AI companion/assistant projects — pulls heavily
from `memory-architecture-expert` findings when available.

### MEMORY_SYSTEM.md Template

```markdown
# Memory System Documentation

## Overview
**Purpose**: [what memory is trying to accomplish in this system]
**Memory Types**: [episodic/semantic/relationship/emotional/etc. — which are implemented]

## Memory Types

### [Type Name, e.g., Episodic Memory]
**What it stores**: [description]
**Storage**: [where/how]
**Example**: [concrete example of a stored memory]

[repeat per memory type]

## Storage
**Technology**: [SQLite/ChromaDB/etc.]
**Schema/Structure**: [key fields, what they mean]

## Retrieval
**Strategy**: [keyword/semantic/hybrid]
**Trigger**: [when retrieval runs]
**Similarity Metric**: [if vector-based — and note any known config gotchas]

## Ranking
**Signals Used**: [similarity/recency/importance/etc.]
**Formula**: [if known — document the actual weighting logic]

## Consolidation
**Deduplication**: [present/absent, how it works]
**Merging Strategy**: [if present]

## Pruning
**Policy**: [what gets removed/archived and when]

## Personalization Logic
**How memory shapes responses**: [concrete description of the connection between
stored memory and actual behavior change]

## Relationship Logic
**Relationship model**: [dimensions tracked — trust/closeness/etc.]
**Update mechanism**: [evidence-based/heuristic — and decay model if present]

## Known Limitations
[Honest list — pull from memory-architecture-expert audit findings if available. Documentation
that hides known issues actively misleads future maintainers.]

---
*Last updated: [date]*
*Last audited by memory-architecture-expert: [date, if applicable]*
```

---

## AGENT DOCUMENTATION MODE {#agents}

### AGENTS.md Template

```markdown
# Agent Documentation

## Overview
**Architecture**: [single-agent / multi-agent — describe routing if multi-agent]

## Agents

### [Agent Name]
**Purpose**: [single clear responsibility]
**NOT Responsible For**: [explicit boundaries]

**Inputs**: [what this agent receives]
**Outputs**: [what this agent produces]

**Tools Available**: [list, or N/A]
**Boundaries**: [what this agent must not do]
**Escalation Path**: [what happens when this agent can't complete its task]

[repeat per agent]

## Inter-Agent Communication
[How agents pass information — shared state, message passing, orchestrator-mediated]

## Routing Logic
[How requests get directed to the right agent — N/A for single-agent systems]

---
*Last updated: [date]*
```

For single-agent systems (most personal assistant projects), this doc can be much shorter —
document the single agent's full scope and skip the inter-agent sections entirely.

---

## PROMPT DOCUMENTATION MODE {#prompts}

Pulls from `prompt-architect` findings when available.

### PROMPTS.md Template

```markdown
# Prompt Documentation

## Prompt Hierarchy
```
System Prompt (Layer 1)
   ↓
Developer/Skill Prompts (Layer 2)
   ↓
Character/Agent Prompts (Layer 3)
   ↓
Memory/Context Injection (Layer 4)
```

## Prompts

### [Prompt Name]
**Layer**: [System/Developer/Skill/Character/Memory]
**Location**: `path/to/prompt`
**Purpose**: [what behavior this produces]

**Dependencies**: [other prompts this relies on or must stay consistent with]
**Expected Behavior**: [what correct behavior looks like]
**Known Risks**: [conflicts, drift risk, hallucination risk — pull from
prompt-architect findings]

**Version History**:
| Date | Change | Reason |
|------|--------|--------|
| [date] | [what changed] | [why] |

[repeat per major prompt]

## Related Prompts
[Cross-reference prompts that must change together to avoid drift/conflict]

---
*Last updated: [date]*
*Last audited by prompt-architect: [date, if applicable]*
```

---

## TOOL DOCUMENTATION MODE {#tools}

### TOOLS.md Template

```markdown
# Tool Documentation

## Tools

### [Tool Name]
**Purpose**: [what this tool does]
**Location**: `path/to/tool`

**Inputs**: [parameters and types]
**Outputs**: [what it returns]

**Failure Modes**: [how this tool can fail]
**Recovery**: [what happens on failure — retry, fallback, error to user]

**Security Considerations**: [any risks — e.g., shell execution, file access —
and what mitigations exist]

[repeat per tool]

---
*Last updated: [date]*
```

---

## WORKFLOW DOCUMENTATION MODE {#workflows}

### WORKFLOWS.md Template

```markdown
# Workflow Documentation

## User Flows

### [Flow Name, e.g., "Voice Conversation Turn"]
```
[Trigger] → [Step] → [Step] → [Step] → [Output]
```
**Description**: [narrative walkthrough]
**Files Involved**: [list]

[repeat per user flow]

## Agent Flows
[If multi-agent — trace how a request moves between agents]

## Data Flows
[How data moves and transforms — can link to DATABASE.md / MEMORY_SYSTEM.md for detail]

## Execution Flows
[Synchronous vs asynchronous paths, background tasks, scheduled jobs]

## Failure Flows

### [Failure Scenario, e.g., "LLM provider unavailable"]
```
[Trigger] → [Detection] → [Fallback/Error Path] → [User-Visible Outcome]
```

[repeat per significant failure scenario]

## Recovery Flows
[How the system recovers from failures — restarts, retries, manual intervention needed]

---
*Last updated: [date]*
```