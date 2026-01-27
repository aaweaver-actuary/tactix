const baseUrl = process.env.TACTIX_AIRFLOW_URL || 'http://localhost:8080';
const dagId = process.env.TACTIX_DAG_ID || 'daily_game_sync';
const airflowUser = process.env.AIRFLOW_USERNAME || 'admin';
const airflowPass = process.env.AIRFLOW_PASSWORD || 'admin';

function authHeader() {
  const token = Buffer.from(`${airflowUser}:${airflowPass}`).toString('base64');
  return `Basic ${token}`;
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed (${res.status}): ${text}`);
  }
  return res.json();
}

(async () => {
  try {
    const health = await fetchJson(`${baseUrl}/api/v1/health`, {
      headers: {
        Authorization: authHeader(),
      },
    });

    const schedulerStatus = String(health?.scheduler?.status || '').toLowerCase();
    if (!schedulerStatus || schedulerStatus !== 'healthy') {
      throw new Error(`Scheduler health check failed: ${schedulerStatus || 'unknown'}`);
    }

    const dagInfo = await fetchJson(`${baseUrl}/api/v1/dags/${dagId}`, {
      headers: {
        Authorization: authHeader(),
      },
    });

    if (dagInfo?.is_paused) {
      throw new Error(`DAG ${dagId} is paused`);
    }

    const runs = await fetchJson(
      `${baseUrl}/api/v1/dags/${dagId}/dagRuns?limit=1&order_by=-execution_date`,
      {
        headers: {
          Authorization: authHeader(),
        },
      },
    );

    const dagRuns = runs?.dag_runs || [];
    if (!dagRuns.length) {
      throw new Error(`No DAG runs found for ${dagId}`);
    }

    const state = String(dagRuns[0]?.state || '').toLowerCase();
    if (!['success', 'running', 'queued'].includes(state)) {
      throw new Error(`Unexpected DAG run state for ${dagId}: ${state || 'unknown'}`);
    }

    console.log('CI check ok');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
})();
