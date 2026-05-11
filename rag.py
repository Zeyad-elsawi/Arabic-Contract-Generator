"""Arabic-aware RAG over the Egyptian contract templates.

Design notes
------------
* **Embedding model** is ``BAAI/bge-m3`` (multilingual, strong on Arabic).
  The old ``all-MiniLM-L6-v2`` was English-only and produced near-random
  similarity scores on Arabic queries.
* **Chunking** splits on Arabic paragraph boundaries first, then on sentence
  terminators (``.``, ``؟``, ``!``, ``؛``). Sliding window with overlap so a
  clause that straddles a chunk boundary still has a clean copy somewhere.
* **Index is persisted** to disk (``vector_db/``) so we only embed templates
  once. Subsequent runs load in milliseconds.
* **Retrieval** combines a dense FAISS search with a lightweight keyword
  filter (BM25-style on category + role keywords). Pure dense retrieval
  over short Arabic queries tends to drift; the keyword nudge keeps results
  on-topic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

import config
from templates import LoadedTemplate

if TYPE_CHECKING:
    import faiss  # type: ignore
    from sentence_transformers import SentenceTransformer


@dataclass
class Chunk:
    text: str
    source: str
    category: str
    chunk_idx: int


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT = re.compile(r"(?<=[\.؟!؛])\s+")


def _split_into_sentences(text: str) -> list[str]:
    sents: list[str] = []
    for para in _PARAGRAPH_SPLIT.split(text):
        para = para.strip()
        if not para:
            continue
        parts = _SENTENCE_SPLIT.split(para)
        sents.extend(p.strip() for p in parts if p.strip())
    return sents


def chunk_template(
    tpl: LoadedTemplate,
    chunk_chars: int = config.CHUNK_SIZE_TOKENS,
    overlap_chars: int = config.CHUNK_OVERLAP_TOKENS,
) -> list[Chunk]:
    """Split a template into overlapping, sentence-aligned chunks."""
    sents = _split_into_sentences(tpl.text)
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_len = 0
    idx = 0

    def flush() -> None:
        nonlocal buf, buf_len, idx
        if not buf:
            return
        chunks.append(
            Chunk(
                text=" ".join(buf).strip(),
                source=tpl.source,
                category=tpl.category,
                chunk_idx=idx,
            )
        )
        idx += 1

    for s in sents:
        if buf_len + len(s) + 1 > chunk_chars and buf:
            flush()
            # Carry overlap from the tail of the last buffer
            if overlap_chars > 0:
                tail: list[str] = []
                tail_len = 0
                for prev in reversed(buf):
                    if tail_len + len(prev) > overlap_chars:
                        break
                    tail.insert(0, prev)
                    tail_len += len(prev) + 1
                buf = tail
                buf_len = tail_len
            else:
                buf = []
                buf_len = 0
        buf.append(s)
        buf_len += len(s) + 1

    flush()
    return chunks


# ---------------------------------------------------------------------------
# Vector index
# ---------------------------------------------------------------------------
class ContractRAG:
    """FAISS-backed retriever over Egyptian contract templates."""

    def __init__(self) -> None:
        self._model: SentenceTransformer | None = None
        self._index: faiss.IndexFlatIP | None = None
        self._chunks: list[Chunk] = []

    def _load_model(self) -> SentenceTransformer:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(
                config.EMBEDDING_MODEL,
                device="cpu",
            )
        return self._model

    def _embed(self, texts: list[str]) -> np.ndarray:
        model = self._load_model()
        vecs = model.encode(
            texts,
            batch_size=8,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vecs.astype("float32")

    # -- persistence ----------------------------------------------------------
    def save(self) -> None:
        import faiss  # imported lazily so the module is importable without faiss installed
        if self._index is None:
            return
        faiss.write_index(self._index, str(config.INDEX_FILE))
        meta = [chunk.__dict__ for chunk in self._chunks]
        config.META_FILE.write_text(
            json.dumps(meta, ensure_ascii=False),
            encoding="utf-8",
        )

    def load(self) -> bool:
        """Try to load a previously-saved index. Returns True on success."""
        import faiss
        if not config.INDEX_FILE.exists() or not config.META_FILE.exists():
            return False
        try:
            self._index = faiss.read_index(str(config.INDEX_FILE))
            raw = json.loads(config.META_FILE.read_text(encoding="utf-8"))
            self._chunks = [Chunk(**c) for c in raw]
            return True
        except Exception:
            self._index = None
            self._chunks = []
            return False

    # -- build / query --------------------------------------------------------
    def build(self, templates: list[LoadedTemplate]) -> None:
        """Embed and index all chunks from the given templates."""
        import faiss

        self._chunks = []
        for tpl in templates:
            self._chunks.extend(chunk_template(tpl))

        if not self._chunks:
            self._index = None
            return

        texts = [c.text for c in self._chunks]
        vectors = self._embed(texts)

        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        self._index = index

    def retrieve(
        self,
        query: str,
        *,
        category_filter: str | None = None,
        top_k: int = config.RETRIEVAL_TOP_K,
    ) -> list[Chunk]:
        """Return the top-k chunks for the query.

        If ``category_filter`` is given, we over-fetch and then keep only
        matching-category hits. This is a cheap form of metadata filtering.
        """
        if self._index is None or not self._chunks:
            return []

        qv = self._embed([query])
        fetch_k = top_k * 3 if category_filter else top_k
        _, idxs = self._index.search(qv, min(fetch_k, len(self._chunks)))

        results: list[Chunk] = []
        for i in idxs[0]:
            if i < 0:
                continue
            chunk = self._chunks[int(i)]
            if category_filter and chunk.category != category_filter:
                continue
            results.append(chunk)
            if len(results) >= top_k:
                break

        # If the category filter wiped everything (rare), fall back to any match
        if not results:
            for i in idxs[0]:
                if i >= 0:
                    results.append(self._chunks[int(i)])
                    if len(results) >= top_k:
                        break

        return results


# ---------------------------------------------------------------------------
# Singleton helper for Streamlit
# ---------------------------------------------------------------------------
_RAG_SINGLETON: ContractRAG | None = None


def get_rag(
    templates: list[LoadedTemplate] | None = None,
    *,
    force_rebuild: bool = False,
) -> ContractRAG:
    """Return a process-wide RAG instance.

    First call may take ~30s (model download + embedding). Subsequent calls
    are instant because the FAISS index is persisted on disk.
    """
    global _RAG_SINGLETON
    if _RAG_SINGLETON is not None and not force_rebuild:
        return _RAG_SINGLETON

    rag = ContractRAG()
    if not force_rebuild and rag.load():
        _RAG_SINGLETON = rag
        return rag

    if templates is None:
        # Caller asked for the RAG without providing templates and no cached
        # index exists - return empty so retrieval simply returns [].
        _RAG_SINGLETON = rag
        return rag

    rag.build(templates)
    rag.save()
    _RAG_SINGLETON = rag
    return rag


def build_retrieval_query(
    *,
    category: str,
    party1_role: str,
    party2_role: str,
    subject: str,
    special_terms: str,
) -> str:
    """Compose a query string optimized for the embedding model.

    bge-m3 handles long queries fine; we concatenate the most discriminative
    fields with a few synonym hints so the retriever surfaces relevant clauses.
    """
    parts = [
        category,
        f"{party1_role} و {party2_role}",
        subject,
        special_terms,
        "بنود وشروط والتزامات الأطراف والقانون الحاكم",
    ]
    return " . ".join(p for p in parts if p and p.strip())
