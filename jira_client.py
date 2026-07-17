import logging
import pandas as pd
from jira import JIRA
from typing import List, Dict, Optional, Any
from config import Config
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JiraClient:
    """Клиент для работы с Jira API без привязки к доскам"""
    
    def __init__(self):
        self.config = Config
        self.client = None
        self.project_key = self.config.JIRA_PROJECT
        self._connect()
    
    def _connect(self):
        """Подключение к Jira"""
        try:
            self.client = JIRA(
                server=self.config.JIRA_URL,
                basic_auth=(self.config.JIRA_USERNAME, self.config.JIRA_PASSWORD)
            )
            logger.info(f"✅ Подключено к Jira: {self.config.JIRA_URL}")
            
            project = self.client.project(self.project_key)
            logger.info(f"✅ Проект: {project.name} ({self.project_key})")
            logger.info(f"   Тип проекта: {project.projectTypeKey}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Jira: {e}")
            raise
    
    def get_all_sprints_data(self) -> pd.DataFrame:
        """Получение всех задач проекта (без привязки к доскам)"""
        try:
            # Получаем все задачи проекта
            jql = f'project = {self.project_key}'
            logger.info(f"📊 Выполнение запроса: {jql}")
            
            issues = self.client.search_issues(
                jql,
                maxResults=self.config.MAX_ISSUES,
                fields=[
                    'summary', 'status', 'assignee', 'reporter',
                    'priority', 'issuetype', 'created', 'updated',
                    'timeoriginalestimate', 'timeestimate', 'timespent',
                    'customfield_10016',  # Story Points
                    'customfield_10004',  # Альтернативное поле для SP
                    'resolutiondate', 'description',
                    'labels', 'components', 'fixVersions', 'versions',
                    'sprint'
                ],
                expand='changelog'
            )
            
            logger.info(f"✅ Найдено {len(issues)} задач в проекте {self.project_key}")
            
            if not issues:
                logger.warning("⚠️ Задачи не найдены")
                return pd.DataFrame()
            
            # Парсим задачи
            all_issues = []
            for issue in issues:
                all_issues.append(self._parse_issue(issue))
            
            # Создаем DataFrame
            df = pd.DataFrame(all_issues)
            
            # Преобразуем даты
            for date_col in ['created', 'updated', 'resolution_date']:
                if date_col in df.columns:
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            
            logger.info(f"✅ Всего получено {len(df)} задач")
            return df
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения данных: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def _parse_issue(self, issue) -> Dict[str, Any]:
        """Парсинг задачи в словарь"""
        # Получаем Story Points
        story_points = None
        try:
            for field in ['customfield_10016', 'customfield_10004']:
                if hasattr(issue.fields, field):
                    value = getattr(issue.fields, field)
                    if value is not None:
                        story_points = float(value)
                        break
        except (ValueError, TypeError):
            pass
        
        # Получаем информацию о спринте (если есть)
        sprint_name = None
        sprint_id = None
        sprint_state = None
        
        if hasattr(issue.fields, 'sprint') and issue.fields.sprint:
            sprints = issue.fields.sprint
            if isinstance(sprints, list) and sprints:
                last_sprint = sprints[-1]
                if hasattr(last_sprint, 'name'):
                    sprint_name = last_sprint.name
                if hasattr(last_sprint, 'id'):
                    sprint_id = last_sprint.id
                if hasattr(last_sprint, 'state'):
                    sprint_state = last_sprint.state
            elif hasattr(sprints, 'name'):
                sprint_name = sprints.name
                if hasattr(sprints, 'id'):
                    sprint_id = sprints.id
                if hasattr(sprints, 'state'):
                    sprint_state = sprints.state
        
        components = [comp.name for comp in issue.fields.components] if issue.fields.components else []
        labels = list(issue.fields.labels) if issue.fields.labels else []
        fix_versions = [v.name for v in issue.fields.fixVersions] if issue.fields.fixVersions else []
        affected_versions = [v.name for v in issue.fields.versions] if issue.fields.versions else []
        
        return {
            'key': issue.key,
            'summary': issue.fields.summary,
            'status': issue.fields.status.name,
            'status_category': issue.fields.status.statusCategory.name if issue.fields.status.statusCategory else None,
            'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned',
            'assignee_key': issue.fields.assignee.key if issue.fields.assignee else None,
            'reporter': issue.fields.reporter.displayName if issue.fields.reporter else 'Unknown',
            'reporter_key': issue.fields.reporter.key if issue.fields.reporter else None,
            'priority': issue.fields.priority.name if issue.fields.priority else 'None',
            'issue_type': issue.fields.issuetype.name,
            'created': issue.fields.created,
            'updated': issue.fields.updated,
            'resolution_date': issue.fields.resolutiondate if hasattr(issue.fields, 'resolutiondate') else None,
            'sprint': sprint_name,
            'sprint_id': sprint_id,
            'sprint_state': sprint_state,
            'story_points': story_points,
            'time_spent_hours': issue.fields.timespent / 3600 if issue.fields.timespent else 0,
            'time_estimate_hours': issue.fields.timeestimate / 3600 if issue.fields.timeestimate else 0,
            'original_estimate_hours': issue.fields.timeoriginalestimate / 3600 if issue.fields.timeoriginalestimate else 0,
            'components': components,
            'labels': labels,
            'fix_versions': fix_versions,
            'affected_versions': affected_versions,
            'has_description': bool(issue.fields.description),
            'description_length': len(issue.fields.description) if issue.fields.description else 0,
            'is_resolved': issue.fields.resolutiondate is not None,
            'resolution': issue.fields.resolution.name if hasattr(issue.fields, 'resolution') and issue.fields.resolution else None,
        }
    
    def get_issues_by_jql(self, jql: str) -> pd.DataFrame:
        """Получение задач по произвольному JQL запросу"""
        try:
            issues = self.client.search_issues(
                jql,
                maxResults=self.config.MAX_ISSUES,
                fields=[
                    'summary', 'status', 'assignee', 'reporter',
                    'priority', 'issuetype', 'created', 'updated',
                    'timespent', 'customfield_10016'
                ]
            )
            
            data = []
            for issue in issues:
                data.append({
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'status': issue.fields.status.name,
                    'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned',
                    'reporter': issue.fields.reporter.displayName if issue.fields.reporter else 'Unknown',
                    'priority': issue.fields.priority.name if issue.fields.priority else 'None',
                    'issue_type': issue.fields.issuetype.name,
                    'created': issue.fields.created,
                    'updated': issue.fields.updated
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения JQL запроса: {e}")
            return pd.DataFrame()
    
    def test_connection(self) -> bool:
        """Тестирование подключения к Jira"""
        try:
            server_info = self.client.server_info()
            logger.info(f"✅ Подключение успешно!")
            logger.info(f"   Версия Jira: {server_info.get('version', 'unknown')}")
            logger.info(f"   База данных: {server_info.get('database', {}).get('type', 'unknown')}")
            
            project = self.client.project(self.project_key)
            logger.info(f"   Проект: {project.name} ({project.key})")
            
            jql = f'project = {self.project_key}'
            count = self.client.search_issues(jql, maxResults=0).total
            logger.info(f"   Всего задач в проекте: {count}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования: {e}")
            return False