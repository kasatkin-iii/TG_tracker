# Используем официальный образ Python с Alpine (лёгкий вариант)
FROM python:3.11-alpine

# Устанавливаем системные зависимости
RUN apk add --no-cache --virtual .build-deps \
    #компиляция Python пакетов
    gcc \
    musl-dev \
    #уменьшение размера контейнера
    && apk add --no-cache \
    #зависимости для python-telegram-bot
    libffi-dev \
    openssl-dev

# Создаём и переходим в рабочую директорию
WORKDIR /app

# Копируем зависимости
# (Отдельное копирование зависимостей позволяет Docker кэшировать этот слой, ускоряя пересборку.)
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Удаляем ненужные системные зависимости
#(После установки пакетов компиляторы больше не нужны - удаляем для уменьшения размера.)
RUN apk del .build-deps gcc musl-dev

# Копируем исходный код (без БД)
COPY *.py ./

# Создаём пустую директорию для БД (том будет монтироваться сюда)
RUN mkdir -p /app/data && chmod 777 /app/data

# Указываем переменную окружения для токена при запуске контейнера.
ENV BOT_TOKEN=""

# Команда для запуска бота
CMD ["python", "main.py"]