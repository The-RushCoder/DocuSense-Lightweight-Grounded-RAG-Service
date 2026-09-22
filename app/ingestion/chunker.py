"""
Text chunking for DocuSense.

Uses RecursiveCharacterTextSplitter from LangChain with configurable
chunk_size and chunk_overlap.  Each chunk receives deterministic metadata.

Design rationale
----------------
chunk_size = 800 characters
    * At ~4 chars/token this corresponds to roughly 200 tokens per chunk.
    * Small enough to keep retrieval granular (a single policy clause
      rather than an entire section), but large enough to contain a
      coherent, self-contained policy statement.
    * Avoids context windows that are too narrow to answer questions
      about multi-sentence policies.

chunk_overlap = 100 characters
    * Prevents answers that span a chunk boundary from being missed.
    * Chosen as ~12.5% of chunk_size — a practical balance between
      retrieval coverage and index size.
    * Higher overlap increases index size and embedding API cost; lower
      overlap risks splitting sentences at retrieval boundaries.

These values are intentional starting points for this take-home
configuration, not universally optimal numbers.  They should be tuned
empirically for production workloads using recall evaluation.
"""

from __future__ import annotations

import logging
from typing import Sequence

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

logger = logging.getLogger(__name__)


def chunk_documents(
    documents: Sequence[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    """
    Split documents into overlapping text chunks.

    Assigns deterministic chunk IDs (chunk_001, chunk_002, …) based on
    position in the resulting list.  The same document with the same
    configuration always produces the same IDs.

    Each output Document carries the following metadata:
        chunk_id     — zero-padded sequential ID, e.g. "chunk_001"
        source       — inherited from the parent document
        chunk_index  — integer index (0-based) within the full chunk list

    Args:
        documents: LangChain Documents to split (typically from the loader).
        chunk_size: Characters per chunk (defaults to settings.chunk_size).
        chunk_overlap: Overlap characters (defaults to settings.chunk_overlap).

    Returns:
        List of chunked LangChain Documents with enriched metadata.
    """
    size = chunk_size if chunk_size is not None else settings.chunk_size
    overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        length_function=len,
        # These separators try to break at section/paragraph/sentence
        # boundaries before resorting to character splitting.
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
    )

    raw_chunks = splitter.split_documents(list(documents))

    chunks: list[Document] = []
    for idx, chunk in enumerate(raw_chunks):
        chunk_id = f"chunk_{idx + 1:03d}"  # chunk_001, chunk_002, …
        enriched_metadata = {
            **chunk.metadata,
            "chunk_id": chunk_id,
            "chunk_index": idx,
        }
        chunks.append(
            Document(
                page_content=chunk.page_content,
                metadata=enriched_metadata,
            )
        )

    logger.info(
        "Created %d chunks (size=%d, overlap=%d)", len(chunks), size, overlap
    )
    return chunks
