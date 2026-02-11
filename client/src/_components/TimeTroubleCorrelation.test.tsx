import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import TimeTroubleCorrelation from './TimeTroubleCorrelation';

const formatCorrelation = (value: number | null) => {
  if (value === null || Number.isNaN(value)) return '--';
  const rounded = value.toFixed(2);
  return value > 0 ? `+${rounded}` : rounded;
};

const formatRate = (value: number | null) => {
  if (value === null || Number.isNaN(value)) return '--';
  return `${(value * 100).toFixed(1)}%`;
};

describe('TimeTroubleCorrelation', () => {
  it('returns null when there is no data', () => {
    const { container } = render(
      <TimeTroubleCorrelation data={[]} columns={[]} />,
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders correlation rows with explanation', () => {
    const data = [
      {
        metric_type: 'time_trouble_correlation',
        time_control: '300+0',
        found_rate: 0.5,
        miss_rate: 0.25,
        total: 12,
      },
      {
        metric_type: 'time_trouble_correlation',
        time_control: '600+5',
        found_rate: -0.75,
        miss_rate: 0.4,
        total: 8,
      },
    ] as any;

    const columns = [
      { header: 'Time control', accessorKey: 'time_control' },
      {
        header: 'Correlation',
        accessorFn: (row: any) => row.found_rate ?? null,
        cell: (info: any) => formatCorrelation(info.getValue()),
      },
      {
        header: 'Time trouble rate',
        accessorFn: (row: any) => row.miss_rate ?? null,
        cell: (info: any) => formatRate(info.getValue()),
      },
      { header: 'Samples', accessorKey: 'total' },
    ];

    render(<TimeTroubleCorrelation data={data} columns={columns as any} />);

    expect(screen.getByText('300+0')).toBeInTheDocument();
    expect(screen.getByText('600+5')).toBeInTheDocument();
    expect(screen.getByText('+0.50')).toBeInTheDocument();
    expect(screen.getByText('-0.75')).toBeInTheDocument();
    expect(screen.getByText('25.0%')).toBeInTheDocument();
    expect(screen.getByText('40.0%')).toBeInTheDocument();
  });
});
