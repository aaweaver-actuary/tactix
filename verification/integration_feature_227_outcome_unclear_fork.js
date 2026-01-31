const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

async function fetchDashboard() {
  const url = `${apiBase}/api/dashboard?source=chesscom&motif=fork`;
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
      (item) => item.motif === 'fork' && item.result === 'unclear',
    );
    if (!row) {
      throw new Error('Expected fork tactic with unclear outcome');
    }
    if (!row.position_id) {
      throw new Error('Expected unclear fork tactic to have position_id');
    }
    console.log('Feature 227 integration check ok');
  } catch (err) {
    console.error('Feature 227 integration check failed:', err);
    process.exit(1);
  }
})();
