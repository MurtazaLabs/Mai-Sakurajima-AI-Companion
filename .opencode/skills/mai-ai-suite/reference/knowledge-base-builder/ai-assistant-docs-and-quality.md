# AI Assistant Documentation, Quality Audit, Knowledge Preservation & Wiki Generation

---

## AI ASSISTANT DOCUMENTATION MODE {#ai-assistant}

The synthesis document for AI companion/assistant projects like Mai_ai — pulls from every
other doc and every specialist skill's findings into one cohesive overview.

### AI_ASSISTANT_OVERVIEW.md Template

```markdown
# [Assistant Name] — AI Assistant Overview

## What Is This?
[2-4 sentences: what the assistant is, who it's for, what makes it distinct]

## Character Design
**Identity**: [who/what the assistant is]
**Personality**: [core traits, with behavioral definitions]
**Voice**: [tone, style — link to PROMPTS.md for full detail]
See `PROMPTS.md` for the full character prompt architecture.

## Prompt Architecture
[High-level summary of the layered prompt system]
See `PROMPTS.md` for full detail.

## Agent Architecture
[Single-agent or multi-agent — high-level summary]
See `AGENTS.md` for full detail.

## Memory Architecture
[High-level summary: what memory types exist, how retrieval/ranking works]
See `MEMORY_SYSTEM.md` for full detail.

## Database Architecture
[High-level summary of persistent storage]
See `DATABASE.md` for full detail.

## Tool Architecture
[What the assistant can do beyond conversation]
See `TOOLS.md` for full detail.

## User Experience Design
**Interaction Model**: [voice/text/hybrid — the actual interface]
**Personalization**: [how the experience adapts per user]
**Reliability Expectations**: [what "working correctly" means for this assistant]

## Scalability Considerations
[Single-user local vs. multi-user hosted — current state and known limits]
See `mai-ai-systems-auditor` scalability findings for full detail, if available.

## System Map
```
[High-level architecture diagram spanning all subsystems]
```

---
*Last updated: [date]*
*Synthesizes: ARCHITECTURE.md, MEMORY_SYSTEM.md, AGENTS.md, PROMPTS.md, DATABASE.md, TOOLS.md*
```

This document should be mostly **links and summaries** — the detail lives in the individual
docs. Its job is to be the front door: someone reads this first, then goes deeper into
whichever subsystem doc they need.

---

## AUTOMATIC DOCUMENTATION GENERATION {#auto-detection}

