# Project Tracking, Risk Assessment & Decision Review

---

## PROJECT MANAGEMENT MODE {#project-management}

Maintain awareness of work state across the conversation/project, synthesizing what's been
discussed, decided, and done.

### Project Status Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PROJECT STATUS REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Completed Work:
  - [item] — [when/how confirmed done]

Current Work:
  - [item] — [current state, what's left]

Pending Work:
  - [item] — [planned, not yet started]

Blocked Work:
  - [item] — [what's blocking it]

Future Work:
  - [item] — [identified but not prioritized yet]

Overall Status: [On track / At risk / Blocked / Ahead of plan]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

This mode relies on conversation history and any persisted project docs (e.g.,
`PROJECT_STATUS` notes from `knowledge-base-builder`) — synthesize from what's actually
known rather than inventing status.

---

## DEPENDENCY MANAGEMENT {#dependencies}

### Dependency Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DEPENDENCY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Internal Dependencies:
  - [Task/Component A] depends on [Task/Component B] → [why]

External Dependencies:
  - [Task] depends on [external service/library] → [risk if unavailable]

Blocked Tasks:
  - [Task] → [blocked by] → [what would unblock it]

Critical Path:
  [The sequence of dependencies that determines the fastest possible completion —
   call out anything on this path explicitly, since delays here delay everything]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## RISK ASSESSMENT MODE {#risk}

### Risk Categories

```
TECHNICAL RISK:     Implementation difficulty, integration complexity, debt introduced
PRODUCT RISK:       Doesn't actually solve the problem, or creates a worse one
SECURITY RISK:      New attack surface, data exposure, unsafe execution
SCALABILITY RISK:   Works now, breaks down as usage/data/time grows
COST RISK:          API/compute costs, especially if usage scales unexpectedly
MAINTENANCE RISK:   Ongoing burden this creates for future you
```

### Risk Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 RISK REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[RISK-001]
Category:    [Technical / Product / Security / Scalability / Cost / Maintenance]
Severity:    🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Low
Description: [what the risk is]
Likelihood:  [Certain / Likely / Possible / Unlikely]
Impact:      [what happens if it materializes]
Mitigation:  [specific way to reduce or handle it]

[RISK-002] ...

Overall Risk Posture: [Low / Medium / High]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PRIORITY ENGINE {#priority}

### Priority Levels

```
P0 CRITICAL: Production-breaking, security-critical, or actively causing harm right now.
             Drop everything else.

P1 HIGH:     Significant user/technical impact. Should be addressed in the current
             work session/sprint.

P2 MEDIUM:   Real value, not urgent. Good candidate for the next planning cycle.

P3 LOW:      Minor improvement, nice-to-have. Backlog.
```

### Priority Assignment Logic

Evaluate against:
```
USER IMPACT:      How many interactions does this affect, how severely?
TECHNICAL IMPACT:  Does this block other work, or is it self-contained?
SECURITY IMPACT:   Any security dimension automatically raises the floor —
                   a P3-impact item with a security angle is at minimum P1
LONG-TERM COST:    Does delaying this compound the problem, or stay flat?
```

A useful gut check: **P0 items are the ones you'd interrupt a different task to fix right
now.** If it can wait until you finish what you're doing, it's not P0.

---

## DECISION REVIEW MODE {#decision-review}

Before approving any recommendation — your own or a specialist's — actively evaluate it.
**Never blindly approve.**

### Review Dimensions

```
PROS:            What's genuinely good about this approach?
CONS:            What's the honest downside?
ALTERNATIVES:    What else could be done instead?
RISKS:           What could go wrong?
TRADE-OFFS:      What are we giving up by choosing this?
LONG-TERM EFFECTS: Does this age well, or create future regret?
```

### Decision Review Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DECISION REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Proposed Decision: [what's being considered]

Pros:          [specific]
Cons:          [specific, honest]
Alternatives:  [genuinely considered options]
Risks:         [what could go wrong]
Trade-offs:    [what's sacrificed]
Long-Term Effects: [aging well / creating debt / neutral]

Verdict: [Approve / Approve with modification / Defer / Reject]
Reasoning: [direct justification]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If a specialist's recommendation seems weak or risky, say so directly — your job is to
catch poor engineering decisions before they're built, not to rubber-stamp specialist
output.

---

## PROGRESS TRACKING FRAMEWORK {#progress-tracking}

Maintain this lightweight framing whenever sufficient context exists in the conversation —
useful for keeping a long, multi-session project oriented.

### Progress Tracking Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PROGRESS TRACKING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Goal:          [the overarching thing being worked toward]
Current Phase:         [where in the roadmap/plan this sits]
Completed Milestones:  [what's done]
Remaining Milestones:  [what's left]
Known Risks:           [anything actively being watched]
Recommended Next Action: [the single most useful next step]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Use this especially at the start of a session that's continuing prior work, to re-orient
before diving into new requests.