import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from '@tanstack/react-table';
import { useMemo, useState } from 'react';

const DEFAULT_PAGE_SIZES = [5, 10, 20];
const joinClassNames = (...classes: Array<string | null | undefined>) =>
  classes.filter(Boolean).join(' ');

type BaseTableProps<TData> = {
  data: TData[] | null;
  columns: ColumnDef<TData, unknown>[];
  initialPageSize?: number;
  pageSizeOptions?: number[];
  emptyMessage?: string;
  loadingMessage?: string;
  className?: string;
  tableClassName?: string;
  headerCellClassName?: string;
  cellClassName?: string;
  enablePagination?: boolean;
  onRowClick?: (row: TData) => void;
  rowTestId?: (row: TData, index: number) => string;
};

export default function BaseTable<TData>({
  data,
  columns,
  initialPageSize = DEFAULT_PAGE_SIZES[0],
  pageSizeOptions = DEFAULT_PAGE_SIZES,
  emptyMessage = 'No rows to display.',
  loadingMessage = 'Loading…',
  className,
  tableClassName,
  headerCellClassName,
  cellClassName,
  enablePagination = true,
  onRowClick,
  rowTestId,
}: BaseTableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: initialPageSize,
  });

  const safeData = useMemo(() => data ?? [], [data]);
  const paginationHandler = enablePagination ? setPagination : undefined;
  const table = useReactTable({
    data: safeData,
    columns,
    state: enablePagination ? { sorting, pagination } : { sorting },
    onSortingChange: setSorting,
    onPaginationChange: paginationHandler,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    ...(enablePagination
      ? { getPaginationRowModel: getPaginationRowModel() }
      : {}),
    manualPagination: false,
  });

  const isLoading = data === null;
  const visibleRows = table.getRowModel().rows;
  const pageCount = table.getPageCount();
  const hasRows = visibleRows.length > 0;
  const showPagination = enablePagination && !isLoading && pageCount > 1;
  const wrapperClassName = joinClassNames('space-y-3', className);
  const tableClassNames = joinClassNames('min-w-full text-sm', tableClassName);
  const headerClassNames = joinClassNames(
    'text-left py-2',
    headerCellClassName,
  );
  const cellClassNames = joinClassNames('py-2', cellClassName);
  const handleRowClick = (
    row: TData,
    event: React.MouseEvent<HTMLElement>,
    stopPropagation = false,
  ) => {
    if (!onRowClick) return;
    if (stopPropagation) event.stopPropagation();
    onRowClick(row);
  };

  return (
    <div className={wrapperClassName}>
      <div className="overflow-x-auto">
        <table className={tableClassNames}>
          <thead className="text-sand/60">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  if (header.isPlaceholder) {
                    return <th key={header.id} />;
                  }

                  const canSort = header.column.getCanSort();
                  const sortState = header.column.getIsSorted();
                  const sortLabel =
                    sortState === 'asc'
                      ? 'Sorted ascending'
                      : sortState === 'desc'
                        ? 'Sorted descending'
                        : 'Not sorted';

                  return (
                    <th key={header.id} className={headerClassNames}>
                      <button
                        type="button"
                        onClick={
                          canSort
                            ? header.column.getToggleSortingHandler()
                            : undefined
                        }
                        className={[
                          'inline-flex items-center gap-2',
                          canSort
                            ? 'text-sand hover:text-sand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/60 focus-visible:ring-offset-2 focus-visible:ring-offset-night'
                            : 'text-sand/80 cursor-default',
                        ].join(' ')}
                        aria-label={sortLabel}
                      >
                        <span>
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                        </span>
                        {canSort ? (
                          <span className="text-[10px] text-sand/60">
                            {sortState === 'asc'
                              ? '▲'
                              : sortState === 'desc'
                                ? '▼'
                                : '↕'}
                          </span>
                        ) : null}
                      </button>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody className="text-sand/90">
            {isLoading ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="py-6 text-center text-xs text-sand/70"
                >
                  {loadingMessage}
                </td>
              </tr>
            ) : hasRows ? (
              visibleRows.map((row, index) => (
                <tr
                  key={row.id}
                  className={[
                    'odd:bg-white/0 even:bg-white/5 border-b border-white/5',
                    onRowClick ? 'cursor-pointer hover:bg-white/10' : null,
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  onClick={
                    onRowClick
                      ? (event) => handleRowClick(row.original, event)
                      : undefined
                  }
                  data-testid={
                    rowTestId ? rowTestId(row.original, index) : undefined
                  }
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className={cellClassNames}
                      onClick={
                        onRowClick
                          ? (event) => handleRowClick(row.original, event, true)
                          : undefined
                      }
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={columns.length}
                  className="py-6 text-center text-xs text-sand/70"
                >
                  {emptyMessage}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showPagination ? (
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-sand/70">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded border border-white/10 px-2 py-1 hover:border-white/30"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              Prev
            </button>
            <button
              type="button"
              className="rounded border border-white/10 px-2 py-1 hover:border-white/30"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              Next
            </button>
          </div>
          <div>
            Page {table.getState().pagination.pageIndex + 1} of {pageCount}
          </div>
          <label className="flex items-center gap-2">
            Rows per page
            <select
              className="rounded border border-white/10 bg-transparent px-2 py-1 text-sand/80"
              value={pagination.pageSize}
              onChange={(event) => {
                const next = Number(event.target.value);
                setPagination({ pageIndex: 0, pageSize: next });
              }}
            >
              {pageSizeOptions.map((size) => (
                <option key={size} value={size} className="bg-night">
                  {size}
                </option>
              ))}
            </select>
          </label>
        </div>
      ) : null}
    </div>
  );
}
