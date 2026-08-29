from fastapi import APIRouter

from app.api.endpoints import auth, health, projects, jira, analytics

router = APIRouter()

# Подключаем все эндпоинты
router.include_router(auth.router)
router.include_router(health.router)
router.include_router(projects.router)
router.include_router(jira.router)
router.include_router(analytics.router)
