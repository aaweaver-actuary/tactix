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

    fireEvent.click(sortButton);
    expect(sortButton).toHaveAttribute('aria-label', 'Sorted descending');

    expect(screen.getByText('Page 1 of 2')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByText('Page 2 of 2')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Prev' }));
    expect(screen.getByText('Page 1 of 2')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Rows per page'), {
      target: { value: '10' },
    });
    expect(screen.queryByText('Page 1 of 1')).not.toBeInTheDocument();
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

  it('ignores row clicks when no handler is provided', () => {
    render(
      <BaseTable
        data={sampleRows.slice(0, 1)}
        columns={columns}
        rowTestId={rowTestId}
        enablePagination={false}
      />,
    );

    fireEvent.click(screen.getByTestId('row-1'));
    expect(screen.getByTestId('row-1')).toBeInTheDocument();
  });

  it('handles grouped headers and cell clicks without double firing', () => {
    const onRowClick = vi.fn();
    const groupedColumns: ColumnDef<SampleRow>[] = [
      {
        header: 'Group',
        columns: [
          { header: 'Name', accessorKey: 'name' },
          { header: 'Value', accessorKey: 'value' },
        ],
      },
    ];

    render(
      <BaseTable
        data={sampleRows.slice(0, 1)}
        columns={groupedColumns}
        onRowClick={onRowClick}
        rowTestId={rowTestId}
        enablePagination={false}
      />,
    );

    fireEvent.click(screen.getByText('Alpha'));
    expect(onRowClick).toHaveBeenCalledTimes(1);
  });

  it('renders placeholder headers for mixed depth groups', () => {
    const mixedColumns: ColumnDef<SampleRow>[] = [
      {
        header: 'Group',
        columns: [{ header: 'Name', accessorKey: 'name' }],
      },
      { header: 'Value', accessorKey: 'value' },
    ];

    render(
      <BaseTable
        data={sampleRows.slice(0, 1)}
        columns={mixedColumns}
        enablePagination={false}
      />,
    );

    const headers = screen.getAllByRole('columnheader');
    const hasPlaceholder = headers.some(
      (header) => (header.textContent ?? '').trim() === '',
    );
    expect(hasPlaceholder).toBe(true);
  });
});
