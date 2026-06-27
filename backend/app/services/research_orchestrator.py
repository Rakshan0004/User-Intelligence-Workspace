import asyncio
import uuid
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import event_bus
from app.services.search_service import SearchService
from app.services.noise_filter import NoiseFilter
from app.services.llm_service import LLMService
from app.services.graph_service import GraphService
from app.services.vector_service import VectorService
from app.services.memory_manager import MemoryManager
from app.api.routes.upload import process_url_background
import structlog

logger = structlog.get_logger(__name__)

class ResearchOrchestrator:
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
        
        self.llm = LLMService()
        self.search = SearchService()
        self.noise_filter = NoiseFilter(self.llm)

    async def run_pipeline(self, session_id: str, topic: str):
        """Execute the full autonomous research pipeline (DAG)."""
        logger.info("Starting research pipeline", session_id=session_id, topic=topic)
        await event_bus.emit(session_id, "STAGE_UPDATE", {"stage": "DECOMPOSITION", "message": f"Analyzing topic: {topic}"})
        
        try:
            # 1. Topic Decomposition (simplified for MVP: just use the topic)
            queries = [topic, f"What are the core concepts of {topic}?", f"Recent developments in {topic}"]
            await event_bus.emit(session_id, "QUERIES_GENERATED", {"queries": queries})
            
            # 2. Web Search
            await event_bus.emit(session_id, "STAGE_UPDATE", {"stage": "SEARCH", "message": "Searching the web..."})
            all_results = []
            for query in queries:
                results = await self.search.search(query)
                all_results.extend(results)
                
            # Deduplicate by URL
            unique_results = {r['url']: r for r in all_results}.values()
            
            # 3. Noise Filter
            await event_bus.emit(session_id, "STAGE_UPDATE", {"stage": "FILTERING", "message": "Evaluating sources..."})
            approved_urls = []
            for res in unique_results:
                eval_res = await self.noise_filter.evaluate_source(res['url'], res.get('title', ''), res.get('content', ''), topic)
                if eval_res.is_relevant and eval_res.information_density > 0.3:
                    approved_urls.append(res['url'])
                    await event_bus.emit(session_id, "SOURCE_APPROVED", {"url": res['url'], "reason": eval_res.reason})
                else:
                    await event_bus.emit(session_id, "SOURCE_REJECTED", {"url": res['url'], "reason": eval_res.reason})

            # Limit to top 3 for MVP speed
            approved_urls = approved_urls[:3]
            
            # 4. Ingest, Chunk, Extract, Graph (reuse the upload logic)
            await event_bus.emit(session_id, "STAGE_UPDATE", {"stage": "EXTRACTION", "message": f"Extracting knowledge from {len(approved_urls)} sources..."})
            
            # Run ingestion concurrently
            ingest_tasks = []
            for url in approved_urls:
                # We pass a dummy upload_id for now since this isn't triggered by a direct user file upload
                dummy_upload_id = uuid.uuid4() 
                task = asyncio.create_task(process_url_background(url, topic, dummy_upload_id, self.db, self.graph, self.vector))
                ingest_tasks.append(task)
                
            await asyncio.gather(*ingest_tasks, return_exceptions=True)
            
            # 5. Memory Synthesis
            await event_bus.emit(session_id, "STAGE_UPDATE", {"stage": "SYNTHESIS", "message": "Synthesizing research findings into memory..."})
            
            # Pull the neighborhood from the graph to synthesize
            # (In a full version, we'd query the graph for the topic and summarize)
            synthesis = f"Successfully researched {topic} across {len(approved_urls)} sources and ingested into the Knowledge Graph."
            
            # Complete
            await event_bus.emit(session_id, "COMPLETE", {"synthesis": synthesis})
            logger.info("Research pipeline completed", session_id=session_id)
            
        except Exception as e:
            logger.error("Research pipeline failed", session_id=session_id, error=str(e))
            await event_bus.emit(session_id, "ERROR", {"message": str(e)})
