from typing import List, Dict, Any
from app.services.graph_service import GraphService
from app.models.domain import Insight
import structlog
import uuid

logger = structlog.get_logger(__name__)

class InsightEngine:
    def __init__(self, graph: GraphService):
        self.graph = graph

    async def detect_contradictions(self, topic: str) -> List[Insight]:
        """Detect CONTRADICTS edges in the graph for a specific topic."""
        query = """
        MATCH (f1:Fact)-[r:CONTRADICTS]->(f2:Fact)
        WHERE f1.topic = $topic OR f2.topic = $topic
        RETURN f1.statement AS fact1, f2.statement AS fact2, r.reason AS reason
        LIMIT 5
        """
        
        insights = []
        async with self.graph.driver.session() as session:
            result = await session.run(query, topic=topic)
            async for record in result:
                content = f"Contradiction found: '{record['fact1']}' vs '{record['fact2']}'. Reason: {record['reason']}"
                insight = Insight(
                    content=content,
                    type="contradiction",
                    category="conflict_detection",
                    confidence=0.9,
                    topic=topic
                )
                insights.append(insight)
                
        logger.info("Insight engine detected contradictions", count=len(insights), topic=topic)
        return insights

    async def generate_neighborhood_summary(self, entity_name: str) -> str:
        """Get a summary of an entity's immediate graph neighborhood."""
        query = """
        MATCH (e:Entity {name: $name})-[r]-(connected)
        RETURN type(r) AS rel_type, connected.name AS connected_name, labels(connected)[0] AS connected_type
        LIMIT 10
        """
        
        connections = []
        async with self.graph.driver.session() as session:
            result = await session.run(query, name=entity_name)
            async for record in result:
                connections.append(f"- {record['rel_type']} -> {record['connected_type']} ({record['connected_name']})")
                
        if not connections:
            return "No strong neighborhood connections found."
            
        summary = f"Entity '{entity_name}' is connected to:\n" + "\n".join(connections)
        return summary
