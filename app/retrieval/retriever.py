"""
FAISS retriever for DocuSense.

Handles:
  - Loading the FAISS index from disk
  - Querying with a user question embedding
  - Score normalisation (cosine similarity)
  - Similarity threshold filtering

Score Calculation
-----------------
During indexing, all document embeddings are L2-normalised before being
added to an IndexFlatIP (inner product) index.

For two L2-normalised unit vectors u and v:
    inner_product(u, v) = cosine_similarity(u, v)

The cosine similarity of two unit vectors lies in [-1.0, 1.0]:
    +1.0  → vectors point in the same direction (highly similar)
     0.0  → vectors are orthogonal (unrelated)
    -1.0  → vectors point in opposite directions

During query, the query vector is also L2-normalised so that FAISS
returns true cosine similarities.  Scores below 0.0 are clamped to 0.0
because a negative cosine similarity indicates the content is semantically
opposed to the query and is certainly not relevant context.

The exposed `similarity_score` is therefore in [0.0, 1.0] and reflects
geometric similarity — not a probability or confidence percentage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.core.config import settings
from app.embeddings.embedder import get_embeddings

logger = logging.getLogger(__name__)


class IndexNotFoundError(Exception):
    """Raised when the FAISS index has not been built yet."""


class EmbeddingError(Exception):
    """Raised when the query embedding API call fails."""


@dataclass
class RetrievedChunk:
    """A document chunk returned by the retriever."""

    document: Document
    similarity_score: float  # Cosine similarity in [0.0, 1.0]

    @property
    def chunk_id(self) -> str:
        return self.document.metadata.get("chunk_id", "unknown")

    @property
    def text(self) -> str:
        return self.document.page_content


class FAISSRetriever:
    """
    Loads and queries a persisted FAISS vector index.

    The index must be built first using:
        python -m app.ingestion.indexer
    """

    def __init__(self, index_path: str | None = None) -> None:
        self._index_path = Path(index_path or settings.faiss_index_path)
        self._vector_store: FAISS | None = None

    def load(self) -> None:
        """
        Load the FAISS index from disk.

        Raises:
            IndexNotFoundError: If the index files are not found.
        """
        if not self._index_path.exists():
            raise IndexNotFoundError(
                f"FAISS index not found at '{self._index_path}'.\n\n"
                "Run the indexer first:\n\n"
                "    python -m app.ingestion.indexer\n"
            )

        required_files = ["index.faiss", "index.pkl"]
        for fname in required_files:
            if not (self._index_path / fname).exists():
                raise IndexNotFoundError(
                    f"FAISS index is incomplete — '{fname}' is missing "
                    f"in '{self._index_path}'.\n\n"
                    "Rebuild the index:\n\n"
                    "    python -m app.ingestion.indexer\n"
                )

        embeddings = get_embeddings()
        self._vector_store = FAISS.load_local(
            str(self._index_path),
            embeddings,
            allow_dangerous_deserialization=True,
        )
        logger.info("FAISS index loaded from '%s'", self._index_path)

    @property
    def is_loaded(self) -> bool:
        return self._vector_store is not None

    def retrieve(
        self,
        question: str,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
    ) -> list[RetrievedChunk]:
        """
        Embed the question and retrieve the most relevant chunks.

        Pipeline:
            question → embedding → L2-normalise → FAISS search →
            cosine scores → threshold filter → sorted results

        Args:
            question: User's natural-language question.
            top_k: Number of FAISS candidates to retrieve.
                   Defaults to settings.top_k.
            similarity_threshold: Minimum score to keep a chunk.
                                  Defaults to settings.similarity_threshold.

        Returns:
            List of RetrievedChunk sorted by similarity_score descending.
            May be empty if no chunks exceed the threshold.

        Raises:
            IndexNotFoundError: If the index has not been loaded.
            EmbeddingError: If the OpenAI embedding call fails.
        """
        if self._vector_store is None:
            raise IndexNotFoundError(
                "FAISS index is not loaded. Call retriever.load() first."
            )

        k = top_k if top_k is not None else settings.top_k
        threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else settings.similarity_threshold
        )

        # Retrieve raw (doc, score) pairs from LangChain FAISS.
        # The score returned by FAISS.similarity_search_with_score is the
        # raw inner-product value because we built an IndexFlatIP.
        # For L2-normalised vectors this equals cosine similarity ∈ [-1, 1].
        try:
            raw_results: list[tuple[Document, float]] = (
                self._vector_store.similarity_search_with_score(question, k=k)
            )
        except Exception as exc:
            raise EmbeddingError(
                f"Failed to embed query or search FAISS: {exc}"
            ) from exc

        chunks: list[RetrievedChunk] = []
        for doc, raw_score in raw_results:
            # Clamp to [0.0, 1.0]: negative cosine similarity means the
            # chunk is semantically opposed — certainly not useful context.
            cosine_sim = float(np.clip(raw_score, 0.0, 1.0))

            if cosine_sim >= threshold:
                chunks.append(
                    RetrievedChunk(document=doc, similarity_score=cosine_sim)
                )

        # Sort descending by similarity (most relevant first)
        chunks.sort(key=lambda c: c.similarity_score, reverse=True)

        logger.info(
            "Retrieved %d/%d chunks above threshold %.2f for query: %.80s…",
            len(chunks),
            k,
            threshold,
            question,
        )
        return chunks


# ----------------------------------------------------------------------- #
# Module-level singleton — created once and reused by the FastAPI app.
# ----------------------------------------------------------------------- #
_retriever: FAISSRetriever | None = None


def get_retriever() -> FAISSRetriever:
    """Return the application-level retriever singleton."""
    global _retriever
    if _retriever is None:
        _retriever = FAISSRetriever()
    return _retriever
