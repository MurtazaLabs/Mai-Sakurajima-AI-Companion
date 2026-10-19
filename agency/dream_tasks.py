"""Dream task implementations for the DreamEngine.

Each task is a pure function ``task(engine, state, report) -> metric`` so the
engine can dispatch them by name without the class ballooning in size. Tasks
read/write ``state`` (MemoryState) and accumulate counters into ``report``
(DreamReport). They may use ``engine.knowledge_graph``, ``engine.llm``, and
``engine.vault_root``.
"""
import json
import logging
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from agency.dream_report import (
    ARCHIVE_DAYS,
    ARCHIVE_IMPORTANCE,
    INFERRED_CONFIDENCE,
    LINK_CO_OCCUR_THRESHOLD,
)

logger = logging.getLogger(__name__)


def _make_knowledge_entry(topic, fact, timestamp=None):
    """Create a lightweight KnowledgeEntry-like object (mirrors engine usage)."""
    return type("KnowledgeEntry", (), {
        "topic": topic,
        "fact": fact,
        "timestamp": timestamp or time.strftime("%Y-%m-%d"),
    })()


def find_orphans(engine, state, report):
    kg = engine.knowledge_graph
    if not kg:
        return 0
    orphan_count = 0
    for entity_list, folder in [
        (state.people, "person"),
        (state.places, "place"),
        (state.projects, "project"),
    ]:
        for ent in entity_list:
            name = ent.get("name", "").strip().lower()
            if not name:
                continue
            relations = kg.get_relations_for(name)
            if not relations:
                orphan_count += 1
                tentative = _find_co_occurring(state, name, folder)
                for target, rel_type in tentative[:3]:
                    if kg.get_entity(target):
                        logger.info("[DreamEngine] orphan link: %s --%s--> %s", name, rel_type, target)
    return orphan_count


def _find_co_occurring(state, name, folder):
    candidates = []
    all_entities: list[tuple[str, str]] = []
    if folder != "person":
        all_entities.extend(
            (e["name"].strip().lower(), "person")
            for e in state.people if e.get("name")
        )
    if folder != "place":
        all_entities.extend(
            (e["name"].strip().lower(), "place")
            for e in state.places if e.get("name")
        )
    if folder != "project":
        all_entities.extend(
            (e["name"].strip().lower(), "project")
            for e in state.projects if e.get("name")
        )
    for other_name, other_type in all_entities:
        if other_name != name:
            candidates.append((other_name, f"related_to_{other_type}"))
    return candidates


def merge_duplicates(engine, state, report):
    merged = 0
    for folder in ("people", "places", "projects"):
        entities = getattr(state, folder, [])
        seen: dict[str, dict[str, Any]] = {}
        to_remove = []
        for ent in entities:
            name = ent.get("name", "").strip().lower()
            if not name:
                continue
            if name in seen:
                existing = seen[name]
                if ent.get("confidence", 0) > existing.get("confidence", 0):
                    seen[name] = ent
                    to_remove.append(existing)
                else:
                    to_remove.append(ent)
                merged += 1
            else:
                seen[name] = ent
        for d in to_remove:
            try:
                entities.remove(d)
            except ValueError as e:
                logger.debug("remove from merge: %s", e)
        setattr(state, folder, entities)
    return merged


def merge_knowledge(engine, state, report):
    before = len(state.knowledge)
    state.merge_knowledge(state.knowledge)
    return max(0, before - len(state.knowledge))


def _build_entity_pairs(state):
    pairs: defaultdict[tuple[str, str], int] = defaultdict(int)
    for folder in ("people", "places", "projects"):
        for ent in getattr(state, folder, []):
            name = ent.get("name", "").strip().lower()
            if not name:
                continue
            for folder2 in ("people", "places", "projects"):
                if folder2 == folder:
                    continue
                for ent2 in getattr(state, folder2, []):
                    name2 = ent2.get("name", "").strip().lower()
                    if name2 and name2 != name:
                        pairs[tuple(sorted([name, name2]))] += 1
    return pairs


