import json
import logging
from typing import Dict, Any, Optional
import pandas as pd
import requests
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YandexGptAnalyzer:
    """Анализ данных с использованием YandexGPT"""
    
    def __init__(self):
        self.config = Config
        self.is_available = self.config.is_yandex_gpt_available()
        
        if not self.is_available:
            logger.warning("⚠️ YandexGPT не настроен. Рекомендации будут пропущены.")
        else:
            logger.info("✅ YandexGPT доступен")
            if self.config.YC_FOLDER_ID:
                logger.info(f"   Folder ID: {self.config.YC_FOLDER_ID[:10]}...")
            logger.info(f"   API Key: {'*' * 10}")
    
    def _get_headers(self) -> dict:
        """Получение заголовков для запроса к YandexGPT API"""
        headers = {
            "Content-Type": "application/json",
            "x-folder-id": self.config.YC_FOLDER_ID,
        }
        
        if self.config.YC_API_KEY:
            headers["Authorization"] = f"Api-Key {self.config.YC_API_KEY}"
        elif self.config.YC_IAM_TOKEN:
            headers["Authorization"] = f"Bearer {self.config.YC_IAM_TOKEN}"
        else:
            raise ValueError("Не задан ни API ключ, ни IAM токен для YandexGPT")
        
        return headers
    
    def _call_gpt(self, prompt: str, temperature: float = 0.3) -> Optional[str]:
        """Вызов YandexGPT API (синхронный режим)"""
        if not self.is_available:
            return None
        
        try:
            url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
            
            payload = {
                "modelUri": f"gpt://{self.config.YC_FOLDER_ID}/yandexgpt-lite",
                "completionOptions": {
                    "stream": False,
                    "temperature": temperature,
                    "maxTokens": "2000"
                },
                "messages": [
                    {
                        "role": "system",
                        "text": "Ты — эксперт по управлению IT-проектами и аналитик данных. "
                                "Твоя задача — анализировать метрики Jira и давать конкретные, "
                                "практические рекомендации для улучшения процессов разработки. "
                                "Отвечай на русском языке, структурируй ответ, "
                                "используй цифры из предоставленных данных. "
                                "Будь конструктивным и конкретным."
                    },
                    {
                        "role": "user",
                        "text": prompt
                    }
                ]
            }
            
            logger.info(f"📤 Отправка запроса к YandexGPT...")
            
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=30)
            
            logger.info(f"📥 Ответ YandexGPT: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                if 'result' in result and 'alternatives' in result['result']:
                    text = result['result']['alternatives'][0]['message']['text']
                    logger.info(f"✅ Получен ответ от YandexGPT ({len(text)} символов)")
                    return text
                else:
                    logger.error(f"⚠️ Неожиданный формат ответа: {result}")
                    return None
            else:
                logger.error(f"❌ Ошибка YandexGPT API: {response.status_code}")
                logger.error(f"   Текст: {response.text[:500]}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("❌ Таймаут при вызове YandexGPT")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка при вызове YandexGPT: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def analyze_metrics(self, metrics: Dict[str, Any], df: pd.DataFrame) -> Dict[str, str]:
        """Генерация рекомендаций на основе метрик"""
        if not self.is_available:
            logger.warning("⚠️ YandexGPT не доступен, используются fallback-рекомендации")
            return self._get_fallback_recommendations(metrics)
        
        logger.info("🤖 Генерация AI-рекомендаций...")
        recommendations = {}
        
        recommendations['overall'] = self._analyze_overall(metrics, df) or self._fallback_overall(metrics)
        recommendations['workload'] = self._analyze_workload(metrics, df) or self._fallback_workload(metrics)
        recommendations['velocity'] = self._analyze_velocity(metrics, df) or self._fallback_velocity(metrics)
        recommendations['quality'] = self._analyze_quality(metrics, df) or self._fallback_quality(metrics)
        recommendations['summary'] = self._generate_summary(metrics, df) or self._fallback_summary(metrics)
        
        logger.info("✅ Все рекомендации сгенерированы")
        return recommendations
    
    def _analyze_overall(self, metrics: Dict[str, Any], df: pd.DataFrame) -> str:
        """Анализ общей эффективности проекта"""
        total_issues = metrics.get('total_issues', 0)
        total_sprints = metrics.get('total_sprints', 0)
        completed = metrics.get('completed_count', 0)
        
        if total_issues == 0:
            return "Нет данных для анализа"
        
        completion_rate = (completed / total_issues * 100) if total_issues > 0 else 0
        
        prompt = f"""
        Проанализируй общую эффективность проекта на основе следующих данных Jira:
        
        - Всего задач: {total_issues}
        - Всего спринтов: {total_sprints}
        - Завершено задач: {completed}
        - Процент завершения: {completion_rate:.1f}%
        
        Дай краткий анализ (3-5 предложений) и 2-3 конкретные рекомендации по улучшению.
        """
        
        return self._call_gpt(prompt)
    
    def _fallback_overall(self, metrics: Dict[str, Any]) -> str:
        """Fallback анализ"""
        completed = metrics.get('completed_count', 0)
        total = metrics.get('total_issues', 0)
        rate = (completed / total * 100) if total > 0 else 0
        
        if rate < 30:
            return f"⚠️ Низкий процент завершения ({rate:.1f}%). Рекомендуется пересмотреть приоритеты."
        elif rate < 70:
            return f"🟡 Средний процент завершения ({rate:.1f}%). Требуется оптимизация."
        else:
            return f"✅ Хороший процент завершения ({rate:.1f}%)."
    
    def _analyze_workload(self, metrics: Dict[str, Any], df: pd.DataFrame) -> str:
        """Анализ загрузки команды"""
        assignees = metrics.get('assignee_distribution', {})
        if not assignees:
            return "Нет данных о загрузке"
        
        total = sum(assignees.values())
        avg = total / len(assignees) if assignees else 0
        
        overloaded = [name for name, count in assignees.items() if count > avg * 1.8]
        
        prompt = f"""
        Проанализируй загрузку команды:
        - Всего задач: {total}
        - Средняя загрузка: {avg:.1f} задач на человека
        - Перегруженные: {', '.join(overloaded) if overloaded else 'Нет'}
        
        Дай рекомендации по балансировке нагрузки.
        """
        
        return self._call_gpt(prompt)
    
    def _fallback_workload(self, metrics: Dict[str, Any]) -> str:
        """Fallback для загрузки"""
        assignees = metrics.get('assignee_distribution', {})
        if not assignees:
            return "Нет данных"
        
        avg = sum(assignees.values()) / len(assignees)
        overloaded = [name for name, count in assignees.items() if count > avg * 1.8]
        
        if overloaded:
            return f"⚠️ Перегружены: {', '.join(overloaded)}. Рекомендуется перераспределить задачи."
        else:
            return "✅ Нагрузка распределена равномерно."
    
    def _analyze_velocity(self, metrics: Dict[str, Any], df: pd.DataFrame) -> str:
        """Анализ скорости"""
        sp_by_sprint = metrics.get('story_points_by_sprint', {})
        if not sp_by_sprint:
            return "Нет данных по Story Points"
        
        values = list(sp_by_sprint.values())
        if len(values) < 2:
            return "Недостаточно данных для анализа скорости (нужно минимум 2 спринта)"
        
        avg_velocity = sum(values) / len(values)
        trend = "растет" if values[-1] > values[0] else "падает" if values[-1] < values[0] else "стабильна"
        
        prompt = f"""
        Проанализируй скорость команды:
        - Средняя скорость: {avg_velocity:.1f} SP/спринт
        - Тренд: {trend}
        Дай рекомендации по улучшению планирования.
        """
        
        return self._call_gpt(prompt)
    
    def _fallback_velocity(self, metrics: Dict[str, Any]) -> str:
        """Fallback для скорости"""
        sp_by_sprint = metrics.get('story_points_by_sprint', {})
        if len(sp_by_sprint) < 2:
            return "Недостаточно спринтов для анализа тренда"
        
        values = list(sp_by_sprint.values())
        avg = sum(values) / len(values)
        
        return f"Средняя скорость {avg:.1f} SP/спринт."
    
    def _analyze_quality(self, metrics: Dict[str, Any], df: pd.DataFrame) -> str:
        """Анализ качества"""
        statuses = metrics.get('status_distribution', {})
        if not statuses:
            return "Нет данных по статусам"
        
        blocked = statuses.get('Blocked', 0) + statuses.get('On Hold', 0)
        total = sum(statuses.values())
        
        prompt = f"""
        Проанализируй качество процесса:
        - Статусы: {statuses}
        - Заблокированных задач: {blocked}
        Дай рекомендации по улучшению потока задач.
        """
        
        return self._call_gpt(prompt)
    
    def _fallback_quality(self, metrics: Dict[str, Any]) -> str:
        """Fallback для качества"""
        statuses = metrics.get('status_distribution', {})
        blocked = statuses.get('Blocked', 0) + statuses.get('On Hold', 0)
        
        if blocked > 0:
            return f"⚠️ Обнаружено {blocked} заблокированных задач."
        else:
            return "✅ Заблокированных задач нет."
    
    def _generate_summary(self, metrics: Dict[str, Any], df: pd.DataFrame) -> str:
        """Генерация итогового вывода"""
        total = metrics.get('total_issues', 0)
        completed = metrics.get('completed_count', 0)
        rate = (completed / total * 100) if total > 0 else 0
        
        prompt = f"""
        Подведи итог анализу проекта:
        - Всего задач: {total}
        - Завершено: {completed} ({rate:.1f}%)
        
        Дай общий вердикт (2-3 предложения) и 3 главные рекомендации.
        """
        
        return self._call_gpt(prompt)
    
    def _fallback_summary(self, metrics: Dict[str, Any]) -> str:
        """Fallback для итогового вывода"""
        total = metrics.get('total_issues', 0)
        completed = metrics.get('completed_count', 0)
        rate = (completed / total * 100) if total > 0 else 0
        
        if rate < 30:
            return f"🔴 Завершено только {rate:.1f}% задач. Необходимо срочно пересмотреть процессы."
        elif rate < 60:
            return f"🟡 Завершено {rate:.1f}% задач. Требуется оптимизация."
        else:
            return f"🟢 Завершено {rate:.1f}% задач. Команда эффективна."
    
    def _get_fallback_recommendations(self, metrics: Dict[str, Any]) -> Dict[str, str]:
        """Получение fallback-рекомендаций"""
        return {
            'summary': self._fallback_summary(metrics),
            'overall': self._fallback_overall(metrics),
            'workload': self._fallback_workload(metrics),
            'velocity': self._fallback_velocity(metrics),
            'quality': self._fallback_quality(metrics)
        }