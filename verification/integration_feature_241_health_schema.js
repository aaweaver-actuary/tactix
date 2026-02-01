const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function fetchHealth() {
  const res = await fetch(`${apiBase}/api/health`, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (!res.ok) {
    throw new Error(`Health request failed: ${res.status}`);
  }
  return res.json();
}

(async () => {
  try {
    const payload = await fetchHealth();
    const expectedKeys = ['status', 'service', 'version', 'timestamp'];
    assert(
      expectedKeys.every((key) => Object.prototype.hasOwnProperty.call(payload, key)),
      `Missing keys in payload. Expected: ${expectedKeys.join(', ')}`,
    );
    assert(payload.status === 'ok', 'Expected status "ok"');
    assert(payload.service === 'tactix', 'Expected service "tactix"');
    assert(typeof payload.version === 'string', 'Expected version to be string');
    assert(typeof payload.timestamp === 'string', 'Expected timestamp to be string');
    assert(!Number.isNaN(Date.parse(payload.timestamp)), 'Expected timestamp to be ISO-8601');

    console.log('Feature 241 integration check ok');
  } catch (err) {
    console.error('Feature 241 integration check failed:', err);
    process.exit(1);
  }
})();
