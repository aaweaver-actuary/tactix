const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken =
  process.env.TACTIX_API_TOKEN ||
  process.env.VITE_TACTIX_API_TOKEN ||
  'local-dev-token';

const requiredKeys = new Set(['status', 'token', 'token_type', 'user']);

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function fetchAuthToken() {
  const url = `${apiBase}/api/auth/token`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (!res.ok) {
    throw new Error(`Auth token fetch failed: ${res.status}`);
  }
  return res.json();
}

(async () => {
  try {
    const payload = await fetchAuthToken();
    for (const key of requiredKeys) {
      assert(
        Object.prototype.hasOwnProperty.call(payload, key),
        `Missing key: ${key}`,
      );
    }
    assert(payload.status === 'ok', 'Expected status=ok');
    assert(payload.token === apiToken, 'Expected token to match supplied token');
    assert(payload.token_type === 'bearer', 'Expected token_type=bearer');
    assert(typeof payload.user === 'string', 'Expected user string');
    console.log('Feature 242 integration check ok');
  } catch (err) {
    console.error('Feature 242 integration check failed:', err);
    process.exit(1);
  }
})();
