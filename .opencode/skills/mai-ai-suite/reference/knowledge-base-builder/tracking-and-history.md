# Decision Log, Change Log, Technical Debt & Knowledge Graph

---

## DECISION LOG BUILDER {#decisions}

The single highest-value document for preventing "why did we do it this way?" confusion
months later. Pulls naturally from `ai-product-manager` planning sessions.

### Why This Matters

Code shows WHAT was built. Decision logs show WHY — and more importantly, what alternatives
were rejected and why. Without this, every future maintainer (including future-you) risks
re-litigating settled decisions or, worse, "fixing" something that was deliberately built
that way for a reason now forgotten.

### DECISIONS.md Template

```markdown
# Decision Log

## [DECISION-NNN] [Decision Title]
**Date**: [date]
**Owner**: [who made/drove this decision]

**Decision**: [what was decided, stated clearly]

**Reason**: [why — the actual problem this solves or goal it serves]

**Alternatives Considered**:
- [Alternative A]: [why it was rejected]
- [Alternative B]: [why it was rejected]

**Risks**: [what could go wrong with this decision, accepted knowingly]

**Expected Outcome**: [what success looks like]

**Status**: [Active / Superseded by DECISION-NNN / Reverted — and why, if not Active]

---

[repeat per decision, most recent first]
```

### When to Create a Decision Entry

- Any architectural choice with real alternatives (e.g., "ChromaDB vs. a simpler keyword
  index for memory")
- Any choice that trades off something meaningful (e.g., "local Whisper over cloud STT,
  accepting lower accuracy for privacy and zero cost")
- Any choice likely to be questioned later ("why isn't this async?")
- Reversals of prior decisions — link explicitly to what's being superseded

### What NOT to Log

- Routine implementation choices with no real alternative worth recording
- Decisions that are obvious from the code and unlikely to be questioned
- Anything that's really a TODO or technical debt item (those belong in TECHNICAL_DEBT.md)

---

## CHANGE LOG BUILDER {#changelog}

### CHANGELOG.md Template (Keep a Changelog style)

```markdown
# Changelog

## [Unreleased]

### Added
- [New feature]

### Changed
- [Improvement to existing behavior]

### Fixed
- [Bug fix]

### Breaking Changes
- [Anything that changes existing behavior in an incompatible way]
**Migration**: [what existing users/code need to do]

---

## [Date or Version] — [Short Theme]

### Added
- [New feature]

### Changed
- [Improvement]

### Fixed
- [Bug fix]

### Breaking Changes
- [Breaking change] — **Migration**: [steps]

---
[repeat per release/period, most recent first]
```

### Changelog Writing Rules

- Write for the reader, not the committer — "Fixed memory retrieval returning negative
  similarity scores" not "fix chromadb bug"
- Group by category (Added/Changed/Fixed/Breaking) consistently
- Breaking changes always get a migration note — never leave the reader to figure out
  what to do
- For solo projects without formal releases, group by date or by theme ("Memory System
  Overhaul — March 2026") rather than forcing semantic versioning that doesn't fit the
  project's actual practice

---

## TECHNICAL DEBT DOCUMENTATION {#debt}

Pulls directly from `python-codebase-architect` and `mai-ai-systems-auditor` debt findings
when available — this doc's job is to make debt visible and trackable over time, not to
re-derive it.

### TECHNICAL_DEBT.md Template

```markdown
# Technical Debt Register

## 🔴 Critical
*Production-threatening — fix immediately*

### [DEBT-NNN] [Title]
**Location**: `path/to/file`
**Issue**: [what's wrong]
**Impact**: [what breaks or degrades]
**Risk**: [likelihood × severity]
**Suggested Fix**: [specific approach]
**Estimated Effort**: [Low/Medium/High]
**Status**: [Open / In Progress / Resolved [date]]

[repeat per item]

## 🟠 High
*Likely future failures*
[same format]

## 🟡 Medium
*Maintainability concerns*
[same format]

## 🔵 Low
*Minor improvements*
[same format]

---
*Last updated: [date]*
*Source: [python-codebase-architect audit on [date] / mai-ai-systems-auditor audit on [date] / manual entry]*
```

### Debt Doc Maintenance Rules

- When an item is resolved, don't delete it — mark it Resolved with a date. The history of
  what debt existed and was fixed is itself valuable knowledge
- Re-run the relevant audit skill periodically and reconcile — stale debt registers are
  actively misleading (showing items as open that were already fixed, or missing new debt)
- Link debt items to the DECISIONS.md entry if the debt was a deliberate tradeoff
  ("we knew this would need revisiting — see DECISION-007")

---

## KNOWLEDGE GRAPH BUILDER {#knowledge-graph}

A lightweight relationship map for navigating larger systems — most valuable once a project
has enough components that "just read all the files" stops being a viable onboarding
strategy.

### KNOWLEDGE_GRAPH.md Template

```markdown
# Knowledge Graph

## Component Relationships

```
[Component A]
   ↓ (imports/calls)
[Component B]
   ↓ (writes to)
[Database]
   ↑ (reads from)
[Component C]
```

## Relationship Index

| From | To | Relationship | Notes |
|------|-----|--------------|-------|
| [Component A] | [Component B] | imports / calls / writes / reads / triggers | [context] |

## Central Components
*Highest connectivity — riskiest to change, most important to understand first*
- [Component]: [N connections] — [why it's central]

## Isolated Components
*Lowest connectivity — safest to change or extract independently*
- [Component]: [why it's isolated]

## Cross-System Links
*Relationships that span major subsystems (e.g., memory ↔ agents ↔ prompts)*
- [System A] ↔ [System B]: [nature of the link]

---
*Last updated: [date]*
```

### Building This Incrementally

For large/complex systems, build this graph incrementally rather than trying to map
everything at once:
1. Start with the central/highest-connectivity components (usually obvious — the ones
   imported everywhere)
2. Add their direct relationships
3. Expand outward only as far as is useful — a complete graph of a 16,000-line codebase
   is less useful than a focused graph of the 10 components that actually matter for
   understanding the system