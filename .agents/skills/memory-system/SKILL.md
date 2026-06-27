---
name: memory-system
description: Memory management system for the User Intelligence Workspace. Covers persistent cross-session memory, memory evolution (learning, updating, reinforcement, contradiction handling, deprecation), incremental learning without full rebuilds, conversation context for chat, and the memory-knowledge graph integration.
---

# Memory System Skill

## Overview
The memory system ensures the workspace learns and evolves over time. Memory is NOT mere accumulation — it supports learning, updating, reinforcement, contradiction handling, and deprecation. Knowledge from one session influences future sessions, and modifications propagate through the memory graph.

## Architecture Decision: Single Source of Truth

> **PostgreSQL** is the single source of truth for session state, conversation history, and audit trails.
> **Neo4j** is the single source of truth for knowledge structure (Memory nodes exist in the graph for relationship queries only).
> **Qdrant** provides semantic retrieval over memory embeddings.

### Data ownership:
| Data | Primary Store | Why |
|------|--------------|-----|
| Session metadata | PostgreSQL | Relational queries, joins with conversations |
| Conversation history | PostgreSQL | Ordered messages, pagination, fast reads |
| Memory entries | PostgreSQL | Audit trail, evolution log, relational queries |
| Memory → Knowledge links | PostgreSQL | Join table, consistent with memory entries |
| Memory evolution log | PostgreSQL | Time-series audit data |
| Memory embeddings | Qdrant (`memory_embeddings`) | Semantic retrieval |
| Memory graph relationships | Neo4j | Graph traversal (what entities does this memory reference?) |

### Sync Strategy
When a memory is created/updated in PostgreSQL:
1. Upsert embedding in Qdrant `memory_embeddings` collection
2. Create/update `:Memory` node in Neo4j with `REFERENCES` edges
3. If either fails → log warning, retry async, mark as `sync_pending`

## Core Principles

1. **Memory evolves** — new information updates existing memories, not just appends
2. **No silent overwrites** — contradictions are explicitly surfaced and tracked
3. **Traceability** — every memory links back to the evidence/session that created it
4. **Incremental** — adding new info doesn't require rebuilding from scratch
5. **Cross-session persistence** — knowledge created in session N influences session N+1
6. **Conversation context** — chat sessions maintain short-term context for follow-up resolution

## Memory Types

| Type | Description | Example |
|------|-------------|---------|
| `learning` | New knowledge acquired for the first time | "Discovered that X causes Y" |
| `update` | Existing knowledge was modified with new info | "Updated X: now includes Z factor" |
| `reinforcement` | Existing knowledge confirmed by additional source | "Confirmed X from 3rd source" |
| `contradiction` | New info contradicts existing knowledge | "Source B says X causes Z, not Y" |
| `deprecation` | Knowledge is no longer valid/relevant | "X was superseded by W" |
| `gap` | Identified area where knowledge is missing | "No sources discuss X's impact on Q" |

## Database Schema (PostgreSQL)

```sql
-- Core memory entries (SOURCE OF TRUTH)
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id),
    type VARCHAR(20) NOT NULL CHECK(type IN ('learning', 'update', 'reinforcement', 'contradiction', 'deprecation', 'gap')),
    content TEXT NOT NULL,
    topic VARCHAR(255),
    confidence REAL DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    superseded_by UUID REFERENCES memories(id),
    is_active BOOLEAN DEFAULT TRUE,
    neo4j_synced BOOLEAN DEFAULT FALSE,
    qdrant_synced BOOLEAN DEFAULT FALSE
);

-- Link memories to knowledge graph entities/facts
CREATE TABLE memory_knowledge_links (
    memory_id UUID REFERENCES memories(id),
    knowledge_type VARCHAR(20) NOT NULL CHECK(knowledge_type IN ('entity', 'fact', 'decision', 'question', 'insight')),
    knowledge_id UUID NOT NULL,
    link_type VARCHAR(20) NOT NULL CHECK(link_type IN ('created', 'updated', 'reinforced', 'contradicted', 'deprecated')),
    PRIMARY KEY (memory_id, knowledge_type, knowledge_id)
);

-- Session tracking
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic VARCHAR(255),
    mode VARCHAR(20) CHECK(mode IN ('research', 'chat')),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    summary TEXT,
    entities_created INTEGER DEFAULT 0,
    facts_created INTEGER DEFAULT 0,
    contradictions_found INTEGER DEFAULT 0
);

-- Conversation history (for chat follow-up context)
CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id),
    role VARCHAR(20) NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',  -- citations, fact_ids, confidence, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_conv_messages_session ON conversation_messages(session_id, created_at);

-- Memory evolution audit trail
CREATE TABLE memory_evolution_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID REFERENCES memories(id),
    action VARCHAR(20) NOT NULL,
    old_content TEXT,
    new_content TEXT,
    reason TEXT,
    evidence_id UUID,
    session_id UUID REFERENCES sessions(id),
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- File upload tracking
CREATE TABLE uploaded_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size_bytes BIGINT,
    storage_path VARCHAR(1000),  -- local path or cloud URL
    processing_status VARCHAR(20) DEFAULT 'pending' CHECK(processing_status IN ('pending', 'processing', 'completed', 'failed')),
    source_id UUID,  -- links to Neo4j Source node after processing
    error_message TEXT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);
```

