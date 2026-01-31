const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

async function fetch_dashboard__payload() {
  const res = await fetch(`${apiBase}/api/dashboard?source=chesscom&motif=pin`, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (!res.ok) {
    throw new Error(`Dashboard fetch failed: ${res.status}`);
  }
  return res.json();
}

(async () => {
  try {
    const data = await fetch_dashboard__payload();
    const tactics = Array.isArray(data?.tactics) ? data.tactics : [];
    const row = tactics.find(
      (item) => item.motif === 'pin' && item.result === 'failed_attempt',
    );
    if (!row) {
      throw new Error('Expected pin tactic with failed_attempt outcome');
    }
    if (!row.position_id) {
      throw new Error('Expected failed_attempt pin tactic to have position_id');
    }
    console.log('Feature 220 integration check ok');
  } catch (err) {
    console.error('Feature 220 integration check failed:', err);
    process.exit(1);
  }
})();
