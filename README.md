# DocuSense

DocuSense is a small, grounded RAG API for answering questions from the
internal policy document at `data/policy.md`. It retrieves relevant passages
with FAISS and asks Gemini 2.5 Flash to answer only from those passages.

If no retrieved passage reaches the configured similarity threshold, the
service returns a deterministic fallback and does not call Gemini.

## Stack and design choices

- **FastAPI + Uvicorn**: typed REST API with automatic OpenAPI documentation.
- **BAAI/bge-small-en-v1.5**: free local 384-dimensional embeddings; no embedding API key or GPU is required.
- **FAISS `IndexFlatIP`**: persistent, exact in-process vector search. L2-normalized vectors make inner product represent cosine similarity.
- **Gemini 2.5 Flash**: fast hosted generation with strong instruction following; used only after retrieval passes the guardrail.
- **Pydantic Settings**: validates configuration loaded from `.env`.
- **Docker Compose**: repeatable API execution and persistent index storage.

## RAG configuration

These values are intentionally kept unchanged:

| Variable | Value | Purpose |
|---|---:|---|
| `CHUNK_SIZE` | `600` | Characters per document chunk |
| `CHUNK_OVERLAP` | `75` | Shared characters between chunks |
| `TOP_K` | `3` | FAISS candidates retrieved per query |
| `SIMILARITY_THRESHOLD` | `0.70` | Minimum cosine similarity to keep a chunk |
| `SOURCE_SNIPPET_LENGTH` | `300` | Maximum source excerpt length in responses |

The production setting is `SIMILARITY_THRESHOLD=0.70` and `TOP_K=3`. Some unit
tests pass `similarity_threshold=0.75` explicitly to test threshold filtering;
that does not change the application configuration.

`600/75` keeps enough local context while limiting prompt size. `TOP_K=3`
provides a small, focused context window, and the threshold prevents weak
matches from reaching the LLM.

## Project structure

```text
app/
  api/routes.py                 FastAPI endpoints
  core/config.py                Environment-backed settings
  ingestion/                    Load, chunk, and index policy text
  embeddings/embedder.py       Local HuggingFace embeddings
  retrieval/retriever.py       FAISS search and threshold filtering
  generation/                   Gemini client and grounded prompt
  services/rag_service.py      RAG orchestration and fallback guardrail
  schemas/query.py              Request and response models
data/policy.md                  Source documentation
storage/faiss/                  Generated FAISS index
tests/                           Unit and API tests
```

## Requirements

- Python 3.11+
- pip
- A Google Gemini API key: <https://aistudio.google.com/app/apikey>
- Docker Desktop, optional

## Installation: PowerShell

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and replace:

```dotenv
GOOGLE_API_KEY=your_google_api_key_here
```

Build the local FAISS index, then start the API:

```powershell
python -m app.ingestion.indexer
uvicorn app.main:app --reload
```

The API is available at <http://localhost:8000> and interactive docs are at
<http://localhost:8000/docs>.

## Installation: Docker

```powershell
Copy-Item .env.example .env
```

Set `GOOGLE_API_KEY` in `.env`, then run:

```powershell
docker compose run --rm docusense python -m app.ingestion.indexer
docker compose up --build
```

The index is persisted in `storage/faiss` and the policy is mounted from
`data/`.

## API usage

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Query from PowerShell:

```powershell
Invoke-RestMethod `
  -Uri http://localhost:8000/api/query `
  -Method Post `
  -ContentType 'application/json' `
  -Body '{"question":"How often should production databases be backed up?"}'
```

The response contains `answer`, retrieved `sources`, and `tokens_used` when
Gemini provides token metadata.

### Evaluation queries

In-scope, high-confidence retrieval:

```text
How often should production databases be backed up?
```

Out-of-scope fallback test:

```text
What is the company's vacation policy?
```

The second question is not answered from general knowledge. It should return
the configured fallback with no source chunks and no Gemini call when no policy
chunk passes the threshold.

## Guardrails and reliability

1. Request validation rejects blank questions and limits them to 2,000 chars.
2. FAISS results are normalized to cosine similarity in `[0.0, 1.0]`.
3. Results below `SIMILARITY_THRESHOLD` are removed before generation.
4. The grounded prompt instructs Gemini to use only supplied context.
5. If no chunk passes, `RAGService` returns the fallback without calling Gemini.
6. Responses include source chunk IDs, scores, and bounded text snippets.

This design prioritizes predictable answers over an ungrounded chat interface.

## Testing

Run the complete test suite:

```powershell
pytest
```

Tests cover chunking, metadata, FAISS retrieval and sorting, score clamping,
threshold filtering, out-of-scope fallback behavior, prompt-injection
resistance, API validation, and missing-index errors. Tests mock external LLM
calls, so a Gemini key is not required to run them.

## Evaluation matrix

| Area | Evidence | Weight |
|---|---|---:|
| RAG architecture | Chunking, embeddings, FAISS retrieval, threshold, grounded prompt | 30% |
| Guardrails and reliability | Deterministic fallback, validation, source attribution, tests | 25% |
| Code quality and structure | Separate ingestion, indexing, retrieval, generation, and API layers | 25% |
| Efficiency and developer experience | Short README, `.env.example`, token awareness, Docker Compose | 20% |

## Submission checklist

- Push the repository to GitHub or GitLab.
- Include `.env.example`, never a real `.env` or API key.
- Include the test suite and the two evaluation queries above.
- Explain the chunking and embedding choices in the repository README.
- Verify both local PowerShell and Docker startup paths.

## Security note

Never commit a real Google API key. The working `.env` shown during setup
contains a key-shaped value; rotate that key in Google AI Studio immediately,
replace it with a new key locally, and keep `.env` ignored by Git.
