from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api import api_router
from app.core.config import settings

# Create FastAPI app instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade AI Stock Market Prediction API for Indian Markets (NSE/BSE).",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include core API router under api/v1 prefix
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["healthcheck"])
async def root():
    """Healthcheck endpoint returning service state metadata."""
    return {
        "status": "online",
        "app_name": settings.PROJECT_NAME,
        "api_version": "1.0.0",
        "docs_url": "/docs",
    }
