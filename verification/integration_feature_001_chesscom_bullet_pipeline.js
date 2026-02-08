const API_BASE = process.env.TACTIX_API_BASE || 'http://localhost:8000';
const API_TOKEN = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const TEST_USER = process.env.TACTIX_TEST_CHESSCOM_USER || 'groborger';
const DB_NAME = 'tactix_feature_001_chesscom_bullet_combined';

async function runPipeline() {
  const url = new URL(`${API_BASE}/api/pipeline/run`);
  url.searchParams.set('source', 'chesscom');
  url.searchParams.set('profile', 'bullet');
  url.searchParams.set('user_id', TEST_USER);
  url.searchParams.set('start_date', '2026-02-01');
  url.searchParams.set('end_date', '2026-02-01');
  url.searchParams.set('use_fixture', 'true');
  url.searchParams.set(
    'fixture_name',
    'chesscom_bullet_mate_hanging_2026_02_01.pgn',
  );
  url.searchParams.set('db_name', DB_NAME);
  url.searchParams.set('reset_db', 'true');

  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: { Authorization: `Bearer ${API_TOKEN}` },
  });
  if (!response.ok) {
    throw new Error(`Pipeline run failed: ${response.status}`);
  }
  return response.json();
}

async function fetchDashboardSummary() {
  const url = new URL(`${API_BASE}/api/dashboard/summary`);
  url.searchParams.set('source', 'chesscom');
  url.searchParams.set('start_date', '2026-02-01');
  url.searchParams.set('end_date', '2026-02-01');
  url.searchParams.set('db_name', DB_NAME);
  const response = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${API_TOKEN}` },
  });
  if (!response.ok) {
    throw new Error(`Dashboard summary fetch failed: ${response.status}`);
  }
  return response.json();
}

function requireCount(value, label) {
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error(`Expected ${label} to be > 0, got ${value}`);
  }
}

(async () => {
  const payload = await runPipeline();
  const result = payload.result || {};
  const counts = payload.counts || {};
  const motifs = payload.motif_counts || {};

  requireCount(result.fetched_games, 'fetched_games');
  requireCount(counts.games, 'games');
  requireCount(counts.positions, 'positions');
  requireCount(counts.user_moves, 'user_moves');
  requireCount(counts.opportunities, 'opportunities');
  requireCount(counts.conversions, 'conversions');
  requireCount(counts.practice_queue, 'practice_queue');

  if (counts.user_moves !== counts.positions) {
    throw new Error(
      `Expected user_moves (${counts.user_moves}) to equal positions (${counts.positions})`,
    );
  }

  requireCount(motifs.hanging_piece, 'motif.hanging_piece');
  requireCount(motifs.mate, 'motif.mate');

  const summaryPayload = await fetchDashboardSummary();
  const summary = summaryPayload.summary || {};

  for (const key of [
    'games',
    'positions',
    'user_moves',
    'opportunities',
    'conversions',
    'practice_queue',
  ]) {
    if (summary[key] !== counts[key]) {
      throw new Error(
        `Expected dashboard summary ${key} (${summary[key]}) to match counts (${counts[key]})`,
      );
    }
  }

  console.log('CI check ok: chess.com bullet pipeline summary verified');
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
