# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем зависимости
# --no-cache-dir экономит место
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь остальной код приложения в рабочую директорию
COPY . .

# (Команда запуска вынесена в docker-compose.yml)
