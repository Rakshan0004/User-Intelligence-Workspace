---
name: research-pipeline
description: Autonomous research workflow orchestration for the User Intelligence Workspace. Covers topic decomposition, web search strategies, source gathering, noise filtering, knowledge extraction with document chunking, graph construction, memory updates, synthesis generation, and real-time progress streaming via SSE.
---

# Research Pipeline Skill

## Overview
The research pipeline is the autonomous backbone of Workflow 1 (Research Mode). Given a topic, the system independently determines what to process, what to ignore, what to extract, what to remember, and what to surface — streaming progress to the frontend in real-time via SSE.

## Pipeline Architecture

```
Topic Input
    │
    ▼
┌─────────────────────┐
│ Topic Decomposition  │  → Break topic into sub-topics & research questions
└─────────┬───────────┘   → Stream: STAGE_UPDATE event
          │
          ▼
┌─────────────────────┐
│   Web Search Agent   │  → Search multiple angles per sub-topic
└─────────┬───────────┘   → Stream: SOURCE_FOUND events
          │
          ▼
┌─────────────────────┐
│   Source Gathering    │  → Fetch, parse, and store raw content
└─────────┬───────────┘   → Stream: SOURCE_PROCESSED events
          │
          ▼
┌─────────────────────┐
│   Noise Filtering    │  → Remove duplicates, low-quality, irrelevant
└─────────┬───────────┘   → Stream: SOURCE_FILTERED events (with reasons)
          │
          ▼
┌─────────────────────┐
│  Document Chunking   │  → Split content into LLM-processable chunks
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Knowledge Extraction │  → Extract entities, facts, relationships per chunk
└─────────┬───────────┘   → Stream: ENTITY_EXTRACTED, FACT_EXTRACTED events
          │
          ▼
┌─────────────────────┐
│  Knowledge Graph     │  → Create/update nodes and edges in Neo4j
│  Construction        │  → Detect contradictions with existing knowledge
└─────────┬───────────┘   → Stream: CONTRADICTION_DETECTED events
          │
          ▼
┌─────────────────────┐
│   Memory Update      │  → Record what was learned, updated, reinforced
└─────────┬───────────┘   → Stream: MEMORY_UPDATED events
          │
          ▼
┌─────────────────────┐
│ Insight Generation   │  → Detect obvious + non-obvious insights
└─────────┬───────────┘   → Stream: INSIGHT_GENERATED events
          │
          ▼
┌─────────────────────┐
│ Synthesis Generation │  → Produce structured research summary
└─────────────────────┘   → Stream: SYNTHESIS_COMPLETE event
```

## Streaming Architecture (SSE)

### Server-Sent Events Design
```python
from fastapi.responses import StreamingResponse
import asyncio
import json

class ResearchEventBus:
    """Per-session event bus for streaming research progress."""
    
    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = {}
    
    def create_session(self, session_id: str) -> None:
        self._queues[session_id] = asyncio.Queue()
    
    async def emit(self, session_id: str, event_type: str, data: dict) -> None:
        """Emit an event to the session's queue."""
        if session_id in self._queues:
            event = {"type": event_type, "data": data, "timestamp": datetime.utcnow().isoformat()}
            await self._queues[session_id].put(event)
    
    async def stream(self, session_id: str):
        """Yield SSE events for a session."""
        queue = self._queues.get(session_id)
        if not queue:
            return
        while True:
            event = await queue.get()
            if event["type"] == "STREAM_END":
                yield f"data: {json.dumps(event)}\n\n"
                break
            yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
    
    def cleanup(self, session_id: str) -> None:
        self._queues.pop(session_id, None)

# FastAPI endpoint
@router.get("/api/research/{session_id}/stream")
async def stream_research_progress(session_id: str):
    return StreamingResponse(
        event_bus.stream(session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )
```

### SSE Event Types
| Event | Payload | When |
|-------|---------|------|
| `STAGE_UPDATE` | `{stage: str, status: str}` | Pipeline stage changes |
| `SOURCE_FOUND` | `{url: str, title: str, relevance: float}` | New source discovered |
| `SOURCE_PROCESSED` | `{source_id: str, title: str, chunks: int}` | Source fetched and chunked |
| `SOURCE_FILTERED` | `{url: str, decision: str, reason: str}` | Source kept or discarded |
| `ENTITY_EXTRACTED` | `{name: str, type: str, is_new: bool}` | Entity found |
| `FACT_EXTRACTED` | `{statement: str, confidence: float}` | Fact extracted |
| `CONTRADICTION_DETECTED` | `{fact_a: str, fact_b: str, explanation: str}` | Contradiction found |
| `MEMORY_UPDATED` | `{type: str, content: str}` | Memory created/evolved |
| `INSIGHT_GENERATED` | `{content: str, type: str, category: str}` | Insight generated |
| `SYNTHESIS_COMPLETE` | `{summary: str}` | Research complete |
| `ERROR` | `{stage: str, message: str}` | Non-fatal error |
| `STREAM_END` | `{}` | Stream finished |

## Step 1: Topic Decomposition

