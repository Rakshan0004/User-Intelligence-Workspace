from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.api.dependencies import get_db, get_graph_service, get_vector_service
from app.services.graph_service import GraphService
from app.services.vector_service import VectorService
from app.services.llm_service import LLMService
from app.services.extraction_service import ExtractionService
from app.services.resolution_service import EntityResolutionService
from app.ingestion.processors.url import URLProcessor
from app.ingestion.chunker import DocumentChunker
from app.models.domain import ChunkingConfig, Source, Evidence
from app.models.db_models import UploadedFile, ProcessingStatus
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])

class URLIngestRequest(BaseModel):
    url: str
    topic: str
    session_id: str | None = None

async def process_url_background(
    url: str, 
    topic: str,
    upload_id: uuid.UUID,
    db: AsyncSession,
    graph: GraphService,
    vector: VectorService
):
    """Background task to fetch, chunk, extract, and store."""
    try:
        # 1. Fetch
        processor = URLProcessor()
        text = await processor.fetch_and_extract(url)
        
        # 2. Chunk
        chunker = DocumentChunker(ChunkingConfig(strategy="fixed"))
        chunks = chunker.chunk_document(text)
        
        # Create Source node representation
        source = Source(url=url, title=url, type="webpage", topic=topic, chunk_count=len(chunks))
        
        # Services
        llm = LLMService()
        extractor = ExtractionService(llm)
        resolver = EntityResolutionService(graph)
        
        all_entities, all_facts, all_evidence, all_decisions, all_questions = [], [], [], [], []
        
        # 3. Extract per chunk
        for i, chunk_text in enumerate(chunks):
            result = await extractor.extract_knowledge(chunk_text, i, source.id)
            
            # 4. Resolve Entities
            resolved_entities = await resolver.resolve_entities(result.entities)
            
            # Evidence object mapping
            evidence = Evidence(content=chunk_text, chunk_index=i, chunk_total=len(chunks), type="text", source_id=source.id)
            
            all_entities.extend(resolved_entities)
            all_facts.extend(result.facts)
            all_decisions.extend(result.decisions)
            all_questions.extend(result.questions)
            all_evidence.append(evidence)
            
        # 5. Write to Graph
        await graph.batch_create_entities(all_entities)
        await graph.batch_create_facts(all_facts, all_evidence, source.id)
        
        # 6. Write to Vector Store
        await vector.upsert_knowledge_embeddings(all_facts)
        
        # Update Postgres Status
        file_record = await db.get(UploadedFile, upload_id)
        if file_record:
            file_record.processing_status = ProcessingStatus.completed
            file_record.source_id = source.id
            await db.commit()
            
        logger.info("Background URL ingestion completed successfully", url=url)
        
    except Exception as e:
        logger.error("Background URL ingestion failed", url=url, error=str(e))
        file_record = await db.get(UploadedFile, upload_id)
        if file_record:
            file_record.processing_status = ProcessingStatus.failed
            file_record.error_message = str(e)
            await db.commit()

@router.post("/url")
async def ingest_url(
    request: URLIngestRequest, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    graph: GraphService = Depends(get_graph_service),
    vector: VectorService = Depends(get_vector_service)
):
    """Endpoint to trigger URL ingestion."""
    
    # Record in Postgres
    upload_record = UploadedFile(
        filename=request.url,
        file_type="url",
        session_id=uuid.UUID(request.session_id) if request.session_id else None,
        processing_status=ProcessingStatus.pending
    )
    db.add(upload_record)
    await db.commit()
    await db.refresh(upload_record)
    
    # Launch background task
    background_tasks.add_task(
        process_url_background, 
        request.url, 
        request.topic, 
        upload_record.id, 
        db, 
        graph, 
        vector
    )
    
    return {"message": "Ingestion started", "upload_id": upload_record.id}
