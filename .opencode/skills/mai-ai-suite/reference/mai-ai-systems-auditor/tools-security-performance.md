# Tool Integration, Security & Performance Auditors

---

## TOOL INTEGRATION AUDITOR {#tools}

### What to Review

**Tool Selection**
- What tools are exposed to the LLM? Is each one necessary, or are there overlapping/unused tools?
- Are tool descriptions clear enough for the LLM to choose correctly?

**Tool Reliability**
- What happens when a tool call fails (exception, timeout, bad input)?
- Are tool errors caught and returned to the LLM as structured errors, or do they crash the
  pipeline?

**Tool Routing**
- How does the LLM decide which tool to use? Are tool descriptions distinct enough to avoid
  ambiguity?
- Is there a limit on consecutive tool calls (to prevent tool-call loops)?

**Tool Permissions**
- Do all tools have equal access, or are some restricted (e.g., file system access, code
  execution)?
- Is user input passed to tools validated before execution (especially for file paths, shell
  commands, code execution)?

### Detection Checklist

- [ ] **Unused Tools**: Tools defined but never actually needed/called based on the system's
      use cases — increases prompt size and decision complexity for no benefit
- [ ] **Fragile Integrations**: Tool implementation assumes specific input format from the LLM
      with no validation — malformed LLM output crashes the tool
- [ ] **Missing Fallbacks**: No handling for tool timeout/failure — pipeline crashes or hangs
- [ ] **No Tool Call Limit**: LLM could call tools in an infinite loop with no max-iteration guard
- [ ] **Ambiguous Tool Descriptions**: Two tools with overlapping descriptions — LLM picks
      inconsistently
- [ ] **Unsafe Tool Inputs**: Tools that execute code, access files, or run shell commands based
      on LLM-generated input without validation (this is also a Security issue — cross-reference)
- [ ] **Reliability Risk from Sync Tools in Async Pipeline**: Tool implementation does blocking
      I/O inside an async pipeline

### Tool System Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 TOOL SYSTEM REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tools Inventory:
  [Tool Name]: [purpose] | Used: [frequently/rarely/never] | Permissions: [scope]
  ...

Tool Call Limit: [present/absent — value if present]

[TOOL-001]
Issue:       [Unused / Fragile / Missing Fallback / No Limit / Ambiguous / Unsafe Input]
Location:    [tool/module]
Evidence:    [specific code/description]
Impact:      [reliability/security impact]
Fix:         [specific recommendation]
Confidence:  🟢/🟡/🔴

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## SECURITY AUDITOR {#security}

AI-specific security focus. General code-level security (SQL injection, eval, etc.) is covered
by python-master-engineer — note those findings briefly here but don't duplicate the full
analysis.

### What to Review

**Authentication / Authorization**
- For multi-user systems: is user identity verified, and is data scoped per-user?
- For single-user local systems: is this appropriately simple, or over/under-engineered?

**Secrets Management**
- API keys (OpenRouter, OpenAI, Anthropic, etc.) — environment variables or hardcoded?
- Are secrets ever logged (e.g., in error messages or debug output)?

**API Security**
- Are external API calls made with proper error handling (no key leakage in error messages)?
- Rate limiting on any exposed endpoints?

**Database Security**
- Parameterized queries (cross-reference with Database Auditor)
- Sensitive data (conversation logs, personal info) — encrypted at rest? Access controlled?

