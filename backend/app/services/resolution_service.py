from typing import List, Dict, Any
from app.models.domain import Entity
from app.services.graph_service import GraphService
import structlog
import uuid

logger = structlog.get_logger(__name__)

class EntityResolutionService:
    def __init__(self, graph_service: GraphService):
        self.graph = graph_service

    async def resolve_entities(self, new_entities: List[Entity]) -> List[Entity]:
        """
        Compare newly extracted entities against existing graph entities.
        If a match is found (same name/type), we use the existing ID.
        Otherwise, we keep the new ID.
        """
        if not new_entities:
            return []

        resolved_entities = []
        
        # In a production system, this would be an embedding similarity search in Qdrant 
        # combined with a Cypher fuzzy match. For this MVP, we do an exact match lookup
        # on name and type using Cypher to prevent basic duplication.
        
        query = """
        UNWIND $candidates AS candidate
        OPTIONAL MATCH (e:Entity {name: candidate.name, type: candidate.type})
        RETURN candidate, e.id AS existing_id
        """
        
        candidates = [{"name": e.name, "type": e.type} for e in new_entities]
        
        async with self.graph.driver.session() as session:
            result = await session.run(query, candidates=candidates)
            records = [record.data() async for record in result]
            
            # Map back to the original entities
            for record, entity in zip(records, new_entities):
                existing_id = record.get("existing_id")
                if existing_id:
                    # Match found! Use existing ID, maybe boost confidence/source_count
                    logger.info("Entity resolved to existing graph node", name=entity.name, existing_id=existing_id)
                    entity.id = existing_id
                    entity.source_count += 1
                else:
                    logger.info("New entity discovered", name=entity.name, new_id=entity.id)
                    
                resolved_entities.append(entity)
                
        return resolved_entities
