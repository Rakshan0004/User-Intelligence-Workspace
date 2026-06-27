from neo4j import AsyncDriver
from typing import List, Dict, Any
from app.models.domain import Entity, Fact, Evidence, Decision, Question
import structlog

logger = structlog.get_logger(__name__)

class GraphService:
    def __init__(self, driver: AsyncDriver):
        self.driver = driver

    async def batch_create_entities(self, entities: List[Entity]):
        """Merge entities into the Neo4j graph safely."""
        query = """
        UNWIND $entities AS entity
        MERGE (e:Entity {id: entity.id})
        SET e.name = entity.name,
            e.type = entity.type,
            e.description = entity.description,
            e.topic = entity.topic,
            e.confidence = entity.confidence,
            e.status = entity.status
        """
        async with self.driver.session() as session:
            await session.run(query, entities=[e.model_dump() for e in entities])
        logger.info("Merged entities to graph", count=len(entities))

    async def batch_create_facts(self, facts: List[Fact], evidence: List[Evidence], source_id: str):
        """Create Facts and link them to Evidence and Source."""
        
        # 1. Ensure Source exists
        # 2. Create Evidence nodes linked to Source
        # 3. Create Fact nodes linked to Evidence (SUPPORTS)
        
        query = """
        MERGE (s:Source {id: $source_id})
        
        WITH s
        UNWIND $evidence AS ev
        MERGE (e:Evidence {id: ev.id})
        SET e.content = ev.content, e.chunk_index = ev.chunk_index
        MERGE (e)-[:EXTRACTED_FROM]->(s)
        
        WITH s
        UNWIND $facts AS fact
        MERGE (f:Fact {id: fact.id})
        SET f.statement = fact.statement, f.confidence = fact.confidence, f.topic = fact.topic
        
        // This is a simplified linking assuming all evidence supports all facts for this chunk
        // In reality, you'd map specific evidence to specific facts.
        WITH f, s
        MATCH (e:Evidence)-[:EXTRACTED_FROM]->(s)
        MERGE (f)-[:SUPPORTED_BY]->(e)
        """
        async with self.driver.session() as session:
            await session.run(query, 
                              facts=[f.model_dump() for f in facts], 
                              evidence=[e.model_dump() for e in evidence],
                              source_id=source_id)
        logger.info("Merged facts and evidence to graph", fact_count=len(facts))

    async def get_traceability_chain(self, fact_id: str) -> Dict[str, Any]:
        """Traverse Fact -> Evidence -> Source to provide explainability."""
        query = """
        MATCH (f:Fact {id: $fact_id})-[:SUPPORTED_BY]->(e:Evidence)-[:EXTRACTED_FROM]->(s:Source)
        RETURN f AS fact, collect({evidence: e, source: s}) AS support_chain
        """
        async with self.driver.session() as session:
            result = await session.run(query, fact_id=fact_id)
            record = await result.single()
            if record:
                return {"fact": record["fact"], "chain": record["support_chain"]}
            return {}

    async def detect_contradictions(self) -> List[Dict[str, Any]]:
        """Find facts that have both SUPPORTS and FACT_CONTRADICTS edges."""
        query = """
        MATCH (f:Fact)-[:SUPPORTED_BY]->(e1:Evidence)
        MATCH (f)-[:CONTRADICTED_BY]->(e2:Evidence)
        RETURN f AS fact, collect(e1) AS supporting, collect(e2) AS contradicting
        """
        async with self.driver.session() as session:
            result = await session.run(query)
            return [record.data() async for record in result]
