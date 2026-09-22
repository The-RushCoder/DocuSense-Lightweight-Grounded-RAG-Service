"""
Embedding model factory for DocuSense.

Temporarily uses HuggingFaceEmbeddings ("all-MiniLM-L6-v2") instead of OpenAI
to bypass the credit limit on the provided API key.
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
    chosen_model = model or "all-MiniLM-L6-v2"
    logger.info("Initialising embedding model: %s", chosen_model)

    return HuggingFaceEmbeddings(model_name=chosen_model)
