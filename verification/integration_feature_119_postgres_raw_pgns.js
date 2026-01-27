const API_BASE = process.env.TACTIX_API_BASE || 'http://localhost:8000';
const API_TOKEN = process.env.TACTIX_API_TOKEN || 'local-dev-token';

async function fetchSummary() {
  const response = await fetch(`${API_BASE}/api/postgres/raw_pgns`, {
    headers: { Authorization: `Bearer ${API_TOKEN}` },
  });
  if (!response.ok) {
    throw new Error(`Postgres raw PGNs fetch failed: ${response.status}`);
  }
  return response.json();
}

async function triggerDailySync(source) {
  const url = new URL(`${API_BASE}/api/jobs/daily_game_sync`);
  url.searchParams.set('source', source);
  url.searchParams.set('backfill_start_ms', '0');
  url.searchParams.set('backfill_end_ms', '32503680000000');
  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: { Authorization: `Bearer ${API_TOKEN}` },
  });
  if (!response.ok) {
    throw new Error(`Daily sync trigger failed: ${response.status}`);
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

(async () => {
  let summary = await fetchSummary();
  if (summary.status === 'disabled') {
    throw new Error('Postgres raw PGN mirror is disabled');
  }

  if (!summary.total_rows) {
    await triggerDailySync('lichess');
    for (let attempt = 0; attempt < 6; attempt += 1) {
      await delay(5000);
      summary = await fetchSummary();
      if (summary.total_rows) break;
    }
  }

  if (!summary.total_rows) {
    throw new Error('Expected Postgres raw PGN rows after daily sync');
  }
  if (!Array.isArray(summary.sources) || summary.sources.length === 0) {
    throw new Error('Expected Postgres raw PGN source breakdown');
  }
  console.log('CI check ok: Postgres raw PGN rows available');
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
