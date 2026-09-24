# Special Modes Reference

---

## NEW DEVELOPER ONBOARDING MODE {#onboarding}

Generate a complete guide for a developer joining the project for the first time.

### Guide Structure

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 NEW DEVELOPER GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 1. Project Purpose
[What this system does and why it exists, in plain English]

## 2. Project Structure
[Annotated folder tree — what each directory contains]
project/
├── core/        ← [what lives here and why]
├── api/         ← [what lives here and why]
├── services/    ← [what lives here and why]
└── ...

## 3. Important Files (read these first)
Priority order for reading:
1. [file] — [why this is the most important first read]
2. [file] — [what this teaches about the system]
3. ...

## 4. Core Components
[For each major component: what it does, how it connects to others]

Component: [Name]
  Purpose:    [one sentence]
  Location:   [path]
  Depends on: [list]
  Used by:    [list]
  Key classes/functions: [list]

## 5. Critical Workflows
[Step-by-step trace of the 2–3 most important user workflows]

Workflow: [Name]
  Entry:  [where it starts]
  Steps:  [step → step → step]
  Output: [what it produces]
  Code:   [which files to read to follow this]

## 6. Architecture Overview
[Short narrative of the architectural style and why it was chosen]
[ASCII diagram of major component relationships]

## 7. Common Pitfalls
[Things that will confuse a new developer]
- [Pitfall 1]: [what it looks like, why it's confusing, how to handle it]
- [Pitfall 2]: ...

## 8. Local Setup Checklist
□ [step 1]
□ [step 2]
...

## 9. Recommended Learning Order
Week 1: [what to read/understand first]
Week 2: [what to tackle next]
Week 3: [when to start making changes]

## 10. Who to Ask / Where to Look
[Key files, comments, or documentation sources]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## REFACTOR PLANNING MODE {#refactor}

Produce a structured refactor roadmap. Never recommend large rewrites without evidence.

### Refactor Plan Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 REFACTOR ROADMAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[REFACTOR-001]
Goal:               [What this refactor achieves]
Trigger:            [Why it's needed — evidence from debt/smell analysis]
Affected Components:[List of modules/classes involved]
Expected Benefits:
  - [Benefit 1: measurable where possible]
  - [Benefit 2]
Potential Risks:
  - [Risk 1: what could break]
  - [Risk 2]
Effort Estimate:    [Low / Medium / High / Very High]
Priority:           [Critical / High / Medium / Low]

Migration Strategy:
  Phase 1: [Safest first step — usually "add the new thing alongside the old"]
  Phase 2: [Migrate callers one by one]
  Phase 3: [Remove the old thing]
  Validation: [How to confirm the migration worked]

Rollback Strategy:
  [How to revert if something goes wrong at each phase]
  [Feature flag approach if applicable]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### When to Recommend Full Rewrite vs Incremental Refactor

**Incremental Refactor** (preferred in almost all cases):
- System is in production and must stay running
- Team understands the existing code well enough to refactor safely
- Individual modules can be improved without touching everything
- Use: Strangler Fig pattern — new code grows alongside old, old gets replaced gradually

**Full Rewrite** (only when all of these are true):
- Evidence that the architecture is fundamentally broken (not just messy)
- Cost of maintaining old code exceeds cost of rewrite (quantify this)
- Existing tests can validate the rewrite's correctness
- Team has clear requirements and timeline
- Stakeholders understand the risk and timeline

If recommending a rewrite, always include:
- Cost estimate (lines of code, team-weeks)
- Risk assessment (what happens if it takes 2x as long)
- Alternative (what would incremental refactoring cost instead)

### Common Refactor Patterns

**Strangler Fig** (replace legacy system incrementally)
```
1. Identify the seam between old and new
2. Build new implementation alongside old
3. Route new traffic to new implementation
4. Verify behavior matches
5. Remove old implementation
6. Repeat for next piece
```

**Extract Service** (split god module)
```
1. Identify the responsibility to extract
2. Create new module/class with clean interface
3. Copy (don't cut) logic to new location
4. Update callers one by one to use new location
5. Add tests to new location
6. Remove old code
```

**Introduce Repository** (add data layer abstraction)
```
1. Create abstract Repository interface
2. Create concrete implementation wrapping existing DB code
3. Update service layer to use interface, not DB directly
4. Now DB is swappable, service is testable with mock repo
```

---

## KNOWLEDGE GRAPH MODE {#knowledge-graph}

Build a relationship map of the entire system for navigating large codebases.

### Knowledge Graph Structure

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SYSTEM KNOWLEDGE GRAPH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Node Types:
  📦 Package   → top-level Python packages
  📄 Module    → individual .py files
  🏛️ Class     → class definitions
  ⚙️ Function  → key functions
  💾 Store     → databases, caches, vector stores
  🌐 External  → external APIs, services

Edge Types:
  imports     → A imports B
  inherits    → A extends B
  calls       → A calls B's methods
  reads       → A reads from store B
  writes      → A writes to store B
  triggers    → A emits event consumed by B

Graph:
[Module A] --imports--> [Module B]
[Class X]  --inherits-> [Class Y]
[Service]  --calls----> [Repository]
[Handler]  --writes---> [Database]
[Agent]    --calls----> [LLM API]

Central Nodes (highest connectivity):
  [List modules/classes with most connections]
  → These are the most risky to change

Isolated Nodes (lowest connectivity):
  [List modules/classes with few connections]
  → These are the safest to change or extract

Clusters:
  [Cluster 1 name]: [modules that belong together]
  [Cluster 2 name]: [modules that belong together]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## TECHNICAL DUE DILIGENCE MODE {#due-diligence}

Act as an engineer evaluating software for acquisition or major investment. Give an honest,
evidence-backed verdict. Do not soften bad findings.

### Due Diligence Questions

Answer all of these, backed by evidence from the code:

1. **Would you acquire this project?** (Yes / With conditions / No)
2. **Would you deploy this to production today?** (Yes / With changes / No — list blocking issues)
3. **Would you trust this with customer data?** (Yes / With fixes / No — list security concerns)
4. **What are the 3 biggest strengths?**
5. **What are the 3 biggest weaknesses?**
6. **Estimated maintenance burden** (hours/week for a team of N)
7. **Estimated cost to reach production-grade** (if not there yet)
8. **Estimated rewrite cost** (team-weeks, and whether it's justified)
9. **What would you do in the first 30 days as the new owner?**

### Due Diligence Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 TECHNICAL DUE DILIGENCE REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERDICT:
  Acquire:          [Yes / With Conditions / No]
  Production Ready: [Yes / With Changes / No]
  Customer Trust:   [Yes / With Fixes / No]

STRENGTHS:
  1. [Specific strength with evidence]
  2. [Specific strength with evidence]
  3. [Specific strength with evidence]

WEAKNESSES:
  1. [Specific weakness with evidence and impact]
  2. [Specific weakness with evidence and impact]
  3. [Specific weakness with evidence and impact]

BLOCKERS (must fix before production):
  [List with specific locations and fixes]

MAINTENANCE BURDEN:
  Estimated: ~[N] hours/week for a [X]-person team
  Reason:    [Why it's high/low — specific debt items]

COST TO PRODUCTION GRADE:
  Estimated: [N] team-weeks
  Breakdown: [by area]

REWRITE COST:
  Estimated: [N] team-months
  Justified: [Yes/No — reason]

FIRST 30 DAYS AS NEW OWNER:
  Week 1: [immediate priorities]
  Week 2: [stabilization work]
  Week 3: [quick wins]
  Week 4: [strategic planning]

OVERALL ASSESSMENT:
  [2–3 sentence honest summary]

Confidence: 🟢/🟡/🔴
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```