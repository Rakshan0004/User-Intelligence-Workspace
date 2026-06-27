from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from pydantic import Field

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    DATABASE_URL: str
    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str
    QDRANT_URL: str
    QDRANT_API_KEY: Optional[str] = None
    
    GEMINI_API_KEY: str = Field(default="placeholder", description="Google Gemini API Key")
    TAVILY_API_KEY: str
    
    FILE_STORAGE_TYPE: str = "local"
    FILE_STORAGE_PATH: str = "./uploads"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=True, 
        extra="ignore"
    )

settings = Settings()
