# Mai AI Documentation Protocol

## Purpose

This protocol defines how all Mai AI specialist skills document their work.

Documentation is a required part of completing significant engineering work.

The purpose is to ensure that the Mai AI project maintains a continuously updated,
interconnected Obsidian knowledge base describing:

- Architecture
- Systems
- Components
- Decisions
- Features
- Bugs
- Fixes
- Changes
- Development procedures
- Dependencies
- Integrations
- Engineering knowledge
- Important implementation details

Documentation must be written to:

`E:\Mai_ai\docs\Mai_documentation\`

---

# Core Rule

After a specialist completes significant analysis, implementation, debugging,
architecture work, feature development, auditing, refactoring, or other engineering
work, the specialist MUST determine whether the result should be documented.

If the work changes, discovers, establishes, or clarifies important project knowledge,
documentation is required.

Do not consider the task completely finished until the relevant documentation has
been created or updated.

---

# Documentation Location

All Mai AI engineering documentation MUST live inside:

`E:\Mai_ai\docs\Mai_documentation\`

Do not create documentation outside this directory unless explicitly requested
by the user.

---

# Documentation Principles

Documentation must:

1. Reflect the actual state of the project.
2. Describe what was actually implemented or discovered.
3. Avoid documenting assumptions as facts.
4. Avoid duplicating information unnecessarily.
5. Update existing documentation when the relevant document already exists.
6. Create a new document only when the information has no appropriate existing home.
7. Use Obsidian Wiki-links extensively.
8. Keep links meaningful and bidirectional where appropriate.
9. Preserve existing documentation unless it is obsolete or factually incorrect.
10. Never invent implementation details.

---

# Obsidian Wiki-Link Requirement

Documentation MUST use Obsidian Wiki-links when referencing another documented
Mai AI concept, system, component, decision, feature, or guide.

Use:

[[Document Name]]

instead of ordinary Markdown links when linking to another document inside
the Mai Documentation vault.

Examples:

[[Memory System]]
[[Memory Pipeline]]
[[Knowledge Graph]]
[[Vector Store]]
[[Obsidian Memory]]
[[Voice System]]
[[Mai AI Suite]]
[[Python Master Engineer]]
[[Architecture Decisions]]

---

# Link Existing Knowledge First

Before creating a new documentation file:

1. Search the Mai Documentation directory.
2. Determine whether an appropriate document already exists.
3. If it exists, update it.
4. If it does not exist, create the appropriate document.
5. Add Wiki-links to related documents.

Do not create multiple documents describing the same system.

---

# Documentation Categories

Choose the appropriate documentation area.

The actual folder structure in `E:\Mai_ai\docs\Mai_documentation\` is:

```
Mai documentation/
│
├── 00-Overview/
│   ├── Project Charter.md
│   └── README.md
│
├── 01-Architecture/
│   ├── 01-System Overview.md
│   ├── 02-Application Boot & Lifecycle.md
│   ├── 03-Core Brain Kernel & State.md
│   ├── 04-Memory Subsystem.md
│   ├── 05-Knowledge Graph & Vault.md
│   ├── 06-Agency Reasoning LLM & Execution.md
│   ├── 07-Voice Subsystem.md
│   ├── 08-API Native & Surface.md
│   ├── 09-Events & Data Flow.md
│   ├── 10-Status & Debt.md
│
├── 02-Subsystems/
│   ├── Identity & Canon.md
│   ├── Event System.md
│   ├── Tool System.md
│   ├── Memory Pipeline.md
│   ├── Knowledge Graph.md
│   ├── Vault Compilation.md
│   ├── Voice Pipeline.md
│
├── 03-Features/
│   ├── Native OS Bridge Architecture.md
│   ├── Event Fabric Architecture.md
│   ├── Discord Integration Plan.md
│   ├── Character Rename PRD.md
│
├── 04-Development/
│   ├── Testing Strategy.md
│   ├── Deployment Guide.md
│
├── 05-Reference/
│   ├── MERGED_COMPLETE Reference.md
│   ├── Complete Folder Structure.md
│
└── 06-Operations/
    ├── README.md
    ├── Monitoring-Alerting/
    │   └── README.md
    ├── Backup-Disaster-Recovery/
    │   └── README.md
    ├── Deployment/
    │   └── README.md
    ├── Incident-Response/
    │   └── README.md
    ├── Maintenance/
    │   └── README.md
    └── Troubleshooting/
        └── README.md
