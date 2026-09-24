# Repository Discovery Protocol — Phases 1–5

Run ALL phases before making any recommendations. Never skip.

---

## PHASE 1 — Repository Discovery {#phase1}

**Goal**: Understand what the system IS and WHY it exists before reading any code.

### 1.1 Project Purpose Discovery

Answer these before analyzing code:
- What problem does this system solve?
- Who are the users (internal devs, end-users, API consumers, other systems)?
- What are the main business objectives?
- Is this a product, a platform, a tool, or infrastructure?

### 1.2 Technology Stack Fingerprint

From imports and config files, identify:

```
Web Framework:    FastAPI / Flask / Django / Starlette
ORM/DB:          SQLAlchemy / Django ORM / Tortoise + Postgres/MySQL/SQLite
Cache:            Redis / Memcached / in-process
Queue:            Celery / arq / RQ / asyncio.Queue / Kafka
Auth:             JWT / OAuth2 / sessions / API keys
AI/ML Stack:      OpenAI / Anthropic / Ollama / LangChain / LangGraph / CrewAI
Vector DB:        ChromaDB / Pinecone / Weaviate / Qdrant / Faiss
Async Model:      asyncio / aiohttp / trio / sync only
Observability:    logging / structlog / Sentry / Prometheus
Deployment:       Docker / systemd / gunicorn / uvicorn / k8s
Testing:          pytest / unittest / hypothesis
```

### 1.3 Entry Point Identification

Locate and document all entry points:
- `main.py`, `run.py`, `app.py`, `__main__.py`
- CLI entrypoints (argparse, click, typer commands)
- WSGI/ASGI app instances (`app = FastAPI()`, `application = Django()`)
- Worker/daemon processes
- Scheduled jobs (APScheduler, Celery beat, cron)
- Event listeners / message consumers

