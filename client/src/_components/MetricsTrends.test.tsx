import { renderToStaticMarkup } from 'react-dom/server';
import MetricsTrends from './MetricsTrends';

const formatPercent = (value: number | null) =>
  value === null || Number.isNaN(value) ? '--' : `${(value * 100).toFixed(1)}%`;

describe('MetricsTrends', () => {
  it('returns empty markup when no valid trend data exists', () => {
    const html = renderToStaticMarkup(<MetricsTrends data={[]} columns={[]} />);

    expect(html).toBe('');
  });

  it('renders trend rows and formats percentages', () => {
    const data = [
      {
        motif: 'alpha',
        seven: {
          found_rate: 0.345,
          trend_date: '2023-01-05',
        },
        thirty: {
          found_rate: null,
          trend_date: '2023-01-03',
        },
      },
      {
        motif: 'beta',
        thirty: {
          found_rate: 0.5,
          trend_date: '2023-02-01',
        },
      },
    ] as any[];

    const columns = [
      { header: 'Motif', accessorKey: 'motif' },
      {
        header: '7g found',
        accessorFn: (row: any) => row.seven?.found_rate ?? null,
        cell: (info: any) => formatPercent(info.getValue()),
      },
      {
        header: '30g found',
        accessorFn: (row: any) => row.thirty?.found_rate ?? null,
        cell: (info: any) => formatPercent(info.getValue()),
      },
      {
        header: 'Last update',
        accessorFn: (row: any) =>
          row.seven?.trend_date || row.thirty?.trend_date || '--',
      },
    ];

    const html = renderToStaticMarkup(
      <MetricsTrends data={data as any} columns={columns as any} />,
    );

    expect(html).toContain('Motif');
    expect(html).toContain('7g found');
    expect(html).toContain('30g found');
    expect(html).toContain('Last update');

    expect(html).toContain('alpha');
    expect(html).toContain('beta');
    expect(html).toContain('34.5%');
    expect(html).toContain('--');
    expect(html).toContain('50.0%');

    expect(html).toContain('2023-01-05');
    expect(html).toContain('2023-02-01');
  });
});
