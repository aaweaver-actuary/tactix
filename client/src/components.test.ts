import { describe, expect, it } from 'vitest';
import * as components from './components';

describe('components barrel exports', () => {
  it('exposes the shared components', () => {
    expect(typeof components.Hero).toBe('function');
    expect(typeof components.Badge).toBe('function');
    expect(typeof components.MetricsGrid).toBe('function');
    expect(typeof components.PositionsList).toBe('function');
    expect(typeof components.MotifTrendsCard).toBe('function');
    expect(typeof components.TimeTroubleCorrelationCard).toBe('function');
    expect(typeof components.RecentGamesModal).toBe('function');
    expect(typeof components.RecentTacticsModal).toBe('function');
    expect(typeof components.ErrorCard).toBe('function');
    expect(typeof components.FiltersCard).toBe('function');
    expect(typeof components.MetricsSummaryCard).toBe('function');
    expect(typeof components.DatabaseModal).toBe('function');
    expect(typeof components.JobProgressCard).toBe('function');
    expect(typeof components.GameDetailModal).toBe('function');
    expect(typeof components.ChessboardModal).toBe('function');
    expect(typeof components.ActionButton).toBe('function');
    expect(typeof components.FloatingActionButton).toBe('function');
    expect(typeof components.TacticsActionButtons).toBe('function');
  });
});
