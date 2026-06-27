# User Intelligence Workspace — Project Context

## What Is This?
A **single-user intelligence workspace** that learns from information over time. It's an AI-native system that can acquire, structure, evolve, and utilize knowledge — functioning as a personal research assistant with persistent memory and a living knowledge graph.

## Two Core Workflows

### Workflow 1: Research Mode
**User gives a topic → System autonomously researches it → Streams progress in real-time**

The pipeline:
1. **Topic Decomposition** — Break into sub-topics and research questions
2. **Web Search** — Gather sources from the web (Tavily API)
3. **Source Processing** — Fetch and clean content
4. **Noise Filtering** — Remove duplicates, low-quality, irrelevant content (with explanations)
5. **Document Chunking** — Split content into LLM-processable chunks (~1000 tokens)
6. **Knowledge Extraction** — LLM extracts entities, facts, decisions, questions, relationships per chunk
7. **Knowledge Graph Construction** — Store in Neo4j with full relationship modeling + contradiction detection
8. **Memory Update** — Record what was learned, detect evolution
9. **Insight Generation** — Surface obvious + non-obvious insights
10. **Synthesis Generation** — Produce structured research summary

All stages stream progress to the frontend via **Server-Sent Events (SSE)**.

### Workflow 2: Knowledge-Augmented Chat
**User asks questions → System responds grounded in accumulated knowledge → Streams response**

The system:
1. **Routes the query** — classifies intent (factual, relational, contradictions, exploratory)
2. **Retrieves context** — vector search (Qdrant) + graph traversal (Neo4j) based on intent
3. **Loads memory** — relevant memories from prior sessions
4. **Loads conversation context** — recent chat messages for follow-up resolution
5. **Generates response** — LLM produces grounded, cited response with confidence indicators
6. **Streams response** — token-by-token via SSE

Every response includes traceability: Response → Knowledge → Evidence → Source

## Architecture Overview

```
Frontend (Next.js) ←→ Backend (FastAPI) ←→ Neo4j (Knowledge Graph)
       ↕ SSE                ↕                  Qdrant (Vector Store)
    Vercel            Railway/Render            PostgreSQL (Sessions, Memory)
```

### Frontend: Next.js 14 (App Router)
- **Research Page** — Topic input, real-time SSE progress, synthesis display
- **Chat Page** — Knowledge-augmented Q&A with streaming + traceability panel
- **Graph Explorer** — Interactive knowledge graph visualization
- **Upload Interface** — Multi-format document upload
- Deployed on **Vercel**

### Backend: FastAPI (Python)
- **ResearchOrchestrator** — Autonomous research pipeline with SSE streaming
- **ChatOrchestrator** — Query routing + retrieval strategy selection
- **IngestionOrchestrator** — Document upload → chunk → extract → graph
- **Knowledge Engine** — CRUD + evolution for entities, facts, decisions, questions
- **Memory Manager** — Cross-session persistent memory with semantic retrieval
- **Conversation Manager** — Chat context for follow-up resolution
- **Insight Engine** — Obvious + non-obvious insight generation
- **Noise Filter** — Deduplication and quality filtering with explanations
- **Document Chunker** — Semantic/fixed-size chunking for LLM processing
- Deployed on **Railway/Render**

### Storage (4 stores, clear ownership)
| Store | Owns | Why |
|-------|------|-----|
| **Neo4j Aura** | Knowledge structure (entities, facts, evidence, relationships, decisions, questions, insights) | Graph queries, contradiction detection, path traversal |
| **Qdrant Cloud** | Embeddings (`knowledge_embeddings`, `memory_embeddings`) | Semantic similarity search |
| **PostgreSQL** (Supabase) | Sessions, conversation history, memory audit trail, file metadata | Relational data, persistence on deploy |
| **Cloudflare R2** / Local | Uploaded raw files | File storage |

## Key Domain Concepts

