import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Optional, Dict
import os
import json
from config import Config
import logging
from datetime import datetime
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Visualizer:
    def __init__(self, df: pd.DataFrame, metrics: dict, recommendations: Optional[Dict[str, str]] = None):
        self.df = df
        self.metrics = metrics
        self.recommendations = recommendations
        self.output_dir = Config.OUTPUT_DIR
        
        # Если рекомендации не переданы, пробуем загрузить из файла
        if not self.recommendations:
            try:
                json_path = os.path.join(self.output_dir, 'recommendations.json')
                if os.path.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as f:
                        self.recommendations = json.load(f)
                    logger.info("✅ Рекомендации загружены из recommendations.json")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось загрузить рекомендации из файла: {e}")
        
        # Создаем папку для выходных файлов
        os.makedirs(self.output_dir, exist_ok=True)
    
    def create_dashboard(self) -> go.Figure:
        """Создание дашборда с графиками"""
        if self.df.empty:
            return go.Figure()
        
        fig = make_subplots(
            rows=3,
            cols=2,
            subplot_titles=(
                'Статусы задач',
                'Загрузка исполнителей',
                'Приоритеты задач',
                'Типы задач',
                'Story Points по задачам',
                'Динамика задач'
            ),
            specs=[
                [{"type": "pie"}, {"type": "bar"}],
                [{"type": "pie"}, {"type": "pie"}],
                [{"type": "bar"}, {"type": "scatter"}]
            ]
        )
        
        # 1. Статусы задач
        status_counts = self.df['status'].value_counts()
        if not status_counts.empty:
            fig.add_trace(
                go.Pie(labels=status_counts.index, values=status_counts.values, name='Статусы'),
                row=1, col=1
            )
        
        # 2. Загрузка исполнителей
        assignee_counts = self.df['assignee'].value_counts().head(10)
        if not assignee_counts.empty:
            fig.add_trace(
                go.Bar(x=assignee_counts.index, y=assignee_counts.values, name='Исполнители'),
                row=1, col=2
            )
        
        # 3. Приоритеты
        priority_counts = self.df['priority'].value_counts()
        if not priority_counts.empty:
            fig.add_trace(
                go.Pie(labels=priority_counts.index, values=priority_counts.values, name='Приоритеты'),
                row=2, col=1
            )
        
        # 4. Типы задач
        type_counts = self.df['issue_type'].value_counts()
        if not type_counts.empty:
            fig.add_trace(
                go.Pie(labels=type_counts.index, values=type_counts.values, name='Типы задач'),
                row=2, col=2
            )
        
        # 5. Story Points по задачам
        if 'story_points' in self.df.columns:
            sp_df = self.df[self.df['story_points'].notna()]
            if not sp_df.empty:
                fig.add_trace(
                    go.Bar(x=sp_df['key'], y=sp_df['story_points'], name='Story Points'),
                    row=3, col=1
                )
        
        # 6. Динамика создания задач
        if 'created' in self.df.columns:
            self.df['created_date'] = pd.to_datetime(self.df['created']).dt.date
            created_by_day = self.df.groupby('created_date').size().reset_index(name='count')
            if not created_by_day.empty:
                fig.add_trace(
                    go.Scatter(x=created_by_day['created_date'], y=created_by_day['count'], 
                              mode='lines+markers', name='Создано задач'),
                    row=3, col=2
                )
        
        fig.update_layout(
            height=1200,
            width=1400,
            title_text="📊 Jira Аналитика - Дашборд",
            template='plotly_white',
            showlegend=True
        )
        
        return fig
    
    def _clean_text(self, text: str) -> str:
        """Очистка текста от HTML-тегов и лишних пробелов"""
        if not text:
            return ''
        
        # Убираем все HTML-теги <br> и подобные
        text = re.sub(r'<br\s*/?>', ' ', text)
        
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        # Убираем пробелы в начале и конце
        text = text.strip()
        
        return text
    
    def save_recommendations_html(self):
        """Сохранение рекомендаций в отдельный HTML-файл с полноценной вёрсткой"""
        
        if not self.recommendations:
            logger.warning("⚠️ Нет рекомендаций для сохранения")
            html_content = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-рекомендации по проекту</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f2f5; padding: 40px; }
        .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 16px; padding: 40px; }
        h1 { color: #1a5276; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚠️ Рекомендации не сгенерированы</h1>
        <p>Проверьте настройки YandexGPT или используйте fallback-аналитику.</p>
    </div>
</body>
</html>'''
        else:
            # Формируем полный HTML с рекомендациями
            sections_html = ""
            
            if self.recommendations.get('summary'):
                sections_html += f'''
                <div class="section summary">
                    <h2>🎯 Итоговый вердикт</h2>
                    <p>{self._clean_text(self.recommendations['summary'])}</p>
                </div>
                '''
            
            if self.recommendations.get('overall'):
                sections_html += f'''
                <div class="section overall">
                    <h2>📈 Общая эффективность</h2>
                    <p>{self._clean_text(self.recommendations['overall'])}</p>
                </div>
                '''
            
            if self.recommendations.get('workload'):
                sections_html += f'''
                <div class="section workload">
                    <h2>👥 Загрузка команды</h2>
                    <p>{self._clean_text(self.recommendations['workload'])}</p>
                </div>
                '''
            
            if self.recommendations.get('velocity'):
                sections_html += f'''
                <div class="section velocity">
                    <h2>🚀 Скорость команды</h2>
                    <p>{self._clean_text(self.recommendations['velocity'])}</p>
                </div>
                '''
            
            if self.recommendations.get('quality'):
                sections_html += f'''
                <div class="section quality">
                    <h2>✅ Качество процесса</h2>
                    <p>{self._clean_text(self.recommendations['quality'])}</p>
                </div>
                '''
            
            html_content = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-рекомендации по проекту</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #f0f2f5;
            margin: 0;
            padding: 40px 20px;
            color: #1a1a2e;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 40px 50px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.08);
        }}
        h1 {{
            color: #1a5276;
            text-align: center;
            border-bottom: 4px solid #1a5276;
            padding-bottom: 20px;
            font-size: 32px;
            margin-top: 0;
        }}
        .section {{
            padding: 20px 25px;
            border-radius: 12px;
            margin-bottom: 25px;
            border-left: 6px solid #1a5276;
        }}
        .section h2 {{
            margin-top: 0;
            font-size: 20px;
            color: #1a1a2e;
        }}
        .section p {{
            font-size: 16px;
            line-height: 1.9;
            margin-bottom: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .section.summary {{ background: #eaf4fb; border-left-color: #1a5276; }}
        .section.overall {{ background: #f5f5f5; border-left-color: #7f8c8d; }}
        .section.workload {{ background: #fef9e7; border-left-color: #f39c12; }}
        .section.velocity {{ background: #eafaf1; border-left-color: #27ae60; }}
        .section.quality {{ background: #fdedec; border-left-color: #e74c3c; }}
        .footer {{
            text-align: center;
            color: #7f8c8d;
            font-size: 14px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
        .badge {{
            display: inline-block;
            background: #1a5276;
            color: white;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 0.5px;
        }}
        .meta-info {{
            text-align: center;
            color: #95a5a6;
            font-size: 13px;
            margin-bottom: 25px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Аналитика и рекомендации от YandexGPT</h1>
        <div class="meta-info">Сгенерировано {datetime.now().strftime('%d.%m.%Y в %H:%M')}</div>
        
        {sections_html}
        
        <div class="footer">
            <span class="badge">AI-аналитика</span>
            &nbsp;•&nbsp; YandexGPT &nbsp;•&nbsp; Jira Analytics Tool
        </div>
    </div>
</body>
</html>'''
        
        # Сохраняем файл
        html_path = os.path.join(self.output_dir, 'recommendations.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"✅ Сохранены рекомендации в HTML: {html_path}")
    
    def save_all_charts(self):
        """Сохранение всех графиков в HTML"""
        # Сохраняем дашборд
        try:
            fig = self.create_dashboard()
            if fig and len(fig.data) > 0:
                html_path = os.path.join(self.output_dir, 'dashboard.html')
                fig.write_html(html_path)
                logger.info(f"✅ Сохранен HTML: {html_path}")
            else:
                logger.warning("⚠️ Дашборд пустой")
        except Exception as e:
            logger.error(f"❌ Ошибка при создании дашборда: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Сохраняем рекомендации отдельно
        self.save_recommendations_html()