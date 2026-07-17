import pandas as pd
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataProcessor:
    """Обработка и расчет метрик по данным Jira"""
    
    def calculate_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Расчет всех метрик"""
        if df.empty:
            return {}
        
        metrics = {}
        
        # 1. Общие метрики
        metrics['total_issues'] = len(df)
        
        # Завершенные задачи
        done_statuses = ['done', 'closed', 'resolved']
        metrics['completed_count'] = len(df[df['status'].str.lower().isin(done_statuses)])
        metrics['total_sprints'] = df['sprint'].nunique() if 'sprint' in df else 0
        
        # 2. Распределение по статусам
        metrics['status_distribution'] = df['status'].value_counts().to_dict()
        
        # 3. Распределение по исполнителям
        metrics['assignee_distribution'] = df['assignee'].value_counts().to_dict()
        
        # 4. Распределение по приоритетам
        metrics['priority_distribution'] = df['priority'].value_counts().to_dict()
        
        # 5. Распределение по типам задач
        metrics['issue_type_distribution'] = df['issue_type'].value_counts().to_dict()
        
        # 6. Story Points по спринтам
        if 'story_points' in df and 'sprint' in df:
            sp_by_sprint = df.groupby('sprint')['story_points'].sum().to_dict()
            metrics['story_points_by_sprint'] = {str(k): float(v) for k, v in sp_by_sprint.items() if pd.notna(v)}
        
        # 7. Общие Story Points
        if 'story_points' in df:
            metrics['total_story_points'] = float(df['story_points'].sum()) if not df['story_points'].isna().all() else 0
            metrics['completed_story_points'] = float(
                df[df['status'].str.lower().isin(done_statuses)]['story_points'].sum()
            ) if not df.empty else 0
        
        # 8. Время
        if 'time_spent_hours' in df:
            metrics['total_time_spent_hours'] = float(df['time_spent_hours'].sum())
            metrics['avg_time_per_issue'] = float(df['time_spent_hours'].mean()) if not df.empty else 0
        
        # 9. Средняя скорость
        if 'story_points_by_sprint' in metrics:
            sp_values = list(metrics['story_points_by_sprint'].values())
            if sp_values:
                metrics['avg_velocity'] = sum(sp_values) / len(sp_values)
                metrics['velocity_trend'] = 'increasing' if len(sp_values) > 1 and sp_values[-1] > sp_values[0] else \
                                           'decreasing' if len(sp_values) > 1 and sp_values[-1] < sp_values[0] else 'stable'
        
        # 10. WIP (Work In Progress)
        wip_statuses = ['in progress', 'in review', 'open', 'reopened']
        metrics['wip_count'] = len(df[df['status'].str.lower().isin(wip_statuses)])
        metrics['wip_percentage'] = (metrics['wip_count'] / metrics['total_issues'] * 100) if metrics['total_issues'] > 0 else 0
        
        # 11. Блокеры
        blocked_statuses = ['blocked', 'on hold']
        metrics['blocked_count'] = len(df[df['status'].str.lower().isin(blocked_statuses)])
        metrics['blocked_percentage'] = (metrics['blocked_count'] / metrics['total_issues'] * 100) if metrics['total_issues'] > 0 else 0
        
        logger.info("✅ Метрики рассчитаны")
        return metrics
    
    def get_sprint_timeline(self, df: pd.DataFrame) -> pd.DataFrame:
        """Получение временной шкалы по спринтам"""
        if df.empty or 'sprint' not in df:
            return pd.DataFrame()
        
        # Группируем по спринтам
        done_statuses = ['done', 'closed', 'resolved']
        timeline = df.groupby('sprint').agg({
            'key': 'count',
            'status': lambda x: (x.str.lower().isin(done_statuses)).sum()
        }).reset_index()
        
        timeline.columns = ['sprint', 'total_issues', 'completed_issues']
        timeline['completion_rate'] = (timeline['completed_issues'] / timeline['total_issues'] * 100)
        
        return timeline