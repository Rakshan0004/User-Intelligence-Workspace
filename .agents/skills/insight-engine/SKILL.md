---
name: insight-engine
description: Insight generation engine for the User Intelligence Workspace. Covers both obvious and non-obvious insight detection, pattern recognition, contradiction surfacing, weak signal detection, and emerging theme identification from accumulated knowledge.
---

# Insight Engine Skill

## Overview
The insight engine generates both **obvious insights** (clearly stated facts, decisions, risks) and **non-obvious insights** (patterns, contradictions, repeated signals, weak connections, emerging themes) from accumulated knowledge in the graph and vector store.

## Insight Types

### Obvious Insights
Directly extractable from source content:
- **Facts**: Clearly stated, well-evidenced claims
- **Decisions**: Explicit decisions or recommendations
- **Risks**: Stated risks, concerns, or warnings
- **Themes**: Major recurring topics
- **Conclusions**: Explicit conclusions drawn by sources

### Non-Obvious Insights
Require cross-referencing, pattern matching, or inference:
- **Patterns**: Recurring themes across multiple sources
- **Contradictions**: Conflicting claims from different sources
- **Repeated Signals**: Same weak signal appearing in multiple contexts
- **Weak Connections**: Entities linked through indirect paths
- **Emerging Themes**: Topics gaining mentions over time
- **Under-discussed Risks**: Risks mentioned briefly but potentially significant
- **Inferred Relationships**: Connections derived from accumulated evidence

## Insight Generation Strategies

### Strategy 1: Graph-Based Pattern Detection
```cypher
// Find entities that appear across many facts (hub nodes)
MATCH (e:Entity)<-[:ABOUT]-(f:Fact)
WHERE f.status = 'active'
WITH e, count(f) AS fact_count, collect(f.statement) AS facts
WHERE fact_count >= 3
RETURN e.name AS entity, fact_count, facts
ORDER BY fact_count DESC
```

### Strategy 2: Contradiction Surfacing
```cypher
// Find all active contradictions
MATCH (f1:Fact)-[c:CONTRADICTS]->(f2:Fact)
WHERE f1.status = 'active' AND f2.status = 'active'
MATCH (f1)<-[:SUPPORTS]-(e1:Evidence)-[:EXTRACTED_FROM]->(s1:Source)
MATCH (f2)<-[:SUPPORTS]-(e2:Evidence)-[:EXTRACTED_FROM]->(s2:Source)
RETURN f1.statement AS claim_a,
       f2.statement AS claim_b,
       s1.title AS source_a,
       s2.title AS source_b,
       c.explanation AS explanation
```

### Strategy 3: Weak Signal Detection (LLM-Powered)
```python
async def detect_weak_signals(self, topic: str) -> list[Insight]:
    """
    Find facts that:
    1. Have low confidence (< 0.5)
    2. But appear across 2+ sources
    3. Or connect to high-confidence entities
    These are potential emerging insights.
    """
    weak_facts = await self.graph_service.get_facts_by_confidence_range(0.2, 0.5)
    
    # Group by related entities
    signals = {}
    for fact in weak_facts:
        entities = await self.graph_service.get_fact_entities(fact.id)
        for entity in entities:
            signals.setdefault(entity.name, []).append(fact)
    
    # Filter: only signals appearing 2+ times
    repeated_signals = {k: v for k, v in signals.items() if len(v) >= 2}
    
    # Use LLM to synthesize weak signals into insights
    insights = await self.llm_service.synthesize_weak_signals(repeated_signals, topic)
    return insights
```

### Strategy 4: Cross-Domain Connection Discovery
```python
async def discover_cross_connections(self) -> list[Insight]:
    """
    Find entities that bridge different clusters in the knowledge graph.
    These bridge nodes often represent non-obvious connections.
    """
    # Use graph community detection or betweenness centrality
    bridges = await self.graph_service.find_bridge_entities()
    
    for bridge in bridges:
        # Get the communities it connects
        communities = await self.graph_service.get_entity_communities(bridge.id)
        
        # Generate insight about why this connection matters
        insight = await self.llm_service.explain_bridge_connection(
            bridge_entity=bridge,
            connected_communities=communities
        )
        yield insight
```

