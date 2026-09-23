"""
Application configuration via Pydantic Settings.

All settings are read from environment variables (with .env file support).
No secrets are hard-coded here.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    DocuSense application settings.

    Values are read from environment variables or a .env file.
    See .env.example for the full list of configurable options.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Google Gemini — LLM generation
    # ------------------------------------------------------------------ #
    google_api_key: str = Field(default="", description="Google Gemini API key")
    llm_model: str = Field(default="gemini-2.5-flash", description="Gemini model name")

    # ------------------------------------------------------------------ #
    # HuggingFace — Embeddings only
    # ------------------------------------------------------------------ #
    openai_api_key: str = Field(default="", description="OpenAI API key for embeddings")
    embedding_model: str = Field(
        default="paraphrase-mpnet-base-v2",
        description="HuggingFace embedding model name",
    )

    # ------------------------------------------------------------------ #
    # RAG parameters
    # ------------------------------------------------------------------ #
    chunk_size: int = Field(default=800, description="Characters per text chunk", ge=100)
    chunk_overlap: int = Field(
        default=100, description="Overlap characters between consecutive chunks", ge=0
    )
    top_k: int = Field(default=4, description="Number of FAISS candidates to retrieve", ge=1)
    similarity_threshold: float = Field(
        default=0.70,
        description="Minimum cosine similarity score for a chunk to be used [0.0–1.0]",
        ge=0.0,
        le=1.0,
    )
    source_snippet_length: int = Field(
        default=300,
        description="Maximum characters shown per source text snippet in the API response",
        ge=50,
    )

    # ------------------------------------------------------------------ #
    # Storage paths
    # ------------------------------------------------------------------ #
    faiss_index_path: str = Field(
        default="storage/faiss", description="Directory where the FAISS index is persisted"
    )
    document_path: str = Field(
        default="data/policy.md", description="Path to the source policy document"
    )

    # ------------------------------------------------------------------ #
    # API server
    # ------------------------------------------------------------------ #
    app_host: str = Field(default="0.0.0.0", description="Uvicorn bind host")
    app_port: int = Field(default=8000, description="Uvicorn bind port", ge=1, le=65535)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    @field_validator("chunk_overlap")
    @classmethod
    def overlap_must_be_less_than_size(cls, v: int, info: object) -> int:
        # Access chunk_size from the model data if available
        data = getattr(info, "data", {})
        chunk_size = data.get("chunk_size", 800)
        if v >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({v}) must be less than chunk_size ({chunk_size})"
            )
        return v


# Singleton settings instance — import this throughout the application.
settings = Settings()
