# AI Ecosystem Discovery Protocol — Phases 1–3

Run before any subsystem auditor. Never audit a component without this context.

---

## PHASE 1 — System Discovery

### 1.1 System Purpose

Answer from evidence in the code/config/docs:
- What is this assistant for? (personal assistant, voice companion, customer support, coding
  agent, character/roleplay companion, etc.)
- Who are the intended users? (single user / multi-user / public-facing)
- What are the main use cases? (trace from entry points and tool definitions)

### 1.2 Core Component Inventory

Identify presence and location of each:

```
Agents:          [list — names, roles, what triggers each]
Memory:          [short-term context handling + long-term storage]
Database:        [relational/SQL store and what it persists]
Vector Database: [ChromaDB/Pinecone/etc — what's embedded and why]
Prompt System:   [where system/agent/skill prompts live]
Tools:           [what tools/functions are exposed to the LLM]
APIs:            [external services called — LLM providers, TTS/STT, etc]
Workflows:       [main pipelines — e.g., wake word → STT → LLM → TTS]
```

### 1.3 Architecture Type Detection

| Type | Signals |
|------|---------|
| Single-Agent Assistant | One LLM loop, no agent routing, direct tool calls |
| Multi-Agent System | Router/orchestrator delegates to specialized agents |
| RAG-Centric | Heavy reliance on vector retrieval before generation |
| Character/Companion | Personality system, emotion state, persona prompts |
| Hybrid | Combination — most real systems are hybrid |

### 1.4 Primary Workflow Tracing

For each major workflow, trace start to finish:
```
[Trigger] → [Processing Steps] → [Memory/Context Touches] → [Tool Calls] → [Output]
```

Example (voice assistant):
```
Wake Word Detected → Audio Capture → STT (Whisper) → Intent/Context Retrieval (Memory)
→ LLM Generation (with personality prompt + retrieved context) → Tool Calls (if any)
→ TTS (Kokoro) → Audio Output → Memory Write (conversation log)
```

### 1.5 System Discovery Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SYSTEM DISCOVERY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Purpose:            [what this system is for]
Users:              [who uses it, how many]
Architecture Type:  [from 1.3]

Core Components:
  Agents:           [list]
  Memory:           [short-term + long-term]
  Database:         [type + purpose]
  Vector Database:  [type + purpose, or "none"]
  Prompt System:    [structure]
  Tools:            [list]
  External APIs:    [list]

Primary Workflows:
  1. [Workflow name]: [trigger → ... → output]
  2. ...

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PHASE 2 — Architecture Mapping

### 2.1 Component Chain Mapping

Build the full chain showing how a request flows through the system:

```
User Input
   ↓
Main Assistant / Entry Point
   ↓
Agent Router (if multi-agent)
   ↓
Context Assembly (memory retrieval + prompt construction)
   ↓
LLM Call
   ↓
Tool Layer (if tools invoked)
   ↓
Response Processing
   ↓
Memory Layer (write-back)
   ↓
Database Layer (persistence)
   ↓
Output to User
```

Annotate each arrow with:
- What data/context moves across it
- Is it synchronous or async?
- What happens if this step fails?

### 2.2 Context Movement Mapping

Trace how "context" (conversation history, retrieved memories, personality state, emotion
state) flows:
- Where is context assembled before the LLM call?
- What's the maximum context size, and how is it bounded?
- Is context truncated, summarized, or dropped when it grows too large?
- Does context include stale or irrelevant information by default?

### 2.3 Agent Communication Mapping (if multi-agent)

For each agent-to-agent or agent-to-router interaction:
- What's passed between them? (full context, summary, structured data)
- Is communication synchronous (blocking) or async (queued)?
- Can agents call each other directly, or only through a router?
- Is there a shared state/blackboard, or is everything passed explicitly?

### 2.4 AI System Map Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 AI SYSTEM MAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User
 ↓
[Entry Point] — [sync/async]
 ↓
[Agent Router] — [present? routing logic?]
 ↓
[Context Assembly] — [what's gathered, from where]
 ↓
[LLM Call] — [provider, model, fallback?]
 ↓
[Tool Layer] — [tools available, how invoked]
 ↓
[Memory Write] — [what's persisted, where]
 ↓
[Database/Vector Store]
 ↓
Output

Component Relationships:
  [Component A] ←→ [Component B]: [what's exchanged]
  ...

Context Flow:
  Max context size:     [tokens/messages]
  Truncation strategy:  [none/sliding window/summarization]
  Memory retrieval:     [when, how much, ranked how]

Agent Communication: (if applicable)
  [describe pattern — router-only, peer-to-peer, shared state]

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PHASE 3 — Risk Surface Analysis

### 3.1 Critical Systems Identification

Which components, if they fail, take down the entire assistant?
- LLM provider (single provider with no fallback?)
- Database connection (in-memory fallback or hard crash?)
- Memory/vector store (does the assistant work without it, degraded?)
- Wake word / audio pipeline (for voice assistants)

### 3.2 Single Points of Failure (SPOFs)

For each critical system, ask:
- Is there a fallback if this is unavailable?
- What does the user experience when this fails?
- Is the failure logged/visible, or silent?

### 3.3 Fragile Component Identification

Components that are likely to break under normal evolution:
- Hardcoded prompts that reference specific tool names (breaks if tools renamed)
- Memory retrieval tightly coupled to a specific embedding model (breaks if model changes)
- Agent routing based on string matching (breaks with new phrasing)
- Settings/config referenced inconsistently across modules (the kind of bug that causes
  `AttributeError: 'Settings' object has no attribute 'X'`)

### 3.4 Bottleneck Identification

- Where does the system wait synchronously when it could be async? (LLM calls, TTS generation,
  vector search)
- Where is there no caching for repeated expensive operations?
- Where does memory grow unbounded? (conversation history, vector store with no pruning)

### 3.5 System Risk Map Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SYSTEM RISK MAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Critical Systems (assistant fails without these):
  [System]: [why critical] → Fallback: [yes/no, describe]

Single Points of Failure:
  [SPOF-001]
  Component:  [name]
  Failure mode: [what happens when it breaks]
  User Impact: [silent failure / error message / crash]
  Severity:    🔴/🟠/🟡

Fragile Components:
  [Component]: [why fragile] → [what would break it]

Bottlenecks:
  [Component]: [sync where it should be async / no cache / unbounded growth]

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```