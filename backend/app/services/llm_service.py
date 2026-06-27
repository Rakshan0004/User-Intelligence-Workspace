from google import genai
from google.genai import types
import structlog
from typing import TypeVar, Type, Any, Dict
from pydantic import BaseModel
from app.core.config import settings
from app.core.exceptions import LLMError
import json

logger = structlog.get_logger(__name__)

T = TypeVar('T', bound=BaseModel)

class LLMService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.default_model = "gemini-2.5-flash"
        
    async def extract_structured(self, system_prompt: str, user_prompt: str, response_model: Type[T], temperature: float = 0.1) -> T:
        """Extract structured data matching a Pydantic model using Gemini Structured Outputs."""
        try:
            # We use the new google-genai SDK to request structured JSON output
            # matching the Pydantic schema
            response = await self.client.aio.models.generate_content(
                model=self.default_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_schema=response_model,
                ),
            )
            
            # Since response_schema enforces the schema, the text is valid JSON matching the model
            if response.text:
                parsed_data = json.loads(response.text)
                result = response_model.model_validate(parsed_data)
                
                # Log usage
                usage = response.usage_metadata
                logger.info("LLM structured extraction complete", 
                            prompt_tokens=usage.prompt_token_count if usage else 0, 
                            completion_tokens=usage.candidates_token_count if usage else 0,
                            model=self.default_model)
                return result
            else:
                raise LLMError("Failed to parse LLM output (empty text)")
                
        except Exception as e:
            logger.error("Unexpected error in LLM extraction", error=str(e))
            raise LLMError(f"Extraction Error: {str(e)}")
