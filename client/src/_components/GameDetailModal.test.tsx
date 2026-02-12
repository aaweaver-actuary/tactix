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

  it('ignores keyboard navigation when no moves exist', () => {
    render(
      <GameDetailModal
        open
        onClose={() => undefined}
        game={sampleGame}
        moves={[]}
        loading={false}
        error={null}
      />,
    );

    const currentMove = screen.getByTestId('game-detail-current-move');
    expect(currentMove.textContent).toContain('No moves loaded');
    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(currentMove.textContent).toContain('No moves loaded');
  });

  it('renders empty states when no game is selected', () => {
    render(
      <GameDetailModal
        open
        onClose={() => undefined}
        game={null}
        moves={[]}
        loading={false}
        error={null}
      />,
    );

    expect(
      screen.getByText('Select a game to view details.'),
    ).toBeInTheDocument();
  });

  it('renders analysis and metadata fallbacks', () => {
    render(
      <GameDetailModal
        open
        onClose={() => undefined}
        game={
          {
            ...sampleGame,
            analysis: [],
            metadata: {
              user_rating: null,
              time_control: null,
              white_player: null,
              black_player: null,
              white_elo: null,
              black_elo: null,
              result: null,
              event: null,
              site: null,
              utc_date: null,
              utc_time: null,
              termination: null,
              start_timestamp_ms: null,
            },
          } as any
        }
        moves={[]}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByText('No metadata available.')).toBeInTheDocument();
    expect(
      screen.getAllByText('No analysis rows found.').length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText('Unknown').length).toBeGreaterThan(0);
  });

  it('updates current move via navigation and list clicks', () => {
    renderModal();

    fireEvent.click(screen.getByTestId('game-detail-nav-first'));
    expect(
      screen.getByTestId('game-detail-current-move').textContent,
    ).toContain('1. e4 e5');

    fireEvent.click(screen.getByTestId('game-detail-nav-next'));
    expect(
      screen.getByTestId('game-detail-current-move').textContent,
    ).toContain('2. Nf3 Nc6');

    fireEvent.click(screen.getByTestId('game-detail-nav-last'));
    expect(
      screen.getByTestId('game-detail-current-move').textContent,
    ).toContain('2. Nf3 Nc6');

    fireEvent.click(screen.getByTestId('game-detail-nav-prev'));
    expect(
      screen.getByTestId('game-detail-current-move').textContent,
    ).toContain('1. e4 e5');

    fireEvent.click(screen.getAllByTestId('game-move-row')[1]);
    expect(
      screen.getByTestId('game-detail-current-move').textContent,
    ).toContain('2. Nf3 Nc6');
  });

  it('jumps to the last move from the first position', () => {
    renderModal();

    fireEvent.click(screen.getByTestId('game-detail-nav-first'));
    fireEvent.click(screen.getByTestId('game-detail-nav-last'));

    expect(
      screen.getByTestId('game-detail-current-move').textContent,
    ).toContain('2. Nf3 Nc6');
  });

  it('renders default player labels when one side is missing', () => {
    render(
      <GameDetailModal
        open
        onClose={() => undefined}
        game={
          {
            ...sampleGame,
            metadata: {
              ...sampleGame.metadata,
              white_player: null,
            },
          } as any
        }
        moves={['1. e4 e5']}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByText('White vs Bob')).toBeInTheDocument();
  });

  it('falls back to a Black label when the black player is missing', () => {
    render(
      <GameDetailModal
        open
        onClose={() => undefined}
        game={
          {
            ...sampleGame,
            metadata: {
              ...sampleGame.metadata,
              black_player: null,
            },
          } as any
        }
        moves={['1. e4 e5']}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByText('Alice vs Black')).toBeInTheDocument();
  });

  it('renders evaluation flags for ok and missing deltas', () => {
    render(
      <GameDetailModal
        open
        onClose={() => undefined}
        game={
          {
            ...sampleGame,
            analysis: [
              {
                ...sampleGame.analysis[0],
                tactic_id: 2,
                eval_cp: null,
                eval_delta: 50,
                move_number: null,
                ply: null,
                san: null,
                user_uci: null,
                motif: null,
              },
              {
                ...sampleGame.analysis[0],
                tactic_id: 3,
                eval_delta: null,
                move_number: 1,
                ply: null,
              },
            ],
          } as any
        }
        moves={['1. e4 e5']}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getAllByText('OK').length).toBeGreaterThan(0);
    expect(screen.getAllByText('--').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Move 1').length).toBeGreaterThan(0);
    fireEvent.keyDown(window, { key: 'x' });
  });
});
