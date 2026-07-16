import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Jira настройки
    JIRA_URL = os.getenv("JIRA_URL", "https://your-company.atlassian.net")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL", "your-email@company.com")
    JIRA_TOKEN = os.getenv("JIRA_TOKEN", "your-api-token")
    JIRA_PROJECT = os.getenv("JIRA_PROJECT", "PROJ")
    
    # Параметры экспорта
    MAX_ISSUES = int(os.getenv("MAX_ISSUES", "1000"))
    SPRINTS_TO_FETCH = int(os.getenv("SPRINTS_TO_FETCH", "10"))
    
    # YandexGPT настройки
    YC_FOLDER_ID = os.getenv("YC_FOLDER_ID", "")      # ID каталога в Yandex Cloud
    YC_API_KEY = os.getenv("YC_API_KEY", "")          # API ключ для YandexGPT
    YC_IAM_TOKEN = os.getenv("YC_IAM_TOKEN", "")      # IAM токен (альтернатива API ключу)
    
    # Пути
    OUTPUT_DIR = "output"
    ANALYTICS_DIR = f"{OUTPUT_DIR}/analytics"
    
    @classmethod
    def validate(cls):
        """Проверка наличия обязательных переменных"""
        if not cls.JIRA_TOKEN or cls.JIRA_TOKEN == "your-api-token":
            raise ValueError("JIRA_TOKEN не задан. Создайте .env файл")
        return True
    
    @classmethod
    def is_yandex_gpt_available(cls) -> bool:
        """Проверка наличия настроек для YandexGPT"""
        return bool(cls.YC_FOLDER_ID and (cls.YC_API_KEY or cls.YC_IAM_TOKEN))