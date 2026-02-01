const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

async function fetch_dashboard__payload() {
  const res = await fetch(
    `${apiBase}/api/dashboard?source=chesscom&motif=discovered_check`,
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
      (item) => item.motif === 'discovered_check' && item.result === 'unclear',
    );
    if (!row) {
      throw new Error(
        'Expected discovered check tactic with unclear outcome',
      );
    }
    if (!row.position_id) {
      throw new Error(
        'Expected unclear discovered check tactic to have position_id',
      );
    }
    console.log('Feature 231 integration check ok');
  } catch (err) {
    console.error('Feature 231 integration check failed:', err);
    process.exit(1);
  }
})();