## Memory Manager Interface

```python
class MemoryManager:
    """Manages persistent memory across sessions."""
    
    async def create_memory(self, session_id: str, type: str, content: str,
                           topic: str = None,
                           related_entity_ids: list[str] = None,
                           related_fact_ids: list[str] = None) -> Memory:
        """Create a new memory entry, embed in Qdrant, sync to Neo4j."""
    
    async def check_and_evolve(self, new_fact: Fact, session_id: str) -> EvolutionResult:
        """
        Core method: Check if new_fact reinforces, modifies, contradicts, 
        or deprecates any existing memory/knowledge.
        
        Returns what changed and why.
        """
    
    async def get_session_memories(self, session_id: str) -> list[Memory]:
        """Get all memories from a specific session."""
    
    async def get_relevant_memories(self, query: str, topic: str = None, limit: int = 10) -> list[Memory]:
        """Retrieve memories relevant to a query using Qdrant semantic search."""
    
    async def get_active_memories(self, topic: str = None) -> list[Memory]:
        """Get all currently active (non-superseded) memories, optionally filtered by topic."""
    
    async def deprecate_memory(self, memory_id: str, reason: str, superseded_by: str = None) -> None:
        """Mark a memory as deprecated with audit trail."""
    
    async def get_evolution_history(self, memory_id: str) -> list[EvolutionLogEntry]:
        """Get the full evolution history of a memory."""
    
    async def get_session_summary(self, session_id: str) -> SessionSummary:
        """Generate a summary of what was learned in a session."""
```

## Conversation Context Manager

```python
class ConversationManager:
    """Manages chat conversation context for follow-up resolution."""
    
    async def add_message(self, session_id: str, role: str, content: str, 
                         metadata: dict = None) -> ConversationMessage:
        """Store a chat message with optional metadata (citations, fact_ids)."""
    
    async def get_recent_context(self, session_id: str, limit: int = 20) -> list[ConversationMessage]:
        """Get recent messages for a chat session (for LLM context window)."""
    
    async def get_conversation_summary(self, session_id: str) -> str:
        """Summarize older messages when conversation exceeds context window."""
    
    async def resolve_references(self, session_id: str, query: str) -> str:
        """
        Resolve anaphoric references like 'that', 'it', 'the previous one'.
        Uses recent conversation context to expand the query.
        Example: "What about that?" → "What about the contradiction in behavioral economics?"
        """
```

### How Conversation Context Works in Chat
```python
async def handle_chat(self, session_id: str, user_query: str) -> ChatResponse:
    # 1. Store the user message
    await self.conversation_manager.add_message(session_id, "user", user_query)
    
    # 2. Resolve references using conversation history
    expanded_query = await self.conversation_manager.resolve_references(session_id, user_query)
    
    # 3. Get recent conversation context for LLM
    recent_messages = await self.conversation_manager.get_recent_context(session_id, limit=10)
    
    # 4. Retrieve knowledge (vector + graph)
    knowledge_context = await self.retrieve_knowledge(expanded_query)
    
    # 5. Get relevant memories
    memories = await self.memory_manager.get_relevant_memories(expanded_query)
    
    # 6. Generate response with full context
    response = await self.llm_service.generate_response(
        query=expanded_query,
        conversation_history=recent_messages,
        knowledge_context=knowledge_context,
        memories=memories
    )
    
    # 7. Store assistant response
    await self.conversation_manager.add_message(session_id, "assistant", response.content, 
        metadata={"fact_ids": response.fact_ids, "citations": response.citations})
    
    return response
```

## Knowledge Evolution Detection

### Algorithm (with weighted confidence)
```python
async def check_and_evolve(self, new_fact: Fact, session_id: str) -> EvolutionResult:
    """
    1. Find existing facts about the same entities
    2. For each existing fact, use LLM to classify the relationship
    3. Apply the appropriate evolution action with WEIGHTED confidence
    4. Create audit trail
    """
    entity_ids = await self.graph_service.get_fact_entities(new_fact.id)
    existing_facts = await self.graph_service.get_facts_by_entities(entity_ids)
    
    # Also check for duplicate facts via embedding similarity
    potential_dupes = await self.graph_service.find_duplicate_facts(new_fact, new_fact.topic)
    existing_facts = list(set(existing_facts + potential_dupes))
    
    evolutions = []
    for existing in existing_facts:
        classification = await self.llm_service.classify_fact_relationship(
            new_fact=new_fact.statement,
            existing_fact=existing.statement,
            context={
                "new_evidence": new_fact.evidence,
                "existing_evidence": existing.evidence,
                "existing_confidence": existing.confidence,
                "existing_source_count": existing.source_count
            }
        )
        
        if classification.type == "reinforces":
            await self._reinforce(existing, new_fact, session_id)
        elif classification.type == "modifies":
            await self._modify(existing, new_fact, classification.explanation, session_id)
        elif classification.type == "contradicts":
            await self._contradict(existing, new_fact, classification.explanation, session_id)
        elif classification.type == "deprecates":
            await self._deprecate(existing, new_fact, classification.explanation, session_id)
        
        evolutions.append(classification)
    
    return EvolutionResult(evolutions=evolutions)
```