def link_notes(engine, state, report):
    kg = engine.knowledge_graph
    if not kg:
        return 0
    entity_pairs = _build_entity_pairs(state)
    links = 0
    for (a, b), count in entity_pairs.items():
        if count >= LINK_CO_OCCUR_THRESHOLD:
            existing = kg.get_relations_for(a) if kg else []
            already = any(r.source == a and r.target == b for r in existing) if existing else False
            if not already:
                kg.add_relation(a, "co_occurs_with", b, weight=min(1.0, count / 20))
                links += 1
    return links


def recalculate_importance(engine, state, report):
    today = datetime.now()
    updated = 0
    for folder in ("people", "places", "projects"):
        for ent in getattr(state, folder, []):
            last_seen = ent.get("last_seen", "")
            try:
                days_since = (today - datetime.strptime(last_seen, "%Y-%m-%d")).days
            except Exception as e:
                logger.debug("[DreamTasks] recalculate_imp date parse: %s | %s", last_seen, e)
                days_since = 0
            base = ent.get("confidence", 0.5)
            decay = base * (0.9 ** days_since)
            ent["importance"] = max(0.05, round(decay, 3))
            ent["importance_source"] = "fresh" if days_since <= 7 else "decayed"
            updated += 1
    return updated


def build_relationships(engine, state, report):
    kg = engine.knowledge_graph
    if not kg:
        return 0
    entity_pairs = _build_entity_pairs(state)
    built = 0
    for (a, b), count in entity_pairs.items():
        if count >= 2:
            existing = kg.get_relations_for(a) if kg else []
            already = any(
                (r.source == a and r.target == b) or (r.source == b and r.target == a)
                for r in existing
            ) if existing else False
            if not already:
                kg.add_relation(a, "co_occurs_with", b, weight=min(1.0, count / 10))
                built += 1
    return built


def compress_conversations(engine, state, report):
    if not engine.vault_root:
        return 0
    conv_dir = engine.vault_root / "conversation"
    if not conv_dir.exists():
        return 0
    compressed = 0
    for fpath in sorted(conv_dir.glob("*.md"))[-10:]:
        content = fpath.read_text(encoding="utf-8", errors="replace")
        if any("summary:" in line for line in content.split("\n")[:10]):
            continue
        summary = _extract_keywords(content)
        if not summary:
            continue
        new_content = _inject_summary(content, summary)
        fpath.write_text(new_content, encoding="utf-8")
        compressed += 1
    return compressed


def _extract_keywords(text, top_n=8):
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    stopwords = {"this", "that", "with", "from", "have", "been", "what",
                 "when", "where", "which", "there", "their", "about",
                 "would", "could", "should", "than", "then", "just", "like",
                 "more", "some", "them", "they", "your", "said", "also",
                 "very", "well", "here", "know", "think"}
    freq = Counter(w for w in words if w not in stopwords)
    top = [w for w, _ in freq.most_common(top_n)]
    return ", ".join(top) if top else ""


def _inject_summary(content, summary):
    lines = content.splitlines()
    insert_at = -1
    for i, line in enumerate(lines):
        if line.startswith("---") and i > 0:
            insert_at = i
            break
    if insert_at < 0:
        return content
    lines.insert(insert_at, f'summary: "{summary}"')
    return "\n".join(lines)


