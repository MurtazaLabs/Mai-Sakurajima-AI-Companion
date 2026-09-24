# Output Formats, Scoring System & Confidence Guide

---

## Full Analysis Report (18 Sections)

Run in Full Analysis Mode. Every section is required. Omit none.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRINCIPAL ENGINEER CODEBASE REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 1. EXECUTIVE SUMMARY
[4–6 sentences: what the system is, overall quality verdict, most critical finding,
 top strength, and the single most important thing to fix first]

## 2. PROJECT DISCOVERY REPORT
[From Phase 1: purpose, users, tech stack, entry points, major components]

## 3. ARCHITECTURE MAP
[From Phase 2: architecture style, layer diagram, component map, violations found]

## 4. DEPENDENCY REPORT
[From Phase 3: fan-in/fan-out analysis, circular deps, hidden deps, external audit]

## 5. DATA FLOW REPORT
[From Phase 4: sources, transformation pipeline, stores, data risks]

## 6. CONTROL FLOW REPORT
[From Phase 5: critical paths, failure paths, SPOFs, async/sync model]

## 7. TECHNICAL DEBT REPORT
[All debt items in DEBT-NNN format, sorted by severity]

## 8. CODE SMELL REPORT
[All smells in SMELL-NNN format, with location and fix]

## 9. SCALABILITY REPORT
[User-scale predictions, bottlenecks, horizontal scaling blockers]

## 10. MAINTAINABILITY REPORT
[Documentation, naming, complexity, onboarding difficulty, refactor risk]

## 11. RISK ASSESSMENT
[All risks in RISK-NNN format, sorted by severity]

## 12. NEW DEVELOPER GUIDE
[Full onboarding guide — structure, important files, workflows, pitfalls]

## 13. REFACTOR ROADMAP
[All refactor items in REFACTOR-NNN format, sorted by priority]

## 14. TOP PRIORITY ISSUES
[The 5 most critical things to fix, in priority order, with specific actions]
1. [Issue] → [Specific action] → [Expected impact]
2. ...

## 15. POSITIVES
[Evidence-backed strengths — specific, not generic]

## 16. NEGATIVES
[Evidence-backed weaknesses — specific, not generic, with locations]

## 17. FINAL RECOMMENDATIONS
[Strategic 30/60/90 day action plan]
  Immediate (this week):    [critical fixes]
  Short-term (30 days):     [high-priority improvements]
  Long-term (90 days):      [architectural evolution]

## 18. OVERALL SCORE
[Full 9-category scorecard — see scoring section below]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 9-Category Scoring System

### Score Output Format

```
┌──────────────────────────────────────────────┐
│          ARCHITECTURE SCORECARD              │
├─────────────────┬────────┬───────────────────┤
│ Category        │ Score  │ Assessment        │
├─────────────────┼────────┼───────────────────┤
│ Architecture    │  X/10  │ [one-line note]   │
│ Maintainability │  X/10  │ [one-line note]   │
│ Scalability     │  X/10  │ [one-line note]   │
│ Reliability     │  X/10  │ [one-line note]   │
│ Modularity      │  X/10  │ [one-line note]   │
│ Code Quality    │  X/10  │ [one-line note]   │
│ Technical Debt  │  X/10  │ [one-line note]   │
│ Documentation   │  X/10  │ [one-line note]   │
│ Security        │  X/10  │ [one-line note]   │
├─────────────────┼────────┼───────────────────┤
│ OVERALL         │  X/10  │ [grade]           │
└─────────────────┴────────┴───────────────────┘

Status:  🟢 Excellent (9-10)  🟡 Acceptable (7-8)
         🟠 Needs Work (5-6)  🔴 Critical (1-4)

Grade:   A (9.0–10)  B (7.0–8.9)  C (5.0–6.9)
         D (3.0–4.9)  F (< 3.0)
```

### Scoring Rubrics

**Architecture (1–10)**
- 9–10: Clean layering, SOLID throughout, clear boundaries, designed for change
- 7–8: Good structure with minor violations, mostly maintainable
- 5–6: Identifiable layers but mixed concerns and coupling
- 3–4: God classes, no real layering, scattered logic
- 1–2: No discernible architecture, spaghetti throughout

**Maintainability (1–10)**
- 9–10: Self-documenting, well-tested, easy to change without breaking things
- 7–8: Mostly maintainable, some risky areas
- 5–6: Changes in some areas are risky, sparse testing
- 3–4: Brittle — changes routinely cause regressions
- 1–2: Any change is dangerous

