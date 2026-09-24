# Agent, Prompt & Character Auditors

---

## AGENT ARCHITECTURE AUDITOR {#agent}

### What to Review

**Agent Responsibilities**
- Does each agent have a single, clear purpose?
- Is there overlap where two agents could both handle the same request?
- Are agent boundaries defined by the prompt only, or also enforced in code (e.g., restricted
  tool access per agent)?

**Agent Boundaries**
- What can each agent do that others can't? (tool access, data access, scope of topics)
- Is there a "catch-all" agent that handles everything not matched elsewhere — and is that
  appropriate or a sign of poor routing?

**Agent Communication**
- How do agents pass information? (shared state, explicit message passing, return values)
- Is there a risk of context loss between agent handoffs?
- Is there a risk of context duplication (same info passed redundantly, wasting tokens)?

**Agent Orchestration**
- Who decides which agent handles a request? (router LLM call, keyword matching, fixed pipeline)
- Is the routing logic deterministic or LLM-based? (LLM-based routing can be inconsistent)
- Is there a maximum iteration/handoff limit to prevent infinite loops?

### Detection Checklist

- [ ] **Agent Overlap**: Two or more agents with prompts that could both claim the same request
- [ ] **Agent Confusion**: Router prompt doesn't clearly distinguish between agent capabilities
- [ ] **Routing Failures**: No fallback when router can't confidently pick an agent
- [ ] **Workflow Inefficiencies**: Unnecessary agent hops for simple requests (e.g., routing a
      "hello" through 3 agents before responding)
- [ ] **No Loop Protection**: Agents can hand off to each other with no max-iteration guard
- [ ] **Lost Context on Handoff**: Agent B doesn't receive what Agent A learned
- [ ] **Inconsistent State Access**: Some agents access `kernel.memory`, others access
      `kernel.brain.memory` — same logical data, different paths (common source of AttributeErrors)