def generate_reflections(engine, state, report):
    if not engine.llm:
        return 0
    identity_str = "; ".join(f.fact for f in state.identity[:5])
    likes_str = ", ".join(state.likes[:8])
    dislikes_str = ", ".join(state.dislikes[:8])
    dreams_str = "; ".join(state.dreams[:5])
    knowledge_str = "; ".join(f"{k.topic}: {k.fact}" for k in state.knowledge[:8])
    inputs = [s for s in [identity_str, likes_str, dislikes_str, dreams_str, knowledge_str] if s]
    if not inputs:
        return 0
    prompt = (
        "Based on the user's current state, produce 1-2 high-level observations.\n"
        + "\n".join(inputs) +
        "\n\nReturn a JSON object: "
        '{"reflections": [{"observation": "...", "confidence": 0.95, '
        '"category": "interest_change|habit|personality_trait|growth"}]}'
    )
    try:
        raw = engine.llm.generate(
            system="You generate high-level user observations. Return ONLY valid JSON.",
            user=prompt,
        )
        if not raw:
            return 0
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= start:
            return 0
        data = json.loads(raw[start:end])
        reflections = data.get("reflections", [])
        count = 0
        today = time.strftime("%Y-%m-%d")
        for item in reflections[:2]:
            obs = item.get("observation", "").strip()
            conf = float(item.get("confidence", 0))
            if obs and conf >= 0.8:
                state.knowledge.append(
                    _make_knowledge_entry(f"reflection_{today}_{count}",
                                          f"[reflection] {obs} (confidence: {conf:.2f})", today)
                )
                count += 1
        return count
    except Exception as e:
        logger.debug("[DreamEngine] reflections: %s", e)
        return 0


def discover_knowledge(engine, state, report):
    if not engine.llm:
        return 0
    discovered = 0
    inputs = []
    if state.likes:
        inputs.append(f"Likes: {', '.join(state.likes)}")
    if state.dislikes:
        inputs.append(f"Dislikes: {', '.join(state.dislikes)}")
    if state.dreams:
        inputs.append(f"Dreams: {', '.join(state.dreams)}")
    if state.identity:
        inputs.append(f"Identity: {'; '.join(f.fact for f in state.identity)}")
    if not inputs:
        return 0
    prompt = (
        "Based on these known facts about the user, infer implicit preferences or traits.\n"
        + "\n".join(inputs) +
        "\n\nReturn up to 3 inferred traits as a JSON list: "
        '[{"trait": "...", "confidence": 0.85}, ...]'
    )
    try:
        raw = engine.llm.generate(
            system="You infer implicit user traits from explicit data. Return ONLY valid JSON.",
            user=prompt,
        )
        if not raw:
            return 0
        start_idx = raw.find("[")
        end_idx = raw.rfind("]") + 1
        if start_idx >= 0 and end_idx > start_idx:
            inferences = json.loads(raw[start_idx:end_idx])
            for item in inferences:
                if isinstance(item, dict):
                    trait = item.get("trait", "").strip()
                    conf = float(item.get("confidence", 0))
                    if trait and conf >= INFERRED_CONFIDENCE:
                        state.knowledge.append(
                            _make_knowledge_entry(trait[:40], f"[inferred] {trait}",
                                                  time.strftime("%Y-%m-%d"))
                        )
                        discovered += 1
    except Exception as e:
        logger.debug("[DreamEngine] knowledge discovery: %s", e)
    return discovered


def emotional_reflection(engine, state, report):
    if not engine.vault_root:
        return 0
    conv_dir = engine.vault_root / "conversation"
    if not conv_dir.exists():
        return 0
    emotions = []
    for fpath in sorted(conv_dir.glob("*.md"))[-20:]:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"emotion:\s*(\w+)", text)
        if m:
            emotions.append((fpath.stem, m.group(1)))
    if len(emotions) < 3:
        return 0
    stress_keywords = {"anxious", "sad", "angry", "frustrated", "stressed", "tired"}
    recent_moods = [m for _, m in emotions[-5:]]
    stress_count = sum(1 for m in recent_moods if m.lower() in stress_keywords)
    if stress_count >= 3:
        period_start = emotions[-5][0]
        period_end = emotions[-1][0]
        state.knowledge.append(
            _make_knowledge_entry(
                f"emotional_reflection_{period_end}",
                f"[emotion] User appears stressed ({stress_count}/5 recent conversations). "
                f"Period: {period_start} to {period_end}.",
                period_end,
            )
        )
        return 1
    happy_keywords = {"happy", "excited", "joyful", "grateful", "content", "loving"}
    happy_count = sum(1 for m in recent_moods if m.lower() in happy_keywords)
    if happy_count >= 3:
        period_start = emotions[-5][0]
        period_end = emotions[-1][0]
        state.knowledge.append(
            _make_knowledge_entry(
                f"emotional_reflection_{period_end}",
                f"[emotion] User appears positive ({happy_count}/5 recent conversations). "
                f"Period: {period_start} to {period_end}.",
                period_end,
            )
        )
        return 1
    return 0


