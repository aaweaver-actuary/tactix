const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

async function fetch_dashboard__payload() {
  const res = await fetch(
    `${apiBase}/api/dashboard?source=chesscom&motif=hanging_piece`,
    {
      headers: { Authorization: `Bearer ${apiToken}` },
    },
  );
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
      (item) => item.motif === 'hanging_piece' && item.result === 'failed_attempt',
    );
    if (!row) {
      throw new Error(
        'Expected hanging piece tactic with failed_attempt outcome',
      );
    }
    if (!row.position_id) {
      throw new Error(
        'Expected failed_attempt hanging piece tactic to have position_id',
      );
    }
    console.log('Feature 224 integration check ok');
  } catch (err) {
    console.error('Feature 224 integration check failed:', err);
    process.exit(1);
  }
})();
