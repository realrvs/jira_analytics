from fastapi import APIRouter

from app.api.endpoints import auth, health, projects, jira, analytics, ai

router = APIRouter()

router.include_router(auth.router)
router.include_router(health.router)
router.include_router(projects.router)
router.include_router(jira.router)
router.include_router(analytics.router)
router.include_router(ai.router)
