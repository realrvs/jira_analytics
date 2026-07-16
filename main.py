import logging
import sys
import json
from config import Config
from jira_client import JiraClient
from data_processor import DataProcessor
from visualizer import Visualizer
from yandex_analyzer import YandexGptAnalyzer

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
            
            logger.info("="*80 + "\n")
        else:
            logger.warning("⚠️ AI-рекомендации не получены")
        
        # 6. Создание дашбордов с рекомендациями
        logger.info("📈 Создание дашбордов...")
        visualizer = Visualizer(df, metrics, recommendations)
        visualizer.save_all_charts()
        
        # 7. Экспорт сырых данных
        df.to_csv(f"{Config.OUTPUT_DIR}/jira_data_export.csv", index=False)
        logger.info(f"✅ Экспорт данных сохранен: {Config.OUTPUT_DIR}/jira_data_export.csv")
        
        logger.info("✅ Готово! Откройте HTML файлы в папке output/ для просмотра.")
        logger.info("📄 Рекомендации: output/recommendations.html и output/dashboard.html")
        
        # Вывод краткой сводки
        logger.info("\n📊 СВОДКА:")
        logger.info(f"   - Всего задач: {metrics.get('total_issues', 0)}")
        logger.info(f"   - Завершено: {metrics.get('completed_count', 0)}")
        if 'total_story_points' in metrics:
            logger.info(f"   - Story Points: {metrics['total_story_points']:.1f}")
        if 'total_time_spent_hours' in metrics:
            logger.info(f"   - Затрачено часов: {metrics['total_time_spent_hours']:.1f}")
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()