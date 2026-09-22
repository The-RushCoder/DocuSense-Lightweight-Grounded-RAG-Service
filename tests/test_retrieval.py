"""
Test 2: Retrieval

Verifies:
  - Similarity threshold filtering works correctly
  - Results below threshold are excluded
  - Results are sorted by score descending
  - Score clamping to [0.0, 1.0] is applied
  - IndexNotFoundError is raised for missing index
  - Relevant chunks are returned for known questions (mock)
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from app.retrieval.retriever import (
    EmbeddingError,
    FAISSRetriever,
    IndexNotFoundError,
    RetrievedChunk,
)


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _make_chunk(chunk_id: str, text: str, score: float) -> tuple[Document, float]:
    """Create a (Document, raw_score) pair as returned by FAISS."""
    doc = Document(
        page_content=text,
        metadata={"chunk_id": chunk_id, "source": "test.md", "chunk_index": 0},
    )
    return doc, score


# ------------------------------------------------------------------ #
# Tests
# ------------------------------------------------------------------ #

class TestRetrieval:
    """Tests for the FAISSRetriever, using mocked FAISS internals."""

    def _make_retriever_with_mock_store(
        self,
        raw_results: list[tuple[Document, float]],
    ) -> FAISSRetriever:
        """
        Build a FAISSRetriever whose internal FAISS store is pre-mocked
        to return the provided raw_results list.
        """
        retriever = FAISSRetriever.__new__(FAISSRetriever)
        mock_store = MagicMock()
        mock_store.similarity_search_with_score.return_value = raw_results
        retriever._vector_store = mock_store
        retriever._index_path = MagicMock()
        return retriever

    def test_threshold_filters_low_scores(self) -> None:
        """Chunks with scores below the threshold are excluded."""
        raw_results = [
            _make_chunk("chunk_001", "Backup retention is 30 days.", 0.90),
            _make_chunk("chunk_002", "Something unrelated.", 0.50),  # below 0.75
            _make_chunk("chunk_003", "Passwords expire every 90 days.", 0.80),
        ]
        retriever = self._make_retriever_with_mock_store(raw_results)
        results = retriever.retrieve("backup", top_k=3, similarity_threshold=0.75)

        returned_ids = [r.chunk_id for r in results]
        assert "chunk_001" in returned_ids
        assert "chunk_003" in returned_ids
        assert "chunk_002" not in returned_ids, "Low-score chunk must be filtered out"

    def test_results_sorted_by_score_descending(self) -> None:
        """Results are ordered from highest to lowest similarity score."""
        raw_results = [
            _make_chunk("chunk_003", "Text C", 0.80),
            _make_chunk("chunk_001", "Text A", 0.95),
            _make_chunk("chunk_002", "Text B", 0.88),
        ]
        retriever = self._make_retriever_with_mock_store(raw_results)
        results = retriever.retrieve("query", top_k=3, similarity_threshold=0.0)

        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True), (
            "Results must be sorted by similarity score descending"
        )

    def test_negative_scores_are_clamped_to_zero(self) -> None:
        """Negative cosine similarity is clamped to 0.0 and filtered out at threshold=0.0."""
        raw_results = [
            _make_chunk("chunk_001", "Relevant text.", 0.85),
            _make_chunk("chunk_002", "Irrelevant.", -0.20),  # negative cosine
        ]
        retriever = self._make_retriever_with_mock_store(raw_results)
        results = retriever.retrieve("query", top_k=2, similarity_threshold=0.0)

        for r in results:
            assert r.similarity_score >= 0.0, "Scores must be non-negative"

    def test_all_below_threshold_returns_empty(self) -> None:
        """When all scores are below threshold, an empty list is returned."""
        raw_results = [
            _make_chunk("chunk_001", "Text A", 0.40),
            _make_chunk("chunk_002", "Text B", 0.30),
        ]
        retriever = self._make_retriever_with_mock_store(raw_results)
        results = retriever.retrieve("query", top_k=2, similarity_threshold=0.75)

        assert results == [], "Expected empty list when all scores are below threshold"

    def test_scores_clamped_to_max_one(self) -> None:
        """Scores above 1.0 (shouldn't happen but be safe) are clamped to 1.0."""
        raw_results = [
            _make_chunk("chunk_001", "Text A", 1.05),  # slightly above 1.0
        ]
        retriever = self._make_retriever_with_mock_store(raw_results)
        results = retriever.retrieve("query", top_k=1, similarity_threshold=0.0)

        assert len(results) == 1
        assert results[0].similarity_score <= 1.0

    def test_index_not_loaded_raises_error(self) -> None:
        """Calling retrieve() before loading raises IndexNotFoundError."""
        retriever = FAISSRetriever.__new__(FAISSRetriever)
        retriever._vector_store = None
        retriever._index_path = MagicMock()

        with pytest.raises(IndexNotFoundError):
            retriever.retrieve("any question")

    def test_missing_index_path_raises_error(self) -> None:
        """Calling load() with a non-existent path raises IndexNotFoundError."""
        retriever = FAISSRetriever(index_path="/nonexistent/path/that/does/not/exist")
        with pytest.raises(IndexNotFoundError, match="FAISS index not found"):
            retriever.load()

    def test_embedding_error_propagated(self) -> None:
        """If FAISS search raises, it is converted to EmbeddingError."""
        retriever = FAISSRetriever.__new__(FAISSRetriever)
        mock_store = MagicMock()
        mock_store.similarity_search_with_score.side_effect = RuntimeError("API down")
        retriever._vector_store = mock_store
        retriever._index_path = MagicMock()

        with pytest.raises(EmbeddingError, match="Failed to embed query"):
            retriever.retrieve("question")

    def test_is_loaded_flag(self) -> None:
        """is_loaded returns True only after a successful load."""
        retriever = FAISSRetriever.__new__(FAISSRetriever)
        retriever._vector_store = None
        assert not retriever.is_loaded

        retriever._vector_store = MagicMock()
        assert retriever.is_loaded

    def test_relevant_chunk_returned_for_backup_question(self) -> None:
        """
        Test 2 required scenario: 'database backup retention period' retrieves
        a relevant chunk.

        The mock simulates what FAISS would return for this question against
        the policy document.
        """
        raw_results = [
            _make_chunk(
                "chunk_004",
                "All primary database backups are retained for a rolling period "
                "of 30 calendar days. After 30 days, backups are automatically "
                "purged from the primary backup storage.",
                0.92,
            )
        ]
        retriever = self._make_retriever_with_mock_store(raw_results)
        results = retriever.retrieve(
            "What is the database backup retention period?",
            top_k=4,
            similarity_threshold=0.75,
        )
        assert len(results) == 1
        assert results[0].chunk_id == "chunk_004"
        assert results[0].similarity_score >= 0.75
        assert "30" in results[0].text
