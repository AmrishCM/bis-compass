from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

from app.db.session import init_db
from app.api.routes import (
    analyze_router,
    products_router,
    standards_router,
    compliance_router,
    laboratories_router,
    documents_router,
    web_router,
    sources_router,
    evaluation_router,
    stats_router,
    chat_router,
    audit_router,
    ai_health_router,
    research_health_router,
    translate_router,
    consumer_router,
    updates_router,
    voice_router
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bis_compass")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting BIS-Compass Open-World Research & Compliance Intelligence Engine...")
    init_db()
    logger.info("BIS-Compass dynamic evidence cache & index ready. Live research active.")
    yield
    # Shutdown
    logger.info("Shutting down BIS-Compass...")

app = FastAPI(
    title="BIS-Compass API",
    description="AI-Powered Indian Standards & BIS Compliance Intelligence Platform (SIH 2026)",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers under /api
app.include_router(analyze_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(standards_router, prefix="/api")
app.include_router(compliance_router, prefix="/api")
app.include_router(laboratories_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(web_router, prefix="/api")
app.include_router(sources_router, prefix="/api")
app.include_router(evaluation_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(ai_health_router, prefix="/api")
app.include_router(research_health_router, prefix="/api")
app.include_router(translate_router, prefix="/api")
app.include_router(consumer_router, prefix="/api")
app.include_router(updates_router, prefix="/api")
app.include_router(voice_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "name": "BIS-Compass Intelligence Platform",
        "description": "AI-Powered Indian Standards & BIS Compliance Intelligence",
        "version": "1.0.0",
        "status": "operational",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "engine": "operational",
        "database": "connected"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)