import logging
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

from app.core.database import SessionLocal
from app.models.sqlalchemy.jira import JiraProject, JiraIssue
from app.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)

def generate_test_data():
    db = SessionLocal()
    try:
        project = db.query(JiraProject).filter(JiraProject.jira_key == 'TEST').first()
        if not project:
            project = JiraProject(
                jira_key='TEST',
                name='Test Project',
                description='Project for analytics demonstration',
                is_active=True,
                last_synced=datetime.utcnow()
            )
            db.add(project)
            db.flush()
            logger.info('Created test project TEST')
        
        db.query(JiraIssue).filter(JiraIssue.project_id == project.id).delete()
        
        statuses = ['To Do', 'In Progress', 'In Review', 'Done', 'Blocked', 'Closed', 'Resolved']
        priorities = ['Highest', 'High', 'Medium', 'Low']
        assignees = ['Ivan Ivanov', 'Petr Petrov', 'Sidor Sidorov', 'Anna Smirnova', 'Elena Kuznetsova']
        issue_types = ['Task', 'Bug', 'Story', 'Epic', 'Sub-task']
        
        issues_count = 50
        for i in range(issues_count):
            status = random.choice(statuses)
            story_points = random.choice([1, 2, 3, 5, 8, 13]) if random.random() > 0.3 else None
            
            issue = JiraIssue(
                project_id=project.id,
                jira_key=f'TEST-{i+100}',
                summary=f'Test issue #{i+1}',
                description=f'Description of test issue {i+1}',
                status=status,
                priority=random.choice(priorities),
                issue_type=random.choice(issue_types),
                assignee=random.choice(assignees) if random.random() > 0.2 else None,
                story_points=story_points,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                updated_at=datetime.utcnow(),
                last_synced=datetime.utcnow()
            )
            db.add(issue)
        
        db.commit()
        logger.info(f'Generated {issues_count} test issues')
        
        metrics = MetricsService.calculate_metrics(db, project.id)
        if metrics and 'error' not in metrics:
            MetricsService.save_analytics(db, project.id, metrics)
            logger.info('Metrics saved')
        
    except Exception as e:
        db.rollback()
        logger.error(f'Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    generate_test_data()