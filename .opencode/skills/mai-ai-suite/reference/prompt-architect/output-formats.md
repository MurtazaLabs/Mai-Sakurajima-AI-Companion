# Output Formats & Scoring

---

## Standard Full Output Format

For any prompt review, design, or audit, always produce these sections:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PROMPT ARCHITECT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## PROMPT OBJECTIVE
[What is this prompt for? What behavior should it produce?]

## PROMPT TYPE
[System / Developer / Skill / Character / Agent / Memory / Tool / Multi-layer]

## ARCHITECTURE ANALYSIS
[Which layer(s) does this belong to? Is it at the right layer?
 How does it interact with other prompts in the stack?]

## CONFLICT ANALYSIS
[Any internal or cross-layer conflicts found?
 Use CONFLICT-NNN format. If none: "No conflicts detected."]

## OPTIMIZATION OPPORTUNITIES
[Specific improvements with before/after examples.
 Always explain WHY each change improves behavior.]

## RISK ANALYSIS
[Hallucination risks, drift risks, injection risks, reliability risks.
 Use RISK-NNN format. If none: "No significant risks identified."]

## RECOMMENDED CHANGES
[Prioritized list of changes to make, from critical to low.
 Each change: what to change, where, and why.]

## FINAL PROMPT
[Complete, ready-to-use prompt — always produce this, even for reviews.
 Don't just describe changes — show the result.]

## TESTING RECOMMENDATIONS
[3-5 specific test cases to verify the prompt works as intended.
 Format: Input → Expected behavior]

## OVERALL SCORE
[9-category scorecard — see scoring section below]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 9-Category Scoring System

### Score Output Format

```
┌────────────────────────────────────────────────┐
│          PROMPT QUALITY SCORECARD              │
├───────────────────────┬───────┬────────────────┤
│ Category              │ Score │ Note           │
├───────────────────────┼───────┼────────────────┤
│ Clarity               │  X/10 │ [one line]     │
│ Specificity           │  X/10 │ [one line]     │
│ Reliability           │  X/10 │ [one line]     │
│ Consistency           │  X/10 │ [one line]     │
│ Scalability           │  X/10 │ [one line]     │
│ Maintainability       │  X/10 │ [one line]     │
│ Hallucination Resist. │  X/10 │ [one line]     │
│ Model Compatibility   │  X/10 │ [one line]     │
├───────────────────────┼───────┼────────────────┤
│ OVERALL               │  X/10 │ [grade]        │
└───────────────────────┴───────┴────────────────┘

Status:  🟢 Excellent (9-10)  🟡 Good (7-8)
         🟠 Needs Work (5-6)  🔴 Poor (1-4)
Grade:   A (9-10) | B (7-8) | C (5-6) | D (3-4) | F (1-2)
```

### Scoring Rubrics

**Clarity (1-10)**
- 9-10: Every instruction has exactly one interpretation; zero ambiguity
- 7-8: Mostly clear; 1-2 phrases that could be misread
- 5-6: Several vague terms ("appropriate", "natural", "good"); model must guess
- 3-4: Majority of instructions are ambiguous or underspecified
- 1-2: Uninterpretable — model is essentially unprompted

**Specificity (1-10)**
- 9-10: Role, scope, output format, edge cases all defined concretely
- 7-8: Core task specific; some edge cases undefined
- 5-6: General task defined; scope and format left to model discretion
- 3-4: Only the role is named; no behavioral specifics
- 1-2: "You are a helpful assistant." level

**Reliability (1-10)**
- 9-10: Deterministic — same input consistently produces correct behavior
- 7-8: Mostly reliable; minor variance in edge cases
- 5-6: Works for central cases; drifts on unusual inputs
- 3-4: Inconsistent even on standard inputs
- 1-2: Completely unpredictable

**Consistency (1-10)**
- 9-10: No internal contradictions; behavior holds across long conversations
- 7-8: Consistent internally; may drift after many turns
- 5-6: Minor contradictions that rarely surface
- 3-4: Multiple contradictions that confuse model behavior
- 1-2: Instructions actively work against each other

**Scalability (1-10)**
- 9-10: Works correctly at conversation turn 1 and turn 50
- 7-8: Holds with moderate conversation length; minor drift at very long
- 5-6: Works early; personality/behavior degrades over long sessions
- 3-4: Instructions assume short context; breaks with any memory/history injection
- 1-2: Only works in the first 1-2 turns

**Maintainability (1-10)**
- 9-10: Well-organized by category; another person can update safely
- 7-8: Mostly organized; some rules are buried or duplicated
- 5-6: Functional but wall-of-text; hard to update without breaking something
- 3-4: Unstructured; high risk of introducing conflicts when editing
- 1-2: Unmaintainable — editing it is guesswork

**Hallucination Resistance (1-10)**
- 9-10: Explicit constraints on uncertainty; fact/fiction boundaries clear
- 7-8: Good constraints; 1-2 uncovered edge cases where model might fabricate
- 5-6: Some constraints; significant gaps that invite confabulation
- 3-4: No uncertainty handling; model will invent answers to stay in character
- 1-2: Actively encourages confabulation ("always have an answer")

**Model Compatibility (1-10)** — Score for the specified target model
- 9-10: Prompt style, length, and instruction type match model's strengths
- 7-8: Works well; minor style mismatches
- 5-6: Generic prompt not optimized for this model's behavior
- 3-4: Prompt style fights the model's defaults
- 1-2: Written for a different model family entirely

---

## Prompt Library Entry Format

When creating reusable prompts, format as library entries:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PROMPT LIBRARY ENTRY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name:            [Unique identifier]
Version:         [1.0.0]
Layer:           [System / Developer / Skill / Context]
Purpose:         [One sentence]
Target Model(s): [Claude / GPT / Qwen / All]
Dependencies:    [Other prompts this requires to work correctly]

Inputs:          [What dynamic variables get injected: {variable_name}]
Outputs:         [What the model produces with this prompt]

Usage Guidelines:
  [When to use this]
  [When NOT to use this]
  [Known limitations]

Prompt Text:
  [Complete prompt with {variable} placeholders]

Test Cases:
  Input:    [example input]
  Expected: [expected output behavior]

Version History:
  1.0.0 — [date] — [initial version]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Quick Reference: Prompt Anti-Patterns

These patterns appear in nearly every weak prompt. Flag them immediately:

| Anti-Pattern | Symptom | Fix |
|-------------|---------|-----|
| Vague role | "You are helpful" | "You are [specific entity] who [specific purpose]" |
| "Always" without scope | "Always be concise" | "Keep responses under 3 sentences for casual questions" |
| No output format | Model picks format randomly | Add explicit format spec with example |
| Missing fallback | Model hallucinates when stuck | Add "If you can't [do X], say [Y]" |
| No constraints | Model does anything it wants | Add 3-5 explicit NEVER rules |
| Contradictory tone | "Be warm AND professional" | Define which wins, or define triggers |
| No injection protection | User can override instructions | Delimit user input; add resistance rule |
| Buried critical rules | Key rule on line 40 | Move most important rules to top 5 lines |
| Character = license | Character justifies bad output | "Character voice applies to TONE, not accuracy" |
| No length guidance | Responses vary wildly in length | "Default response length: [X]" |

---

## Model-Specific Prompt Notes

### For Qwen 2.5:3B (local — used in Mai_ai)
- **Keep system prompts SHORT** — 3B models weight recent tokens disproportionately;
  long system prompts dilute all but the last few instructions
- **Be extremely explicit** — Qwen 3B infers less from context than larger models;
  write what you mean, don't imply it
- **Repeat critical rules** — unlike larger models that remember a rule from turn 1
  across 20 turns, small models benefit from key rules being restated in injected context
- **Simple sentence structure** — avoid complex nested conditionals in instructions;
  break them into simple if/then pairs
- **Recommended max system prompt length**: ~500 tokens for 3B models

### For Claude (claude.ai)
- Responds well to XML-structured prompts (`<role>`, `<rules>`, `<examples>`)
- Excellent at following nuanced conditional instructions
- Benefits from explicit reasoning requests ("think step by step before answering")
- Strong instruction hierarchy adherence — system prompt rules hold well

### For GPT-4o
- Excellent tool use and JSON adherence
- Responds well to explicit format examples (few-shot)
- Good at long-context instruction following
- Benefits from numbered rules (follows ordering)

### For Llama 3.x (local)
- Similar to Qwen: be explicit, keep it short for smaller models
- Llama 3 70B+ handles complex prompts well; 8B and below need simple instructions
- Responds well to direct imperative style: "Do X. Do not Y."