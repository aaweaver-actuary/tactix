import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import PracticeQueue from './PracticeQueue';

vi.mock('./Badge', () => ({
  __esModule: true,
  default: ({ label }: { label: string }) => (
    <span data-testid="badge">{label}</span>
  ),
}));

vi.mock('./Text', () => ({
  __esModule: true,
  default: ({ value }: { value: string }) => <p data-testid="text">{value}</p>,
}));

const baseItem = {
  tactic_id: 1,
  position_id: 10,
  motif: 'fork',
  result: 'missed',
  best_uci: 'e2e4',
  user_uci: 'e2e3',
  move_number: 12,
  ply: 1,
  eval_delta: -2.4,
};

describe('PracticeQueue', () => {
  it('renders header, description, and checkbox state', () => {
    render(
      <PracticeQueue
        data={[]}
        includeFailedAttempt={true}
        onToggleIncludeFailedAttempt={vi.fn()}
        loading={false}
      />,
    );

    expect(screen.getByText('Practice queue')).toBeInTheDocument();
    expect(
      screen.getByText('Missed tactics from your games, ready to drill.'),
    ).toBeInTheDocument();

    const checkbox = screen.getByRole('checkbox', {
      name: /include failed attempts/i,
    }) as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
    expect(checkbox.disabled).toBe(false);
  });

  it('shows loading state and disables checkbox when loading', () => {
    render(
      <PracticeQueue
        data={[]}
        includeFailedAttempt={false}
        onToggleIncludeFailedAttempt={vi.fn()}
        loading={true}
      />,
    );

    expect(screen.getByText('Loading practice queue…')).toBeInTheDocument();

    const checkbox = screen.getByRole('checkbox', {
      name: /include failed attempts/i,
    }) as HTMLInputElement;
    expect(checkbox.disabled).toBe(true);
  });

  it('shows empty state when no data and not loading', () => {
    render(
      <PracticeQueue
        data={[]}
        includeFailedAttempt={false}
        onToggleIncludeFailedAttempt={vi.fn()}
        loading={false}
      />,
    );

    expect(
      screen.getByText('No missed tactics queued yet.'),
    ).toBeInTheDocument();
  });

  it('renders table rows with values and fallback for best move', () => {
    const data = [
      baseItem,
      {
        ...baseItem,
        tactic_id: 2,
        position_id: 11,
        motif: 'pin',
        best_uci: '',
        user_uci: 'g1f3',
        move_number: 7,
        ply: 2,
        eval_delta: -1.1,
        result: 'failed',
      },
    ];

    render(
      <PracticeQueue
        data={data}
        includeFailedAttempt={false}
        onToggleIncludeFailedAttempt={vi.fn()}
        loading={false}
      />,
    );

    expect(screen.getByText('Motif')).toBeInTheDocument();
    expect(screen.getByText('Result')).toBeInTheDocument();
    expect(screen.getByText('Best')).toBeInTheDocument();
    expect(screen.getByText('Your move')).toBeInTheDocument();
    expect(screen.getByText('Move')).toBeInTheDocument();
    expect(screen.getByText('Delta')).toBeInTheDocument();

    expect(screen.getByText('fork')).toBeInTheDocument();
    expect(screen.getByText('pin')).toBeInTheDocument();

    const badges = screen.getAllByTestId('badge').map((n) => n.textContent);
    expect(badges).toEqual(expect.arrayContaining(['missed', 'failed']));

    expect(screen.getByText('e2e4')).toBeInTheDocument();
    expect(screen.getAllByText('--').length).toBe(1);
    expect(screen.getByText('e2e3')).toBeInTheDocument();
    expect(screen.getByText('g1f3')).toBeInTheDocument();
    expect(screen.getByText('12.1')).toBeInTheDocument();
    expect(screen.getByText('7.2')).toBeInTheDocument();
    expect(screen.getByText('-2.4')).toBeInTheDocument();
    expect(screen.getByText('-1.1')).toBeInTheDocument();
  });

  it('calls onToggleIncludeFailedAttempt with next value when checkbox changes', () => {
    const onToggleIncludeFailedAttempt = vi.fn();
    render(
      <PracticeQueue
        data={[]}
        includeFailedAttempt={false}
        onToggleIncludeFailedAttempt={onToggleIncludeFailedAttempt}
        loading={false}
      />,
    );

    const checkbox = screen.getByRole('checkbox', {
      name: /include failed attempts/i,
    }) as HTMLInputElement;

    fireEvent.click(checkbox);
    expect(onToggleIncludeFailedAttempt).toHaveBeenCalledWith(true);
  });
});