def archive_stale(engine, state, report):
    today = datetime.now()
    archived = 0
    for folder in ("people", "places", "projects"):
        entities = getattr(state, folder, [])
        keep = []
        for ent in entities:
            last_seen = ent.get("last_seen", "")
            importance = ent.get("importance", ent.get("confidence", 0.5))
            try:
                days_since = (today - datetime.strptime(last_seen, "%Y-%m-%d")).days
            except Exception as e:
                logger.debug("[DreamTasks] archive date parse: %s | %s", last_seen, e)
                days_since = 0
            if days_since > ARCHIVE_DAYS and importance < ARCHIVE_IMPORTANCE:
                archived += 1
            else:
                keep.append(ent)
        setattr(state, folder, keep)
    return archived


def optimize_graph(engine, state, report):
    kg = engine.knowledge_graph
    if not kg:
        return
    try:
        all_relations = kg.all_relations()
        seen = set()
        dupes = 0
        for rel in all_relations:
            key = (rel.source, rel.relation, rel.target)
            if key in seen:
                kg.remove_relation(rel.source, rel.relation, rel.target)
                dupes += 1
            else:
                seen.add(key)
        weak = 0
        for rel in kg.all_relations():
            if rel.weight < 0.1:
                kg.remove_relation(rel.source, rel.relation, rel.target)
                weak += 1
        logger.info("[DreamEngine] graph optimization: %s dupes removed, %s weak edges removed", dupes, weak)
    except Exception as e:
        logger.debug("[DreamEngine] graph optimization: %s", e)


def recalculate_importance_full(engine, state, report):
    today = datetime.now()
    updated = recalculate_importance(engine, state, report)
    if engine.knowledge_graph:
        for ent in engine.knowledge_graph.all_entities():
            created = getattr(ent, "created_at", 0)
            try:
                days_since = (today - datetime.fromtimestamp(created)).days
            except Exception as e:
                logger.debug("[DreamTasks] full_imp timestamp parse: %s | %s", created, e)
                days_since = 0
            if not hasattr(ent, "metadata") or ent.metadata is None:
                ent.metadata = {}
            base = ent.metadata.get("confidence", 0.5)
            decay = base * (0.9 ** days_since)
            ent.metadata["importance"] = max(0.05, round(decay, 3))
            ent.metadata["importance_source"] = "fresh" if days_since <= 7 else "decayed"
            updated += 1
    return updated


