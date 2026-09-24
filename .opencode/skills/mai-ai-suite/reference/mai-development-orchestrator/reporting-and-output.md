# Findings Interpretation, Executive Reporting & Required Output Format

---

## ANALYSIS INTERPRETATION ENGINE {#interpretation}

Convert raw specialist findings (technical, often dense) into actionable insight. This is
the translation layer between "here's what's wrong, in engineering detail" and "here's what
to actually do about it."

### Findings Summary Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 FINDINGS SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Root Cause:        [the underlying issue, in plain terms]
Impact:            [what this actually affects, in user/project terms — not just
                   technical terms]
Priority:          [P0/P1/P2/P3 — see Priority Engine]
Recommended Action: [the practical next step]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Translation Discipline

- A specialist might report "ChromaDB collection lacks cosine distance metric configuration"
  — your job is to also say plainly: "this means Mai's long-term memory has effectively not
  been working, and fixing it is a 2-line change"
- Don't strip out the technical detail entirely — preserve it for when implementation
  happens — but always lead with what it MEANS before what it IS
- When multiple specialists report overlapping findings (e.g., both
  `python-codebase-architect` and `mai-ai-systems-auditor` flag the same scheduler bug),
  consolidate into one finding rather than presenting it twice

---

## EXECUTIVE REPORTING MODE {#executive-reporting}

Concise, CTO-to-stakeholder style summary. Use when the user wants the headline without
the full detail — or as the opening of any larger report.

### Executive Summary Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 EXECUTIVE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Situation:   [where things stand, in 1-2 sentences]
Key Findings:        [the 2-3 things that matter most right now]
Recommended Action:  [what to do]
Priority:            [P0/P1/P2/P3]
Next Step:           [the single, concrete next action]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Keep this genuinely short — if it's longer than the detailed report it's summarizing,
it's not doing its job.

---

## KNOWLEDGE PRESERVATION INTEGRATION {#knowledge-integration}

After any major analysis (a significant bug resolution, a completed feature, an
architecture decision, a full audit), evaluate whether it's worth preserving and recommend
`knowledge-base-builder` involvement when it is.

### When to Recommend Documentation

```
A decision was made with real alternatives considered  → DECISIONS.md entry
A significant bug was fixed with a non-obvious root cause → note in TECHNICAL_DEBT.md
  (as resolved) or a troubleshooting note
A new subsystem or major feature was built              → corresponding system doc
  (MEMORY_SYSTEM.md, AGENTS.md, etc.)
An architecture change was made                         → ARCHITECTURE.md update
A full audit was completed                               → AI_ASSISTANT_OVERVIEW.md
  refresh, plus the specific findings into their relevant docs
```

### Recommendation Format

Keep this brief and natural — not a forced ritual:

> "This is worth capturing — want me to hand this off to knowledge-base-builder to update
> [specific doc]?"

Don't recommend documentation for routine, self-evident changes (a typo fix doesn't need a
decision log entry).

---

## REQUIRED OUTPUT FORMAT {#output-format}

For any substantive request that goes through classification and routing, structure the
response using this skeleton. Omit sections that don't apply (e.g., no RISK ANALYSIS needed
for a trivial one-line fix) — but make that omission a deliberate choice, not an oversight.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 MAI DEVELOPMENT ORCHESTRATOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK CLASSIFICATION:
  [from classification-and-routing.md#classification]

SPECIALIST ASSIGNMENT:
  [from classification-and-routing.md#routing]

COMPLEXITY ANALYSIS:
  [Low/Medium/High/Very High, with brief justification]

RISK ANALYSIS:
  [from tracking-risk-decisions.md#risk — abbreviated if low-stakes]

FINDINGS SUMMARY: (if specialist analysis has occurred)
  [from #interpretation]

RECOMMENDED ACTION:
  [the practical next step]

NEXT STEP:
  [the single most immediate thing to do]

PLANNING PROMPT AVAILABLE?
  [Always ask: "Would you like me to generate an implementation planning prompt
   based on these findings?" — Mandatory Planning Prompt Workflow]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**If the user approves planning** (responds yes to the Planning Prompt question), continue
with:

```
IMPLEMENTATION PLAN:       [from planning-and-roadmap.md#implementation-planning]
EXECUTION ROADMAP:         [from planning-and-roadmap.md#roadmap, if medium/large]
AI IMPLEMENTATION PROMPT:  [from planning-and-roadmap.md#ai-prompt]
VALIDATION CHECKLIST:      [specific, checkable items confirming correctness]
SUCCESS CRITERIA:          [from the Implementation Plan, restated as a checklist]
```

---

## SCORING FRAMEWORK {#scoring}

Used when evaluating proposed work, completed work, or specialist output quality.

### Score Output Format

```
┌──────────────────────────────────────────────────┐
│       ORCHESTRATOR EVALUATION SCORECARD            │
├──────────────────────────┬────────┬─────────────────┤
│ Category                  │ Score  │ Note            │
├──────────────────────────┼────────┼─────────────────┤
│ Clarity                   │  X/10  │ [one line]      │
│ Technical Quality         │  X/10  │ [one line]      │
│ Maintainability           │  X/10  │ [one line]      │
│ Scalability               │  X/10  │ [one line]      │
│ Risk Level                │  X/10  │ [one line, higher = lower risk] │
│ Implementation Readiness  │  X/10  │ [one line]      │
│ Overall Confidence        │  X/10  │ [one line]      │
└──────────────────────────┴────────┴─────────────────┘
```

### Scoring Rubrics

**Clarity (1-10)** — How well-defined is the task/plan/finding?
- 9-10: Crystal clear, no ambiguity in scope or approach
- 5-6: Generally clear, some open questions
- 1-2: Vague, needs significant clarification before proceeding

**Technical Quality (1-10)** — How sound is the proposed/actual implementation?
- 9-10: Excellent engineering, follows best practices, fits existing architecture
- 5-6: Acceptable, some concerns
- 1-2: Poor quality, significant issues

**Maintainability (1-10)** — How easy will this be to maintain going forward?
- 9-10: Easy to understand and safely modify later
- 5-6: Some future burden but manageable
- 1-2: High maintenance burden, fragile

**Scalability (1-10)** — Does this hold up as usage/data/time grows?
- 9-10: Designed for growth
- 5-6: Fine for now, will need revisiting
- 1-2: Will not hold up

**Risk Level (1-10, higher = lower risk)**
- 9-10: Very low risk, easy to reverse
- 5-6: Moderate risk, manageable
- 1-2: High risk, significant consequences if wrong

**Implementation Readiness (1-10)** — Is this actually ready to build?
- 9-10: Fully specified, dependencies clear, ready to hand to a specialist
- 5-6: Mostly ready, some gaps to fill first
- 1-2: Not ready — too many open questions

**Overall Confidence (1-10)** — How confident is this assessment overall?
- 9-10: High confidence, strong evidence behind every conclusion
- 5-6: Reasonable confidence, some assumptions made
- 1-2: Low confidence, significant unknowns remain — say so explicitly