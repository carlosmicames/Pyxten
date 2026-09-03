"""
Pyxten API - FastAPI Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import get_settings
from app.routers import projects, validations, folders, chat, address, pcoc, documents, billing, reviewer


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Pyxten API",
    description="Phase 1 Zoning Validation API for Puerto Rico",
    version="1.0.0",
)

# CORS Configuration
# Uses settings.cors_origins from env var CORS_ALLOWED_ORIGINS
# Default includes: https://pyxten.com, https://www.pyxten.com, localhost:3000, localhost:3001
cors_origins = settings.cors_origins
logger.info(f"CORS allowed origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    # Also allow Vercel preview deployments
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods including OPTIONS
    allow_headers=["*"],
)

# Include routers
app.include_router(address.router)
app.include_router(projects.router)
app.include_router(validations.router)
app.include_router(folders.router)
app.include_router(chat.router)
app.include_router(pcoc.router)
app.include_router(documents.router)
app.include_router(billing.router)
# Reviewer console. Isolated under /reviewer; applicant routes above are untouched.
app.include_router(reviewer.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "Pyxten API", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/cors-test")
def cors_test(request: Request):
    """
    Test endpoint to verify CORS is working.
    Returns request headers and origin info for debugging.
    CORSMiddleware handles OPTIONS preflight automatically.
    """
    origin = request.headers.get("origin", "no-origin-header")
    if settings.debug:
        logger.info(f"CORS test from origin: {origin}")
    return {
        "status": "ok",
        "message": "CORS test endpoint reached",
        "origin_received": origin,
        "allowed_origins": cors_origins,
    }
