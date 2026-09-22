"""
Document loader for DocuSense.

Loads the policy document from disk and returns LangChain Documents
with source metadata preserved.  Document loading is intentionally
kept separate from API routing and chunking logic.
"""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.documents import Document

from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentLoadError(Exception):
    """Raised when the source document cannot be loaded."""


def load_document(document_path: str | None = None) -> list[Document]:
    """
    Load the policy Markdown document from disk.

    Args:
        document_path: Override path to the document file.
                       Defaults to settings.document_path.

    Returns:
        A list containing a single LangChain Document with
        'source' metadata set to the resolved file path.

    Raises:
        DocumentLoadError: If the file does not exist or cannot be read.
    """
    path = Path(document_path or settings.document_path)

    if not path.exists():
        raise DocumentLoadError(
            f"Document not found at '{path}'. "
            "Ensure the file exists before running the indexer."
        )

    if not path.is_file():
        raise DocumentLoadError(f"Path '{path}' is not a file.")

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DocumentLoadError(
            f"Failed to read document '{path}': {exc}"
        ) from exc

    if not content.strip():
        raise DocumentLoadError(
            f"Document at '{path}' is empty. Nothing to index."
        )

    logger.info("Loaded document '%s' (%d characters)", path, len(content))

    return [
        Document(
            page_content=content,
            metadata={"source": str(path)},
        )
    ]
