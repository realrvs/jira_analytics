import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.sqlalchemy.jira import JiraIssue, JiraProject, JiraSprint
from app.models.sqlalchemy.analytics import AnalyticsHistory

logger = logging.getLogger(__name__)


class MetricsService:
    
    @staticmethod
    def calculate_metrics(db: Session, project_id: int) -> Dict[str, Any]:
        issues = db.query(JiraIssue).filter(JiraIssue.project_id == project_id).all()
        
        if not issues:
            return {"error": "No issues found"}
        
        total = len(issues)
        done_statuses = ['Done', 'Closed', 'Resolved']
        completed = len([i for i in issues if i.status in done_statuses])
        
        metrics = {
            "total_issues": total,
            "completed_count": completed,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "blocked_count": len([i for i in issues if i.status == "Blocked"]),
            "wip_count": len([i for i in issues if i.status in ["In Progress", "In Review", "In Testing"]]),
            "status_distribution": {},
            "priority_distribution": {},
            "assignee_distribution": {},
            "issue_type_distribution": {}
        }
        
        for issue in issues:
            metrics["status_distribution"][issue.status] = metrics["status_distribution"].get(issue.status, 0) + 1
            metrics["priority_distribution"][issue.priority] = metrics["priority_distribution"].get(issue.priority, 0) + 1
            if issue.assignee:
                metrics["assignee_distribution"][issue.assignee] = metrics["assignee_distribution"].get(issue.assignee, 0) + 1
            if issue.issue_type:
                metrics["issue_type_distribution"][issue.issue_type] = metrics["issue_type_distribution"].get(issue.issue_type, 0) + 1
        
        if any(i.story_points for i in issues if i.story_points):
            total_sp = sum(i.story_points for i in issues if i.story_points)
            metrics["total_story_points"] = total_sp
            completed_sp = sum(i.story_points for i in issues if i.story_points and i.status in done_statuses)
            metrics["completed_story_points"] = completed_sp
            metrics["velocity"] = total_sp / max(len(metrics["status_distribution"]), 1)
        
        if metrics["assignee_distribution"]:
            assignee_counts = list(metrics["assignee_distribution"].values())
            metrics["avg_load"] = sum(assignee_counts) / len(assignee_counts)
            metrics["max_load"] = max(assignee_counts)
        
        if metrics["completion_rate"] >= 80:
            metrics["efficiency_score"] = "high"
        elif metrics["completion_rate"] >= 50:
            metrics["efficiency_score"] = "medium"
        else:
            metrics["efficiency_score"] = "low"
        
        logger.info(f"Metrics calculated for project {project_id}: {total} issues")
        return metrics
    
    @staticmethod
    def get_project_analytics(db: Session, project_id: int, limit: int = 10) -> List[AnalyticsHistory]:
        return db.query(AnalyticsHistory).filter(
            AnalyticsHistory.project_id == project_id
        ).order_by(AnalyticsHistory.date.desc()).limit(limit).all()
    
    @staticmethod
    def save_analytics(db: Session, project_id: int, metrics: Dict[str, Any]) -> AnalyticsHistory:
        history = AnalyticsHistory(
            project_id=project_id,
            velocity=metrics.get("velocity", 0),
            completion_rate=metrics.get("completion_rate", 0),
            load_index=metrics.get("avg_load", 0),
            blocked_count=metrics.get("blocked_count", 0),
            wip_count=metrics.get("wip_count", 0),
            total_issues=metrics.get("total_issues", 0),
            completed_issues=metrics.get("completed_count", 0),
            metrics=metrics
        )
        db.add(history)
        db.commit()
        db.refresh(history)
        logger.info(f"Analytics saved for project {project_id}")
        return history