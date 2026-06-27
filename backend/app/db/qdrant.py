from qdrant_client import AsyncQdrantClient
from app.core.config import settings

class QdrantConnection:
    def __init__(self):
        self.client: AsyncQdrantClient | None = None

    async def connect(self):
        kwargs = {"url": settings.QDRANT_URL}
        if settings.QDRANT_API_KEY:
            kwargs["api_key"] = settings.QDRANT_API_KEY
            
        self.client = AsyncQdrantClient(**kwargs)

    async def close(self):
        if self.client is not None:
            await self.client.close()

qdrant_conn = QdrantConnection()

def get_vector_store() -> AsyncQdrantClient:
    if not qdrant_conn.client:
        raise RuntimeError("Qdrant client not initialized")
    return qdrant_conn.client
