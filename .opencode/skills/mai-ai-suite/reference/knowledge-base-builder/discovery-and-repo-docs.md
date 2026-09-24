# Repository, Architecture & Onboarding Documentation

---

## REPOSITORY DOCUMENTATION MODE {#repository}

### What to Capture

**Folder Structure** — annotated, not just listed; explain WHY things are organized this way
**Modules/Packages/Components** — what each major grouping is responsible for
**Entry Points** — where execution actually begins
**Important Files** — the handful of files a new reader should look at first

### REPOSITORY_OVERVIEW.md Template

```markdown
# [Project Name] — Repository Overview

## Purpose
[What this project does, in 2-3 sentences]

## Project Structure

```
project/
├── config/          # [what lives here, why]
├── core/            # [what lives here, why]
├── memory/          # [what lives here, why]
├── voice/           # [what lives here, why]
└── run.py           # [entry point — what it does]
```

## Major Components

### [Component Name]
- **Location**: `path/to/component`
- **Purpose**: [what it does]
- **Depends on**: [list]
- **Used by**: [list]

[repeat per major component]

## Entry Points

| Entry Point | Purpose | Run With |
|--------------|---------|----------|
| `run.py` | [purpose] | `python run.py` |

## Important Files (read these first)

1. `[file]` — [why this is the best starting point]
2. `[file]` — [what this teaches about the system]
3. ...

## Critical Workflows

### [Workflow Name]
```
[Trigger] → [Step] → [Step] → [Output]
```
See `WORKFLOWS.md` for full detail.

---
*Last updated: [date] — keep this in sync with the actual structure*
```

---

## ARCHITECTURE DOCUMENTATION MODE {#architecture}

### What to Capture

**System Overview** — the 30-second mental model
**Architecture Layers** — what's where, and why it's separated that way
**Component Relationships** — who talks to whom
**Data Flow** — how information moves through the system
**Control Flow** — how execution moves through the system
**Dependencies** — internal and external

### ARCHITECTURE.md Template

```markdown
# [Project Name] — Architecture

## System Overview
[2-4 sentences: the architectural style and the core idea behind it]

## Architecture Diagram

```
User Input
    ↓
[Layer 1] — [one-line purpose]
    ↓
[Layer 2] — [one-line purpose]
    ↓
[Layer 3] — [one-line purpose]
    ↓
Output
```

## Architecture Layers

### [Layer Name]
**Purpose**: [why this layer exists]
**Contains**: [modules/files in this layer]
**Responsibilities**: [what this layer does and does NOT do]

[repeat per layer]

## Component Relationships

| Component | Talks To | How | Why |
|-----------|----------|-----|-----|
| [A] | [B] | [sync call/event/shared state] | [reason for the relationship] |

## Data Flow

[Trace the path of data through the system from input to persistence/output]

```
[Source] → [Transform] → [Transform] → [Store/Output]
```

## Control Flow

[Trace the execution path for the 1-2 most important operations]

## Dependencies

**Internal**: [key internal coupling worth knowing about]
**External**: [key libraries/services this architecture relies on]

## Design Decisions
[Link to relevant entries in DECISIONS.md rather than re-explaining here]

---
*Last updated: [date]*
```

### Diagram Guidance

- Use simple ASCII arrows (`→`, `↓`) for linear flows — renders everywhere, no tooling needed
- Use a tree structure (`├──`, `└──`) for hierarchical/folder relationships
- Keep diagrams to what fits in ~20 lines — split into multiple smaller diagrams rather than
  one overwhelming one
- Always pair a diagram with 2-3 sentences of prose — diagrams alone are ambiguous

---

## DEVELOPER ONBOARDING MODE {#onboarding}

### What to Capture

**Project Purpose** — why this exists
**Setup Instructions** — exact, copy-pasteable steps from zero to running
**Project Structure** — link to REPOSITORY_OVERVIEW.md, don't duplicate
**Development Workflow** — how to make a change safely
**Common Tasks** — the 5-10 things a developer does most often
**Common Pitfalls** — the mistakes a new person is likely to make
**Learning Path** — recommended order to explore the codebase
**FAQ** — actual questions that have actually come up

### DEVELOPER_GUIDE.md Template

```markdown
# [Project Name] — Developer Guide

## Project Purpose
[What this is and why it exists — 2-3 sentences]

## Setup Instructions

```bash
# Exact, copy-pasteable commands
git clone [repo]
cd [project]
pip install -r requirements.txt --break-system-packages
# [any other required setup — model downloads, env vars, etc.]
python run.py
```

**Prerequisites**: [hardware/software requirements — e.g., "8GB+ RAM for local LLM inference"]

## Project Structure
See `REPOSITORY_OVERVIEW.md` for the full structure.

## Development Workflow

1. [How to make a change — e.g., "Create a feature branch"]
2. [How to test locally]
3. [How to verify nothing broke]

## Common Tasks

### [Task Name, e.g., "Adding a new memory type"]
1. [Step]
2. [Step]
**Files typically touched**: [list]

[repeat for 5-10 most common tasks]

## Common Pitfalls

- **[Pitfall]**: [what it looks like] → [how to avoid/fix it]
- **[Pitfall]**: [what it looks like] → [how to avoid/fix it]

## Learning Path

**Week 1**: [what to read/understand first]
**Week 2**: [what to explore next]
**Week 3**: [when to start making real changes]

## FAQ

**Q: [Actual question that's come up]**
A: [Answer]

---
*Last updated: [date]*
```

### Onboarding Doc Quality Rules

- Setup instructions must be tested, not assumed — if you can't verify a command works,
  flag it as unverified rather than presenting it confidently
- Common Pitfalls should come from REAL observed mistakes (bugs found, confusion expressed)
  not hypothetical ones — pull from prior audit findings if available
- Don't duplicate content that belongs in ARCHITECTURE.md or REPOSITORY_OVERVIEW.md — link
  to it instead, so updates only need to happen in one place