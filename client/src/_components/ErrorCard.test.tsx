import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ErrorCard from './ErrorCard';

describe('ErrorCard', () => {
  it('renders the message and test id', () => {
    render(<ErrorCard message="Something went wrong" testId="error-card" />);

    expect(screen.getByTestId('error-card')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });
});
