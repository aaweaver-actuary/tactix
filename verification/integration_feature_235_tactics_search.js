const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

const requiredKeys = new Set([
  'tactic_id',
  'game_id',
  'position_id',
  'source',
  'motif',
  'result',
  'user_uci',
  'eval_delta',
  'severity',
  'created_at',
  'best_uci',
  'best_san',
  'explanation',
  'eval_cp',
]);

async function fetchTactics() {
  const url = `${apiBase}/api/tactics/search?source=all&limit=5`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (!res.ok) {
    throw new Error(`Tactics search failed: ${res.status}`);
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
    const payload = await fetchTactics();
    assert(payload.source === 'all', 'Expected source=all');
    assert(Number.isInteger(payload.limit), 'Expected limit integer');
    assert(Array.isArray(payload.tactics), 'Expected tactics array');

    if (payload.tactics.length) {
      const row = payload.tactics[0];
      for (const key of requiredKeys) {
        assert(Object.prototype.hasOwnProperty.call(row, key), `Missing key: ${key}`);
      }
    }

    console.log('Feature 235 integration check ok');
  } catch (err) {
    console.error('Feature 235 integration check failed:', err);
    process.exit(1);
  }
})();
