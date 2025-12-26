"""
GhostLine API Service

A multi-agent AI ghost-writing platform API.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.base import engine


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to handle X-Forwarded headers from load balancer"""

    async def dispatch(self, request: StarletteRequest, call_next):
        # Check for X-Forwarded-Proto header
        forwarded_proto = request.headers.get("x-forwarded-proto")
        
        # If no forwarded proto but host is api.dev.ghostline.ai, assume HTTPS
        if not forwarded_proto and request.headers.get("host") == "api.dev.ghostline.ai":
            forwarded_proto = "https"
            
        if forwarded_proto:
            # Update the request scheme
            request._url = request.url.replace(scheme=forwarded_proto)
            
        # Log the request details for debugging
        print(f"[ProxyHeaders] Host: {request.headers.get('host')}, "
              f"X-Forwarded-Proto: {request.headers.get('x-forwarded-proto')}, "
              f"Scheme: {request.url.scheme}")

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
    # CRITICAL: Disable automatic trailing slash redirects to prevent HTTPS->HTTP redirect issues
    redirect_slashes=False,
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

# Global exception handler to ensure CORS headers on all responses (including 500 errors)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions and ensure CORS headers are present."""
    print(f"[ERROR] Unhandled exception: {type(exc).__name__}: {str(exc)}")
    
    # Create a proper JSON error response with CORS headers
    response = JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "type": type(exc).__name__
        }
    )
    
    # Manually add CORS headers (since middleware didn't get to run)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

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
    return {
        "status": "healthy",
        "service": "ghostline-api",
        "version": settings.VERSION,
    }


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
