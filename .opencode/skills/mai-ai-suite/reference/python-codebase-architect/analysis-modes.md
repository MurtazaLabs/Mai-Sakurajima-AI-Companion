# Analysis Modes Reference

---

## ARCHITECTURE REVIEW MODE {#architecture}

Evaluate after Phase 1–2 are complete.

### Evaluation Dimensions

**Separation of Concerns**
- Are HTTP, business logic, and data access cleanly separated?
- Do route handlers contain SQL or business rules?
- Do models know about HTTP concepts?
- Is config accessed at the boundary (entry point) or deep in business logic?

**Layer Isolation**
- Can the service layer be tested without starting an HTTP server?
- Can the data layer be swapped (e.g., SQLite → PostgreSQL) without touching business logic?
- Do domain objects have zero framework imports?

**Modularity**
- Can individual modules be understood and tested independently?
- Are there clear, minimal interfaces between modules?
- Could a module be extracted to a separate package with minimal changes?

**Reusability**
- Are common operations (pagination, error formatting, auth checks) centralized?
- Is there duplication of business rules across multiple places?

**Extensibility**
- How hard is it to add a new LLM provider? A new storage backend? A new API endpoint?
- Are there extension points, or does everything require modifying existing code?

**Architectural Anti-Patterns to Flag**

| Anti-Pattern | Signal | Risk |
|-------------|--------|------|
| Transaction Script | All logic in route handlers | High — untestable, bloated |
| Anemic Domain | Models are just data bags, logic scattered | Medium — maintainability |
| Distributed Monolith | Microservice shape, monolith coupling | Critical — worst of both |
| Big Ball of Mud | No discernible structure | High — unmaintainable |
| Leaky Abstraction | ORM types leaking into API layer | Medium — coupling |
| Service Locator | Global registry for dependencies | Medium — testability |

---

## TECHNICAL DEBT SCANNER {#debt}

Categorize all debt found by severity. Every item must include evidence.

### Debt Categories and Detection

**Critical Debt** (Severity 9–10) — Fix immediately
- Production-threatening issues
- Security vulnerabilities in active code paths
- Data corruption risks
- Crashes waiting to happen
- Hardcoded credentials in committed code

**High Debt** (Severity 7–8) — Fix this sprint
- Likely future failures under realistic load
- Missing retry/timeout on all external calls
- Race conditions in concurrent code
- Silent exception swallowing on critical paths
- No health checks or startup validation

**Medium Debt** (Severity 4–6) — Fix this quarter
- Maintainability drags that slow development
- God classes/functions
- Duplicate business logic
- Missing input validation on secondary paths
- Magic numbers throughout codebase
- Inconsistent error handling patterns

**Low Debt** (Severity 1–3) — Backlog
- Code quality improvements
- Missing docstrings on public APIs
- Style inconsistencies
- Minor naming improvements
- Unused imports

### Debt Item Format
```
[DEBT-NNN]
Category:    [Architecture / Performance / Security / Reliability / Maintainability]
Severity:    X/10
Confidence:  🟢/🟡/🔴
Location:    module.py → ClassName.method_name
Description: [What is wrong]
Evidence:    [The specific code pattern that proves it]
Impact:      [What breaks/degrades/becomes unmaintainable]
Effort:      [Low / Medium / High / Very High]
Fix:         [Specific recommended approach]
```

---

## CODE SMELL DETECTION {#smells}

### Smell Catalog

**God Object**
- Class with 20+ methods and unrelated responsibilities
- Class > 500 lines with mixed concerns
- Detection: `class X` with methods spanning HTTP, DB, email, auth, business logic
- Risk: any change is high-risk, testing near-impossible

**Spaghetti Code**
- No clear flow from function to function
- Long functions (>100 lines) with complex branching
- Detection: cyclomatic complexity > 10, deep nesting (>4 levels)
- Risk: debugging and modification are equally painful

**Feature Envy**
- Method that uses more data/methods from another class than its own
- Detection: method calls `other.x`, `other.y`, `other.z()` repeatedly
- Fix: move the method to the class it's "envious" of

**Shotgun Surgery**
- One change requires modifying many unrelated files
- Detection: changing a business rule requires edits in 5+ files
- Risk: change velocity drops to near zero, regression risk is high

**Primitive Obsession**
- Using raw strings/ints for domain concepts instead of types
- Examples: `user_id: int`, `email: str`, `status: str = "active"`
- Fix: `UserId`, `Email`, `UserStatus(Enum)` as proper types

**Long Parameter Lists**
- Functions with > 4 parameters
- Detection: `def process(a, b, c, d, e, f)`
- Fix: dataclass or TypedDict to group related params

**Deep Nesting**
- > 3–4 levels of indent in a single function
- Detection: pyramid-of-doom if/for/try stacks
- Fix: guard clauses, extract methods

**Circular Imports**
- Module A imports B, B imports A (or longer chains)
- Risk: import errors, unpredictable initialization, impossible to test in isolation

