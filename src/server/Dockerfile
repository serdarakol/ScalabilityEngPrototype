FROM node:18-alpine

RUN apk add --no-cache \
      python3 \
      make \
      g++ \
      sqlite-dev

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

RUN mkdir -p /app/data

EXPOSE 3000

ENV PORT=3000 \
    REDIS_URL=redis://127.0.0.1:6379 \
    DB_PATH=/app/data/species.db \
    REQUEST_LIMIT=60 \
    CACHE_TTL=30

# Start the service
CMD ["node", "app.js"]
