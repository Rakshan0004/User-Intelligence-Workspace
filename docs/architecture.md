# User Intelligence Workspace — Architecture Document

## 1. System Overview

The User Intelligence Workspace is an AI-native system that acquires, structures, evolves, and utilizes knowledge over time. It supports two primary workflows: autonomous research and knowledge-augmented chat.

## 2. Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        Browser["Browser (User)"]
    end

    subgraph "Frontend — Next.js 14 on Vercel"
        ResearchUI["Research Mode UI"]
        ChatUI["Chat UI"]
        GraphUI["Knowledge Graph Explorer"]
        UploadUI["File Upload"]
        TraceUI["Traceability Panel"]
        APIRoutes["Next.js API Routes (Proxy)"]
    end

    subgraph "Backend — FastAPI on Railway"
        direction TB
        
        subgraph "API Layer"
            ResearchAPI["POST /api/research"]
            ChatAPI["POST /api/chat"]
            UploadAPI["POST /api/upload"]
            GraphAPI["GET /api/graph"]
            KnowledgeAPI["GET /api/knowledge"]
        end
        
        subgraph "Service Layer"
            Orchestrator["Workflow Orchestrator"]
            ResearchAgent["Research Agent"]
            KnowledgeEngine["Knowledge Engine"]
            MemoryManager["Memory Manager"]
            InsightEngine["Insight Engine"]
            NoiseFilter["Noise Filter"]
            LLMService["LLM Service"]
        end
        
        subgraph "Ingestion Layer"
            IngestionRouter["Ingestion Router"]
            PDFProc["PDF Processor"]
            DOCXProc["DOCX Processor"]
            XLSXProc["XLSX Processor"]
            ImageProc["Image Processor"]
            AudioProc["Audio Processor"]
            VideoProc["Video Processor"]
            URLProc["URL Processor"]
            YouTubeProc["YouTube Processor"]
        end
        
        subgraph "Data Access Layer"
            GraphService["Graph Service"]
            VectorService["Vector Service"]
            PostgresService["PostgreSQL Service"]
        end
    end

    subgraph "Storage Layer"
        Neo4j["Neo4j Aura<br/>Knowledge Graph"]
        Qdrant["Qdrant Cloud<br/>Vector Store"]
        Postgres["PostgreSQL (Supabase)<br/>Sessions & Memory"]
    end

    subgraph "External APIs"
        OpenAI["OpenAI / Gemini<br/>LLM API"]
        Tavily["Tavily<br/>Web Search"]
        Whisper["Whisper<br/>Audio Transcription"]
    end

    Browser --> ResearchUI
    Browser --> ChatUI
    Browser --> GraphUI
    Browser --> UploadUI
    
    ResearchUI --> APIRoutes
    ChatUI --> APIRoutes
    UploadUI --> APIRoutes
    GraphUI --> APIRoutes
    
    APIRoutes --> ResearchAPI
    APIRoutes --> ChatAPI
    APIRoutes --> UploadAPI
    APIRoutes --> GraphAPI
    
    ResearchAPI --> Orchestrator
    ChatAPI --> Orchestrator
    UploadAPI --> IngestionRouter
    GraphAPI --> GraphService
    
    Orchestrator --> ResearchAgent
    Orchestrator --> KnowledgeEngine
    Orchestrator --> MemoryManager
    Orchestrator --> InsightEngine
    
    ResearchAgent --> Tavily
    ResearchAgent --> LLMService
    ResearchAgent --> NoiseFilter
    
    KnowledgeEngine --> GraphService
    KnowledgeEngine --> VectorService
    KnowledgeEngine --> LLMService
    
    MemoryManager --> PostgresService
    MemoryManager --> GraphService
    
    InsightEngine --> GraphService
    InsightEngine --> VectorService
    InsightEngine --> LLMService
    
    NoiseFilter --> LLMService
    
    IngestionRouter --> PDFProc
    IngestionRouter --> DOCXProc
    IngestionRouter --> XLSXProc
    IngestionRouter --> ImageProc
    IngestionRouter --> AudioProc
    IngestionRouter --> VideoProc
    IngestionRouter --> URLProc
    IngestionRouter --> YouTubeProc
    
    AudioProc --> Whisper
    VideoProc --> Whisper
    YouTubeProc --> Whisper
    ImageProc --> OpenAI
    
    GraphService --> Neo4j
    VectorService --> Qdrant
    PostgresService --> Postgres
    LLMService --> OpenAI
