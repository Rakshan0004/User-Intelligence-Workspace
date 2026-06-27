import asyncio
from typing import List, Dict, Any, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.services.graph_service import GraphService
from app.services.vector_service import VectorService
from app.services.memory_manager import MemoryManager
from app.services.query_router import QueryRouter
from app.services.insight_engine import InsightEngine
from app.services.llm_service import LLMService
from app.core.event_bus import event_bus
import structlog
from google import genai
from app.core.config import settings

logger = structlog.get_logger(__name__)

class ChatOrchestrator:
    def __init__(
        self,
        db: AsyncSession,
        graph: GraphService,
        vector: VectorService,
        memory: MemoryManager
    ):
        self.db = db
        self.graph = graph
        self.vector = vector
        self.memory = memory
        
        self.llm_service = LLMService()
        self.query_router = QueryRouter(self.llm_service)
        self.insight_engine = InsightEngine(self.graph)

    async def _gather_context(self, query: str, topic: str) -> str:
        """Gather context based on intent."""
        
        # 1. Route the query
        intent = await self.query_router.route_query(query)
        logger.info("Chat orchestrator routed query", intent=intent.category)
        
        context_parts = []
        
        # 2. Retrieve Vector Context (always useful for exact facts)
        vector_results = await self.vector.semantic_search(
            query=query, 
            collection=self.vector.knowledge_collection, 
            top_k=3, 
            topic=topic
        )
        if vector_results:
            context_parts.append("--- Semantic Search Results ---")
            for r in vector_results:
                context_parts.append(r.payload.get('statement', ''))
                
        # 3. Retrieve Graph Context based on intent
        if intent.category in ["relational", "comparative", "exploratory"] and intent.entities:
            context_parts.append("--- Graph Neighborhood ---")
            for entity in intent.entities:
                summary = await self.insight_engine.generate_neighborhood_summary(entity)
                context_parts.append(summary)
                
        if intent.category == "contradictions":
            context_parts.append("--- Known Contradictions ---")
            insights = await self.insight_engine.detect_contradictions(topic)
            for insight in insights:
                context_parts.append(insight.content)
                
        return "\n\n".join(context_parts)

    async def stream_response(self, session_id: str, query: str, topic: str):
        """Gather context and stream LLM response via the event bus."""
        logger.info("Starting chat response stream", session_id=session_id)
        
        try:
            # 1. Assemble Context
            await event_bus.emit(session_id, "STATUS", {"message": "Thinking and gathering context..."})
            context = await self._gather_context(query, topic)
            
            # 2. Build Prompt
            system_prompt = f"""
            You are an intelligence workspace assistant.
            Use the following retrieved context to answer the user's question.
            If the context does not contain the answer, say so clearly. Do not hallucinate.
            
            Context:
            {context}
            """
            
            # 3. Stream from Gemini directly to the Event Bus
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            stream = client.aio.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=query,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_prompt,
                )
            )
            
            full_response = ""
            async for chunk in stream:
                if chunk.text:
                    full_response += chunk.text
                    await event_bus.emit(session_id, "TOKEN", {"token": chunk.text})
                    
            # 4. Save to Memory (as a user interaction)
            await self.memory.record_memory(
                session_id=uuid.UUID(session_id),
                content=f"Q: {query}\nA: {full_response}",
                type="learning",  # Using the enum string value
                topic=topic,
                confidence=1.0
            )
            
            await event_bus.emit(session_id, "COMPLETE", {"message": "Done streaming"})
            logger.info("Chat stream completed", session_id=session_id)
            
        except Exception as e:
            logger.error("Chat streaming failed", session_id=session_id, error=str(e))
            await event_bus.emit(session_id, "ERROR", {"message": str(e)})