### LLM Prompt Strategy
```
System: You are a research strategist. Given a topic, decompose it into:
1. Core sub-topics (3-5) that cover the topic comprehensively
2. Key research questions (2-3 per sub-topic)
3. Expected entity types to look for
4. Potential relationship types between entities

Output as structured JSON.
```

### Output Schema
```python
class TopicDecomposition(BaseModel):
    topic: str
    sub_topics: list[SubTopic]
    expected_entity_types: list[str]
    expected_relationship_types: list[str]

class SubTopic(BaseModel):
    name: str
    description: str
    research_questions: list[str]
    search_queries: list[str]  # Pre-generated search queries
```

## Step 2: Web Search Agent

### Search Strategy
- Use **Tavily API** (or SerpAPI) for AI-optimized search results
- Generate 2-3 search queries per sub-topic (diverse angles)
- Fetch top 5 results per query
- Deduplicate URLs across queries
- Score sources by relevance before fetching full content

### Rate Limiting
- Max 10 concurrent search requests
- 1-second delay between batches
- Total source cap: 20-30 sources per research session

### Source Scoring (Pre-fetch)
```python
class SourceRelevanceScore(BaseModel):
    url: str
    title: str
    snippet: str
    relevance_score: float   # LLM-assessed 0-1
    expected_quality: str    # "high", "medium", "low"
    decision: str            # "fetch", "skip"
    reason: str              # Why fetch or skip
```

## Step 3: Source Gathering

### Content Extraction
- Use `httpx` for async fetching
- Use `trafilatura` or `BeautifulSoup` for HTML → clean text
- Store raw content metadata in PostgreSQL `uploaded_files` table
- Track: URL, title, content length, fetch timestamp, HTTP status

### Quality Checks
- Minimum content length: 200 characters
- Language detection (skip non-English unless topic requires it)
- Duplicate content detection via MinHash/SimHash

## Step 4: Noise Filtering

### LLM-Powered Noise Assessment
```
System: You are a research quality analyst. Evaluate this content for:
1. Relevance to the topic (0-1)
2. Information density (0-1) - ratio of useful facts to filler
3. Credibility signals (author expertise, citations, data)
4. Duplication - is this content similar to previously processed sources?

Output: Keep/Discard decision with explanation.
```

### Filtering Rules
- Discard if relevance < 0.3
- Discard if information density < 0.2
- Flag duplicates but keep the higher-quality version
- Log all filtering decisions with explanations (for user transparency)
- **Stream each decision** to frontend via `SOURCE_FILTERED` event

## Step 5: Document Chunking (NEW — Critical)

### Why Chunking is Required
LLMs have context window limits. A 50-page PDF (~25,000 tokens) cannot be sent as one prompt. Content MUST be chunked before extraction.

### Chunking Strategy
```python
class ChunkingConfig(BaseModel):
    strategy: Literal["semantic", "fixed"] = "semantic"
    max_chunk_tokens: int = 1000
    overlap_tokens: int = 200
    min_chunk_tokens: int = 100

class ContentChunk(BaseModel):
    content: str
    chunk_index: int
    chunk_total: int
    source_id: str
    token_count: int
    
class DocumentChunker:
    """Splits documents into LLM-processable chunks."""
    
    async def chunk(self, content: str, config: ChunkingConfig = None) -> list[ContentChunk]:
        """
        Semantic chunking (preferred):
        1. Split by natural boundaries (paragraphs, sections, headings)
        2. Merge small paragraphs into chunks up to max_chunk_tokens
        3. Add overlap between adjacent chunks for context continuity
        
        Fixed-size chunking (fallback):
        1. Split into chunks of max_chunk_tokens
        2. Overlap by overlap_tokens
        """
    
    def _split_by_semantic_boundaries(self, content: str) -> list[str]:
        """Split on: double newlines, headings, section breaks."""
    
    def _merge_small_chunks(self, paragraphs: list[str], max_tokens: int) -> list[str]:
        """Merge consecutive small paragraphs up to max_tokens."""
    
    def _add_overlap(self, chunks: list[str], overlap_tokens: int) -> list[str]:
        """Add overlap from previous chunk to start of next chunk."""
```

### Chunking Rules
- Each chunk becomes one or more Evidence nodes in Neo4j
- Each Evidence node stores `chunk_index` and `chunk_total` for reassembly
- The Source node stores `chunk_count` for reference
- Knowledge extraction runs independently on each chunk
- Entity resolution merges entities discovered across chunks of the same source

## Step 6: Knowledge Extraction (per chunk)

### LLM Extraction Prompt
```
System: You are a knowledge extraction engine. From the provided text chunk, extract:

1. ENTITIES: Named concepts, people, organizations, technologies, events, places
   - For each: name, type, description, confidence

2. FACTS: Verifiable claims or statements
   - For each: statement, confidence, supporting_quote

3. RELATIONSHIPS: Connections between entities
   - For each: source_entity, target_entity, type, description, strength

4. DECISIONS: Any decisions, conclusions, or recommendations mentioned
   - For each: statement, context, implications, made_by

5. QUESTIONS: Open questions or unresolved issues in the domain
   - For each: question, context, why_it_matters

Output as structured JSON. Only extract what the text actually states or clearly implies.
Do NOT hallucinate or infer beyond what the evidence supports.
```

