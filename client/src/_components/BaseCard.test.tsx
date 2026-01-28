import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import BaseCard from './BaseCard';

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

  it('does not toggle when interacting with header controls', () => {
    render(
      <BaseCard
        header={
          <div>
            <span>Interactive header</span>
            <button type="button">Action</button>
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
});
