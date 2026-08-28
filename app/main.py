from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.api.router import router as api_router

app = FastAPI(
    title="Jira Analytics Tool API",
    description="Enterprise AI-PMO Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутер
app.include_router(api_router, prefix="/api/v1")
logger.info("API router registered with prefix /api/v1")

# Корневые эндпоинты
@app.get("/")
async def root():
    return {"message": "Jira Analytics Tool API"}

@app.get("/health")
async def health():
    return {"status": "ok"}

# Выводим все пути при старте
@app.on_event("startup")
async def startup():
    logger.info("=" * 50)
    logger.info("Registered routes:")
    for route in app.routes:
        if hasattr(route, "path"):
            methods = ", ".join(route.methods) if hasattr(route, "methods") else "N/A"
            logger.info(f"  {methods} {route.path}")
    logger.info("=" * 50)
