"""
Pyxten API - FastAPI Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import get_settings
from app.routers import projects, validations, folders, chat


# Configure logging for CORS debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Pyxten API",
    description="Phase 1 Zoning Validation API for Puerto Rico",
    version="1.0.0",
)

# CORS: Allow Vercel + local dev
# Applied ONCE before any routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router)
app.include_router(validations.router)
app.include_router(folders.router)
app.include_router(chat.router)


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
    """
    origin = request.headers.get("origin", "no-origin-header")
    logger.info(f"CORS test hit from origin: {origin}")
    return {
        "status": "ok",
        "message": "CORS test endpoint reached",
        "origin_received": origin,
        "all_headers": dict(request.headers),
    }


@app.options("/cors-test")
def cors_test_preflight(request: Request):
    """
    Explicit OPTIONS handler for debugging preflight.
    Note: CORSMiddleware should handle this, but this logs if it doesn't.
    """
    origin = request.headers.get("origin", "no-origin-header")
    logger.info(f"CORS preflight OPTIONS hit from origin: {origin}")
    return JSONResponse(
        content={"message": "Preflight OK"},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        },
    )
