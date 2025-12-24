FROM python:3.11-slim

WORKDIR /app

# Копируем файл зависимостей
COPY src/requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY src/ .

# Открываем порт
EXPOSE 5000

# Запускаем приложение
CMD ["python", "app.py"]

