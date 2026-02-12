import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import TacticsActionButtons from './TacticsActionButtons';

const baseTactic = {
  tactic_id: 1,
  game_id: 'g1',
  position_id: 1,
  source: 'chesscom',
  motif: 'fork',
  result: 'missed',
  user_uci: 'e2e4',
  eval_delta: -1,
  severity: 2,
  created_at: '2026-01-01T00:00:00Z',
  best_uci: 'e2e4',
};

describe('TacticsActionButtons', () => {
  it('fires actions when enabled', () => {
    const onOpenGameDetail = vi.fn();
    const onOpenLichess = vi.fn();

    render(
      <TacticsActionButtons
        tactic={baseTactic as any}
        onOpenGameDetail={onOpenGameDetail}
        onOpenLichess={onOpenLichess}
      />,
    );

    fireEvent.click(screen.getByTestId('tactics-go-to-game-g1'));
    fireEvent.click(screen.getByTestId('tactics-open-lichess-g1'));

    expect(onOpenGameDetail).toHaveBeenCalledWith(baseTactic);
    expect(onOpenLichess).toHaveBeenCalledWith(baseTactic);
  });

  it('does not fire actions when disabled', () => {
    const onOpenGameDetail = vi.fn();
    const onOpenLichess = vi.fn();

    render(
      <TacticsActionButtons
        tactic={{ ...baseTactic, game_id: null } as any}
        onOpenGameDetail={onOpenGameDetail}
        onOpenLichess={onOpenLichess}
      />,
    );

    const goToGame = screen.getByTestId('tactics-go-to-game-unknown');
    const openLichess = screen.getByTestId('tactics-open-lichess-unknown');

    expect(goToGame).toBeDisabled();
    expect(openLichess).toBeDisabled();

    fireEvent.click(goToGame);
    fireEvent.click(openLichess);

    expect(onOpenGameDetail).not.toHaveBeenCalled();
    expect(onOpenLichess).not.toHaveBeenCalled();
  });

  it('stops disabled actions even when the button is forced enabled', () => {
    const onOpenGameDetail = vi.fn();
    const onOpenLichess = vi.fn();

    render(
      <TacticsActionButtons
        tactic={{ ...baseTactic, game_id: null } as any}
        onOpenGameDetail={onOpenGameDetail}
        onOpenLichess={onOpenLichess}
      />,
    );

    const goToGame = screen.getByTestId('tactics-go-to-game-unknown');
    const openLichess = screen.getByTestId('tactics-open-lichess-unknown');
    goToGame.removeAttribute('disabled');
    openLichess.removeAttribute('disabled');
    goToGame.disabled = false;
    openLichess.disabled = false;

    fireEvent.click(goToGame);
    fireEvent.click(openLichess);

    expect(onOpenGameDetail).not.toHaveBeenCalled();
    expect(onOpenLichess).not.toHaveBeenCalled();
  });
});
