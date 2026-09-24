# Discovery & Ideation Modes

---

## PRODUCT DISCOVERY PROTOCOL {#discovery}

Run this before anything else, for any new idea or feature request — even a one-line request.
Discovery can be brief, but it must happen.

### The 4 Discovery Questions

```
PROBLEM:  What problem actually exists? (not "what feature is missing" — what PAIN exists)
USER:     Who experiences this problem? (be specific — "the user" isn't specific enough
          if there are multiple user types)
IMPACT:   Why does this problem matter? What happens if it's never solved?
GOAL:     What outcome is desired? (not "build feature X" — what changes for the user
          when this is solved?)
```

### Red Flags During Discovery

- The "problem" is actually "I want to build X" with no underlying pain identified —
  push back and ask what's actually broken without it
- The user can't articulate who experiences the problem — likely solving an imagined
  problem rather than a real one
- The desired outcome is the feature itself ("the goal is to have memory pruning") rather
  than a result ("the goal is for Mai to stop running out of relevant context after months
  of use") — restate in outcome terms

### Product Discovery Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRODUCT DISCOVERY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Problem:          [the actual pain point, not the proposed solution]
Target User:      [specific — who experiences this]
Pain Point:       [concrete description of what goes wrong today]
Business Impact:  [why this matters — for a personal project, this can be "user
                   satisfaction" or "project viability" rather than revenue]
Desired Outcome:  [what changes when this is solved — stated as a result, not a feature]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## IDEA ANALYSIS MODE {#idea-analysis}

When the user presents an idea (not yet a defined feature), evaluate it honestly before
helping build it out further.

### Evaluation Dimensions

**Value** — How much does this actually improve the product/experience if built well?
**Feasibility** — Can this realistically be built with current resources/constraints?
**Complexity** — How much engineering effort, and how much ongoing maintenance?
**Risk** — What could go wrong — technically, for the user, or for the product direction?
**Dependencies** — What does this idea require that doesn't exist yet?

### Idea Evaluation Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 IDEA EVALUATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Idea Summary:        [restate the idea in one clear sentence]
Potential Benefits:  [specific, not generic — what actually improves]
Potential Drawbacks: [be honest — complexity added, risk introduced, what gets harder]
Complexity:          [Low / Medium / High / Very High — with brief justification]
Risk:                [Low / Medium / High — with brief justification]

Recommendation:      [Build now / Build later / Build differently / Don't build —
                      with a one-sentence reason]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### How to Challenge Weak Ideas Respectfully

- Lead with what's genuinely good about the idea before raising concerns
- Frame concerns as questions when uncertain: "What happens when X grows to Y scale?"
- Frame concerns as statements when confident: "This will create Z problem because..."
- Always offer an alternative path forward, not just a rejection
- Distinguish "this is a bad idea" from "this is a good idea, wrong time" — most ideas
  fall into the second category

---

## FEATURE DEFINITION MODE {#feature-definition}

Transform a validated idea into a concrete feature specification.

### Feature Specification Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 FEATURE SPECIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Feature Name:      [clear, specific name]

Purpose:           [what this feature does, in one or two sentences]

User Value:        [what the user gains — concretely, not "better experience"]

Business Value:    [what the product/project gains — for personal projects, this might be
                    "reduces a known pain point" or "unblocks future feature X"]

Success Criteria:  [how we'll know this feature works — specific and observable]

Dependencies:      [what must exist or be true before this can be built]

Priority:          [Critical / High / Medium / Low — see Prioritization Mode for full logic]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## USER STORY GENERATOR {#user-stories}

### Standard User Story Format

```
As a [specific user type],
I want [specific capability],
So that [specific benefit/outcome].
```

Always generate three tiers:

**Primary User Stories** — the core use cases this feature must satisfy
**Secondary User Stories** — related but non-essential use cases
**Edge Cases** — unusual situations the feature must handle gracefully (not necessarily
perfectly, but not break either)

### User Story Quality Checklist

- [ ] Is the user type specific? ("As a returning user with 6+ months of conversation
      history" is better than "As a user")
- [ ] Is the want a capability, not an implementation detail? ("I want my AI to remember
      our past conversations" not "I want a ChromaDB vector store")
- [ ] Is the "so that" a genuine outcome, not a restatement of the want?
- [ ] Are edge cases genuinely edge cases, not core functionality mislabeled?

### User Stories Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 USER STORIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRIMARY:
  1. As a [user], I want [capability], so that [outcome].
  2. ...

SECONDARY:
  1. As a [user], I want [capability], so that [outcome].
  2. ...

EDGE CASES:
  1. As a [user in unusual situation], I want [graceful handling], so that
     [the experience doesn't break].
  2. ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## COMPETITIVE THINKING MODE {#competitive}

Only run this when genuinely applicable — not every feature needs competitive analysis,
especially for a personal project. Use when the user explicitly asks, or when comparing
approaches/alternatives is directly relevant to the decision.

### Competitive Analysis Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 COMPETITIVE ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Solution:   [what exists today — could be "nothing", an existing feature,
                     or a competing product/approach]

Alternative Solutions: [other ways to solve the same problem]
  Option A: [approach] — [tradeoffs]
  Option B: [approach] — [tradeoffs]

Competitive Advantages: [what this approach offers that alternatives don't]

Differentiators:    [what makes this approach genuinely distinct, not just different]

Weaknesses:         [honest assessment of where this approach falls short vs alternatives]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

For Mai_ai specifically: competitive thinking often means comparing approaches (e.g.,
"local Whisper vs. cloud STT", "ChromaDB vs. a simpler keyword search") rather than
comparing to commercial competitor products — adapt the template accordingly.