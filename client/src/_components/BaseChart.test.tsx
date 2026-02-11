import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import BaseButton from './BaseButton';
import BaseChart from './BaseChart';

describe('BaseChart', () => {
  it('renders title, description, actions, and content', () => {
    render(
      <BaseChart
        title="Tactics trend"
        description="Last 7 days"
        actions={<BaseButton type="button">Export</BaseButton>}
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

  it('renders a header without actions when only a title is provided', () => {
    render(
      <BaseChart title="Focus">
        <div>Chart body</div>
      </BaseChart>,
    );

    expect(screen.getByText('Focus')).toBeInTheDocument();
    expect(screen.getByText('Chart body')).toBeInTheDocument();
  });

  it('renders description without a title', () => {
    render(
      <BaseChart description="Weekly rollup">
        <div>Chart body</div>
      </BaseChart>,
    );

    expect(screen.getByText('Weekly rollup')).toBeInTheDocument();
    expect(screen.getByText('Chart body')).toBeInTheDocument();
  });
});
