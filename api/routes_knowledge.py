"""Knowledge-base ingestion domain logic for the Mai API.

Kept as a mixin so ``MaiAPI`` can inherit these methods without changing any
call sites. See ``api.server`` for how this is composed.
"""
import logging
from typing import Any

from api.errors import safe_error

logger = logging.getLogger("api.server")


class KnowledgeMixin:
    """Knowledge base ingestion handler."""

    # Set by MaiAPI at runtime — declared here for type checker
    knowledge_builder: Any = None

    def knowledge_ingest(self, source, text=None, file_path=None, directory=None):
        if not self.knowledge_builder:
            return {"error": "knowledge_builder_not_available"}
        try:
            if text:
                result = self.knowledge_builder.build_from_text(text, source=source)
            elif file_path:
                result = self.knowledge_builder.build_from_file(file_path)
            elif directory:
                result = self.knowledge_builder.build_from_directory(directory)
            else:
                return {"error": "no_content_provided"}
            return result
        except Exception as e:
            return {"error": safe_error(e)}
