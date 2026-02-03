"""
RWD IE Optimizer - Main Application Entry Point
Clean, production-ready FastAPI server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Import API routes
from src.api.routes import router

# Create FastAPI application
app = FastAPI(
    title="RWD IE Optimizer",
    description="AI-powered clinical trial criteria to SQL converter",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS for frontend on Vercel
allowed_origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    os.getenv("FRONTEND_URL", "*"),  # Set in Render dashboard
]

# Add wildcard for Vercel preview deployments
if os.getenv("ALLOW_VERCEL_PREVIEWS", "true").lower() == "true":
    allowed_origins.append("https://*.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if os.getenv("ENV") == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "services": {
            "api": "running",
            "database": "connected"
        }
    }


if __name__ == "__main__":
    import uvicorn

    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"

    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║           RWD IE Optimizer - Version 2.0.0              ║
    ║                                                          ║
    ║  Server running at: http://{host}:{port}              ║
    ║  API Documentation: http://{host}:{port}/api/docs     ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