### Evolution Actions (with weighted confidence)

```python
async def _reinforce(self, existing_fact, new_fact, session_id):
    """Increase confidence weighted by source quality, increment source count."""
    source = await self.graph_service.get_source(new_fact.source_id)
    confidence_delta = 0.1 * source.quality_score  # WEIGHTED by source quality
    existing_fact.confidence = min(1.0, existing_fact.confidence + confidence_delta)
    existing_fact.source_count += 1
    await self.graph_service.update_fact(existing_fact)
    await self.graph_service.create_edge(new_fact.evidence_id, existing_fact.id, "SUPPORTS")
    await self.create_memory(session_id, "reinforcement", 
        f"Reinforced: '{existing_fact.statement}' (now {existing_fact.source_count} sources, confidence: {existing_fact.confidence:.2f})",
        topic=existing_fact.topic)

async def _modify(self, existing_fact, new_fact, explanation, session_id):
    """Create evolution edge, update fact content, preserve history."""
    evolved_fact = await self.graph_service.evolve_fact(
        old_fact_id=existing_fact.id,
        new_fact=new_fact,
        evolution_type="modified"
    )
    await self.create_memory(session_id, "update",
        f"Modified: '{existing_fact.statement}' → '{evolved_fact.statement}'. Reason: {explanation}",
        topic=existing_fact.topic)

async def _contradict(self, existing_fact, new_fact, explanation, session_id):
    """Create contradiction edge, flag both facts, surface to user."""
    await self.graph_service.create_edge(new_fact.id, existing_fact.id, "FACT_CONTRADICTS", 
        {"explanation": explanation, "detected_at": datetime.utcnow()})
    await self.create_memory(session_id, "contradiction",
        f"Contradiction detected: '{new_fact.statement}' vs '{existing_fact.statement}'. {explanation}",
        topic=existing_fact.topic)

async def _deprecate(self, existing_fact, new_fact, explanation, session_id):
    """Mark old fact as deprecated, link to replacement."""
    existing_fact.status = "deprecated"
    existing_fact.deprecated_at = datetime.utcnow()
    await self.graph_service.update_fact(existing_fact)
    await self.graph_service.create_edge(existing_fact.id, new_fact.id, "EVOLVED_TO",
        {"evolution_type": "deprecated"})
    await self.create_memory(session_id, "deprecation",
        f"Deprecated: '{existing_fact.statement}'. Replaced by: '{new_fact.statement}'. Reason: {explanation}",
        topic=existing_fact.topic)
```

## Incremental Learning

### Key Design: No Full Rebuilds
- New documents are processed **incrementally** — only new content is extracted
- Entity resolution checks existing graph before creating new nodes
- Fact evolution checks existing facts before creating duplicates
- **Fact deduplication** via embedding similarity (parallel to entity resolution)
- Memory links new information to existing knowledge structure
- Vector store supports upsert (add new embeddings without reindexing)

### Incremental Update Flow
```
New Information
    │
    ▼
Chunk document (semantic or fixed-size)
    │
    ▼
Extract entities & facts (per chunk)
    │
    ▼
Entity Resolution (merge with existing?)
    │
    ├── New entity → Create node
    └── Existing entity → Update/merge
         │
         ▼
    Fact Deduplication Check (embedding similarity)
         │
         ├── Duplicate → Skip or merge
         └── Not duplicate →
              │
              ▼
         Fact Evolution Check
              │
              ├── New fact → Create node + evidence
              ├── Reinforcement → Update confidence (weighted)
              ├── Modification → Create new version
              ├── Contradiction → Flag + create edge
              └── Deprecation → Mark old as deprecated
                   │
                   ▼
              Memory Update (PostgreSQL + Qdrant + Neo4j)
                   │
                   ▼
              Vector Store Upsert
```

## Cross-Session Memory Influence

### How Session N influences Session N+1:
1. **Context loading**: At session start, load active memories relevant to the current topic via Qdrant semantic search
2. **Knowledge priming**: Include relevant facts and entities in LLM system prompts
3. **Contradiction awareness**: When extracting new knowledge, check against ALL existing knowledge (not just current session)
4. **Cumulative confidence**: Facts seen across multiple sessions get higher confidence scores (weighted by source quality)
5. **Memory-aware responses**: Chat responses cite memories from prior sessions when relevant
6. **Conversation continuity**: Prior chat sessions' summaries are available for reference
