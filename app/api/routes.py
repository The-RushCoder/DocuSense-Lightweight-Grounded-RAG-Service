"""
API routes for DocuSense.

Endpoints:
  GET  /health     — liveness check
  POST /api/query  — RAG question answering
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.generation.generator import GenerationError
from app.retrieval.retriever import EmbeddingError, IndexNotFoundError, FAISSRetriever
from app.schemas.query import ErrorResponse, QueryRequest, QueryResponse
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------- #
# Dependency: retrieve the loaded FAISSRetriever from app state
# ---------------------------------------------------------------------- #

def _get_retriever(request: Request) -> FAISSRetriever:
    retriever: FAISSRetriever = request.app.state.retriever
    return retriever


# ---------------------------------------------------------------------- #
# GET /health
# ---------------------------------------------------------------------- #

@router.get(
    "/health",
    summary="Health check",
    description="Returns service liveness status and whether the FAISS vector store is loaded.",
    response_description="Service health information",
    tags=["Health"],
)
async def health_check(request: Request) -> JSONResponse:
    retriever = request.app.state.retriever
    vector_store_loaded = retriever is not None and retriever.is_loaded
    return JSONResponse(
        content={
            "status": "ok",
            "vector_store_loaded": vector_store_loaded,
        }
    )


# ---------------------------------------------------------------------- #
# POST /api/query
# ---------------------------------------------------------------------- #

@router.post(
    "/api/query",
    response_model=QueryResponse,
    summary="Query the documentation",
    description=(
        "Submit a natural-language question. "
        "The service retrieves relevant policy documentation chunks via FAISS, "
        "applies a similarity threshold filter, and generates a strictly grounded "
        "answer using Gemini 2.5 Flash. "
        "If the documentation does not contain relevant information, the deterministic "
        "fallback message is returned without calling the LLM."
    ),
    responses={
        200: {
            "description": "Grounded answer with source attribution",
            "model": QueryResponse,
        },
        422: {
            "description": "Invalid request — question is empty, too long, or missing",
            "model": ErrorResponse,
        },
        503: {
            "description": "Service unavailable — FAISS index not built or API error",
            "model": ErrorResponse,
        },
    },
    tags=["Query"],
)
async def query_endpoint(
    request_body: QueryRequest,
    retriever: FAISSRetriever = Depends(_get_retriever),
) -> QueryResponse:
    """
    POST /api/query

    Accepts a JSON body with a `question` field (1–2000 characters).
    Returns a grounded answer, source chunks, and token usage.
    """
    rag_service = RAGService(retriever=retriever)

    try:
        response = rag_service.answer(question=request_body.question)
    except IndexNotFoundError as exc:
        logger.error("FAISS index not found: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "FAISS index not found. Build the index first:\n\n"
                "    python -m app.ingestion.indexer"
            ),
        )
    except EmbeddingError as exc:
        logger.error("Embedding error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Failed to generate query embedding. "
                "Check your OPENAI_API_KEY and try again."
            ),
        )
    except GenerationError as exc:
        logger.error("Gemini generation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Failed to generate an answer from the LLM. "
                "Check your GOOGLE_API_KEY and try again."
            ),
        )
    except Exception as exc:
        # Catch-all: log the real error, return a generic message
        logger.exception("Unexpected error processing query: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred. Please try again.",
        )

    return response
