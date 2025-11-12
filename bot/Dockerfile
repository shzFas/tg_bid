FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# системные зависимости (для ssl и сертификатов)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt

# копируем исходники
COPY src /app/src

# передаём часовой пояс
ENV TZ=${TZ:-Europe/Prague}

# запускаем бота
CMD ["python", "-m", "src.main"]
