import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { vi } from 'vitest';
import TacticsTable from './TacticsTable';

vi.mock('./Badge', () => ({
  __esModule: true,
  default: ({ label }: { label: string }) => (
    <span data-testid="badge">{label}</span>
  ),
}));

const sampleData = [
  {
    tactic_id: 't1',
    motif: 'pin',
    result: 'correct',
    user_uci: 'e2e4',
    eval_delta: 120,
  },
  {
    tactic_id: 't2',
    motif: 'fork',
    result: 'wrong',
    user_uci: 'g1f3',
    eval_delta: -85,
  },
];

function renderToDocument() {
  const html = renderToStaticMarkup(
    <TacticsTable tacticsData={sampleData as any} />,
  );
  const parser = new DOMParser();
  return parser.parseFromString(html, 'text/html');
}

describe('TacticsTable', () => {
  it('renders the title and table headers', () => {
    const doc = renderToDocument();

    expect(doc.querySelector('h3')?.textContent).toBe('Recent tactics');

    const headers = Array.from(doc.querySelectorAll('th')).map((th) =>
      th.textContent?.trim(),
    );
    expect(headers).toEqual(['Motif', 'Result', 'Move', 'Delta (cp)']);
  });

  it('renders rows with motif, result badge, move, and delta', () => {
    const doc = renderToDocument();

    const rows = Array.from(doc.querySelectorAll('tbody tr'));
    expect(rows).toHaveLength(2);

    const firstRowCells = Array.from(rows[0].querySelectorAll('td')).map((td) =>
      td.textContent?.trim(),
    );
    expect(firstRowCells).toContain('pin');
    expect(firstRowCells).toContain('e2e4');
    expect(firstRowCells).toContain('120');

    const secondRowCells = Array.from(rows[1].querySelectorAll('td')).map(
      (td) => td.textContent?.trim(),
    );
    expect(secondRowCells).toContain('fork');
    expect(secondRowCells).toContain('g1f3');
    expect(secondRowCells).toContain('-85');

    const badges = Array.from(
      doc.querySelectorAll('[data-testid="badge"]'),
    ).map((el) => el.textContent?.trim());
    expect(badges).toEqual(['Live', 'correct', 'wrong']);
  });
});
