import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import BaseCard, { isInteractiveTarget } from './BaseCard';
import BaseButton from './BaseButton';

describe('BaseCard', () => {
  it('defaults to collapsed and toggles on click', () => {
    render(
      <BaseCard header={<span>Card header</span>}>
        <p>Card content</p>
      </BaseCard>,
    );

    const header = screen.getByRole('button', { name: /card header/i });
    expect(header).toHaveAttribute('aria-expanded', 'false');

    const contentWrapper = screen
      .getByText('Card content')
      .closest('[data-state]') as HTMLElement;
    expect(contentWrapper).toHaveAttribute('data-state', 'collapsed');

    fireEvent.click(header);
    expect(header).toHaveAttribute('aria-expanded', 'true');
    expect(contentWrapper).toHaveAttribute('data-state', 'expanded');
  });

  it('toggles via keyboard activation', () => {
    render(
      <BaseCard header={<span>Keyboard header</span>}>
        <p>Keyboard content</p>
      </BaseCard>,
    );

    const header = screen.getByRole('button', { name: /keyboard header/i });
    fireEvent.keyDown(header, { key: 'Enter' });
    expect(header).toHaveAttribute('aria-expanded', 'true');

    fireEvent.keyDown(header, { key: ' ' });
    expect(header).toHaveAttribute('aria-expanded', 'false');
  });

  it('ignores non-toggle keyboard events', () => {
    render(
      <BaseCard header={<span>Ignore key header</span>}>
        <p>Ignore key content</p>
      </BaseCard>,
    );

    const header = screen.getByRole('button', { name: /ignore key header/i });
    fireEvent.keyDown(header, { key: 'Escape' });
    expect(header).toHaveAttribute('aria-expanded', 'false');
  });

  it('does not toggle when interacting with header controls', () => {
    render(
      <BaseCard
        header={
          <div>
            <span>Interactive header</span>
            <BaseButton>Action</BaseButton>
          </div>
        }
      >
        <p>Interactive content</p>
      </BaseCard>,
    );

    const header = screen.getByRole('button', { name: /interactive header/i });
    const actionButton = screen.getByRole('button', { name: 'Action' });

    fireEvent.click(actionButton);
    expect(header).toHaveAttribute('aria-expanded', 'false');
  });

  it('renders a drag handle and does not toggle on drag handle click', () => {
    render(
      <BaseCard
        header={<span>Drag header</span>}
        dragHandleProps={{}}
        dragHandleLabel="Reorder card"
      >
        <p>Drag content</p>
      </BaseCard>,
    );

    const header = screen.getByRole('button', { name: /drag header/i });
    const dragHandle = screen.getByRole('button', { name: /reorder card/i });

    fireEvent.click(dragHandle);
    expect(header).toHaveAttribute('aria-expanded', 'false');
  });

  it('falls back to the default drag handle label', () => {
    render(
      <BaseCard header={<span>Default drag label</span>} dragHandleProps={{}}>
        <p>Drag content</p>
      </BaseCard>,
    );

    expect(
      screen.getByRole('button', { name: 'Reorder card' }),
    ).toBeInTheDocument();
  });

  it('prefers drag handle aria labels when provided', () => {
    render(
      <BaseCard
        header={<span>Aria drag label</span>}
        dragHandleProps={{ 'aria-label': 'Grab card' }}
      >
        <p>Drag content</p>
      </BaseCard>,
    );

    expect(
      screen.getByRole('button', { name: 'Grab card' }),
    ).toBeInTheDocument();
  });

  it('calls onCollapsedChange when toggling', () => {
    const onCollapsedChange = vi.fn();
    render(
      <BaseCard
        header={<span>Callback header</span>}
        onCollapsedChange={onCollapsedChange}
      >
        <p>Callback content</p>
      </BaseCard>,
    );

    const header = screen.getByRole('button', { name: /callback header/i });
    expect(onCollapsedChange).toHaveBeenCalledWith(true);

    fireEvent.click(header);
    expect(onCollapsedChange).toHaveBeenLastCalledWith(false);
  });

  it('renders non-collapsible cards without toggle controls', () => {
    render(
      <BaseCard header={<span>Static header</span>} collapsible={false}>
        <p>Static content</p>
      </BaseCard>,
    );

    expect(screen.queryByRole('button', { name: /static header/i })).toBeNull();
    expect(screen.getByText('Static content')).toBeInTheDocument();
  });

  it('treats non-element targets as non-interactive', () => {
    expect(isInteractiveTarget(null)).toBe(false);
    expect(isInteractiveTarget(document.createTextNode('x'))).toBe(false);
  });
});