| Concept | Description |
|---------|-------------|
| **Entity** | A named concept, person, organization, technology, event, or place |
| **Fact** | A verifiable claim with confidence score and status tracking |
| **Evidence** | A chunk extracted from a source that supports or contradicts a fact |
| **Source** | Origin of information (web page, document, video, etc.) |
| **Decision** | An explicit decision or recommendation found in sources |
| **Question** | An open question or unresolved issue in the domain |
| **Insight** | A finding — obvious (stated) or non-obvious (inferred/pattern) |
| **Memory** | A record of what was learned, updated, reinforced, or contradicted |
| **Relationship** | A typed, weighted connection between entities |

## Knowledge Evolution Model
Knowledge is NOT static. The system tracks 4 types of evolution:
1. **Reinforcement** — Same claim confirmed by additional sources → confidence increases (weighted by source quality)
2. **Modification** — Existing knowledge updated with new info → new version created
3. **Contradiction** — New info conflicts with existing knowledge → flagged explicitly via `FACT_CONTRADICTS` edge
4. **Deprecation** — New info makes old knowledge obsolete → marked deprecated

All evolution creates an audit trail. Nothing is silently deleted.

## What Makes This "Senior AI Engineer Level"
1. **Graph + Vector dual storage** — structural queries (contradictions, paths) + semantic search
2. **Memory evolution, not accumulation** — memories have lifecycle states, weighted confidence
3. **Autonomous pipeline with streaming** — real-time SSE progress, not blank screen
4. **Explainability chain** — every response traces back to original sources
5. **Non-obvious insight detection** — patterns, weak signals, bridge entities
6. **Incremental learning** — no full rebuilds when new info arrives
7. **Document chunking** — proper handling of large documents
8. **Query routing** — different retrieval strategies for different question types
9. **Conversation context** — follow-up questions work via chat history
10. **Clean separation of concerns** — split orchestrators, injectable services, exception hierarchy

## Sprint Roadmap
| Sprint | Focus | Description |
|--------|-------|-------------|
| **0** | Foundation | Skills, context, architecture docs ✅ |
| **1** | Backend Core | FastAPI + Neo4j + PostgreSQL + domain models |
| **2** | Research Mode | Autonomous research pipeline with SSE streaming |
| **3** | Memory + Evolution | Persistent memory, contradiction detection |
| **4** | Ingestion | Multi-format document processing with chunking |
| **5** | Chat + Insights | RAG chat with query routing, insight engine |
| **6** | Frontend | Next.js UI for all workflows |
| **7** | Deploy + Demo | Vercel + Railway + demo video |

## File Structure
```
User-Intelligence-workspace/
├── .agents/                    # AI agent skills & rules
│   ├── AGENTS.md              # Project rules
│   └── skills/                # 6 domain skills
├── frontend/                   # Next.js 14 app
├── backend/                    # FastAPI app
│   ├── app/
│   │   ├── models/            # Pydantic schemas
│   │   ├── services/          # Business logic (split orchestrators)
│   │   ├── ingestion/         # Document processors + chunker
│   │   ├── routes/            # API endpoints (SSE streaming)
│   │   └── db/                # Database clients (Neo4j, Qdrant, PostgreSQL)
├── docs/                       # Architecture & design docs
├── docker-compose.yml          # Local dev services (Neo4j + Qdrant + PostgreSQL)
└── README.md
```

## Key Technical Decisions
- **Neo4j over NetworkX**: Persistence, Cypher queries, free cloud tier
- **Qdrant over ChromaDB**: Better performance, cloud hosting, mature API
- **PostgreSQL over SQLite**: Persistent on container restart, proper async, cloud-hosted
- **FastAPI over Flask**: Async-native, Pydantic integration, SSE streaming support
- **Next.js over Vite**: SSR, API routes, native Vercel deployment
- **SSE over WebSocket**: Simpler, unidirectional (server → client), sufficient for progress streaming
- **Semantic chunking over fixed-size**: Better extraction quality, respects document structure
