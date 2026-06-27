# User Intelligence Workspace — Project Rules

## Project Overview
This is a **single-user intelligence workspace** that learns from information over time. It supports Research Mode (autonomous topic research) and Knowledge-Augmented Chat (grounded Q&A with traceability).

## Architecture Rules

### Backend (Python / FastAPI)
- Use **FastAPI** with async endpoints throughout
- Use **Pydantic v2** models for all data schemas — never pass raw dicts between services
- All services must be **dependency-injectable** via FastAPI's `Depends()`
- Use **structured logging** (JSON format) with `structlog`
- Every LLM call must log: prompt tokens, completion tokens, latency, model name, and estimated cost
- All knowledge mutations must create an **audit trail** (who/what/when/why)
- All list endpoints must support **pagination** (`?page=1&limit=20`)
- All requests must carry a **correlation ID** for tracing

### Streaming & Real-time
- Research progress MUST stream via **SSE** (`text/event-stream`)
- Chat responses MUST stream token-by-token via **SSE**
- Use `asyncio.Queue` per session for event buffering
- Frontend uses `EventSource` API for SSE consumption

### Knowledge Graph (Neo4j)
- All graph operations go through `graph_service.py` — never write raw Cypher in route handlers
- Node labels: `Entity`, `Fact`, `Evidence`, `Source`, `Decision`, `Question`, `Insight`, `Memory`
- Relationship types are UPPERCASE_SNAKE: `SUPPORTS`, `CONTRADICTS`, `DERIVED_FROM`, `RELATES_TO`, `INFLUENCES`, `DEPENDS_ON`, `INFORMS`, `RAISED_BY`, `ANSWERS`
- Every node must have: `id`, `created_at`, `updated_at`, `status`, `topic` properties
- Knowledge evolution must preserve history — never delete, only deprecate
- Use **batch writes** for pipeline operations (not individual creates)

### Vector Store (Qdrant)
- Collection naming: `{domain}_embeddings` (e.g., `knowledge_embeddings`, `memory_embeddings`)
- Always store `source_id`, `entity_id`, or `fact_id` in payload metadata
- Use cosine similarity for all searches
- Embedding model must be consistent across all operations
- Memories MUST be embedded in a `memory_embeddings` collection for semantic retrieval

### Database (PostgreSQL via Supabase/Neon)
- Use **PostgreSQL** (not SQLite) for all relational data — sessions, conversation history, audit trail, file metadata
- Use **SQLAlchemy async** with `asyncpg` driver
- Alembic for schema migrations
- Connection pooling via SQLAlchemy async engine
- PostgreSQL is the **single source of truth** for session/conversation state
- Neo4j is the **single source of truth** for knowledge structure

### Frontend (Next.js)
- Use **App Router** (not Pages Router)
- Use **Server Components** by default, Client Components only when needed
- API calls to backend go through Next.js API routes (proxy pattern)
- Use **shadcn/ui** components — don't build basic UI from scratch
- All interactive elements must have unique, descriptive IDs
- Chat MUST use `EventSource` for streaming responses
- Research MUST show real-time progress via SSE

### LLM Usage
- All LLM calls go through `llm_service.py` — never call OpenAI/Gemini directly from other services
- Use **structured output** (JSON mode / function calling) for knowledge extraction
- Include **system prompts** that define the knowledge domain context
- Temperature: 0.1 for extraction/analysis, 0.7 for synthesis/insights
- Always include retry logic with exponential backoff
- Track estimated cost per call and per session
- Add **daily budget limit** with circuit breaker

### Document Processing
- All documents MUST be **chunked** before LLM processing
- Chunking strategy: semantic chunking (preferred) or fixed-size (~1000 tokens, 200 token overlap)
- Each chunk becomes an Evidence node linked to its Source
- Never send an entire document to an LLM in one call

## Service Architecture Rules
- **No god objects** — split orchestration by workflow:
  - `ResearchOrchestrator` — autonomous research pipeline
  - `ChatOrchestrator` — chat with query routing
  - `IngestionOrchestrator` — document upload → extraction
- **Query routing** — classify chat intent before retrieval:
  - `factual` → vector search + graph facts
  - `relational` → graph traversal (neighborhood, paths)
  - `contradictions` → graph CONTRADICTS edges
  - `exploratory` → broad graph + vector search
  - `comparative` → multi-entity graph queries

## Exception Hierarchy
```python
class AppError(Exception):
    """Base application error."""
    def __init__(self, message: str, details: dict = None): ...

class KnowledgeError(AppError): ...
class ExtractionError(KnowledgeError): ...
class ContradictionError(KnowledgeError): ...
class EntityResolutionError(KnowledgeError): ...

class MemoryError(AppError): ...
class EvolutionError(MemoryError): ...

class IngestionError(AppError): ...
class UnsupportedFormatError(IngestionError): ...
class FileTooLargeError(IngestionError): ...

class LLMError(AppError): ...
class RateLimitError(LLMError): ...
class ContextLengthError(LLMError): ...
class BudgetExceededError(LLMError): ...

class GraphError(AppError): ...
class VectorError(AppError): ...
class DatabaseError(AppError): ...
```

## Code Quality Rules
- Type hints on all function signatures
- Docstrings on all public functions (Google style)
- No hardcoded API keys — use environment variables via `.env`
- Error handling: raise domain-specific exceptions (see hierarchy above)
- No `print()` statements — use the logger
- All API responses use structured error format: `{"error": {"code": str, "message": str, "details": dict}}`

## Knowledge Quality Rules
- Every fact must link to at least one evidence
- Every evidence must link to exactly one source
- Confidence scores are floats [0.0, 1.0]
- Confidence deltas are **weighted by source quality**: `delta = base_delta * source.quality_score`
- Source quality scores consider: recency, authority, corroboration
- Contradictions must be explicitly surfaced, never silently overwritten
- All knowledge nodes must have a `topic` property for domain scoping

## Testing Rules
- Unit tests for all service methods
- Integration tests for Neo4j queries using a test database
- API tests using FastAPI TestClient
- Test files follow `test_{module}.py` naming
