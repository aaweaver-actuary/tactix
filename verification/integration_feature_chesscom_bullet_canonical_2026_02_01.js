const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_CMD = path.join(ROOT_DIR, '.venv', 'bin', 'python');
const BACKEND_RUNNING = process.env.TACTIX_BACKEND_RUNNING === '1';
const BACKEND_PORT = process.env.TACTIX_BACKEND_PORT || '8003';
const API_BASE =
  process.env.TACTIX_API_BASE || `http://localhost:${BACKEND_PORT}`;
const API_TOKEN = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const TEST_USER = (
  process.env.TACTIX_TEST_CHESSCOM_USER || 'groborger'
).toLowerCase();
const LOG_PATH =
  process.env.TACTIX_LOG_PATH ||
  path.resolve(
    __dirname,
    '..',
    'tmp-logs',
    'feature_chesscom_bullet_canonical_integration_2026_02_07.json',
  );
const DB_PATH =
  process.env.TACTIX_DUCKDB_PATH ||
  path.resolve(
    ROOT_DIR,
    'tmp-logs',
    'feature_chesscom_bullet_canonical_integration_2026_02_07.duckdb',
  );

function startBackend() {
  return new Promise((resolve, reject) => {
    fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
    if (fs.existsSync(DB_PATH)) {
      fs.unlinkSync(DB_PATH);
    }
    const proc = spawn(
      BACKEND_CMD,
      [
        '-m',
        'uvicorn',
        'tactix.api:app',
        '--host',
        '0.0.0.0',
        '--port',
        BACKEND_PORT,
      ],
      {
        cwd: ROOT_DIR,
        env: {
          ...process.env,
          TACTIX_API_TOKEN: API_TOKEN,
          TACTIX_DUCKDB_PATH: DB_PATH,
          TACTIX_SOURCE: 'chesscom',
          TACTIX_USER: TEST_USER,
          TACTIX_CHESSCOM_PROFILE: 'bullet',
          TACTIX_CHESSCOM_USE_FIXTURE: '1',
          TACTIX_USE_FIXTURE: '1',
          CHESSCOM_USERNAME: TEST_USER,
          CHESSCOM_USER: TEST_USER,
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

function requireValue(value, label) {
  if (value === null || value === undefined || value === '') {
    throw new Error(`Expected ${label} to be present`);
  }
}

function requireCount(value, expected, label) {
  if (value !== expected) {
    throw new Error(`Expected ${label} to be ${expected}, got ${value}`);
  }
}

function ratingDelta(metadata) {
  const white = (metadata.white_player || '').toLowerCase();
  const black = (metadata.black_player || '').toLowerCase();
  const whiteElo = Number(metadata.white_elo || 0);
  const blackElo = Number(metadata.black_elo || 0);
  if (white === TEST_USER) {
    return blackElo - whiteElo;
  }
  if (black === TEST_USER) {
    return whiteElo - blackElo;
  }
  throw new Error('User not found in game metadata');
}

function pieceAtSquare(fen, square) {
  const placement = String(fen || '').split(' ')[0] || '';
  const file = square?.[0];
  const rank = Number(square?.[1]);
  const files = 'abcdefgh';
  if (!placement || !file || Number.isNaN(rank)) {
    return null;
  }
  const ranks = placement.split('/');
  if (ranks.length !== 8) {
    return null;
  }
  const rankIndex = 8 - rank;
  const fileIndex = files.indexOf(file);
  if (rankIndex < 0 || rankIndex > 7 || fileIndex < 0) {
    return null;
  }
  let cursor = 0;
  for (const ch of ranks[rankIndex]) {
    const spaces = Number(ch);
    if (!Number.isNaN(spaces)) {
      cursor += spaces;
      continue;
    }
    if (cursor === fileIndex) {
      return ch;
    }
    cursor += 1;
  }
  return null;
}

function capturedPieceLabel(fen, bestUci) {
  if (!bestUci || bestUci.length < 4) {
    return null;
  }
  const toSquare = bestUci.slice(2, 4);
  const fromSquare = bestUci.slice(0, 2);
  const piece =
    pieceAtSquare(fen, toSquare) || pieceAtSquare(fen, fromSquare);
  if (!piece) {
    return null;
  }
  const lower = piece.toLowerCase();
  if (lower === 'n') {
    return 'knight';
  }
  if (lower === 'b') {
    return 'bishop';
  }
  return null;
}

async function runPipeline() {
  const url = new URL(`${API_BASE}/api/pipeline/run`);
  url.searchParams.set('source', 'chesscom');
  url.searchParams.set('profile', 'bullet');
  url.searchParams.set('user_id', TEST_USER);
  url.searchParams.set('start_date', '2026-02-01');
  url.searchParams.set('end_date', '2026-02-01');
  url.searchParams.set('use_fixture', 'true');
  url.searchParams.set('fixture_name', 'chesscom_2_bullet_games.pgn');
  url.searchParams.set('reset_db', 'true');

  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: { Authorization: `Bearer ${API_TOKEN}` },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Pipeline run failed: ${response.status} ${body}`);
  }
  return response.json();
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitForHealth(retries = 20, delayMs = 500) {
  const url = new URL(`${API_BASE}/api/health`);
  for (let attempt = 0; attempt < retries; attempt += 1) {
    try {
      const response = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${API_TOKEN}` },
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

async function fetchDashboard() {
  const url = new URL(`${API_BASE}/api/dashboard`);
  url.searchParams.set('source', 'chesscom');
  url.searchParams.set('time_control', 'bullet');
  url.searchParams.set('start_date', '2026-02-01');
  url.searchParams.set('end_date', '2026-02-01');

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

async function fetchGameDetail(gameId) {
  const url = new URL(`${API_BASE}/api/games/${gameId}`);
  url.searchParams.set('source', 'chesscom');

  const response = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${API_TOKEN}` },
  });
  if (!response.ok) {
    throw new Error(`Game detail fetch failed: ${response.status}`);
  }
  return response.json();
}

(async () => {
  let backend = null;
  let runError = null;
  try {
    if (!BACKEND_RUNNING) {
      console.log('Starting backend...');
      backend = await startBackend();
    }
    await waitForHealth();

    const payload = await runPipeline();

    const dashboard = await fetchDashboard();
    const recentGames = dashboard.recent_games || [];
    requireCount(recentGames.length, 2, 'recent games count');

    const wins = recentGames.filter((row) => row.result === 'win');
    const losses = recentGames.filter((row) => row.result === 'loss');
    requireCount(wins.length, 1, 'win count');
    requireCount(losses.length, 1, 'loss count');

    const winGameId = wins[0]?.game_id;
    const lossGameId = losses[0]?.game_id;
    requireValue(winGameId, 'win game_id');
    requireValue(lossGameId, 'loss game_id');

    const winDetail = await fetchGameDetail(winGameId);
    const lossDetail = await fetchGameDetail(lossGameId);
    const winDelta = ratingDelta(winDetail.metadata || {});
    const lossDelta = ratingDelta(lossDetail.metadata || {});

    if (!(lossDelta > 50)) {
      throw new Error(`Expected loss rating delta > 50, got ${lossDelta}`);
    }
    if (!(winDelta <= 50)) {
      throw new Error(`Expected win rating delta <= 50, got ${winDelta}`);
    }

    const practicePayload = await fetchPracticeQueue();
    const items = practicePayload.items || [];
    if (items.length < 2) {
      throw new Error(
        `Expected at least 2 practice items, got ${items.length}`,
      );
    }

    const lossItems = items.filter((item) => item.game_id === lossGameId);
    if (lossItems.length < 2) {
      throw new Error('Expected practice queue items to reference loss game');
    }

    const positionIds = new Set();
    for (const item of lossItems) {
      requireValue(item.position_id, 'practice position_id');
      requireValue(item.fen, 'practice FEN');
      positionIds.add(item.position_id);
    }

    if (positionIds.size < 2) {
      throw new Error('Expected at least two unique practice positions');
    }

    const labels = new Set();
    const canonicalItems = [];
    for (const item of lossItems) {
      const label = capturedPieceLabel(item.fen, item.best_uci);
      if (label) {
        labels.add(label);
        canonicalItems.push({ ...item, label });
      }
    }
    if (!labels.has('knight') || !labels.has('bishop')) {
      throw new Error('Expected hanging knight and bishop tactics');
    }
    for (const item of canonicalItems) {
      requireValue(item.position_uci, 'practice position_uci');
      requireValue(item.best_uci, 'practice best_uci');
      if (String(item.position_uci).toLowerCase() === String(item.best_uci).toLowerCase()) {
        throw new Error('Expected pre-blunder position (user move differs from best)');
      }
    }

    const queueByTacticId = new Map(
      lossItems.map((item) => [item.tactic_id, item]),
    );
    for (const item of lossItems) {
      requireValue(queueByTacticId.get(item.tactic_id)?.fen, 'practice FEN');
    }

    fs.mkdirSync(path.dirname(LOG_PATH), { recursive: true });
    fs.writeFileSync(
      LOG_PATH,
      JSON.stringify(
        {
          pipeline: payload,
          recent_games: recentGames,
          win_delta: winDelta,
          loss_delta: lossDelta,
          practice_queue: lossItems,
        },
        null,
        2,
      ),
    );

    console.log(
      'Integration check ok: chess.com bullet canonical scenario verified',
    );
  } catch (err) {
    console.error(err);
    runError = err;
    process.exitCode = 1;
  } finally {
    if (backend) backend.kill();
  }
  if (runError) {
    return;
  }
})();
