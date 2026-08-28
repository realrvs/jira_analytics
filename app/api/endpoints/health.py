from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.sqlalchemy.user import User

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    return {
        "status": "ok",
        "service": "jira-analytics-api",
        "version": "0.1.0"
    }


@router.get("/readiness")
async def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ready" if db_status == "ok" else "unhealthy",
        "database": db_status,
        "redis": "ok"
    }


@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {
        "message": f"Hello, {current_user.full_name}!",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role.value if current_user.role else "user"
        }
    }
