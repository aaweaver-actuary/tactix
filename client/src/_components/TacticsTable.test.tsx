import { renderToStaticMarkup } from 'react-dom/server';
import TacticsTable from './TacticsTable';
import { extractTableHeaders, extractTableRowCells } from './testUtils';

const sampleData = [
  {
    tactic_id: 't1',
    motif: 'hanging_piece',
    result: 'correct',
    user_uci: 'e2e4',
    eval_delta: 120,
  },
  {
    tactic_id: 't2',
    motif: 'mate',
    result: 'wrong',
    user_uci: 'g1f3',
    eval_delta: -85,
  },
];

const columns = [
  { header: 'Motif', accessorKey: 'motif' },
  { header: 'Result', accessorKey: 'result' },
  { header: 'Move', accessorKey: 'user_uci' },
  { header: 'Delta (cp)', accessorKey: 'eval_delta' },
];

function renderToDocument() {
  const html = renderToStaticMarkup(
    <TacticsTable data={sampleData as any} columns={columns as any} />,
  );
  const parser = new DOMParser();
  return parser.parseFromString(html, 'text/html');
}

describe('TacticsTable', () => {
  it('renders the title and table headers', () => {
    const doc = renderToDocument();

    const headers = extractTableHeaders(doc);
    expect(headers).toEqual(['Motif', 'Result', 'Move', 'Delta (cp)']);
  });

  it('renders rows with motif, result badge, move, and delta', () => {
    const doc = renderToDocument();

    const rows = extractTableRowCells(doc);
    expect(rows).toHaveLength(2);

    const firstRowCells = rows[0];
    expect(firstRowCells).toContain('hanging_piece');
    expect(firstRowCells).toContain('e2e4');
    expect(firstRowCells).toContain('120');

    const secondRowCells = rows[1];
    expect(secondRowCells).toContain('mate');
    expect(secondRowCells).toContain('g1f3');
    expect(secondRowCells).toContain('-85');
  });
});
