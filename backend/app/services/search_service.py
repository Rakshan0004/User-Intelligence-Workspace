import httpx
from typing import List, Dict, Any
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)

class SearchService:
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com/search"

    async def search(self, query: str, depth: str = "basic", max_results: int = 5) -> List[Dict[str, Any]]:
        """Search the web using Tavily API."""
        if not self.api_key or self.api_key.startswith("tvly-..."):
            logger.warning("Tavily API key not set, returning mock results")
            return [
                {"url": "https://example.com/mock1", "title": "Mock Result 1", "content": "Mock content 1"},
                {"url": "https://example.com/mock2", "title": "Mock Result 2", "content": "Mock content 2"}
            ]

        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": depth,
                    "include_answer": False,
                    "include_raw_content": False,
                    "max_results": max_results
                }
                
                response = await client.post(self.base_url, json=payload, timeout=15.0)
                response.raise_for_status()
                
                data = response.json()
                results = data.get("results", [])
                
                logger.info("Tavily search completed", query=query, results_count=len(results))
                return results
                
        except Exception as e:
            logger.error("Tavily search failed", query=query, error=str(e))
            return []
