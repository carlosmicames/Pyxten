"""
Pyxten API - FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import projects, validations, folders

settings = get_settings()

app = FastAPI(
    title="Pyxten API",
    description="Phase 1 Zoning Validation API for Puerto Rico",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router)
app.include_router(validations.router)
app.include_router(folders.router)


@app.get("/")
def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "Pyxten API", "version": "1.0.0"}


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy"}
