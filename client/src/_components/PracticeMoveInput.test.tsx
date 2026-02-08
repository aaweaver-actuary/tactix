import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import PracticeMoveInput from './PracticeMoveInput';

describe('PracticeMoveInput', () => {
  it('renders with value and placeholder', () => {
    render(
      <PracticeMoveInput
        practiceMove="e2e4"
        onPracticeMoveChange={() => {}}
        onPracticeSubmit={(move) => {
          void move;
        }}
        practiceSubmitting={false}
      />,
    );

    const input = screen.getByPlaceholderText(
      'Enter your move (UCI e.g., e2e4)',
    ) as HTMLInputElement;
    expect(input).toBeInTheDocument();
    expect(input.value).toBe('e2e4');
  });

  it('disables input when submitting', () => {
    render(
      <PracticeMoveInput
        practiceMove=""
        onPracticeMoveChange={() => {}}
        onPracticeSubmit={(move) => {
          void move;
        }}
        practiceSubmitting={true}
      />,
    );

    const input = screen.getByPlaceholderText(
      'Enter your move (UCI e.g., e2e4)',
    );
    expect(input).toBeDisabled();
  });

  it('calls onPracticeMoveChange on change', () => {
    const onPracticeMoveChange = vi.fn();
    render(
      <PracticeMoveInput
        practiceMove=""
        onPracticeMoveChange={onPracticeMoveChange}
        onPracticeSubmit={(move) => {
          void move;
        }}
        practiceSubmitting={false}
      />,
    );

    const input = screen.getByPlaceholderText(
      'Enter your move (UCI e.g., e2e4)',
    );
    fireEvent.change(input, { target: { value: 'g1f3' } });

    expect(onPracticeMoveChange).toHaveBeenCalledWith('g1f3');
  });

  it('submits on Enter when there is input', () => {
    const onPracticeSubmit = vi.fn();
    render(
      <PracticeMoveInput
        practiceMove="e2e4"
        onPracticeMoveChange={() => {}}
        onPracticeSubmit={onPracticeSubmit}
        practiceSubmitting={false}
      />,
    );

    const input = screen.getByPlaceholderText(
      'Enter your move (UCI e.g., e2e4)',
    );
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(onPracticeSubmit).toHaveBeenCalledWith('e2e4');
  });

  it('does not submit on Enter when input is empty', () => {
    const onPracticeSubmit = vi.fn();
    render(
      <PracticeMoveInput
        practiceMove=""
        onPracticeMoveChange={() => {}}
        onPracticeSubmit={onPracticeSubmit}
        practiceSubmitting={false}
      />,
    );

    const input = screen.getByPlaceholderText(
      'Enter your move (UCI e.g., e2e4)',
    );
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(onPracticeSubmit).not.toHaveBeenCalled();
  });
});
