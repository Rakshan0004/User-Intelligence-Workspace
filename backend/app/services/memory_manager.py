from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import Memory as DBMemory, MemoryEvolutionLog, MemoryType
from app.models.domain import Memory as PydanticMemory
from typing import Optional
import uuid
import structlog

logger = structlog.get_logger(__name__)

class MemoryManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_memory(self, session_id: uuid.UUID, content: str, type: MemoryType, topic: str, confidence: float = 0.8) -> PydanticMemory:
        """Create a new base memory (learning state)."""
        memory = DBMemory(
            session_id=session_id,
            content=content,
            type=type,
            topic=topic,
            confidence=confidence
        )
        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)
        
        await self._log_evolution(memory.id, "created", None, content, "Initial learning")
        logger.info("Recorded new memory", memory_id=str(memory.id))
        return PydanticMemory.model_validate(memory)

    async def evolve_memory(self, memory_id: uuid.UUID, action: str, new_content: str, reason: str) -> PydanticMemory:
        """Evolve an existing memory based on the state machine."""
        
        memory = await self.db.get(DBMemory, memory_id)
        if not memory:
            raise ValueError(f"Memory {memory_id} not found")

        old_content = memory.content

        if action == "reinforce":
            memory.confidence = min(1.0, memory.confidence + 0.1)
            memory.type = MemoryType.reinforcement
        elif action == "modify":
            memory.content = new_content
            memory.type = MemoryType.update
        elif action == "contradict":
            memory.type = MemoryType.contradiction
            memory.confidence = max(0.0, memory.confidence - 0.3)
            memory.is_active = memory.confidence > 0.2
        elif action == "deprecate":
            memory.type = MemoryType.deprecation
            memory.is_active = False

        await self.db.commit()
        await self._log_evolution(memory.id, action, old_content, memory.content, reason)
        logger.info("Evolved memory", memory_id=str(memory.id), action=action)
        return PydanticMemory.model_validate(memory)

    async def _log_evolution(self, memory_id: uuid.UUID, action: str, old_content: Optional[str], new_content: str, reason: str):
        log = MemoryEvolutionLog(
            memory_id=memory_id,
            action=action,
            old_content=old_content,
            new_content=new_content,
            reason=reason
        )
        self.db.add(log)
        await self.db.commit()
