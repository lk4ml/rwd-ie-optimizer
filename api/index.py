"""
Vercel Serverless Function Entry Point
Adapts FastAPI application for Vercel deployment
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# Import routes
from src.api.routes import router

# Create FastAPI app
app = FastAPI(
    title="RWD IE Optimizer",
    description="AI-powered clinical trial criteria to SQL converter",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "environment": "vercel",
        "services": {
            "api": "running"
        }
    }


# Vercel serverless handler
handler = Mangum(app, lifespan="off")
