const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const job = process.env.TACTIX_JOB_NAME || 'migrations';
const source = process.env.TACTIX_SOURCE || 'lichess';

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function triggerJob() {
  const url = `${apiBase}/api/jobs/trigger?job=${encodeURIComponent(job)}&source=${encodeURIComponent(source)}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (!res.ok) {
    throw new Error(`Job trigger failed: ${res.status}`);
  }
  return res.json();
}

(async () => {
  try {
    const payload = await triggerJob();
    assert(payload.status === 'ok', 'Expected status=ok');
    assert(payload.job === job, `Expected job=${job}`);
    assert(payload.result && typeof payload.result === 'object', 'Expected result object');
    console.log('Feature 238 integration check ok');
  } catch (err) {
    console.error('Feature 238 integration check failed:', err);
    process.exit(1);
  }
})();
