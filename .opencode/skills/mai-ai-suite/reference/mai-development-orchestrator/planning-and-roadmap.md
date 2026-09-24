# Implementation Planning & Roadmap Modes

---

## IMPLEMENTATION PLANNING MODE {#implementation-planning}

Triggered after the user approves the Mandatory Planning Prompt Workflow offer. Converts
findings (from any specialist) into an executable plan.

### Implementation Plan Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 IMPLEMENTATION PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Objective:          [what this implementation should accomplish]

Background:         [context — what analysis/findings led here, which specialist
                     identified the need]

Current Problem:     [the specific issue or gap being addressed]

Desired Outcome:     [what changes when this is done — concrete, observable]

Constraints:         [real limitations — hardware, existing architecture to preserve,
                     time, must-not-break list]

Dependencies:        [what must exist/be true first]

Success Criteria:    [how we'll know this worked]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

For small/obvious fixes, this can be a few lines. Match the depth to the actual stakes —
don't produce a heavyweight plan for a one-line config change.

---

## ENGINEERING ROADMAP GENERATOR {#roadmap}

For medium or large tasks only. Skip for small, single-specialist work — a roadmap for a
bug fix is overhead, not value.

### Roadmap Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ENGINEERING ROADMAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## PHASE 1 — [Name]
Objective:   [what this phase achieves]
Tasks:
  - [task]
  - [task]
Validation:  [how we confirm this phase is actually done correctly]

## PHASE 2 — [Name]
Objective:   [what this phase achieves]
Tasks:
  - [task]
Validation:  [how we confirm this phase is done]

## PHASE 3 — [Name] (continue as needed)
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Each phase should be independently valuable where possible — avoid a roadmap where nothing
works until the final phase completes.

---

## AI PROMPT GENERATOR {#ai-prompt}

Generate prompts optimized for whichever AI coding assistant/specialist will execute the
plan — most often this means generating a prompt to kick off a `python-master-engineer`
(or other specialist) conversation with full context pre-loaded.

### AI Implementation Prompt Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 AI IMPLEMENTATION PROMPT
 → For: [target specialist]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTEXT:
[What this fits into, why it's being built, relevant background]

PROBLEM:
[The specific issue or gap, stated precisely]

REQUIREMENTS:
  - [Requirement]
  - [Requirement]

CONSTRAINTS:
[Real limitations — hardware (8GB RAM), existing patterns to preserve, style consistency]

EXPECTED BEHAVIOR:
[What correct behavior looks like once this is implemented]

FILES INVOLVED:
[Known or likely files — best guess if uncertain]

DEPENDENCIES:
[What this relies on — including outputs from prior specialist work if sequenced]

SUCCESS CRITERIA:
[Specific, observable conditions that confirm this is done correctly]

VALIDATION REQUIREMENTS:
[How to test/verify before considering this complete]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Prompt Generation Rules

- Never generate a vague prompt — every section above must have concrete content, not
  placeholders
- Pull constraints from what's actually known about the project (8GB RAM, local-first,
  free-tier preference) rather than generic engineering advice
- If multiple specialists are sequenced, each prompt should explicitly reference what the
  prior step is expected to produce

---

## BUG RESOLUTION PLANNER {#bug-resolution}

### Bug Resolution Plan Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 BUG RESOLUTION PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Issue:           [what's broken, observed behavior]

Root Cause:      [why it's happening — evidence-based, not guessed]

Fix Strategy:    [the approach to resolve it]

Implementation Steps:
  1. [step]
  2. [step]

Testing Plan:    [how to confirm the fix actually works, including edge cases]

Rollback Plan:   [how to revert if the fix causes new problems]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Route the actual fix implementation to `python-master-engineer` — this plan is the
specification, not the code.

---

## FEATURE DEVELOPMENT PLANNER {#feature-development}

### Feature Implementation Plan Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 FEATURE IMPLEMENTATION PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Feature Goal:          [what this feature accomplishes]

Business Value:        [why it matters — for personal projects, this is project/user
                       value rather than revenue]

Technical Requirements: [what must be built]

Dependencies:           [what this relies on]

Implementation Phases:  [link to Roadmap if multi-phase, or list directly if simple]

Testing Strategy:       [how this gets validated]

Deployment Strategy:    [for Mai_ai: usually "restart the local process" — note any
                       migration steps for memory/database changes]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If the feature is still idea-stage (value/scope unclear), route to `ai-product-manager`
first rather than generating this plan prematurely.

---

## REFACTOR PLANNER {#refactor}

### Refactor Plan Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 REFACTOR PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Issue:       [what's wrong with the current state — debt, complexity, coupling]

Target State:        [what it should look like after]

Affected Components: [files/modules touched]

Risk Assessment:      [what could break, how likely, how bad]

Implementation Plan:  [the approach — prefer incremental over big-bang, see
                      python-codebase-architect's Strangler Fig guidance if relevant]

Rollback Strategy:    [how to revert if something goes wrong]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

For refactors identified via `python-codebase-architect`'s debt register, reference the
specific DEBT-NNN item this resolves.

---

## ARCHITECTURE EVOLUTION PLANNER {#architecture-evolution}

For proposed architecture changes — evaluate before recommending, don't just approve
because it sounds technically appealing.

### Evaluation Dimensions

```
BENEFITS:           What genuinely improves?
RISKS:              What could go wrong, and how costly?
COMPLEXITY:         How much harder does this make the system to understand?
MAINTENANCE COST:   What does this cost to keep working over time?
SCALABILITY IMPACT: Does this help or hurt future growth?
SECURITY IMPACT:    Does this open or close any risk surface?
LONG-TERM IMPACT:   Does this compound positively or create future debt?
```

### Architecture Evolution Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ARCHITECTURE EVOLUTION ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Proposed Change: [description]

Benefits:            [specific, evidence-based]
Risks:               [specific, with severity]
Complexity Added:    [Low/Medium/High/Very High]
Maintenance Cost:    [ongoing burden this creates]
Scalability Impact:  [Positive/Neutral/Negative — why]
Security Impact:     [Positive/Neutral/Negative — why]
Long-Term Impact:    [compounds well / creates debt / neutral]

Recommendation: [Proceed / Proceed with modifications / Defer / Reject]
Reasoning:       [direct, evidence-based justification]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

For substantial architecture changes, route the detailed structural analysis to
`python-codebase-architect` first, then use this evaluation to decide whether to proceed.