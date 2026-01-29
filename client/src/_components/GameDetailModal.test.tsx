import { renderToStaticMarkup } from 'react-dom/server';
import GameDetailModal from './GameDetailModal';
import type { GameDetailResponse } from '../api';

const sampleGame: GameDetailResponse = {
  game_id: 'game-123',
  source: 'chesscom',
  pgn: '[Event "Test"]\n\n1. e4 e5 2. Nf3 Nc6 1-0',
  metadata: {
    user_rating: 1400,
    time_control: '300',
    white_player: 'Alice',
    black_player: 'Bob',
    white_elo: 1400,
    black_elo: 1380,
    result: '1-0',
    event: 'Test',
    site: 'https://chess.com/game/123',
    utc_date: '2024.01.01',
    utc_time: '12:00:00',
    termination: 'Normal',
    start_timestamp_ms: 1704110400000,
  },
  analysis: [
    {
      tactic_id: 1,
      position_id: 2,
      game_id: 'game-123',
      motif: 'fork',
      severity: 1.5,
      best_uci: 'g1f3',
      best_san: 'Nf3',
      explanation: 'Best line',
      eval_cp: 120,
      created_at: '2024-01-01T00:00:00Z',
      result: 'missed',
      user_uci: 'g1f3',
      eval_delta: -220,
      move_number: 2,
      ply: 3,
      san: 'Nf3',
      uci: 'g1f3',
      side_to_move: 'w',
      fen: 'test',
    },
  ],
};

function renderModal() {
  const html = renderToStaticMarkup(
    <GameDetailModal
      open
      onClose={() => undefined}
      game={sampleGame}
      moves={['1. e4 e5', '2. Nf3 Nc6']}
      loading={false}
      error={null}
    />,
  );
  const parser = new DOMParser();
  return parser.parseFromString(html, 'text/html');
}

describe('GameDetailModal', () => {
  it('renders move list and analysis sections', () => {
    const doc = renderModal();
    const modal = doc.querySelector('[data-testid="game-detail-modal"]');
    expect(modal).not.toBeNull();

    const moves = doc.querySelectorAll('[data-testid="game-move-row"]');
    expect(moves).toHaveLength(2);

    const analysis = doc.querySelector('[data-testid="game-detail-analysis"]');
    expect(analysis?.textContent).toContain('Eval (cp)');
    expect(analysis?.textContent).toContain('Blunder');
  });
});
