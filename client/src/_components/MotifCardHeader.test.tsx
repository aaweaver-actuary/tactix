import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import MotifCardHeader from './MotifCardHeader';

const baseProps = {
  motif: 'mate',
  found: 3,
  total: 5,
  missed: 1,
  failedAttempt: 1,
};

describe('MotifCardHeader', () => {
  it('renders motif stats summary', () => {
    render(<MotifCardHeader {...baseProps} />);

    expect(screen.getByText('mate')).toBeInTheDocument();
    expect(screen.getByText('3/5')).toBeInTheDocument();
    expect(screen.getByText('1 missed, 1 failed')).toBeInTheDocument();
  });
});
