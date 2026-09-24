# Full Output Formats & 14-Category Scoring

---

## Full Ecosystem Audit — 24-Section Report

Used in Full Ecosystem Audit mode. Every section required unless explicitly marked optional
for targeted audits.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 AI ASSISTANT ECOSYSTEM AUDIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 1. EXECUTIVE SUMMARY
[4-6 sentences: what the system is, overall health verdict, single most critical finding,
 top strength, single most important next step]

## 2. SYSTEM DISCOVERY REPORT
[Phase 1 output]

## 3. ARCHITECTURE REPORT (AI SYSTEM MAP)
[Phase 2 output]

## 4. RISK SURFACE (SYSTEM RISK MAP)
[Phase 3 output]

## 5. AGENT ARCHITECTURE REPORT
[Auditor 1 output]

## 6. PROMPT HEALTH REPORT
[Auditor 2 output]

## 7. CHARACTER CONSISTENCY REPORT
[Auditor 3 output — omit if no character/personality system present]

## 8. MEMORY HEALTH REPORT
[Auditor 4 output]

## 9. DATABASE HEALTH REPORT
[Auditor 5 output]

## 10. VECTOR DATABASE REPORT
[Auditor 6 output — omit if no vector store present]

## 11. RAG HEALTH REPORT
[Auditor 7 output — omit if no RAG pipeline present]

## 12. TOOL SYSTEM REPORT
[Auditor 8 output]

## 13. SECURITY REPORT
[Auditor 9 output]

## 14. PERFORMANCE REPORT
[Auditor 10 output]

## 15. RELIABILITY REPORT
[Auditor 11 output]

## 16. SCALABILITY REPORT
[Auditor 12 output]

## 17. TECHNICAL DEBT HEATMAP
[Auditor 13 output]

## 18. AI ASSISTANT HEALTH REPORT
[Synthesis]

## 19. PRODUCTION READINESS REPORT
[Synthesis]

## 20. TOP PRIORITY ISSUES
[Top 5 across all auditors, ranked by severity × impact]
1. [Issue] → [Source auditor] → [Specific fix] → [Expected impact]
2. ...

## 21. POSITIVES
[Evidence-backed strengths across the whole system — specific, not generic]

## 22. NEGATIVES
[Evidence-backed weaknesses across the whole system — specific, with locations]

## 23. CTO ASSESSMENT
[CTO Review output]

## 24. FINAL RECOMMENDATIONS & OVERALL SCORE
  Immediate (this week):  [critical fixes]
  Short-term (30 days):   [high-priority improvements]
  Long-term (90 days):    [strategic improvements]

  [14-category scorecard — see below]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 14-Category Scoring System

### Score Output Format

```
┌─────────────────────────────────────────────────┐
│        AI ECOSYSTEM SCORECARD                   │
├──────────────────────┬────────┬─────────────────┤
│ Category              │ Score  │ Note            │
├──────────────────────┼────────┼─────────────────┤
│ Architecture          │  X/10  │ [one line]      │
│ Agent Design          │  X/10  │ [one line]      │
│ Prompt Design         │  X/10  │ [one line]      │
│ Character Consistency │  X/10  │ [one line]      │
│ Memory System         │  X/10  │ [one line]      │
│ Database Design       │  X/10  │ [one line]      │
│ RAG Quality           │  X/10  │ [one line]      │
│ Security              │  X/10  │ [one line]      │
│ Performance           │  X/10  │ [one line]      │
│ Reliability           │  X/10  │ [one line]      │
│ Scalability           │  X/10  │ [one line]      │
│ Maintainability        │  X/10  │ [one line]      │
│ Production Readiness  │  X/10  │ [one line]      │
├──────────────────────┼────────┼─────────────────┤
│ OVERALL                │  X/10  │ [grade]         │
└──────────────────────┴────────┴─────────────────┘

Status:  🟢 Excellent (9-10)  🟡 Acceptable (7-8)
         🟠 Needs Work (5-6)  🔴 Critical (1-4)
Grade:   A (9.0-10) | B (7.0-8.9) | C (5.0-6.9) | D (3.0-4.9) | F (<3.0)
```

Note: if Character Consistency or RAG Quality don't apply (no personality system / no RAG),
omit that row and note "N/A — not present in this system" rather than scoring it.

### Scoring Rubrics

