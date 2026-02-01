const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

const practiceSource = process.env.TACTIX_PRACTICE_SOURCE || 'chesscom';

const requiredKeys = new Set([
  'attempt_id',
  'tactic_id',
  'position_id',
  'source',
  'attempted_uci',
  'best_uci',
  'best_san',
  'correct',
  'success',
  'motif',
  'severity',
  'eval_delta',
  'message',
  'explanation',
  'latency_ms',
]);

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function fetchPracticeNext() {
  const url = `${apiBase}/api/practice/next?source=${practiceSource}&include_failed_attempt=0`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (!res.ok) {
    throw new Error(`Practice next fetch failed: ${res.status}`);
  }
  return res.json();
}

async function postPracticeAttempt(payload) {
  const res = await fetch(`${apiBase}/api/practice/attempt`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Practice attempt failed: ${res.status}`);
  }
  return res.json();
}

(async () => {
  try {
    const nextPayload = await fetchPracticeNext();
    assert(nextPayload.item, 'Expected practice item in payload');

    const bestUci =
      nextPayload.item.best_uci || nextPayload.item.position_uci || 'e2e4';
    const attemptPayload = {
      tactic_id: nextPayload.item.tactic_id,
      position_id: nextPayload.item.position_id,
      attempted_uci: bestUci,
      served_at_ms: Date.now() - 250,
    };

    const attempt = await postPracticeAttempt(attemptPayload);
    for (const key of requiredKeys) {
      assert(Object.prototype.hasOwnProperty.call(attempt, key), `Missing key: ${key}`);
    }
    assert(Number.isInteger(attempt.attempt_id), 'Expected attempt_id integer');
    assert(Number.isInteger(attempt.tactic_id), 'Expected tactic_id integer');
    assert(Number.isInteger(attempt.position_id), 'Expected position_id integer');
    assert(typeof attempt.attempted_uci === 'string', 'Expected attempted_uci string');
    assert(typeof attempt.best_uci === 'string', 'Expected best_uci string');
    assert(typeof attempt.correct === 'boolean', 'Expected correct boolean');
    assert(typeof attempt.success === 'boolean', 'Expected success boolean');
    assert(typeof attempt.motif === 'string', 'Expected motif string');

    console.log('Feature 237 integration check ok');
  } catch (err) {
    console.error('Feature 237 integration check failed:', err);
    process.exit(1);
  }
})();
