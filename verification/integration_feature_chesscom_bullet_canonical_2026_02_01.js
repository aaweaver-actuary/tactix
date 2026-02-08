const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const {
  startBackend,
  waitForHealth,
  runPipeline,
} = require('./helpers/backend_canonical_helpers');

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
const RUN_DATE = '2026-02-01';

const PYTHON_CMD =
  process.env.TACTIX_PYTHON || path.join(ROOT_DIR, '.venv', 'bin', 'python');
const FALLBACK_PYTHON = 'python';

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

function loadDbSnapshot(dbPath) {
  const python = fs.existsSync(PYTHON_CMD) ? PYTHON_CMD : FALLBACK_PYTHON;
  const script = `import json, sys\nimport duckdb\n\npath = sys.argv[1]\nconn = duckdb.connect(path)\ntry:\n    games = conn.execute(\n        """\n        SELECT game_id, user_rating, time_control, played_at\n        FROM games\n        WHERE source = 'chesscom'\n        AND time_control = '120+1'\n        AND CAST(played_at AS DATE) = '${RUN_DATE}'\n        ORDER BY game_id\n        """\n    ).fetchall()\n    queue = conn.execute(\n        """\n        SELECT opportunity_id, game_id, position_id, fen, result, motif\n        FROM practice_queue\n        WHERE source = 'chesscom'\n        ORDER BY opportunity_id\n        """\n    ).fetchall()\nfinally:\n    conn.close()\n\nprint(json.dumps({\n    'games': [\n        {\n            'game_id': row[0],\n            'user_rating': row[1],\n            'time_control': row[2],\n            'played_at': str(row[3]) if row[3] is not None else None,\n        }\n        for row in games\n    ],\n    'practice_queue': [\n        {\n            'opportunity_id': row[0],\n            'game_id': row[1],\n            'position_id': row[2],\n            'fen': row[3],\n            'result': row[4],\n            'motif': row[5],\n        }\n        for row in queue\n    ],\n}))\n`;
  const result = spawnSync(python, ['-c', script, dbPath], {
    encoding: 'utf-8',
  });
  if (result.status !== 0) {
    throw new Error(`DuckDB snapshot failed: ${result.stderr || result.stdout}`);
  }
  return JSON.parse(result.stdout || '{}');
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

    const payload = await runPipeline({
      apiBase: API_BASE,
      apiToken: API_TOKEN,
      source: 'chesscom',
      profile: 'bullet',
      userId: TEST_USER,
      startDate: RUN_DATE,
      endDate: RUN_DATE,
      useFixture: true,
      fixtureName: 'chesscom_2_bullet_games.pgn',
      resetDb: true,
    });

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

    const canonicalItems = lossItems.filter(
      (item) => item.motif === 'hanging_piece' && item.result === 'missed',
    );
    if (canonicalItems.length < 2) {
      throw new Error('Expected at least two missed hanging piece items');
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

    const dbSnapshot = loadDbSnapshot(DB_PATH);
    const dbGames = dbSnapshot.games || [];
    requireCount(dbGames.length, 2, 'db games count');
    const dbGameIds = new Set(dbGames.map((row) => row.game_id));
    if (!dbGameIds.has(winGameId) || !dbGameIds.has(lossGameId)) {
      throw new Error('Expected DB games to match API win/loss game ids');
    }

    const dbQueue = dbSnapshot.practice_queue || [];
    const dbLossQueue = dbQueue.filter((row) => row.game_id === lossGameId);
    if (dbLossQueue.length < 2) {
      throw new Error('Expected DB practice queue items for loss game');
    }
    const dbPositionIds = new Set(dbLossQueue.map((row) => row.position_id));
    for (const item of lossItems) {
      if (!dbPositionIds.has(item.position_id)) {
        throw new Error('Expected API practice items to exist in DB');
      }
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
          db_snapshot: dbSnapshot,
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
