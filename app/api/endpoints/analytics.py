from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.sqlalchemy.user import User
from app.models.sqlalchemy.jira import JiraProject
from app.models.sqlalchemy.analytics import AnalyticsHistory
from app.services.metrics_service import MetricsService

router = APIRouter(prefix=\"/analytics\", tags=[\"analytics\"])


@router.get(\"/metrics/{project_key}\")
async def get_project_metrics(
    project_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    \"\"\"Получить текущие метрики проекта\"\"\"
    project = db.query(JiraProject).filter(JiraProject.jira_key == project_key).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=\"Проект не найден\"
        )
    
    metrics = MetricsService.calculate_metrics(db, project.id)
    return {
        \"project\": project_key,
        \"project_name\": project.name,
        \"metrics\": metrics,
        \"last_synced\": project.last_synced,
        \"timestamp\": datetime.utcnow().isoformat()
    }


@router.post(\"/metrics/{project_key}/refresh\")
async def refresh_metrics(
    project_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    \"\"\"Обновить и сохранить метрики проекта\"\"\"
    project = db.query(JiraProject).filter(JiraProject.jira_key == project_key).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=\"Проект не найден\"
        )
    
    metrics = MetricsService.calculate_metrics(db, project.id)
    history = MetricsService.save_analytics(db, project.id, metrics)
    
    return {
        \"message\": f\"Метрики для {project_key} обновлены\",
        \"id\": history.id,
        \"date\": history.date,
        \"metrics\": metrics
    }


@router.get(\"/history/{project_key}\")
async def get_metrics_history(
    project_key: str,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    \"\"\"Получить историю метрик проекта\"\"\"
    project = db.query(JiraProject).filter(JiraProject.jira_key == project_key).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=\"Проект не найден\"
        )
    
    history = MetricsService.get_project_analytics(db, project.id, limit)
    
    return {
        \"project\": project_key,
        \"total_records\": len(history),
        \"history\": [
            {
                \"id\": h.id,
                \"date\": h.date,
                \"velocity\": h.velocity,
                \"completion_rate\": h.completion_rate,
                \"load_index\": h.load_index,
                \"blocked_count\": h.blocked_count,
                \"wip_count\": h.wip_count,
                \"total_issues\": h.total_issues,
                \"completed_issues\": h.completed_issues,
                \"metrics\": h.metrics
            }
            for h in history
        ]
    }


@router.get(\"/dashboard/{project_key}\")
async def get_dashboard_data(
    project_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    \"\"\"Получить данные для дашборда\"\"\"
    project = db.query(JiraProject).filter(JiraProject.jira_key == project_key).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=\"Проект не найден\"
        )
    
    # Текущие метрики
    metrics = MetricsService.calculate_metrics(db, project.id)
    
    # История (последние 5 записей)
    history = MetricsService.get_project_analytics(db, project.id, 5)
    
    # Последняя аналитика
    last_analytics = history[0] if history else None
    
    return {
        \"project\": {
            \"key\": project.jira_key,
            \"name\": project.name,
            \"last_synced\": project.last_synced
        },
        \"current_metrics\": metrics,
        \"trends\": {
            \"velocity\": [h.velocity for h in history] if history else [],
            \"completion_rate\": [h.completion_rate for h in history] if history else [],
            \"dates\": [h.date.isoformat() for h in history] if history else []
        },
        \"summary\": {
            \"total_issues\": metrics.get(\"total_issues\", 0),
            \"completed\": metrics.get(\"completed_count\", 0),
            \"completion_rate\": metrics.get(\"completion_rate\", 0),
            \"blocked\": metrics.get(\"blocked_count\", 0),
            \"wip\": metrics.get(\"wip_count\", 0),
            \"efficiency\": metrics.get(\"efficiency_score\", \"unknown\"),
            \"velocity\": metrics.get(\"velocity\", 0)
        }
    }
