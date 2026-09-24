# Character Rename PRD — Identity Layer Migration

> **Status:** **DECIDED** — Migration in progress  
> **Priority:** P1 (blocks public release)  
> **Date:** 2026-08-29  
> **Final Name:** **Yukira**  
> **Owner:** AI Product Manager + Character Narrative Designer + Python Master Engineer

---

## Executive Summary

**"Mai" is a trademark liability.** The name is identical to the anime character **Mai Sakurajima** from *Rascal Does Not Dream of Bunny Girl Senpai*. USPTO/WIPO similarity searches will flag this. A public launch would face cease-and-desist or forced rebrand.

**Decision:** **Yukira** — selected 2026-08-29. Pre-launch rename executed via config-driven identity migration. Personality, canon (4 volumes), psychological architecture **unchanged**.

**Scope:** `Mai` → `Yukira` via canonical identity migration. Personality, canon (4 volumes), psychological architecture **unchanged**.

---

## Product Discovery

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PRODUCT DISCOVERY REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Problem:          "Mai" = trademark risk (existing anime character IP).
                  Every week of usage deepens rebrand cost.

Target User:      Sole developer + primary user (future: potential users).

Pain Point:       Building brand equity on a name we don't own.

Business Impact:  Project viability — forced rebrand post-launch destroys 
                  trust, breaks continuity, wastes months of canon work.

Desired Outcome:  Distinctive, trademark-clear name fitting existing personality.
                  Zero disruption to 4-volume canon or psychological architecture.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Idea Evaluation

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 IDEA EVALUATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Idea Summary:        Rename "Mai" → [NewName] via config-driven identity migration.
                     Generate 20–30 candidates → weighted scoring → trademark screen.

Potential Benefits:  
  - Eliminates existential trademark risk pre-launch
  - Creates ownable brand asset (domain, handle, mark)
  - Forces cleanup of hardcoded "Mai" refs (tech debt payoff)
  - Psychological: owning the name strengthens product identity

Potential Drawbacks:  
  - Engineering effort: ~40–60 files reference "Mai"
  - Migration must be thorough (prompts, memory, voice, tests, docs)
  - User habit retraining
  - Risk of picking another conflicted name without screening

Complexity:          Medium — well-scoped migration, wide surface area
Risk:                Medium — trademark conflict if screening skipped;
                     personality drift if name leaks into prompts

Recommendation:      **Build now** — architecture supports this. 
                     Do it seriously: generate → score → screen → choose → migrate.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Scoring Framework (7 Criteria)

| Criterion | Weight | Guide |
|-----------|--------|-------|
| **Distinctiveness** | 25% | Unique phonemes; not generic AI names (Aria, Nova, Luna, Maya, Eve) |
| **Trademark Clearance Potential** | 25% | Low AI/fictional collisions; distinctive spelling helps |
| **Character Fit** | 15% | Matches personality: sophisticated, reserved, emotionally intelligent, playful-but-grounded |
| **Pronunciation** | 10% | 2–3 syllables, intuitive spelling, cross-lingual |
| **Memorability** | 10% | Sticks after one hearing |
| **Domain/Brand Potential** | 10% | `.com`/.`ai` available; `@handle` free |
| **International Usability** | 5% | No unfortunate meanings; easy romanization |

---

## Candidate Pool (25 Generated)

