import { describe, expect, it } from 'vitest';
import { extractTableHeaders, extractTableRowCells } from './testUtils';

describe('table test utils', () => {
  it('extracts headers without sort glyphs', () => {
    const doc = document.implementation.createHTMLDocument('test');
    const table = doc.createElement('table');
    const thead = doc.createElement('thead');
    const tr = doc.createElement('tr');
    const th = doc.createElement('th');
    th.textContent = 'Name ▲';
    tr.appendChild(th);
    thead.appendChild(tr);
    table.appendChild(thead);
    doc.body.appendChild(table);

    expect(extractTableHeaders(doc)).toEqual(['Name']);
  });

  it('extracts row cells with empty fallbacks', () => {
    const doc = document.implementation.createHTMLDocument('test');
    const table = doc.createElement('table');
    const tbody = doc.createElement('tbody');
    const tr = doc.createElement('tr');
    const td = doc.createElement('td');
    Object.defineProperty(td, 'textContent', { value: null, writable: true });
    tr.appendChild(td);
    tbody.appendChild(tr);
    table.appendChild(tbody);
    doc.body.appendChild(table);

    expect(extractTableRowCells(doc)).toEqual([['']]);
  });
});
