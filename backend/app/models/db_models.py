from sqlalchemy import Column, String, Integer, Float, Boolean, Text, JSON, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.db.postgres import Base

class SessionMode(str, enum.Enum):
    research = "research"
    chat = "chat"

class MemoryType(str, enum.Enum):
    learning = "learning"
    update = "update"
    reinforcement = "reinforcement"
    contradiction = "contradiction"
    deprecation = "deprecation"
    gap = "gap"

class ProcessingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class Session(Base):
    __tablename__ = "sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic = Column(String(255), nullable=True)
    mode = Column(Enum(SessionMode), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True)
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.pending)
    error_message = Column(Text, nullable=True)
    source_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Memory(Base):
    __tablename__ = "memories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    type = Column(Enum(MemoryType), nullable=False)
    content = Column(Text, nullable=False)
    topic = Column(String(255), nullable=True)
    confidence = Column(Float, default=0.5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

class MemoryEvolutionLog(Base):
    __tablename__ = "memory_evolution_log"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id = Column(UUID(as_uuid=True), ForeignKey("memories.id"), nullable=False)
    action = Column(String(20), nullable=False)
    new_content = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
