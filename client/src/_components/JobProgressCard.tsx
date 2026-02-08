import { JobProgressItem } from '../types';
import Badge from './Badge';
import BaseCard, { BaseCardDragHandleProps } from './BaseCard';

interface JobProgressCardProps {
  entries: JobProgressItem[];
  status: 'idle' | 'running' | 'error' | 'complete';
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export default function JobProgressCard({
  entries,
  status,
  dragHandleProps,
  dragHandleLabel,
  onCollapsedChange,
}: JobProgressCardProps) {
  if (!entries.length) return null;

  return (
    <BaseCard
      className="p-4"
      header={
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-display text-sand">Job progress</h3>
          <Badge
            label={
              status === 'running'
                ? 'Running'
                : status === 'complete'
                  ? 'Complete'
                  : status === 'error'
                    ? 'Error'
                    : 'Idle'
            }
          />
        </div>
      }
      contentClassName="pt-3"
      dragHandleProps={dragHandleProps}
      dragHandleLabel={dragHandleLabel}
      onCollapsedChange={onCollapsedChange}
    >
      <ol className="space-y-2 text-sm">
        {entries.map((entry, index) => {
          const detail =
            entry.analyzed !== undefined && entry.total !== undefined
              ? `${entry.analyzed}/${entry.total}`
              : entry.fetched_games !== undefined
                ? `${entry.fetched_games} games`
                : entry.positions !== undefined
                  ? `${entry.positions} positions`
                  : entry.metrics_version !== undefined
                    ? `v${entry.metrics_version}`
                    : entry.schema_version !== undefined
                      ? `schema v${entry.schema_version}`
                      : null;
          const timestamp = entry.timestamp
            ? new Date(entry.timestamp * 1000).toLocaleTimeString()
            : null;
          return (
            <li
              key={`${entry.step}-${entry.timestamp ?? index}`}
              className="flex flex-wrap items-center gap-2 text-sand/80"
            >
              {timestamp ? (
                <span className="font-mono text-xs text-sand/60">
                  {timestamp}
                </span>
              ) : null}
              <span className="font-display text-sand">{entry.step}</span>
              {entry.message ? (
                <span className="text-sand/70">{entry.message}</span>
              ) : null}
              {detail ? <Badge label={detail} /> : null}
            </li>
          );
        })}
      </ol>
    </BaseCard>
  );
}
