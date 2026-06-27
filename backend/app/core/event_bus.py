import asyncio
from typing import Dict, Any, AsyncGenerator
import json
import structlog
import uuid

logger = structlog.get_logger(__name__)

class ResearchEventBus:
    """Manages Server-Sent Events (SSE) queues for active research sessions."""
    
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = {}

    def subscribe(self, session_id: str) -> asyncio.Queue:
        if session_id not in self.queues:
            self.queues[session_id] = asyncio.Queue()
            logger.info("Created SSE queue for session", session_id=session_id)
        return self.queues[session_id]

    def unsubscribe(self, session_id: str):
        if session_id in self.queues:
            del self.queues[session_id]
            logger.info("Deleted SSE queue for session", session_id=session_id)

    async def emit(self, session_id: str, event_type: str, data: Any):
        """Emit an event to the specific session's queue."""
        if session_id in self.queues:
            payload = {
                "type": event_type,
                "data": data,
                "timestamp": str(uuid.uuid1())
            }
            await self.queues[session_id].put(payload)
            
    async def event_generator(self, session_id: str) -> AsyncGenerator[str, None]:
        """Generator that yields SSE formatted strings."""
        queue = self.subscribe(session_id)
        try:
            while True:
                payload = await queue.get()
                
                # Format for Server-Sent Events
                yield f"event: {payload['type']}\ndata: {json.dumps(payload['data'])}\n\n"
                
                # Stop if we hit a terminal event
                if payload['type'] == 'COMPLETE' or payload['type'] == 'ERROR':
                    break
        finally:
            self.unsubscribe(session_id)

# Global singleton for the event bus
event_bus = ResearchEventBus()
