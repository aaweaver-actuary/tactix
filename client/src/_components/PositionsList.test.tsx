import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import PositionsList from './PositionsList';

describe('PositionsList', () => {
  it('renders the header and badge', () => {
    const html = renderToStaticMarkup(<PositionsList positionsData={[]} />);

    expect(html).toContain('Latest positions');
    expect(html).toContain('Fen');
    expect(html).toContain('aria-expanded="false"');
  });

  it('renders position details with clock seconds', () => {
    const positionsData = [
      {
        position_id: 'p1',
        fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
        move_number: 1,
        san: 'e4',
        clock_seconds: 120,
      },
    ];

    const html = renderToStaticMarkup(
      <PositionsList positionsData={positionsData} />,
    );

    expect(html).toContain(positionsData[0].fen);
    expect(html).toContain('Move 1 · e4');
    expect(html).toContain('120s');
  });

  it('renders fallback clock when clock_seconds is missing', () => {
    const positionsData = [
      {
        position_id: 'p2',
        fen: '8/8/8/8/8/8/8/8 w - - 0 1',
        move_number: 5,
        san: 'Nf3',
      },
    ];

    const html = renderToStaticMarkup(
      <PositionsList positionsData={positionsData} />,
    );

    expect(html).toContain(positionsData[0].fen);
    expect(html).toContain('Move 5 · Nf3');
    expect(html).toContain('--s');
  });
});
