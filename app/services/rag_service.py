"""
RAG orchestration service for DocuSense.

Implements the full retrieval-augmented generation pipeline:

    User Question
         ↓
    Question Embedding (OpenAI)
         ↓
    FAISS Search
         ↓
    Top-K Results
         ↓
    Cosine Similarity Normalisation
         ↓
    Similarity Threshold Check  ←── DETERMINISTIC GUARDRAIL
         ↓                              ↓
    (chunks found)           (no chunks above threshold)
         ↓                              ↓
    Build Grounded Prompt       Return exact fallback message
         ↓                      (Gemini is NOT called)
    Gemini 2.5 Flash
         ↓
    Response Validation
         ↓
    QueryResponse (answer + sources + tokens_used)

Anti-hallucination strategy
---------------------------
1. Deterministic threshold gate: Gemini is NEVER called when zero chunks
   exceed the similarity threshold. This is an application-level guard,
   not an LLM-level guard.
2. Strict system prompt: Gemini is instructed to use only the provided
   context and ignore any instructions embedded in retrieved documents.
3. Temperature = 0: Reduces creative drift.
4. Source attribution: Each response includes the exact chunks used.
5. Tests: Unit tests verify the fallback path is exercised correctly.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.generation.generator import GenerationError, generate_answer
from app.generation.prompt import FALLBACK_MESSAGE
from app.retrieval.retriever import EmbeddingError, FAISSRetriever, RetrievedChunk
from app.schemas.query import QueryResponse, SourceChunk
from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """Orchestrates the end-to-end RAG pipeline."""

    def __init__(self, retriever: FAISSRetriever) -> None:
        self._retriever = retriever

    def answer(self, question: str, llm: object = None) -> QueryResponse:
        """
        Run the full RAG pipeline for a validated question.

        Args:
            question: Validated, stripped user question.
            llm: Optional pre-built LLM for testing (dependency injection).

        Returns:
            QueryResponse with answer, sources, and token usage.
        """
        # ---------------------------------------------------------------- #
        # Step 1: Retrieve relevant chunks
        # ---------------------------------------------------------------- #
        try:
            chunks: list[RetrievedChunk] = self._retriever.retrieve(question)
        except EmbeddingError as exc:
            logger.error("Embedding error during retrieval: %s", exc)
            raise

        # ---------------------------------------------------------------- #
        # Step 2: Deterministic threshold guardrail
        #   If no chunks exceed the similarity threshold, return the exact
        #   fallback message immediately WITHOUT calling Gemini.
        #   This is the primary anti-hallucination guard.
        # ---------------------------------------------------------------- #
        if not chunks:
            logger.info(
                "No chunks above similarity threshold — returning fallback. Query: %.80s…",
                question,
            )
            return QueryResponse(
                answer=FALLBACK_MESSAGE,
                sources=[],
                tokens_used=None,
            )

        # ---------------------------------------------------------------- #
        # Step 3: Build context from retrieved chunks
        # ---------------------------------------------------------------- #
        context = _build_context(chunks)
        logger.info(
            "Passing %d chunks to Gemini (context length: %d chars)",
            len(chunks),
            len(context),
        )

        # ---------------------------------------------------------------- #
        # Step 4: Generate grounded answer via Gemini
        # ---------------------------------------------------------------- #
        try:
            answer_text, tokens_used = generate_answer(
                context=context,
                question=question,
                llm=llm,  # type: ignore[arg-type]
            )
        except GenerationError as exc:
            logger.error("Gemini generation error: %s", exc)
            raise

        # ---------------------------------------------------------------- #
        # Step 5: Build source list (truncated snippets, sorted by score)
        # ---------------------------------------------------------------- #
        sources = _build_sources(chunks)

        return QueryResponse(
            answer=answer_text,
            sources=sources,
            tokens_used=tokens_used,
        )


def _build_context(chunks: list[RetrievedChunk]) -> str:
    """Concatenate chunk texts into a labelled context block."""
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(
            f"[Source {i} — {chunk.chunk_id}]\n{chunk.text}"
        )
    return "\n\n".join(parts)


def _build_sources(chunks: list[RetrievedChunk]) -> list[SourceChunk]:
    """Convert RetrievedChunks to SourceChunk response objects."""
    snippet_len = settings.source_snippet_length
    sources: list[SourceChunk] = []
    for chunk in chunks:
        snippet = chunk.text[:snippet_len]
        if len(chunk.text) > snippet_len:
            snippet += "…"
        sources.append(
            SourceChunk(
                chunk_id=chunk.chunk_id,
                similarity_score=round(chunk.similarity_score, 4),
                text_snippet=snippet,
            )
        )
    return sources