def weekly_digest(engine, state, report):
    if not engine.llm or not engine.vault_root:
        return False
    conv_dir = engine.vault_root / "conversation"
    if not conv_dir.exists():
        return False
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    conversations = []
    for fpath in sorted(conv_dir.glob("*.md")):
        if fpath.stem >= week_ago:
            text = fpath.read_text(encoding="utf-8", errors="replace")
            conversations.append(f"--- {fpath.stem} ---\n{text[:3000]}")
    if not conversations:
        return False
    identity_str = "; ".join(f.fact for f in state.identity[:5]) or "none"
    likes_str = ", ".join(state.likes[:8]) or "none"
    dislikes_str = ", ".join(state.dislikes[:8]) or "none"
    knowledge_str = "; ".join(f"{k.topic}: {k.fact}" for k in state.knowledge[:8]) or "none"
    prompt = (
        "Summarize this week's conversations into a digest.\n\n"
        f"Conversation log (last 7 days):\n{chr(10).join(conversations[-5:])}\n\n"
        f"Current state:\nIdentity: {identity_str}\n"
        f"Preferences: {likes_str} / {dislikes_str}\n"
        f"Knowledge: {knowledge_str}\n\n"
        "Produce a summary covering:\n"
        "1. Key topics discussed\n"
        "2. Any decisions or plans made\n"
        "3. User's apparent emotional state this week\n"
        "4. Any new information learned about the user\n\n"
        'Return a JSON object: {"digest": "...", "key_topics": [...], '
        '"mood": "...", "new_information": [...]}'
    )
    try:
        raw = engine.llm.generate(
            system="You generate weekly digests. Return ONLY valid JSON.",
            user=prompt,
        )
        if not raw:
            return False
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= start:
            return False
        data = json.loads(raw[start:end])
        digest_text = data.get("digest", "")
        if digest_text:
            state.knowledge.append(
                _make_knowledge_entry(
                    f"weekly_digest_{datetime.now().strftime('%Y-%m-%d')}",
                    f"[digest] {digest_text[:500]}",
                    datetime.now().strftime("%Y-%m-%d"),
                )
            )
            return True
        return False
    except Exception as e:
        logger.debug("[DreamEngine] weekly digest: %s", e)
        return False


def detect_contradictions(engine, state, report):
    """Temporal contradiction detection on MemoryState knowledge.

    Same topic with differing facts and timestamps -> keep both as temporal
    knowledge (do NOT overwrite) and flag the contradiction as an insight.
    """
    by_topic: dict[str, list] = {}
    for e in state.knowledge:
        by_topic.setdefault(e.topic.lower(), []).append(e)
    found = 0
    today = time.strftime("%Y-%m-%d")
    for topic, entries in by_topic.items():
        facts = {e.fact.strip().lower() for e in entries if e.fact}
        if len(facts) > 1:
            found += 1
            state.knowledge.append(
                _make_knowledge_entry(
                    f"contradiction_{topic[:30]}",
                    f"[contradiction] Topic '{topic}' has differing facts over time "
                    f"(temporal knowledge): {len(entries)} versions kept.",
                    today,
                )
            )
    return found


def split_giant_pages(engine, state, report):
    """Detect oversized knowledge pages and re-key them by sub-topic.

    The ``knowledge`` list is already topic-keyed (merge_knowledge dedupes by
    topic), so a "giant page" is a topic with an over-long fact string. Such
    facts are split into sub-entries so the compiled ``knowledge.md`` stays
    readable. Returns the number of pages split.
    """
    GIANT_FACT_CHARS = 280
    split = 0
    new_entries = []
    kept = []
    for e in state.knowledge:
        fact = (e.fact or "").strip()
        if len(fact) > GIANT_FACT_CHARS:
            parts = [p.strip() for p in fact.split(". ") if p.strip()]
            for i, part in enumerate(parts):
                sub = part if part.endswith(".") else part + "."
                new_entries.append(
                    _make_knowledge_entry(
                        f"{e.topic}_{i+1}", sub,
                        getattr(e, "timestamp", "") or time.strftime("%Y-%m-%d"),
                    )
                )
            split += 1
        else:
            kept.append(e)
    if split:
        state.knowledge = kept + new_entries
    return split


