export const extractTableHeaders = (doc: Document): string[] =>
  Array.from(doc.querySelectorAll('th')).map((th) =>
    th.textContent?.replace(/[▲▼↕]/g, '').trim(),
  );

export const extractTableRowCells = (doc: Document): string[][] =>
  Array.from(doc.querySelectorAll('tbody tr')).map((row) =>
    Array.from(row.querySelectorAll('td')).map(
      (td) => td.textContent?.trim() ?? '',
    ),
  );
