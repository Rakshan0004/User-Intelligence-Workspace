from pydantic import BaseModel, Field
from app.services.llm_service import LLMService
import structlog

logger = structlog.get_logger(__name__)

class SourceEvaluation(BaseModel):
    is_relevant: bool = Field(description="Is this source highly relevant to the topic?")
    reason: str = Field(description="Reason for relevance or rejection")
    information_density: float = Field(ge=0.0, le=1.0, description="Estimated information density score")

class NoiseFilter:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def evaluate_source(self, url: str, title: str, snippet: str, topic: str) -> SourceEvaluation:
        """Use LLM to judge if a search result is worth full extraction."""
        
        system_prompt = "You are a strict research noise filter. Evaluate if the source is worth reading."
        user_prompt = f"Topic: {topic}\nURL: {url}\nTitle: {title}\nSnippet: {snippet}"
        
        try:
            eval_result = await self.llm.extract_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=SourceEvaluation,
                temperature=0.0
            )
            
            logger.info("Source evaluated", url=url, is_relevant=eval_result.is_relevant, score=eval_result.information_density)
            return eval_result
            
        except Exception as e:
            logger.warning("Noise filter failed, defaulting to relevant", url=url, error=str(e))
            # Fail open if the LLM filter fails, so we don't drop potential knowledge
            return SourceEvaluation(is_relevant=True, reason="Filter fallback", information_density=0.5)
