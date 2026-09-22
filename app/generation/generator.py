"""
Gemini 2.5 Flash LLM integration for DocuSense.

Handles:
  - Configuring ChatGoogleGenerativeAI via langchain-google-genai
  - Sending grounded prompts to Gemini
  - Extracting token usage from response metadata
  - Handling API errors, timeouts, and empty responses

NOTE: Gemini is used ONLY for text generation.
      OpenAI (see embedder.py) is used ONLY for embeddings.
      These two responsibilities are intentionally kept separate.
"""

from __future__ import annotations

import logging
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.generation.prompt import FALLBACK_MESSAGE, build_prompt

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """Raised when the Gemini API call fails or returns an unusable response."""


def _extract_tokens(ai_message: object) -> Optional[int]:
    """
    Extract total token usage from a Gemini AIMessage.

    LangChain's ChatGoogleGenerativeAI populates response_metadata with
    a 'usage_metadata' dict when available.  The structure is:
        ai_message.usage_metadata = {
            "input_tokens": int,
            "output_tokens": int,
            "total_tokens": int,
        }

    If this metadata is absent (e.g. streaming, API version differences),
    we return None — token counts are never fabricated.
    """
    # Try the standard LangChain usage_metadata attribute first
    usage = getattr(ai_message, "usage_metadata", None)
    if isinstance(usage, dict):
        total = usage.get("total_tokens") or (
            (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0)
        )
        if total:
            return int(total)

    # Fallback: check response_metadata
    response_meta = getattr(ai_message, "response_metadata", None)
    if isinstance(response_meta, dict):
        usage_meta = response_meta.get("usage_metadata", {})
        if isinstance(usage_meta, dict):
            total = usage_meta.get("total_token_count") or (
                (usage_meta.get("prompt_token_count") or 0)
                + (usage_meta.get("candidates_token_count") or 0)
            )
            if total:
                return int(total)

    return None  # Token metadata not available — return null, not a guess


def generate_answer(
    context: str,
    question: str,
    llm: ChatGoogleGenerativeAI | None = None,
) -> tuple[str, Optional[int]]:
    """
    Generate a grounded answer using Gemini 2.5 Flash.

    Args:
        context: Concatenated retrieved document chunks.
        question: The user's question (already validated by the API layer).
        llm: Optional pre-built LLM instance (used for dependency injection
             in tests). If None, a default instance is created.

    Returns:
        A tuple of (answer_text, tokens_used).
        tokens_used is None if token metadata was not available.

    Raises:
        GenerationError: If the API call fails or returns an empty response.
    """
    if llm is None:
        if not settings.google_api_key or settings.google_api_key.startswith("your_"):
            raise GenerationError(
                "GOOGLE_API_KEY is not set. "
                "Copy .env.example to .env and provide a valid Google API key."
            )
        llm = ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,  # type: ignore[arg-type]
            temperature=0,      # deterministic — we want grounded answers, not creative ones
            max_retries=2,
        )

    prompt_text = build_prompt(context=context, question=question)

    try:
        response = llm.invoke([HumanMessage(content=prompt_text)])
    except Exception as exc:
        # Surface API errors (rate limits, network issues, auth failures)
        # as a controlled GenerationError rather than leaking internals.
        logger.error("Gemini API call failed: %s", exc)
        raise GenerationError(
            f"Gemini API request failed: {type(exc).__name__}. "
            "Please try again later."
        ) from exc

    # Validate the response content
    answer_text: str = getattr(response, "content", "") or ""
    answer_text = answer_text.strip()

    if not answer_text:
        logger.warning("Gemini returned an empty response")
        raise GenerationError(
            "Gemini returned an empty response. Please try again."
        )

    tokens_used = _extract_tokens(response)

    logger.info(
        "Gemini response: %d chars, tokens_used=%s",
        len(answer_text),
        tokens_used,
    )

    return answer_text, tokens_used
