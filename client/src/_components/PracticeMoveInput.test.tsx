import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import PracticeMoveInput from './PracticeMoveInput';

describe('PracticeMoveInput', () => {
  it('renders with value and placeholder', () => {
    render(
      <PracticeMoveInput
        practiceMove="e2e4"
        setPracticeMove={() => {}}
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
        setPracticeMove={() => {}}
        practiceSubmitting={true}
      />,
    );

    const input = screen.getByPlaceholderText(
      'Enter your move (UCI e.g., e2e4)',
    );
    expect(input).toBeDisabled();
  });

  it('calls setPracticeMove on change', () => {
    const setPracticeMove = jest.fn();
    render(
      <PracticeMoveInput
        practiceMove=""
        setPracticeMove={setPracticeMove}
        practiceSubmitting={false}
      />,
    );

    const input = screen.getByPlaceholderText(
      'Enter your move (UCI e.g., e2e4)',
    );
    fireEvent.change(input, { target: { value: 'g1f3' } });

    expect(setPracticeMove).toHaveBeenCalledWith('g1f3');
  });
});
