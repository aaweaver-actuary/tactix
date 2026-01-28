import { renderToStaticMarkup } from 'react-dom/server';
import MetricsTrends from './MetricsTrends';

describe('MetricsTrends', () => {
  it('returns empty markup when no valid trend data exists', () => {
    const metricsData = [
      {
        motif: 'alpha',
        metric_type: 'count',
        trend_date: '2023-01-01',
        window_days: 7,
        found_rate: 0.1,
      },
      {
        motif: 'beta',
        metric_type: 'trend',
        trend_date: null,
        window_days: 30,
        found_rate: 0.2,
      },
    ] as any[];

    const html = renderToStaticMarkup(
      <MetricsTrends metricsData={metricsData} />,
    );

    expect(html).toBe('');
  });

  it('renders latest trends per motif and formats percentages', () => {
    const metricsData = [
      {
        motif: 'alpha',
        metric_type: 'trend',
        trend_date: '2023-01-01',
        window_days: 7,
        found_rate: 0.1234,
      },
      {
        motif: 'alpha',
        metric_type: 'trend',
        trend_date: '2023-01-05',
        window_days: 7,
        found_rate: 0.345,
      },
      {
        motif: 'alpha',
        metric_type: 'trend',
        trend_date: '2023-01-03',
        window_days: 30,
        found_rate: null,
      },
      {
        motif: 'beta',
        metric_type: 'trend',
        trend_date: '2023-02-01',
        window_days: 30,
        found_rate: 0.5,
      },
      {
        motif: 'ignored',
        metric_type: 'count',
        trend_date: '2023-02-02',
        window_days: 7,
        found_rate: 0.9,
      },
    ] as any[];

    const html = renderToStaticMarkup(
      <MetricsTrends metricsData={metricsData} />,
    );

    expect(html).toContain('Motif trends');
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain('data-state="collapsed"');
    expect(html).toContain('Motif');
    expect(html).toContain('7g found');
    expect(html).toContain('30g found');
    expect(html).toContain('Last update');

    expect(html).toContain('alpha');
    expect(html).toContain('beta');
    expect(html).not.toContain('ignored');

    expect(html).toContain('34.5%');
    expect(html).toContain('--');
    expect(html).toContain('50.0%');

    expect(html).toContain('2023-01-05');
    expect(html).toContain('2023-02-01');
  });
});