| Name | Phonetics | Vibe | Distinctiveness | Key Notes |
|------|-----------|------|-----------------|-----------|
| **Veyra** | /ˈveɪ.rə/ | Elegant, precise | High | "vera" (truth) adjacent |
| **Sylis** | /ˈsaɪ.lɪs/ | Sharp, modern | High | Tech-forward |
| **Elian** | /ˈiː.li.ən/ | Warm, classic | Medium | Approachable |
| **Calyx** | /ˈkæ.lɪks/ | Structured, organic | Very High | Protects the flower/bud |
| **Riven** | /ˈrɪv.ən/ | Complex, layered | High | Duality fits |
| **Aeris** | /ˈɛə.rɪs/ | Airy, light | Medium | FF association (risk) |
| **Nyxia** | /ˈnɪk.si.ə/ | Night, mystery | High | Nyx + feminine |
| **Oriel** | /ˈɔː.ri.əl/ | Golden, dawn | Medium | Architectural + angelic |
| **Vespera** | /vɛsˈpɛr.ə/ | Evening, reflective | High | "Vesper" root |
| **Zephyra** | /zɛˈfaɪ.rə/ | Light, swift | High | Zephyr (west wind) |
| **Isolde** | /ɪˈsoʊl.də/ | Romantic, tragic | Medium | Wagner/Arthurian |
| **Cassia** | /ˈkæʃ.ə/ | Warm, spice | Medium | Gentle |
| **Thalassa** | /θəˈlæs.ə/ | Deep, vast | High | Greek "sea" — memory metaphor |
| **Eowyn** | /ˈeɪ.oʊ.wɪn/ | Noble, shield | Medium | LotR (strong IP) |
| **Liora** | /liˈɔː.rə/ | Light, mine | Medium | Hebrew "my light" |
| **Sereia** | /səˈreɪ.ə/ | Siren, song | High | Portuguese "mermaid" |
| **Amaris** | /əˈmɑː.rɪs/ | Promised, bitter | Medium | Latin "bitter" |
| **Vaelin** | /ˈveɪ.lɪn/ | Soft, balanced | High | No strong associations |
| **Ondine** | /ɒnˈdiːn/ | Water spirit | Medium | Mythological |
| **Caelum** | /ˈkaɪ.ləm/ | Sky, heaven | High | Latin "sky" — vault metaphor |
| **Lyra** | /ˈlaɪ.rə/ | Lyre, constellation | Medium | His Dark Materials |
| **Sylva** | /ˈsɪl.və/ | Forest, wild | Medium | Latin "forest" |
| **Eira** | /ˈaɪ.rə/ | Snow, mercy | High | Welsh/Norse |
| **Vesna** | /ˈvɛs.nə/ | Spring, renewal | High | Slavic "spring" |
| **Azura** | /əˈzjʊə.rə/ | Sky blue | Medium | Common in games |

---

## Top 5 Shortlist (Pre-Screening)

| Rank | Name | Est. Score | Strengths | Flags |
|------|------|------------|-----------|-------|
| 1 | **Veyra** | ~88 | Distinctive, pronounceable, "vera" resonance | Check `.ai` domain |
| 2 | **Calyx** | ~86 | Perfect metaphor (protects the bud), unique | 1-syllable risk |
| 3 | **Vaelin** | ~84 | Original, soft, balanced, no baggage | Unknown = no associations |
| 4 | **Thalassa** | ~82 | Deep metaphor (sea = memory), elegant | Longer; pronunciation |
| 5 | **Vespera** | ~81 | Evening/reflective, sophisticated | 3 syllables |

---

## Risk Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 RISK REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[RISK-001] Legal/Trademark — 🔴 Critical
  Selected name has existing TM in AI/software (Class 9/42)
  Mitigation: USPTO TESS + WIPO + common law search BEFORE selection.
              Budget $500–2000 for attorney opinion.

[RISK-002] Product/UX — 🟠 High
  Name doesn't "feel like her" — personality mismatch
  Mitigation: Character Designer validates top 3 vs Volumes I–IV.
              Test in conversation before commit.

[RISK-003] Technical/Migration — 🟠 High
  Incomplete migration leaves "Mai" in prompts/vault/memory
  Mitigation: Automated grep audit + IdentityCore as single source.
              Migration script + test suite validation.

[RISK-004] Security/Brand — 🟡 Medium
  Domain/handle squatting before registration
  Mitigation: Register .com/.ai + @handles IMMEDIATELY after selection.

[RISK-005] Scalability/International — 🔵 Low
  Negative meaning in major language
  Mitigation: Native speaker check for top 3 (JA, ZH, ES, DE, FR, PT, KO)

Summary: 2 Critical, 2 High, 1 Medium, 1 Low. Overall: HIGH — trademark is blocker.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Roadmap

### Phase 1 — Candidate Generation & Screening (Week 1)
- Score all 25 on 7 criteria with Character Designer input
- USPTO TESS + WIPO + Google + social handles for top 10
- Eliminate conflicts → narrow to top 5
- Deep TM attorney opinion on top 3 ($500–2000)
- Character Designer validates top 3 vs Volumes I–IV
- **Exit:** 3 names with attorney "likely clear" + character fit ≥ 14/15 + domain/handle available

