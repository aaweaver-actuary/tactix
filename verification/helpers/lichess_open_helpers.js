const LICHESS_ANALYSIS_PREFIX = 'https://lichess.org/analysis/pgn/';

const installLichessSpy = async (page) => {
  await page.evaluate(() => {
    window.__lastLichessUrl = null;
    window.__lastOpenArgs = null;
    window.__openCallCount = 0;
    window.open = (url) => {
      window.__openCallCount += 1;
      window.__lastOpenArgs = url || null;
      if (url && url !== 'about:blank') {
        window.__lastLichessUrl = url;
      }
      return {
        close() {},
        opener: null,
        location: {
          set href(nextUrl) {
            if (nextUrl) window.__lastLichessUrl = nextUrl;
          },
        },
      };
    };
  });
};

const resetLichessSpy = async (page) => {
  await page.evaluate(() => {
    window.__lastLichessUrl = null;
    window.__lastOpenArgs = null;
    window.__openCallCount = 0;
  });
};

const getLichessSpyState = async (page) => {
  return page.evaluate(() => ({
    url: window.__lastLichessUrl || '',
    openCount: window.__openCallCount || 0,
    lastOpenArgs: window.__lastOpenArgs || '',
  }));
};

const waitForLichessUrl = async (page, timeoutMs = 15000) => {
  await page.waitForFunction(() => Boolean(window.__lastLichessUrl), {
    timeout: timeoutMs,
  });
  return page.evaluate(() => window.__lastLichessUrl || '');
};

const assertLichessAnalysisUrl = (url, label = 'Lichess URL') => {
  if (!url.startsWith(LICHESS_ANALYSIS_PREFIX)) {
    throw new Error(`Unexpected ${label}: ${url}`);
  }
  if (!url.includes('?color=')) {
    throw new Error(`Missing color param for ${label}: ${url}`);
  }
  if (!url.includes('#')) {
    throw new Error(`Missing move anchor for ${label}: ${url}`);
  }
};

module.exports = {
  LICHESS_ANALYSIS_PREFIX,
  installLichessSpy,
  resetLichessSpy,
  getLichessSpyState,
  waitForLichessUrl,
  assertLichessAnalysisUrl,
};
