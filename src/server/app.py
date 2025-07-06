import os
import json
import sqlite3
import time
from datetime import datetime
from flask import Flask, request, jsonify
import redis

app = Flask(__name__)

# ENV variables
PORT = int(os.getenv("PORT", 3000))
REQUEST_LIMIT = int(os.getenv("REQUEST_LIMIT", "100"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "30"))
REDIS_URL = os.getenv("REDIS_URL")
DB_PATH = os.getenv("DB_PATH", "/app/data/species.db")
POD_NAME = os.getenv("HOSTNAME", "unknown")

# Validate env
print(f"[INIT] Starting service initialization on pod {POD_NAME}")
if not REDIS_URL or not DB_PATH:
    print("[INIT][ERROR] REDIS_URL and DB_PATH must be set")
    exit(1)

# redis
print(f"[INIT] Connecting to Redis at {REDIS_URL}")
redis_client = redis.Redis.from_url(REDIS_URL)

print(f"[DB] Opening SQLite database at {DB_PATH}")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS species (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  info TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  count INTEGER DEFAULT 0
);
""")
conn.commit()
print("[DB] Ensured species table exists")

seed_file = os.path.join(os.getcwd(), 'species_seed.json')
if os.path.exists(seed_file):
    print(f"[DB] Seeding species data from {seed_file}")
    with open(seed_file) as f:
        data = json.load(f)
    for rec in data:
        cursor.execute(
            """
            INSERT INTO species (id, name, info)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET name=excluded.name, info=excluded.info
            """,
            (rec['id'], rec['name'], json.dumps(rec.get('info', {})))
        )
    conn.commit()
    print(f"[DB] Seeded {len(data)} species records")
else:
    print(f"[DB][WARN] No seed file found at {seed_file}")

# LoadShedding strategy
timestamps = []
@app.before_request
def rate_limit():
    global timestamps
    now = time.time() * 1000  # ms
    timestamps = [t for t in timestamps if now - t < 60000]
    print(f"[LoadShedding] Window size: {len(timestamps)}/{REQUEST_LIMIT}")
    if len(timestamps) >= REQUEST_LIMIT:
        print("[LoadShedding][WARN] LoadShedding limit exceeded")
        return jsonify({
            "pod": POD_NAME,
            "timestamp": datetime.utcnow().isoformat(),
            "fromCache": False,
            "status": 429,
            "error": "LoadShedding limit exceeded"
        }), 429
    timestamps.append(now)

@app.route('/species/<id>', methods=['GET'])
def get_species(id):
    timestamp = datetime.utcnow().isoformat()
    print(f"[REQUEST] GET /species/{id} @ {timestamp} by pod {POD_NAME}")
    cache_key = f"species:{id}"

    cached = redis_client.get(cache_key)
    if cached:
        print(f"[CACHE] Hit for id={id} by pod {POD_NAME}")
        return jsonify({
            "pod": POD_NAME,
            "timestamp": timestamp,
            "fromCache": True,
            "data": json.loads(cached)
        })
    print(f"[CACHE] Miss for id={id}, querying DB by pod {POD_NAME}")

    # Query SQLite
    cursor.execute('SELECT * FROM species WHERE id = ?', (id,))
    row = cursor.fetchone()
    if not row:
        print(f"[DB] No record found for id={id} by pod {POD_NAME}")
        return jsonify({
            "pod": POD_NAME,
            "timestamp": timestamp,
            "fromCache": False,
            "status": 404,
            "error": "Species not found"
        }), 404

    record = dict(row)
    print(f"[DB] Retrieved record for id={id} by pod {POD_NAME}")

    # Cache and respond
    redis_client.setex(cache_key, CACHE_TTL, json.dumps(record))
    print(f"[CACHE] Cached record for id={id} by pod {POD_NAME}")

    return jsonify({
        "pod": POD_NAME,
        "timestamp": timestamp,
        "fromCache": False,
        "data": record
    })

if __name__ == '__main__':
    print(f"[INIT] Service listening on port {PORT}")
    app.run(host='0.0.0.0', port=PORT)
