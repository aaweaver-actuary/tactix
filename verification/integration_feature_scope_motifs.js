const path = require('path');
const {
  startBackend,
  waitForHealth,
  runPipeline,
} = require('./helpers/backend_canonical_helpers');

const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const BACKEND_RUNNING = process.env.TACTIX_BACKEND_RUNNING === '1';
const BACKEND_PORT = process.env.TACTIX_BACKEND_PORT || '8004';
const API_BASE =
  process.env.TACTIX_API_BASE || `http://localhost:${BACKEND_PORT}`;
const API_TOKEN = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const TEST_USER = (
  process.env.TACTIX_TEST_CHESSCOM_USER || 'groborger'
).toLowerCase();
const DB_PATH =
  process.env.TACTIX_DUCKDB_PATH ||
  path.resolve(ROOT_DIR, 'tmp-logs', 'feature_scope_motifs.duckdb');
const RUN_DATE = '2026-02-01';
const FIXTURE_NAME = 'chesscom_bullet_mate_hanging_2026_02_01.pgn';
const ALLOWED_MOTIFS = new Set(['hanging_piece', 'mate']);

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function assertScopedMotifRow(row) {
  const motif = row.motif;
  assert(ALLOWED_MOTIFS.has(motif), `Unexpected motif: ${motif}`);
  if (motif === 'mate') {
    assert(row.mate_type, 'Expected mate_type for mate motif');
  }
}

function assertScopedMotifList(items, label) {
  if (!Array.isArray(items)) return;
  for (const item of items) {
    if (!item || typeof item !== 'object') continue;
    if ('motif' in item) {
      assertScopedMotifRow(item);
    }
  }
  console.log(`Scoped motifs ok for ${label}`);
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

    await runPipeline({
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

    const dashboard = await fetchDashboard();
    assertScopedMotifList(dashboard.tactics || [], 'dashboard tactics');
    assertScopedMotifList(
      dashboard.practice_queue || [],
      'dashboard practice queue',
    );

    const practicePayload = await fetchPracticeQueue();
    assertScopedMotifList(practicePayload.items || [], 'practice queue');

    const motifStats = await fetchMotifStats();
    const motifs = motifStats.motifs || [];
    for (const row of motifs) {
      if (!row || typeof row !== 'object') continue;
      const motif = row.motif;
      if (motif) {
        assert(ALLOWED_MOTIFS.has(motif), `Unexpected stats motif: ${motif}`);
      }
    }

    console.log('Feature scope motifs integration check ok');
  } catch (err) {
    console.error('Feature scope motifs integration check failed:', err);
    process.exit(1);
  } finally {
    if (backend && backend.pid) {
      backend.kill('SIGTERM');
    }
  }
})();
