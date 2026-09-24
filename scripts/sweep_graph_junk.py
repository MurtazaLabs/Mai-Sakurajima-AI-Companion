"""Sweep junk entities/notes out of the Obsidian vault graph.

One-time hygiene script for the entity pollution left by the rule-based
extractor fallback (unknown-type entities at confidence 0.2-0.3, e.g. ``siad``,
``pormise``, ``messing``, ``ohh``).

The runtime guard in ``GraphManager.process_conversation`` prevents new junk
from entering; this script cleans existing history.

Usage:
    python scripts/sweep_graph_junk.py          # dry run (default)
    python scripts/sweep_graph_junk.py --apply  # actually remove
"""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sweep")
logging.getLogger("knowledge").setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Apply removals (default: dry run)")
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from config.paths import OBSIDIAN_VAULT
    from knowledge.graph import KnowledgeGraph
    from knowledge.graph_manager import GraphManager
    from knowledge.vault_janitor import VaultJanitor

    vault = Path(OBSIDIAN_VAULT)
    graph = KnowledgeGraph()
    graph_manager = GraphManager(graph=graph)
    graph_path = vault / "graph"

    # Rebuild the graph from exported notes if a graph.json exists
    state_file = graph_path / "graph.json"
    if state_file.exists():
        try:
            import json
            raw = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and "entities" in raw:
                graph = KnowledgeGraph.load(state_file)
            elif isinstance(raw, list):
                # BrainGraph export format: [{"name": ..., "type": ...}]
                for item in raw:
                    name = item.get("name") if isinstance(item, dict) else None
                    if name:
                        graph.add_entity(
                            name,
                            entity_type=item.get("type", "unknown"),
                            metadata={"confidence": item.get("confidence", 0.5)},
                        )
            else:
                graph = KnowledgeGraph.load(state_file)
            logger.info("Loaded graph state: %d entities",
                        graph.entity_count())
        except Exception as e:
            logger.warning("Could not load %s (%s) — starting empty", state_file, e)
    else:
        logger.info("No graph.json found — starting with empty graph")

    janitor = VaultJanitor(graph=graph, vault_root=vault)
    result = janitor.sweep(dry_run=not args.apply)

    entities = result["entities"]
    files = result["note_files"]
    logger.info("Entities marked junk: %d (dry_run=%s)", entities["removed"], entities["dry_run"])
    logger.info("Note files marked junk: %d (dry_run=%s)", files["removed"], files["dry_run"])

    if entities["names"]:
        logger.info("Entity samples: %s", ", ".join(entities["names"][:20]))
    if files["files"]:
        logger.info("File samples: %s", ", ".join(files["files"][:20]))

    if not args.apply:
        print("\nDry run — pass --apply to actually remove.")
    else:
        print(f"\nSwept — removed {entities['removed']} entities, "
              f"{files['removed']} orphan note files")


if __name__ == "__main__":
    main()
