FROM python:3.11-slim

WORKDIR /app

COPY ../requirements.txt .

# Выводим содержимое requirements.txt и пробуем установить с подробным выводом
RUN echo "=== CONTENT OF requirements.txt ===" && cat requirements.txt && echo "=== END ==="
RUN pip install --no-cache-dir -r requirements.txt --verbose || (echo "=== INSTALLATION FAILED ===" && exit 1)

COPY ../app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
