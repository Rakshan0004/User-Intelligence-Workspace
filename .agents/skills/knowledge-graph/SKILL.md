---
name: knowledge-graph
description: Knowledge graph design patterns, Neo4j Cypher queries, schema management, and graph traversal strategies for the User Intelligence Workspace. Covers entity/relationship modeling, contradiction detection via graph paths, knowledge evolution tracking, and traceability chain construction.
---

# Knowledge Graph Skill

## Overview
This skill covers the design, implementation, and querying of the Neo4j knowledge graph — the core structural backbone of the intelligence workspace.

## Graph Schema

### Node Labels & Properties

#### Entity
```
(:Entity {
  id: String (UUID),
  name: String,
  type: String,           // extensible — not a fixed enum
  description: String,
  confidence: Float,       // 0.0 - 1.0
  source_count: Integer,
  topic: String,           // domain scoping (e.g., "behavioral_economics")
  status: String,          // "active", "deprecated", "contradicted"
  created_at: DateTime,
  updated_at: DateTime,
  deprecated_at: DateTime  // nullable
})
```

#### Fact
```
(:Fact {
  id: String (UUID),
  statement: String,
  confidence: Float,
  source_count: Integer,
  supporting_evidence_count: Integer,
  contradicting_evidence_count: Integer,
  topic: String,
  status: String,          // "active", "modified", "deprecated", "contradicted"
  first_seen: DateTime,
  last_updated: DateTime,
  previous_version_id: String  // nullable, links to prior version
})
```

#### Evidence
```
(:Evidence {
  id: String (UUID),
  content: String,
  chunk_index: Integer,    // position within source document
  chunk_total: Integer,    // total chunks from this source
  type: String,            // "direct_quote", "inference", "synthesis"
  reliability: Float,
  extracted_at: DateTime,
  source_id: String
})
```

#### Source
```
(:Source {
  id: String (UUID),
  url: String,
  title: String,
  type: String,            // "web", "pdf", "docx", "xlsx", "image", "audio", "video", "youtube"
  quality_score: Float,
  topic: String,
  chunk_count: Integer,    // how many chunks this source produced
  ingested_at: DateTime
})
```

#### Decision (NEW — required by assignment)
```
(:Decision {
  id: String (UUID),
  statement: String,       // the decision or recommendation
  context: String,         // what led to this decision
  implications: String,    // what this decision means
  made_by: String,         // who/what made the decision (if known)
  confidence: Float,
  topic: String,
  status: String,          // "active", "deprecated", "superseded"
  created_at: DateTime,
  updated_at: DateTime
})
```

#### Question (NEW — required by assignment)
```
(:Question {
  id: String (UUID),
  question: String,
  context: String,         // why this question matters
  status: String,          // "open", "partially_answered", "answered"
  answer_summary: String,  // nullable — summary of answer if answered
  topic: String,
  created_at: DateTime,
  updated_at: DateTime
})
```

#### Insight
```
(:Insight {
  id: String (UUID),
  content: String,
  type: String,            // "obvious", "non_obvious"
  category: String,        // "pattern", "contradiction", "signal", "theme", "risk", "connection"
  confidence: Float,
  topic: String,
  generated_at: DateTime
})
```

#### Memory
```
(:Memory {
  id: String (UUID),
  session_id: String,
  content: String,
  type: String,            // "learning", "update", "reinforcement", "contradiction", "deprecation"
  topic: String,
  created_at: DateTime
})
```

### Relationship Types

