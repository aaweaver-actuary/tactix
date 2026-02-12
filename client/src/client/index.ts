import { fetchDashboard, fetchGameDetail } from './dashboard';
import { fetchPracticeQueue, submitPracticeAttempt } from './practice';
import {
  fetchPostgresStatus,
  fetchPostgresAnalysis,
  fetchPostgresRawPgns,
} from './postgres';
import {
  getJobStreamUrl,
  getMetricsStreamUrl,
  openEventStream,
} from './streams';

const clientExports = {
  fetchDashboard,
  fetchGameDetail,
  fetchPracticeQueue,
  submitPracticeAttempt,
  fetchPostgresStatus,
  fetchPostgresAnalysis,
  fetchPostgresRawPgns,
  getJobStreamUrl,
  getMetricsStreamUrl,
  openEventStream,
};

void clientExports;

export {
  fetchDashboard,
  fetchGameDetail,
  fetchPracticeQueue,
  submitPracticeAttempt,
  fetchPostgresStatus,
  fetchPostgresAnalysis,
  fetchPostgresRawPgns,
  getJobStreamUrl,
  getMetricsStreamUrl,
  openEventStream,
};
