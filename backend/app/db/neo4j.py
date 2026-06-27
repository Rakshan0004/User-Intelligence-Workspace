from neo4j import AsyncGraphDatabase, AsyncDriver
from app.core.config import settings

class Neo4jConnection:
    def __init__(self):
        self.driver: AsyncDriver | None = None

    async def connect(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
        )

    async def close(self):
        if self.driver is not None:
            await self.driver.close()

neo4j_conn = Neo4jConnection()

def get_graph() -> AsyncDriver:
    if not neo4j_conn.driver:
        raise RuntimeError("Neo4j driver not initialized")
    return neo4j_conn.driver