### Extraction Output Schema
```python
class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity]
    facts: list[ExtractedFact]
    relationships: list[ExtractedRelationship]
    decisions: list[ExtractedDecision]
    questions: list[ExtractedQuestion]
    source_id: str
    chunk_index: int
    extraction_confidence: float
```

### Entity Resolution
- Before creating new entities, check for existing matches in Neo4j
- Use embedding similarity (>0.85 threshold) + name fuzzy matching
- **Also check across chunks of the same source** — same entity mentioned in chunk 1 and chunk 5
- Merge duplicates, preserving all evidence links
- Log all merge decisions

## Step 7: Knowledge Graph Construction (Batch)

### Process (using batch operations)
1. Collect all extracted knowledge from all chunks
2. **Batch entity resolution** across all chunks
3. **Batch create** entities → Neo4j nodes
4. **Batch create** facts → linked to entities via `ABOUT` edges
5. **Batch create** evidence → linked to facts via `SUPPORTS` edges
6. Create relationships → entity-to-entity edges
7. Create decisions → linked to entities and facts
8. Create questions → linked to entities
9. Run contradiction detection against existing facts
10. If contradictions found → create `FACT_CONTRADICTS` edges

### Contradiction Detection Flow
```python
async def check_and_handle_contradiction(new_fact: Fact, existing_facts: list[Fact]):
    for existing in existing_facts:
        contradiction = await llm_service.detect_contradiction(new_fact, existing)
        if contradiction.is_contradicting:
            await graph_service.create_edge(new_fact.id, existing.id, "FACT_CONTRADICTS",
                {"explanation": contradiction.explanation})
            await memory_manager.record_contradiction(new_fact, existing, contradiction)
            await event_bus.emit(session_id, "CONTRADICTION_DETECTED", {
                "fact_a": new_fact.statement,
                "fact_b": existing.statement,
                "explanation": contradiction.explanation
            })
```

## Step 8: Memory Update
(See memory-system SKILL.md for full details)

## Step 9: Synthesis Generation

### Synthesis Structure
```markdown
# Research Synthesis: {Topic}

## Executive Summary
{2-3 paragraph overview of key findings}

## Key Entities
{Table of main entities discovered with descriptions}

## Core Findings
{Numbered list of major facts with confidence and evidence count}

## Decisions & Recommendations
{Decisions found in the research with supporting evidence}

## Relationships & Connections
{Description of how entities relate, with graph context}

## Insights
### Obvious Insights
{Facts, decisions, risks clearly stated in sources}

### Non-Obvious Insights
{Patterns, weak signals, contradictions, emerging themes}

## Contradictions & Open Questions
{Any conflicting information with evidence from both sides}
{Open questions identified during research}

## Knowledge Quality
{Confidence distribution, source quality, gaps identified}

## Sources
{Numbered list of all sources used with quality scores}
```

## Research Orchestrator (Split from generic Orchestrator)

```python
class ResearchOrchestrator:
    """Manages the autonomous research pipeline with streaming progress."""
    
    def __init__(self, 
                 event_bus: ResearchEventBus,
                 llm_service: LLMService,
                 graph_service: GraphService,
                 vector_service: VectorService,
                 memory_manager: MemoryManager,
                 insight_engine: InsightEngine,
                 noise_filter: NoiseFilter,
                 document_chunker: DocumentChunker):
        ...
    
    async def start_research(self, topic: str, config: ResearchConfig = None) -> ResearchSession:
        """Kicks off the full autonomous research pipeline with SSE streaming."""
        session = await self._create_session(topic)
        self.event_bus.create_session(session.id)
        
        # Run pipeline as background task
        asyncio.create_task(self._run_pipeline(session))
        return session
    
    async def _run_pipeline(self, session: ResearchSession):
        """Execute each pipeline stage, streaming events."""
        try:
            await self._decompose_topic(session)
            await self._search_web(session)
            await self._gather_sources(session)
            await self._filter_noise(session)
            await self._chunk_documents(session)
            await self._extract_knowledge(session)
            await self._construct_graph(session)
            await self._update_memory(session)
            await self._generate_insights(session)
            await self._generate_synthesis(session)
        except Exception as e:
            await self.event_bus.emit(session.id, "ERROR", {"message": str(e)})
        finally:
            await self.event_bus.emit(session.id, "STREAM_END", {})
            self.event_bus.cleanup(session.id)
    
    async def get_progress(self, session_id: str) -> ResearchProgress:
        """Returns current pipeline stage and progress metrics."""
    
    async def get_synthesis(self, session_id: str) -> Synthesis:
        """Returns the generated synthesis for a completed research session."""
```

## Error Handling
- If web search fails → retry with alternative queries
- If source fetch fails → skip, log, stream `ERROR` event
- If LLM extraction fails → retry with simplified prompt
- If Neo4j write fails → retry with exponential backoff
- Never fail the entire pipeline for a single source failure
- All errors are streamed to frontend via `ERROR` events
