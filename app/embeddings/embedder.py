"""
Embedding model factory for DocuSense.

Uses HuggingFaceEmbeddings ("BAAI/bge-small-en-v1.5") for local, free embeddings.
"""

from __future__ import annotations

import logging

from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


def get_embeddings(
    model: str | None = None,
    api_key: str | None = None,
) -> HuggingFaceEmbeddings:
    """
    Build and return a configured HuggingFaceEmbeddings instance.
    """
    chosen_model = model or "BAAI/bge-small-en-v1.5"
    logger.info("Initialising embedding model: %s", chosen_model)

    return HuggingFaceEmbeddings(
        model_name=chosen_model,
        encode_kwargs={'normalize_embeddings': True}
    )
