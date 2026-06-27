from app.models.domain import ExtractionResult, Entity, Fact, Decision, Question
from app.services.llm_service import LLMService
import structlog
from textwrap import dedent

logger = structlog.get_logger(__name__)

EXTRACTION_SYSTEM_PROMPT = dedent("""
    You are an expert AI knowledge extractor.
    Your goal is to extract structured knowledge from the provided text chunk.
    You must extract Entities, Facts, Decisions, and Questions.
    
    Guidelines:
    - Entities: People, places, organizations, concepts. Include a type and description.
    - Facts: Atomic, verifiable statements. Must be standalone and self-contained.
    - Decisions: Explicit choices made, conclusions reached, or policies set in the text.
    - Questions: Unresolved issues, future research questions, or explicit questions asked in the text.
    - Confidence: Assign a confidence score (0.0 to 1.0) based on how explicitly the text states the extracted item.
    - Topic: Assign a single, consistent 1-3 word topic to categorize the extraction.
    
    If an item type is not present in the text, return an empty list for that type.
""")

class ExtractionService:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def extract_knowledge(self, chunk: str, chunk_index: int, source_id: str) -> ExtractionResult:
        """Extract structured knowledge from a chunk of text."""
        
        user_prompt = f"Text Chunk to process:\n\n{chunk}"
        
        logger.info("Starting knowledge extraction for chunk", chunk_index=chunk_index, source_id=source_id)
        
        # We define a temporary Pydantic model for the exact output we want the LLM to produce
        from pydantic import BaseModel, Field
        from typing import List
        
        class LLMExtractionOutput(BaseModel):
            entities: List[Entity] = Field(description="List of extracted entities")
            facts: List[Fact] = Field(description="List of extracted facts")
            decisions: List[Decision] = Field(description="List of extracted decisions")
            questions: List[Question] = Field(description="List of extracted questions")
            extraction_confidence: float = Field(description="Overall confidence in this extraction")
            
        result: LLMExtractionOutput = await self.llm.extract_structured(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=LLMExtractionOutput,
            temperature=0.1
        )
        
        # Map to final output
        final_result = ExtractionResult(
            entities=result.entities,
            facts=result.facts,
            decisions=result.decisions,
            questions=result.questions,
            source_id=source_id,
            chunk_index=chunk_index,
            extraction_confidence=result.extraction_confidence
        )
        
        logger.info("Extraction complete", 
                    entities=len(final_result.entities), 
                    facts=len(final_result.facts),
                    chunk_index=chunk_index)
                    
        return final_result
