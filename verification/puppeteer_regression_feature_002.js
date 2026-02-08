const { runDashboardRegression } = require('./helpers/run_dashboard_regression');

const targetUrl = process.env.TACTIX_UI_URL || 'http://localhost:5173/';
const screenshotName =
  process.env.TACTIX_SCREENSHOT_NAME ||
  'regression-002-chesscom-blitz-2026-02-01.png';

runDashboardRegression({
  targetUrl,
  screenshotName,
  sourceValue: 'chesscom',
  profileTestId: 'filter-chesscom-profile',
  profileValue: 'blitz',
  failureMessage: 'Feature 002 regression verification failed',
});
