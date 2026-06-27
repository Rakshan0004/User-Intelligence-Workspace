from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from neo4j import AsyncDriver
from qdrant_client import AsyncQdrantClient

from app.db.postgres import get_db
from app.db.neo4j import get_graph
from app.db.qdrant import get_vector_store

from app.services.memory_manager import MemoryManager
from app.services.graph_service import GraphService
from app.services.vector_service import VectorService

def get_memory_manager(db: AsyncSession = Depends(get_db)) -> MemoryManager:
    return MemoryManager(db)

def get_graph_service(graph: AsyncDriver = Depends(get_graph)) -> GraphService:
    return GraphService(graph)

def get_vector_service(client: AsyncQdrantClient = Depends(get_vector_store)) -> VectorService:
    return VectorService(client)
