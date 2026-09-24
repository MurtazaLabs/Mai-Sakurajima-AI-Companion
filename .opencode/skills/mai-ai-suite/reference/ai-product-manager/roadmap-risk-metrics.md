# Roadmap, Risk & Metrics Modes

---

## ROADMAP GENERATOR {#roadmap}

Convert goals into sequenced, executable phases. Each phase should be independently
shippable/valuable where possible — avoid designing a roadmap where nothing works until
the final phase completes.

### Roadmap Design Principles

- Phase 1 should deliver real value on its own, not just lay groundwork invisible to the user
- Each phase should have a clear "done" definition — vague phases never actually complete
- Order phases by dependency AND by value — don't bury the highest-value work in Phase 3
  just because it's "supposed" to come after infrastructure work, if a leaner path exists
- Realistic phase count for most features: 2-4. More than that usually means the feature
  should be broken into separate features with separate roadmaps

### Roadmap Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ROADMAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## PHASE 1 — [Name]
Objective:        [what this phase achieves]
Tasks:
  - [Task]
  - [Task]
Deliverables:      [concrete, observable outputs]
Success Criteria:  [how we know this phase is actually done]

## PHASE 2 — [Name]
Objective:         [what this phase achieves]
Tasks:
  - [Task]
  - [Task]
Deliverables:      [concrete, observable outputs]
Success Criteria:  [how we know this phase is actually done]

## PHASE 3 — [Name]
Objective:         [what this phase achieves]
Tasks:
  - [Task]
  - [Task]
Deliverables:      [concrete, observable outputs]
Success Criteria:  [how we know this phase is actually done]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## RISK ASSESSMENT MODE {#risk}

### Risk Categories

**Product Risks** — the feature doesn't actually solve the problem, or solves it in a way
that creates a worse problem (e.g., adding proactive notifications that become annoying)

**Technical Risks** — implementation complexity, integration difficulty, technical debt
introduced

**User Risks** — confusing UX, broken expectations, privacy concerns, trust erosion
(especially relevant for companion AI — e.g., a memory feature that makes Mai seem like
she's "spying" rather than "remembering")

**Scalability Risks** — works fine now, breaks down as usage/data/time grows

**Security Risks** — new attack surface, data exposure, unsafe execution paths

### Risk Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 RISK REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[RISK-001]
Category:    [Product / Technical / User / Scalability / Security]
Severity:    🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Low
Description: [what the risk is]
Likelihood:  [Certain / Likely / Possible / Unlikely]
Impact:      [what happens if this risk materializes]
Mitigation:  [specific way to reduce or handle this risk]

[RISK-002] ...

Summary: [N] critical, [N] high risks identified. [Overall risk posture: Low/Med/High]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## SUCCESS METRICS DESIGNER {#metrics}

### Metric Design Rules

- Metrics must be observable — if you can't measure it, it's not a metric, it's a hope
- Prefer leading indicators (predict success early) alongside lagging indicators
  (confirm success after the fact)
- For personal/solo projects, "metrics" can be qualitative but should still be specific
  and checkable (e.g., "Mai correctly recalls a fact mentioned 2+ weeks ago in 8/10 test
  conversations" is measurable even without analytics infrastructure)

### Success Metrics Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SUCCESS METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Primary Metrics:
  - [Metric] — [target value/threshold] — [how measured]

Secondary Metrics:
  - [Metric] — [target value/threshold] — [how measured]

Failure Indicators:
  [Specific signs this feature is NOT working — not just "low primary metric" but
   concrete failure patterns to watch for]
  - [Indicator]

Acceptance Criteria:
  [The specific, binary conditions that must be true to consider this feature complete
   and working]
  - [ ] [Criterion]
  - [ ] [Criterion]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PRODUCT VALIDATION MODE {#validation}

How to actually test whether the feature works before considering it done.

### Validation Plan Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 VALIDATION PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
How to Test:
  [Specific test approach — manual conversation testing, scripted test cases,
   automated tests if applicable]

What to Measure:
  [Specific observable signals during testing]

Test Scenarios:
  1. [Happy path scenario]
  2. [Edge case scenario]
  3. [Failure/degraded scenario]

What Success Means:
  [Concrete definition — when do we know this is genuinely working, not just
   "seems to work in one conversation"]

What Failure Means:
  [Concrete definition — when do we know this needs more work before shipping/using]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

For AI assistant features specifically, recommend testing across:
- A short conversation (immediate behavior)
- A long conversation (does it hold up over many turns)
- A multi-session test (does it persist correctly across restarts)
- An adversarial/edge-case input (does it degrade gracefully)

---

## PROJECT TRACKING MODE {#tracking}

### Project Status Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PROJECT STATUS REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPLETED:
  - [Item] — [when/how verified]

IN PROGRESS:
  - [Item] — [current state, what's left]

BLOCKED:
  - [Item] — [what's blocking it, what's needed to unblock]

FUTURE:
  - [Item] — [planned but not started, rough priority]

Overall Status: [On track / At risk / Blocked / Ahead of plan]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Use this mode when the user asks for a status check across an ongoing feature or project,
synthesizing prior planning artifacts (PRD, roadmap) against what's actually been
reported as done.