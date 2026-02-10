const path = require('path');
const {
  startBackend,
  waitForHealth,
  runPipeline,
} = require('./helpers/backend_canonical_helpers');

const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const BACKEND_RUNNING = process.env.TACTIX_BACKEND_RUNNING === '1';
const BACKEND_PORT = process.env.TACTIX_BACKEND_PORT || '8010';
const API_BASE =
  process.env.TACTIX_API_BASE || `http://localhost:${BACKEND_PORT}`;
const API_TOKEN = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const TEST_USER = (
  process.env.TACTIX_TEST_CHESSCOM_USER || 'groborger'
).toLowerCase();
const DB_PATH =
  process.env.TACTIX_DUCKDB_PATH ||
  path.resolve(ROOT_DIR, 'tmp-logs', 'feature_remove_initiative.duckdb');
const RUN_DATE = '2026-02-01';
const FIXTURE_NAME = 'chesscom_bullet_mate_hanging_2026_02_01.pgn';

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function assertNoInitiative(label, motifCounts) {
  if (!motifCounts || typeof motifCounts !== 'object') return;
  assert(
    !Object.prototype.hasOwnProperty.call(motifCounts, 'initiative'),
    `Initiative motif still present in ${label}`,
  );
}

async function fetchDashboard() {
  const url = new URL(`${API_BASE}/api/dashboard`);
  url.searchParams.set('source', 'chesscom');
  url.searchParams.set('time_control', 'bullet');
  url.searchParams.set('start_date', RUN_DATE);
  url.searchParams.set('end_date', RUN_DATE);
  const response = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${API_TOKEN}` },
  });
  if (!response.ok) {
    throw new Error(`Dashboard fetch failed: ${response.status}`);
  }
  return response.json();
}

async function fetchPracticeQueue() {
  const url = new URL(`${API_BASE}/api/practice/queue`);
  url.searchParams.set('source', 'chesscom');
  url.searchParams.set('include_failed_attempt', 'false');
  url.searchParams.set('limit', '10');
  const response = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${API_TOKEN}` },
  });
  if (!response.ok) {
    throw new Error(`Practice queue fetch failed: ${response.status}`);
  }
  return response.json();
}

async function fetchMotifStats() {
  const url = new URL(`${API_BASE}/api/stats/motifs`);
  url.searchParams.set('source', 'all');
  const response = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${API_TOKEN}` },
  });
  if (!response.ok) {
    throw new Error(`Motif stats fetch failed: ${response.status}`);
  }
  return response.json();
}

function assertNoInitiativeMotifs(rows, label) {
  if (!Array.isArray(rows)) return;
  rows.forEach((row) => {
    if (!row || typeof row !== 'object') return;
    if ('motif' in row) {
      assert(row.motif !== 'initiative', `Initiative motif still in ${label}`);
    }
  });
}

(async () => {
  let backend = null;
  try {
    if (!BACKEND_RUNNING) {
      backend = await startBackend({
        rootDir: ROOT_DIR,
        backendCmd: BACKEND_CMD,
        backendPort: BACKEND_PORT,
        duckdbPath: DB_PATH,
        env: {
          TACTIX_API_TOKEN: API_TOKEN,
          TACTIX_SOURCE: 'chesscom',
          TACTIX_USER: TEST_USER,
          TACTIX_CHESSCOM_PROFILE: 'bullet',
          TACTIX_CHESSCOM_USE_FIXTURE: '1',
          TACTIX_USE_FIXTURE: '1',
          CHESSCOM_USERNAME: TEST_USER,
          CHESSCOM_USER: TEST_USER,
        },
      });
    }

    await waitForHealth({ apiBase: API_BASE, apiToken: API_TOKEN });

    const pipelineResult = await runPipeline({
      apiBase: API_BASE,
      apiToken: API_TOKEN,
      source: 'chesscom',
      profile: 'bullet',
      userId: TEST_USER,
      startDate: RUN_DATE,
      endDate: RUN_DATE,
      useFixture: true,
      fixtureName: FIXTURE_NAME,
      resetDb: true,
    });

    assertNoInitiative('pipeline motif_counts', pipelineResult?.motif_counts);

    const dashboard = await fetchDashboard();
    assertNoInitiativeMotifs(dashboard.tactics || [], 'dashboard tactics');
    assertNoInitiativeMotifs(
      dashboard.practice_queue || [],
      'dashboard practice queue',
    );

    const practicePayload = await fetchPracticeQueue();
    assertNoInitiativeMotifs(practicePayload.items || [], 'practice queue');

    const motifStats = await fetchMotifStats();
    assertNoInitiativeMotifs(motifStats.motifs || [], 'motif stats');

    console.log('Remove initiative integration check ok');
  } catch (err) {
    console.error('Remove initiative integration check failed:', err);
    process.exit(1);
  } finally {
    if (backend && backend.pid) {
      backend.kill('SIGTERM');
    }
  }
})();
