"""
DocuSense FastAPI application factory.

Startup behaviour:
  - Loads the pre-built FAISS index from storage/faiss/
  - Attaches the retriever to app.state for use by route handlers
  - Does NOT rebuild the index on startup
  - Fails clearly if the index is missing, instructing the user to run the indexer

Endpoints registered:
  GET  /health
  POST /api/query
  GET  /docs        (Swagger UI — FastAPI built-in)
  GET  /redoc       (ReDoc — FastAPI built-in)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.retrieval.retriever import FAISSRetriever, IndexNotFoundError, get_retriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    On startup:
      - Loads the FAISS index into memory.
      - Sets app.state.retriever for use by dependency injection.
      - If the index is missing, sets retriever to None so the /health
        endpoint can report vector_store_loaded=False and /api/query
        returns a clear 503.

    On shutdown:
      - Nothing to clean up (FAISS index is in-memory).
    """
    logger.info("DocuSense starting up…")
    retriever = get_retriever()

    try:
        retriever.load()
        logger.info("FAISS index loaded successfully.")
    except IndexNotFoundError as exc:
        logger.error(
            "\n\n"
            "=================================================================\n"
            "  FAISS index not found. The API will start but queries will\n"
            "  return errors until the index is built.\n"
            "\n"
            "  Build the index first:\n"
            "      python -m app.ingestion.indexer\n"
            "=================================================================\n"
        )
        # We allow the server to start so /health can report the problem,
        # rather than refusing to start and hiding the error.
        retriever = None  # type: ignore[assignment]

    application.state.retriever = retriever
    logger.info("DocuSense is ready.")

    yield  # Application runs here

    logger.info("DocuSense shutting down.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="DocuSense",
        description=(
            "## Lightweight Grounded RAG Service\n\n"
            "DocuSense answers questions using **only** the content of indexed "
            "internal policy documentation. Answers are strictly grounded — the "
            "system will never fabricate information not found in the documents.\n\n"
            "### Key properties\n"
            "- **Grounded answers**: Gemini 2.5 Flash responds only to retrieved context\n"
            "- **Deterministic fallback**: If no relevant chunks exceed the similarity "
            "threshold, the exact fallback message is returned without calling the LLM\n"
            "- **Source attribution**: Every answer includes the source chunks used\n"
            "- **Prompt injection protection**: Retrieved document text is treated as "
            "untrusted data — instructions inside documents are never executed\n\n"
            "### Embeddings\n"
            "Query and document embeddings use `text-embedding-3-small` (OpenAI). "
            "The same model is used for both indexing and retrieval.\n\n"
            "### Vector store\n"
            "FAISS `IndexFlatIP` with L2-normalised embeddings gives exact cosine "
            "similarity scores in `[0.0, 1.0]`."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — permissive for a local development take-home.
    # Tighten allowed_origins in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )

    app.include_router(router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
