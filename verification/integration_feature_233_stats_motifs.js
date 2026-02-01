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

async function fetchMotifStats() {
  const url = `${apiBase}/api/stats/motifs?source=all`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (!res.ok) {
    throw new Error(`Motif stats fetch failed: ${res.status}`);
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
    const payload = await fetchMotifStats();
    assert(payload.source === 'all', 'Expected source=all');
    assert(Number.isInteger(payload.metrics_version), 'Expected metrics_version integer');
    assert(Array.isArray(payload.motifs), 'Expected motifs array');

    if (payload.motifs.length) {
      const row = payload.motifs[0];
      for (const key of requiredKeys) {
        assert(Object.prototype.hasOwnProperty.call(row, key), `Missing key: ${key}`);
      }
      assert(row.metric_type === 'motif_breakdown', 'Expected metric_type=motif_breakdown');
    }

    console.log('Feature 233 integration check ok');
  } catch (err) {
    console.error('Feature 233 integration check failed:', err);
    process.exit(1);
  }
})();