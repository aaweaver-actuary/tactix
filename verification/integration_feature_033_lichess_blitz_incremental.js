const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken =
  process.env.TACTIX_API_TOKEN ||
  process.env.VITE_TACTIX_API_TOKEN ||
  'local-dev-token';
const source = process.env.TACTIX_SOURCE || 'lichess';
const profile = process.env.TACTIX_PROFILE || 'blitz';
const job = process.env.TACTIX_JOB || 'daily_game_sync';

function getStreamUrl() {
  const params = new URLSearchParams({
    job,
    source,
    profile,
  });
  return `${apiBase}/api/jobs/stream?${params.toString()}`;
}

async function waitForIncrementalRun() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 180000);
  const response = await fetch(getStreamUrl(), {
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
  let sawAirflowTriggered = false;
  let sawComplete = false;
  let errorMessage = null;

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

      if (!data) continue;
      const payload = JSON.parse(data);
      if (eventName === 'progress' && payload.step === 'airflow_triggered') {
        sawAirflowTriggered = true;
      }
      if (eventName === 'error') {
        errorMessage = payload.message || 'Unknown stream error';
      }
      if (eventName === 'complete') {
        sawComplete = true;
        await reader.cancel();
        break;
      }
    }
    if (sawComplete) break;
  }

  clearTimeout(timeout);
  if (errorMessage) {
    throw new Error(errorMessage);
  }
  return sawAirflowTriggered && sawComplete;
}

(async () => {
  const ok = await waitForIncrementalRun();
  if (!ok) {
    throw new Error('Did not receive airflow_triggered + complete events');
  }
  console.log('Lichess blitz incremental stream verified.');
})();
