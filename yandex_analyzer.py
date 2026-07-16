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
            # Используем синхронный режим YandexGPT
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
            
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                # Извлекаем текст ответа
                if 'result' in result and 'alternatives' in result['result']:
                    return result['result']['alternatives'][0]['message']['text']
                else:
                    logger.error(f"⚠️ Неожиданный формат ответа: {result}")
                    return None
            else:
                logger.error(f"❌ Ошибка YandexGPT API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка при вызове YandexGPT: {e}")
            return None
    
    def analyze_metrics(self, metrics: Dict[str, Any], df: pd.DataFrame) -> Dict[str, str]:
        """Генерация рекомендаций на основе метрик"""
        if not self.is_available:
            return {"error": "YandexGPT не доступен"}
        
        recommendations = {}
        
        # 1. Анализ общей эффективности
        recommendations['overall'] = self._analyze_overall(metrics, df)
        
        # 2. Анализ загрузки команды
        recommendations['workload'] = self._analyze_workload(metrics, df)
        
        # 3. Анализ скорости (Velocity)
        recommendations['velocity'] = self._analyze_velocity(metrics, df)
        
        # 4. Анализ качества (статусы, переделки)
        recommendations['quality'] = self._analyze_quality(metrics, df)
        
        # 5. Общий итоговый вывод
        recommendations['summary'] = self._generate_summary(metrics, df)
        
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
        Если процент завершения ниже 80%, предложи, как увеличить delivery rate.
        Если задач в спринте слишком много или мало, дай рекомендацию по оптимальному объему.
        """
        
        return self._call_gpt(prompt) or self._fallback_overall(metrics)
    
    def _fallback_overall(self, metrics: Dict[str, Any]) -> str:
        """Fallback анализ (если GPT недоступен)"""
        completed = metrics.get('completed_count', 0)
        total = metrics.get('total_issues', 0)
        rate = (completed / total * 100) if total > 0 else 0
        
        if rate < 70:
            return f"⚠️ Низкий процент завершения ({rate:.1f}%). Рекомендации: 1) Пересмотрите объем спринта, 2) Увеличьте количество ревью, 3) Проведите ретроспективу для выявления блокеров."
        elif rate < 90:
            return f"✅ Хороший процент завершения ({rate:.1f}%). Рекомендации: 1) Продолжайте мониторинг, 2) Оптимизируйте процесс согласования требований."
        else:
            return f"🏆 Отличный результат! ({rate:.1f}%). Рекомендации: 1) Масштабируйте успешные практики, 2) Подумайте о снижении WIP-лимитов для улучшения качества."
    
    def _analyze_workload(self, metrics: Dict[str, Any], df: pd.DataFrame) -> str:
        """Анализ загрузки команды"""
        assignees = metrics.get('assignee_distribution', {})
        if not assignees:
            return "Нет данных о загрузке"
        
        total = sum(assignees.values())
        avg = total / len(assignees) if assignees else 0
        max_tasks = max(assignees.values()) if assignees else 0
        min_tasks = min(assignees.values()) if assignees else 0
        
        # Выявляем перегруженных и недозагруженных
        overloaded = [name for name, count in assignees.items() if count > avg * 1.8]
        underloaded = [name for name, count in assignees.items() if count < avg * 0.5]
        
        prompt = f"""
        Проанализируй загрузку команды:
        
        - Всего задач: {total}
        - Активных исполнителей: {len(assignees)}
        - Средняя загрузка: {avg:.1f} задач на человека
        - Максимум задач у одного: {max_tasks}
        - Минимум задач у одного: {min_tasks}
        
        Перегруженные сотрудники (> 1.8x от среднего): {', '.join(overloaded) if overloaded else 'Нет'}
        Недозагруженные сотрудники (< 0.5x от среднего): {', '.join(underloaded) if underloaded else 'Нет'}
        
        Дай рекомендации:
        1. Как сбалансировать нагрузку
        2. Нужно ли перераспределить задачи
        3. Есть ли признаки выгорания
        """
        
        return self._call_gpt(prompt) or self._fallback_workload(metrics)
    
    def _fallback_workload(self, metrics: Dict[str, Any]) -> str:
        """Fallback для загрузки"""
        assignees = metrics.get('assignee_distribution', {})
        if not assignees:
            return "Нет данных"
        
        avg = sum(assignees.values()) / len(assignees)
        overloaded = [name for name, count in assignees.items() if count > avg * 1.8]
        
        if overloaded:
            return f"⚠️ Обнаружены перегруженные сотрудники: {', '.join(overloaded)}. Рекомендуется перераспределить часть задач."
        else:
            return "✅ Нагрузка распределена равномерно."
    
    def _analyze_velocity(self, metrics: Dict[str, Any], df: pd.DataFrame) -> str:
        """Анализ скорости команды"""
        sp_by_sprint = metrics.get('story_points_by_sprint', {})
        if not sp_by_sprint:
            return "Нет данных по Story Points"
        
        sprints = list(sp_by_sprint.keys())
        values = list(sp_by_sprint.values())
        
        if len(values) < 2:
            return "Недостаточно данных для анализа скорости (нужно минимум 2 спринта)"
        
        avg_velocity = sum(values) / len(values)
        min_velocity = min(values)
        max_velocity = max(values)
        trend = "растет" if values[-1] > values[0] else "падает" if values[-1] < values[0] else "стабильна"
        
        prompt = f"""
        Проанализируй скорость команды (Velocity):
        
        - Спринты: {', '.join(sprints)}
        - Story Points: {values}
        - Средняя скорость: {avg_velocity:.1f} SP/спринт
        - Минимум: {min_velocity} SP
        - Максимум: {max_velocity} SP
        - Тренд: {trend}
        
        Дай рекомендации:
        1. Оптимальная ли скорость для текущего бэклога?
        2. Что делать, если скорость падает?
        3. Как улучшить планирование спринтов?
        """
        
        return self._call_gpt(prompt) or self._fallback_velocity(metrics)
    
    def _fallback_velocity(self, metrics: Dict[str, Any]) -> str:
        """Fallback для скорости"""
        sp_by_sprint = metrics.get('story_points_by_sprint', {})
        if len(sp_by_sprint) < 2:
            return "Недостаточно спринтов для анализа тренда"
        
        values = list(sp_by_sprint.values())
        avg = sum(values) / len(values)
        
        if values[-1] < avg * 0.8:
            return f"⚠️ Скорость в последнем спринте ({values[-1]} SP) ниже среднего ({avg:.1f} SP). Рекомендуется провести ретроспективу и выявить причины замедления."
        else:
            return f"✅ Средняя скорость {avg:.1f} SP. Команда стабильна."
    
    def _analyze_quality(self, metrics: Dict[str, Any], df: pd.DataFrame) -> str:
        """Анализ качества (статусы, переделки)"""
        statuses = metrics.get('status_distribution', {})
        if not statuses:
            return "Нет данных по статусам"
        
        # Считаем процент задач в статусах, требующих внимания
        in_progress = statuses.get('In Progress', 0) + statuses.get('In Review', 0)
        blocked = statuses.get('Blocked', 0) + statuses.get('On Hold', 0)
        total = sum(statuses.values())
        
        in_progress_pct = (in_progress / total * 100) if total > 0 else 0
        blocked_pct = (blocked / total * 100) if total > 0 else 0
        
        prompt = f"""
        Проанализируй качество процесса:
        
        - Статусы: {statuses}
        - Задачи в работе (In Progress/Review): {in_progress} ({in_progress_pct:.1f}%)
        - Заблокированные задачи (Blocked/On Hold): {blocked} ({blocked_pct:.1f}%)
        
        Дай рекомендации:
        1. Много ли задач в статусе "в работе" — нужны ли WIP-лимиты?
        2. Много ли заблокированных задач — какие типы блокеров?
        3. Как улучшить поток задач?
        """
        
        return self._call_gpt(prompt) or self._fallback_quality(metrics)
    
    def _fallback_quality(self, metrics: Dict[str, Any]) -> str:
        """Fallback для качества"""
        statuses = metrics.get('status_distribution', {})
        blocked = statuses.get('Blocked', 0) + statuses.get('On Hold', 0)
        
        if blocked > 0:
            return f"⚠️ Обнаружено {blocked} заблокированных задач. Рекомендуется ежедневно проводить синк по блокерам и эскалировать их."
        else:
            return "✅ Заблокированных задач нет. Процесс идет гладко."
    
    def _generate_summary(self, metrics: Dict[str, Any], df: pd.DataFrame) -> str:
        """Генерация общего итогового вывода"""
        total = metrics.get('total_issues', 0)
        completed = metrics.get('completed_count', 0)
        rate = (completed / total * 100) if total > 0 else 0
        
        prompt = f"""
        Подведи итог анализу проекта на основе метрик:
        
        - Всего задач: {total}
        - Завершено: {completed} ({rate:.1f}%)
        - Есть ли проблемы с загрузкой команды?
        - Какова скорость команды?
        - Качество процесса?
        
        Дай общий вердикт (2-3 предложения) и 3 главные рекомендации для улучшения.
        """
        
        return self._call_gpt(prompt) or self._fallback_summary(metrics)
    
    def _fallback_summary(self, metrics: Dict[str, Any]) -> str:
        """Fallback для итогового вывода"""
        total = metrics.get('total_issues', 0)
        completed = metrics.get('completed_count', 0)
        rate = (completed / total * 100) if total > 0 else 0
        
        if rate < 70:
            return f"🔴 Критическая ситуация: завершено только {rate:.1f}% задач. Необходимо срочно пересмотреть процессы, провести ретроспективу и сократить объем спринтов."
        elif rate < 90:
            return f"🟡 Процесс требует улучшения: завершено {rate:.1f}% задач. Рекомендуется оптимизировать планирование и усилить кросс-командную коммуникацию."
        else:
            return f"🟢 Проект в зеленой зоне: завершено {rate:.1f}% задач. Команда эффективна, процессы отлажены. Рекомендуется масштабировать успешные практики на другие проекты."