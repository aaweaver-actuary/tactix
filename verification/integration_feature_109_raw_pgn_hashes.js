const puppeteer = require('../client/node_modules/puppeteer');

const baseUrl = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const sources = ['lichess', 'chesscom'];

async function fetchSummary(page, source) {
  const url = `${baseUrl}/api/raw_pgns/summary?source=${encodeURIComponent(source)}`;
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
  const raw = await page.evaluate(() => document.body.innerText || '');
  const parsed = JSON.parse(raw);
  return parsed.summary || [];
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();

  await page.setExtraHTTPHeaders({ Authorization: `Bearer ${apiToken}` });

  try {
    for (const source of sources) {
      const summary = await fetchSummary(page, source);
      if (!Array.isArray(summary)) {
        throw new Error(`Expected summary array for ${source}`);
      }
      for (const row of summary) {
        const total = Number(row.total || 0);
        const hashed = Number(row.hashed || 0);
        const missing = Number(row.missing || 0);
        if (total !== hashed || missing !== 0) {
          throw new Error(
            `Hash count mismatch for ${source}: total=${total} hashed=${hashed} missing=${missing}`,
          );
        }
      }
    }
  } catch (err) {
    console.error('Feature 109 integration check failed:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
