"""FastAPI application entry point."""
import uuid
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import structlog

from core.config import settings
from api.routers import crypto

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting API service", env=settings.app_env)
    yield
    logger.info("Shutting down API service")


app = FastAPI(
    title="Kasparro Crypto Data API",
    description="ETL pipeline for cryptocurrency data from multiple sources",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id_and_timing(request: Request, call_next):
    """Add request ID and measure API latency."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    response = await call_next(request)
    latency_ms = (time.time() - start_time) * 1000
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-API-Latency-MS"] = f"{latency_ms:.2f}"
    
    logger.info(
        "Request completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=f"{latency_ms:.2f}"
    )
    
    return response


# Include routers
app.include_router(crypto.router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Root endpoint - serve dashboard."""
    return FileResponse("static/dashboard.html")


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "service": "Kasparro Crypto Data API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "dashboard": "/",
            "api_docs": "/docs",
            "data": "/data",
            "health": "/health",
            "stats": "/stats"
        }
    }
