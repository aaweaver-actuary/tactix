const baseUrl = process.env.TACTIX_API_URL || 'http://localhost:8000';
const token = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const sources = (process.env.TACTIX_SOURCES || 'lichess,chesscom')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Request failed ${response.status}: ${text}`);
  }
  return response.json();
}

async function triggerSync(source) {
  const url = new URL('/api/jobs/daily_game_sync', baseUrl);
  if (source) url.searchParams.set('source', source);
  return fetchJson(url.toString(), {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

async function fetchSummary(source) {
  const url = new URL('/api/raw_pgns/summary', baseUrl);
  if (source) url.searchParams.set('source', source);
  return fetchJson(url.toString(), {
    headers: { Authorization: `Bearer ${token}` },
  });
}

(async () => {
  try {
    for (const source of sources) {
      const trigger = await triggerSync(source);
      if (!trigger || trigger.status !== 'ok') {
        throw new Error(`daily_game_sync failed for ${source}`);
      }
      const summary = await fetchSummary(source);
      const rows = Array.isArray(summary.summary) ? summary.summary : [];
      if (!rows.length) {
        throw new Error(`raw_pgns summary empty for ${source}`);
      }
      for (const row of rows) {
        if (row.missing && Number(row.missing) > 0) {
          throw new Error(
            `raw_pgns missing hashes for ${row.source}: ${row.missing}`,
          );
        }
      }
    }
    console.log('Feature 108 CI check ok');
  } catch (err) {
    console.error('Feature 108 CI verification failed:', err);
    process.exit(1);
  }
})();
