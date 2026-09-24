# Code Review Format — V2

Focused on coding excellence. Architecture-level scoring belongs to python-codebase-architect.

---

## Review Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PYTHON MASTER ENGINEER — CODE REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📋 SUMMARY
[2–3 sentences: what this code does, general quality, most important thing to know]

---

## ✅ STRENGTHS
[Genuine positives — specific, not generic. Reference actual functions/patterns.]

---

## ❌ WEAKNESSES
[Specific problems found. Always reference where: function name, class, line if possible.]

---

## 🚨 RISKS

### 🔴 Critical — breaks production or creates security vulnerability
[Crashes, data loss, injection risk, hardcoded secrets, silent corruption]

### 🟠 High — creates instability or significant bugs
[Unhandled edge cases, race conditions, wrong algorithm, broken async]

### 🟡 Medium — hurts maintainability or correctness
[Tight coupling, missing validation, duplicate logic, magic numbers]

### 🔵 Low — improvements worth making
[Style, naming, missing docstrings, minor inefficiencies]

---

## 💡 RECOMMENDATIONS
[Prioritized, specific improvements — each with WHAT, WHY, HOW]

1. [Most critical]
2. [Second priority]
3. [Third priority]
...

---

## 📊 CODE QUALITY SCORE

| Category        | Score  | Note |
|-----------------|--------|------|
| Readability     | X / 10 | [one line] |
| Maintainability | X / 10 | [one line] |
| Performance     | X / 10 | [one line] |
| Security        | X / 10 | [one line] |
| Scalability     | X / 10 | [one line] |

**Overall: X / 10**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Scoring Guide

### Readability (1–10)
- 9–10: Intent obvious from names alone, zero unnecessary comments
- 7–8: Mostly clear, minor naming gaps
- 5–6: Readable with effort, some confusing parts
- 3–4: Hard to follow, poor naming, missing context
- 1–2: Unreadable

### Maintainability (1–10)
- 9–10: Single responsibility, low coupling, easy to change
- 7–8: Mostly maintainable, minor coupling issues
- 5–6: Some tight coupling or god functions
- 3–4: Changes are risky, high blast radius
- 1–2: Untouchable without breaking something

### Performance (1–10)
- 9–10: Efficient algorithms, appropriate data structures, no blocking in async
- 7–8: Generally good, 1–2 minor inefficiencies
- 5–6: Noticeable bottlenecks
- 3–4: Multiple serious issues (N+1, O(n²), sync in async)
- 1–2: Will not handle real load

### Security (1–10)
- 9–10: Input validated, parameterized queries, no secrets in code, safe execution
- 7–8: Mostly secure, minor gaps
- 5–6: Some exposure
- 3–4: Significant vulnerabilities (injection risk, hardcoded creds)
- 1–2: Critical failures — not production-safe

### Scalability (1–10)
- 9–10: Stateless where possible, async throughout, no in-process-only state
- 7–8: Can scale with minor changes
- 5–6: Will hit limits at moderate load
- 3–4: Architectural blockers to scaling
- 1–2: Cannot scale at all

---

## Code Review Checklist (run mentally every time)

### Pythonic Style
- [ ] Comprehensions used where appropriate (not overused)
- [ ] `with` (context managers) for files and resources
- [ ] f-strings, not `%` or `.format()`
- [ ] `enumerate()` / `zip()` instead of manual index
- [ ] Type hints on function signatures
- [ ] Dataclasses / NamedTuples for structured data

### Error Handling
- [ ] No bare `except:` (catches KeyboardInterrupt, SystemExit)
- [ ] Exceptions are specific to the expected error type
- [ ] Errors logged or re-raised, never silently swallowed
- [ ] Resources cleaned up in `finally` or context manager

### Code Structure
- [ ] Functions do ONE thing
- [ ] No function longer than ~50 lines
- [ ] No class longer than ~200 lines
- [ ] Constants at top level, not buried as magic numbers
- [ ] No circular imports
- [ ] Config/settings separate from business logic

### Production Readiness
- [ ] No `print()` used for logging (use `logging` module)
- [ ] No hardcoded secrets or environment values
- [ ] No `TODO` / `FIXME` in code meant for production
- [ ] Input validated before use
- [ ] Edge cases handled (empty list, None, zero, negative, very large values)