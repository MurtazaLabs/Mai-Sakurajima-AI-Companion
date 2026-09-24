# Reliability, Scalability & Technical Debt Auditors

---

## RELIABILITY AUDITOR {#reliability}

### What to Review

**Error Handling**
- Are errors from LLM calls, tool calls, memory operations, and TTS/STT caught and handled, or
  do they propagate as crashes?
- Are error messages useful for debugging (include context: which component, what input)?

**Recovery Systems**
- If the LLM provider fails, is there a fallback (e.g., OpenRouter free model → local Ollama)?
- If memory retrieval fails, does the assistant still respond (degraded, without memory) or
  does it crash?

**Fallback Systems**
- For each critical component (LLM, memory, TTS, STT), what's the fallback when it's
  unavailable?

**Agent Failures**
- If an agent in a multi-agent system fails/times out, what happens? Does the router retry,
  fall back to a default agent, or does the whole request fail?

**Tool Failures**
- Already covered in Tool Auditor — cross-reference here for overall reliability impact.

**Memory Failures**
- If ChromaDB/vector store is unreachable, does the system degrade gracefully or crash?

### Detection Checklist

- [ ] **No LLM Fallback**: Single provider/model with no fallback — provider outage = total
      assistant outage
- [ ] **Memory Failure = Crash**: Vector store connection failure isn't caught, crashes the
      whole pipeline instead of degrading to "no memory context" mode
- [ ] **Silent Failures**: `except: pass` or equivalent on critical operations — failures
      invisible to both user and developer
- [ ] **No Startup Validation**: System starts even if critical config (`Settings.*`) is
      missing/misconfigured, then crashes on first use instead of failing fast at startup
- [ ] **Unhandled Async Task Failures**: `asyncio.create_task()` without exception handling —
      background task failures disappear silently
- [ ] **No Graceful Degradation Path**: Every component failure is treated as fatal, when many
      could degrade gracefully (no memory → respond without context; no TTS → text-only response)

### Reliability Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 RELIABILITY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Component Fallback Matrix:
  LLM:        Primary: [model] → Fallback: [model/none]
  Memory:     Failure mode: [crash/degrade] → Fallback: [describe]
  TTS:        Failure mode: [crash/degrade] → Fallback: [describe]
  STT:        Failure mode: [crash/degrade] → Fallback: [describe]
  Tools:      Failure mode: [per Tool Auditor]

Startup Validation: [present/absent]

[REL-001]
Issue:       [No Fallback / Crash on Failure / Silent Failure / No Validation /
              Unhandled Async / No Degradation]
Location:    [module/function]
Evidence:    [specific code]
Impact:      [what fails and how visibly]
Fix:         [specific recommendation]
Confidence:  🟢/🟡/🔴

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## SCALABILITY AUDITOR {#scalability}

### What to Review

Predict what happens to the AI assistant ecosystem at each scale level. For single-user/local
assistants, "scale" may mean conversation length and memory growth over time rather than
concurrent users — adapt the framework accordingly and say so.

### Scale Prediction Framework

For multi-user/hosted systems:
```
100 users:      [LLM API rate limits? DB connections? Vector store size?]
1,000 users:    [Cost at this volume? Concurrent request handling?]
10,000 users:   [Vector store performance with N×1000 memories per user?]
100,000 users:  [Architectural changes needed — sharding, caching, queueing?]
1,000,000 users: [Complete re-architecture likely needed — what would it look like?]
```

For single-user/local systems, reframe as:
```
After 1 week of use:    [memory store size, context handling]
After 1 month of use:   [memory store growth, retrieval quality degradation?]
After 1 year of use:    [vector store size, performance impact, pruning needed?]
```

### Detection Checklist

- [ ] **Vector Store Growth**: No pruning/archiving strategy — retrieval quality and speed
      degrade as the store grows unbounded
- [ ] **In-Memory State Bottleneck**: Conversation state, agent state held in-process — doesn't
      survive restarts, doesn't scale to multiple instances
- [ ] **LLM Rate Limits**: Free-tier API usage (e.g., OpenRouter free models) has rate limits
      that become binding at even modest usage
- [ ] **Local Model Hardware Limits**: Local Ollama model size vs. available RAM/CPU — what
      breaks first as conversation length/complexity grows?
- [ ] **Database Scaling**: SQLite is fine for single-user but becomes a bottleneck for
      concurrent multi-user access (file locking)
- [ ] **No Caching Layer**: Repeated expensive operations (embeddings, LLM calls for common
      queries) recomputed every time

### Scalability Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SCALABILITY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
System Type: [single-user local / multi-user hosted]

[Use the appropriate prediction framework from above]

Prediction:
  [Scale point 1]: ✅/⚠️/❌ [what happens]
  [Scale point 2]: ✅/⚠️/❌ [what happens]
  [Scale point 3]: ✅/⚠️/❌ [what happens]

Bottlenecks Identified:
  [Bottleneck]: [location, severity, fix]

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## TECHNICAL DEBT SCANNER {#debt}

AI-ecosystem-specific debt — covers debt in agents, prompts, memory, RAG, and AI infrastructure.
General code debt is covered by python-codebase-architect.

### Debt Categories

**Critical Debt** (production-threatening)
- Missing `Settings.*` constants causing startup crashes
- Inconsistent state access paths (`kernel.memory` vs `kernel.brain.memory`) causing
  AttributeErrors
- Direct provider imports bypassing the manager abstraction (e.g., importing `OllamaLLM`
  directly instead of through `LLMManager`) — breaks fallback logic
- Hardcoded API keys

**High Debt** (likely future failures)
- No LLM fallback chain
- Memory/vector store failures crash the pipeline
- No tool call iteration limit
- Personality prompt not protected from context truncation

**Medium Debt** (maintainability concerns)
- Prompt redundancy across system/agent/skill prompts
- Memory pollution (no filtering of what gets stored)
- No re-ranking or threshold on RAG retrieval
- Agent overlap / unclear boundaries

**Low Debt** (minor improvements)
- Missing docstrings on agent/tool definitions
- Inconsistent logging across components
- Unused tool definitions

### Technical Debt Heatmap Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 TECHNICAL DEBT HEATMAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Component:  [e.g., emotion.py]
Risk:       🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Low
Reason:     [specific issue with evidence]
Priority:   [Immediate / This Sprint / This Quarter / Backlog]
Confidence: 🟢/🟡/🔴

Component:  [e.g., scheduler.py]
Risk:       ...
Reason:     ...
Priority:   ...
Confidence: ...

[Repeat for each component with identified debt]

Heatmap Summary (sorted by risk):
  🔴 Critical: [count] — [list components]
  🟠 High:     [count] — [list components]
  🟡 Medium:   [count] — [list components]
  🔵 Low:      [count] — [list components]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```