### Agent Architecture Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 AGENT ARCHITECTURE REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agents Identified:
  [Agent Name]: [responsibility] | Tools: [list] | Triggers: [how it's invoked]
  ...

Overlap Issues:
  [Agent A] vs [Agent B]: [where they could both claim the same request]

Routing Mechanism: [LLM-based / keyword / fixed pipeline]
  Fallback when routing fails: [yes/no — describe]
  Loop protection: [yes/no]

Communication Pattern: [shared state / message passing / return values]
  Context loss risk: [where]
  Context duplication risk: [where]

Workflow Efficiency:
  [Any unnecessary hops for simple requests]

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PROMPT ARCHITECTURE AUDITOR {#prompt}

### What to Review

**Prompt Inventory**
- System prompts (top-level identity/instructions)
- Developer/skill prompts (task-specific instructions)
- Agent prompts (per-agent role definitions)
- Memory prompts (instructions for how memory is summarized/retrieved/injected)

**For each prompt, check:**
- Length (overly long prompts dilute attention, overly short ones underspecify)
- Specificity (vague instructions like "be helpful" vs concrete behavioral rules)
- Internal consistency (does the prompt contradict itself?)

### Detection Checklist

- [ ] **Contradictions**: One prompt says "always do X", another says "never do X" or "do Y instead"
- [ ] **Conflicts Across Layers**: System prompt says one thing, agent prompt overrides it
      silently (which wins? is that intentional?)
- [ ] **Redundancy**: Same instruction repeated across multiple prompts — increases token cost,
      risk of them drifting out of sync
- [ ] **Weak Instructions**: Vague guidance ("be natural", "respond appropriately") with no
      concrete behavioral definition
- [ ] **Ambiguous Instructions**: Instructions that could be interpreted multiple ways
      (e.g., "keep responses short" — how short? always, or only sometimes?)
- [ ] **Hallucination Risks**: Prompts that encourage confident answers without grounding
      (e.g., "always have an answer" without "say you don't know if uncertain")
- [ ] **Missing Guardrails**: No instructions for what to do when memory retrieval fails, tool
      calls fail, or input is malformed
- [ ] **Prompt Injection Surface**: User input concatenated directly into prompts without
      delimiters or sanitization — could let user input override instructions

### Prompt Health Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PROMPT HEALTH REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Prompt Inventory:
  System Prompt:    [location, length, purpose]
  Agent Prompts:    [list with location/purpose]
  Skill Prompts:    [list with location/purpose]
  Memory Prompts:   [location, what it instructs]

[PROMPT-001]
Issue:        [Contradiction / Conflict / Redundancy / Weak / Ambiguous / Hallucination Risk]
Location:     [which prompt(s)]
Description:  [what's wrong]
Evidence:     [the specific conflicting/weak text]
Impact:       [what behavior this causes or risks]
Fix:          [specific rewording or restructuring]
Confidence:   🟢/🟡/🔴

[PROMPT-002]
...

Prompt Injection Surface:
  [Where user input enters prompts, whether it's delimited/sanitized]

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## CHARACTER CONSISTENCY AUDITOR {#character}

Relevant for assistants with a defined personality/character (e.g., anime-inspired companions,
branded assistants with a "voice").

### What to Review

**Personality Design**
- Is the personality defined in one place, or scattered across multiple prompts/files?
- Are personality traits specific and actionable (e.g., "responds with dry humor when teased")
  or vague (e.g., "has a fun personality")?

**Behavioral Rules**
- Are there explicit rules for how the character responds in different situations (happy, asked
  a hard question, asked something off-limits)?
- Do behavioral rules conflict with the base system prompt's instructions (e.g., character is
  "sassy and pushes back" but system prompt says "always agree and be deferential")?

**Conversation Style**
- Is the tone/vocabulary/sentence structure consistent across different code paths that
  generate responses (e.g., normal chat vs. tool-result summaries vs. error messages)?

**Emotional Consistency** (for systems with emotion/mood state)
- Is emotional state persisted, or reset every session?
- Do emotional states map to actual behavioral changes, or just a label that's stored but
  unused?
- Can emotional state get stuck (e.g., stuck in "angry" with no path back to neutral)?

**Long-Term Consistency**
- Does the character "remember" its own personality across sessions (via memory), or does it
  reset to a generic assistant after context window fills up?
- If personality is in the system prompt only, does it survive context truncation/summarization?

### Detection Checklist

- [ ] **Personality Drift**: Character behaves noticeably differently early vs. late in long
      conversations (often due to context truncation dropping the personality prompt)
- [ ] **Contradictory Instructions**: Personality traits conflict with safety/behavior rules
      elsewhere in the prompt stack
- [ ] **Character Instability**: No mechanism to keep personality consistent — relies entirely
      on the LLM "remembering" from a prompt that may get truncated
- [ ] **Broken Immersion**: Error messages, tool outputs, or system messages presented in a
      different voice/format than the character (e.g., character is warm and casual, but
      errors say "Error: NoneType object has no attribute...")
- [ ] **Emotion State Disconnect**: Emotion/mood values are tracked but don't influence actual
      prompt construction or response generation
- [ ] **Unused Personality Config**: Personality traits defined in config/data files that
      aren't actually loaded into the prompt at runtime

### Character Consistency Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CHARACTER CONSISTENCY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Personality Definition:
  Location(s): [where personality is defined]
  Specificity: [concrete behavioral rules vs vague traits]

Behavioral Rules:
  [list key rules and where they're enforced — prompt only, or also in code]

Conflicts with Base Instructions:
  [PROMPT vs PERSONALITY] — [describe conflict]

Conversation Style Consistency:
  [Where style breaks — error messages, tool outputs, fallback responses]

Emotional System: (if present)
  State persistence: [per-session / cross-session / none]
  Behavioral impact: [does emotion state actually change responses?]
  Stuck-state risk:  [can it get stuck in one emotion with no recovery?]

Long-Term Consistency:
  Personality survival under context truncation: [at risk / protected — how]

[CHAR-001]
Issue:       [Drift / Contradiction / Instability / Broken Immersion / Disconnect]
Location:    [file/prompt]
Evidence:    [specific text or code]
Impact:      [what the user experiences]
Fix:         [specific recommendation]
Confidence:  🟢/🟡/🔴

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```