import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import MotifCard from './MotifCard';

const baseProps = {
  motif: 'mate',
  found: 3,
  total: 5,
  missed: 1,
  failedAttempt: 1,
};

describe('MotifCard', () => {
  it('renders labels and counts for the default variant', () => {
    render(<MotifCard {...baseProps} />);

    expect(screen.getByText('mate')).toBeInTheDocument();
    expect(screen.getByText('3/5')).toBeInTheDocument();
    expect(screen.getByText('1 missed, 1 failed')).toBeInTheDocument();
  });

  it('renders a highlighted variant with a drag handle', () => {
    render(
      <MotifCard
        {...baseProps}
        dragHandleProps={{}}
        dragHandleLabel="Reorder mate"
      />,
    );

    expect(
      screen.getByRole('button', { name: /reorder mate/i }),
    ).toBeInTheDocument();
  });

  it('toggles the header via click and keyboard', () => {
    render(<MotifCard {...baseProps} />);

    const header = screen.getByRole('button', { name: /mate/i });
    expect(header).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(header);
    expect(header).toHaveAttribute('aria-expanded', 'true');

    fireEvent.keyDown(header, { key: 'Enter' });
    expect(header).toHaveAttribute('aria-expanded', 'false');

    fireEvent.keyDown(header, { key: ' ' });
    expect(header).toHaveAttribute('aria-expanded', 'true');
  });
});