Whenever analyzing code, repositories, databases, memory systems, agents, or prompts
(whether directly or via another skill's findings in the conversation), proactively
identify:

```
WHAT SHOULD BE DOCUMENTED?  → Major components with no corresponding doc
WHAT'S MISSING?              → Doc sections that exist but are incomplete
WHAT'S OUTDATED?             → Docs that no longer match the actual code/behavior
```

Don't wait to be asked "is anything missing" — flag this naturally when you notice it
during any documentation task, the same way a careful colleague would say "by the way,
there's no doc for the scheduler at all."

### Outdated Documentation Detection

A doc is outdated when:
- It references files/functions/classes that no longer exist or have been renamed
- It describes behavior that contradicts what the code actually does
- It has no "last updated" marker and the surrounding code has clearly changed since
  (new patterns, new dependencies not mentioned)
- It documents a decision that's been superseded without a note pointing to the new one

---

## DOCUMENTATION QUALITY AUDITOR {#quality-audit}

### Quality Dimensions

**Completeness** — are all major components/systems documented at all?
**Accuracy** — does the documentation match current reality?
**Consistency** — same terminology, same structure across documents?
**Clarity** — could a new reader actually understand it?
**Maintainability** — is it structured so updates are easy, or will it rot?
**Searchability** — can someone find the answer to a specific question quickly?

### Documentation Quality Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DOCUMENTATION QUALITY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Completeness:      🟢/🟡/🟠/🔴 — [what's covered, what's missing]
Accuracy:          🟢/🟡/🟠/🔴 — [any stale/wrong content found]
Consistency:       🟢/🟡/🟠/🔴 — [terminology/structure consistency]
Clarity:           🟢/🟡/🟠/🔴 — [readability for a new audience]
Maintainability:   🟢/🟡/🟠/🔴 — [structure supports easy updates?]
Searchability:     🟢/🟡/🟠/🔴 — [organized for finding answers fast?]

[DOC-001]
Issue:       [Missing / Outdated / Inconsistent / Unclear / Hard to Maintain / Hard to Find]
Location:    [doc/section]
Evidence:    [specific gap or problem]
Fix:         [specific recommendation]

[DOC-002] ...

Overall Documentation Health: 🟢/🟡/🟠/🔴
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## KNOWLEDGE PRESERVATION MODE {#preservation}

Identify knowledge that exists only in someone's head, in scattered chat history, or in
no durable form at all — before it's lost.

### What to Look For

**Critical Knowledge** — things that, if forgotten, would seriously hurt the project
(e.g., "why the context window was set to a specific value", "the reason a workaround
exists for a specific library bug")

**Hidden Knowledge** — true but undocumented facts about how the system actually behaves
(e.g., "the scheduler silently fails if X happens" — known from experience, not written
anywhere)

**Tribal Knowledge** — things "everyone just knows" because they were there when it
happened, but a new person would have no way to discover

**Undocumented Processes** — how things actually get done (deployment steps, debugging
approaches, recovery procedures) that only exist as muscle memory

**Single Points of Knowledge** — for a solo project, this means: what happens if you
forget this in 6 months? For a team, it's about bus-factor.

### Knowledge Risk Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 KNOWLEDGE RISK REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[KNOW-001]
Type:        [Critical / Hidden / Tribal / Undocumented Process / Single Point]
Description: [the knowledge at risk]
Risk:        [what happens if this is lost/forgotten]
Recommendation: [which doc this should live in, and what to capture]

[KNOW-002] ...

Highest Priority to Preserve: [the single most important item to write down right now]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

For a solo developer specifically: this mode is most useful as a "write it down before you
forget why you did this" prompt — periodically ask what's been decided/learned recently that
hasn't made it into DECISIONS.md, MEMORY_SYSTEM.md known limitations, or TECHNICAL_DEBT.md.

---

## REPOSITORY WIKI GENERATOR {#wiki}

Generates a complete documentation set in one pass. Use when the user wants comprehensive
documentation built from scratch, or wants everything brought up to date at once.

### Standard Wiki Structure

```
docs/
├── README.md              # Entry point — links to everything below
├── ARCHITECTURE.md
├── DATABASE.md
├── MEMORY_SYSTEM.md        # if applicable
├── AGENTS.md                # if applicable
├── PROMPTS.md                # if applicable
├── TOOLS.md
├── WORKFLOWS.md
├── DECISIONS.md
├── TECHNICAL_DEBT.md
├── CHANGELOG.md
├── DEVELOPER_GUIDE.md
└── AI_ASSISTANT_OVERVIEW.md  # if this is an AI assistant project
```

### Generation Workflow

1. Run the Knowledge Discovery Protocol first — understand the system before writing
   anything
2. Determine which documents actually apply (skip DATABASE.md if there's no database,
   skip AGENTS.md for non-agent systems, etc.) — never generate empty/placeholder docs
   for things that don't exist
3. Build documents in dependency order: REPOSITORY_OVERVIEW and ARCHITECTURE first (other
   docs reference these), then the specific subsystem docs, then the synthesis docs
   (AI_ASSISTANT_OVERVIEW, DEVELOPER_GUIDE) last since they link to everything else
4. Write actual files via `create_file`, save to `/mnt/user-data/outputs/docs/`, and use
   `present_files` to share the complete set
5. Generate a `README.md` as the entry point with a short description of the project and
   a linked table of contents to every other doc

### README.md Template (wiki entry point)

```markdown
# [Project Name]

[1-2 sentence description]

## Documentation

| Document | Covers |
|----------|--------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and component relationships |
| [DATABASE.md](DATABASE.md) | Schema, relationships, query patterns |
| [MEMORY_SYSTEM.md](MEMORY_SYSTEM.md) | Memory types, retrieval, ranking |
| [AGENTS.md](AGENTS.md) | Agent responsibilities and boundaries |
| [PROMPTS.md](PROMPTS.md) | Prompt architecture and hierarchy |
| [TOOLS.md](TOOLS.md) | Available tools and their behavior |
| [WORKFLOWS.md](WORKFLOWS.md) | User flows, data flows, failure handling |
| [DECISIONS.md](DECISIONS.md) | Why things are built the way they are |
| [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) | Known issues and priorities |
| [CHANGELOG.md](CHANGELOG.md) | What's changed over time |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | Setup and contribution guide |

## Quick Start
[The fastest path to running this project — full detail in DEVELOPER_GUIDE.md]

---
*Documentation last generated: [date]*
```