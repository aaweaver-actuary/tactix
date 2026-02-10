import { fireEvent, render, screen } from '@testing-library/react';
import type { ColumnDef } from '@tanstack/react-table';
import { describe, expect, it, vi } from 'vitest';
import BaseTable from './BaseTable';

type SampleRow = {
  id: number;
  name: string;
  value: number;
};

const columns: ColumnDef<SampleRow>[] = [
  { header: 'Name', accessorKey: 'name' },
  { header: 'Value', accessorKey: 'value' },
];

const sampleRows: SampleRow[] = [
  { id: 1, name: 'Alpha', value: 10 },
  { id: 2, name: 'Beta', value: 20 },
  { id: 3, name: 'Gamma', value: 30 },
  { id: 4, name: 'Delta', value: 40 },
  { id: 5, name: 'Epsilon', value: 50 },
  { id: 6, name: 'Zeta', value: 60 },
];

const rowTestId = (row: SampleRow) => `row-${row.id}`;

describe('BaseTable', () => {
  it('renders a loading state when data is null', () => {
    render(<BaseTable data={null} columns={columns} />);

    expect(screen.getByText(/Loading/)).toBeInTheDocument();
  });

  it('renders an empty state when no rows are provided', () => {
    render(<BaseTable data={[]} columns={columns} />);

    expect(screen.getByText('No rows to display.')).toBeInTheDocument();
  });

  it('supports sorting and pagination controls', () => {
    render(
      <BaseTable
        data={sampleRows}
        columns={columns}
        rowTestId={rowTestId}
        initialPageSize={5}
      />,
    );

    const sortButton = screen.getAllByRole('button', {
      name: /not sorted/i,
    })[0];
    fireEvent.click(sortButton);
    expect(sortButton).toHaveAttribute('aria-label', 'Sorted ascending');

    expect(screen.getByText('Page 1 of 2')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByText('Page 2 of 2')).toBeInTheDocument();
    expect(screen.getByTestId('row-6')).toBeInTheDocument();
  });

  it('fires onRowClick when a row is clicked', () => {
    const onRowClick = vi.fn();

    render(
      <BaseTable
        data={sampleRows.slice(0, 2)}
        columns={columns}
        onRowClick={onRowClick}
        rowTestId={rowTestId}
      />,
    );

    fireEvent.click(screen.getByTestId('row-1'));
    expect(onRowClick).toHaveBeenCalledWith(sampleRows[0]);
  });
});