def discover_patterns(engine, state, report):
    """Discover cross-topic patterns and emit insight entries.

    Counts theme co-occurrence across identity / likes / dreams / knowledge
    topics and records a high-level insight when a theme recurs.
    """
    if not engine.llm:
        return 0
    themes = []
    themes.extend(state.likes)
    themes.extend(state.dislikes)
    themes.extend([k.topic for k in state.knowledge])
    themes.extend(state.dreams)
    counts = Counter(t.lower() for t in themes if t)
    recurring = {t: c for t, c in counts.items() if c >= 3}
    if not recurring:
        return 0
    prompt = (
        "The user's data shows these recurring themes:\n"
        + "\n".join(f"- {t} (x{c})" for t, c in recurring.items()) +
        "\n\nReturn up to 3 high-level insights as a JSON list: "
        '[{"insight": "...", "confidence": 0.8}, ...]'
    )
    try:
        raw = engine.llm.generate(
            system="You synthesize recurring user themes into insights. Return ONLY valid JSON.",
            user=prompt,
        )
        if not raw:
            return 0
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start < 0 or end <= start:
            return 0
        insights = json.loads(raw[start:end])
        today = time.strftime("%Y-%m-%d")
        added = 0
        for item in insights[:3]:
            if isinstance(item, dict):
                ins = item.get("insight", "").strip()
                conf = float(item.get("confidence", 0))
                if ins and conf >= 0.7:
                    state.knowledge.append(
                        _make_knowledge_entry(f"insight_{today}_{added}", f"[insight] {ins}", today)
                    )
                    added += 1
        return added
    except Exception as e:
        logger.debug("[DreamEngine] pattern discovery: %s", e)
        return 0


def experience_reflection(engine, state, report):
    """Dreaming revisits significant experiences (M6).

    Reads engine.experience_store (ExperienceStore), picks significant
    unreflected experiences, and lazily fills meaning/lessons/growth —
    via LLM when available (cheap reflection), otherwise deterministic
    keyword-based meaning. Marks entries reflected; appends a knowledge
    entry per revisited experience. Returns count revisited.
    """
    store = getattr(engine, "experience_store", None)
    if not store:
        return 0
    candidates = store.unreflected(threshold=0.6)
    if not candidates:
        return 0
    revisited = 0
    today = time.strftime("%Y-%m-%d")
    for exp in candidates[:5]:
        meaning, lessons, growth = _reflect_experience(engine, exp)
        store.mark_reflected(
            exp.id, meaning=meaning, lessons=lessons, growth=growth,
        )
        summary = exp.event[:120]
        if growth:
            summary += f" — {growth[:160]}"
        state.knowledge.append(
            _make_knowledge_entry(
                f"experience_{exp.id[:8]}",
                f"[experience] {summary}",
                today,
            )
        )
        revisited += 1
    logger.info("[DreamEngine] experience_reflection: %d revisited", revisited)
    return revisited


def _reflect_experience(engine, exp):
    """Cheap reflection: LLM when present, deterministic fallback otherwise."""
    if engine.llm:
        try:
            raw = engine.llm.generate(
                system="You reflect on one personal experience. Return ONLY "
                       'valid JSON: {"meaning": "...", "lesson": "...", "growth": "..."}',
                user=exp.event,
            )
            if raw:
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    data = json.loads(raw[start:end])
                    meaning = str(data.get("meaning", "")).strip()
                    lesson = str(data.get("lesson", "")).strip()
                    growth = str(data.get("growth", "")).strip()
                    lessons = [lesson] if lesson else []
                    return meaning, lessons, growth
        except Exception as e:
            logger.debug("[DreamEngine] experience reflection LLM: %s", e)

    emotion = (exp.emotion or {}).get("type", "neutral")
    meaning = f"Significant event marked by '{emotion}' emotion."
    lessons = []
    growth = ""
    return meaning, lessons, growth


# ── Task name → implementation dispatch ──────────────────────────────────
DREAM_TASKS = {
    "orphans": find_orphans,
    "merge_duplicates": merge_duplicates,
    "merge_knowledge": merge_knowledge,
    "link_notes": link_notes,
    "importance": recalculate_importance,
    "relationship_building": build_relationships,
    "conversation_compression": compress_conversations,
    "reflections": generate_reflections,
    "knowledge_discovery": discover_knowledge,
    "emotional_reflection": emotional_reflection,
    "contradictions": detect_contradictions,
    "archive_stale": archive_stale,
    "graph_optimization": optimize_graph,
    "importance_full": recalculate_importance_full,
    "weekly_digest": weekly_digest,
    "split_giant": split_giant_pages,
    "patterns": discover_patterns,
    "experience_reflection": experience_reflection,
}