### Strategy 5: Temporal Emergence Detection
```python
async def detect_emerging_themes(self) -> list[Insight]:
    """
    Find topics/entities that are increasingly mentioned over recent sessions.
    """
    recent_sessions = await self.memory_manager.get_recent_sessions(limit=5)
    entity_frequency = defaultdict(list)
    
    for session in recent_sessions:
        memories = await self.memory_manager.get_session_memories(session.id)
        for memory in memories:
            for entity_id in memory.related_entity_ids:
                entity_frequency[entity_id].append(session.started_at)
    
    # Find entities with increasing frequency
    emerging = []
    for entity_id, timestamps in entity_frequency.items():
        if len(timestamps) >= 2 and self._is_trending(timestamps):
            entity = await self.graph_service.get_entity(entity_id)
            emerging.append(entity)
    
    return emerging
```

## Insight Engine Interface

```python
class InsightEngine:
    async def generate_all_insights(self, topic: str) -> InsightReport:
        """Run all insight strategies and compile results."""
        obvious = await self.generate_obvious_insights(topic)
        non_obvious = await self.generate_non_obvious_insights(topic)
        return InsightReport(obvious=obvious, non_obvious=non_obvious)
    
    async def generate_obvious_insights(self, topic: str) -> list[Insight]:
        """Extract clearly stated facts, decisions, risks, themes."""
    
    async def generate_non_obvious_insights(self, topic: str) -> list[Insight]:
        """Detect patterns, contradictions, signals, connections."""
    
    async def detect_contradictions(self) -> list[Contradiction]:
        """Find all contradicting facts in the knowledge graph."""
    
    async def detect_weak_signals(self, topic: str) -> list[Insight]:
        """Find recurring low-confidence signals."""
    
    async def discover_connections(self) -> list[Insight]:
        """Find non-obvious entity connections via graph analysis."""
    
    async def detect_emerging_themes(self) -> list[Insight]:
        """Find topics gaining traction across sessions."""
```

## LLM Prompts for Insight Generation

### Obvious Insight Extraction
```
System: You are an intelligence analyst. Given the following knowledge (entities, facts, 
and relationships), identify:

1. KEY FACTS: The most important, well-evidenced findings
2. DECISIONS/RECOMMENDATIONS: Any explicit decisions or recommendations
3. RISKS: Stated or implied risks and concerns
4. THEMES: Major recurring topics across the knowledge base
5. CONCLUSIONS: Well-supported conclusions

For each insight, provide:
- Statement (clear, concise)
- Confidence (0-1)
- Supporting fact IDs
- Category (fact/decision/risk/theme/conclusion)
```

### Non-Obvious Insight Synthesis
```
System: You are a strategic intelligence analyst specializing in pattern recognition.
Given the following knowledge graph data, identify NON-OBVIOUS insights:

1. PATTERNS: What recurring patterns emerge across multiple sources?
2. CONTRADICTIONS: Where do sources disagree, and what might this mean?
3. WEAK SIGNALS: What under-discussed points might be significant?
4. HIDDEN CONNECTIONS: What entities are connected in unexpected ways?
5. EMERGING THEMES: What topics seem to be gaining importance?
6. UNDER-DISCUSSED RISKS: What risks are mentioned but not fully explored?

For each insight:
- Statement (clear, actionable)
- Type (pattern/contradiction/signal/connection/theme/risk)
- Confidence (0-1)
- Reasoning: Why is this non-obvious? What evidence supports it?
- Supporting fact IDs
```

## Insight Quality & Metadata

```python
class Insight(BaseModel):
    id: str
    content: str
    type: Literal["obvious", "non_obvious"]
    category: Literal["fact", "decision", "risk", "theme", "conclusion",
                       "pattern", "contradiction", "signal", "connection", 
                       "emerging_theme", "under_discussed_risk"]
    confidence: float
    supporting_fact_ids: list[str]
    supporting_evidence_ids: list[str]
    reasoning: str | None        # For non-obvious: why this matters
    generated_at: datetime
    session_id: str
```

## Integration Points
- **Research Pipeline** → calls `generate_all_insights()` after knowledge graph construction
- **Chat** → calls relevant insight methods when user asks about patterns/contradictions
- **Knowledge Graph UI** → displays insights as overlay on graph visualization
- **Synthesis** → incorporates both obvious and non-obvious insights in reports
