from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.db.postgres import engine
from app.db.neo4j import neo4j_conn
from app.db.qdrant import qdrant_conn
from app.core.middleware import CorrelationIdMiddleware
from app.core.exceptions import AppError
from app.api.routes import upload, research, chat
import structlog

logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await neo4j_conn.connect()
    await qdrant_conn.connect()
    yield
    await neo4j_conn.close()
    await qdrant_conn.close()
    await engine.dispose()

from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(title="User Intelligence Workspace", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIdMiddleware)
app.include_router(upload.router)
app.include_router(research.router)
app.include_router(chat.router)

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logger.error("Application error", error_code=exc.__class__.__name__, error_message=exc.message, details=exc.details)
    return JSONResponse(
        status_code=400,
        content=exc.to_dict()
    )

@app.get("/health")
async def health():
    return {"status": "ok"}
