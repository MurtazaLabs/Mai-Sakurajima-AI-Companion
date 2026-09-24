# NOTE: P2-16 — consider collapsing BrainGraph/GraphManager/KnowledgeGraph into 2 layers
import logging

logger = logging.getLogger(__name__)


class GraphManager:

    def __init__(self, graph=None, extractor=None, consolidation=None, event_bus=None):
        from knowledge.graph import KnowledgeGraph
        from knowledge.extractor import EntityExtractor
        from knowledge.consolidation import ConsolidationEngine
        self.graph = graph or KnowledgeGraph()
        self.extractor = extractor or EntityExtractor()
        self.consolidation = consolidation or ConsolidationEngine()
        self.event_bus = event_bus

    def process_conversation(self, user_message, ai_response):
        extracted = self.extractor.extract_from_conversation(
            user_message, ai_response
        )
        raw_entities = extracted.get("entities", [])
        raw_relations = extracted.get("relations", [])

        raw_names = [e.get("name", "") for e in raw_entities if isinstance(e, dict)]
        deduped_entities, deduped_relations = self.consolidation.deduplicate(
            self.graph, raw_entities, raw_relations
        )

        added_count = 0
        skipped_low_confidence = 0
        for ent in deduped_entities:
            name = ent.get("name", "").strip()
            etype = ent.get("type", "unknown")
            confidence = ent.get("confidence", 0.5)
            # 🧠 Junk gate: the rule-based fallback extractor tags every unknown
            # lowercase word at confidence 0.2.  Refuse those — they produce
            # meaningless entity notes (siad.md, pormise.md, messing.md, ...).
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = 0.0
            if str(etype).lower() == "unknown" and confidence < 0.25:
                skipped_low_confidence += 1
                continue
            self.graph.add_entity(
                name,
                entity_type=etype,
                metadata={"confidence": confidence, "source": "extractor"},
            )
            added_count += 1

        relation_added = 0
        for rel in deduped_relations:
            src = rel.get("source", "").strip()
            rel_type = rel.get("relation", "related_to")
            tgt = rel.get("target", "").strip()
            confidence = rel.get("confidence", 0.5)
            if src and tgt:
                self.graph.add_relation(
                    src, rel_type, tgt,
                    weight=confidence,
                    metadata={"source": "extractor"},
                )
                relation_added += 1

        duplicates_skipped = len(raw_names) - added_count

        summary = {
            "entities_added": added_count,
            "relations_added": relation_added,
            "duplicates_skipped": max(0, duplicates_skipped),
            "junk_skipped": skipped_low_confidence,
        }

        if self.event_bus:
            try:
                from core.event_specs import GRAPH_UPDATED, STATE_KNOWLEDGE_UPDATED
                from core.mai_message import publish_event
                publish_event(self.event_bus, GRAPH_UPDATED, summary, source="knowledge")
                publish_event(self.event_bus, STATE_KNOWLEDGE_UPDATED, {
                    "entities_added": added_count,
                    "relations_added": relation_added,
                }, source="knowledge")
            except Exception as e:
                logger.warning("[GraphManager] Event publish failed: %s", e)

        return summary

    def all_entities(self):
        return self.graph.all_entities()

    # NOTE: GraphManager is a processing pipeline (entity extraction + consolidation),
    # not a graph-access wrapper.  Callers use brain_graph or knowledge_graph directly
    # for read/write access to graph data.