### 1.4 Project Discovery Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PROJECT DISCOVERY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Purpose:           [What the system does]
Users:             [Who uses it]
Tech Stack:        [Full stack summary]
Entry Points:      [All entry points found]
Major Components:  [High-level component list]
Confidence:        🟢/🟡/🔴 [overall discovery confidence]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PHASE 2 — Architecture Mapping {#phase2}

**Goal**: Build a complete layered architecture map.

### 2.1 Layer Identification

Identify which layers exist and which files/modules belong to each:

```
PRESENTATION LAYER  → UI, templates, CLI output, WebSocket handlers
API LAYER           → HTTP routes, request/response schemas, middleware
SERVICE LAYER       → Business logic orchestration, use cases
BUSINESS/DOMAIN     → Core domain models, business rules, domain events
DATA LAYER          → Repositories, ORM models, query builders
INFRASTRUCTURE      → DB connections, external API clients, file system, queues
CROSS-CUTTING       → Config, logging, auth, error handling, monitoring
```

### 2.2 Architecture Style Detection

Identify the dominant architectural style:

| Style | Signals |
|-------|---------|
| Layered/N-Tier | Clear folder separation by layer (api/, services/, models/) |
| Clean/Onion | `core/` with zero external deps, `adapters/` implementing interfaces |
| MVC | models.py, views.py, controllers.py pattern |
| Event-Driven | EventBus, pub/sub, message brokers central to flow |
| Microservices | Multiple independent deployable units with their own DBs |
| Monolith | Single deployable, shared DB, everything in one process |
| CQRS | Separate read/write models, explicit command/query separation |
| Agent/LLM-Centric | LLM calls as primary orchestration, tools, memory systems |

### 2.3 Architecture Map Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SYSTEM ARCHITECTURE MAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Style: [Detected architectural style]

System Overview:
├── Presentation / API Layer
│   └── [modules/files]
├── Service / Business Logic Layer
│   └── [modules/files]
├── Domain / Core Layer
│   └── [modules/files]
├── Data Layer
│   └── [modules/files]
├── Infrastructure Layer
│   └── [modules/files]
└── Cross-Cutting Concerns
    └── [config, logging, auth, error handling]

Component Map:
[ASCII diagram of major component relationships]

Architecture Violations Found:
- [Any layer boundary violations]
- [Mixed concerns]

Confidence: 🟢/🟡/🔴
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PHASE 3 — Dependency Mapping {#phase3}

**Goal**: Build a complete dependency graph. Find coupling, circular deps, hidden dependencies.

### 3.1 Internal Dependency Scan

For each module, map:
- What it imports from other internal modules
- What imports IT (reverse dependency)
- Fan-out: number of internal modules it depends on
- Fan-in: number of modules that depend on it

**Risk flags**:
- Fan-out > 8 → complex module, likely needs splitting
- Fan-in > 10 → high-risk module (changes cascade everywhere)
- Fan-in AND Fan-out both high → god module

### 3.2 Circular Dependency Detection

Trace import chains to find cycles:
```
A → B → C → A  ← circular
A → B → A       ← circular (simpler)
```

Circular deps cause:
- `ImportError` at runtime under certain load orders
- Unpredictable initialization behavior
- Impossible to test modules in isolation

### 3.3 Hidden Dependency Detection

Look for dependencies not visible in import statements:
- Global mutable state accessed by multiple modules (`global` keyword, module-level dicts/lists)
- Singletons accessed directly (not injected)
- `os.environ` read deep inside business logic
- Database connections passed between layers as implicit shared state
- Monkey-patching in `__init__.py`

### 3.4 External Dependency Audit

From `requirements.txt`, `pyproject.toml`, `setup.py`:
- Total number of external dependencies
- Pinned vs unpinned versions (unpinned = risk)
- Known vulnerable packages (flag for security review)
- Unused dependencies (dead weight, security surface)
- Transitive dependency conflicts

### 3.5 Dependency Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DEPENDENCY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Internal Dependencies:
  High Fan-In Modules:  [list — most fragile to change]
  High Fan-Out Modules: [list — most complex]
  God Modules:          [both high fan-in AND fan-out]

Circular Dependencies:
  [chain → chain → chain]
  Risk: [Critical/High/Medium]

Hidden Dependencies:
  [list with location and type]

External Dependencies:
  Total:       [N]
  Unpinned:    [N] — [names]
  Potentially Unused: [list]
  Security Flags: [any known vulnerable packages]

Coupling Risk:
  Tight Coupling: [module pairs with excessive direct coupling]
  Loose Coupling: [well-isolated modules]

Confidence: 🟢/🟡/🔴
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PHASE 4 — Data Flow Analysis {#phase4}

**Goal**: Trace how data enters, transforms, and exits the system.

### 4.1 Data Source Identification

Where does data originate?
- HTTP request body / query params / headers
- CLI arguments / stdin
- Database reads
- File system reads
- External API responses
- Message queue messages
- User input (voice, text, file upload)
- Environment variables / config files

### 4.2 Transformation Tracing

Follow data through the system:
```
Raw Input → Validation → Parsing → Normalization → Business Processing
→ Persistence → Retrieval → Formatting → Output
```

Flag:
- Points where data is mutated without validation
- Points where external/untrusted data enters without sanitization
- Where data schema changes across layers (ORM model → domain object → API response)
- Where data is silently dropped or defaulted

### 4.3 Data Storage Mapping

Document all data stores and what goes in them:
- Database tables/collections and their roles
- Cache keys and TTLs
- Vector store collections (for AI systems)
- File system paths used for storage
- In-memory state (who owns it, what's in it, lifetime)

### 4.4 Data Flow Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DATA FLOW REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Data Sources:     [list all inputs]
Transformation Pipeline:
  [Input] → [step] → [step] → [Output]
Data Stores:
  Primary DB:     [tables/purpose]
  Cache:          [keys/TTL/purpose]
  Vector Store:   [collections/purpose] (if present)
  In-Memory:      [what's kept, who owns it, lifetime]
Data Risks:
  Unvalidated Entry Points: [locations]
  Schema Mismatches:        [locations]
  Sensitive Data Exposure:  [PII/secrets in wrong places]
Confidence: 🟢/🟡/🔴
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PHASE 5 — Control Flow Analysis {#phase5}

**Goal**: Map how execution flows through the system. Find critical paths and failure paths.

### 5.1 Critical Path Identification

For each major user workflow, trace the complete execution chain:
```
[Trigger] → [Handler] → [Service] → [Domain Logic] → [Storage] → [Response]
```

Annotate each step with:
- Synchronous or asynchronous
- Can it fail? What happens when it does?
- Is there a timeout?
- Is there a retry?

### 5.2 Business Workflow Mapping

Identify the 3–5 most business-critical workflows and trace them completely:
- Happy path
- Error path
- Timeout/partial failure path
- Concurrent access path (if relevant)

### 5.3 Failure Path Analysis

For each critical path, trace what happens on failure:
- Exception raised → caught where? → handled how?
- Timeout → fallback? → user error? → silent failure?
- External dependency down → circuit breaker? → retry? → crash?
- Queue message fails → dead-letter queue? → lost?

### 5.4 Control Flow Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CONTROL FLOW REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Critical Paths:
  [Workflow 1]:
    Happy Path:    [step → step → step]
    Failure Path:  [what breaks, what recovers]
    Timeout Risk:  [yes/no, where]

  [Workflow 2]: ...

Execution Model:
  Synchronous:  [% / areas]
  Asynchronous: [% / areas]
  Mixed:        [problem areas]

Failure Handling:
  Well-handled:  [critical paths with proper error handling]
  At Risk:       [critical paths with bare except / no fallback]
  Silent Failures: [locations where errors disappear]

Single Points of Failure:
  [list with severity]

Confidence: 🟢/🟡/🔴
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```