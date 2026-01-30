import { render, fireEvent, screen } from '@testing-library/react';
import { renderToStaticMarkup } from 'react-dom/server';
import { vi } from 'vitest';
import RecentGamesTable from './RecentGamesTable';
import { extractTableHeaders, extractTableRowCells } from './testUtils';

const sampleData = [
  {
    game_id: 'g1',
    source: 'chesscom',
    opponent: 'opponent1',
    result: '1-0',
    played_at: '2026-01-29T12:00:00.000Z',
    time_control: '300+0',
    user_color: 'white',
  },
  {
    game_id: 'g2',
    source: 'lichess',
    opponent: 'opponent2',
    result: '0-1',
    played_at: '2026-01-28T18:30:00.000Z',
    time_control: '600+5',
    user_color: 'black',
  },
];

const columns = [
  { header: 'Source', accessorKey: 'source' },
  { header: 'Opponent', accessorKey: 'opponent' },
  { header: 'Result', accessorKey: 'result' },
  { header: 'Date', accessorKey: 'played_at' },
  { header: 'Time control', accessorKey: 'time_control' },
];

function renderToDocument() {
  const html = renderToStaticMarkup(
    <RecentGamesTable data={sampleData as any} columns={columns as any} />,
  );
  const parser = new DOMParser();
  return parser.parseFromString(html, 'text/html');
}

describe('RecentGamesTable', () => {
  it('renders the table headers', () => {
    const doc = renderToDocument();

    const headers = extractTableHeaders(doc);
    expect(headers).toEqual([
      'Source',
      'Opponent',
      'Result',
      'Date',
      'Time control',
    ]);
  });

  it('renders rows with opponent, result, and date', () => {
    const doc = renderToDocument();

    const rows = extractTableRowCells(doc);
    expect(rows).toHaveLength(2);

    const firstRowCells = rows[0];
    expect(firstRowCells).toContain('opponent1');
    expect(firstRowCells).toContain('1-0');
    expect(firstRowCells).toContain('2026-01-29T12:00:00.000Z');

    const secondRowCells = rows[1];
    expect(secondRowCells).toContain('opponent2');
    expect(secondRowCells).toContain('0-1');
    expect(secondRowCells).toContain('2026-01-28T18:30:00.000Z');
  });

  it('fires onRowClick when a row is clicked', () => {
    const handleRowClick = vi.fn();
    render(
      <RecentGamesTable
        data={sampleData as any}
        columns={columns as any}
        onRowClick={handleRowClick}
      />,
    );

    const rows = screen.getAllByRole('row');
    fireEvent.click(rows[1]);

    expect(handleRowClick).toHaveBeenCalledTimes(1);
    expect(handleRowClick).toHaveBeenCalledWith(sampleData[0]);
  });
});
