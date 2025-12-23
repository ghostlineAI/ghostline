"""
GhostLine API Service

A multi-agent AI ghost-writing platform API.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.base import engine


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to handle X-Forwarded headers from load balancer"""

    async def dispatch(self, request: Request, call_next):
        # Check for X-Forwarded-Proto header
        forwarded_proto = request.headers.get("x-forwarded-proto")
        if forwarded_proto:
            # Update the request scheme
            request._url = request.url.replace(scheme=forwarded_proto)

        response = await call_next(request)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    print("Starting up GhostLine API...")
    yield
    # Shutdown
    print("Shutting down GhostLine API...")


# Create FastAPI instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    # Important: Use the forwarded headers when behind proxy
    root_path_in_servers=False,
)

# Set up middleware
# IMPORTANT: Add ProxyHeadersMiddleware FIRST (before CORS)
app.add_middleware(ProxyHeadersMiddleware)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.dev.ghostline.ai", "localhost", "127.0.0.1", "*"],
)


# Global exception handler that preserves CORS headers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all exceptions and ensure CORS headers are included."""
    origin = request.headers.get("origin")
    headers = {}
    
    # Add CORS headers if origin is allowed
    if origin in settings.BACKEND_CORS_ORIGINS:
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    
    # Log the error
    import traceback
    print(f"ERROR: {exc}")
    print(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=headers
    )


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to GhostLine API",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    # Test database connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection established")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        # Don't fail startup, allow health endpoint to report status


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    # Clean up database connections
    engine.dispose()
    print("✓ Database connections closed")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    ) 