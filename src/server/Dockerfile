FROM python:3.10

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

RUN mkdir -p /app/data

EXPOSE 3000

ENV PORT=3000 \
    REQUEST_LIMIT=100 \
    CACHE_TTL=30 \
    REDIS_URL=redis://127.0.0.1:6379 \
    DB_PATH=/app/data/species.db

CMD ["python", "app.py"]
