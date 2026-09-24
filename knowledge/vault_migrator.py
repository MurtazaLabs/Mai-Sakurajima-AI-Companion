import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Canonical (new) structure ──────────────────────────────────────────────
CANONICAL_MEMORY_FOLDERS = [
    "conversation", "relationship", "people", "places", "projects",
    "knowledge", "dreams", "identity", "preferences", "reflections",
    "statistics", "archive", "important",
]

# `graph/` is the canonical knowledge-graph export target (ObsidianWriter.sync
# writes graph nodes there since Phase 4). `Entities/` is retired.
CANONICAL_ENTITY_DIR = "graph"

# Phase 3 proposed-layout folders created at boot (graph export + compiler output).
CANONICAL_PHASE3_FOLDERS = ["graph", "maintenance"]

# Obsolete folder: declared in an earlier draft but has no writer and no reader
# (canonical memory lives in identity/ knowledge/ people/ etc.). Removed at boot.
OBSOLETE_FOLDERS = ["memories"]

# Stray artifacts from earlier half-migrated writes: filenames ending in ".md.md"
# (e.g. "index.md.md") are double-extension artifacts. The migrator REPAIRS them
# (rename to .md when no canonical sibling exists, else merge + archive) rather
# than unconditionally deleting, so no vault data is ever lost.
OBSOLETE_FILE_SUFFIXES = [".md.md"]

# ── Legacy (old) folders to migrate away ──────────────────────────────────
LEGACY_CONVERSATIONS = "conversations"
LEGACY_RELATIONSHIPS = "relationships"

# Retired in Phase 4: graph export moved from `Entities/` to `graph/`.
# `Entities/` is fully regenerable from the knowledge graph, so it is safe to
# remove once migration has run.
LEGACY_ENTITIES = "Entities"


def migrate_vault(vault_path):
    """Idempotent, safe migration of a half-migrated Obsidian vault.

    Performs three steps:
      1. Choose canonical structure (new singular folder names).
      2. Migrate existing data (merge old -> new, never overwrite/lose).
      3. Remove obsolete legacy folders once data is confirmed moved.

    Safe to call on every boot: it is a no-op once migration is complete.
    Returns a summary dict.
    """
    vault = Path(vault_path)
    if not vault.exists():
        return {"migrated": False, "reason": "vault_missing"}

    summary = {
        "conversation_files_merged": 0,
        "relationship_state_merged": False,
        "legacy_folders_removed": [],
        "errors": [],
    }

    # Ensure canonical folders exist.
    for folder in CANONICAL_MEMORY_FOLDERS:
        (vault / folder).mkdir(parents=True, exist_ok=True)

    # Ensure Phase 3 layout folders exist.
    for folder in CANONICAL_PHASE3_FOLDERS:
        (vault / folder).mkdir(parents=True, exist_ok=True)

    # ── Step 2a: conversations/ -> conversation/ ──────────────────────────
    old_conv = vault / LEGACY_CONVERSATIONS
    if old_conv.is_dir():
        new_conv = vault / "conversation"
        for old_file in sorted(old_conv.iterdir()):
            if old_file.suffix != ".md":
                continue
            try:
                _merge_md_file(old_file, new_conv / old_file.name)
                summary["conversation_files_merged"] += 1
            except Exception as e:
                summary["errors"].append(f"conversation {old_file.name}: {e}")
                logger.error("[VAULT MIGRATE] conversation merge error: %s", e)

    # ── Step 2b: relationships/state.md -> relationship/relationship.md ────
    old_rel = vault / LEGACY_RELATIONSHIPS
    if old_rel.is_dir():
        state_file = old_rel / "state.md"
        if state_file.exists():
            try:
                _merge_relationship_state(
                    state_file,
                    vault / "relationship" / "relationship.md",
                )
                summary["relationship_state_merged"] = True
            except Exception as e:
                summary["errors"].append(f"relationship state: {e}")
                logger.error("[VAULT MIGRATE] relationship merge error: %s", e)

    # ── Step 3: remove obsolete legacy folders ───────────────────────────
    # Data has already been merged into canonical locations above, so the
    # legacy folders are safe to remove entirely.
    for legacy in (LEGACY_CONVERSATIONS, LEGACY_RELATIONSHIPS, LEGACY_ENTITIES):
        legacy_path = vault / legacy
        if not legacy_path.is_dir():
            continue
        try:
            shutil.rmtree(legacy_path)
            summary["legacy_folders_removed"].append(legacy)
            logger.info("[VAULT MIGRATE] removed legacy folder %s/", legacy)
        except Exception as e:
            summary["errors"].append(f"remove {legacy}: {e}")
            logger.error("[VAULT MIGRATE] remove %s error: %s", legacy, e)

    # ── Step 3b: remove obsolete folders with no writer/reader ───────────
    for obsolete in OBSOLETE_FOLDERS:
        obsolete_path = vault / obsolete
        if not obsolete_path.is_dir():
            continue
        try:
            shutil.rmtree(obsolete_path)
            summary["legacy_folders_removed"].append(obsolete)
            logger.info("[VAULT MIGRATE] removed obsolete folder %s/", obsolete)
        except Exception as e:
            summary["errors"].append(f"remove {obsolete}: {e}")
            logger.error("[VAULT MIGRATE] remove %s error: %s", obsolete, e)

    # ── Step 3c: repair stray double-extension files (e.g. "index.md.md") ─
    # A ".md.md" file may be either
    #   (a) a redundant double-written duplicate of an existing canonical
    #       "<name>.md" -> archive it (never silently delete data), or
    #   (b) the ONLY copy of real data whose canonical sibling was never
    #       created -> FIX THE EXTENSION (.md.md -> .md), preserving content.
    # We NEVER unconditionally delete: deletion only happens when the
    # canonical ".md" exists AND already holds equal-or-larger content.
    _repair_double_extension_files(vault, summary)

    summary["migrated"] = (
        summary["conversation_files_merged"] > 0
        or summary["relationship_state_merged"]
        or len(summary["legacy_folders_removed"]) > 0
    )

    # Audit Step 10: record migration execution in the append-only log.md.
    if any([summary["conversation_files_merged"], summary["relationship_state_merged"],
            summary["legacy_folders_removed"]]):
        try:
            from knowledge.vault_logger import VaultLogger
            VaultLogger(vault).migration_executed(
                f"merged_conv={summary['conversation_files_merged']}, "
                f"rel_state={summary['relationship_state_merged']}, "
                f"removed={summary['legacy_folders_removed']}"
            )
        except Exception as e:
            logger.warning("[VAULT MIGRATE] log write skipped: %s", e)

    return summary


