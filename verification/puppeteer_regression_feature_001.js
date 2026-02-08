const { runDashboardRegression } = require('./helpers/run_dashboard_regression');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME || 'regression-001-lichess-2026-01-25.png';

runDashboardRegression({
  targetUrl,
  screenshotName,
  sourceValue: 'lichess',
  waitUntil: 'domcontentloaded',
  waitForTable: false,
  failureMessage: 'Feature 001 regression verification failed',
});
