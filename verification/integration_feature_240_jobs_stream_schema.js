const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken =
  process.env.TACTIX_API_TOKEN ||
  process.env.VITE_TACTIX_API_TOKEN ||
  'local-dev-token';
const jobId = process.env.TACTIX_JOB_ID || 'refresh_metrics';
const source = process.env.TACTIX_SOURCE || 'lichess';

function buildStreamUrl() {
  const params = new URLSearchParams();
  if (source && source !== 'all') params.set('source', source);
  return `${apiBase}/api/jobs/${encodeURIComponent(jobId)}/stream?${params.toString()}`;
}

function assertProgressSchema(payload) {
  if (payload.job !== jobId) {
    throw new Error(`Expected job ${jobId} but got ${payload.job}`);
  }
  if (payload.job_id !== jobId) {
    throw new Error(`Expected job_id ${jobId} but got ${payload.job_id}`);
  }
  if (typeof payload.step !== 'string') {
    throw new Error('Expected progress payload.step to be a string');
  }
  if (!('timestamp' in payload)) {
    throw new Error('Expected progress payload.timestamp to be present');
  }
}

function assertCompleteSchema(payload) {
  if (payload.job !== jobId) {
    throw new Error(`Expected job ${jobId} but got ${payload.job}`);
  }
  if (payload.job_id !== jobId) {
    throw new Error(`Expected job_id ${jobId} but got ${payload.job_id}`);
  }
  if (payload.step !== 'complete') {
    throw new Error(`Expected step=complete but got ${payload.step}`);
  }
  if (typeof payload.message !== 'string') {
    throw new Error('Expected complete payload.message to be a string');
  }
  if (!payload.result || typeof payload.result !== 'object') {
    throw new Error('Expected complete payload.result to be an object');
  }
}

async function verifyStreamSchema() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
  const response = await fetch(buildStreamUrl(), {
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
  let sawProgress = false;
  let sawComplete = false;

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
      if (eventName === 'progress') {
        assertProgressSchema(payload);
        sawProgress = true;
      }
      if (eventName === 'complete') {
        assertCompleteSchema(payload);
        sawComplete = true;
        controller.abort();
        clearTimeout(timeout);
        return { sawProgress, sawComplete };
      }
      if (eventName === 'error') {
        throw new Error(`Stream error: ${payload.message || 'unknown'}`);
      }
    }
  }

  clearTimeout(timeout);
  return { sawProgress, sawComplete };
}

(async () => {
  const result = await verifyStreamSchema();
  if (!result.sawProgress || !result.sawComplete) {
    throw new Error('Did not receive expected progress + complete events');
  }
  console.log('Job stream schema integration check passed.');
})();
