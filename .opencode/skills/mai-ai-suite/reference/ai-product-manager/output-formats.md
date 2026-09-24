# Full Output Format & Scoring

---

## Full Product Planning Report — 14 Sections

Use this full format for substantial features/ideas. For small, obvious changes, use a
lighter subset — see "Scaling the Output" below.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRODUCT PLAN: [Feature/Idea Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 1. EXECUTIVE SUMMARY
[3-5 sentences: what this is, why it matters, the recommendation, and the
 single most important next step]

## 2. PRODUCT DISCOVERY REPORT
[Problem / User / Pain Point / Impact / Desired Outcome]

## 3. FEATURE SPECIFICATION
[Name / Purpose / User Value / Business Value / Success Criteria / Dependencies / Priority]

## 4. USER STORIES
[Primary / Secondary / Edge Cases]

## 5. REQUIREMENTS DOCUMENT
[Full PRD — Objective/Background/Problem/Goals/Non-Goals/Requirements/Constraints/
 Dependencies/Success Metrics]

## 6. TECHNICAL PLAN
[Required Systems/Components/APIs/Databases/Agents + Build Order]

## 7. DEPENDENCY ANALYSIS
[Internal/External Dependencies, Blocking Factors, Dependency Risks]

## 8. RISK REPORT
[Product/Technical/User/Scalability/Security risks, severity-tagged]

## 9. ROADMAP
[Phased plan — typically 2-4 phases]

## 10. SUCCESS METRICS
[Primary/Secondary Metrics, Failure Indicators, Acceptance Criteria]

## 11. VALIDATION PLAN
[How to test, what to measure, what success/failure means]

## 12. SPECIALIST ASSIGNMENTS
[Which engineering skill(s) handle implementation, in what sequence]

## 13. IMPLEMENTATION PROMPT(S)
[Ready-to-use prompt(s) for each specialist handoff]

## 14. FINAL RECOMMENDATIONS & SCORE
[Overall recommendation + 9-category scorecard]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Scaling the Output to the Request Size

Not every request needs all 14 sections. Match the depth to the actual stakes:

```
TINY (config tweak, one-line fix):
  → Skip full report. Just confirm the problem/goal in a sentence and route to the
    right specialist directly.

SMALL (single function/feature, low risk, one file):
  → Discovery + Feature Spec + Quick Risk Check + Specialist Assignment. Skip full PRD,
    roadmap, and formal metrics — note them inline if relevant.

MEDIUM (new capability, multiple files, some risk):
  → Discovery + Feature Spec + User Stories + Lightweight PRD + Risk Report +
    Specialist Assignment + Implementation Prompt. Skip formal roadmap phases unless
    genuinely multi-stage.

LARGE (new subsystem, cross-cutting, high risk/complexity):
  → Full 14-section report. This is what the full template above is for.
```

Always state which depth level you're using and why, briefly, so the user isn't confused
about why a simple request didn't get a full PRD (or vice versa).

---

## 9-Category Scoring System

### Score Output Format

```
┌──────────────────────────────────────────────────┐
│            PRODUCT PLAN SCORECARD                 │
├───────────────────────┬────────┬──────────────────┤
│ Category               │ Score  │ Note             │
├───────────────────────┼────────┼──────────────────┤
│ User Value             │  X/10  │ [one line]       │
│ Business Value         │  X/10  │ [one line]       │
│ Technical Feasibility  │  X/10  │ [one line]       │
│ Complexity             │  X/10  │ [one line, lower=more complex if inverted, state clearly] │
│ Scalability            │  X/10  │ [one line]       │
│ Maintainability        │  X/10  │ [one line]       │
│ Risk Level             │  X/10  │ [one line, higher=lower risk, state clearly] │
│ Strategic Importance   │  X/10  │ [one line]       │
├───────────────────────┼────────┼──────────────────┤
│ OVERALL RECOMMENDATION │  X/10  │ [Build now / later / differently / don't] │
└───────────────────────┴────────┴──────────────────┘
```

Note: for Complexity and Risk Level, always state explicitly whether higher is better or
worse in context, since these are naturally "lower is better" dimensions — avoid ambiguity
by writing e.g. "Complexity: 3/10 (low complexity — good)" rather than a bare number.

### Scoring Rubrics

**User Value (1-10)**
- 9-10: Solves a real, frequently-felt pain point; clearly improves daily experience
- 7-8: Solves a real but less frequent pain point, or a moderate improvement
- 5-6: Nice-to-have; marginal improvement to experience
- 3-4: Minor value; mostly addresses an edge case or rare annoyance
- 1-2: Unclear or negligible user value

**Business Value (1-10)** (for personal projects: project viability/satisfaction value)
- 9-10: Directly advances core project goals or removes a major blocker
- 7-8: Meaningfully supports project direction
- 5-6: Tangential benefit, doesn't move core goals much
- 3-4: Minimal connection to project objectives
- 1-2: No clear connection to what the project is trying to achieve

**Technical Feasibility (1-10)**
- 9-10: Straightforward with current architecture and skills
- 7-8: Achievable with moderate new work, no major unknowns
- 5-6: Achievable but with real unknowns or new technology/approach needed
- 3-4: Significant technical uncertainty or missing prerequisites
- 1-2: Not currently feasible given constraints

**Complexity (1-10, lower = simpler = generally better)**
- 1-2: Trivial — single function/config change
- 3-4: Low — contained to one module, clear implementation path
- 5-6: Medium — touches multiple files/systems, moderate design decisions needed
- 7-8: High — cross-cutting, significant design work, multiple specialists needed
- 9-10: Very High — major subsystem, architecture-level decisions, high uncertainty

**Scalability (1-10)**
- 9-10: Designed to hold up well as usage/data/time grows
- 7-8: Will scale reasonably with minor future adjustments
- 5-6: Works now, will need revisiting at meaningfully higher scale
- 3-4: Likely to need rework relatively soon as usage grows
- 1-2: Will not hold up — scaling concerns should block this as-is

**Maintainability (1-10)**
- 9-10: Easy to understand, modify, and extend after the fact
- 7-8: Reasonably maintainable, follows existing patterns
- 5-6: Some future maintenance burden, but manageable
- 3-4: Likely to be confusing or fragile to maintain
- 1-2: High maintenance burden, hard to safely modify later

**Risk Level (1-10, higher = lower risk = better)**
- 9-10: Very low risk — easy to reverse, low blast radius if wrong
- 7-8: Low risk — contained impact, recoverable
- 5-6: Moderate risk — real consequences if it goes wrong, but manageable
- 3-4: High risk — significant consequences, harder to reverse
- 1-2: Very high risk — could seriously harm the product/system/user trust

**Strategic Importance (1-10)**
- 9-10: Unblocks or enables significant future work; core to the product vision
- 7-8: Meaningfully supports strategic direction
- 5-6: Standalone value, doesn't particularly enable or block other work
- 3-4: Minor strategic relevance
- 1-2: No strategic connection — purely isolated, one-off value

---

## Final Recommendations Format

Always close with a direct, unambiguous recommendation — not just a score table.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 FINAL RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Recommendation: [Build now / Build later / Build differently / Don't build]

Reasoning: [2-3 sentences synthesizing the discovery, risk, and scoring into a
            clear case for this recommendation]

If Building Now:
  Next Step: [the very first concrete action — usually the first specialist assignment]

If Building Later:
  Trigger Condition: [what should change before revisiting this — e.g., "once the
                      critical context-window bug is fixed" or "once usage data shows
                      this is actually a pain point"]

If Building Differently:
  Alternative Approach: [what to do instead, briefly]

If Not Building:
  Reason: [direct, honest explanation — and what problem (if real) should be solved
           a different way]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```