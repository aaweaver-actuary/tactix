import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ModalShell from './ModalShell';

describe('ModalShell', () => {
  it('closes on Escape key press', () => {
    const onClose = vi.fn();
    render(
      <ModalShell testId="modal" onClose={onClose}>
        <div>Content</div>
      </ModalShell>,
    );

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('closes when clicking on the backdrop only', () => {
    const onClose = vi.fn();
    render(
      <ModalShell testId="modal" onClose={onClose}>
        <div data-testid="modal-content">Content</div>
      </ModalShell>,
    );

    fireEvent.click(screen.getByTestId('modal'));
    expect(onClose).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('modal-content'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
