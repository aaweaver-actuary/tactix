const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

const requiredKeys = new Set([
  'source',
  'metric_type',
  'motif',
  'window_days',
  'trend_date',
  'rating_bucket',
  'time_control',
  'total',
  'found',
  'missed',
  'failed_attempt',
  'unclear',
  'found_rate',
  'miss_rate',
  'updated_at',
]);

async function fetchTrendStats() {
  const url = `${apiBase}/api/stats/trends?source=all`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (!res.ok) {
    throw new Error(`Trend stats fetch failed: ${res.status}`);
  }
  return res.json();
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

(async () => {
  try {
    const payload = await fetchTrendStats();
    assert(payload.source === 'all', 'Expected source=all');
    assert(Number.isInteger(payload.metrics_version), 'Expected metrics_version integer');
    assert(Array.isArray(payload.trends), 'Expected trends array');

    if (payload.trends.length) {
      const row = payload.trends[0];
      for (const key of requiredKeys) {
        assert(Object.prototype.hasOwnProperty.call(row, key), `Missing key: ${key}`);
      }
      assert(row.metric_type === 'trend', 'Expected metric_type=trend');
      assert([7, 30].includes(row.window_days), 'Expected window_days 7 or 30');
    }

    console.log('Feature 234 integration check ok');
  } catch (err) {
    console.error('Feature 234 integration check failed:', err);
    process.exit(1);
  }
})();