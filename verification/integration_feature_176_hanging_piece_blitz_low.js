const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const GAME_ID =
  process.env.TACTIX_HANGING_PIECE_GAME_ID || 'blitz-hanging-piece-low';
const MAX_SEVERITY = process.env.TACTIX_HANGING_PIECE_MAX_SEVERITY
  ? Number(process.env.TACTIX_HANGING_PIECE_MAX_SEVERITY)
  : 1.0;

async function fetchDashboard() {
  const url = `${apiBase}/api/dashboard?source=chesscom&motif=hanging_piece`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (!res.ok) {
    throw new Error(`Dashboard fetch failed: ${res.status}`);
  }
  return res.json();
}

(async () => {
  try {
    const data = await fetchDashboard();
    const tactics = Array.isArray(data?.tactics) ? data.tactics : [];
    const row = tactics.find((item) => {
      if (item.motif !== 'hanging_piece') return false;
      if (item.game_id !== GAME_ID) return false;
      const severity = Number(item.severity);
      if (Number.isNaN(severity)) return false;
      return severity <= MAX_SEVERITY;
    });
    if (!row) {
      throw new Error('Expected hanging piece tactic with low severity');
    }
    if (!row.best_uci || typeof row.best_uci !== 'string') {
      throw new Error('Expected best_uci to be persisted for hanging piece');
    }
    if (!row.explanation || !String(row.explanation).includes('Best line')) {
      throw new Error('Expected explanation to include Best line');
    }
    if (!row.position_id) {
      throw new Error('Expected tactic to be linked to a position_id');
    }
    console.log('Feature 176 integration check ok');
  } catch (err) {
    console.error('Feature 176 integration check failed:', err);
    process.exit(1);
  }
})();
