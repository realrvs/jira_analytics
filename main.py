import logging
import sys
import json
import os
from config import Config
from jira_client import JiraClient
from data_processor import DataProcessor
from visualizer import Visualizer
from yandex_analyzer import YandexGptAnalyzer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("🚀 Запуск Jira Analytics Tool с AI-аналитикой")
    
    try:
        # 1. Проверка конфигурации
        Config.validate()
        
        # 2. Подключение к Jira
        logger.info("📡 Подключение к Jira...")
        client = JiraClient()
        
        # 3. Получение данных
        logger.info("📊 Получение данных...")
        df = client.get_all_sprints_data()
        
        if df.empty:
            logger.error("❌ Данные не получены. Проверьте настройки.")
            sys.exit(1)
        
        logger.info(f"✅ Получено {len(df)} задач")
        
        # 4. Расчет метрик
        logger.info("🧮 Расчет метрик...")
        processor = DataProcessor()
        metrics = processor.calculate_metrics(df)
        
        # 5. Генерация AI-рекомендаций
        logger.info("🤖 Генерация рекомендаций через YandexGPT...")
        analyzer = YandexGptAnalyzer()
        recommendations = analyzer.analyze_metrics(metrics, df)
        
        if recommendations and 'error' not in recommendations:
            # Сохраняем рекомендации в JSON
            os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
            with open(f"{Config.OUTPUT_DIR}/recommendations.json", 'w', encoding='utf-8') as f:
                json.dump(recommendations, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Рекомендации сохранены: {Config.OUTPUT_DIR}/recommendations.json")
            
            # Выводим в консоль для наглядности
            logger.info("\n" + "="*80)
            logger.info("🎯 РЕКОМЕНДАЦИИ ОТ YANDEXGPT:")
            logger.info("="*80)
            
            if 'summary' in recommendations:
                logger.info(f"\n📌 ИТОГОВЫЙ ВЕРДИКТ:\n{recommendations['summary']}\n")
            
            if 'overall' in recommendations:
                logger.info(f"📈 ЭФФЕКТИВНОСТЬ:\n{recommendations['overall']}\n")
            
            if 'workload' in recommendations:
                logger.info(f"👥 ЗАГРУЗКА:\n{recommendations['workload']}\n")
            
            if 'velocity' in recommendations:
                logger.info(f"🚀 СКОРОСТЬ:\n{recommendations['velocity']}\n")
            
            if 'quality' in recommendations:
                logger.info(f"✅ КАЧЕСТВО:\n{recommendations['quality']}\n")
            
            logger.info("="*80 + "\n")
        else:
            logger.warning("⚠️ AI-рекомендации не получены")
            recommendations = None
        
        # 6. Создание дашбордов с рекомендациями
        logger.info("📈 Создание дашбордов...")
        visualizer = Visualizer(df, metrics, recommendations)
        visualizer.save_all_charts()
        
        # 7. Экспорт сырых данных
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        df.to_csv(f"{Config.OUTPUT_DIR}/jira_data_export.csv", index=False)
        logger.info(f"✅ Экспорт данных сохранен: {Config.OUTPUT_DIR}/jira_data_export.csv")
        
        logger.info("✅ Готово! Откройте HTML файлы в папке output/ для просмотра.")
        logger.info("📄 Рекомендации: output/recommendations.html и output/dashboard.html")
        
        # Вывод краткой сводки
        logger.info("\n📊 СВОДКА:")
        logger.info(f"   - Всего задач: {metrics.get('total_issues', 0)}")
        logger.info(f"   - Завершено: {metrics.get('completed_count', 0)}")
        logger.info(f"   - В работе: {metrics.get('wip_count', 0)}")
        logger.info(f"   - Заблокировано: {metrics.get('blocked_count', 0)}")
        
        if 'total_story_points' in metrics and metrics['total_story_points'] > 0:
            logger.info(f"   - Story Points: {metrics['total_story_points']:.1f}")
        if 'total_time_spent_hours' in metrics and metrics['total_time_spent_hours'] > 0:
            logger.info(f"   - Затрачено часов: {metrics['total_time_spent_hours']:.1f}")
        if 'avg_velocity' in metrics:
            logger.info(f"   - Средняя скорость: {metrics['avg_velocity']:.1f} SP/спринт")
        
        logger.info(f"   - Исполнителей: {len(metrics.get('assignee_distribution', {}))}")
        logger.info(f"   - Типов задач: {len(metrics.get('issue_type_distribution', {}))}")
        
        # Вывод распределения по статусам
        if 'status_distribution' in metrics:
            logger.info("\n📊 РАСПРЕДЕЛЕНИЕ ПО СТАТУСАМ:")
            for status, count in metrics['status_distribution'].items():
                logger.info(f"   - {status}: {count}")
        
        logger.info("\n✅ Анализ завершен успешно!")
        
    except KeyboardInterrupt:
        logger.info("⚠️ Прервано пользователем")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()