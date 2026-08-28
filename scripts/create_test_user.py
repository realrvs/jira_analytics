# Jira Analytics Tool

Enterprise AI-PMO Platform для анализа проектов в Jira с использованием YandexGPT.

## Быстрый старт

### 1. Клонируйте репозиторий и создайте .env файл
\\\ash
cp .env.example .env
\\\

### 2. Запустите Docker-контейнеры
\\\ash
cd docker
docker-compose up -d
\\\

### 3. Создайте тестовых пользователей
\\\ash
docker exec -it jira_analytics_api python scripts/create_test_user.py
\\\

### 4. Откройте документацию API
http://localhost:8000/api/docs

## Тестовые учетные записи
- **Администратор:** admin / admin123
- **Project Manager:** pm_user / pm12345

## Структура проекта
\\\
jira_analytics/
├── app/
│   ├── api/           # REST API эндпоинты
│   ├── core/          # Конфигурация, безопасность, БД
│   ├── models/        # SQLAlchemy и Pydantic модели
│   ├── workers/       # Celery задачи
│   └── utils/         # Вспомогательные функции
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
└── scripts/           # Вспомогательные скрипты
\\\
"@ | Out-File -FilePath "README.md" -Encoding utf8

Write-Host "✅ README.md создан" -ForegroundColor Green

# 7. Создаем скрипт для тестового пользователя
Write-Host "👤 Создание create_test_user.py..." -ForegroundColor Yellow

@"
#!/usr/bin/env python
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.sqlalchemy.user import User, UserRole
from app.core.security import get_password_hash

def create_test_user():
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.username == "admin").first()
        if existing_user:
            print("Пользователь admin уже существует")
            return
        
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Administrator",
            role=UserRole.ADMIN,
            is_superuser=True,
            is_active=True
        )
        db.add(admin)
        
        pm = User(
            username="pm_user",
            email="pm@example.com",
            hashed_password=get_password_hash("pm12345"),
            full_name="Project Manager",
            role=UserRole.PM,
            is_superuser=False,
            is_active=True
        )
        db.add(pm)
        
        db.commit()
        print("✅ Тестовые пользователи созданы:")
        print("   - admin / admin123 (администратор)")
        print("   - pm_user / pm12345 (Project Manager)")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()
