import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
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
      motif: 'hanging_piece',
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
  render(
    <GameDetailModal
      open
      onClose={() => undefined}
      game={sampleGame}
      moves={['1. e4 e5', '2. Nf3 Nc6']}
      loading={false}
      error={null}
    />,
  );
}

describe('GameDetailModal', () => {
  it('renders move list, player info, and metadata sections', () => {
    renderModal();
    expect(screen.getByTestId('game-detail-modal')).toBeInTheDocument();

    const moves = screen.getAllByTestId('game-move-row');
    expect(moves).toHaveLength(2);

    const analysis = screen.getByTestId('game-detail-analysis');
    expect(analysis.textContent).toContain('Eval (cp)');
    expect(analysis.textContent).toContain('Blunder');

    const players = screen.getByTestId('game-detail-players');
    expect(players.textContent).toContain('Alice');
    expect(players.textContent).toContain('Bob');

    const metadata = screen.getByTestId('game-detail-metadata');
    expect(metadata.textContent).toContain('Test');
    expect(metadata.textContent).toContain('https://chess.com/game/123');
  });

  it('supports keyboard navigation shortcuts', () => {
    renderModal();
    const currentMove = () => screen.getByTestId('game-detail-current-move');
    expect(currentMove().textContent).toContain('2. Nf3 Nc6');

    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(currentMove().textContent).toContain('1. e4 e5');

    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(currentMove().textContent).toContain('2. Nf3 Nc6');

    fireEvent.keyDown(window, { key: 'ArrowUp' });
    expect(currentMove().textContent).toContain('1. e4 e5');

    fireEvent.keyDown(window, { key: 'ArrowDown' });
    expect(currentMove().textContent).toContain('2. Nf3 Nc6');
  });
});
