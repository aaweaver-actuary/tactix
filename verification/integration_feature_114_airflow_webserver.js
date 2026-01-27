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
    const dags = await fetchJson(`${baseUrl}/api/v1/dags?limit=200`, {
      headers: {
        Authorization: authHeader(),
      },
    });

    const dagIds = (dags.dags || []).map((dag) => dag.dag_id);
    if (!dagIds.length) {
      throw new Error('No DAGs returned from Airflow API');
    }
    if (!dagIds.includes(dagId)) {
      throw new Error(`Expected DAG ${dagId} not found in API response`);
    }

    const runId = `feature-114-${Date.now()}`;
    const dagRun = await fetchJson(`${baseUrl}/api/v1/dags/${dagId}/dagRuns`, {
      method: 'POST',
      headers: {
        Authorization: authHeader(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        dag_run_id: runId,
        conf: {
          source: process.env.TACTIX_SOURCE || 'lichess',
        },
      }),
    });

    if (!dagRun || dagRun.dag_run_id !== runId) {
      throw new Error('Failed to trigger DAG via Airflow API');
    }

    console.log('CI check ok');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
})();
