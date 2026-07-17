import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Jira настройки
    JIRA_URL = os.getenv("JIRA_URL", "http://localhost:8080")
    JIRA_USERNAME = os.getenv("JIRA_USERNAME", "admin")
    JIRA_PASSWORD = os.getenv("JIRA_PASSWORD", "")
    JIRA_PROJECT = os.getenv("JIRA_PROJECT", "PROJ")
    
    # Параметры экспорта
    MAX_ISSUES = int(os.getenv("MAX_ISSUES", "1000"))
    SPRINTS_TO_FETCH = int(os.getenv("SPRINTS_TO_FETCH", "10"))
    
    # YandexGPT настройки
    YC_FOLDER_ID = os.getenv("YC_FOLDER_ID", "")
    YC_API_KEY = os.getenv("YC_API_KEY", "")
    YC_IAM_TOKEN = os.getenv("YC_IAM_TOKEN", "")
    
    # Пути
    OUTPUT_DIR = "output"
    
    @classmethod
    def validate(cls):
        """Проверка наличия обязательных переменных"""
        if not cls.JIRA_PASSWORD:
            raise ValueError("JIRA_PASSWORD не задан. Создайте .env файл")
        if not cls.JIRA_PROJECT or cls.JIRA_PROJECT == "PROJ":
            raise ValueError("JIRA_PROJECT не задан. Укажите ключ проекта")
        
        # Создаем выходную папку, если её нет
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
        
        return True
    
    @classmethod
    def is_yandex_gpt_available(cls) -> bool:
        """Проверка наличия настроек для YandexGPT"""
        return bool(cls.YC_FOLDER_ID and (cls.YC_API_KEY or cls.YC_IAM_TOKEN))