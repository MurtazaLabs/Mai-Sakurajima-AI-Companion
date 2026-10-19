import hashlib
import json
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)


class DocumentRecord:

    def __init__(self, source, doc_type, title="", metadata=None):
        self.source_id = hashlib.md5(str(source).encode()).hexdigest()
        self.source = str(source)
        self.doc_type = str(doc_type)
        self.title = str(title) or os.path.basename(str(source))
        self.metadata = dict(metadata or {})
        self.chunk_count = 0
        self.total_tokens = 0
        self.indexed_at = time.time()
        self.updated_at = self.indexed_at
        self.file_modified_at = os.path.getmtime(source) if os.path.isfile(source) else 0.0

    def to_dict(self):
        return {
            "source_id": self.source_id,
            "source": self.source,
            "doc_type": self.doc_type,
            "title": self.title,
            "metadata": dict(self.metadata),
            "chunk_count": self.chunk_count,
            "total_tokens": self.total_tokens,
            "indexed_at": self.indexed_at,
            "updated_at": self.updated_at,
            "file_modified_at": self.file_modified_at,
        }


class DocumentStore:

    def __init__(self, path: str | None = None):
        self.path: str | None = path
        self._lock = threading.RLock()
        self._records: dict[str, DocumentRecord] = {}
        self._dirty = False

        if path:
            self._load()

    def add(self, source, doc_type, title="", metadata=None, chunk_count=0, total_tokens=0):
        with self._lock:
            record = DocumentRecord(source, doc_type, title, metadata)
            record.chunk_count = chunk_count
            record.total_tokens = total_tokens
            self._records[record.source_id] = record
            self._dirty = True
            if self.path:
                self._save()
            return record

    def get(self, source_id):
        with self._lock:
            return self._records.get(source_id)

    def get_by_source(self, source):
        source_id = hashlib.md5(str(source).encode()).hexdigest()
        with self._lock:
            return self._records.get(source_id)

    def remove(self, source_id):
        with self._lock:
            removed = self._records.pop(source_id, None)
            if removed:
                self._dirty = True
                if self.path:
                    self._save()
            return removed is not None

    def list(self, doc_type=None):
        with self._lock:
            if doc_type:
                return [r for r in self._records.values() if r.doc_type == doc_type]
            return list(self._records.values())

    def update_chunk_count(self, source, chunk_count, total_tokens):
        with self._lock:
            record = self.get_by_source(source)
            if record:
                record.chunk_count = chunk_count
                record.total_tokens = total_tokens
                record.updated_at = time.time()
                self._dirty = True
                if self.path:
                    self._save()
                return True
            return False

    def needs_reindex(self, source):
        with self._lock:
            record = self.get_by_source(source)
            if record is None:
                return True
            if os.path.isfile(source):
                current_mtime = os.path.getmtime(source)
                if current_mtime != record.file_modified_at:
                    return True
            return False

    def count(self, doc_type=None):
        with self._lock:
            if doc_type:
                return sum(1 for r in self._records.values() if r.doc_type == doc_type)
            return len(self._records)

    def stats(self):
        with self._lock:
            records = self._records.values()
            return {
                "total_documents": len(records),
                "total_chunks": sum(r.chunk_count for r in records),
                "total_tokens": sum(r.total_tokens for r in records),
                "types": {t: sum(1 for r in records if r.doc_type == t) for t in {r.doc_type for r in records}},
            }

    def _load(self):
        if self.path is None:
            return
        with self._lock:
            try:
                if os.path.exists(self.path):
                    with open(self.path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for item in data:
                        record = DocumentRecord(
                            source=item.get("source", ""),
                            doc_type=item.get("doc_type", "unknown"),
                            title=item.get("title", ""),
                            metadata=item.get("metadata", {}),
                        )
                        record.source_id = item.get("source_id", record.source_id)
                        record.chunk_count = item.get("chunk_count", 0)
                        record.total_tokens = item.get("total_tokens", 0)
                        record.indexed_at = item.get("indexed_at", time.time())
                        record.updated_at = item.get("updated_at", time.time())
                        record.file_modified_at = item.get("file_modified_at", 0.0)
                        self._records[record.source_id] = record
                    logger.info("[DocumentStore] Loaded %d records from %s", len(data), self.path)
            except Exception as e:
                logger.error("[DocumentStore] Load error: %s", e)

    def _save(self):
        if self.path is None:
            return
        try:
            data = [r.to_dict() for r in self._records.values()]
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._dirty = False
        except Exception as e:
            logger.error("[DocumentStore] Save error: %s", e)
