const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const jobId = process.env.TACTIX_JOB_ID || 'refresh_metrics';
const source = process.env.TACTIX_SOURCE || 'lichess';
const backfillStartMs = Number(process.env.TACTIX_BACKFILL_START_MS || '1000');
const backfillEndMs = Number(process.env.TACTIX_BACKFILL_END_MS || '2000');

const requiredKeys = new Set([
  'status',
  'job',
  'job_id',
  'source',
  'profile',
  'backfill_start_ms',
  'backfill_end_ms',
  'requested_at_ms',
  'airflow_enabled',
]);

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function fetchJobDetail() {
  const url = `${apiBase}/api/jobs/${encodeURIComponent(jobId)}?source=${encodeURIComponent(
    source,
  )}&backfill_start_ms=${encodeURIComponent(backfillStartMs)}&backfill_end_ms=${encodeURIComponent(
    backfillEndMs,
  )}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (!res.ok) {
    throw new Error(`Job status fetch failed: ${res.status}`);
  }
  return res.json();
}

(async () => {
  try {
    const payload = await fetchJobDetail();
    for (const key of requiredKeys) {
      assert(
        Object.prototype.hasOwnProperty.call(payload, key),
        `Missing key: ${key}`,
      );
    }
    assert(payload.status === 'ok', 'Expected status=ok');
    assert(payload.job === jobId, `Expected job=${jobId}`);
    assert(payload.job_id === jobId, `Expected job_id=${jobId}`);
    assert(payload.source === source, `Expected source=${source}`);
    assert(payload.backfill_start_ms === backfillStartMs, 'Expected backfill_start_ms');
    assert(payload.backfill_end_ms === backfillEndMs, 'Expected backfill_end_ms');
    assert(
      Number.isInteger(payload.requested_at_ms),
      'Expected requested_at_ms integer',
    );
    assert(typeof payload.airflow_enabled === 'boolean', 'Expected airflow_enabled boolean');
    console.log('Feature 239 integration check ok');
  } catch (err) {
    console.error('Feature 239 integration check failed:', err);
    process.exit(1);
  }
})();
