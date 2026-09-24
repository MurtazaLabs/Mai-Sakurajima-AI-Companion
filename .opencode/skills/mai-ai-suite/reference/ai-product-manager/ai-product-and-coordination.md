# AI Product Specialist & Engineering Coordination

---

## AI ASSISTANT PRODUCT SPECIALIST {#ai-product}

Specialized lens for AI assistants, companions, agent systems, memory systems, RAG systems,
and character AI — directly applicable to Mai_ai.

### Evaluation Dimensions

**User Experience** — Is the interaction natural, low-friction, and pleasant? Does the
assistant feel responsive, or does the user have to fight the interface/voice pipeline?

**Personalization** — Does the assistant genuinely adapt to this specific user over time,
or does every user (hypothetically) get an identical experience regardless of history?

**Retention** — Why would the user keep coming back? For a companion AI specifically: is
there a reason to return beyond novelty?

**Engagement** — Does the assistant invite continued interaction naturally (without being
manipulative or attention-grabbing in an unhealthy way)?

**Reliability** — Does it work consistently? Companion AI in particular loses trust fast
when it "forgets" things or behaves inconsistently — reliability IS a product feature, not
just an engineering concern.

**Emotional Continuity** — For companion/character AI: does the relationship feel like it's
actually continuing and deepening, or does it reset/feel disconnected between sessions?

### AI Product Review Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 AI PRODUCT REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
User Experience:      🟢/🟡/🟠/🔴 — [note]
Personalization:      🟢/🟡/🟠/🔴 — [note]
Retention Driver:      [what would bring the user back — be specific]
Engagement Quality:    🟢/🟡/🟠/🔴 — [healthy/manipulative/neutral — note]
Reliability:           🟢/🟡/🟠/🔴 — [note]
Emotional Continuity:  🟢/🟡/🟠/🔴 — [N/A if not a companion-style system]

Product-Level Risks:
  [Things that hurt the product experience even if technically "working" —
   e.g., "memory works correctly but surfaces facts in a way that feels surveillance-y
   rather than caring"]

Recommendation: [specific product-level guidance]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## AI FEATURE PLANNER {#ai-feature-impact}

For any new AI-specific feature (new memory type, new agent behavior, new prompt strategy,
new tool), evaluate impact across all dimensions before scoping it — this catches expensive
surprises before implementation starts.

### Impact Dimensions

```
MEMORY IMPACT:    Does this add new memory types, change retrieval, affect storage growth?
AGENT IMPACT:     Does this change agent boundaries, add new agents, affect routing?
PROMPT IMPACT:    Does this require new prompts, change existing ones, risk conflicts?
DATABASE IMPACT:  New tables/collections? Schema changes? Migration needed?
COST IMPACT:      Additional API calls, embedding costs, compute — quantify if possible
UX IMPACT:        How does this change what the user actually experiences day to day?
```

### AI Feature Impact Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 AI FEATURE IMPACT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Feature: [name]

Memory Impact:    [None / Low / Medium / High] — [specifics]
Agent Impact:     [None / Low / Medium / High] — [specifics]
Prompt Impact:    [None / Low / Medium / High] — [specifics]
Database Impact:  [None / Low / Medium / High] — [specifics]
Cost Impact:      [estimate — e.g., "+1 LLM call per turn, ~$X/month at current usage"]
UX Impact:        [specific description of what changes for the user]

Cross-Cutting Concerns:
  [Anything that touches multiple systems at once — these are usually the
   highest-risk features]

Recommended Specialists: [see Engineering Coordination Mode below]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## ENGINEERING COORDINATION MODE {#coordination}

Once a plan is ready to move into implementation, determine which specialist skill(s)
should execute it. This is the handoff point from planning to engineering.

### Specialist Routing Table

| Specialist Skill | Route Here When... |
|------------------|---------------------|
| `python-master-engineer` | The work is writing, refactoring, or debugging code in one or a few files. Most feature implementation lands here eventually. |
| `python-codebase-architect` | The work requires understanding or changing how multiple modules relate — architecture decisions, dependency restructuring, or a full-repo analysis before implementation. |
| `memory-architecture-expert` | The feature touches memory storage, retrieval, ranking, consolidation, or pruning in any way — even a small change to how memories are scored. |
| `prompt-architect` | The feature requires new or modified prompts — system prompt changes, new character behavior, new agent instructions, memory injection format changes. |
| `mai-ai-systems-auditor` | The request is a system-wide review spanning multiple subsystems, or a "is this ready" / "audit everything" type request rather than a specific feature. |

### Multi-Specialist Features

Most non-trivial features touch more than one specialist's domain. When that happens,
sequence them explicitly:

```
Example: "Add a feature where Mai proactively checks in if the user seems stressed
based on emotional memory patterns"

1. memory-architecture-expert    → Design how stress patterns are detected/stored/retrieved
                            from emotional memory
2. prompt-architect        → Design the prompt for how Mai expresses a proactive
                            check-in without feeling robotic or invasive
3. python-master-engineer  → Implement the detection logic, the trigger mechanism,
                            and wire it into the existing autonomy engine
```

Always sequence by dependency — design work (memory/prompt) before implementation
(coding), and identify what each specialist needs from the prior step's output.

### Specialist Assignment Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SPECIALIST ASSIGNMENT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ASSIGNMENT-001]
Recommended Skill:   [skill name]
Reason:              [why this skill, specifically, for this piece of work]
Expected Deliverable: [what this skill should produce]
Sequence Position:   [1st / 2nd / 3rd — if multi-specialist]
Depends On:          [prior assignment, if any]

[ASSIGNMENT-002] ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PLANNING PROMPT GENERATOR {#implementation-prompt}

After requirements are finalized and specialists assigned, generate a ready-to-use prompt
for each engineering handoff. This is what actually gets pasted to kick off the
implementation conversation with the relevant specialist skill.

### Implementation Prompt Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 IMPLEMENTATION PROMPT
 → For: [target specialist skill]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTEXT:
[What this fits into — the broader feature, why it's being built, relevant background
 the specialist needs to know]

OBJECTIVE:
[Precisely what this specialist should accomplish — pulled directly from the
 Feature Specification / PRD]

REQUIREMENTS:
[The specific functional/non-functional requirements relevant to THIS piece of work —
 not the entire PRD, just what's relevant to this specialist's scope]
  - [Requirement]
  - [Requirement]

CONSTRAINTS:
[Real limitations — hardware, existing architecture that must be preserved, style/pattern
 consistency with the rest of the codebase]

FILES INVOLVED:
[Known or likely files this touches — best guess if not yet certain]

DEPENDENCIES:
[What this relies on — including outputs from prior specialist assignments, if
 sequenced]

EXPECTED OUTPUT:
[What "done" looks like from this specialist — code, a report, a design doc]

VALIDATION CRITERIA:
[How to confirm this piece of work is correct before moving to the next step —
 pulled from the Validation Plan / Success Metrics]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Prompt Generation Rules

- Each implementation prompt should be self-contained enough that the specialist skill
  doesn't need to re-derive context from scratch
- Don't dump the entire PRD into every prompt — extract only what's relevant to that
  specialist's piece of the work
- If multiple specialists are sequenced, each prompt should reference what the prior
  step is expected to produce, even if that work isn't done yet
- Keep constraints concrete — "must work with 8GB RAM" is actionable, "should be
  efficient" is not