const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function startBackend({
  rootDir,
  backendCmd,
  backendPort,
  duckdbPath,
  env,
  host = '0.0.0.0',
}) {
  return new Promise((resolve, reject) => {
    if (duckdbPath) {
      fs.mkdirSync(path.dirname(duckdbPath), { recursive: true });
      if (fs.existsSync(duckdbPath)) {
        fs.unlinkSync(duckdbPath);
      }
    }

    const proc = spawn(
      backendCmd,
      ['-m', 'uvicorn', 'tactix.api:app', '--host', host, '--port', backendPort],
      {
        cwd: rootDir,
        env: {
          ...process.env,
          ...(duckdbPath ? { TACTIX_DUCKDB_PATH: duckdbPath } : {}),
          ...(env || {}),
        },
        stdio: ['ignore', 'pipe', 'pipe'],
      },
    );

    const onData = (data) => {
      const text = data.toString();
      if (text.includes('Uvicorn running')) {
        cleanup();
        resolve(proc);
      }
    };

    const onError = (err) => {
      cleanup();
      reject(err);
    };

    function cleanup() {
      proc.stdout.off('data', onData);
      proc.stderr.off('data', onData);
      proc.off('error', onError);
    }

    proc.stdout.on('data', onData);
    proc.stderr.on('data', onData);
    proc.on('error', onError);
  });
}

async function waitForHealth({ apiBase, apiToken, retries = 20, delayMs = 500 }) {
  const url = new URL(`${apiBase}/api/health`);
  for (let attempt = 0; attempt < retries; attempt += 1) {
    try {
      const response = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${apiToken}` },
      });
      if (response.ok) {
        return;
      }
    } catch (err) {
      // ignore until retries exhausted
    }
    await sleep(delayMs);
  }
  throw new Error('Backend health check failed');
}

async function runPipeline({
  apiBase,
  apiToken,
  source,
  profile,
  userId,
  startDate,
  endDate,
  useFixture = true,
  fixtureName,
  resetDb = true,
  retries = 1,
  retryDelayMs = 1000,
}) {
  const url = new URL(`${apiBase}/api/pipeline/run`);
  url.searchParams.set('source', source);
  url.searchParams.set('profile', profile);
  url.searchParams.set('user_id', userId);
  url.searchParams.set('start_date', startDate);
  url.searchParams.set('end_date', endDate);
  url.searchParams.set('use_fixture', String(useFixture));
  if (fixtureName) {
    url.searchParams.set('fixture_name', fixtureName);
  }
  url.searchParams.set('reset_db', String(resetDb));

  for (let attempt = 1; attempt <= retries; attempt += 1) {
    const response = await fetch(url.toString(), {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiToken}` },
    });

    if (response.ok) {
      return response.json();
    }

    const body = await response.text();
    if (attempt === retries) {
      throw new Error(`Pipeline run failed: ${response.status} ${body}`);
    }
    await sleep(retryDelayMs);
  }

  return null;
}

module.exports = { startBackend, waitForHealth, runPipeline };
