"""
Indexer CLI entry point for DocuSense.

Usage:
    python -m app.ingestion.indexer

This command:
    1. Loads the policy document
    2. Chunks the document
    3. Generates HuggingFace embeddings
    4. Creates a FAISS index (IndexFlatIP on L2-normalised vectors)
    5. Saves the index to storage/faiss/
    6. Prints useful statistics

Do NOT use this command to rebuild the index at API startup.
The FastAPI application loads the pre-built index.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np

from app.core.config import settings
from app.embeddings.embedder import get_embeddings
from app.ingestion.chunker import chunk_documents
from app.ingestion.loader import DocumentLoadError, load_document

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _validate_api_keys() -> None:
    """Fail fast with a clear message if required API keys are missing."""
    if not settings.google_api_key or settings.google_api_key.startswith("your_"):
        print(
            "\n[ERROR] GOOGLE_API_KEY is not set.\n"
            "        Copy .env.example to .env and fill in your Google API key.\n",
            file=sys.stderr,
        )
        sys.exit(1)


def build_index() -> None:
    """Orchestrate the full document indexing pipeline."""

    # ------------------------------------------------------------------ #
    # 0. Pre-flight checks
    # ------------------------------------------------------------------ #
    _validate_api_keys()

    # ------------------------------------------------------------------ #
    # 1. Load document
    # ------------------------------------------------------------------ #
    print("Loading document...")
    try:
        documents = load_document()
    except DocumentLoadError as exc:
        print(f"\n[ERROR] {exc}\n", file=sys.stderr)
        sys.exit(1)
    print("Document loaded successfully.\n")

    # ------------------------------------------------------------------ #
    # 2. Chunk document
    # ------------------------------------------------------------------ #
    chunks = chunk_documents(documents)
    print(f"Chunks created:     {len(chunks)}")
    print(f"Chunk size:         {settings.chunk_size} characters")
    print(f"Chunk overlap:      {settings.chunk_overlap} characters")

    # ------------------------------------------------------------------ #
    # 3. Generate embeddings
    # ------------------------------------------------------------------ #
    print(f"\nEmbedding model:    {settings.embedding_model}")
    print("Generating embeddings (this uses HuggingFace)...")

    embeddings_model = get_embeddings()
    texts = [chunk.page_content for chunk in chunks]

    try:
        vectors = embeddings_model.embed_documents(texts)
    except Exception as exc:
        print(f"\n[ERROR] Embedding generation failed: {exc}\n", file=sys.stderr)
        sys.exit(1)

    print(f"Embeddings generated: {len(vectors)} vectors of dimension {len(vectors[0])}")

    # ------------------------------------------------------------------ #
    # 4. Build FAISS index
    #    We use IndexFlatIP (inner product) on L2-normalised vectors.
    #    For unit vectors: inner_product = cosine_similarity ∈ [-1, 1].
    #    This gives us true cosine similarity without approximation.
    # ------------------------------------------------------------------ #
    try:
        import faiss  # noqa: PLC0415
    except ImportError:
        print(
            "\n[ERROR] faiss-cpu is not installed. Run: pip install faiss-cpu\n",
            file=sys.stderr,
        )
        sys.exit(1)

    matrix = np.array(vectors, dtype=np.float32)
    faiss.normalize_L2(matrix)  # in-place L2 normalisation

    dimension = matrix.shape[1]
    index = faiss.IndexFlatIP(dimension)  # exact inner product (= cosine on unit vectors)
    index.add(matrix)

    print(f"Vector store:       FAISS (IndexFlatIP, dimension={dimension})")
    print(f"Vectors indexed:    {index.ntotal}")

    # ------------------------------------------------------------------ #
    # 5. Save FAISS index + metadata
    #    We persist two files:
    #      index.faiss — the raw FAISS binary index
    #      index.pkl   — chunk metadata (IDs, text, source) via LangChain helper
    #    We use the LangChain FAISS wrapper for consistent load/save.
    # ------------------------------------------------------------------ #
    # Build a LangChain FAISS object from our pre-built index and chunks.
    from langchain_community.vectorstores import FAISS  # noqa: PLC0415
    from langchain_community.docstore.in_memory import InMemoryDocstore  # noqa: PLC0415

    # Map from FAISS index position → chunk document
    index_to_docstore_id: dict[int, str] = {
        i: chunk.metadata["chunk_id"] for i, chunk in enumerate(chunks)
    }
    docstore_dict: dict[str, object] = {
        chunk.metadata["chunk_id"]: chunk for chunk in chunks
    }
    docstore = InMemoryDocstore(docstore_dict)

    vector_store = FAISS(
        embedding_function=embeddings_model,
        index=index,
        docstore=docstore,
        index_to_docstore_id=index_to_docstore_id,
    )

    output_path = Path(settings.faiss_index_path)
    output_path.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(output_path))

    print(f"\nIndex saved to:     {output_path}")
    print("\nIndexing completed successfully.")


if __name__ == "__main__":
    build_index()
