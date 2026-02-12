import { describe, expect, it } from 'vitest';
import * as client from './index';

describe('client index exports', () => {
  it('exposes the client helpers', () => {
    expect(typeof client.fetchDashboard).toBe('function');
    expect(typeof client.fetchGameDetail).toBe('function');
    expect(typeof client.fetchPracticeQueue).toBe('function');
    expect(typeof client.submitPracticeAttempt).toBe('function');
    expect(typeof client.fetchPostgresStatus).toBe('function');
    expect(typeof client.fetchPostgresAnalysis).toBe('function');
    expect(typeof client.fetchPostgresRawPgns).toBe('function');
    expect(typeof client.getJobStreamUrl).toBe('function');
    expect(typeof client.getMetricsStreamUrl).toBe('function');
    expect(typeof client.openEventStream).toBe('function');
  });
});