**Architecture (1-10)**
- 9-10: Clear component boundaries, clean data/context flow, no SPOFs in critical paths
- 7-8: Good structure, minor coupling issues
- 5-6: Identifiable structure but mixed concerns
- 3-4: Significant architectural confusion
- 1-2: No coherent architecture

**Agent Design (1-10)**
- 9-10: Clear boundaries, no overlap, robust routing with fallback, loop protection
- 7-8: Mostly clear, minor overlap or routing gaps
- 5-6: Some confusion in boundaries or routing
- 3-4: Significant overlap/confusion, no loop protection
- 1-2: No real agent design — everything handled ad-hoc

**Prompt Design (1-10)**
- 9-10: Consistent, specific, no contradictions, clear hierarchy
- 7-8: Mostly consistent, minor redundancy
- 5-6: Some contradictions or weak instructions
- 3-4: Multiple contradictions, vague instructions throughout
- 1-2: Prompts actively work against each other

**Character Consistency (1-10)** (N/A if no character system)
- 9-10: Personality persists long-term, behaviorally consistent everywhere including errors
- 7-8: Mostly consistent, minor drift risk
- 5-6: Personality defined but not protected from truncation/drift
- 3-4: Frequent inconsistency, broken immersion in error paths
- 1-2: Personality exists only nominally, no real consistency

**Memory System (1-10)**
- 9-10: Efficient retrieval, deduplication, aging, high relevance
- 7-8: Generally good, minor pollution or aging gaps
- 5-6: Works but has pollution/duplication/relevance issues
- 3-4: Significant retrieval quality issues
- 1-2: Memory system unreliable or effectively non-functional

**Database Design (1-10)**
- 9-10: Proper schema, indexes, constraints, migrations
- 7-8: Mostly solid, minor gaps
- 5-6: Functional but missing indexes/constraints
- 3-4: Significant schema issues, N+1 patterns
- 1-2: No real schema design

**RAG Quality (1-10)** (N/A if no RAG)
- 9-10: Precise retrieval, good chunking, hallucination guards, efficient pipeline
- 7-8: Generally good, minor precision issues
- 5-6: Works but noisy retrieval or missing fallback
- 3-4: Poor chunking/retrieval, no hallucination guard
- 1-2: RAG pipeline effectively non-functional

**Security (1-10)**
- 9-10: No exposed secrets, injection-resistant, proper scoping
- 7-8: Mostly secure, minor gaps
- 5-6: Some exposure or missing validation
- 3-4: Significant vulnerabilities
- 1-2: Critical security failures

**Performance (1-10)**
- 9-10: Efficient token usage, appropriate model selection, no waste
- 7-8: Generally efficient, minor waste
- 5-6: Noticeable inefficiencies
- 3-4: Significant token/compute waste
- 1-2: Severely inefficient, costly or unusably slow

**Reliability (1-10)**
- 9-10: Fallbacks everywhere, graceful degradation, no silent failures
- 7-8: Most paths handled, minor gaps
- 5-6: Some unhandled failure modes
- 3-4: Frequent crashes on component failure
- 1-2: Fragile — any component hiccup breaks the assistant

**Scalability (1-10)**
- 9-10: Designed for growth at every layer (memory, DB, compute)
- 7-8: Can grow with moderate changes
- 5-6: Will hit bottlenecks at moderate growth
- 3-4: Architectural blockers to growth
- 1-2: Will not survive realistic growth

**Maintainability (1-10)**
- 9-10: Clear structure, documented, consistent patterns, easy to extend
- 7-8: Mostly maintainable
- 5-6: Some areas hard to change safely
- 3-4: Brittle, inconsistent patterns
- 1-2: Very difficult to maintain or extend

**Production Readiness (1-10)**
- 9-10: Monitoring, logging, testing, docs, recovery all present
- 7-8: Most present, minor gaps
- 5-6: Some present, significant gaps
- 3-4: Minimal production infrastructure
- 1-2: Not production-ready in any sense

---

## Reporting Rules

- Every finding (FINDING-NNN format across all auditors) must include a confidence rating
- Every section must distinguish HIGH/MEDIUM/LOW confidence and ⚪ UNKNOWN findings
- When context is incomplete, issue a ⚠️ PARTIAL ANALYSIS NOTICE (same format as
  python-codebase-architect) listing what's missing and how it limits confidence
- For targeted audits (single subsystem), produce only that auditor's report plus a brief note
  on how it connects to the rest of the system — don't force the full 24-section format
- Always end with actionable next steps, even for targeted audits