```

## 3. Data Flow Diagrams

### 3.1 Research Mode Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant O as Orchestrator
    participant R as Research Agent
    participant N as Noise Filter
    participant K as Knowledge Engine
    participant M as Memory Manager
    participant I as Insight Engine
    participant G as Neo4j Graph
    participant V as Qdrant Vectors

    U->>F: Enter topic "Behavioral Economics"
    F->>O: POST /api/research {topic}
    O->>R: start_research(topic)
    
    R->>R: Decompose topic into sub-topics
    R->>R: Generate search queries
    R->>R: Search web (Tavily)
    R->>R: Fetch & parse sources
    R->>N: Filter noise & duplicates
    N-->>R: Cleaned sources
    
    R->>K: Extract knowledge from sources
    K->>K: Extract entities, facts, relationships
    K->>G: Create/merge entity nodes
    K->>G: Create fact nodes + evidence links
    K->>G: Create relationship edges
    K->>V: Store embeddings
    
    K->>K: Detect contradictions with existing knowledge
    K->>M: Update memory (learnings, contradictions)
    M->>G: Create memory nodes + links
    
    O->>I: Generate insights
    I->>G: Query graph for patterns
    I->>I: Detect obvious + non-obvious insights
    
    O->>O: Generate synthesis report
    O-->>F: Return synthesis + progress
    F-->>U: Display research results
```

### 3.2 Knowledge-Augmented Chat Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant O as Orchestrator
    participant K as Knowledge Engine
    participant M as Memory Manager
    participant L as LLM Service
    participant G as Neo4j Graph
    participant V as Qdrant Vectors

    U->>F: Ask "What are the key biases in behavioral economics?"
    F->>O: POST /api/chat {query}
    
    O->>V: Semantic search for relevant facts
    V-->>O: Top-K relevant embeddings
    
    O->>G: Get entity neighborhood for matched entities
    G-->>O: Related entities, facts, evidence
    
    O->>M: Get relevant memories
    M-->>O: Prior session memories
    
    O->>G: Get contradiction info
    G-->>O: Any contradicting evidence
    
    O->>L: Generate grounded response with context
    Note over L: Context includes:<br/>- Matched facts + evidence<br/>- Graph relationships<br/>- Prior memories<br/>- Contradiction info<br/>- Confidence scores
    
    L-->>O: Response with citations
    
    O-->>F: Response + traceability chain
    F-->>U: Display response with evidence panel
```

## 4. Knowledge Graph Schema

```mermaid
graph LR
    Entity((Entity))
    Fact((Fact))
    Evidence((Evidence))
    Source((Source))
    Decision((Decision))
    Question((Question))
    Insight((Insight))
    Memory((Memory))

    Entity -->|RELATES_TO| Entity
    Entity -->|INFLUENCES| Entity
    Entity -->|DEPENDS_ON| Entity
    Fact -->|ABOUT| Entity
    Evidence -->|SUPPORTS| Fact
    Evidence -->|CONTRADICTS| Fact
    Evidence -->|EXTRACTED_FROM| Source
    Evidence -->|MENTIONS| Entity
    Fact -->|DERIVED_FROM| Source
    Fact -->|FACT_CONTRADICTS| Fact
    Fact -->|EVOLVED_TO| Fact
    Fact -->|ANSWERS| Question
    Decision -->|INFORMS| Entity
    Decision -->|BASED_ON| Fact
    Question -->|ABOUT| Entity
    Question -->|RAISED_BY| Source
    Insight -->|GENERATED_FROM| Fact
    Memory -->|REFERENCES| Entity
    Memory -->|TRIGGERED_BY| Evidence
