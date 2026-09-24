import re
import hashlib
import logging
import math
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Single overlap constant for token-level overlap across all chunking paths
OVERLAP_TOKENS = 64


class Chunk:

    def __init__(
        self,
        text: str,
        index: int,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
        section_heading: str = "",
        position: int = 0,
        embedding_hash: str = "",
    ):
        self.id = hashlib.md5(f"{source}:{index}:{text[:50]}".encode()).hexdigest()
        self.text = str(text)
        self.index = int(index)
        self.source = str(source)
        self.metadata = dict(metadata or {})
        self.section_heading = str(section_heading)
        self.position = int(position)  # Position in document (character offset)
        self.embedding_hash = str(embedding_hash)  # Hash of embedding for cache invalidation
        self.token_estimate = max(1, len(self.text) // 4)
        self.length = len(self.text)

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "index": self.index,
            "source": self.source,
            "metadata": dict(self.metadata),
            "section_heading": self.section_heading,
            "position": self.position,
            "embedding_hash": self.embedding_hash,
            "token_estimate": self.token_estimate,
            "length": self.length,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        """Reconstruct Chunk from dictionary."""
        chunk = cls(
            text=data.get("text", ""),
            index=data.get("index", 0),
            source=data.get("source", ""),
            metadata=data.get("metadata", {}),
            section_heading=data.get("section_heading", ""),
            position=data.get("position", 0),
            embedding_hash=data.get("embedding_hash", ""),
        )
        chunk.id = data.get("id", chunk.id)
        chunk.token_estimate = data.get("token_estimate", chunk.token_estimate)
        chunk.length = data.get("length", chunk.length)
        return chunk


def _cosine_similarity(a, b):
    import numpy as np
    a = np.array(a, dtype=np.float64)
    b = np.array(b, dtype=np.float64)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm < 1e-12:
        return 0.0
    return float(np.dot(a, b) / norm)


class TextChunker:

    def __init__(
        self,
        chunk_size: int = 512,
        overlap: Optional[int] = None,
        embedding_service=None,
        semantic_threshold: float = 0.3,
    ):
        self.chunk_size = max(64, int(chunk_size))
        # Use single token-level overlap constant across all chunking paths
        self.overlap = (
            min(self.chunk_size // 2, max(0, int(overlap)))
            if overlap is not None
            else OVERLAP_TOKENS
        )
        self.embedding_service = embedding_service
        self.semantic_threshold = float(semantic_threshold)

    def chunk_text(self, text, source="", metadata=None):
        if not text:
            return []

        text = str(text).strip()
        if not text:
            return []

        metadata = dict(metadata or {})
        paragraphs = self._split_paragraphs(text)
        chunks = []
        buffer = ""
        index = 0
        position = 0  # Track character position in document
        current_section = ""  # Track current section heading

        # Build semantic boundary map upfront if embeddings available
        boundary_map = self._build_boundary_map(text)

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if this paragraph is a section heading (short line, no period at end)
            if len(para) < 80 and not para.endswith((".", "!", "?")):
                current_section = para

            # Check for semantic boundary between buffer and this paragraph
            if buffer and self._is_semantic_boundary(buffer, para, boundary_map):
                chunks.extend(self._split_large(buffer, source, metadata, index, current_section, position))
                index += 1
                buffer = ""

            if len(buffer) + len(para) < self.chunk_size:
                buffer = (buffer + "\n\n" + para).strip()
            else:
                if buffer:
                    chunks.extend(self._split_large(buffer, source, metadata, index, current_section, position, boundary_map=boundary_map))
                    index += 1
                    buffer = self._carry_over(buffer)

                if len(para) > self.chunk_size:
                    sub_chunks = self._split_large(para, source, metadata, index, current_section, position, boundary_map=boundary_map)
                    chunks.extend(sub_chunks)
                    index += len(sub_chunks)
                    buffer = ""
                else:
                    buffer = para

        if buffer:
            chunks.extend(self._split_large(buffer, source, metadata, index, current_section, position, boundary_map=boundary_map))

        return chunks

    def _is_semantic_boundary(self, buffer, paragraph, boundary_map):
        if not self.embedding_service or not self.embedding_service.is_available:
            return False
        if not boundary_map:
            return False
        # Find the last sentence of buffer and first of paragraph
        buffer_sents = self._split_sentences(buffer)
        para_sents = self._split_sentences(paragraph)
        if not buffer_sents or not para_sents:
            return False
        last_sent = buffer_sents[-1].strip()
        first_sent = para_sents[0].strip()
        if not last_sent or not first_sent:
            return False
        emb_last = boundary_map.get(last_sent)
        emb_first = boundary_map.get(first_sent)
        if emb_last is None or emb_first is None:
            return False
        sim = _cosine_similarity(emb_last, emb_first)
        return sim < self.semantic_threshold

    def _build_boundary_map(self, text):
        if not self.embedding_service or not self.embedding_service.is_available:
            return {}
        sentences = self._split_sentences(text)
        # Deduplicate identical sentences to reduce embed calls
        unique = list(dict.fromkeys(s.strip() for s in sentences if s.strip()))
        result = {}
        for sent in unique:
            try:
                emb = self.embedding_service.embed(sent)
                if emb is not None:
                    result[sent] = emb
            except Exception as e:
                logger.debug("[Chunker] embed failed for sentence: %s", e)
                continue
        return result

    def _split_paragraphs(self, text):
        text = text.replace("\r\n", "\n")
        raw = re.split(r"\n\s*\n", text)
        return [p.strip() for p in raw if p.strip()]

    def _split_large(self, text, source, metadata, start_index, section_heading="", position=0, boundary_map=None):
        chunks = []
        sentences = self._split_sentences(text)
        buffer = ""
        index = start_index
        pos = position  # Track position within this text segment

        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue

            # Semantic boundary check between buffer and next sentence
            if buffer and self.embedding_service and boundary_map:
                buffer_sents = self._split_sentences(buffer)
                if buffer_sents and buffer_sents[-1].strip() in boundary_map and sent in boundary_map:
                    emb_last = boundary_map.get(buffer_sents[-1].strip())
                    emb_next = boundary_map.get(sent)
                    if emb_last is not None and emb_next is not None:
                        sim = _cosine_similarity(emb_last, emb_next)
                        if sim < self.semantic_threshold:
                            if buffer:
                                # Compute embedding hash for cache invalidation
                                emb_hash = hashlib.md5(buffer.encode()).hexdigest()[:16]
                                chunks.append(
                                    Chunk(
                                        buffer,
                                        index,
                                        source,
                                        metadata,
                                        section_heading=section_heading,
                                        position=pos,
                                        embedding_hash=emb_hash,
                                    )
                                )
                                index += 1
                                buffer = self._carry_over(buffer)

            if len(buffer) + len(sent) < self.chunk_size:
                buffer = (buffer + " " + sent).strip()
                pos += len(sent) + 1  # +1 for space
            else:
                if buffer:
                    emb_hash = hashlib.md5(buffer.encode()).hexdigest()[:16]
                    chunks.append(
                        Chunk(
                            buffer,
                            index,
                            source,
                            metadata,
                            section_heading=section_heading,
                            position=pos,
                            embedding_hash=emb_hash,
                        )
                    )
                    index += 1
                    buffer = self._carry_over(buffer)
                    pos += len(self._carry_over(buffer)) + 1  # approximate

                if len(sent) > self.chunk_size:
                    sub = self._split_by_tokens(sent, source, metadata, index, section_heading=section_heading, position=pos)
                    chunks.extend(sub)
                    index += len(sub)
                    buffer = ""
                else:
                    buffer = sent

        if buffer:
            emb_hash = hashlib.md5(buffer.encode()).hexdigest()[:16]
            chunks.append(
                Chunk(
                    buffer,
                    index,
                    source,
                    metadata,
                    section_heading=section_heading,
                    position=pos,
                    embedding_hash=emb_hash,
                )
            )

        return chunks

    def _split_sentences(self, text):
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if p.strip()]

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (roughly 4 chars per token for English)."""
        return max(1, len(text) // 4)

    def _tokenize_overlap(self, text: str, overlap_tokens: int) -> str:
        """Extract the last `overlap_tokens` worth of text using token-level overlap."""
        # Rough tokenization: ~4 chars per token
        chars_per_token = 4
        overlap_chars = overlap_tokens * chars_per_token
        if len(text) <= overlap_chars:
            return text
        return text[-overlap_chars:]

    def _split_by_tokens(self, text, source, metadata, start_index, section_heading="", position=0):
        """Split text by token-level chunks with token-level overlap."""
        chunks = []
        index = start_index
        start = 0
        overlap_chars = OVERLAP_TOKENS * 4  # ~4 chars per token

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            if chunk_text.strip():
                # Compute embedding hash for cache invalidation
                embedding_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:16]
                chunks.append(
                    Chunk(
                        chunk_text.strip(),
                        index,
                        source,
                        metadata,
                        section_heading=section_heading,
                        position=position + start,
                        embedding_hash=embedding_hash,
                    )
                )
                index += 1
            # Move start position with token-level overlap
            if end < len(text):
                start = end - overlap_chars
            else:
                start = end

        return chunks

    def _carry_over(self, buffer: str) -> str:
        """Return the last OVERLAP_TOKENS worth of text for overlap."""
        return self._tokenize_overlap(buffer, self.overlap)
