import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import BaseChart from './BaseChart';

describe('BaseChart', () => {
  it('renders title, description, actions, and content', () => {
    render(
      <BaseChart
        title="Tactics trend"
        description="Last 7 days"
        actions={<button type="button">Export</button>}
      >
        <div>Chart content</div>
      </BaseChart>,
    );

    expect(screen.getByText('Tactics trend')).toBeInTheDocument();
    expect(screen.getByText('Last 7 days')).toBeInTheDocument();
    expect(screen.getByText('Export')).toBeInTheDocument();
    expect(screen.getByText('Chart content')).toBeInTheDocument();
  });

  it('renders content without a header when none is provided', () => {
    render(
      <BaseChart>
        <div>Inline chart</div>
      </BaseChart>,
    );

    expect(screen.getByText('Inline chart')).toBeInTheDocument();
  });
});
