from fastapi import APIRouter, Depends, BackgroundTasks, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.api.dependencies import get_db, get_graph_service, get_vector_service, get_memory_manager
from app.services.graph_service import GraphService
from app.services.vector_service import VectorService
from app.services.memory_manager import MemoryManager
from app.services.chat_orchestrator import ChatOrchestrator
from app.core.event_bus import event_bus
from app.models.db_models import Session, SessionMode
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatMessageRequest(BaseModel):
    query: str
    topic: str
    session_id: str | None = None

@router.post("")
async def send_chat_message(
    request: ChatMessageRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    graph: GraphService = Depends(get_graph_service),
    vector: VectorService = Depends(get_vector_service),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """Send a message to the chat interface. Starts a stream in the background."""
    
    # Session handling
    if not request.session_id:
        session_id = uuid.uuid4()
        db_session = Session(
            id=session_id,
            topic=request.topic,
            mode=SessionMode.chat
        )
        db.add(db_session)
        await db.commit()
    else:
        session_id = uuid.UUID(request.session_id)
        
    orchestrator = ChatOrchestrator(db, graph, vector, memory)
    
    # Execute the LLM stream in the background so it can push to the event bus
    background_tasks.add_task(orchestrator.stream_response, str(session_id), request.query, request.topic)
    
    return {"session_id": str(session_id), "status": "processing"}

@router.get("/{session_id}/stream")
async def stream_chat(session_id: str, request: Request):
    """Stream Server-Sent Events (tokens) for a specific chat session."""
    
    async def event_generator():
        try:
            async for event in event_bus.event_generator(session_id):
                if await request.is_disconnected():
                    logger.info("Client disconnected from chat SSE stream", session_id=session_id)
                    break
                yield event
        except asyncio.CancelledError:
            logger.info("Chat SSE Stream cancelled", session_id=session_id)
            
    return EventSourceResponse(event_generator())
