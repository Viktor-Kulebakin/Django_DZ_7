# Берём официальный стабильный образ Python
FROM python:3.12-slim


# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Настройки для оптимизации работы Python в Docker
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Копируем и устанавливаем зависимости
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir gunicorn \
    && pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в контейнер
COPY . /app/