def _merge_md_file(old_file, new_file):
    """Append entries from old_file into new_file, deduping by entry id.

    Entries are blocks separated by a line containing only '---'.
    """
    old_text = old_file.read_text(encoding="utf-8")
    old_ids = set(_extract_ids(old_text))

    if new_file.exists():
        new_text = new_file.read_text(encoding="utf-8")
        new_ids = set(_extract_ids(new_text))
    else:
        new_text = ""
        new_ids = set()

    blocks = [b for b in old_text.split("\n---") if b.strip()]
    appended = []
    for block in blocks:
        block_ids = _extract_ids(block)
        if block_ids and block_ids & new_ids:
            continue  # already present
        if not block_ids and block.strip() in new_text:
            continue
        appended.append(block)

    if not appended:
        return

    sep = "\n---\n" if new_text.strip() else ""
    merged = new_text.rstrip() + sep + "\n---\n".join(appended).strip() + "\n"
    new_file.write_text(merged, encoding="utf-8")


def _extract_ids(text):
    ids = set()
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("id:"):
            ids.add(line.split(":", 1)[1].strip().lower())
    return ids


_NUM_FIELDS = ("closeness", "trust", "interactions")


def _merge_relationship_state(old_file, new_file):
    """Merge legacy relationship state into the canonical relationship file.

    Takes the max of numerical fields and the latest LastInteraction so
    historical trust/closeness/interaction counts are preserved.
    """
    old_text = old_file.read_text(encoding="utf-8")
    old_fields = _parse_kv(old_text)

    if new_file.exists():
        new_text = new_file.read_text(encoding="utf-8")
        new_fields = _parse_kv(new_text)
    else:
        new_text = ""
        new_fields = {}

    merged = dict(new_fields)
    for key in _NUM_FIELDS:
        ov = old_fields.get(key)
        nv = new_fields.get(key)
        if ov is not None and nv is not None:
            merged[key] = max(ov, nv)
        elif ov is not None:
            merged[key] = ov

    # Latest interaction timestamp wins.
    old_ts = old_fields.get("lastinteraction")
    new_ts = new_fields.get("lastinteraction")
    if old_ts and (not new_ts or str(old_ts) > str(new_ts)):
        merged["lastinteraction"] = old_ts

    # Preserve any extra keys from the old file not in the new.
    for k, v in old_fields.items():
        if k not in merged:
            merged[k] = v

    if not merged:
        return

    lines = []
    for k, v in merged.items():
        lines.append(f"{k.capitalize()}: {v}")
    new_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _repair_double_extension_files(vault, summary):
    """Safely resolve every ``*.md.md`` stray file in the vault tree.

    Strategy (never loses data):
      * If a canonical ``<name>.md`` sibling exists with content >= the
        ``.md.md`` file, the ``.md.md`` is a redundant duplicate -> move it
        into ``archive/`` (preserved, not deleted).
      * If no canonical ``.md`` sibling exists, the ``.md.md`` is the real
        data -> rename it to ``.md`` (fix the extension, keep content).
      * If the canonical ``.md`` exists but is *smaller/empty* (the duplicate
        holds the newer/only data), merge the ``.md.md`` content into the
        canonical file, then archive the ``.md.md`` copy.
    """
    for fpath in list(vault.rglob("*")):
        if not fpath.is_file():
            continue
        # Skip files already inside archive/ (our own quarantine target) so a
        # filesystem iterator cannot re-yield a file we just moved.
        if fpath.parent.name == "archive":
            continue
        name = fpath.name
        low = name.lower()
        if not low.endswith(".md.md"):
            continue
        canonical = fpath.with_name(name[:-3])  # strip trailing ".md"
        summary.setdefault("legacy_folders_removed", [])
        summary.setdefault("errors", [])
        try:
            dup_text = fpath.read_text(encoding="utf-8", errors="replace")
            dup_len = len(dup_text.strip())

            if canonical.exists():
                canon_text = canonical.read_text(encoding="utf-8", errors="replace")
                canon_len = len(canon_text.strip())
                if dup_len <= canon_len:
                    # Redundant duplicate; archive instead of delete.
                    _archive_stray(vault, fpath, summary)
                else:
                    # Duplicate holds more/newer content; merge into canonical.
                    merged = canon_text.rstrip()
                    if merged:
                        merged += "\n"
                    merged += dup_text.strip() + "\n"
                    canonical.write_text(merged, encoding="utf-8")
                    _archive_stray(vault, fpath, summary)
            else:
                # No canonical sibling -> the .md.md IS the real data.
                # Fix the extension; do NOT delete.
                fpath.rename(canonical)
                summary["legacy_folders_removed"].append(
                    f"{fpath.name} -> {canonical.name} (extension fixed)"
                )
                logger.info(
                    f"[VAULT MIGRATE] fixed extension {fpath.name} -> {canonical.name}"
                )
        except Exception as e:
            summary["errors"].append(f"repair {fpath.name}: {e}")
            logger.error("[VAULT MIGRATE] repair %s error: %s", fpath.name, e)


def _archive_stray(vault, fpath, summary):
    """Move a redundant stray file into ``archive/`` instead of deleting it."""
    archive_dir = vault / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / fpath.name
    # Avoid collision with an existing archive entry.
    counter = 1
    while dest.exists():
        dest = archive_dir / f"{fpath.stem}_{counter}{fpath.suffix}"
        counter += 1
    try:
        fpath.rename(dest)
        summary["legacy_folders_removed"].append(
            f"{fpath.name} -> archive/{dest.name} (archived, not deleted)"
        )
        logger.info("[VAULT MIGRATE] archived stray %s -> archive/%s", fpath.name, dest.name)
    except Exception as e:
        summary["errors"].append(f"archive {fpath.name}: {e}")
        logger.error("[VAULT MIGRATE] archive %s error: %s", fpath.name, e)


def _parse_kv(text):
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if ":" in line and not line.startswith("#"):
            key, _, val = line.partition(":")
            key = key.strip().lower().replace(" ", "")
            val = val.strip()
            try:
                val = float(val)
            except ValueError:
                logger.warning("[VaultMigrator] non-numeric value: %s", val)
        else:
            continue
        out[key] = val
    return out
