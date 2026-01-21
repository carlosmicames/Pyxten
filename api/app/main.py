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

# ✅ CORS: Allow Vercel + local dev
# Use allow_origin_regex for Vercel preview/prod domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://pyxten-6mncuruaf-carlos-micames-projects.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
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
    return {"status": "ok", "service": "Pyxten API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}
