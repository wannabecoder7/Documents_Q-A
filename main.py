from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import create_tables
from app.schemas import HealthResponse
from datetime import datetime
import logging
import uvicorn

# 👇 THIS LINE: update to import directly from routers.py
from app.routers import documents_router, questions_router, health_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Document Q&A Service",
    version="1.0.0"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

# Register routers
app.include_router(documents_router)
app.include_router(questions_router)
app.include_router(health_router)

@app.on_event("startup")
async def startup():
    logger.info("Running startup tasks...")
    await create_tables()

@app.get("/")
async def root():
    return {"message": "Document Q&A Service is running."}

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy", timestamp=datetime.utcnow())

# Entry point
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
