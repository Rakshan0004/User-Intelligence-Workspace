import httpx
import trafilatura
from app.core.exceptions import IngestionError
import structlog

logger = structlog.get_logger(__name__)

class URLProcessor:
    async def fetch_and_extract(self, url: str) -> str:
        """Fetch a URL and extract the main body text."""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Trafilatura extracts main content and strips boilerplate
                extracted_text = trafilatura.extract(
                    response.text,
                    include_links=False,
                    include_images=False,
                    include_tables=True
                )
                
                if not extracted_text:
                    logger.warning("Trafilatura failed to extract text, raw HTML was returned", url=url)
                    raise IngestionError("Could not extract meaningful text from URL")
                    
                logger.info("Successfully extracted text from URL", url=url, length=len(extracted_text))
                return extracted_text
                
        except httpx.HTTPError as e:
            logger.error("HTTP error while fetching URL", url=url, error=str(e))
            raise IngestionError(f"Failed to fetch URL: {str(e)}")
        except Exception as e:
            logger.error("Unexpected error processing URL", url=url, error=str(e))
            raise IngestionError(f"Error processing URL: {str(e)}")
