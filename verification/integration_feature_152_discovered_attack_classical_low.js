const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const EXPECTED_GAME_ID =
  process.env.TACTIX_DISCOVERED_ATTACK_GAME_ID || '3344556677';
const MIN_SEVERITY = process.env.TACTIX_DISCOVERED_ATTACK_MIN_SEVERITY
  ? Number(process.env.TACTIX_DISCOVERED_ATTACK_MIN_SEVERITY)
  : null;
const MAX_SEVERITY = process.env.TACTIX_DISCOVERED_ATTACK_MAX_SEVERITY
  ? Number(process.env.TACTIX_DISCOVERED_ATTACK_MAX_SEVERITY)
  : MIN_SEVERITY === null
    ? 1.0
    : null;

async function fetchDashboard() {
  const url = `${apiBase}/api/dashboard?source=chesscom&motif=discovered_attack`;
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
      if (item.motif !== 'discovered_attack') return false;
      if (item.game_id !== EXPECTED_GAME_ID) return false;
      const severity = Number(item.severity);
      if (Number.isNaN(severity)) return false;
      if (MIN_SEVERITY !== null && severity < MIN_SEVERITY) return false;
      if (MAX_SEVERITY !== null && severity > MAX_SEVERITY) return false;
      return true;
    });
    if (!row) {
      const expectedText = MIN_SEVERITY === null
        ? 'low severity (<= 1.0)'
        : `high severity (>= ${MIN_SEVERITY})`;
      throw new Error(`Expected discovered attack tactic with ${expectedText}`);
    }
    if (!row.best_uci || typeof row.best_uci !== 'string') {
      throw new Error(
        'Expected best_uci to be persisted for discovered attack',
      );
    }
    if (!row.explanation || !String(row.explanation).includes('Best line')) {
      throw new Error('Expected explanation to include Best line');
    }
    if (!row.position_id) {
      throw new Error('Expected tactic to be linked to a position_id');
    }
    console.log('Feature 152 integration check ok');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
})();