**Scalability (1–10)**
- 9–10: Stateless, fully async, horizontal scaling ready, proper connection pooling
- 7–8: Can scale with moderate refactoring
- 5–6: Will hit bottlenecks at moderate load
- 3–4: Architectural blockers to scaling (sync I/O in async, in-process state)
- 1–2: Will not survive production load

**Reliability (1–10)**
- 9–10: Retry, timeout, circuit-breaking, health checks, graceful shutdown, monitoring
- 7–8: Most failure paths handled, minor gaps
- 5–6: Some unhandled failure modes, no circuit breaking
- 3–4: Silent failures common, SPOFs present, no retry
- 1–2: Will fail in production in the first week

**Modularity (1–10)**
- 9–10: Clear module boundaries, each module independently understandable and testable
- 7–8: Mostly modular, some coupling
- 5–6: Mixed — some modules clean, some tangled
- 3–4: High coupling, difficult to work on one module without touching others
- 1–2: Everything coupled to everything

**Code Quality (1–10)**
- 9–10: Consistent style, great naming, short focused functions, type hints, no magic numbers
- 7–8: Mostly clean with lapses
- 5–6: Inconsistent, some functions too long
- 3–4: Poor naming, magic numbers, deep nesting common
- 1–2: Unreadable

**Technical Debt (1–10)** (inverted — higher = LESS debt)
- 9–10: Minimal debt, actively maintained, no critical items
- 7–8: Some debt but manageable, no critical items
- 5–6: Moderate debt starting to slow development
- 3–4: Heavy debt, critical items present, velocity impacted
- 1–2: Debt crisis — any change is dangerous

**Documentation (1–10)**
- 9–10: README accurate, docstrings on all public APIs, ADRs present, inline comments explain why
- 7–8: Most things documented, minor gaps
- 5–6: Sparse documentation, some key areas undocumented
- 3–4: Minimal documentation, hard to onboard
- 1–2: No meaningful documentation

**Security (1–10)**
- 9–10: Input validated, parameterized queries, no secrets in code, principle of least privilege
- 7–8: Mostly secure, minor gaps
- 5–6: Some exposure, missing validation in places
- 3–4: Significant vulnerabilities (injection risk, hardcoded creds, unsafe exec)
- 1–2: Critical failures — not production-safe

---

## Confidence Scoring Guide

Apply to every finding. Never skip confidence rating.

```
🟢 HIGH CONFIDENCE
   Definition: Directly visible in the code, no inference required.
   Example:    "Line 47 of auth.py: password stored as MD5 hash"
   Use when:   You can point to the exact code that proves the finding.

🟡 MEDIUM CONFIDENCE
   Definition: Reasoned from patterns, some inference involved.
   Example:    "Based on the import structure, this module likely has tight coupling"
   Use when:   The finding is logical but based on partial evidence.

🔴 LOW CONFIDENCE
   Definition: Hypothesis based on limited evidence.
   Example:    "This might have performance issues at scale, but load profile unknown"
   Use when:   You're speculating — must be labeled clearly as assumption.
   Required:   State explicitly "This is an assumption — confirm with [specific evidence]"
```

**Rules:**
- A LOW CONFIDENCE finding must never be presented as a fact
- If you have < LOW confidence in something, don't include it — ask for more context instead
- Aggregate confidence: if a report section relies on many LOW confidence findings,
  flag the entire section as low confidence

---

## Partial Analysis (when not all files are provided)

When analyzing an incomplete picture of the codebase, always state upfront:

```
⚠️ PARTIAL ANALYSIS NOTICE
Files provided: [list]
Files referenced but not provided: [list]
Analysis based on: [what's available]
Limitations: [what can't be determined without the missing files]
Confidence impact: Several findings are 🟡 or 🔴 due to incomplete context.
```

Request the most important missing files before proceeding with low-confidence analysis.

---

## Report Length Guidance

| Mode | Expected Length |
|------|----------------|
| Full Analysis (18 sections) | Comprehensive — do not truncate |
| Single mode (e.g., Scalability only) | 1–2 pages focused on that section |
| Executive Summary only | 1 paragraph + scorecard |
| Due Diligence | Full DDD template — do not abbreviate |
| Onboarding Guide | Full guide — new devs need complete info |
| Quick debt scan | Debt register only, sorted by severity |