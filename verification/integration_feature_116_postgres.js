const API_BASE = process.env.TACTIX_API_BASE || 'http://localhost:8000';
const API_TOKEN = process.env.TACTIX_API_TOKEN || 'local-dev-token';

async function fetchStatus() {
  const response = await fetch(`${API_BASE}/api/postgres/status`, {
    headers: { Authorization: `Bearer ${API_TOKEN}` },
  });
  if (!response.ok) {
    throw new Error(`Status fetch failed: ${response.status}`);
  }
  return response.json();
}

async function triggerDailySync() {
  const response = await fetch(
    `${API_BASE}/api/jobs/daily_game_sync?source=lichess`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${API_TOKEN}` },
    },
  );
  if (!response.ok) {
    throw new Error(`Daily sync trigger failed: ${response.status}`);
  }
  return response.json();
}

(async () => {
  const status = await fetchStatus();
  if (!status.enabled) {
    throw new Error('Postgres is not enabled');
  }
  if (status.status !== 'ok') {
    throw new Error(`Postgres status not ok: ${status.status}`);
  }
  if (!status.tables || !status.tables.includes('ops_events')) {
    throw new Error('Expected tactix_ops.ops_events table missing');
  }

  if (!status.events || status.events.length === 0) {
    await triggerDailySync();
  }

  const refreshed = await fetchStatus();
  if (!refreshed.events || refreshed.events.length === 0) {
    throw new Error('Expected ops events after daily sync');
  }

  const hasIngestion = refreshed.events.some(
    (event) => event.event_type === 'raw_pgns_persisted',
  );
  const hasAnalysis = refreshed.events.some(
    (event) => event.event_type === 'analysis_complete',
  );
  if (!hasIngestion || !hasAnalysis) {
    throw new Error('Missing ingestion/analysis ops events in Postgres');
  }

  console.log('Postgres integration check passed');
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
