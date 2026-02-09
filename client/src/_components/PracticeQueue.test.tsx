import { render, screen } from '@testing-library/react';
import PracticeQueue from './PracticeQueue';

const baseItem = {
  tactic_id: 1,
  position_id: 10,
  motif: 'hanging_piece',
  result: 'missed',
  best_uci: 'e2e4',
  user_uci: 'e2e3',
  move_number: 12,
  ply: 1,
  eval_delta: -2.4,
};

const columns = [
  { header: 'Motif', accessorKey: 'motif' },
  { header: 'Result', accessorKey: 'result' },
  { header: 'Best', accessorKey: 'best_uci' },
  { header: 'Your move', accessorKey: 'user_uci' },
  {
    header: 'Move',
    accessorFn: (row: any) => `${row.move_number}.${row.ply}`,
  },
  { header: 'Delta', accessorKey: 'eval_delta' },
];

describe('PracticeQueue', () => {
  it('shows loading message when data is null', () => {
    render(<PracticeQueue data={null} columns={columns as any} />);
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('renders table rows with values', () => {
    const data = [
      baseItem,
      {
        ...baseItem,
        tactic_id: 2,
        position_id: 11,
        motif: 'mate',
        best_uci: '',
        user_uci: 'g1f3',
        move_number: 7,
        ply: 2,
        eval_delta: -1.1,
        result: 'failed',
      },
    ];

    render(<PracticeQueue data={data as any} columns={columns as any} />);

    expect(screen.getByText('Motif')).toBeInTheDocument();
    expect(screen.getByText('Result')).toBeInTheDocument();
    expect(screen.getByText('Best')).toBeInTheDocument();
    expect(screen.getByText('Your move')).toBeInTheDocument();
    expect(screen.getByText('Move')).toBeInTheDocument();
    expect(screen.getByText('Delta')).toBeInTheDocument();

    expect(screen.getByText('hanging_piece')).toBeInTheDocument();
    expect(screen.getByText('mate')).toBeInTheDocument();
    expect(screen.getByText('e2e4')).toBeInTheDocument();
    expect(screen.getByText('e2e3')).toBeInTheDocument();
    expect(screen.getByText('g1f3')).toBeInTheDocument();
    expect(screen.getByText('12.1')).toBeInTheDocument();
    expect(screen.getByText('7.2')).toBeInTheDocument();
    expect(screen.getByText('-2.4')).toBeInTheDocument();
    expect(screen.getByText('-1.1')).toBeInTheDocument();
  });
});
