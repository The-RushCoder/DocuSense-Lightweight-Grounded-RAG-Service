"""
Pydantic schemas for the DocuSense API.

Defines request/response models with validation and OpenAPI examples.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ------------------------------------------------------------------ #
# Request
# ------------------------------------------------------------------ #

class QueryRequest(BaseModel):
    """Request body for POST /api/query."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The question to answer using the policy documentation.",
        examples=["How often should production databases be backed up?"],
    )

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be empty or only whitespace")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"question": "How often should production databases be backed up?"}
            ]
        }
    }


# ------------------------------------------------------------------ #
# Response components
# ------------------------------------------------------------------ #

class SourceChunk(BaseModel):
    """A single retrieved source chunk included in the response."""

    chunk_id: str = Field(
        ...,
        description="Deterministic identifier for this chunk (e.g. 'chunk_004').",
        examples=["chunk_004"],
    )
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Cosine similarity between the query embedding and the chunk embedding. "
            "Scores are in [0.0, 1.0]. This is a geometric similarity measure, "
            "not a probability or confidence percentage."
        ),
        examples=[0.89],
    )
    text_snippet: str = Field(
        ...,
        description="Truncated excerpt from the source chunk (up to SOURCE_SNIPPET_LENGTH chars).",
        examples=["...all primary database backups are retained for 30 calendar days..."],
    )


# ------------------------------------------------------------------ #
# Response
# ------------------------------------------------------------------ #

class QueryResponse(BaseModel):
    """Response body for POST /api/query."""

    answer: str = Field(
        ...,
        description=(
            "Grounded answer derived exclusively from retrieved documentation context. "
            "Returns the exact fallback message when no relevant context is found."
        ),
        examples=["Database backups must be retained for a rolling period of 30 days."],
    )
    sources: list[SourceChunk] = Field(
        default_factory=list,
        description=(
            "Source chunks used to generate the answer, sorted by similarity score descending. "
            "Empty when the fallback message is returned."
        ),
    )
    tokens_used: Optional[int] = Field(
        default=None,
        description=(
            "Total tokens consumed by the Gemini API call (prompt + completion). "
            "Null when token metadata is unavailable or when Gemini was not called "
            "(e.g. fallback path). Never fabricated."
        ),
        examples=[164],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": "Database backups must be retained for a rolling period of 30 calendar days.",
                    "sources": [
                        {
                            "chunk_id": "chunk_004",
                            "similarity_score": 0.89,
                            "text_snippet": "...all primary database backups are retained for 30 calendar days...",
                        }
                    ],
                    "tokens_used": 164,
                }
            ]
        }
    }


# ------------------------------------------------------------------ #
# Error response
# ------------------------------------------------------------------ #

class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str = Field(..., description="Human-readable error description.")

    model_config = {
        "json_schema_extra": {
            "examples": [{"detail": "FAISS index not found. Run: python -m app.ingestion.indexer"}]
        }
    }
