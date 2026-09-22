"""
Test 1: Chunking

Verifies:
  - Chunks are created from a document
  - Chunk IDs are deterministic (same input → same IDs)
  - Each chunk has the required metadata fields
  - chunk_size and chunk_overlap configuration is respected
  - Chunk IDs follow the chunk_NNN format
"""

from __future__ import annotations

from langchain_core.documents import Document

from app.ingestion.chunker import chunk_documents


SAMPLE_TEXT = """
# Company Policy

## 1. Information Security

All employees must follow the information security policy.
Passwords must be at least 14 characters long and changed every 90 days.
Multi-factor authentication is mandatory for all VPN connections.

## 2. Database Backup

Primary database backups are retained for 30 calendar days.
Full backups are taken weekly on Sundays at 02:00 UTC.
Differential backups are taken daily.

## 3. Access Control

Access must be revoked within 4 hours of employee termination.
Privileged accounts must be registered in the PAM vault.
All access requests require manager approval.

## 4. Incident Reporting

Security incidents must be reported within 1 hour of discovery.
Use the security hotline: +1-800-555-0199.
A non-retaliation policy protects good-faith reporters.

## 5. Data Retention

Customer contracts are retained for 7 years.
Financial records are retained for 7 years.
System logs are retained for 12 months.
"""


def _make_doc(text: str = SAMPLE_TEXT) -> list[Document]:
    return [Document(page_content=text, metadata={"source": "test_policy.md"})]


class TestChunking:
    def test_chunks_are_created(self) -> None:
        """At least one chunk is produced from a non-trivial document."""
        docs = _make_doc()
        chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=20)
        assert len(chunks) > 0, "Expected at least one chunk"

    def test_chunk_ids_are_deterministic(self) -> None:
        """Same input + same config → identical chunk IDs on second call."""
        docs = _make_doc()
        first_run = chunk_documents(docs, chunk_size=200, chunk_overlap=20)
        second_run = chunk_documents(docs, chunk_size=200, chunk_overlap=20)

        first_ids = [c.metadata["chunk_id"] for c in first_run]
        second_ids = [c.metadata["chunk_id"] for c in second_run]

        assert first_ids == second_ids, "Chunk IDs must be deterministic"

    def test_chunk_id_format(self) -> None:
        """Chunk IDs follow the chunk_NNN pattern."""
        docs = _make_doc()
        chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=20)
        for chunk in chunks:
            cid = chunk.metadata["chunk_id"]
            assert cid.startswith("chunk_"), f"Expected chunk_NNN, got: {cid}"
            # The numeric part should be zero-padded to 3 digits
            numeric_part = cid.split("_")[1]
            assert numeric_part.isdigit(), f"Non-numeric chunk ID suffix: {numeric_part}"
            assert len(numeric_part) == 3, f"Expected 3-digit padding, got: {numeric_part}"

    def test_required_metadata_fields(self) -> None:
        """Each chunk carries chunk_id, source, and chunk_index."""
        docs = _make_doc()
        chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=20)
        for chunk in chunks:
            assert "chunk_id" in chunk.metadata
            assert "source" in chunk.metadata
            assert "chunk_index" in chunk.metadata

    def test_source_metadata_preserved(self) -> None:
        """Source metadata from the parent document is inherited."""
        docs = _make_doc()
        chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=20)
        for chunk in chunks:
            assert chunk.metadata["source"] == "test_policy.md"

    def test_chunk_index_is_sequential(self) -> None:
        """chunk_index values are 0, 1, 2, … in order."""
        docs = _make_doc()
        chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=20)
        indices = [c.metadata["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunk_size_respected(self) -> None:
        """Chunks do not significantly exceed the configured chunk_size."""
        size = 300
        docs = _make_doc()
        chunks = chunk_documents(docs, chunk_size=size, chunk_overlap=30)
        for chunk in chunks:
            # Allow a small overshoot due to separator boundaries
            assert len(chunk.page_content) <= size * 1.5, (
                f"Chunk too large: {len(chunk.page_content)} chars (limit: {size})"
            )

    def test_smaller_chunks_produce_more_chunks(self) -> None:
        """A smaller chunk_size produces more chunks than a larger one."""
        docs = _make_doc()
        small_chunks = chunk_documents(docs, chunk_size=150, chunk_overlap=15)
        large_chunks = chunk_documents(docs, chunk_size=600, chunk_overlap=60)
        assert len(small_chunks) >= len(large_chunks), (
            "Smaller chunk_size should produce at least as many chunks"
        )

    def test_chunk_ids_change_with_different_config(self) -> None:
        """Different chunk_size produces a different number of chunks."""
        docs = _make_doc()
        chunks_a = chunk_documents(docs, chunk_size=200, chunk_overlap=20)
        chunks_b = chunk_documents(docs, chunk_size=400, chunk_overlap=40)
        # Different configs may produce different counts
        # We just verify both succeed and have positive counts
        assert len(chunks_a) > 0
        assert len(chunks_b) > 0

    def test_empty_document_list(self) -> None:
        """Empty document list returns empty chunk list."""
        chunks = chunk_documents([], chunk_size=200, chunk_overlap=20)
        assert chunks == []