```

> **Note**: All nodes carry a `topic` property for domain scoping. Evidence→Fact uses `CONTRADICTS`; Fact→Fact uses `FACT_CONTRADICTS` to avoid Cypher ambiguity.

## 5. Knowledge Evolution State Machine

```mermaid
stateDiagram-v2
    [*] --> Active : Created
    Active --> Reinforced : Same claim confirmed
    Reinforced --> Active : Continues as active
    Active --> Modified : Updated with new info
    Modified --> Active : New version active
    Active --> Contradicted : Conflicting evidence found
    Contradicted --> Active : Resolution chosen
    Active --> Deprecated : Superseded by new knowledge
    Deprecated --> [*] : Archived
    
    note right of Active : confidence ∈ [0, 1]
    note right of Reinforced : confidence += 0.1
    note right of Contradicted : Both facts flagged
```

## 6. API Design

### Research Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/research` | Start autonomous research on a topic |
| `GET` | `/api/research/{session_id}/stream` | **SSE stream** of research progress events |
| `GET` | `/api/research/{session_id}/progress` | Get current progress (polling fallback) |
| `GET` | `/api/research/{session_id}/synthesis` | Get research synthesis |

### Chat Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Send a chat message → **SSE stream** of response tokens |
| `GET` | `/api/chat/{session_id}/history?page=1&limit=20` | Get paginated chat history |

> Chat POST body: `{session_id, query, conversation_id}` — includes session context for follow-ups.

### Knowledge Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/knowledge/entities?topic=X&page=1&limit=20` | List entities (paginated, filterable) |
| `GET` | `/api/knowledge/facts?status=active&confidence_min=0.5&topic=X` | List facts (paginated, filterable) |
| `GET` | `/api/knowledge/facts/{id}/trace` | Get full traceability chain |
| `GET` | `/api/knowledge/decisions?topic=X` | List decisions |
| `GET` | `/api/knowledge/decisions/{id}/trace` | Get decision traceability |
| `GET` | `/api/knowledge/questions?status=open&topic=X` | List open questions |
| `GET` | `/api/knowledge/contradictions?topic=X` | List all contradictions |
| `GET` | `/api/knowledge/stats?topic=X` | Knowledge base statistics |

### Graph Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/graph?topic=X&limit=200` | Get graph for visualization |
| `GET` | `/api/graph/entity/{id}/neighborhood?depth=2` | Get entity neighborhood |
| `GET` | `/api/graph/search?q=term&topic=X` | Search entities/facts |

### Upload Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Upload a document for processing |
| `POST` | `/api/upload/batch` | Upload multiple documents |
| `GET` | `/api/upload/{id}/status` | Get processing status |

### Memory Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/memory/sessions?page=1&limit=20` | List all sessions (paginated) |
| `GET` | `/api/memory/{session_id}` | Get session memories |
| `GET` | `/api/memory/evolution/{id}` | Get memory evolution history |

## 7. Non-Functional Requirements

### Performance
- Research pipeline completes in < 5 minutes for a standard topic
- Chat first token in < 2 seconds (streaming)
- Chat full response in < 10 seconds
- Graph visualization loads in < 3 seconds
- Document upload processing feedback within 1 second

### Streaming
- Research progress: SSE with `text/event-stream` content type
- Chat responses: SSE with token-by-token streaming
- Frontend uses `EventSource` API (native browser support)
- Fallback: polling endpoints for environments without SSE

### Reliability
- Graceful degradation: if web search fails, use existing knowledge
- Retry logic with exponential backoff on all external API calls
- No data loss on pipeline failure (atomic operations where possible)
- PostgreSQL ensures data persistence across container restarts

### Security
- API keys stored as environment variables, never committed
- CORS restricted to frontend domain
- File upload size limits and type validation
- No PII stored in knowledge graph
- Bearer token authentication on all endpoints

### Scalability Considerations
- Single-user design (sufficient for assessment)
- Neo4j Aura free tier: 200K nodes (enough for research workspace)
- Qdrant free tier: 1GB (thousands of embeddings)
- PostgreSQL (Supabase free tier): 500MB
- Future: could add Redis for caching, Celery for task queues

