const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken =
  process.env.TACTIX_API_TOKEN ||
  process.env.VITE_TACTIX_API_TOKEN ||
  'local-dev-token';
const source = process.env.TACTIX_SOURCE || 'lichess';

function getStreamUrl(backfillStartMs, backfillEndMs) {
  const params = new URLSearchParams({
    job: 'daily_game_sync',
    source,
    backfill_start_ms: String(backfillStartMs),
    backfill_end_ms: String(backfillEndMs),
  });
  return `${apiBase}/api/jobs/stream?${params.toString()}`;
}

async function waitForBackfillTrigger() {
  const now = Date.now();
  const backfillStartMs = now - 7 * 24 * 60 * 60 * 1000;
  const backfillEndMs = now + 7 * 24 * 60 * 60 * 1000;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
  const response = await fetch(getStreamUrl(backfillStartMs, backfillEndMs), {
    headers: { Authorization: `Bearer ${apiToken}` },
    signal: controller.signal,
  });

  if (!response.ok || !response.body) {
    clearTimeout(timeout);
    throw new Error(`Stream request failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let backfillWindowOk = false;
  let airflowTriggered = false;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';

    for (const part of parts) {
      const lines = part.split('\n');
      let eventName = 'message';
      let data = '';
      for (const line of lines) {
        if (!line || line.startsWith(':')) continue;
        if (line.startsWith('event:')) {
          eventName = line.replace('event:', '').trim();
        } else if (line.startsWith('data:')) {
          data += line.replace('data:', '').trim();
        }
      }
      if (eventName !== 'progress' || !data) continue;
      const payload = JSON.parse(data);
      if (payload.step === 'backfill_window') {
        if (!payload.backfill_start_ms || !payload.backfill_end_ms) {
          throw new Error('Backfill window payload missing timestamps');
        }
        if (payload.backfill_start_ms !== backfillStartMs) {
          throw new Error('Backfill start timestamp mismatch');
        }
        if (
          payload.triggered_at_ms &&
          payload.backfill_end_ms > payload.triggered_at_ms
        ) {
          throw new Error(
            'Backfill end timestamp was not clamped to trigger time',
          );
        }
        backfillWindowOk = true;
      }
      if (payload.step === 'airflow_triggered') {
        airflowTriggered = true;
      }
      if (backfillWindowOk && airflowTriggered) {
        controller.abort();
        clearTimeout(timeout);
        return true;
      }
    }
  }

  clearTimeout(timeout);
  return backfillWindowOk && airflowTriggered;
}

(async () => {
  const ok = await waitForBackfillTrigger();
  if (!ok) {
    throw new Error(
      'Did not receive backfill_window and airflow_triggered events',
    );
  }
  console.log('Backfill trigger stream event verified.');
})();
