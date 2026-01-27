const baseUrl = process.env.TACTIX_AIRFLOW_URL || 'http://localhost:8080';
const dagId = process.env.TACTIX_DAG_ID || 'daily_game_sync';
const airflowUser = process.env.AIRFLOW_USERNAME || 'admin';
const airflowPass = process.env.AIRFLOW_PASSWORD || 'admin';

async function fetchWithSession(url, options = {}) {
  let res = await fetch(url, options);
  if (res.status !== 403) return res;

  const loginPage = await fetch(`${baseUrl}/login/`);
  const html = await loginPage.text();
  const loginCookie = loginPage.headers.get('set-cookie');
  const csrfMatch = html.match(/name="csrf_token"[^>]*value="([^"]+)"/);
  const csrfToken = csrfMatch ? csrfMatch[1] : null;
  if (!csrfToken) {
    throw new Error('CSRF token not found on Airflow login page');
  }

  const formBody = new URLSearchParams({
    username: airflowUser,
    password: airflowPass,
    csrf_token: csrfToken,
  });

  const loginRes = await fetch(`${baseUrl}/login/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      ...(loginCookie ? { Cookie: loginCookie.split(';')[0] } : {}),
    },
    body: formBody,
    redirect: 'manual',
  });

  const setCookie = loginRes.headers.get('set-cookie') || loginCookie;
  if (!setCookie) {
    throw new Error('No session cookie returned from Airflow login');
  }
  const sessionCookie = setCookie.split(';')[0];

  res = await fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Cookie: sessionCookie,
      'X-CSRFToken': csrfToken,
      Referer: `${baseUrl}/login/`,
    },
  });
  return res;
}

async function fetchJson(url) {
  const res = await fetchWithSession(url);
  if (!res.ok) {
    throw new Error(`Request failed: ${url} (${res.status})`);
  }
  return res.json();
}

function normalizeSchedule(scheduleInterval) {
  if (!scheduleInterval) return '';
  if (typeof scheduleInterval === 'string') return scheduleInterval;
  if (scheduleInterval.value) return scheduleInterval.value;
  if (scheduleInterval.expression) return scheduleInterval.expression;
  return JSON.stringify(scheduleInterval);
}

(async () => {
  const dagInfo = await fetchJson(`${baseUrl}/api/v1/dags/${dagId}`);
  const scheduleValue = normalizeSchedule(dagInfo.schedule_interval);
  const hourlyValues = new Set(['@hourly', '0 * * * *', '0 */1 * * *']);
  if (!hourlyValues.has(scheduleValue)) {
    throw new Error(`Expected hourly schedule, got: ${scheduleValue}`);
  }

  const tasks = await fetchJson(`${baseUrl}/api/v1/dags/${dagId}/tasks`);
  const taskIds = new Set((tasks.tasks || []).map((task) => task.task_id));
  const requiredTasks = ['run_lichess_pipeline', 'run_chesscom_pipeline'];
  for (const taskId of requiredTasks) {
    if (!taskIds.has(taskId)) {
      throw new Error(`Missing expected task: ${taskId}`);
    }
  }

  console.log('Airflow hourly schedule and task checks passed.');
})();
