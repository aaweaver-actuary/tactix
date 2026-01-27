const { execSync } = require('child_process');

const baseUrl = process.env.TACTIX_AIRFLOW_URL || 'http://localhost:8080';
const airflowUser = process.env.AIRFLOW_USERNAME || 'admin';
const airflowPass = process.env.AIRFLOW_PASSWORD || 'admin';
const composeFile = process.env.TACTIX_COMPOSE_FILE || 'compose.yml';

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

    const metadbStatus = String(health?.metadatabase?.status || '').toLowerCase();
    if (metadbStatus !== 'healthy') {
      throw new Error(`Metadatabase health check failed: ${metadbStatus || 'unknown'}`);
    }

    const connValue = execSync(
      `docker compose -f ${composeFile} exec -T airflow-webserver airflow config get-value database sql_alchemy_conn`,
      { encoding: 'utf8' },
    );

    if (!connValue.toLowerCase().includes('postgres')) {
      throw new Error(`Expected Postgres sql_alchemy_conn, got: ${connValue.trim()}`);
    }

    console.log('CI check ok');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
})();
