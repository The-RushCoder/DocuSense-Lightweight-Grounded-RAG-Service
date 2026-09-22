"""
Tests 5, 6, 7: API

Verifies:
  5. Empty question → 422 validation error
  6. Valid response schema (answer, sources, tokens_used fields present)
  7. Missing FAISS index → clear error response
  + Health endpoint returns 200 with correct fields
  + Question too long → 422 validation error
  + Whitespace-only question → 422 validation error

Note: We inject the retriever directly into app.state before each test,
bypassing the lifespan startup (which would try to load a real FAISS index).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.generation.prompt import FALLBACK_MESSAGE
from app.main import create_app
from app.retrieval.retriever import FAISSRetriever, IndexNotFoundError


# ------------------------------------------------------------------ #
# App and client fixture helpers
# ------------------------------------------------------------------ #

def _make_app_client(retriever: FAISSRetriever | None) -> TestClient:
    """
    Create a TestClient.  We use lifespan=False so the startup handler
    (which tries to load a real FAISS index) is skipped, then we manually
    inject the mock retriever into app.state.
    """
    app = create_app()
    # Inject state before the client starts making requests
    app.state.retriever = retriever
    client = TestClient(app, raise_server_exceptions=False)
    return client


def _make_loaded_retriever(chunks: list | None = None) -> FAISSRetriever:
    """Return a mocked retriever that returns the given chunks."""
    retriever = MagicMock(spec=FAISSRetriever)
    retriever.is_loaded = True
    retriever.retrieve.return_value = chunks if chunks is not None else []
    return retriever


def _make_unloaded_retriever() -> FAISSRetriever:
    """Return a retriever that raises IndexNotFoundError on retrieve()."""
    retriever = MagicMock(spec=FAISSRetriever)
    retriever.is_loaded = False
    retriever.retrieve.side_effect = IndexNotFoundError(
        "FAISS index not found. Run: python -m app.ingestion.indexer"
    )
    return retriever


# ------------------------------------------------------------------ #
# Health endpoint tests
# ------------------------------------------------------------------ #

class TestHealthEndpoint:
    def test_health_returns_200(self) -> None:
        client = _make_app_client(_make_loaded_retriever())
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status_ok(self) -> None:
        client = _make_app_client(_make_loaded_retriever())
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_reports_vector_store_loaded(self) -> None:
        client = _make_app_client(_make_loaded_retriever())
        data = client.get("/health").json()
        assert "vector_store_loaded" in data
        assert data["vector_store_loaded"] is True

    def test_health_reports_vector_store_not_loaded(self) -> None:
        client = _make_app_client(None)
        data = client.get("/health").json()
        assert data["vector_store_loaded"] is False


# ------------------------------------------------------------------ #
# Test 5: Empty / invalid question validation
# ------------------------------------------------------------------ #

class TestQuestionValidation:
    """Test 5 — question validation returns 4xx errors."""

    def test_missing_question_field(self) -> None:
        """Missing 'question' field → 422."""
        client = _make_app_client(_make_loaded_retriever())
        response = client.post("/api/query", json={})
        assert response.status_code == 422

    def test_empty_string_question(self) -> None:
        """Empty string question → 422."""
        client = _make_app_client(_make_loaded_retriever())
        response = client.post("/api/query", json={"question": ""})
        assert response.status_code == 422

    def test_whitespace_only_question(self) -> None:
        """Whitespace-only question → 422."""
        client = _make_app_client(_make_loaded_retriever())
        response = client.post("/api/query", json={"question": "   "})
        assert response.status_code == 422

    def test_question_too_long(self) -> None:
        """Question exceeding 2000 characters → 422."""
        client = _make_app_client(_make_loaded_retriever())
        long_q = "a" * 2001
        response = client.post("/api/query", json={"question": long_q})
        assert response.status_code == 422

    def test_valid_question_passes_validation(self) -> None:
        """A valid question reaches the service layer (mock returns fallback)."""
        client = _make_app_client(_make_loaded_retriever(chunks=[]))
        with patch("app.services.rag_service.generate_answer"):
            response = client.post(
                "/api/query",
                json={"question": "What is the password policy?"},
            )
        # 200 with fallback (no chunks)
        assert response.status_code == 200

    def test_question_at_max_length_passes(self) -> None:
        """Question at exactly 2000 characters is valid."""
        client = _make_app_client(_make_loaded_retriever(chunks=[]))
        max_q = "a" * 2000
        response = client.post("/api/query", json={"question": max_q})
        assert response.status_code == 200


# ------------------------------------------------------------------ #
# Test 6: Response schema
# ------------------------------------------------------------------ #

class TestResponseSchema:
    """Test 6 — Response always contains answer, sources, tokens_used."""

    def test_fallback_response_schema(self) -> None:
        """Fallback path returns all required schema fields."""
        client = _make_app_client(_make_loaded_retriever(chunks=[]))
        data = client.post(
            "/api/query",
            json={"question": "What is the vacation policy?"},
        ).json()

        assert "answer" in data, "Response missing 'answer' field"
        assert "sources" in data, "Response missing 'sources' field"
        assert "tokens_used" in data, "Response missing 'tokens_used' field"

    def test_fallback_sources_is_empty_list(self) -> None:
        """Fallback response has sources=[]."""
        client = _make_app_client(_make_loaded_retriever(chunks=[]))
        data = client.post(
            "/api/query", json={"question": "Vacation policy?"}
        ).json()
        assert data["sources"] == []

    def test_fallback_tokens_used_is_null(self) -> None:
        """Fallback response has tokens_used=null."""
        client = _make_app_client(_make_loaded_retriever(chunks=[]))
        data = client.post(
            "/api/query", json={"question": "Vacation policy?"}
        ).json()
        assert data["tokens_used"] is None

    def test_grounded_response_schema(self) -> None:
        """Grounded answer response (with mocked LLM) contains all schema fields."""
        from langchain_core.documents import Document
        from app.retrieval.retriever import RetrievedChunk

        doc = Document(
            page_content="Backup retention is 30 days.",
            metadata={"chunk_id": "chunk_004", "source": "test.md", "chunk_index": 3},
        )
        chunk = RetrievedChunk(document=doc, similarity_score=0.92)
        client = _make_app_client(_make_loaded_retriever(chunks=[chunk]))

        with patch("app.services.rag_service.generate_answer") as mock_gen:
            mock_gen.return_value = ("Retention is 30 days.", 164)
            data = client.post(
                "/api/query",
                json={"question": "What is the backup retention period?"},
            ).json()

        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) == 1
        assert "chunk_id" in data["sources"][0]
        assert "similarity_score" in data["sources"][0]
        assert "text_snippet" in data["sources"][0]
        assert data["tokens_used"] == 164

    def test_source_similarity_score_in_range(self) -> None:
        """Source similarity scores are in [0.0, 1.0]."""
        from langchain_core.documents import Document
        from app.retrieval.retriever import RetrievedChunk

        doc = Document(
            page_content="Some policy text.",
            metadata={"chunk_id": "chunk_001", "source": "test.md", "chunk_index": 0},
        )
        chunk = RetrievedChunk(document=doc, similarity_score=0.87)
        client = _make_app_client(_make_loaded_retriever(chunks=[chunk]))

        with patch("app.services.rag_service.generate_answer") as mock_gen:
            mock_gen.return_value = ("Answer.", 50)
            data = client.post(
                "/api/query", json={"question": "Policy question?"}
            ).json()

        score = data["sources"][0]["similarity_score"]
        assert 0.0 <= score <= 1.0


# ------------------------------------------------------------------ #
# Test 7: Missing FAISS index
# ------------------------------------------------------------------ #

class TestMissingIndex:
    """Test 7 — Missing FAISS index returns a clear, actionable error."""

    def test_missing_index_returns_503(self) -> None:
        """503 is returned when the FAISS index is not built."""
        client = _make_app_client(_make_unloaded_retriever())
        response = client.post(
            "/api/query",
            json={"question": "What is the password policy?"},
        )
        assert response.status_code == 503

    def test_missing_index_error_message_is_helpful(self) -> None:
        """The error detail mentions the indexer command."""
        client = _make_app_client(_make_unloaded_retriever())
        data = client.post(
            "/api/query",
            json={"question": "What is the password policy?"},
        ).json()
        detail = data.get("detail", "").lower()
        assert "index" in detail or "indexer" in detail

    def test_health_shows_not_loaded_when_index_missing(self) -> None:
        """Health endpoint shows vector_store_loaded=False for missing index."""
        client = _make_app_client(None)
        data = client.get("/health").json()
        assert data["vector_store_loaded"] is False
