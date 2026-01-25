import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Hero from './Hero';
import { SOURCE_OPTIONS } from '../utils/SOURCE_OPTIONS';

describe('Hero', () => {
  const baseProps = {
    onRun: jest.fn(),
    onBackfill: jest.fn(),
    onRefresh: jest.fn(),
    onMigrate: jest.fn(),
    loading: false,
    version: 42,
    source: 'lichess' as const,
    user: 'andy',
    onSourceChange: jest.fn(),
  };

  it('renders title and metadata', () => {
    render(<Hero {...baseProps} />);
    expect(
      screen.getByText('Airflow DAG · daily_game_sync'),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: /lichess rapid pipeline/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Execution stamped via metrics version 42 · user andy'),
    ).toBeInTheDocument();
  });

  it('renders source options and triggers change', () => {
    render(<Hero {...baseProps} />);
    SOURCE_OPTIONS.forEach((opt) => {
      const btn = screen.getByRole('button', { name: opt.label });
      expect(btn).toBeInTheDocument();
    });

    const target = SOURCE_OPTIONS[0];
    fireEvent.click(screen.getByRole('button', { name: target.label }));
    expect(baseProps.onSourceChange).toHaveBeenCalledWith(target.id);
  });

  it('fires action callbacks', () => {
    render(<Hero {...baseProps} />);
    fireEvent.click(screen.getByRole('button', { name: 'Run + Refresh' }));
    fireEvent.click(screen.getByRole('button', { name: 'Backfill history' }));
    fireEvent.click(screen.getByRole('button', { name: 'Run migrations' }));
    fireEvent.click(screen.getByRole('button', { name: 'Refresh metrics' }));

    expect(baseProps.onRun).toHaveBeenCalled();
    expect(baseProps.onBackfill).toHaveBeenCalled();
    expect(baseProps.onMigrate).toHaveBeenCalled();
    expect(baseProps.onRefresh).toHaveBeenCalled();
  });

  it('shows loading state and disables buttons', () => {
    render(<Hero {...baseProps} loading={true} />);
    expect(screen.getByRole('button', { name: 'Running…' })).toBeDisabled();
    expect(
      screen.getByRole('button', { name: 'Backfill history' }),
    ).toBeDisabled();
    expect(
      screen.getByRole('button', { name: 'Run migrations' }),
    ).toBeDisabled();
    expect(
      screen.getByRole('button', { name: 'Refresh metrics' }),
    ).toBeDisabled();

    SOURCE_OPTIONS.forEach((opt) => {
      expect(screen.getByRole('button', { name: opt.label })).toBeDisabled();
    });
  });

  it('renders chess.com title when source is not lichess', () => {
    render(<Hero {...baseProps} source={'chess.com' as const} />);
    expect(
      screen.getByRole('heading', { name: /chess\.com blitz pipeline/i }),
    ).toBeInTheDocument();
  });
});