### Phase 2 — Final Selection & Brand Lock (Week 1–2)
- Choose final name from 3 finalists
- Register `.com` + `.ai` domains
- Claim @handles (X, Discord, GitHub, Bluesky, Reddit)
- File USPTO intent-to-use (if commercial)
- Update `IdentityCore` config
- **Exit:** All brand assets secured; zero "Mai" in `IdentityCore`

### Phase 3 — Canonical Migration (Week 2)
- Automated migration script (`scripts/migrate_character_name.py`)
- Manual review: prompts, voice persona, vault folders, docs
- Update `AGENTS.md`, `MERGED_COMPLETE.md`, vault README, all `.md`
- Full test suite (1,832 tests) — zero failures
- Vault recompilation with new name
- **Exit:** `rg -i "mai"` returns 0 hits (excl. git history); all tests green

### Phase 4 — Validation & Continuity (Week 2–3)
- Behavior harness (6 scenarios) — all green
- M9 evaluation (stub) — rubric ≥ 4.0/5.0
- Multi-session: restart → memory → relationship continuity
- Voice persona: TTS emotion/prosody unchanged
- Your 1-hour conversation — rate "feels like her" ≥ 9/10
- **Exit:** Behavior 100% pass; M9 ≥ 4.0; your sign-off ≥ 9/10

---

## Success Metrics

| Metric | Target |
|--------|--------|
| TM attorney "likely registrable" | YES |
| `rg -i mai` (code/docs) = 0 hits | YES |
| 1,832 tests pass | YES |
| Behavior harness 6/6 green | YES |
| M9 rubric (stub) avg ≥ 4.0 | YES |
| Your "feels like her" rating ≥ 9/10 | YES |
| `.com` + `.ai` registered; 5+ handles claimed | YES |
| Vault recompilation: 0 broken wiki-links | YES |
| TTS emotion/prosody cosine sim ≥ 0.95 | PASS |

---

## Validation Plan

1. **Automated:** `pytest tests/ -x -q`
2. **Behavior:** `pytest tests/behavior/ -v`
3. **M9 Stub:** `python -m evaluation.runner --mode stub --scenario all`
4. **Manual:** 1-hour conversation (memory, emotion, relationship)
5. **Voice:** TTS sample comparison (pre/post, same prompts)
6. **Vault:** `scripts/check_vault_writers.py` + spot-check

---

## Architecture Notes

- **Single Source of Truth:** `config/character.py` → `CHARACTER_NAME = "[NewName]"`
- `IdentityCore.config.name` reads from config — no hardcoded names in classes
- Classes already name-agnostic: `IdentityCore`, `PersonalityState`, `RelationshipEngine`, `EmotionExperience`
- Vault recompiles from structured state via `ObsidianWriter.write_all()`
- Migration is **config-driven**, not structural

---

## Specialist Handoff

| Specialist | Task | Deliverable |
|------------|------|-------------|
| **Python Master Engineer** | Migration script + audit | `scripts/migrate_character_name.py`; zero `rg -i mai` hits |
| **Character / Narrative Designer** | Score top 10 vs Volumes I–IV | Scored matrix with rationale |
| **AI Product Manager** | TM screening coordination; selection | Clearance memo; brand asset checklist |

---

## Implementation Prompt (for Python Master Engineer)

> **MIGRATE CHARACTER NAME: Mai → [SELECTED_NAME]**
> 
> **Single Source:** `config/character.py` → `CHARACTER_NAME = "[SELECTED_NAME]"`
> 
> **Steps:**
> 1. Write `scripts/migrate_character_name.py` — context-aware regex (skip comments, user-facing strings)
> 2. Target: `core/identity/`, `prompt/`, `voice/`, `config/`, `tests/`, `docs/`, `AGENTS.md`, `run*.py`
> 3. Vault: recompile via `ObsidianWriter.write_all()`
> 4. `pytest tests/ -x` — zero failures
> 5. `pytest tests/behavior/ -v` — 6/6 green
> 6. Manual audit: `rg -i "mai" --type=py --type=md --type=yml --type=toml` → only git history

---

## Related Documentation

- [[01-Architecture/03-Core Brain Kernel & State]] — IdentityCore config
- [[02-Subsystems/Identity & Canon]] — canon volumes reference
- [[00-Overview/Project Charter]] — project identity
- [[05-Reference/Complete Folder Structure]] — migration surface area

---

*This PRD will be finalized upon trademark clearance and final name selection.*