import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Optional, Dict
import os
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Visualizer:
    def __init__(self, df: pd.DataFrame, metrics: dict, recommendations: Optional[Dict[str, str]] = None):
        self.df = df
        self.metrics = metrics
        self.recommendations = recommendations
        self.output_dir = Config.OUTPUT_DIR
        
        # Создаем папку для выходных файлов
        os.makedirs(self.output_dir, exist_ok=True)
    
    def create_dashboard(self) -> go.Figure:
        """Создание комплексного дашборда"""
        if self.df.empty:
            return go.Figure()
        
        # Создаем подграфики 2x2 + блок с рекомендациями
        fig = make_subplots(
            rows=4, 
            cols=2,
            subplot_titles=(
                'Статусы задач', 
                'Загрузка исполнителей',
                'Скорость по спринтам (Story Points)', 
                'Типы задач',
                'Спринт: Завершение vs Всего',
                'Распределение приоритетов',
                '📊 Рекомендации AI',  # Новый ряд для рекомендаций
                ''
            ),
            specs=[
                [{"type": "pie"}, {"type": "bar"}],
                [{"type": "bar"}, {"type": "pie"}],
                [{"type": "bar"}, {"type": "pie"}],
                [{"type": "domain"}, {"type": "domain"}]  # Пустые для текста
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.15
        )
        
        # ... (все предыдущие графики остаются без изменений) ...
        # Добавляем графики как в предыдущей версии (строки 1-3)
        
        # Добавляем аннотацию с рекомендациями в 4-й ряд
        if self.recommendations:
            summary_text = self.recommendations.get('summary', 'Рекомендации не сгенерированы')
            
            # Добавляем текстовую аннотацию
            fig.add_annotation(
                text=f"<b>🎯 Итоговые рекомендации от AI</b><br><br>{summary_text}",
                xref="paper",
                yref="paper",
                x=0.5,
                y=-0.05,
                showarrow=False,
                font=dict(size=14, color="black"),
                align="left",
                bgcolor="rgba(240, 248, 255, 0.9)",
                bordercolor="blue",
                borderwidth=2,
                borderpad=15
            )
        
        # Обновление layout
        fig.update_layout(
            height=1600,  # Увеличиваем высоту для рекомендаций
            width=1400,
            showlegend=True,
            title_text="📊 Jira Аналитика - Дашборд с AI-рекомендациями",
            title_font_size=24,
            template='plotly_white'
        )
        
        return fig
    
    def create_recommendations_page(self) -> go.Figure:
        """Создание отдельной страницы с рекомендациями"""
        if not self.recommendations or self.recommendations.get('error'):
            return go.Figure()
        
        fig = go.Figure()
        
        # Создаем структурированный текст с рекомендациями
        sections = [
            ("📈 Общая эффективность", self.recommendations.get('overall', '')),
            ("👥 Загрузка команды", self.recommendations.get('workload', '')),
            ("🚀 Скорость команды", self.recommendations.get('velocity', '')),
            ("✅ Качество процесса", self.recommendations.get('quality', '')),
            ("🎯 Итоговый вердикт", self.recommendations.get('summary', ''))
        ]
        
        text = "<b>🤖 Аналитика и рекомендации от YandexGPT</b><br><br>"
        
        for title, content in sections:
            if content:
                text += f"<b>{title}</b><br>{content}<br><br>"
        
        fig.add_annotation(
            text=text,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16),
            align="left",
            bgcolor="rgba(255, 255, 255, 0.95)",
            bordercolor="navy",
            borderwidth=3,
            borderpad=20
        )
        
        fig.update_layout(
            title="📋 AI-анализ и рекомендации по проекту",
            height=1000,
            width=1200,
            template='plotly_white',
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[]  # Очищаем стандартные аннотации
        )
        
        # Добавляем наш текст через add_annotation
        fig.add_annotation(
            text=text,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14),
            align="left"
        )
        
        return fig
    
    def save_all_charts(self):
        """Сохранение всех графиков в HTML и PNG"""
        charts = {
            'dashboard': self.create_dashboard,
            'recommendations': self.create_recommendations_page
        }
        
        # Добавляем стандартные графики, если они есть
        if hasattr(self, 'create_velocity_chart'):
            charts['velocity'] = self.create_velocity_chart
        if hasattr(self, 'create_team_workload_chart'):
            charts['team_workload'] = self.create_team_workload_chart
        if hasattr(self, 'create_status_timeline'):
            charts['status_timeline'] = self.create_status_timeline
        
        for name, chart_func in charts.items():
            try:
                fig = chart_func()
                if fig and len(fig.data) > 0:
                    # HTML
                    html_path = os.path.join(self.output_dir, f'{name}.html')
                    fig.write_html(html_path)
                    logger.info(f"✅ Сохранен HTML: {html_path}")
                    
                    # PNG (требуется kaleido)
                    try:
                        png_path = os.path.join(self.output_dir, f'{name}.png')
                        fig.write_image(png_path, width=1400, height=800)
                        logger.info(f"✅ Сохранен PNG: {png_path}")
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось сохранить PNG: {e}")
            except Exception as e:
                logger.error(f"❌ Ошибка при создании графика {name}: {e}")