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
    const onPracticeAttempt = vi.fn();

    act(() => {
      root.render(
        <PracticeAttemptButton
          onPracticeAttempt={onPracticeAttempt}
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
    const onPracticeAttempt = vi.fn();

    act(() => {
      root.render(
        <PracticeAttemptButton
          onPracticeAttempt={onPracticeAttempt}
          practiceSubmitting={true}
        />,
      );
    });

    const button = container.querySelector('button') as HTMLButtonElement;
    expect(button.textContent).toBe('Submitting…');
    expect(button.disabled).toBe(true);
  });

  it('calls handlePracticeAttempt on click', async () => {
    const onPracticeAttempt = vi.fn();

    act(() => {
      root.render(
        <PracticeAttemptButton
          onPracticeAttempt={onPracticeAttempt}
          practiceSubmitting={false}
        />,
      );
    });

    const button = container.querySelector('button') as HTMLButtonElement;

    await act(async () => {
      button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(onPracticeAttempt).toHaveBeenCalledTimes(1);
  });

  it('passes through the provided click handler', async () => {
    const onPracticeAttempt = vi.fn();

    act(() => {
      root.render(
        <PracticeAttemptButton
          onPracticeAttempt={onPracticeAttempt}
          practiceSubmitting={false}
        />,
      );
    });

    const button = container.querySelector('button') as HTMLButtonElement;

    await act(async () => {
      button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(onPracticeAttempt).toHaveBeenCalledTimes(1);
  });
});