| Relationship | From | To | Properties |
|-------------|------|-----|-----------|
| `RELATES_TO` | Entity | Entity | `strength: Float, context: String` |
| `SUPPORTS` | Evidence | Fact | `strength: Float` |
| `CONTRADICTS` | Evidence | Fact | `strength: Float, explanation: String` |
| `FACT_CONTRADICTS` | Fact | Fact | `detected_at: DateTime, explanation: String` |
| `DERIVED_FROM` | Fact | Source | |
| `EXTRACTED_FROM` | Evidence | Source | |
| `ABOUT` | Fact | Entity | |
| `MENTIONS` | Evidence | Entity | |
| `GENERATED_FROM` | Insight | Fact | |
| `INFLUENCES` | Entity | Entity | `direction: String, strength: Float` |
| `DEPENDS_ON` | Entity | Entity | |
| `EVOLVED_TO` | Fact | Fact | `evolution_type: String, detected_at: DateTime` |
| `REFERENCES` | Memory | Entity | |
| `TRIGGERED_BY` | Memory | Evidence | |
| `INFORMS` | Decision | Entity | `impact: String` |
| `BASED_ON` | Decision | Fact | |
| `RAISED_BY` | Question | Source | |
| `ABOUT` | Question | Entity | |
| `ANSWERS` | Fact | Question | `completeness: String` |

> **Note**: `CONTRADICTS` between Evidence→Fact is kept. Fact-to-Fact contradiction uses `FACT_CONTRADICTS` to avoid ambiguity in Cypher queries.

## Key Cypher Patterns

### 1. Contradiction Detection (Graph-Only Capability)
```cypher
// Find facts with both supporting AND contradicting evidence
MATCH (f:Fact)<-[:SUPPORTS]-(se:Evidence)
MATCH (f)<-[:CONTRADICTS]-(ce:Evidence)
WHERE f.status = 'active'
RETURN f.statement AS fact,
       collect(DISTINCT se.content) AS supporting,
       collect(DISTINCT ce.content) AS contradicting,
       f.confidence AS confidence
ORDER BY size(collect(DISTINCT ce.content)) DESC
```

### 2. Evidence Traceability Chain
```cypher
// Trace: Response → Knowledge → Evidence → Source
MATCH (f:Fact)-[:ABOUT]->(e:Entity {name: $entity_name})
MATCH (f)<-[:SUPPORTS]-(ev:Evidence)-[:EXTRACTED_FROM]->(s:Source)
WHERE f.topic = $topic OR $topic IS NULL
RETURN f.statement AS fact,
       f.confidence AS confidence,
       ev.content AS evidence,
       ev.type AS evidence_type,
       s.title AS source_title,
       s.url AS source_url,
       s.type AS source_type
ORDER BY f.confidence DESC
```

### 3. Knowledge Evolution History
```cypher
// Track how a fact evolved over time
MATCH path = (original:Fact)-[:EVOLVED_TO*]->(current:Fact)
WHERE original.id = $fact_id
RETURN [n IN nodes(path) | {
  statement: n.statement,
  status: n.status,
  confidence: n.confidence,
  updated: n.last_updated
}] AS evolution_chain
```

### 4. Relationship Exploration (with topic scoping)
```cypher
// Explore all connections of an entity within 2 hops
MATCH path = (e:Entity {id: $entity_id})-[r*1..2]-(connected)
WHERE all(node IN nodes(path) WHERE node.status = 'active')
  AND (connected.topic = $topic OR $topic IS NULL)
RETURN path
```

### 5. Influence Mapping (with timeout protection)
```cypher
// Find all entities that influence a given entity (transitive, max 3 hops)
MATCH path = (influencer:Entity)-[:INFLUENCES*1..3]->(target:Entity {id: $entity_id})
RETURN influencer.name AS influencer,
       length(path) AS distance,
       [r IN relationships(path) | r.strength] AS strengths
ORDER BY distance ASC
LIMIT 50
```

### 6. Dependency Discovery
```cypher
// Find dependency chains (max 4 hops)
MATCH path = (dep:Entity)-[:DEPENDS_ON*1..4]->(target:Entity {id: $entity_id})
RETURN dep.name AS dependency,
       length(path) AS depth,
       [n IN nodes(path) | n.name] AS chain
LIMIT 50
```

### 7. Decision Traceability (NEW)
```cypher
// Trace a decision back to its supporting facts and evidence
MATCH (d:Decision {id: $decision_id})-[:BASED_ON]->(f:Fact)
MATCH (f)<-[:SUPPORTS]-(ev:Evidence)-[:EXTRACTED_FROM]->(s:Source)
RETURN d.statement AS decision,
       d.context AS context,
       f.statement AS supporting_fact,
       ev.content AS evidence,
       s.title AS source
```

