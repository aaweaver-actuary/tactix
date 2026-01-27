const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken =
  process.env.TACTIX_API_TOKEN ||
  process.env.VITE_TACTIX_API_TOKEN ||
  'local-dev-token';
const source = process.env.TACTIX_SOURCE || 'lichess';

function getStreamUrl() {
  const params = new URLSearchParams({ job: 'daily_game_sync', source });
  return `${apiBase}/api/jobs/stream?${params.toString()}`;
}

async function waitForAirflowTrigger() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
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
      if (payload.step === 'airflow_triggered') {
        airflowTriggered = true;
        controller.abort();
        clearTimeout(timeout);
        return airflowTriggered;
      }
    }
  }

  clearTimeout(timeout);
  return airflowTriggered;
}

(async () => {
  const ok = await waitForAirflowTrigger();
  if (!ok) {
    throw new Error('Did not receive airflow_triggered progress event');
  }
  console.log('Airflow trigger stream event verified.');
})();
