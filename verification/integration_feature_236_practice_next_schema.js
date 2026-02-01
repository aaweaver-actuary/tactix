const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

const requiredKeys = new Set([
  'tactic_id',
  'game_id',
  'position_id',
  'source',
  'motif',
  'result',
  'best_uci',
  'user_uci',
  'eval_delta',
  'severity',
  'created_at',
  'fen',
  'position_uci',
  'san',
  'ply',
  'move_number',
  'side_to_move',
  'clock_seconds',
]);

async function fetchPracticeNext() {
  const url = `${apiBase}/api/practice/next?source=lichess&include_failed_attempt=0`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (!res.ok) {
    throw new Error(`Practice next fetch failed: ${res.status}`);
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
    const payload = await fetchPracticeNext();
    assert(payload.source, 'Expected source in payload');
    assert(
      typeof payload.include_failed_attempt === 'boolean',
      'Expected include_failed_attempt boolean',
    );
    assert(Object.prototype.hasOwnProperty.call(payload, 'item'), 'Expected item key');

    if (payload.item) {
      for (const key of requiredKeys) {
        assert(
          Object.prototype.hasOwnProperty.call(payload.item, key),
          `Missing key: ${key}`,
        );
      }
      assert(Number.isInteger(payload.item.tactic_id), 'Expected tactic_id integer');
      assert(Number.isInteger(payload.item.position_id), 'Expected position_id integer');
      assert(typeof payload.item.source === 'string', 'Expected source string');
      assert(typeof payload.item.motif === 'string', 'Expected motif string');
    }

    console.log('Feature 236 integration check ok');
  } catch (err) {
    console.error('Feature 236 integration check failed:', err);
    process.exit(1);
  }
})();
