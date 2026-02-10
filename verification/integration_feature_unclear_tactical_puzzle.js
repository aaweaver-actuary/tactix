const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const source = process.env.TACTIX_SOURCE || 'chesscom';

async function fetchPracticeQueue() {
  const url = `${apiBase}/api/practice/queue?source=${source}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (!res.ok) {
    throw new Error(`Practice queue fetch failed: ${res.status}`);
  }
  return res.json();
}

(async () => {
  try {
    const data = await fetchPracticeQueue();
    const items = Array.isArray(data?.items) ? data.items : [];
    if (!items.length) {
      throw new Error('Expected practice queue items to verify best_uci.');
    }
    const missing = items.filter(
      (item) => !String(item.best_uci || '').trim(),
    );
    if (missing.length) {
      throw new Error(
        `Expected practice queue to exclude items without best_uci (missing: ${missing.length}).`,
      );
    }
    console.log('Feature unclear tactical puzzle integration check ok');
  } catch (err) {
    console.error('Feature unclear tactical puzzle integration check failed:', err);
    process.exit(1);
  }
})();
