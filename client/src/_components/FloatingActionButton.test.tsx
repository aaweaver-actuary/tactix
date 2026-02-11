import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import FloatingActionButton from './FloatingActionButton';

describe('FloatingActionButton', () => {
  it('opens and closes via Escape key', () => {
    render(
      <FloatingActionButton
        label="Open settings"
        actions={[{ id: 'a', label: 'First', onClick: vi.fn() }]}
      />,
    );

    fireEvent.click(screen.getByTestId('fab-toggle'));
    expect(screen.getByRole('menu')).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  it('closes when clicking outside and keeps open on inside pointer down', () => {
    render(
      <FloatingActionButton
        label="Open settings"
        actions={[{ id: 'a', label: 'First', onClick: vi.fn() }]}
      />,
    );

    fireEvent.click(screen.getByTestId('fab-toggle'));
    expect(screen.getByRole('menu')).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByTestId('fab-toggle'));
    expect(screen.getByRole('menu')).toBeInTheDocument();

    const nullTargetEvent = new MouseEvent('mousedown', { bubbles: true });
    Object.defineProperty(nullTargetEvent, 'target', { value: null });
    window.dispatchEvent(nullTargetEvent);
    expect(screen.getByRole('menu')).toBeInTheDocument();

    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  it('fires actions and uses label fallback for aria-labels', () => {
    const onClick = vi.fn();
    render(
      <FloatingActionButton
        label="Open settings"
        actions={[{ id: 'a', label: 'Launch', onClick }]}
      />,
    );

    fireEvent.click(screen.getByTestId('fab-toggle'));

    const actionButton = screen.getByRole('menuitem', { name: 'Launch' });
    fireEvent.click(actionButton);

    expect(onClick).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  it('ignores non-escape key presses while open', () => {
    render(
      <FloatingActionButton
        label="Open settings"
        actions={[{ id: 'a', label: 'First', onClick: vi.fn() }]}
      />,
    );

    fireEvent.click(screen.getByTestId('fab-toggle'));
    expect(screen.getByRole('menu')).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Enter' });
    expect(screen.getByRole('menu')).toBeInTheDocument();
  });
});
