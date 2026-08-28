from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import asyncio

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.sqlalchemy.user import User
from app.models.sqlalchemy.jira import JiraProject, JiraIssue
from app.services.etl_engine import ETLEngine

router = APIRouter(prefix="/jira", tags=["jira"])


@router.post("/sync/{project_key}")
async def sync_project(
    project_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для синхронизации"
        )

    engine = ETLEngine()
    success = await engine.sync_project(project_key)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка синхронизации проекта"
        )

    return {"message": f"Проект {project_key} успешно синхронизирован"}


@router.get("/projects")
async def get_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    projects = db.query(JiraProject).filter(JiraProject.is_active == True).all()
    return [
        {
            "id": p.id,
            "key": p.jira_key,
            "name": p.name,
            "last_synced": p.last_synced,
            "issues_count": len(p.issues) if p.issues else 0
        }
        for p in projects
    ]


@router.get("/issues/{project_key}")
async def get_project_issues(
    project_key: str,
    limit: int = 100,
    skip: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(JiraProject).filter(JiraProject.jira_key == project_key).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проект не найден"
        )

    issues = db.query(JiraIssue).filter(
        JiraIssue.project_id == project.id
    ).offset(skip).limit(limit).all()

    total = db.query(JiraIssue).filter(JiraIssue.project_id == project.id).count()

    return {
        "total": total,
        "issues": [
            {
                "key": i.jira_key,
                "summary": i.summary,
                "status": i.status,
                "priority": i.priority,
                "assignee": i.assignee,
                "story_points": i.story_points,
                "created_at": i.created_at
            }
            for i in issues
        ]
    }
