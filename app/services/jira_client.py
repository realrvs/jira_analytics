import logging
import pandas as pd
from typing import List, Dict, Optional, Any
from datetime import datetime
import httpx
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.sqlalchemy.jira import JiraProject, JiraSprint, JiraIssue

logger = logging.getLogger(__name__)


class JiraClient:
    \"\"\"Асинхронный клиент для работы с Jira API\"\"\"
    
    def __init__(self):
        self.base_url = settings.JIRA_URL.rstrip('/') if settings.JIRA_URL else ''
        self.email = settings.JIRA_EMAIL
        self.api_token = settings.JIRA_API_TOKEN
        self.timeout = 30.0
        
        # Проверяем наличие настроек
        if not self.base_url or not self.email or not self.api_token:
            logger.warning("⚠️ Jira настройки не полные. Используйте .env файл.")
            self.is_configured = False
        else:
            self.is_configured = True
            self.auth = (self.email, self.api_token)
            self.headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            logger.info(f"✅ Jira клиент настроен: {self.base_url}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout))
    )
    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        \"\"\"Базовый метод для выполнения запросов к Jira API\"\"\"
        if not self.is_configured:
            logger.error("❌ Jira не настроен")
            return {}
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout, auth=self.auth) as client:
            try:
                logger.debug(f"📤 {method} {url}")
                response = await client.request(method, url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ Jira API ошибка: {e.response.status_code} - {e.response.text[:200]}")
                raise
            except Exception as e:
                logger.error(f"❌ Ошибка запроса: {str(e)}")
                raise
    
    async def get_project(self, project_key: str) -> Optional[Dict[str, Any]]:
        \"\"\"Получить информацию о проекте\"\"\"
        try:
            return await self._request("GET", f"/rest/api/2/project/{project_key}")
        except Exception as e:
            logger.error(f"❌ Ошибка получения проекта {project_key}: {e}")
            return None
    
    async def get_issues(
        self, 
        project_key: str, 
        start_at: int = 0,
        max_results: int = 50,
        updated_after: Optional[str] = None,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        \"\"\"Получить задачи проекта\"\"\"
        jql = f"project = {project_key}"
        if updated_after:
            jql += f" AND updated >= '{updated_after}'"
        
        default_fields = [
            'summary', 'status', 'priority', 'assignee', 
            'issuetype', 'created', 'updated', 'resolutiondate',
            'customfield_10016', 'customfield_10004'
        ]
        
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": ','.join(fields or default_fields),
            "expand": "changelog"
        }
        
        return await self._request("GET", "/rest/api/2/search", params=params)
    
    async def get_all_issues(self, project_key: str, updated_after: Optional[str] = None) -> List[Dict[str, Any]]:
        \"\"\"Получить все задачи проекта\"\"\"
        all_issues = []
        start_at = 0
        max_results = 100
        
        logger.info(f"📊 Получение задач проекта {project_key}...")
        
        while True:
            try:
                response = await self.get_issues(
                    project_key=project_key,
                    start_at=start_at,
                    max_results=max_results,
                    updated_after=updated_after
                )
                
                issues = response.get("issues", [])
                all_issues.extend(issues)
                
                total = response.get("total", 0)
                logger.info(f"   Получено {len(all_issues)} из {total} задач")
                
                if start_at + max_results >= total:
                    break
                    
                start_at += max_results
                
            except Exception as e:
                logger.error(f"❌ Ошибка получения задач: {e}")
                break
        
        logger.info(f"✅ Получено {len(all_issues)} задач")
        return all_issues
    
    def parse_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Парсинг задачи в словарь\"\"\"
        fields = issue.get('fields', {})
        
        # Получаем Story Points
        story_points = None
        for field in ['customfield_10016', 'customfield_10004']:
            if field in fields and fields[field] is not None:
                try:
                    story_points = float(fields[field])
                    break
                except (ValueError, TypeError):
                    pass
        
        # Получаем assignee
        assignee = fields.get('assignee', {})
        assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
        assignee_email = assignee.get('emailAddress', '') if assignee else ''
        
        # Получаем priority
        priority = fields.get('priority', {})
        priority_name = priority.get('name', 'None') if priority else 'None'
        
        # Получаем status
        status = fields.get('status', {})
        status_name = status.get('name', 'Unknown') if status else 'Unknown'
        
        # Получаем issue type
        issue_type = fields.get('issuetype', {})
        issue_type_name = issue_type.get('name', 'Unknown') if issue_type else 'Unknown'
        
        return {
            'jira_key': issue.get('key', ''),
            'summary': fields.get('summary', ''),
            'description': fields.get('description', ''),
            'status': status_name,
            'priority': priority_name,
            'issue_type': issue_type_name,
            'assignee': assignee_name,
            'assignee_email': assignee_email,
            'story_points': story_points,
            'created_at': fields.get('created'),
            'updated_at': fields.get('updated'),
            'resolved_at': fields.get('resolutiondate'),
            'custom_fields': {
                'labels': fields.get('labels', []),
                'components': [c.get('name', '') for c in fields.get('components', [])],
                'fix_versions': [v.get('name', '') for v in fields.get('fixVersions', [])]
            }
        }
