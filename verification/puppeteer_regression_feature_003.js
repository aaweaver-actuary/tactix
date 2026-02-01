const { runDashboardRegression } = require('./helpers/run_dashboard_regression');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'regression-003-lichess-since-2026-02-01.png';

runDashboardRegression({
  targetUrl,
  screenshotName,
  sourceValue: 'lichess',
  profileTestId: 'filter-lichess-profile',
  profileValue: 'blitz',
  failureMessage: 'Feature 003 regression verification failed',
});
