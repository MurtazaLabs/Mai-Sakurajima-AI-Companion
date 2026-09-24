# Requirements & Planning Modes

---

## PRODUCT REQUIREMENTS MODE {#prd}

The full PRD is the most complete artifact this skill produces. Use it for anything beyond
a small, obvious change — features that touch multiple files, change user-facing behavior,
or carry real risk if done wrong.

### Product Requirements Document Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRODUCT REQUIREMENTS DOCUMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## OBJECTIVE
[One or two sentences: what this PRD is for and what it will produce when done]

## BACKGROUND
[Context needed to understand why this matters now — prior attempts, related work,
 what prompted this]

## PROBLEM STATEMENT
[The specific problem, stated precisely — pulls from Product Discovery Report]

## GOALS
[What this MUST achieve to be considered successful]
- [Goal 1]
- [Goal 2]

## NON-GOALS
[What this explicitly will NOT attempt — prevents scope creep, sets clear boundaries]
- [Non-goal 1: explicitly out of scope, and why]
- [Non-goal 2]

## REQUIREMENTS
[Functional and non-functional requirements, prioritized]

Functional:
  - [The system MUST do X]
  - [The system MUST handle Y]

Non-Functional:
  - [Performance: must respond within Xs]
  - [Reliability: must degrade gracefully when Y is unavailable]

## CONSTRAINTS
[Real limitations that shape the solution — hardware (8GB RAM), budget (free-tier
 preference), existing architecture that must be preserved, time]

## DEPENDENCIES
[What this requires to exist or be true first — see Dependency Analysis for full detail]

## SUCCESS METRICS
[How we'll know this worked — see Success Metrics Designer for full detail]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### PRD Writing Rules

- Non-Goals are as important as Goals — they prevent the most common cause of scope creep
- Requirements should be testable statements, not vague aspirations
  ("Must respond within 2 seconds" not "should be fast")
- Constraints should be REAL constraints (hardware, budget, time) not assumed ones —
  ask if unclear rather than inventing limitations
- Keep the PRD proportional to the feature — a one-line config change doesn't need a
  full PRD; a new memory subsystem does

---

## TECHNICAL PLANNING MODE {#technical-planning}

Identify what's actually needed to build this, at a planning level — not implementation
detail (that's the specialist skills' job).

### What to Identify

```
REQUIRED SYSTEMS:    [which existing subsystems does this touch — memory, agents,
                      voice pipeline, scheduler, etc.]
REQUIRED COMPONENTS: [new classes/modules likely needed]
REQUIRED APIS:       [external services — LLM provider, embedding model, TTS/STT, etc.]
REQUIRED DATABASES:  [new tables/collections, or changes to existing schema]
REQUIRED AGENTS:     [new agent roles, or changes to existing agent behavior — N/A if
                      single-agent system]
```

### Technical Implementation Plan Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 TECHNICAL IMPLEMENTATION PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Required Systems:     [list, with how each is touched]
Required Components:  [new modules/classes — name and one-line purpose each]
Required APIs:        [external services needed]
Required Databases:   [schema changes or new storage needed]
Required Agents:      [N/A or list with role]

Build Order:
  1. [What must be built first — usually the lowest-level dependency]
  2. [Next]
  3. ...

Estimated Complexity: [Low / Medium / High / Very High]
Recommended Specialist: [see Engineering Coordination Mode]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

This plan is intentionally implementation-light — it identifies WHAT's needed and in WHAT
order, not the actual code. That's handed off to the specialist skill.

---

## DEPENDENCY ANALYSIS {#dependencies}

### Dependency Categories

**Internal Dependencies** — things within the existing system this feature relies on
(e.g., "requires the existing MemoryGraph to expose a new query method")

**External Dependencies** — third-party services, libraries, or APIs this feature relies on
(e.g., "requires a new embedding model", "requires OpenRouter API access")

**Blocking Factors** — things that must be resolved before work can even start
(e.g., "blocked until LLM_MAX_CONTEXT bug is fixed, since this feature relies on full
context being available")

**Risks** (dependency-specific) — what happens if a dependency changes or becomes
unavailable

### Dependency Analysis Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DEPENDENCY ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Internal Dependencies:
  - [Dependency] → [why needed] → [currently exists? yes/no/partial]

External Dependencies:
  - [Dependency] → [why needed] → [cost/reliability consideration]

Blocking Factors:
  - [Factor] → [must be resolved before] → [current status]

Dependency Risks:
  - [Risk] → [likelihood] → [mitigation]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## MVP ARCHITECT MODE {#mvp}

Separate what's essential from what's aspirational. This is one of the highest-value modes
for preventing scope creep on personal projects, where it's easy to keep adding "just one
more thing" before shipping anything.

### MoSCoW-Style Breakdown

```
MUST HAVE:    Without this, the feature doesn't solve the core problem. Ship blockers.
SHOULD HAVE:  Meaningfully improves the feature but isn't load-bearing. Can ship without,
              add soon after.
COULD HAVE:   Nice polish, low priority, build only if time/energy remains.
FUTURE VISION: Genuinely good ideas that are explicitly OUT of scope for now — captured
              so they're not lost, not forgotten, but not distracting from the MVP.
```

### MVP Plan Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 MVP PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Must Have:
  - [Item] — [why this is non-negotiable for the MVP]

Should Have:
  - [Item] — [why this matters but isn't blocking]

Could Have:
  - [Item] — [nice-to-have, low priority]

Future Vision:
  - [Item] — [good idea, explicitly deferred — and why now isn't the time]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### MVP Scoping Rules

- If removing an item doesn't break the core value proposition, it's not Must Have
- "Should Have" items should be genuinely buildable as fast-follows, not disguised Must Haves
- Be honest about Future Vision items — don't let them quietly become Must Haves through
  scope creep during implementation
- For a solo developer (like Murtaza working on Mai_ai), MVP scoping should account for
  available time/energy realistically, not just theoretical minimum scope

---

## FEATURE PRIORITIZATION MODE {#prioritization}

### Prioritization Dimensions

```
IMPACT:               How much does this improve the product if done well?
COMPLEXITY:           How much effort to build and maintain?
RISK:                 What could go wrong, and how costly would that be?
COST:                 Direct cost (API usage, compute) plus opportunity cost
STRATEGIC IMPORTANCE: Does this unblock other valuable work, or is it a dead end?
```

### Priority Assignment Logic

```
CRITICAL: High impact + (Low-Medium complexity OR blocking other critical work)
          → Do this now, before anything else

HIGH:     High impact + Medium-High complexity, OR Medium impact + Low complexity
          → Do this soon, in the current planning cycle

MEDIUM:   Medium impact + Medium complexity, with no urgency driver
          → Worth doing, not urgent — good for a slower week

LOW:      Low impact, OR high complexity with limited payoff
          → Backlog — revisit if priorities shift or complexity drops
```

### Feature Prioritization Table Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 FEATURE PRIORITIZATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
| Feature   | Impact | Complexity | Risk | Strategic | Priority |
|-----------|--------|------------|------|-----------|----------|
| [name]    | [H/M/L]| [H/M/L]    |[H/M/L]| [H/M/L]  | [C/H/M/L]|
| ...       |        |            |      |           |          |

Reasoning per item:
  [Feature]: [why this priority — reference the dimensions above]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```