const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

const requiredSteps = [
  'start',
  'fetch_games',
  'raw_pgns',
  'raw_pgns_persisted',
  'extract_positions',
  'positions_ready',
  'analyze_positions',
  'metrics_refreshed',
];

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function streamJobEvents() {
  const url = `${apiBase}/api/jobs/stream?job=daily_game_sync&source=chesscom&profile=blitz`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 420000);

  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${apiToken}` },
    signal: controller.signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`Stream request failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  const steps = new Set();
  let lastEvent = null;

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        let eventName = 'message';
        let data = '';
        for (const line of part.split('\n')) {
          if (!line || line.startsWith(':')) continue;
          if (line.startsWith('event:')) {
            eventName = line.replace('event:', '').trim();
          } else if (line.startsWith('data:')) {
            data += line.replace('data:', '').trim();
          }
        }
        if (!data) continue;
        let payload = null;
        try {
          payload = JSON.parse(data);
        } catch (err) {
          continue;
        }
        if (payload?.step) {
          steps.add(payload.step);
        }
        if (payload?.source) {
          assert(payload.source === 'chesscom', 'Expected chesscom source in stream payload');
        }
        lastEvent = eventName;
        if (eventName === 'complete' || eventName === 'error') {
          await reader.cancel();
          return { steps, lastEvent };
        }
      }
    }
  } finally {
    clearTimeout(timeoutId);
  }

  return { steps, lastEvent };
}

(async () => {
  try {
    const { steps, lastEvent } = await streamJobEvents();
    for (const step of requiredSteps) {
      assert(steps.has(step), `Missing step in SSE stream: ${step}`);
    }
    assert(lastEvent !== 'error', 'Stream ended with error event');
    console.log('Feature 012 integration check ok');
  } catch (err) {
    console.error('Feature 012 integration check failed:', err);
    process.exit(1);
  }
})();
