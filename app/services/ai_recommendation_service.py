import logging
import json
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.sqlalchemy.jira import JiraProject
from app.models.sqlalchemy.analytics import AIRecommendation, RecommendationStatus
from app.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)


class AIRecommendationService:
    def __init__(self):
        self.api_key = settings.YANDEXGPT_API_KEY
        self.folder_id = settings.YANDEXGPT_FOLDER_ID
        self.is_available = bool(self.api_key and self.folder_id)
        
        if not self.is_available:
            logger.warning("YandexGPT not configured. AI recommendations disabled.")
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id
        }
    
    def _call_gpt(self, prompt: str, temperature: float = 0.3) -> Optional[str]:
        if not self.is_available:
            return None
        
        try:
            url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
            
            payload = {
                "modelUri": f"gpt://{self.folder_id}/yandexgpt-lite",
                "completionOptions": {
                    "stream": False,
                    "temperature": temperature,
                    "maxTokens": "2000"
                },
                "messages": [
                    {
                        "role": "system",
                        "text": "You are an expert IT project manager. Analyze Jira metrics and provide actionable recommendations. Respond in Russian."
                    },
                    {
                        "role": "user",
                        "text": prompt
                    }
                ]
            }
            
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result and 'alternatives' in result['result']:
                    return result['result']['alternatives'][0]['message']['text']
            else:
                logger.error(f"YandexGPT API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"YandexGPT error: {e}")
            return None
    
    def generate_recommendations(self, project_key: str) -> List[Dict[str, Any]]:
        if not self.is_available:
            return []
        
        db = SessionLocal()
        try:
            project = db.query(JiraProject).filter(JiraProject.jira_key == project_key).first()
            if not project:
                return []
            
            metrics = MetricsService.calculate_metrics(db, project.id)
            if 'error' in metrics:
                return []
            
            prompt = self._build_prompt(project.name, metrics)
            response = self._call_gpt(prompt)
            
            if not response:
                return []
            
            recommendations = self._parse_recommendations(response)
            
            saved = []
            for rec in recommendations:
                db_rec = AIRecommendation(
                    project_id=project.id,
                    title=rec.get('title', 'Recommendation'),
                    description=rec.get('description', ''),
                    impact=rec.get('impact', 'MEDIUM'),
                    category=rec.get('category', 'general'),
                    action=rec.get('action', {}),
                    status=RecommendationStatus.NEW
                )
                db.add(db_rec)
                db.commit()
                db.refresh(db_rec)
                saved.append({
                    'id': db_rec.id,
                    'title': db_rec.title,
                    'description': db_rec.description,
                    'impact': db_rec.impact,
                    'category': db_rec.category
                })
            
            logger.info(f"Generated {len(saved)} recommendations for {project_key}")
            return saved
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
        finally:
            db.close()
    
    def _build_prompt(self, project_name: str, metrics: Dict[str, Any]) -> str:
        total = metrics.get('total_issues', 0)
        completed = metrics.get('completed_count', 0)
        rate = metrics.get('completion_rate', 0)
        blocked = metrics.get('blocked_count', 0)
        wip = metrics.get('wip_count', 0)
        velocity = metrics.get('velocity', 0)
        
        status_dist = metrics.get('status_distribution', {})
        assignee_dist = metrics.get('assignee_distribution', {})
        
        return f"""
Project: {project_name}
Metrics:
- Total issues: {total}
- Completed: {completed} ({rate:.1f}%)
- Blocked: {blocked}
- In progress: {wip}
- Velocity: {velocity:.1f}
- Status distribution: {status_dist}
- Assignee distribution: {assignee_dist}

Provide 3 recommendations in JSON format:
{{
  "recommendations": [
    {{
      "title": "Short title",
      "description": "Detailed description",
      "impact": "HIGH|MEDIUM|LOW",
      "category": "velocity|workload|quality|process"
    }}
  ]
}}
"""
    
    def _parse_recommendations(self, response: str) -> List[Dict[str, Any]]:
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = response[start:end]
                data = json.loads(json_str)
                return data.get('recommendations', [])
        except:
            pass
        
        return [{
            'title': 'Process Improvement',
            'description': response[:500],
            'impact': 'MEDIUM',
            'category': 'general'
        }]