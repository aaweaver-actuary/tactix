const apiBase = process.env.TACTIX_API_BASE || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';

(async () => {
  const response = await fetch(`${apiBase}/api/postgres/analysis?limit=5`, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (!response.ok) {
    throw new Error(`Postgres analysis endpoint failed: ${response.status}`);
  }
  const payload = await response.json();
  const tactics = Array.isArray(payload.tactics) ? payload.tactics : [];
  const hasRow = tactics.some((row) => row && row.tactic_id);
  if (!hasRow) {
    throw new Error('Expected at least one Postgres analysis row');
  }
  console.log('CI check ok: Postgres analysis rows available');
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
