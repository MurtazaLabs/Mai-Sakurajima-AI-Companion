# Task Classification, Routing & Coordination

---

## TASK CLASSIFICATION ENGINE {#classification}

Run this for every incoming request, even briefly. This is what makes routing deliberate
rather than reflexive.

### Task Types

```
Bug Fix              → something is broken, needs correction
Feature Request       → something new should be built
Architecture Review   → understand/evaluate system structure
Memory Review         → memory system specifically
Prompt Review         → prompt design/behavior specifically
Database Review       → schema/query/storage specifically
Security Review       → vulnerabilities, exposure, safety
Performance Review    → speed, cost, efficiency
Documentation Request → needs to be written down/preserved
Product Planning      → should we build this, what's the plan
Research Task         → needs investigation before a decision can be made
System Audit          → full or multi-subsystem health check
```

### Classification Dimensions

**Complexity** — Low / Medium / High / Very High
- Low: single function, obvious fix, one file
- Medium: multiple files, some design decisions needed
- High: cross-cutting, multiple specialists needed, real unknowns
- Very High: architecture-level, significant uncertainty, major effort

**Priority** — see Priority Engine in `tracking-risk-decisions.md#priority` for full logic

### Task Classification Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 TASK CLASSIFICATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Request:               [restate what was asked, in one sentence]
Task Type:             [from the list above — can be more than one]
Complexity:            [Low/Medium/High/Very High]
Priority:              [P0/P1/P2/P3 — see Priority Engine]
Recommended Specialist: [primary specialist]
Reason:                [why this specialist, specifically, for this task]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## AUTOMATIC SPECIALIST ROUTING {#routing}

### Routing Decision Logic

```
Bug in existing code             → python-master-engineer
New code needed                  → python-master-engineer
Multiple files / repo structure  → python-codebase-architect (then python-master-engineer
                                    for specific fixes it identifies)
Memory-specific issue            → memory-architecture-expert
Prompt-specific issue            → prompt-architect
Whole-system health question     → mai-ai-systems-auditor
"Should I build X" / planning    → ai-product-manager
"Document this" / "what's missing in docs" → knowledge-base-builder
Mixed/unclear                    → Run Task Classification first, then decide
```

### Specialist Assignment Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SPECIALIST ASSIGNMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Primary Specialist:      [skill name]
Supporting Specialists:  [list, or "none needed"]
Expected Deliverables:   [what each specialist will produce]
Estimated Complexity:    [Low/Medium/High/Very High]

Reasoning: [why this assignment, and why NOT the specialists not chosen —
            briefly, only if there's a non-obvious alternative someone might expect]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Routing Discipline

- Never assign a specialist "just in case" — if `python-master-engineer` alone can resolve
  a bug, don't also loop in `python-codebase-architect`
- When uncertain between two specialists, pick the one whose deliverable the user more
  directly needs right now, and note the other as a possible follow-up
- If the request is trivial enough that routing logic itself would be overkill (e.g., "what
  does this one-line error mean"), just answer directly — you don't need to formally invoke
  a specialist workflow for everything

---

## PYTHON FILE WORKFLOW {#python-file}

Whenever a Python file is shared without a clear stated intent, determine what the user
is actually trying to accomplish before routing.

### Intent Detection Questions

```
Is there an error/traceback attached?        → likely Fix Bug
Is the user asking "what does this do"?       → likely Understand Code
Is the user asking for something new?          → likely Add Feature
Is the user expressing dissatisfaction with
  structure/readability/cleanliness?           → likely Refactor
Is the file part of a larger system being
  evaluated as a whole?                        → likely Review Architecture
Is there a stated concern about speed/cost?    → likely Review Performance
Is there a stated concern about safety/
  exposure/secrets?                             → likely Review Security
```

### Resulting Routing

```
Understand Code        → python-master-engineer (explain mode)
Fix Bug                 → python-master-engineer (debug mode)
Add Feature              → python-master-engineer, possibly preceded by
                          ai-product-manager if the feature is still vague
Refactor                 → python-master-engineer (refactor mode)
Review Architecture       → python-codebase-architect
Review Performance        → python-master-engineer (performance mode) for a single file,
                          python-codebase-architect for system-wide performance
Review Security            → python-master-engineer (security mode) for a single file,
                          mai-ai-systems-auditor for system-wide security
```

If intent genuinely can't be determined from context, ask directly rather than guessing —
a wrong guess wastes more time than a clarifying question.

---

## MULTI-SPECIALIST COORDINATION {#multi-specialist}

For larger initiatives that genuinely span multiple specialist domains, sequence the work
explicitly rather than running specialists in an arbitrary order.

### Sequencing Principles

- Design/analysis specialists generally precede implementation specialists
  (`memory-architecture-expert` or `prompt-architect` before `python-master-engineer`)
- System-wide understanding precedes targeted fixes
  (`python-codebase-architect` or `mai-ai-systems-auditor` before diving into specific files)
- Documentation generally comes last, once the actual implementation is settled
  (`knowledge-base-builder` after the work is done, not before)
- Product strategy precedes everything if the request is still idea-shaped
  (`ai-product-manager` first if "should we build this" hasn't been answered yet)

### Workflow Coordination Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 WORKFLOW COORDINATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Initiative: [name/description]

Specialist 1: [name]
  Responsibilities: [what they handle]
  Deliverables:     [what they produce]
  Dependencies:     [what they need before starting — usually "none, goes first"]

---

Specialist 2: [name]
  Responsibilities: [what they handle]
  Deliverables:     [what they produce]
  Dependencies:     [what they need — usually Specialist 1's output]

---

[continue for each specialist involved]

Overall Sequence: [1 → 2 → 3, with brief reasoning for the order]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Example Coordination

```
Request: "Add a feature where Mai notices when conversations have been emotionally
heavy and gently checks in later"

Specialist 1: memory-architecture-expert
  Responsibilities: Design how emotional weight is detected/stored/retrieved
  Deliverables: Memory schema addition, retrieval logic for "recent heavy moments"
  Dependencies: None — goes first

Specialist 2: prompt-architect
  Responsibilities: Design how the check-in is expressed without feeling clinical/forced
  Deliverables: Character-consistent check-in prompt, trigger condition wording
  Dependencies: Needs to know what data Specialist 1's design makes available

Specialist 3: python-master-engineer
  Responsibilities: Implement detection logic, wire into autonomy engine, implement
                    the trigger
  Deliverables: Working code
  Dependencies: Needs Specialist 1's schema and Specialist 2's prompt design

Specialist 4: knowledge-base-builder
  Responsibilities: Document the new memory field and the new autonomy behavior
  Deliverables: Updates to MEMORY_SYSTEM.md and AGENTS.md (or autonomy docs)
  Dependencies: Needs the implementation finalized

Overall Sequence: 1 → 2 → 3 → 4
```