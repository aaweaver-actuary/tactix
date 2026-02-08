import { PostgresStatus } from '../api';
import Badge from './Badge';
import BaseCard, { BaseCardDragHandleProps } from './BaseCard';
import Text from './Text';

interface PostgresStatusCardProps {
  status: PostgresStatus | null;
  loading: boolean;
  dragHandleProps?: BaseCardDragHandleProps;
  dragHandleLabel?: string;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export default function PostgresStatusCard({
  status,
  loading,
  dragHandleProps,
  dragHandleLabel,
  onCollapsedChange,
}: PostgresStatusCardProps) {
  if (!status && !loading) return null;

  if (!status) {
    return (
      <BaseCard
        className="p-4"
        header={<span className="sr-only">Postgres status</span>}
        dragHandleProps={dragHandleProps}
        dragHandleLabel={dragHandleLabel}
        onCollapsedChange={onCollapsedChange}
      >
        <div className="text-sand/70">Loading Postgres status...</div>
      </BaseCard>
    );
  }

  return (
    <BaseCard
      className="p-4"
      header={
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-display text-sand">Postgres status</h3>
          <Badge
            label={
              status.status === 'ok'
                ? 'Connected'
                : status.status === 'disabled'
                  ? 'Disabled'
                  : 'Unreachable'
            }
          />
        </div>
      }
      contentClassName="pt-3"
      data-testid="postgres-status"
      dragHandleProps={dragHandleProps}
      dragHandleLabel={dragHandleLabel}
      onCollapsedChange={onCollapsedChange}
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="flex flex-col gap-1">
          <Text mode="uppercase" value="Latency" />
          <Text
            size="sm"
            mode="normal"
            value={
              status.latency_ms !== undefined
                ? `${status.latency_ms.toFixed(2)} ms`
                : 'n/a'
            }
          />
        </div>
        <div className="flex flex-col gap-1">
          <Text mode="uppercase" value="Schema" />
          <Text size="sm" mode="normal" value={status.schema ?? 'n/a'} />
        </div>
        <div className="flex flex-col gap-1">
          <Text mode="uppercase" value="Tables" />
          <Text
            size="sm"
            mode="normal"
            value={
              status.tables && status.tables.length
                ? status.tables.join(', ')
                : 'n/a'
            }
          />
        </div>
      </div>
      {status.error ? <Text mode="error" value={status.error} mt="2" /> : null}
      <div className="mt-4">
        <Text mode="uppercase" value="Recent ops events" />
        {status.events && status.events.length ? (
          <ul className="mt-2 space-y-2 text-xs text-sand/70">
            {status.events.slice(0, 5).map((event) => (
              <li key={event.id} className="flex flex-wrap gap-2">
                <span className="font-mono text-sand/50">
                  {new Date(event.created_at).toLocaleTimeString()}
                </span>
                <span className="text-sand">
                  {event.component}:{event.event_type}
                </span>
                {event.source ? <Badge label={event.source} /> : null}
              </li>
            ))}
          </ul>
        ) : (
          <Text
            size="xs"
            mode="normal"
            value={loading ? 'Loading events...' : 'No events yet'}
            mt="2"
          />
        )}
      </div>
    </BaseCard>
  );
}