**Over-Engineering**
- Abstractions with only one implementation, ever
- Factory that creates one type of object
- Strategy pattern with one strategy
- Risk: complexity with no benefit, new devs get lost

**Under-Engineering**
- Copy-paste code instead of extraction
- Business logic directly in route handlers
- No error handling on external calls
- Risk: inconsistency, fragility, maintenance burden

### Code Smell Report Template
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CODE SMELL REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SMELL-001]
Type:        God Object
Location:    module.py → ClassName
Evidence:    [N] methods, spans [X] unrelated responsibilities
Impact:      [specific risk]
Fix:         [specific split approach]
Confidence:  🟢

[SMELL-002]
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## SCALABILITY ANALYSIS {#scalability}

**Goal**: Predict where the system fails as load grows. Give concrete projections.

### Scalability Evaluation Dimensions

**Concurrency Model**
- Is the system async throughout, or sync with async mixed in?
- Are there blocking calls (requests, time.sleep, open()) inside async functions?
- Are there locks or semaphores that could become bottlenecks?

**State Management**
- Is session/conversation state stored in-process? → blocks horizontal scaling
- Is file storage local? → blocks horizontal scaling
- Are background tasks coupled to the web process? → blocks horizontal scaling

**Database Layer**
- Is connection pooling configured?
- Are queries indexed appropriately?
- N+1 query patterns present?
- Are large datasets paginated?

**Caching**
- Are expensive, repeated computations cached?
- Is there a caching strategy, or is everything recalculated?

**External Dependencies**
- Is there retry + exponential backoff on all external calls?
- Is there circuit breaking for flaky services?
- Are external calls concurrent or sequential?

### User-Scale Prediction Table

Estimate system behavior at each scale level:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SCALABILITY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current State: [sync/async, single-process, stateful/stateless]

Predicted Behavior at Scale:
  100 users:     ✅/⚠️/❌ [what breaks or holds]
  1,000 users:   ✅/⚠️/❌ [bottleneck prediction]
  10,000 users:  ✅/⚠️/❌ [bottleneck prediction]
  100,000 users: ✅/⚠️/❌ [what definitely breaks]
  1,000,000 users: ❌ [what architectural changes are needed]

Identified Bottlenecks:
  [Bottleneck 1]: [location, type, severity, fix]
  [Bottleneck 2]: ...

Horizontal Scaling Blockers:
  [In-process state / local file storage / process-coupled tasks]

Infrastructure Recommendations:
  [specific: add Redis for session, move to async HTTP client, add DB read replica]

Confidence: 🟢/🟡/🔴
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## MAINTAINABILITY ANALYSIS {#maintainability}

### Evaluation Dimensions

**Documentation Quality**
- Docstrings on public functions and classes?
- README up to date and accurate?
- Architecture decision records (ADRs) present?
- Inline comments explain "why", not "what"?

**Naming Consistency**
- Consistent naming convention throughout (snake_case enforced)?
- Domain terms used consistently (not `user` in one place, `account` in another)?
- Module names reflect their contents?

**Complexity**
- Average function length (target: < 30 lines)
- Cyclomatic complexity hotspots
- Nesting depth hotspots

**Developer Onboarding Difficulty**
- How long to understand the system from scratch?
- Is the entry point obvious?
- Are there hidden setup requirements?

**Refactor Difficulty**
- High fan-in modules that are hard to change
- Highly coupled components with no seams for testing
- Business logic embedded in framework code

### Maintainability Report Template
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 MAINTAINABILITY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Documentation:     [score and findings]
Naming:            [consistency assessment]
Complexity:        [hotspot locations]
Onboarding:        [estimated hours for new dev to be productive]
Refactor Risk:     [highest-risk modules to change]
Test Coverage:     [estimated / actual if known]

Top Maintainability Drains:
  1. [Issue + location + impact]
  2. ...

Confidence: 🟢/🟡/🔴
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## RISK ASSESSMENT MODE {#risk}

### Risk Categories

**Critical Risk** — Could cause production outage
- Single points of failure with no fallback
- Security vulnerabilities on active code paths
- Data loss scenarios (no transactions, no backups, no rollback)
- Memory leaks in long-running processes

**High Risk** — Likely future incidents
- Missing retry/timeout on external calls
- No health checks (broken deploy not detected)
- Race conditions in concurrent code
- Unbounded growth of in-memory state

**Medium Risk** — Maintenance problems
- Highly coupled modules where a change ripples everywhere
- No test coverage on critical business logic
- Config changes require full deploy

**Low Risk** — Quality concerns
- Minor inconsistencies
- Suboptimal but not dangerous patterns

### Risk Report Template
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 RISK ASSESSMENT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[RISK-001]
Severity:    🔴 Critical
Confidence:  🟢 High
Location:    [module/function]
Description: [What the risk is]
Trigger:     [What causes it to materialize]
Impact:      [What happens when it does]
Likelihood:  [Certain / Likely / Possible / Unlikely]
Mitigation:  [Specific fix or workaround]

[RISK-002]
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```