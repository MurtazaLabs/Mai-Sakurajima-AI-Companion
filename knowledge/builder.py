import fnmatch
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)


class KnowledgeBaseBuilder:

    def __init__(self, indexer, document_store, vector_store, event_bus=None):
        self.indexer = indexer
        self.document_store = document_store
        self.vector_store = vector_store
        self.event_bus = event_bus
        self._lock = threading.RLock()
        self._builds = []

    def build_from_text(self, text, source="", doc_type="text", title="", metadata=None):
        if not text:
            return {"success": False, "error": "no_text"}

        start = time.time()
        result = self.indexer.index_text(text, source=source, doc_type=doc_type, title=title, metadata=metadata)
        duration = round(time.time() - start, 3)

        summary = {
            "source": source,
            "method": "text",
            "indexed": result.get("indexed", 0),
            "duration": duration,
            "success": result.get("indexed", 0) > 0,
        }
        with self._lock:
            self._builds.append(summary)

        if self.event_bus:
            from core.event_specs import KNOWLEDGE_BUILD_COMPLETED
            from core.mai_message import publish_event
            publish_event(self.event_bus, KNOWLEDGE_BUILD_COMPLETED, summary, source="knowledge")

        return summary

    def build_from_file(self, file_path, doc_type=None, metadata=None):
        if not os.path.isfile(file_path):
            return {"error": f"file_not_found:{file_path}"}

        start = time.time()
        result = self.indexer.index_file(file_path, doc_type=doc_type, metadata=metadata)
        duration = round(time.time() - start, 3)

        summary = {
            "source": file_path,
            "method": "file",
            "indexed": result.get("indexed", 0),
            "duration": duration,
            "success": result.get("indexed", 0) > 0,
            "error": result.get("error"),
        }
        with self._lock:
            self._builds.append(summary)

        if self.event_bus:
            from core.event_specs import KNOWLEDGE_BUILD_COMPLETED
            from core.mai_message import publish_event
            publish_event(self.event_bus, KNOWLEDGE_BUILD_COMPLETED, summary, source="knowledge")

        return summary

    def build_from_directory(self, dir_path, pattern="*.*", recursive=True, doc_type="text"):
        if not os.path.isdir(dir_path):
            return {"error": f"directory_not_found:{dir_path}"}

        start = time.time()

        if not recursive:
            files = [os.path.join(dir_path, f) for f in os.listdir(dir_path)
                     if os.path.isfile(os.path.join(dir_path, f))]
        else:
            files = []
            for root, _, filenames in os.walk(dir_path):
                for fn in filenames:
                    files.append(os.path.join(root, fn))

        if pattern != "*.*":
            files = [f for f in files if fnmatch.fnmatch(os.path.basename(f), pattern)]

        total = 0
        skipped = 0
        errors = []

        for file_path in files:
            result = self.indexer.index_file(file_path, doc_type=doc_type)
            if result.get("indexed", 0) > 0:
                total += result["indexed"]
            elif result.get("error") == "up_to_date":
                skipped += 1
            else:
                errors.append({"file": file_path, "error": result.get("error")})

        duration = round(time.time() - start, 3)
        summary = {
            "source": dir_path,
            "method": "directory",
            "indexed": total,
            "files_found": len(files),
            "skipped": skipped,
            "errors": errors,
            "duration": duration,
            "success": len(errors) == 0,
        }
        with self._lock:
            self._builds.append(summary)

        if self.event_bus:
            from core.event_specs import KNOWLEDGE_BUILD_COMPLETED
            from core.mai_message import publish_event
            publish_event(self.event_bus, KNOWLEDGE_BUILD_COMPLETED, summary, source="knowledge")

        return summary

    def search(self, query, top_k=5):
        return self.vector_store.search(query, top_k=top_k)

    def rebuild_all(self):
        docs = self.document_store.list()
        total = 0
        results = []

        for doc in docs:
            if os.path.isfile(doc.source):
                result = self.build_from_file(doc.source)
                if result.get("success"):
                    total += int(result.get("indexed", 0))
                results.append(result)

        return {"total_reindexed": total, "documents": len(docs), "results": results}

    def stats(self):
        store_stats = self.document_store.stats()
        indexer_stats = self.indexer.stats()
        vector_count = self.vector_store.count()

        with self._lock:
            builds_count = len(self._builds)

        return {
            "documents": store_stats,
            "indexer": indexer_stats,
            "vector_store_count": vector_count,
            "builds_completed": builds_count,
        }

    def history(self, limit=10):
        with self._lock:
            return self._builds[-limit:]
