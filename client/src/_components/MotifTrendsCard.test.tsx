import { ColumnDef } from '@tanstack/react-table';
import { render, screen } from '@testing-library/react';
import MotifTrendsCard from './MotifTrendsCard';
import type { MetricsTrendsRow } from './MetricsTrends';

const formatPercent = (value: number | null) =>
  value === null || Number.isNaN(value) ? '--' : `${(value * 100).toFixed(1)}%`;

const columns: ColumnDef<MetricsTrendsRow>[] = [
  { header: 'Motif', accessorKey: 'motif' },
  {
    header: '7d',
    accessorFn: (row) => row.seven?.found_rate ?? null,
    cell: (info) => formatPercent(info.getValue() as number | null),
  },
  {
    header: '30d',
    accessorFn: (row) => row.thirty?.found_rate ?? null,
    cell: (info) => formatPercent(info.getValue() as number | null),
  },
];

describe('MotifTrendsCard', () => {
  it('renders a loading state with data-testid values', () => {
    render(<MotifTrendsCard data={null} columns={columns} />);

    expect(screen.getByTestId('motif-trends-card')).toBeInTheDocument();
    expect(screen.getByTestId('motif-trends-table')).toBeInTheDocument();
    expect(screen.getByText(/Loading/i)).toBeInTheDocument();
  });

  it('renders an empty state when no trends are available', () => {
    render(<MotifTrendsCard data={[]} columns={columns} />);

    expect(screen.getByTestId('motif-trends-card')).toBeInTheDocument();
    expect(screen.getByTestId('motif-trends-table')).toBeInTheDocument();
    expect(screen.getByText('No rows to display.')).toBeInTheDocument();
  });

  it('renders labels and values for populated trend data', () => {
    const data: MetricsTrendsRow[] = [
      {
        motif: 'mate',
        seven: { found_rate: 0.7 } as MetricsTrendsRow['seven'],
        thirty: { found_rate: 0.4 } as MetricsTrendsRow['thirty'],
      },
      {
        motif: 'hanging_piece',
        seven: { found_rate: 0.5 } as MetricsTrendsRow['seven'],
      },
    ];

    render(<MotifTrendsCard data={data} columns={columns} />);

    expect(screen.getByText('Motif trends')).toBeInTheDocument();
    expect(screen.getByText('Rolling 7/30 days')).toBeInTheDocument();
    expect(screen.getByText('Motif')).toBeInTheDocument();
    expect(screen.getByText('7d')).toBeInTheDocument();
    expect(screen.getByText('30d')).toBeInTheDocument();
    expect(screen.getByText('mate')).toBeInTheDocument();
    expect(screen.getByText('hanging_piece')).toBeInTheDocument();
    expect(screen.getByText('70.0%')).toBeInTheDocument();
    expect(screen.getByText('40.0%')).toBeInTheDocument();
    expect(screen.getByText('50.0%')).toBeInTheDocument();
    expect(screen.getAllByText('--').length).toBeGreaterThan(0);
  });
});
