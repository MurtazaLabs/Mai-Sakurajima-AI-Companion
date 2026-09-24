# Output Format & Scoring

---

## Full Analysis Report — 11 Sections

Use this format when asked to assess a project's documentation state (not when simply asked
to write one document — that just produces the document via `create_file`).

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 KNOWLEDGE BASE ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 1. EXECUTIVE SUMMARY
[3-5 sentences: overall documentation state, single most important gap,
 single most valuable next document to create]

## 2. KNOWLEDGE DISCOVERY REPORT
[Purpose / Users / Core Systems / Dependencies / Major Workflows]

## 3. DOCUMENTATION COVERAGE REPORT
[What exists today, mapped against what should exist]
| Document | Status | Quality |
|----------|--------|---------|
| ARCHITECTURE.md | Exists/Missing/Partial | 🟢/🟡/🟠/🔴 |
| ... | | |

## 4. MISSING DOCUMENTATION
[Specific docs that don't exist but should, ranked by value]
1. [Doc] → [why this matters most]

## 5. OUTDATED DOCUMENTATION
[Specific docs that exist but no longer match reality]
[DOC-NNN format — see ai-assistant-docs-and-quality.md#quality-audit]

## 6. RECOMMENDED DOCUMENTS
[The specific set of documents recommended for this project, with reasoning —
 not just the full standard wiki list applied blindly]

## 7. DOCUMENT STRUCTURE
[Proposed folder/file structure for the recommended documentation]

## 8. KNOWLEDGE RISKS
[From Knowledge Preservation Mode — what's at risk of being lost]

## 9. KNOWLEDGE PRESERVATION PLAN
[Prioritized plan for capturing at-risk knowledge]

## 10. DOCUMENTATION ROADMAP
[Phased plan: what to document first, second, third — proportional to project size]

## 11. FINAL RECOMMENDATIONS
[Direct, prioritized next steps + scorecard]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 8-Category Scoring System

### Score Output Format

```
┌──────────────────────────────────────────────────┐
│         KNOWLEDGE BASE SCORECARD                  │
├────────────────────────┬────────┬──────────────────┤
│ Category                │ Score  │ Note             │
├────────────────────────┼────────┼──────────────────┤
│ Documentation Coverage  │  X/10  │ [one line]       │
│ Documentation Quality   │  X/10  │ [one line]       │
│ Architecture Docs       │  X/10  │ [one line]       │
│ Developer Onboarding    │  X/10  │ [one line]       │
│ Knowledge Preservation  │  X/10  │ [one line]       │
│ Maintainability         │  X/10  │ [one line]       │
│ Searchability           │  X/10  │ [one line]       │
│ Knowledge Accessibility │  X/10  │ [one line]       │
├────────────────────────┼────────┼──────────────────┤
│ OVERALL                 │  X/10  │ [grade]          │
└────────────────────────┴────────┴──────────────────┘

Status:  🟢 Excellent (9-10)  🟡 Good (7-8)
         🟠 Needs Work (5-6)  🔴 Critical Gap (1-4)
Grade:   A (9-10) | B (7-8) | C (5-6) | D (3-4) | F (<3)
```

### Scoring Rubrics

**Documentation Coverage (1-10)**
- 9-10: Every major system has corresponding documentation
- 7-8: Most systems documented, minor gaps
- 5-6: Core systems documented, several gaps in secondary systems
- 3-4: Sparse — only the most obvious things documented
- 1-2: Little to no documentation exists

**Documentation Quality (1-10)**
- 9-10: Accurate, clear, well-structured, genuinely useful to a new reader
- 7-8: Good quality, minor clarity or accuracy issues
- 5-6: Usable but rough — some confusion likely for a new reader
- 3-4: Significant quality issues — hard to trust or use as-is
- 1-2: Misleading or unusable

**Architecture Documentation (1-10)**
- 9-10: Clear system overview, diagrams, layer explanations, data/control flow documented
- 7-8: Good architecture doc, minor gaps
- 5-6: Basic overview exists, lacks depth on flow/relationships
- 3-4: Minimal or significantly outdated
- 1-2: No architecture documentation exists

**Developer Onboarding (1-10)**
- 9-10: A new developer could be productive within hours using only the docs
- 7-8: Good onboarding path, some gaps requiring code archaeology
- 5-6: Basic setup documented, workflow/pitfalls missing
- 3-4: Minimal onboarding support
- 1-2: No onboarding documentation — new developer is on their own

**Knowledge Preservation (1-10)**
- 9-10: Decisions, tradeoffs, and tribal knowledge are actively captured
- 7-8: Most significant decisions documented
- 5-6: Some decisions captured, inconsistently
- 3-4: Rarely captured — mostly lives in memory/chat history
- 1-2: No mechanism for preserving decisions or rationale at all

**Maintainability (1-10)**
- 9-10: Well-structured, easy to update, clear ownership of what goes where
- 7-8: Reasonably maintainable
- 5-6: Functional but some duplication/inconsistency makes updates error-prone
- 3-4: Significant duplication or structural issues
- 1-2: Documentation structure actively discourages keeping it updated

**Searchability (1-10)**
- 9-10: Clear naming, good cross-linking, easy to find the answer to a specific question
- 7-8: Mostly easy to navigate
- 5-6: Findable with some effort
- 3-4: Hard to locate specific information
- 1-2: No real organization — would require reading everything to find anything

**Knowledge Accessibility (1-10)**
- 9-10: Written for the actual intended audience, jargon explained, approachable
- 7-8: Generally accessible, occasional unexplained jargon
- 5-6: Assumes significant prior context
- 3-4: Written in a way that mostly only the original author could follow
- 1-2: Inaccessible to anyone but the person who wrote it, right after writing it

---

## Reporting Rules

- When generating documents (not assessing), skip the 11-section report — just build the
  files and present them with a brief conversational summary of what was created
- When assessing existing documentation, always end with a clear, prioritized "build this
  next" recommendation — assessment without action items isn't useful
- Cross-reference findings from other skills when available rather than re-deriving them —
  attribute the source (e.g., "per the mai-ai-systems-auditor review on [topic]...")
- Keep the doc set proportional to project size — a small personal project doesn't need
  all 13 wiki documents; recommend only what adds real value