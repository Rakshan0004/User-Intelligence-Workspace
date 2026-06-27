from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import structlog

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract from header or generate new
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # Add to request state so downstream handlers can access it if needed
        request.state.correlation_id = correlation_id
        
        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        
        response = await call_next(request)
        
        # Add to response header
        response.headers["X-Correlation-ID"] = correlation_id
        return response
