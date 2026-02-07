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
        practiceSubmitting={false}
      />,
    );

    const input = screen.getByPlaceholderText(
      'Enter your move (UCI e.g., e2e4)',
    );
    fireEvent.change(input, { target: { value: 'g1f3' } });

    expect(onPracticeMoveChange).toHaveBeenCalledWith('g1f3');
  });
});
