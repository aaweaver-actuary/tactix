import React, { act } from 'react';
import { createRoot, Root } from 'react-dom/client';
import { vi } from 'vitest';
import PracticeAttemptButton from './PracticeAttemptButton';

describe('PracticeAttemptButton', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it('renders default label and is enabled when not submitting', () => {
    const handlePracticeAttempt = vi.fn().mockResolvedValue(undefined);

    act(() => {
      root.render(
        <PracticeAttemptButton
          handlePracticeAttempt={handlePracticeAttempt}
          practiceSubmitting={false}
        />,
      );
    });

    const button = container.querySelector('button') as HTMLButtonElement;
    expect(button).not.toBeNull();
    expect(button.textContent).toBe('Submit attempt');
    expect(button.disabled).toBe(false);
  });

  it('renders submitting label and is disabled when submitting', () => {
    const handlePracticeAttempt = vi.fn().mockResolvedValue(undefined);

    act(() => {
      root.render(
        <PracticeAttemptButton
          handlePracticeAttempt={handlePracticeAttempt}
          practiceSubmitting={true}
        />,
      );
    });

    const button = container.querySelector('button') as HTMLButtonElement;
    expect(button.textContent).toBe('Submitting…');
    expect(button.disabled).toBe(true);
  });

  it('calls handlePracticeAttempt on click', async () => {
    const handlePracticeAttempt = vi.fn().mockResolvedValue(undefined);

    act(() => {
      root.render(
        <PracticeAttemptButton
          handlePracticeAttempt={handlePracticeAttempt}
          practiceSubmitting={false}
        />,
      );
    });

    const button = container.querySelector('button') as HTMLButtonElement;

    await act(async () => {
      button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(handlePracticeAttempt).toHaveBeenCalledTimes(1);
  });

  it('passes the input ref value as an override move', async () => {
    const handlePracticeAttempt = vi.fn().mockResolvedValue(undefined);
    const input = document.createElement('input');
    input.value = 'e2e4';

    act(() => {
      root.render(
        <PracticeAttemptButton
          handlePracticeAttempt={handlePracticeAttempt}
          practiceSubmitting={false}
          practiceMoveRef={{ current: input }}
        />,
      );
    });

    const button = container.querySelector('button') as HTMLButtonElement;

    await act(async () => {
      button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(handlePracticeAttempt).toHaveBeenCalledWith('e2e4');
  });
});
