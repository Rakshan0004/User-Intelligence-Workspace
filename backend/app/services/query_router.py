from pydantic import BaseModel, Field
from app.services.llm_service import LLMService
import structlog
from typing import List

logger = structlog.get_logger(__name__)

class QueryIntent(BaseModel):
    category: str = Field(description="Must be one of: factual, relational, contradictions, exploratory, comparative")
    confidence: float = Field(ge=0.0, le=1.0)
    entities: List[str] = Field(description="Key entities mentioned in the query")
    reasoning: str = Field(description="Why this category was chosen")

class QueryRouter:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def route_query(self, user_query: str) -> QueryIntent:
        """Route query to determine retrieval strategy."""
        
        system_prompt = """
        You are a query router for a knowledge graph + vector database system.
        Classify the user's intent into exactly one of these categories:
        - factual: Specific questions about facts (e.g. "When was X born?", "What is the capital of Y?")
        - relational: Questions about connections between entities (e.g. "How is X related to Y?")
        - contradictions: Asking about conflicting information or debates (e.g. "Is there any disagreement about X?")
        - exploratory: Broad, open-ended research (e.g. "Tell me about X", "What is the history of Y?")
        - comparative: Comparing two or more things (e.g. "What is the difference between X and Y?")
        """
        
        try:
            intent = await self.llm.extract_structured(
                system_prompt=system_prompt,
                user_prompt=f"Query: {user_query}",
                response_model=QueryIntent,
                temperature=0.0
            )
            logger.info("Query routed", category=intent.category, entities=intent.entities)
            return intent
        except Exception as e:
            logger.error("Query routing failed, defaulting to exploratory", error=str(e))
            return QueryIntent(
                category="exploratory",
                confidence=0.1,
                entities=[],
                reasoning="Fallback due to error"
            )
