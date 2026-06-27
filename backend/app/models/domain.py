from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
import uuid

class BaseDomainModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# --- Graph Node Models ---

class Entity(BaseDomainModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_count: int = 1
    topic: str
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deprecated_at: Optional[datetime] = None

class Fact(BaseDomainModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_count: int = 1
    supporting_evidence_count: int = 1
    contradicting_evidence_count: int = 0
    topic: str
    status: str = "active"
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    previous_version_id: Optional[str] = None

class Evidence(BaseDomainModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    chunk_index: int
    chunk_total: int
    type: str
    reliability: float = Field(ge=0.0, le=1.0, default=1.0)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    source_id: str

class Source(BaseDomainModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    title: str
    type: str
    quality_score: float = Field(ge=0.0, le=1.0, default=0.8)
    topic: str
    chunk_count: int
    ingested_at: datetime = Field(default_factory=datetime.utcnow)

class Decision(BaseDomainModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    statement: str
    context: str
    implications: str
    made_by: str
    confidence: float = Field(ge=0.0, le=1.0)
    topic: str
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Question(BaseDomainModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    context: str
    status: str = "open"
    answer_summary: Optional[str] = None
    topic: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Insight(BaseDomainModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    type: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    topic: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class Memory(BaseDomainModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    type: str
    content: str
    topic: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


# --- Configuration & Utility Models ---

class ChunkingConfig(BaseModel):
    strategy: str = "semantic"
    max_chunk_tokens: int = 1000
    overlap_tokens: int = 200
    min_chunk_tokens: int = 100

class ResearchConfig(BaseModel):
    max_sources: int = 10
    depth: int = 2
    chunking_config: ChunkingConfig = Field(default_factory=ChunkingConfig)

class ExtractionResult(BaseModel):
    entities: List[Entity]
    facts: List[Fact]
    decisions: List[Decision]
    questions: List[Question]
    source_id: str
    chunk_index: int
    extraction_confidence: float

class EvolutionResult(BaseModel):
    evolutions: List[Any]