```

Use the most specific appropriate location.

---

# Specialist Documentation Rules

## Python Master Engineer

Document:

- Significant bugs
- Root causes
- Important fixes
- Architectural changes
- New components
- Refactoring decisions
- Performance changes
- Important implementation patterns
- Testing changes

Typical locations:

`01-Architecture/` — for architectural changes
`02-Subsystems/` — for subsystem changes
`04-Development/` — for development workflow changes

Example:

A major MemoryPipeline bug is fixed.

Update:

[[Memory Pipeline]]

and, if appropriate:

[[Memory System]]
[[Testing]]

---

## Python Codebase Architect

Document:

- Repository architecture
- Component relationships
- Dependency relationships
- Important modules
- Data flow
- Architectural boundaries
- Technical debt
- Structural changes

Typical locations:

`01-Architecture/`
`02-Subsystems/`

Always update architecture documentation when the actual architecture changes.

---

## Mai AI Systems Auditor

Document:

- Audit findings
- Security findings
- Reliability issues
- Architecture risks
- Production-readiness findings
- Important vulnerabilities
- Recommended architectural changes
- Resolved audit findings

Typical locations:

`01-Architecture/`
`06-Operations/` — for monitoring, incident response, backup/recovery

If an audit finding is resolved, update the documentation to reflect the
current state rather than leaving the old finding as if it were still active.

---

## Principal Software Advisor

Document significant:

- Engineering decisions
- Design patterns
- Maintainability recommendations
- Scalability decisions
- Code-quality standards
- Engineering conventions

Typical locations:

`04-Development/`

---

## AI Memory Architect

Document:

- Memory architecture
- Memory pipeline
- Retrieval architecture
- RAG
- Embeddings
- Vector stores
- Knowledge graphs
- Memory consolidation
- Memory ranking
- Obsidian integration
- Memory data flow

Typical locations:

`02-Subsystems/Memory/`
`01-Architecture/` — for architecture
`02-Subsystems/` — for subsystems

Memory documentation should use Wiki-links heavily because memory systems
usually interact with many other Mai systems.

---

## Prompt Architect

Document significant:

- Prompt architecture
- Agent prompt design
- Character behavior rules
- Prompt optimization decisions
- Prompt versioning
- Prompt-related system behavior

Typical locations:

`02-Subsystems/` — for prompt subsystems
`03-Features/` — for features involving prompts

---

## AI Product Manager

Document:

- Feature requirements
- Product decisions
- MVP decisions
- Roadmap changes
- Priorities
- Product trade-offs
- User-facing capabilities

Typical locations:

`01-Architecture/` — for architecture decisions
`06-Operations/Deployment/` — for deployment decisions
`03-Features/` — for feature specs

---

## Knowledge Base Builder

The Knowledge Base Builder is responsible for maintaining documentation quality.

It may:

- Consolidate duplicate documents.
- Improve Wiki-link connectivity.
- Repair broken references.
- Update indexes.
- Organize documentation.
- Create missing documentation.
- Archive obsolete documentation.
- Maintain documentation consistency.

Typical locations:

All documentation areas.

---

## Mai Development Orchestrator

The orchestrator is responsible for ensuring that documentation happens after
significant specialist work.

It must determine:

1. What changed?
2. What was discovered?
3. What knowledge is now important?
4. Which documentation should be updated?
5. Which new Wiki-links should be created?
6. Whether a new decision record is required.
7. Whether the Knowledge Base Builder should perform a documentation cleanup.

---

# What To Document

Documentation is required when the specialist:

- Changes architecture.
- Adds a significant feature.
- Fixes a non-trivial bug.
- Changes an important subsystem.
- Introduces a dependency.
- Removes a dependency.
- Changes an interface.
- Changes data flow.
- Changes memory behavior.
- Changes security behavior.
- Changes deployment behavior.
- Makes an important engineering decision.
- Discovers an important architectural fact.
- Changes project workflow.
- Establishes a new development convention.

---

# What NOT To Document

Do not create documentation for trivial changes such as:

- Simple typo fixes.
- Formatting-only changes.
- Temporary debugging output.
- Unimportant variable renaming.
- Minor internal changes that do not affect project understanding.

However, if a trivial change reveals an important architectural problem,
document the discovery.

---

# Documentation Workflow

After completing the specialist task:

### Step 1 — Determine Documentation Impact

Ask:

"What permanent knowledge did this task create, change, or confirm?"

Possible answers:

- No documentation required.
- Existing document must be updated.
- New document required.
- Existing document and related documents must be updated.
- Architecture Decision Record required.

---

### Step 2 — Locate Existing Documentation

Search:

`E:\Mai_ai\docs\Mai_documentation\`

Find the most relevant existing documents.

Do not create duplicates.

---

### Step 3 — Update or Create Documentation

Document:

- What changed
- Why it changed
- How it works now
- Important implementation details
- Dependencies
- Interfaces
- Constraints
- Validation
- Related systems

Only document verified facts.

---

### Step 4 — Add Wiki-links

Connect the new or updated documentation to related concepts.

Example:

# Memory Pipeline

The [[Memory Pipeline]] receives conversation data from
[[Memory Coordinator]] and sends extracted information to
[[Memory Intelligence]].

Processed memories may be stored through:

- [[Memory Graph]]
- [[Vector Store]]
- [[Obsidian Memory]]

The resulting graph may be exported through [[Graph Exporter]].

---

### Step 5 — Update Related Documents

If a change affects another documented system, update that document too.

For example:

Changing the MemoryPipeline may require updates to:

[[Memory System]]
[[Memory Pipeline]]
[[Memory Graph]]
[[Vector Store]]
[[Obsidian Memory]]
[[Data Flow]]

Do not update unrelated documentation.

---

### Step 6 — Update Indexes When Necessary

If the documentation vault contains an index, system map, architecture map,
or table of contents, update it when a new document is created.

---

### Step 7 — Check Wiki-Link Integrity

Before finishing:

- Check that new Wiki-links refer to real documents where possible.
- Identify broken links.
- Do not silently invent documents merely to make a link appear valid.
- If a referenced concept has no document yet, either create appropriate
  documentation or clearly mark the missing documentation.

---

# Architecture Decision Records

When a specialist makes a significant architectural decision, create or update
an ADR in:

`08-Decisions/` (if folder exists — create if needed)

Use:

`ADR-NNN-Short-Decision-Name.md`

Each ADR should contain:

# Decision Title

## Status

Proposed / Accepted / Rejected / Superseded

## Context

What problem required a decision?

## Decision

What was decided?

## Reasoning

Why was this approach selected?

## Alternatives

What alternatives were considered?

## Trade-offs

What are the advantages and disadvantages?

## Consequences

What does this decision mean for the project?

## Related Systems

- [[System A]]
- [[System B]]
- [[System C]]

---

# Documentation Front Matter

Use YAML front matter for major documentation files when useful.

Example:

---
title: Memory Pipeline
type: system
status: active
domain: memory
---

Do not add metadata that cannot be verified.

---

# Documentation Quality Standard

Good documentation should allow another AI agent or developer to understand:

- What the system does.
- Why it exists.
- Where it lives in the codebase.
- How it interacts with other systems.
- What inputs it receives.
- What outputs it produces.
- What dependencies it has.
- What assumptions it makes.
- What constraints exist.
- How it should be modified safely.

---

# Documentation Quality Standard

Good documentation should allow another AI agent or developer to understand:

- What the system does.
- Why it exists.
- Where it lives in the codebase.
- How it interacts with other systems.
- What inputs it receives.
- What outputs it produces.
- What dependencies it has.
- What assumptions it makes.
- What constraints exist.
- How it should be modified safely.

---

# Completion Report

After documentation is completed, the specialist should report:

Documentation Status:
- Created / Updated / Not Required

Files:
- List documentation files created or modified.

Wiki-links:
- List important Wiki-links added or updated.

Architecture Impact:
- None / Low / Medium / High

ADR:
- Created / Updated / Not Required

Documentation Notes:
- Briefly explain what knowledge was preserved.

---

# Critical Rule

Never claim that documentation was updated unless the files were actually
created or modified.

Never claim Wiki-links were added unless they were actually added.

Documentation must represent the real state of the Mai AI project.

The objective is to maintain a living, interconnected engineering knowledge
base for Mai AI.