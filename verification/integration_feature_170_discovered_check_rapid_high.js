const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const GAME_ID =
  process.env.TACTIX_DISCOVERED_CHECK_GAME_ID ||
  'rapid-discovered-check-high';
const MIN_SEVERITY = process.env.TACTIX_DISCOVERED_CHECK_MIN_SEVERITY
  ? Number(process.env.TACTIX_DISCOVERED_CHECK_MIN_SEVERITY)
  : 1.5;

async function fetchDashboard() {
  const url = `${apiBase}/api/dashboard?source=chesscom&motif=discovered_check`;
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
    const row = tactics.find(
      (item) =>
        item.motif === 'discovered_check' &&
        item.game_id === GAME_ID &&
        Number(item.severity) >= MIN_SEVERITY,
    );
    if (!row) {
      throw new Error('Expected discovered check tactic with high severity');
    }
    if (!row.best_uci || typeof row.best_uci !== 'string') {
      throw new Error('Expected best_uci to be persisted for discovered check');
    }
    if (!row.explanation || !String(row.explanation).includes('Best line')) {
      throw new Error('Expected explanation to include Best line');
    }
    if (!row.position_id) {
      throw new Error('Expected tactic to be linked to a position_id');
    }
    console.log('Feature 170 integration check ok');
  } catch (err) {
    console.error('Feature 170 integration check failed:', err);
    process.exit(1);
  }
})();