### 8. Open Questions (NEW)
```cypher
// Find unanswered questions for a topic
MATCH (q:Question)
WHERE q.status = 'open' AND q.topic = $topic
OPTIONAL MATCH (q)-[:ABOUT]->(e:Entity)
RETURN q.question AS question,
       q.context AS context,
       collect(e.name) AS related_entities
ORDER BY q.created_at DESC
```

### 9. Fact Deduplication Check (NEW)
```cypher
// Find potentially duplicate facts about the same entities
MATCH (f1:Fact)-[:ABOUT]->(e:Entity)<-[:ABOUT]-(f2:Fact)
WHERE f1.id < f2.id
  AND f1.status = 'active'
  AND f2.status = 'active'
  AND f1.topic = f2.topic
RETURN f1.statement AS fact_a,
       f2.statement AS fact_b,
       e.name AS shared_entity,
       f1.confidence AS confidence_a,
       f2.confidence AS confidence_b
```

## Implementation Notes

### Graph Service Interface
```python
class GraphService:
    # --- Core CRUD ---
    async def create_entity(self, entity: EntityCreate) -> Entity
    async def create_fact(self, fact: FactCreate, entity_ids: list[str], evidence_ids: list[str]) -> Fact
    async def create_evidence(self, evidence: EvidenceCreate, source_id: str) -> Evidence
    async def create_decision(self, decision: DecisionCreate, entity_ids: list[str], fact_ids: list[str]) -> Decision
    async def create_question(self, question: QuestionCreate, entity_ids: list[str]) -> Question
    async def create_relationship(self, source_id: str, target_id: str, rel_type: str, properties: dict) -> None
    
    # --- Batch Operations (for pipelines) ---
    async def batch_create_entities(self, entities: list[EntityCreate]) -> list[Entity]
    async def batch_create_facts(self, facts: list[FactWithLinks]) -> list[Fact]
    async def batch_create_evidence(self, evidence: list[EvidenceCreate]) -> list[Evidence]
    
    # --- Knowledge Queries ---
    async def detect_contradictions(self, fact: Fact) -> list[Contradiction]
    async def get_traceability_chain(self, fact_id: str) -> TraceabilityChain
    async def get_decision_trace(self, decision_id: str) -> DecisionTrace
    async def get_open_questions(self, topic: str) -> list[Question]
    async def find_duplicate_facts(self, fact: Fact, topic: str) -> list[Fact]
    
    # --- Evolution ---
    async def evolve_fact(self, old_fact_id: str, new_fact: FactCreate, evolution_type: str) -> Fact
    async def answer_question(self, question_id: str, answer_fact_id: str) -> None
    
    # --- Graph Exploration ---
    async def get_entity_neighborhood(self, entity_id: str, depth: int = 2, topic: str = None) -> SubGraph
    async def find_influence_paths(self, entity_id: str) -> list[InfluencePath]
    async def get_knowledge_stats(self, topic: str = None) -> KnowledgeStats
    async def get_graph_for_visualization(self, topic: str = None, limit: int = 200) -> VisualizationGraph
```

### Connection Management
- Use `neo4j` Python async driver
- Connection pooling with max 50 connections
- All queries use parameterized statements (never string interpolation)
- Transaction management: read transactions for queries, write transactions for mutations
- Retry logic for transient failures
- **Query timeout: 30 seconds** for all queries to prevent runaway path traversals

### Indexing Strategy
- Unique constraint on `Entity.id`, `Fact.id`, `Evidence.id`, `Source.id`, `Decision.id`, `Question.id`
- Index on `Entity.name` for fast lookup
- Index on `Fact.status` for filtering active facts
- Composite index on `Entity(name, topic)` for scoped lookups
- Composite index on `Fact(status, confidence)` for quality queries
- Index on `*.topic` for all node types — enables topic-scoped queries
- Full-text index on `Fact.statement` for text search
