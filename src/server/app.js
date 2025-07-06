require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const { createClient } = require('redis');
const sqlite3 = require('sqlite3').verbose();
const { open } = require('sqlite');
const fs = require('fs');
const path = require('path');

const app = express();

// ENV variables
const port = process.env.PORT || 3000;
const REQUEST_LIMIT = parseInt(process.env.REQUEST_LIMIT, 10) || 100;
const CACHE_TTL = parseInt(process.env.CACHE_TTL, 10) || 30;
const REDIS_URL = process.env.REDIS_URL;
const DB_PATH = process.env.DB_PATH || "/app/data/species.db";
const podName = process.env.HOSTNAME || 'unknown';

console.log('[INIT] Starting service initialization');
if (!REDIS_URL || !DB_PATH) {
  console.error('[INIT][ERROR] REDIS_URL and DB_PATH must be set');
  process.exit(1);
}

// Initialize Redis client
console.log('[INIT] Connecting to Redis at', REDIS_URL);
const redisClient = createClient({ url: REDIS_URL });
redisClient.on('error', err => console.error('[REDIS][ERROR]', err));
(async () => {
  await redisClient.connect();
  console.log('[REDIS] Connected successfully');
})();

// Initialize SQLite database
let db;
(async () => {
  try {
    console.log('[DB] Opening SQLite database at', DB_PATH);
    const dir = path.dirname(DB_PATH);
    if (!fs.existsSync(dir)) {
      console.log('[DB] Creating data directory at', dir);
      fs.mkdirSync(dir, { recursive: true });
    }

    db = await open({ filename: DB_PATH, driver: sqlite3.Database });
    console.log('[DB] SQLite database opened');

    // Create species table if missing
    console.log('[DB] Ensuring species table exists');
    await db.exec(`
      CREATE TABLE IF NOT EXISTS species (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        info TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        count INTEGER DEFAULT 0
      );
    `);
    console.log('[DB] Species table is ready');

    // Seed data if seed file exists
    const seedFile = 'species_seed.json';
    if (fs.existsSync(seedFile)) {
      console.log('[DB] Seeding species data from', seedFile);
      const data = JSON.parse(fs.readFileSync(seedFile, 'utf-8'));
      const stmt = await db.prepare(
        `INSERT INTO species (id, name, info)
         VALUES (?, ?, ?)
         ON CONFLICT(id)
         DO UPDATE SET name=excluded.name, info=excluded.info`
      );
      for (const rec of data) {
        await stmt.run(rec.id, rec.name, JSON.stringify(rec.info));
      }
      await stmt.finalize();
      console.log(`[DB] Seeded ${data.length} species records`);
    } else {
      console.warn('[DB][WARN] No seed file found at', seedFile);
    }
  } catch (error) {
    console.error('[DB][ERROR] Initialization failed:', error);
    process.exit(1);
  }
})();

// JSON parser
app.use(bodyParser.json());

// LoadShedding middleware
let timestamps = [];
app.use((req, res, next) => {
  const now = Date.now();
  timestamps = timestamps.filter(t => now - t < 60000);
  console.log(`[RATE] Window size: ${timestamps.length}/${REQUEST_LIMIT}`);
  if (timestamps.length >= REQUEST_LIMIT) {
    console.warn('[RATE][WARN] Rate limit exceeded');
    return res.status(429).json({
      pod: process.env.HOSTNAME,
      timestamp: new Date().toISOString(),
      fromCache: false,
      status: 429,
      error: 'Rate limit exceeded'
    });
  }
  timestamps.push(now);
  console.log('[RATE] Request accepted, updated window size:', timestamps.length);
  next();
});

// GET /species/:id endpoint
app.get('/species/:id', async (req, res) => {
  const { id } = req.params;
  const cacheKey = `species:${id}`;
  const timestamp = new Date().toISOString();
  console.log(`[REQUEST] GET /species/${id} @ ${timestamp} by pod ${podName}`);

  try {
    // Attempt Redis cache
    const cached = await redisClient.get(cacheKey);
    if (cached) {
      console.log(`[CACHE] Hit for id=${id} by pod ${podName}`);
      return res.json({
        pod: podName,
        timestamp,
        fromCache: true,
        data: JSON.parse(cached)
      });
    }
    console.log(`[CACHE] Miss for id=${id}, querying DB by pod ${podName}`);

    // Query SQLite
    const row = await db.get('SELECT * FROM species WHERE id = ?', id);
    if (!row) {
      console.warn(`[DB] No record found for id=${id} by pod ${podName}`);
      return res.status(404).json({
        pod: podName,
        timestamp,
        fromCache: false,
        status: 404,
        error: 'Species not found'
      });
    }
    console.log(`[DB] Retrieved record for id=${id} by pod ${podName}`);

    // Cache and respond
    await redisClient.set(cacheKey, JSON.stringify(row), { EX: CACHE_TTL });
    console.log(`[CACHE] Cached record for id=${id} by pod ${podName}`);

    return res.json({
      pod: podName,
      timestamp,
      fromCache: false,
      data: row
    });
  } catch (error) {
    console.error('[REQUEST][ERROR] Failed to handle request:', error);
    return res.status(500).json({
      pod: podName,
      timestamp,
      fromCache: false,
      status: 500,
      error: 'Internal server error'
    });
  }
});

// Start server
app.listen(port, () => {
  console.log(`[INIT] Service listening on port ${port}`);
  console.log(`[INIT] Pod name: ${process.env.HOSTNAME}`);
});
