process.env.TACTIX_DISCOVERED_ATTACK_GAME_ID =
  process.env.TACTIX_DISCOVERED_ATTACK_GAME_ID || '6677008894';

require('./integration_feature_152_discovered_attack_classical_low');const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const EXPECTED_GAME_ID =
  process.env.TACTIX_DISCOVERED_ATTACK_GAME_ID || '6677008894';

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
    const row = tactics.find(
      (item) =>
        item.motif === 'discovered_attack' &&
        item.game_id === EXPECTED_GAME_ID &&
        Number(item.severity) <= 1.0,
    );    if (!row) {
      throw new Error(
        'Expected discovered attack tactic with low severity (<= 1.0)',
      );
    }
    if (!row.best_uci || typeof row.best_uci !== 'string') {
      throw new Error('Expected best_uci to be persisted for discovered attack');
    }
    if (!row.explanation || !String(row.explanation).includes('Best line')) {
      throw new Error('Expected explanation to include Best line');
    }
    if (!row.position_id) {
      throw new Error('Expected tactic to be linked to a position_id');
    }
    console.log('Feature 154 integration check ok');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
})();
const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

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
    const row = tactics.find(
      (item) =>
        item.motif === 'discovered_attack' &&
        item.game_id === '6677008894' &&
        Number(item.severity) <= 1.0,    if (!row) {
      throw new Error('Expected discovered attack tactic with low severity (<= 1.0)');
    }
    if (!row.best_uci || typeof row.best_uci !== 'string') {
      throw new Error('Expected best_uci to be persisted for discovered attack');
    }
    if (!row.explanation || !String(row.explanation).includes('Best line')) {
      throw new Error('Expected explanation to include Best line');
    }
    if (!row.position_id) {
      throw new Error('Expected tactic to be linked to a position_id');
    }
    console.log('Feature 154 integration check ok');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
})();
