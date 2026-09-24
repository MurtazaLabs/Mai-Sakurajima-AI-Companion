import os
import glob as glob_mod
import time
import threading
import logging

logger = logging.getLogger(__name__)


class Indexer:

    def __init__(self, vector_store, chunker, document_store=None, event_bus=None):
        self.vector_store = vector_store
        self.chunker = chunker
        self.document_store = document_store
        self.event_bus = event_bus
        self._lock = threading.RLock()
        self._indexed_count = 0

    def index_text(self, text, source="", doc_type="text", title="", metadata=None):
        if not text:
            return {"indexed": 0, "error": "no_text"}

        metadata = dict(metadata or {})
        chunks = self.chunker.chunk_text(text, source=source, metadata=metadata)

        return self._index_chunks(chunks, source, doc_type, title, metadata)

    def index_file(self, file_path, doc_type=None, metadata=None):
        if not os.path.isfile(file_path):
            return {"indexed": 0, "error": f"file_not_found:{file_path}"}

        if self.document_store and not self.document_store.needs_reindex(file_path):
            return {"indexed": 0, "error": "up_to_date"}

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as e:
            logger.error("[Indexer] Read error %s: %s", file_path, e)
            return {"indexed": 0, "error": f"read_failed:{e}"}

        detected_type = doc_type or self._detect_type(file_path)
        title = os.path.splitext(os.path.basename(file_path))[0]
        meta = dict(metadata or {})
        meta["file_path"] = file_path
        meta["file_size"] = os.path.getsize(file_path)

        return self.index_text(text, source=file_path, doc_type=detected_type, title=title, metadata=meta)

    def index_directory(self, dir_path, pattern="*.txt", recursive=True, doc_type="text"):
        if not os.path.isdir(dir_path):
            return {"indexed": 0, "error": f"directory_not_found:{dir_path}"}

        total_indexed = 0
        total_files = 0
        skipped = 0
        errors = []

        if recursive:
            search = os.path.join(dir_path, "**", pattern)
        else:
            search = os.path.join(dir_path, pattern)

        for file_path in glob_mod.glob(search, recursive=recursive):
            if os.path.isfile(file_path):
                total_files += 1
                result = self.index_file(file_path, doc_type=doc_type)
                if result.get("indexed", 0) > 0:
                    total_indexed += result["indexed"]
                elif result.get("error") == "up_to_date":
                    skipped += 1
                else:
                    errors.append({"file": file_path, "error": result.get("error")})

        summary = {
            "indexed": total_indexed,
            "files_processed": total_files,
            "skipped": skipped,
            "errors": errors,
        }

        if self.event_bus:
            from core.event_specs import INDEXER_COMPLETED
            from core.mai_message import publish_event
            publish_event(self.event_bus, INDEXER_COMPLETED, summary, source="knowledge")

        return summary

    def _index_chunks(self, chunks, source, doc_type, title, metadata):
        count = 0
        total_tokens = 0
        errors = 0

        # 🧠 F-03: drop stale chunks for this source before re-indexing
        # so updated content does not leave orphaned vectors behind.
        if source and hasattr(self.vector_store, "delete_by_metadata"):
            self.vector_store.delete_by_metadata(source=source, memory_type="knowledge")

        for chunk in chunks:
            try:
                chunk_meta = dict(chunk.metadata)
                chunk_meta["chunk_index"] = chunk.index
                chunk_meta["chunk_source"] = chunk.source
                chunk_meta["chunk_id"] = chunk.id
                chunk_meta["doc_type"] = doc_type
                chunk_meta["title"] = title
                chunk_meta["source"] = source
                chunk_meta["memory_type"] = "knowledge"

                self.vector_store.add(chunk.text, metadata=chunk_meta)
                count += 1
                total_tokens += chunk.token_estimate
            except Exception as e:
                logger.error("[Indexer] Chunk index error: %s", e)
                errors += 1

        if self.document_store:
            existing = self.document_store.get_by_source(source)
            if existing:
                self.document_store.update_chunk_count(source, count, total_tokens)
            else:
                self.document_store.add(source, doc_type, title, metadata, count, total_tokens)

        with self._lock:
            self._indexed_count += count

        if self.event_bus:
            from core.event_specs import INDEXER_CHUNKS_INDEXED
            from core.mai_message import publish_event
            publish_event(self.event_bus, INDEXER_CHUNKS_INDEXED, {
                "source": source,
                "chunks": count,
                "errors": errors,
                "total_tokens": total_tokens,
            }, source="knowledge")

        return {"indexed": count, "chunks": len(chunks), "errors": errors, "total_tokens": total_tokens}

    def _detect_type(self, file_path):
        ext = file_path.lower()
        if ext.endswith(".md"):
            return "markdown"
        if ext.endswith((".py", ".js", ".ts", ".java", ".cpp", ".go", ".rs")):
            return "code"
        if ext.endswith((".txt", ".rst")):
            return "text"
        if ext.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".cfg")):
            return "config"
        if ext.endswith((".html", ".htm", ".xml")):
            return "markup"
        if ext.endswith(".csv"):
            return "data"
        return "text"

    def stats(self):
        return {"total_indexed_chunks": self._indexed_count}