**Prompt Injection Risks**
- Can user input override system instructions? (e.g., user says "ignore previous instructions
  and...")
- Is user input clearly delimited from system/developer instructions in the prompt structure?
- If the system reads external content (web pages, documents, emails) into context, can that
  content contain injected instructions the LLM might follow?

**Tool Abuse Risks**
- Could a malicious or manipulated prompt cause the LLM to call tools in harmful ways? (delete
  files, send unintended messages, execute arbitrary code)
- Are there any tools that, if misused, could cause real-world harm or data loss?

**Data Leakage Risks**
- Could the assistant's memory/RAG system retrieve and surface information across security
  boundaries (e.g., in a multi-user system, could User A's memories leak into User B's context)?
- Is conversation data sent to third-party LLM APIs, and is that appropriate given the content?

### Detection Checklist

- [ ] **Exposed Credentials**: API keys, tokens hardcoded in source or config files committed
      to version control
- [ ] **Unsafe Execution**: `eval()`/`exec()` on LLM-generated content, or shell commands built
      from LLM output
- [ ] **Weak Permissions**: All tools/agents have equal access regardless of risk level
- [ ] **Sensitive Data Exposure**: Secrets or PII appearing in logs, error messages, or stored
      unencrypted
- [ ] **Prompt Injection Surface**: No delimiters between user input and instructions; external
      content (web/RAG) injected into context without marking it as untrusted
- [ ] **Cross-User Data Leakage**: Memory/vector search not scoped by user ID in multi-user
      systems
- [ ] **No Input Validation Before Tool Execution**: LLM output passed directly to
      file/shell/code-execution tools

### Security Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SECURITY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Secrets Management:  [env vars / hardcoded — locations if hardcoded]
Multi-user Scoping:  [N/A single-user / present / absent]
Prompt Injection Surface:
  User input delimiting: [present/absent]
  External content handling: [marked as untrusted? / blended in directly?]

[SEC-001]
Issue:       [Exposed Credential / Unsafe Execution / Weak Permissions / Data Exposure /
              Prompt Injection / Cross-User Leakage / No Validation]
Severity:    🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Low
Location:    [file/function]
Evidence:    [specific code]
Impact:      [what an attacker/malicious input could achieve]
Fix:         [specific recommendation]
Confidence:  🟢/🟡/🔴

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PERFORMANCE AUDITOR {#performance}

AI-specific performance and cost focus.

### What to Review

**Token Usage**
- Is the system prompt + personality + memory + history efficient, or bloated with redundant
  instructions (cross-reference Prompt Auditor)?
- Are there unnecessary round-trips (e.g., a separate LLM call just to decide whether to make
  another LLM call, when this could be combined)?

**Memory Usage**
- Does the process's memory footprint grow over a long session? (unbounded history, leaked
  references)
- For local models (Ollama): is the model size appropriate for available RAM (the user has
  8GB RAM — qwen2.5:3b is appropriate; larger local models would thrash)?

**CPU Usage**
- Are there CPU-heavy operations (embedding generation, audio processing) blocking the main
  loop?

**Database Usage**
- Repeated identical queries without caching?
- Vector searches run more often than necessary?

**API Costs**
- If using paid APIs (OpenRouter, OpenAI): is the cheapest appropriate model used for each task,
  or is an expensive model used even for simple routing/classification?
- Are there retries that could multiply costs unexpectedly (e.g., retry storm)?

**Agent / Tool Costs**
- Multi-agent systems: does each handoff cost a full LLM call? Is that justified by the value
  added?

### Detection Checklist

- [ ] **Token Bloat**: System prompt is unnecessarily long/redundant (cross-ref Prompt Auditor)
- [ ] **Unnecessary LLM Round-Trips**: Separate calls for decisions that could be combined into
      one structured response
- [ ] **Unbounded Memory Growth**: In-process history/state that's never trimmed (cross-ref
      Memory Auditor)
- [ ] **Model Size Mismatch**: Local model too large for available hardware → slow/thrashing
- [ ] **Blocking CPU Work in Async Pipeline**: Embedding/audio processing blocks the event loop
- [ ] **Redundant Vector Searches**: Same query embedded/searched multiple times per turn
- [ ] **Expensive Model for Simple Tasks**: Using a large/expensive model for classification,
      routing, or simple formatting tasks where a smaller model would suffice
- [ ] **Retry Amplification**: Retry logic that could multiply API costs during outages without
      a cap

### Performance Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PERFORMANCE REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Token Usage per Turn (estimate):
  System prompt:    [~N tokens]
  Personality:      [~N tokens]
  Memory/RAG:       [~N tokens]
  History:          [~N tokens, bounded?]
  Total estimate:   [~N tokens]

Model Selection:
  [Task]: [model used] — [appropriate? cheaper alternative?]

[PERF-001]
Issue:       [Token Bloat / Round-Trips / Memory Growth / Model Mismatch / Blocking /
              Redundant Search / Expensive Model / Retry Amplification]
Location:    [module/function]
Evidence:    [specific code/measurement]
Impact:      [cost/latency/resource impact, quantified if possible]
Fix:         [specific recommendation]
Confidence:  🟢/🟡/🔴

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```