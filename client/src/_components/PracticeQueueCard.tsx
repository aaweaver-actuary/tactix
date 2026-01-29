import { ColumnDef } from '@tanstack/react-table';
import { PracticeQueueItem } from '../api';
import BaseCard, { BaseCardDragHandleProps } from './BaseCard';
import PracticeQueue from './PracticeQueue';
import Text from './Text';

interface PracticeQueueCardProps {
  data: PracticeQueueItem[] | null;
  columns: ColumnDef<PracticeQueueItem>[];
  includeFailedAttempt: boolean;
  loading: boolean;
  onIncludeFailedAttemptChange: (next: boolean) => void;
  onRowClick?: (row: PracticeQueueItem) => void;
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export default function PracticeQueueCard({
  data,
  columns,
  includeFailedAttempt,
  loading,
  onIncludeFailedAttemptChange,
  onRowClick,
  dragHandleProps,
  dragHandleLabel,
  onCollapsedChange,
}: PracticeQueueCardProps) {
  return (
    <BaseCard
      className="p-4"
      header={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-display text-sand">Practice queue</h3>
            <Text value="Missed tactics from your games, ready to drill." />
          </div>
          <label className="flex items-center gap-2 text-xs text-sand/70">
            <input
              type="checkbox"
              className="accent-teal"
              checked={includeFailedAttempt}
              onChange={(event) =>
                onIncludeFailedAttemptChange(event.target.checked)
              }
              disabled={loading}
            />
            Include failed attempts
          </label>
        </div>
      }
      contentClassName="pt-3"
      dragHandleProps={dragHandleProps}
      dragHandleLabel={dragHandleLabel}
      onCollapsedChange={onCollapsedChange}
    >
      <PracticeQueue data={data} columns={columns} onRowClick={onRowClick} />
    </BaseCard>
  );
}
