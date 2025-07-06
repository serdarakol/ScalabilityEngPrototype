require('dotenv').config();
const axios = require('axios');
const fs = require('fs');

const THREADS = parseInt(process.env.THREADS, 10) || 5;
const RATE = parseFloat(process.env.RATE, 10) || 6;
const SPECIES_IDS = process.env.SPECIES_IDS
  ? process.env.SPECIES_IDS.split(',')
  : ['1','2','3','4','5', '6','7','8','9','10'];
const SERVER_URL = process.env.SERVER_URL || 'http://localhost:8080';
const OUTPUT_FILE = process.env.OUTPUT_FILE || 'responses.log';
const CLIENT_NAME = process.env.CLIENT_NAME || 'default-client';

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

(async () => {
  const stream = fs.createWriteStream(OUTPUT_FILE, { flags: 'a' });
  console.log(`Starting load generator '${CLIENT_NAME}' with ${THREADS} threads at ${RATE} rpm per thread`);

  const intervalMs = 60000 / RATE;

  const workers = [];
  for (let t = 0; t < THREADS; t++) {
    workers.push((async () => {
      while (true) {
        const id = SPECIES_IDS[Math.floor(Math.random() * SPECIES_IDS.length)];
        const timestamp = new Date().toISOString();
        try {
          const start = Date.now();
          const res = await axios.get(`${SERVER_URL}/species/${id}`);
          const latency = Date.now() - start;

          const entry = {
            client: CLIENT_NAME,
            thread: t,
            timestamp,
            id,
            latency,
            response: res.data
          };
          stream.write(JSON.stringify(entry) + '\n');
        } catch (err) {
          const entry = {
            client: CLIENT_NAME,
            thread: t,
            timestamp,
            id,
            error: JSON.stringify({code: err.code, message: err.message, response: err.response ? err.response.data : null})
          };
          stream.write(JSON.stringify(entry) + '\n');
        }

        await sleep(intervalMs);
      }
    })());
  }

  await Promise.all(workers);
})();
