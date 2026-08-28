from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.sqlalchemy.user import User
from app.models.sqlalchemy.project import Project

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def get_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    projects = db.query(Project).filter(Project.is_active == True).all()
    return [
        {
            "id": p.id,
            "key": p.jira_key,
            "name": p.name,
            "description": p.description,
            "last_synced": p.last_synced
        }
        for p in projects
    ]


@router.post("")
async def create_project(
    project_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )

    project = Project(
        jira_key=project_data.get("key"),
        name=project_data.get("name"),
        description=project_data.get("description", ""),
        is_active=True
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
