import tiktoken
from typing import List
from app.models.domain import ChunkingConfig
import structlog

logger = structlog.get_logger(__name__)

class DocumentChunker:
    def __init__(self, config: ChunkingConfig):
        self.config = config
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def chunk_document(self, text: str) -> List[str]:
        if self.config.strategy == "fixed":
            return self._fixed_chunk(text)
        elif self.config.strategy == "semantic":
            # Real semantic chunking requires an NLP model or LLM.
            # Falling back to fixed for this MVP.
            logger.info("Semantic chunking not fully implemented, falling back to fixed")
            return self._fixed_chunk(text)
        else:
            raise ValueError(f"Unknown chunking strategy: {self.config.strategy}")

    def _fixed_chunk(self, text: str) -> List[str]:
        tokens = self.encoding.encode(text)
        chunks = []
        
        i = 0
        while i < len(tokens):
            end = min(i + self.config.max_chunk_tokens, len(tokens))
            chunk_tokens = tokens[i:end]
            
            if len(chunk_tokens) >= self.config.min_chunk_tokens or len(chunks) == 0:
                chunks.append(self.encoding.decode(chunk_tokens))
                
            i += self.config.max_chunk_tokens - self.config.overlap_tokens
            
        logger.info("Document chunked", total_tokens=len(tokens), chunk_count=len(chunks))
        return chunks
