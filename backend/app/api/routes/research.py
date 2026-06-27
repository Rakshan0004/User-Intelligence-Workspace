from fastapi import APIRouter, Depends, BackgroundTasks, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.api.dependencies import get_db, get_graph_service, get_vector_service, get_memory_manager
from app.services.graph_service import GraphService
from app.services.vector_service import VectorService
from app.services.memory_manager import MemoryManager
from app.services.research_orchestrator import ResearchOrchestrator
from app.core.event_bus import event_bus
from app.models.db_models import Session, SessionMode

import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/research", tags=["Research"])

class ResearchStartRequest(BaseModel):
    topic: str

@router.post("")
async def start_research(
    request: ResearchStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    graph: GraphService = Depends(get_graph_service),
    vector: VectorService = Depends(get_vector_service),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """Start an autonomous research session."""
    
    # 1. Create session in Postgres
    session_id = uuid.uuid4()
    db_session = Session(
        id=session_id,
        topic=request.topic,
        mode=SessionMode.research
    )
    db.add(db_session)
    await db.commit()
    
    # 2. Initialize orchestrator
    orchestrator = ResearchOrchestrator(db, graph, vector, memory)
    
    # 3. Fire and forget
    background_tasks.add_task(orchestrator.run_pipeline, str(session_id), request.topic)
    
    return {"session_id": str(session_id), "topic": request.topic, "status": "started"}

@router.get("/{session_id}/stream")
async def stream_research_events(session_id: str, request: Request):
    """Stream Server-Sent Events for a specific research session."""
    
    async def event_generator():
        try:
            async for event in event_bus.event_generator(session_id):
                if await request.is_disconnected():
                    logger.info("Client disconnected from SSE stream", session_id=session_id)
                    break
                yield event
        except asyncio.CancelledError:
            logger.info("SSE Stream cancelled", session_id=session_id)
            
    return EventSourceResponse(event_generator())
